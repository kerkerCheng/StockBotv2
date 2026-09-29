"""投資人短評（Investor Brief，2026-09-15）：**七格前因後果、文字由 session 寫、數字由 authority 填**。

## 它解什麼

APP 的首屏原本是一堆格（現價、目標價、兩桿拆解、敏感度…）與內部名詞（session_judgment、
input_dependency）。投資人要的單位不是「格」，是「句」：什麼在放量、這家公司供什麼、為什麼卡在它、
市場現在怎麼看、我們賭什麼、對了／錯了會怎樣、什麼時候知道——**順序就是前因後果**。

## 三條規則（型別層強制，不是自律）

1. **文字由 session 寫，數字由 authority 填。** 每格文字裡的數字只能是 `{placeholder}`（封閉字彙，
   見 `PLACEHOLDERS`）；materialize 時由 read model 的 Datum 填入，所以數字永遠不會過期、也不會是 LLM 打的。
   ⚠ 允許的例外只有**年份**（`2030 年`）與**證據裡的事實數字**（`20 億美元`）——它們指得回引用；
   但 `{price}`／`{bet_target}` 這七種 authority 數字若被打成字面值，寫入端擋下。
2. **每格必帶引用**，且引用必須解析到 packet 的 evidence index——與五軸判斷同一道驗證（L15：先解析
   身分，再查權限）。解析不到就整格拒收，不是整筆。
3. **禁字表**：`FORBIDDEN_TERMS` 裡的內部名詞出現在任何一格就拒收。首屏是投資人的，不是分析師的。

## 它不是什麼

- 不是 thesis 的替代：thesis／variant view／五軸照舊；短評是**給人讀的投影**，每一句都指得回它們的證據。
- 不是新的數字：它一個數都不產生；沒有 `{payoff}` 可填時那一格就印「（尚無）」並標 missing。
- 不跑 runtime LLM：寫的時機是研究 session（`python -m alpha research <T>` 的 packet 多了 `brief_frame`；套件叫 narrative 是因為 `alpha/brief.py` 已是 daily brief 的渲染模組），
  APP 只讀 materialize 的結果（`LLM changes cognition; APP reads cognition`）。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from ..errors import ContractViolation

RECORD_VERSION = "investor-brief/v1"
#: v1＝原七格（含已退役的估值 placeholder）；**照讀、不改寫**，新寫一律 v2（Phase 3 Step 3.4，ROADMAP A1）。
RECORD_VERSION_V1 = RECORD_VERSION
RECORD_VERSION_V2 = "investor-brief/v2"
RECORD_VERSIONS: tuple[str, ...] = (RECORD_VERSION_V1, RECORD_VERSION_V2)

#: 七格，**順序即前因後果**。key 是封閉字彙；label 是首屏印出來的小標題。
BRIEF_SLOTS: tuple[tuple[str, str], ...] = (
    ("demand", "什麼在放量、誰在花錢"),
    ("supply", "這家公司供什麼"),
    ("bottleneck", "為什麼卡在它"),
    ("market_view", "市場現在怎麼看"),
    ("our_bet", "我們賭什麼"),
    ("if_right_if_wrong", "如果對了／錯了"),
    ("when", "什麼時候知道"),
)
SLOT_KEYS: tuple[str, ...] = tuple(k for k, _ in BRIEF_SLOTS)
SLOT_LABELS: Mapping[str, str] = dict(BRIEF_SLOTS)

#: v2 七格（Phase 3 Step 3.4，使用者定案 #1）。**題目變了的格換 key**（L12）：`supply`→`position`、
#: `market_view`→`priced_in`、`if_right_if_wrong`→`what_must_be_true`——同一個 key 承載新舊兩個題目，
#: 讀的人分不出哪一份在答哪一題。
BRIEF_SLOTS_V2: tuple[tuple[str, str], ...] = (
    ("demand", "什麼在放量、誰在花錢"),
    ("position", "坐在哪幾層／格、各占多少營收"),
    ("bottleneck", "為什麼卡在它"),
    ("priced_in", "已定價嗎"),
    ("our_bet", "我們賭什麼"),
    ("what_must_be_true", "什麼必須為真、錯的訊號是什麼"),
    ("when", "什麼時候知道"),
)
SLOT_KEYS_V2: tuple[str, ...] = tuple(k for k, _ in BRIEF_SLOTS_V2)
SLOT_LABELS_V2: Mapping[str, str] = dict(BRIEF_SLOTS_V2)


def slot_keys(version: str) -> tuple[str, ...]:
    return SLOT_KEYS_V2 if version == RECORD_VERSION_V2 else SLOT_KEYS


def slot_labels(version: str) -> Mapping[str, str]:
    return SLOT_LABELS_V2 if version == RECORD_VERSION_V2 else SLOT_LABELS

#: 每格的提問與「不得」——放進 packet 的 `brief_frame`，session 照這個寫。
BRIEF_FRAME: Mapping[str, Mapping[str, str]] = {
    "demand": {
        "question": "什麼在放量、誰在花錢？（需求端：哪個系統／哪家客戶正在花真錢，錢往哪裡流）",
        "look_at": "demand anchor、客戶端的資本承諾（投資／預付／長約）、你當初抓到的推文與文件",
        "do_not": "⚠ 不得寫『AI 需求強勁』這種沒有主詞的句子——要有誰、花多少、買什麼。⚠ 金額要指得回引用。",
    },
    "supply": {
        "question": "這家公司供什麼？（一句話說它賣的東西在那個系統裡的位置）",
        "look_at": "supplies_to 邊、產品線、分部",
        "do_not": "⚠ 不得用內部節點名（tech:external_laser_source）——用人話（CPO 用的外部雷射光源）。",
    },
    "bottleneck": {
        "question": "為什麼卡在它？（換掉它有多難、要多久、誰驗證過）",
        "look_at": "substitutability、sole_source 的客戶端印證、qualification、產能瓶頸、法規",
        "do_not": "⚠ 不得寫 sole_source／designed_in／substitutability=5——寫『目前只有它一家被設計進去』。"
                  "⚠ 供應商自己說的獨家不算，要說出是誰印證的。",
    },
    "market_view": {
        "question": "市場現在怎麼看？（市場已經把什麼算進價格了）",
        "look_at": "共識 EPS／營收成長、賣方目標價、現價對共識付的倍數",
        "do_not": "⚠ 數字一律用 placeholder：{sell_side_target}、{market_multiple}、{analyst_count}。"
                  "⚠ 不得寫 forward P/E、consensus——寫『市場付的倍數』『分析師平均』。",
    },
    "our_bet": {
        "question": "我們賭什麼？（我們跟市場的差異看法是哪一件事，一句話）",
        "look_at": "variant 假設（scenario=variant）、thesis 的爭點",
        "do_not": "⚠ 賭的必須是 variant 假設寫下的那件事，不得多寫一個 ledger 裡沒有的賭注。"
                  "⚠ 假設值用 {bet_assumption:driver[scope]}／{assumption:driver[scope]}，不得打字面值。",
    },
    "if_right_if_wrong": {
        "question": "如果對了值多少？如果判斷錯了值多少？錯的訊號是什麼？",
        "look_at": "{bet_target}、{payoff}、{downside_target}、{downside_return}、{price}、disproof 條件",
        "do_not": "⚠ 目標價與報酬一律 placeholder。⚠ 錯的訊號要是可觀測的條件，不是『情況變差』。"
                  "⚠ **對了與錯了要對稱**（D2，2026-09-16）：只寫上檔的那一半不算寫完——"
                  "首屏是使用者唯一會讀的那一屏，對稱在這裡斷掉等於沒有對稱。"
                  "⚠ 沒有 downside scenario 時**不要硬寫**：那兩個 placeholder 會印「（尚無）」並標 partial，"
                  "而「還沒做」與「做了，結論是跌幅有限」是兩件不同的事（缺席不得被壓成一句無資料）。"
                  "⚠ **不得在 placeholder 旁邊寫一句依賴那個數字大小的結論**"
                  "（「兩邊差不多大」「極不對稱」「跌不下去」）：數字由 authority 每天重填，那句話不會——"
                  "2026-09-19 實測，寫的當下用的是 +10.1%／−10.0%，填出來是 +5.7%／−13.6%，**當場就是錯的**。"
                  "要講不對稱就講「兩邊一起看」，把大小留給數字自己說。",
    },
    "when": {
        "question": "什麼時候知道？（最近的裁決點）",
        "look_at": "催化劑、檢核點、下一次財報",
        "do_not": "⚠ 日期用 {next_checkpoint_date}；『終究會被發現』不是時點。",
    },
}

#: v2 的題目（放進 packet 的 `brief_frame`）。**題目本身就是目標**（L19）——所以估值的題目整格拿掉，不是只加欄位。
BRIEF_FRAME_V2: Mapping[str, Mapping[str, str]] = {
    "demand": {
        "question": "什麼在放量、誰在花錢？（需求端：哪個系統／哪家客戶正在花真錢，錢往哪裡流）",
        "look_at": "你騎的讀圖的需求側、客戶端的資本承諾（投資／預付／長約）",
        "do_not": "⚠ 不得寫『AI 需求強勁』這種沒有主詞的句子——要有誰、花多少、買什麼。⚠ 金額要指得回引用。",
    },
    "position": {
        "question": "它坐在哪幾層／哪幾格？各占多少營收？（出現在數字裡了嗎——引用「年增 {in_numbers_latest}（{in_numbers_as_of}）」；它填的是年增率，不是營收）",
        "look_at": "rides[] 的讀圖供給側、分部／產品線占比、三題稽核區「出現在數字裡了嗎」那一行",
        "do_not": "⚠ 不得用內部節點名——用人話。⚠ 答了 `answers.in_numbers`＝yes／no 這一格就必須含 {in_numbers_latest}。",
    },
    "bottleneck": {
        "question": "為什麼卡在它？（引用你騎的讀圖結論；誰想殺它＝反向路徑上的替代者）",
        "look_at": "rides[] 的讀圖判讀（護城河／量）、substitutability、客戶端印證、反向路徑",
        "do_not": "⚠ 不得寫 sole_source／designed_in／substitutability=5——寫『目前只有它一家被設計進去』。"
                  "⚠ 供應商自己說的獨家不算，要說出是誰印證的。",
    },
    "priced_in": {
        "question": "已定價嗎？（自己跟自己的三年歷史比；主題等權組只當脈絡）",
        "look_at": "三題稽核區：{own_history_pctile}（{own_history_basis}）、{cohort_median}、{rel_return_30d}／{rel_return_90d}",
        "do_not": "⚠ **必須含 {own_history_pctile}**；組的兩行有值時必須一併引用。⚠ 不設門檻：幾分算已定價是你的判斷，"
                  "寫出理由，不寫目標價、不寫同業折價、不寫報酬。",
    },
    "our_bet": {
        "question": "我們賭的是哪一件事？騎的是層還是插槽？",
        "look_at": "rides[] 的單位與讀圖結論、thesis 的爭點",
        "do_not": "⚠ 賭的是一件可被反證的事，不是一個價格。",
    },
    "what_must_be_true": {
        "question": "什麼必須為真？錯的訊號是什麼？",
        "look_at": "disproof[]（每條都會自動登記成 watch）、讀圖與 thesis 的反證",
        "do_not": "⚠ **不得有價格或報酬**（不得用 {price}、不得寫目標價）。⚠ 錯的訊號要是可觀測的條件，不是『情況變差』。",
    },
    "when": {
        "question": "什麼時候知道？（最近的裁決點）",
        "look_at": "催化劑、檢核點、下一次財報",
        "do_not": "⚠ 日期用 {next_checkpoint_date}；『終究會被發現』不是時點。",
    },
}

#: placeholder 封閉字彙 → 填值時取哪一格。**只有這些**；別的 `{…}` 一律拒收。
PLACEHOLDERS: Mapping[str, str] = {
    "price": "現價（Engine C；含報價單位）",
    "base_target": "base 目標價（valuation.fair_value）",
    "bet_target": "賭注目標價（variant fair value）",
    "base_return": "base 隱含價格報酬（simple）",
    "payoff": "賭注對了的隱含價格報酬（simple）",
    "downside_target": "判斷錯了的目標價（downside scenario fair value）",
    "downside_return": "判斷錯了的隱含價格報酬（simple）",
    "sell_side_target": "賣方目標價均值（Engine C 快照）",
    "market_multiple": "市場對共識付的倍數",
    "analyst_count": "分析師人數",
    "value_date": "目標價是哪一天的值",
    "next_checkpoint_date": "最近的檢核點／催化劑日期",
    "ripeness": "熟成度：已裁決／有指名假設的催化劑數（V1；沒有連結時印「（尚無）」）",
    "gap_closure": "市場承認了嗎：自判斷日以來共識每股盈餘的移動（V2）",
}
#: v2 的 placeholder 字彙（Phase 3 Step 3.4）：拿掉已退役估值鏈的九個與帶參數的兩種（它們的值來源已不存在，
#: 填出來恆是「（尚無）」），留下仍有 authority 的五個，加三題稽核區的七個。
PLACEHOLDERS_V2: Mapping[str, str] = {
    "price": "現價（Engine C；含報價單位）",
    "analyst_count": "分析師人數",
    "next_checkpoint_date": "最近的檢核點／催化劑日期",
    "ripeness": "熟成度：已裁決／有指名假設的催化劑數",
    "gap_closure": "市場承認了嗎：自判斷日以來共識每股盈餘的移動",
    "own_history_pctile": "已定價①：自家三年歷史百分位（三題稽核區）",
    "own_history_basis": "已定價①的口徑（EV/S 或 P/S）",
    "cohort_median": "已定價②：主題等權組同口徑中位數",
    "rel_return_30d": "已定價③：相對組 30 個交易日漲幅",
    "rel_return_90d": "已定價③：相對組 90 個交易日漲幅",
    "in_numbers_latest": "出現在數字裡了嗎：序列最新一點的**年增率**（YoY；不是營收本身——寫「年增 {in_numbers_latest}」；最新一點沒有年增〔例：分部占比序列〕時印（尚無））",
    "in_numbers_as_of": "出現在數字裡了嗎：最新一點的日期",
}
#: `what_must_be_true` 不得出現的 placeholder：價格與已定價的數字（「對了值多少」已退役，那一格只談條件）。
WHAT_MUST_BE_TRUE_FORBIDDEN: frozenset[str] = frozenset({
    "price", "own_history_pctile", "cohort_median", "rel_return_30d", "rel_return_90d"})


def placeholder_vocab(version: str) -> Mapping[str, str]:
    return PLACEHOLDERS_V2 if version == RECORD_VERSION_V2 else PLACEHOLDERS


#: 帶參數的 placeholder：`{assumption:driver[scope]}`（base 值）／`{bet_assumption:driver[scope]}`（variant 值）。
PARAM_PLACEHOLDER = re.compile(r"\{(assumption|bet_assumption):([a-z_]+)\[([^\]{}]+)\]\}")
SIMPLE_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")

#: 首屏禁字表。出現任何一個就拒收——這是首屏的定義，不是風格建議。
FORBIDDEN_TERMS: tuple[str, ...] = (
    "session_judgment", "input_dependency", "heuristic_proxy", "base-case", "base case", "implied return",
    "隱含報酬", "EPS 差異貢獻", "倍數差異貢獻", "兩桿", "non-GAAP", "non_gaap", "GAAP", "sole_source",
    "designed_in", "substitutability", "evidence tier", "evidence_tier", "variant view", "variant_view",
    "consensus_inverted", "expectation gap", "expectation_gap", "readiness", "absence_kind",
    "forward P/E", "forward PE", "fair value", "fair_value", "tech:", "co:", "mat:", "engine_c://", "graph://",
)


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractViolation(f"{label} 必須是非空字串")
    return value


def placeholders_in(text: str) -> list[str]:
    """一段文字裡用到的 placeholder（含帶參數的，原樣回傳），順序保留。"""
    found: list[str] = []
    for match in PARAM_PLACEHOLDER.finditer(text):
        found.append(match.group(0))
    stripped = PARAM_PLACEHOLDER.sub("", text)
    for match in SIMPLE_PLACEHOLDER.finditer(stripped):
        found.append(match.group(0))
    return found


def validate_slot_text(slot: str, text: str, *, version: str = RECORD_VERSION_V1) -> None:
    """一格文字的三條規則：禁字、placeholder 字彙（依版本）、不得有未知的 `{…}`。"""
    for term in FORBIDDEN_TERMS:
        if term.lower() in text.lower():
            raise ContractViolation(f"brief[{slot}] 含首屏禁字 {term!r}——短評是給投資人讀的，不是分析師欄位")
    vocab = placeholder_vocab(version)
    for token in placeholders_in(text):
        if PARAM_PLACEHOLDER.fullmatch(token):
            if version == RECORD_VERSION_V2:
                raise ContractViolation(
                    f"brief[{slot}] 用了 {token}——v2 沒有帶參數的 placeholder（假設 ledger 的值來源已隨估值鏈退役）")
            continue
        name = token[1:-1]
        if name not in vocab:
            raise ContractViolation(
                f"brief[{slot}] 用了未登記的 placeholder {token}；已知 {sorted(vocab)}"
                + ("" if version == RECORD_VERSION_V2 else " 與 {assumption:driver[scope]}／{bet_assumption:driver[scope]}"))
    leftover = SIMPLE_PLACEHOLDER.sub("", PARAM_PLACEHOLDER.sub("", text))
    if "{" in leftover or "}" in leftover:
        raise ContractViolation(f"brief[{slot}] 有不成對或格式錯誤的大括號")


@dataclass(frozen=True, slots=True)
class BriefSlot:
    key: str
    text: str
    evidence_refs: tuple[str, ...]
    record_version: str = RECORD_VERSION_V1

    def __post_init__(self) -> None:
        keys = slot_keys(self.record_version)
        if self.key not in keys:
            raise ContractViolation(f"brief slot 未登記：{self.key!r}；{self.record_version} 已知 {keys}")
        _nonempty(self.text, f"brief[{self.key}].text")
        validate_slot_text(self.key, self.text, version=self.record_version)
        if not self.evidence_refs:
            raise ContractViolation(f"brief[{self.key}] 必須至少引用一條證據——每一句都要指得回它從哪來")
        if any(not isinstance(r, str) or not r.strip() for r in self.evidence_refs):
            raise ContractViolation("evidence_refs 每一項必須是非空字串")

    @property
    def placeholders(self) -> tuple[str, ...]:
        return tuple(placeholders_in(self.text))


#: 候選狀態（Phase 3 Step 3.4，使用者定案 #2）。寫的人能宣告的只有前四個；**`held`（已持有）一律由 Sheet 推導**，不收。
CANDIDATE_STATES_DECLARABLE: tuple[str, ...] = ("open", "missing", "priced_wait", "pass")
CANDIDATE_STATES: tuple[str, ...] = (*CANDIDATE_STATES_DECLARABLE, "held")
#: 三題中由寫的人宣告的兩題（會死嗎由四盞燈機械回答，不由人答）。
ANSWER_KEYS: tuple[str, ...] = ("priced_in", "in_numbers")
ANSWER_VALUES: tuple[str, ...] = ("yes", "no", "unmeasurable")
#: 醒來／觸及／到期的敘事來源 watch 在下一版的處置（對到 watch 既有的封閉收據字彙，§5 第 6 點）。
ACK_DISPOSITIONS: tuple[str, ...] = ("still_holds", "thesis_changed", "retired")
RIDE_UNITS: tuple[str, ...] = ("layer", "socket")
#: 反證的 `source`：自己寫的（self）、thesis 的 claim／memo 條目、或讀圖 id——**指得回原文**（L18）。
DISPROOF_SOURCE_PREFIXES: tuple[str, ...] = ("self", "thesis:", "claim:", "sr_")


def _iso_day(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise ContractViolation(f"{label} 必須是 YYYY-MM-DD（收到 {value!r}）") from None


@dataclass(frozen=True, slots=True)
class Ride:
    """敘事騎的一格：節點＋單位（層／插槽）＋那時現行的讀圖 id。"""

    node: str
    unit: str
    reading_id: str

    def __post_init__(self) -> None:
        _nonempty(self.node, "rides[].node")
        if self.unit not in RIDE_UNITS:
            raise ContractViolation(f"rides[].unit 必須是 {RIDE_UNITS} 之一（收到 {self.unit!r}）")
        if not str(self.reading_id).startswith("sr_"):
            raise ContractViolation("rides[].reading_id 必須是讀圖 id（sr_…）")

    def as_dict(self) -> dict[str, str]:
        return {"node": self.node, "unit": self.unit, "reading_id": self.reading_id}


@dataclass(frozen=True, slots=True)
class NarrativeDisproof:
    """敘事依賴的一條反證（L7 三件套＋實體＋到期＋出處）。寫入即登記成語意 watch，或以來源鍵連到已在盯的那一筆。"""

    condition: str
    check_frequency: str
    action_48h: str
    entities: tuple[str, ...]
    expires: date
    source: str
    link_source_ref: str | None = None

    def __post_init__(self) -> None:
        _nonempty(self.condition, "disproof[].condition")
        _nonempty(self.check_frequency, "disproof[].check_frequency（L7：核查頻率）")
        _nonempty(self.action_48h, "disproof[].action_48h（L7：觸發後 48 小時動作）")
        if not any(str(e).startswith("co:") for e in self.entities):
            raise ContractViolation("disproof[].entities 至少一個 co:*（語意 watch 只認 co:*；INV-1）")
        if not isinstance(self.expires, date):
            raise ContractViolation("disproof[].expires 必須是日期")
        if not str(self.source).startswith(DISPROOF_SOURCE_PREFIXES):
            raise ContractViolation(f"disproof[].source 必須是 {DISPROOF_SOURCE_PREFIXES} 之一開頭（指得回原文，L18）")
        if self.link_source_ref is not None and not str(self.link_source_ref).startswith(("thesis:", "reading:")) \
                or (self.link_source_ref is not None and "#" not in str(self.link_source_ref)):
            raise ContractViolation("disproof[].link_source_ref 必須是既有 watch 的來源鍵（thesis:…#n 或 reading:…#n）")

    def as_dict(self) -> dict[str, Any]:
        return {"condition": self.condition, "check_frequency": self.check_frequency, "action_48h": self.action_48h,
                "entities": sorted(self.entities), "expires": self.expires.isoformat(), "source": self.source,
                "link_source_ref": self.link_source_ref}


@dataclass(frozen=True, slots=True)
class CandidateState:
    state: str
    watch_id: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.state == "held":
            raise ContractViolation("candidate_state 不收 held——「已持有」一律由 Sheet 推導，寫的人不能宣告（定案 #2）")
        if self.state not in CANDIDATE_STATES_DECLARABLE:
            raise ContractViolation(f"candidate_state.state 必須是 {CANDIDATE_STATES_DECLARABLE} 之一（收到 {self.state!r}）")
        if self.state in ("missing", "priced_wait") and not str(self.watch_id or "").strip():
            raise ContractViolation(f"candidate_state={self.state} 必須帶 watch_id（缺 X／等回落都要指向一筆在等的 watch）")
        if self.state == "pass" and not str(self.reason or "").strip():
            raise ContractViolation("candidate_state=pass 必須帶 reason（「不要」附理由、append-only）")

    def as_dict(self) -> dict[str, Any]:
        return {"state": self.state, "watch_id": self.watch_id, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class Answers:
    priced_in: str
    in_numbers: str

    def __post_init__(self) -> None:
        for key in ANSWER_KEYS:
            if getattr(self, key) not in ANSWER_VALUES:
                raise ContractViolation(f"answers.{key} 必須是 {ANSWER_VALUES} 之一")

    def as_dict(self) -> dict[str, str]:
        return {"priced_in": self.priced_in, "in_numbers": self.in_numbers}


@dataclass(frozen=True, slots=True)
class HistoryNotComparable:
    since: date
    reason: str
    source: str

    def __post_init__(self) -> None:
        _nonempty(self.reason, "history_not_comparable.reason")
        _nonempty(self.source, "history_not_comparable.source")

    def as_dict(self) -> dict[str, str]:
        return {"since": self.since.isoformat(), "reason": self.reason, "source": self.source}


@dataclass(frozen=True, slots=True)
class Acknowledgement:
    watch_id: str
    disposition: str
    note: str

    def __post_init__(self) -> None:
        _nonempty(self.watch_id, "acknowledged_touched[].watch_id")
        if self.disposition not in ACK_DISPOSITIONS:
            raise ContractViolation(f"acknowledged_touched[].disposition 必須是 {ACK_DISPOSITIONS} 之一")
        _nonempty(self.note, "acknowledged_touched[].note")

    def as_dict(self) -> dict[str, str]:
        return {"watch_id": self.watch_id, "disposition": self.disposition, "note": self.note}


@dataclass(frozen=True, slots=True)
class InvestorBrief:
    """一份短評（append-only；改一句＝append 一筆新的 supersede 舊的）。"""

    brief_id: str
    company_id: str
    ticker: str
    slots: tuple[BriefSlot, ...]
    created_at: datetime
    author: str = "session"
    supersedes_id: str | None = None
    retracted: bool = False
    context_digest: str | None = None
    record_version: str = RECORD_VERSION
    note: str = ""
    #: v2 結構化欄位（Phase 3 Step 3.4）。v1 紀錄一律是空的——**不為 v1 補寫任何一欄**（它們 id 裡沒有這些）。
    rides: tuple[Ride, ...] = ()
    disproof: tuple[NarrativeDisproof, ...] = ()
    answers: Answers | None = None
    candidate_state: CandidateState | None = None
    history_not_comparable: HistoryNotComparable | None = None
    acknowledged_touched: tuple[Acknowledgement, ...] = ()

    def __post_init__(self) -> None:
        if self.record_version not in RECORD_VERSIONS:
            raise ContractViolation(f"record_version 未登記：{self.record_version!r}；已知 {RECORD_VERSIONS}")
        _nonempty(self.brief_id, "InvestorBrief.brief_id")
        if not self.brief_id.startswith("ib_"):
            raise ContractViolation("brief_id 必須以 ib_ 開頭（由 new_brief_id 產生）")
        _nonempty(self.company_id, "InvestorBrief.company_id")
        _nonempty(self.ticker, "InvestorBrief.ticker")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ContractViolation("created_at 必須是帶時區的 datetime")
        keys = [s.key for s in self.slots]
        if len(set(keys)) != len(keys):
            raise ContractViolation(f"brief 有重複的 slot：{keys}")
        if not self.retracted:
            missing = [k for k in slot_keys(self.record_version) if k not in keys]
            if missing:
                raise ContractViolation(f"brief 七格缺一不可；缺 {missing}——少一格就不是前因後果，是片段")
        if self.record_version == RECORD_VERSION_V2:
            self._check_v2_static()
        elif (self.rides or self.disproof or self.answers or self.candidate_state
              or self.history_not_comparable or self.acknowledged_touched):
            raise ContractViolation("v1 紀錄不得帶 v2 的結構化欄位——v1 照讀、不補寫")

    def _check_v2_static(self) -> None:
        """v2 的**內容**規則（寫在紀錄上的東西本身就違規）。寫入當下才成立的檢查（讀圖現行、watch active、
        稽核行有值）只放寫入端（`alpha/providers/briefs.py`）——放在這裡，舊紀錄日後會變成解析失敗、從候選板安靜消失。"""
        if self.answers is None:
            raise ContractViolation("v2 必須帶 answers（已定價嗎／出現在數字裡了嗎；可以是 unmeasurable，不能不答）")
        if self.candidate_state is None:
            raise ContractViolation("v2 必須帶 candidate_state（可開／缺 X／已定價等回落／不要）")
        slots = {s.key: s for s in self.slots}
        priced = slots.get("priced_in")
        if priced is not None and "{own_history_pctile}" not in priced.text:
            raise ContractViolation("priced_in 那一格必須含 {own_history_pctile}——已定價嗎的主參照是自己的歷史")
        position = slots.get("position")
        if self.answers.in_numbers in ("yes", "no") and position is not None \
                and "{in_numbers_latest}" not in position.text:
            raise ContractViolation("answers.in_numbers 答了 yes／no，position 那一格就必須含 {in_numbers_latest}（型別層強制引用）")
        wmbt = slots.get("what_must_be_true")
        if wmbt is not None:
            bad = sorted(t for t in wmbt.placeholders if t[1:-1] in WHAT_MUST_BE_TRUE_FORBIDDEN)
            if bad:
                raise ContractViolation(f"what_must_be_true 不得有價格或報酬：{bad}")
        if self.candidate_state.state == "open" and not self.rides:
            raise ContractViolation("candidate_state=open 至少要騎一格讀圖（rides[] 不得為空）")
        seen: set[str] = set()
        for a in self.acknowledged_touched:
            if a.watch_id in seen:
                raise ContractViolation(f"acknowledged_touched 重複處置 {a.watch_id}")
            seen.add(a.watch_id)

    @property
    def created_on(self) -> date:
        return self.created_at.date()

    def slot(self, key: str) -> BriefSlot | None:
        return next((s for s in self.slots if s.key == key), None)

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for s in self.slots:
            for r in s.evidence_refs:
                seen.setdefault(r, None)
        return tuple(seen)


_ID_FIELDS = ("company_id", "ticker", "slots", "created_at", "author", "supersedes_id", "retracted",
              "context_digest", "note")
#: v2 的 id 欄位集合：v1 的全部＋版本＋六個結構化欄位（比照讀圖 `_ID_FIELDS_V2`）。**v1 的集合一個字都不動**——
#: 動了，7 行既有紀錄的 id 全變（plan §13）。
_ID_FIELDS_V2 = (*_ID_FIELDS, "record_version", "rides", "disproof", "answers", "candidate_state",
                 "history_not_comparable", "acknowledged_touched")


def new_brief_id(payload: Mapping[str, Any]) -> str:
    fields = _ID_FIELDS_V2 if payload.get("record_version") == RECORD_VERSION_V2 else _ID_FIELDS
    body = {k: payload.get(k) for k in fields}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "ib_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def brief_record(
    *,
    company_id: str,
    ticker: str,
    slots: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
    created_at: datetime | None = None,
    author: str = "session",
    supersedes_id: str | None = None,
    retracted: bool = False,
    context_digest: str | None = None,
    note: str = "",
    record_version: str = RECORD_VERSION_V1,
    rides: Sequence[Mapping[str, Any]] = (),
    disproof: Sequence[Mapping[str, Any]] = (),
    answers: Mapping[str, Any] | None = None,
    candidate_state: Mapping[str, Any] | None = None,
    history_not_comparable: Mapping[str, Any] | None = None,
    acknowledged_touched: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """建一筆可寫進 ledger 的紀錄（先經 `InvestorBrief` 驗證，驗不過就不產生）。

    `record_version` 預設 v1 只是為了既有呼叫端與夾具；**新寫的正式入口（`alpha brief --add`）一律 v2**。

    `slots` 可以是 `{key: {"text": …, "evidence_refs": […]}}` 或同形的 list（帶 `key`）。
    """
    stamp = created_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise ContractViolation("created_at 必須帶時區")
    stamp = stamp.astimezone(timezone.utc)
    if isinstance(slots, Mapping):
        items = [{"key": k, **dict(v)} for k, v in slots.items()]
    else:
        items = [dict(v) for v in slots]
    keys = slot_keys(record_version)
    ordered = sorted(items, key=lambda s: keys.index(s["key"]) if s.get("key") in keys else 99)
    payload: dict[str, Any] = {
        "record_version": record_version,
        "company_id": str(company_id),
        "ticker": str(ticker).upper(),
        "slots": [{"key": str(s.get("key")), "text": str(s.get("text") or ""),
                   "evidence_refs": [str(r) for r in (s.get("evidence_refs") or [])]} for s in ordered],
        "created_at": stamp.isoformat(),
        "author": author,
        "supersedes_id": supersedes_id,
        "retracted": bool(retracted),
        "context_digest": context_digest,
        "note": note,
    }
    if record_version == RECORD_VERSION_V2:
        payload.update(_v2_payload(rides=rides, disproof=disproof, answers=answers, candidate_state=candidate_state,
                                   history_not_comparable=history_not_comparable,
                                   acknowledged_touched=acknowledged_touched))
    payload["brief_id"] = new_brief_id(payload)
    parse_brief_record(payload)          # 驗證；不合法就在這裡炸，不會寫進 ledger
    return payload


def parse_brief_record(raw: Mapping[str, Any]) -> InvestorBrief:
    try:
        created = datetime.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"brief 紀錄欄位不合法：{exc}") from None
    slots_raw = raw.get("slots") or []
    if not isinstance(slots_raw, (list, tuple)):
        raise ContractViolation("slots 必須是 list")
    version = str(raw.get("record_version") or RECORD_VERSION)
    slots = tuple(BriefSlot(key=str(s.get("key") or ""), text=str(s.get("text") or ""),
                            evidence_refs=tuple(str(r) for r in (s.get("evidence_refs") or [])),
                            record_version=version)
                  for s in slots_raw)
    structured = _parse_v2_fields(raw) if version == RECORD_VERSION_V2 else {}
    return InvestorBrief(
        brief_id=str(raw.get("brief_id") or ""), company_id=str(raw.get("company_id") or ""),
        ticker=str(raw.get("ticker") or ""), slots=slots, created_at=created,
        author=str(raw.get("author") or "session"),
        supersedes_id=(str(raw["supersedes_id"]) if raw.get("supersedes_id") else None),
        retracted=bool(raw.get("retracted")), context_digest=(str(raw["context_digest"]) if raw.get("context_digest") else None),
        record_version=version, note=str(raw.get("note") or ""), **structured,
    )


def _v2_payload(*, rides, disproof, answers, candidate_state, history_not_comparable,
                acknowledged_touched) -> dict[str, Any]:
    """v2 結構化欄位 → 正規化的 payload（先建型別物件驗證、再轉回 dict——id 由正規化後的 dict 算，決定論）。"""
    parsed = _parse_v2_fields({"rides": list(rides), "disproof": list(disproof), "answers": answers,
                               "candidate_state": candidate_state, "history_not_comparable": history_not_comparable,
                               "acknowledged_touched": list(acknowledged_touched)})
    return {
        "rides": [r.as_dict() for r in parsed["rides"]],
        "disproof": [d.as_dict() for d in parsed["disproof"]],
        "answers": parsed["answers"].as_dict() if parsed["answers"] else None,
        "candidate_state": parsed["candidate_state"].as_dict() if parsed["candidate_state"] else None,
        "history_not_comparable": (parsed["history_not_comparable"].as_dict()
                                   if parsed["history_not_comparable"] else None),
        "acknowledged_touched": [a.as_dict() for a in parsed["acknowledged_touched"]],
    }


def _parse_v2_fields(raw: Mapping[str, Any]) -> dict[str, Any]:
    def seq(key: str) -> list[Mapping[str, Any]]:
        value = raw.get(key) or []
        if not isinstance(value, (list, tuple)) or any(not isinstance(v, Mapping) for v in value):
            raise ContractViolation(f"{key} 必須是物件的 list")
        return list(value)

    rides = tuple(Ride(node=str(r.get("node") or ""), unit=str(r.get("unit") or ""),
                       reading_id=str(r.get("reading_id") or "")) for r in seq("rides"))
    disproof = tuple(NarrativeDisproof(
        condition=str(d.get("condition") or ""), check_frequency=str(d.get("check_frequency") or ""),
        action_48h=str(d.get("action_48h") or ""),
        entities=tuple(sorted({str(e).strip() for e in (d.get("entities") or ()) if str(e).strip()})),
        expires=_iso_day(d.get("expires"), "disproof[].expires"), source=str(d.get("source") or ""),
        link_source_ref=(str(d["link_source_ref"]) if d.get("link_source_ref") else None)) for d in seq("disproof"))
    ans = raw.get("answers")
    answers = (Answers(priced_in=str(ans.get("priced_in") or ""), in_numbers=str(ans.get("in_numbers") or ""))
               if isinstance(ans, Mapping) else None)
    cs = raw.get("candidate_state")
    candidate = (CandidateState(state=str(cs.get("state") or ""), watch_id=(str(cs["watch_id"]) if cs.get("watch_id") else None),
                                reason=(str(cs["reason"]) if cs.get("reason") else None))
                 if isinstance(cs, Mapping) else None)
    hnc = raw.get("history_not_comparable")
    history = (HistoryNotComparable(since=_iso_day(hnc.get("since"), "history_not_comparable.since"),
                                    reason=str(hnc.get("reason") or ""), source=str(hnc.get("source") or ""))
               if isinstance(hnc, Mapping) else None)
    acks = tuple(Acknowledgement(watch_id=str(a.get("watch_id") or ""), disposition=str(a.get("disposition") or ""),
                                 note=str(a.get("note") or "")) for a in seq("acknowledged_touched"))
    return {"rides": rides, "disproof": disproof, "answers": answers, "candidate_state": candidate,
            "history_not_comparable": history, "acknowledged_touched": acks}


def select_brief(records: Sequence[InvestorBrief], *, as_of: date | None, today: date) -> InvestorBrief | None:
    """as-of 視角下生效的那一份：`created_at <= T`、最新者勝出、最新若是撤回就沒有。"""
    cutoff = as_of or today
    visible = sorted((r for r in records if r.created_on <= cutoff), key=lambda r: (r.created_at, r.brief_id))
    if not visible:
        return None
    latest = visible[-1]
    return None if latest.retracted else latest


__all__ = [
    "ACK_DISPOSITIONS", "ANSWER_KEYS", "ANSWER_VALUES", "Acknowledgement", "Answers", "BRIEF_FRAME_V2",
    "BRIEF_SLOTS_V2", "CANDIDATE_STATES", "CANDIDATE_STATES_DECLARABLE", "CandidateState", "HistoryNotComparable",
    "NarrativeDisproof", "PLACEHOLDERS_V2", "RECORD_VERSION_V1", "RECORD_VERSION_V2", "RECORD_VERSIONS", "RIDE_UNITS",
    "Ride", "SLOT_KEYS_V2", "SLOT_LABELS_V2", "WHAT_MUST_BE_TRUE_FORBIDDEN", "placeholder_vocab", "slot_keys",
    "slot_labels",
    "BRIEF_FRAME", "BRIEF_SLOTS", "FORBIDDEN_TERMS", "PARAM_PLACEHOLDER", "PLACEHOLDERS", "RECORD_VERSION",
    "SLOT_KEYS", "SLOT_LABELS", "BriefSlot", "InvestorBrief", "brief_record", "new_brief_id",
    "parse_brief_record", "placeholders_in", "select_brief", "validate_slot_text",
]
