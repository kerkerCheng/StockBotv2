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
        "question": "如果對了值多少？錯的訊號是什麼？",
        "look_at": "{bet_target}、{payoff}、{price}、disproof 條件",
        "do_not": "⚠ 目標價與報酬一律 placeholder。⚠ 錯的訊號要是可觀測的條件，不是『情況變差』。",
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
    "sell_side_target": "賣方目標價均值（Engine C 快照）",
    "market_multiple": "市場對共識付的倍數",
    "analyst_count": "分析師人數",
    "value_date": "目標價是哪一天的值",
    "next_checkpoint_date": "最近的檢核點／催化劑日期",
}
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


def validate_slot_text(slot: str, text: str) -> None:
    """一格文字的三條規則：禁字、placeholder 字彙、不得有未知的 `{…}`。"""
    for term in FORBIDDEN_TERMS:
        if term.lower() in text.lower():
            raise ContractViolation(f"brief[{slot}] 含首屏禁字 {term!r}——短評是給投資人讀的，不是分析師欄位")
    for token in placeholders_in(text):
        if PARAM_PLACEHOLDER.fullmatch(token):
            continue
        name = token[1:-1]
        if name not in PLACEHOLDERS:
            raise ContractViolation(
                f"brief[{slot}] 用了未登記的 placeholder {token}；已知 {sorted(PLACEHOLDERS)} "
                "與 {assumption:driver[scope]}／{bet_assumption:driver[scope]}")
    leftover = SIMPLE_PLACEHOLDER.sub("", PARAM_PLACEHOLDER.sub("", text))
    if "{" in leftover or "}" in leftover:
        raise ContractViolation(f"brief[{slot}] 有不成對或格式錯誤的大括號")


@dataclass(frozen=True, slots=True)
class BriefSlot:
    key: str
    text: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.key not in SLOT_KEYS:
            raise ContractViolation(f"brief slot 未登記：{self.key!r}；已知 {SLOT_KEYS}")
        _nonempty(self.text, f"brief[{self.key}].text")
        validate_slot_text(self.key, self.text)
        if not self.evidence_refs:
            raise ContractViolation(f"brief[{self.key}] 必須至少引用一條證據——每一句都要指得回它從哪來")
        if any(not isinstance(r, str) or not r.strip() for r in self.evidence_refs):
            raise ContractViolation("evidence_refs 每一項必須是非空字串")

    @property
    def placeholders(self) -> tuple[str, ...]:
        return tuple(placeholders_in(self.text))


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

    def __post_init__(self) -> None:
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
            missing = [k for k in SLOT_KEYS if k not in keys]
            if missing:
                raise ContractViolation(f"brief 七格缺一不可；缺 {missing}——少一格就不是前因後果，是片段")

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


def new_brief_id(payload: Mapping[str, Any]) -> str:
    body = {k: payload.get(k) for k in _ID_FIELDS}
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
) -> dict[str, Any]:
    """建一筆可寫進 ledger 的紀錄（先經 `InvestorBrief` 驗證，驗不過就不產生）。

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
    ordered = sorted(items, key=lambda s: SLOT_KEYS.index(s["key"]) if s.get("key") in SLOT_KEYS else 99)
    payload: dict[str, Any] = {
        "record_version": RECORD_VERSION,
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
    slots = tuple(BriefSlot(key=str(s.get("key") or ""), text=str(s.get("text") or ""),
                            evidence_refs=tuple(str(r) for r in (s.get("evidence_refs") or [])))
                  for s in slots_raw)
    return InvestorBrief(
        brief_id=str(raw.get("brief_id") or ""), company_id=str(raw.get("company_id") or ""),
        ticker=str(raw.get("ticker") or ""), slots=slots, created_at=created,
        author=str(raw.get("author") or "session"),
        supersedes_id=(str(raw["supersedes_id"]) if raw.get("supersedes_id") else None),
        retracted=bool(raw.get("retracted")), context_digest=(str(raw["context_digest"]) if raw.get("context_digest") else None),
        record_version=str(raw.get("record_version") or RECORD_VERSION), note=str(raw.get("note") or ""),
    )


def select_brief(records: Sequence[InvestorBrief], *, as_of: date | None, today: date) -> InvestorBrief | None:
    """as-of 視角下生效的那一份：`created_at <= T`、最新者勝出、最新若是撤回就沒有。"""
    cutoff = as_of or today
    visible = sorted((r for r in records if r.created_on <= cutoff), key=lambda r: (r.created_at, r.brief_id))
    if not visible:
        return None
    latest = visible[-1]
    return None if latest.retracted else latest


__all__ = [
    "BRIEF_FRAME", "BRIEF_SLOTS", "FORBIDDEN_TERMS", "PARAM_PLACEHOLDER", "PLACEHOLDERS", "RECORD_VERSION",
    "SLOT_KEYS", "SLOT_LABELS", "BriefSlot", "InvestorBrief", "brief_record", "new_brief_id",
    "parse_brief_record", "placeholders_in", "select_brief", "validate_slot_text",
]
