"""故事層的寫法規則（2026-10-29；ROADMAP 旁支「個股頁：故事層與依據層」B 段）——**純規則，不讀不寫任何檔**。

## 它解什麼

敘事每一格同時寫給兩種讀者（brainstorm `2026-10-28-app-attention-ia.md` F12）：研究為了稽核寫的**依據**（原文、日期、
出處、寫作經過、「推一步」），與首屏給人讀的那一句。兩層住同一格，首屏就照印依據——使用者 2026-10-29：「理由太冗長
看不完」「太多日期很沒必要」「1815.two 真的太長了」；同時「還是很 appreciate 這種說故事的方式…至少是一個故事我可以
理解為什麼我可以投資或不能」。修法是先分開再各自定規則（L12）：**依據照舊住敘事那一格**（`contracts.BriefSlot.text`），
**故事另寫一句**（`alpha.providers.stories`，一筆對一版敘事）。

## 故事的規則（寫入時機械擋，`story_problems`）

故事是因果，不是紀錄：讀得出「為什麼能投、為什麼不能」，拿掉的是贅字，不是故事。所以擋的都是「依據的字」——
日期（只留「哪一季、哪一年」這種粒度）、內部編號、系統用語、整段英文原文、長引文，以及超過字數。
數字照舊只能是 placeholder（數字由 authority 填，首屏規則；`contracts.PLACEHOLDERS_V2`），但不准用會填出日期的那幾個。
跟著每天重算的值走的結論也擋：寫死的燈色、已定價的位置詞（「在中間」「偏貴端」——數字會動、這句不會，failure log #120、#137）、
沒寫截至的股價走勢（「之後回落約一成五」——同一句帶月份粒度的截至「（11 月中）」，2026-11-19）。
"""
from __future__ import annotations

import re
from datetime import date
from typing import Mapping

from .contracts import (FORBIDDEN_TERMS, PARAM_PLACEHOLDER, PLACEHOLDERS_V2, SIMPLE_PLACEHOLDER, SLOT_LABELS_V2,
                        lamp_colour_claims, undated_position_claims, undated_price_move_claims)

#: 只有故事、敘事裡沒有對應格的兩格（個股頁 B3、B5；F13：十三塊有 4 塊在敘事裡沒有格，首屏永遠印「還沒寫」）。
#: 它們沒有依據那一格可以指回，所以這兩格的故事**自己帶引用**（`evidence_refs`）。
STORY_ONLY_SLOTS: tuple[tuple[str, str], ...] = (
    ("revenue", "營收從哪來"),
    ("events", "最近發生什麼、影響多大"),
)
STORY_ONLY_KEYS: tuple[str, ...] = tuple(k for k, _ in STORY_ONLY_SLOTS)
#: 一份故事要寫的格：敘事 v2 七格（順序照敘事）＋只有故事的兩格。
STORY_SLOT_LABELS: Mapping[str, str] = {**SLOT_LABELS_V2, **dict(STORY_ONLY_SLOTS)}
STORY_SLOT_KEYS: tuple[str, ...] = tuple(STORY_SLOT_LABELS)

#: 每格故事最多幾個字（placeholder 以填值後約 `PLACEHOLDER_WIDTH` 字估）。使用者 2026-10-29：「押什麼這三段長度 ok
#: 但文字希望更精煉」——Sterlite 那三段現在 150–230 字；160 字是「一段話講完一件事」的長度。
STORY_MAX = 160
#: 候選理由的故事（首屏候選狀態下面那一行）：一兩句話。
CANDIDATE_STORY_MAX = 80
#: 缺 X 的短標（首頁卡片「缺：二代占比」；使用者：「缺x是缺啥 可以五字一目瞭然嗎」）。
MISSING_LABEL_MAX = 6
PLACEHOLDER_WIDTH = 8

#: 會填出日期的 placeholder：故事**每一格都不用**（日期留在依據；「什麼時候知道」寫月份字「11 月中」）。
#: `next_checkpoint_date` 原本准「什麼時候知道」那一格用，2026-10-29 拿掉：它填的是名冊上**最近的未來催化劑日**，
#: 不是句子講的那個裁決點，日子一過就換成下一個或「（尚無）」——85 份故事 5 份用了，寫完當天 2 份已印
#: 「最近的觀測點是（尚無）的第三季報」（brainstorm F17）。
STORY_DATE_PLACEHOLDERS: frozenset[str] = frozenset({"in_numbers_as_of", "in_numbers_mix_as_of", "next_checkpoint_date"})

#: 日期：ISO、年月日、月日、斜線日期。年份、季度、「1 月下旬」這種粒度不擋——故事講的是「什麼時候知道」，不是哪一天寫的。
STORY_DATE_PATTERN = re.compile(
    r"\d{4}\s*-\s*\d{1,2}\s*-\s*\d{1,2}"          # 2026-10-28
    r"|\d{4}\s*/\s*\d{1,2}\s*/\s*\d{1,2}"         # 2026/10/28
    r"|\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"   # 2026 年 10 月 28 日
    r"|\d{1,2}\s*月\s*\d{1,2}\s*日"               # 10 月 28 日
    r"|(?<![\d.])\d{1,2}-\d{1,2}(?=\s*(?:收盤|重看|那天|當天|起|前|後))"   # 10-28 收盤、11-16 重看
)
#: 內部編號：watch、假說、讀圖、敘事、故事、介紹的 id，與 pq2 編號（`[806]`）。⚠ 不用 `\b`：中文字也算 word 字元，
#: 「的ew_1452」中間沒有 word boundary。
STORY_ID_PATTERN = re.compile(r"(?<![A-Za-z0-9_])(?:ew|hy|sr|ib|st|tl|rp|ln)_[0-9a-z]{3,}|\[\d{2,4}\]")
#: 系統用語：讀的人不必知道系統怎麼運作。寫作經過（「寫這句的」「推一步」）也在這裡——那是依據的字。
STORY_SYSTEM_WORDS: tuple[str, ...] = (
    "讀圖", "watch", "pq1", "pq2", "ledger", "materialize", "placeholder", "thesis", "claim", "brief",
    "敘事", "候選", "推一步", "寫這句", "寫這格", "寫入時", "（尚無）", "稽核區",
)
#: 相對年份：故事會被讀很久（敘事換版前一直掛在首屏），2026 年寫的「今年」到 2027 年就是錯的——寫成「2026 年」。
STORY_RELATIVE_YEARS: tuple[str, ...] = ("今年", "去年", "明年", "前年", "後年")
#: 整段英文原文：連續四個以上的拉丁字詞（型號、縮寫「CW DFB 雷射」「HBM4」不擋；「Low DK2 glass fiber cloth」擋）。
STORY_ENGLISH_RUN = re.compile(r"[A-Za-z][A-Za-z0-9.\-/']*(?:[ ,]+[A-Za-z][A-Za-z0-9.\-/']*){3,}")
#: 長引文：「」裡超過 12 個字——逐字原文是依據；故事用自己的話說。
STORY_QUOTE = re.compile(r"「[^」]{13,}」")
#: 缺 X 短標不准有的字元（它是一個名詞片語，不是一句話）。
_LABEL_BANNED = re.compile(r"[，。、；：:,;（）()「」\s{}]")


def story_length(text: str) -> int:
    """故事的字數：placeholder 以填值後約 `PLACEHOLDER_WIDTH` 字估（`{own_history_pctile}` 填出來是「77」，
    `{revenue_ttm}` 是「713.7 億 INR」——取一個中間值，讓寫的人不必猜）。"""
    stripped = PARAM_PLACEHOLDER.sub("", text)
    count = len(SIMPLE_PLACEHOLDER.findall(stripped)) + len(PARAM_PLACEHOLDER.findall(text))
    return len(SIMPLE_PLACEHOLDER.sub("", stripped).strip()) + count * PLACEHOLDER_WIDTH


def story_problems(key: str, text: object, *, limit: int = STORY_MAX) -> list[str]:
    """一句故事的問題清單（空＝可以寫）。`key` 是格名（`demand`…）或 `candidate`；只用來寫錯誤訊息。"""
    label = STORY_SLOT_LABELS.get(key) or BET_LABELS.get(key) or ("候選理由" if key == "candidate" else key)
    where = f"故事〔{label}〕"
    if not isinstance(text, str) or not text.strip():
        return [f"{where} 必須是非空字串"]
    text = text.strip()
    out: list[str] = []
    size = story_length(text)
    if size > limit:
        out.append(f"{where} 約 {size} 字，上限 {limit}——拿掉日期、出處與寫作經過（那些留在依據），留下因果")
    lowered = text.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            out.append(f"{where} 含首屏禁字 {term!r}")
    for word in STORY_SYSTEM_WORDS:
        if word.lower() in lowered:
            out.append(f"{where} 含系統用語「{word}」——讀的人不必知道系統怎麼運作")
    # 寫死的燈色（2026-10-31，failure log #120）：燈每天重算、首屏另有一行——故事寫「現金跑道紅燈」，燈一變就錯
    for sentence in lamp_colour_claims(text):
        out.append(f"{where} 寫死了燈色——燈每天重算、首屏另有一行；講燈背後的事實：{sentence[:24]}")
    # 已定價的位置詞（failure log #94 的對稱面，#137）：敘事那一格可以寫明日期，故事不准寫日期——位置詞在故事裡只會凍住
    # （MOD「第 5 百分位，在中間」）。已定價那一格每句都查；候選理由只查講到價格的句子（同敘事端）。
    if key in ("priced_in", "candidate", "magnitude"):
        for words, sentence in undated_position_claims(text, require_price_word=key in ("candidate", "magnitude")):
            out.append(f"{where} 用了位置詞「{'、'.join(words)}」——百分位每天重填、這句不會；故事讓數字自己說，"
                       f"位置的判斷留在依據（敘事那一格寫明日期）：{sentence[:24]}")
    # 股價走勢沒寫截至（2026-11-19，ROADMAP 旁支）：股價會繼續動、這句不會——EFXT 10-29 寫的「回落約一成五」11-09 換版照抄。
    # 每一格都查（事件格也寫走勢，ATS.VI）；截至只到月份，日子照舊擋在下面的日期檢查。
    for sentence in undated_price_move_claims(text):
        out.append(f"{where} 寫了股價走勢卻沒寫截至——股價會繼續動、這句不會；同一句帶月份粒度的截至，"
                   f"例：脈絡（11 月中）：…或「截至 11 月中」：{sentence[:24]}")
    if PARAM_PLACEHOLDER.search(text):
        out.append(f"{where} 用了帶參數的 placeholder——v2 沒有這種字彙")
    for name in SIMPLE_PLACEHOLDER.findall(PARAM_PLACEHOLDER.sub("", text)):
        if name not in PLACEHOLDERS_V2:
            out.append(f"{where} 用了未登記的 placeholder {{{name}}}；已知 {sorted(PLACEHOLDERS_V2)}")
        elif name in STORY_DATE_PLACEHOLDERS:
            out.append(f"{where} 用了會填出日期的 {{{name}}}——日期留在依據"
                       + ("（它填的是名冊上最近的未來催化劑日，日子一過就變；寫月份字，例：11 月中）"
                          if name == "next_checkpoint_date" else ""))
    leftover = SIMPLE_PLACEHOLDER.sub("", PARAM_PLACEHOLDER.sub("", text))
    if "{" in leftover or "}" in leftover:
        out.append(f"{where} 有不成對或格式錯誤的大括號")
    for match in STORY_DATE_PATTERN.finditer(text):
        out.append(f"{where} 含日期「{match.group(0)}」——故事只寫到哪一季、哪一年；哪一天留在依據")
    for word in STORY_RELATIVE_YEARS:
        if word in text:
            out.append(f"{where} 含相對年份「{word}」——故事會被讀很久，寫成絕對年份（例：2026 年）")
    for match in STORY_ID_PATTERN.finditer(text):
        out.append(f"{where} 含內部編號「{match.group(0)}」")
    for match in STORY_ENGLISH_RUN.finditer(text):
        out.append(f"{where} 含整段英文「{match.group(0)[:40]}」——用中文說，原文留在依據")
    for match in STORY_QUOTE.finditer(text):
        out.append(f"{where} 含長引文「{match.group(0)[:24]}…」——逐字原文留在依據，故事用自己的話說")
    return out


#: 值尾端的日期括號（`market_cap` 填出「37.6 億 USD（2026-10-02）」、`revenue_ttm` 填出「…（近四季，快照 2026-10-02）」）：
#: 故事模式拿掉——日期是依據的字（它照舊在依據那一格與稽核區）。
_VALUE_DATE_NOTE = re.compile(r"\s*（[^（）]*\d{4}-\d{2}-\d{2}[^（）]*）\s*$")


def story_values(values: Mapping[str, str | None], *, today: date) -> dict[str, str | None]:
    """敘事的 placeholder 值 → 故事模式的值（**純格式化**，不算任何數）：值尾端的日期括號拿掉；`next_checkpoint_date`
    印成「11 月 14 日」（不同年才帶年份；2026-10-29 起寫入端不准故事用它，這裡留給之前寫的與 as-of 回看）。其他照抄。"""
    out: dict[str, str | None] = {}
    for key, value in values.items():
        out[key] = _VALUE_DATE_NOTE.sub("", value) if isinstance(value, str) else value
    when = values.get("next_checkpoint_date")
    if isinstance(when, str):
        try:
            day = date.fromisoformat(when[:10])
        except ValueError:
            day = None
        if day is not None:
            out["next_checkpoint_date"] = (f"{day.month} 月 {day.day} 日" if day.year == today.year
                                           else f"{day.year} 年 {day.month} 月 {day.day} 日")
    return out


#: 兩個中文字（含全形標點）之間的一格空白：placeholder 兩側習慣留空白（「第 {own_history_pctile} 百分位」），
#: 填出來是中文（「12 月 31 日」「（尚無）」）時那一格就多餘——「12 月 31 日 的」。數字與英文兩側的空白不動。
_CJK_GAP = re.compile(r"(?<=[　-〿一-鿿＀-￯]) (?=[　-〿一-鿿＀-￯])")


def fill_story(text: str, values: Mapping[str, str | None], *, absent: str) -> tuple[str, list[str]]:
    """一句故事填值：回 `(填好的句子, 缺值的 placeholder)`；缺值印 `absent`（與敘事同一個「（尚無）」，不補 0）。"""
    missing: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        value = values.get(match.group(1))
        if value is None:
            missing.append(match.group(0))
            return absent
        return value

    return _CJK_GAP.sub("", SIMPLE_PLACEHOLDER.sub(_sub, text)), missing


def missing_label_problems(label: object) -> list[str]:
    """缺 X 的短標（首頁卡片「缺：<短標>」）：一個名詞片語、≤ `MISSING_LABEL_MAX` 字、不帶標點與 placeholder。"""
    if not isinstance(label, str) or not label.strip():
        return ["缺 X 的短標必須是非空字串（首頁卡片印「缺：<短標>」）"]
    text = label.strip()
    out = []
    if len(text) > MISSING_LABEL_MAX:
        out.append(f"缺 X 的短標「{text}」有 {len(text)} 字，上限 {MISSING_LABEL_MAX}（例：二代占比、客戶是誰、產能多大）")
    if _LABEL_BANNED.search(text):
        out.append(f"缺 X 的短標「{text}」含標點或空白——它是一個名詞片語，不是一句話")
    for word in ("缺",):
        if text.startswith(word):
            out.append(f"缺 X 的短標「{text}」不必再寫「缺」——卡片會印「缺：{text[1:] or '…'}」")
    return out


# ---------------------------------------------------------------------------
# 賭注句（2026-11-22 使用者「A0 1b 2B 3b，S1–S3 做」；提案 docs/brainstorms/2026-11-22-a0-bet-line-proposal.md）
# ---------------------------------------------------------------------------
# 使用者 2026-11-20：「難把敘事組成一個我們在賭的東西」。一檔一句四格：押什麼｜翻倍要什麼｜下一個對帳日｜認錯看哪一條。
# 寫的人只寫前兩格的字與「第幾條反證」；押哪一層照抄敘事的 rides、對帳日與反證的條件／到期由程式帶（`alpha.narrative.bet_line`）。
# 它是故事（不比依據多主張）：住故事紀錄的選填鍵 `bet`，敘事換版就跟著故事一起過期。不 gate、不改候選狀態、不排序。

BET_KEYS: tuple[str, ...] = ("stake", "doubling", "disproof")
BET_LABELS: Mapping[str, str] = {"bet.stake": "賭注句：押什麼", "bet.doubling": "賭注句：翻倍要"}
BET_STAKE_MAX = 60
BET_DOUBLING_MAX = 80
# 賭注句兩格**不收任何 placeholder**（S2，2026-11-22；比提案寫的「價格與已定價的佔位字不得出現」嚴）：這一句不只印在個股頁，
# 也印在沒有值表的地方（依層頁、日曆、待做清單）——同一句不能有填了值與沒填值兩種樣子（L12）。只寫門檻（到多少），
# 現在是多少留在依據。價格與已定價的數字因此本來就進不來（G3）。檢查在 `bet_problems`。
#: 賭注句兩格都不准的字：它講的是營業數字，不是價格。
BET_PRICE_WORDS: tuple[str, ...] = ("股價", "目標價", "報酬率", "本益比", "市值要")
#: 「翻倍要」寫不出數字時的合法寫法：以這三個字開頭、寫明缺什麼（例：「無法量：缺產能與單價」）。
BET_UNMEASURABLE_PREFIX = "無法量"
#: 「翻倍要」機械分三種——**只標不擋**（L18：偵測器生出問句，不自動修）：有數字有時點｜宣告無法量｜其餘。
DOUBLING_KINDS: tuple[str, ...] = ("number", "unmeasurable", "vague")
DOUBLING_KIND_LABELS: Mapping[str, str] = {"number": "有數字", "unmeasurable": "無法量", "vague": "翻倍條件還沒寫成數字"}
#: 時點的字（年、季、半年、哪一份定期報告）；判「有數字」前先拿掉，免得「2027 年要大幅成長」的 2027 被當成數字。
_BET_TIME = re.compile(r"20\d{2}\s*年(?:度)?(?:\s*第?\s*[一二三四1-4]\s*季)?|第\s*[一二三四1-4]\s*季|[上下]半年|Q[1-4]|\d{1,2}\s*月")
_BET_QUANTITY = re.compile(r"\d|[一二兩三四五六七八九十百千]\s*(?:倍|成|億|萬)|翻倍|倍增")


def doubling_kind(text: object) -> str:
    """「翻倍要」那一句屬於哪一種（`DOUBLING_KINDS`）。純函式。"""
    if not isinstance(text, str) or not text.strip():
        return "vague"
    body = text.strip()
    if body.startswith(BET_UNMEASURABLE_PREFIX):
        return "unmeasurable"
    has_time = bool(_BET_TIME.search(body))
    has_quantity = bool(_BET_QUANTITY.search(_BET_TIME.sub("", body)))
    return "number" if has_time and has_quantity else "vague"


def bet_problems(bet: object, *, disproof_count: int) -> list[str]:
    """賭注句的問題清單（空＝可以寫）。`disproof_count`：這一版敘事有幾條反證（`disproof` 是從 1 起的序號）。"""
    if not isinstance(bet, Mapping):
        return ["bet 必須是 {stake: 押哪個量, doubling: 翻倍要哪個營業數字到多少、最晚哪一份文件看得到, disproof: 第幾條反證}"]
    out: list[str] = []
    unknown = sorted(set(bet) - set(BET_KEYS))
    if unknown:
        out.append(f"bet 有不認得的鍵 {unknown}；認得的是 {list(BET_KEYS)}（押哪一層不用寫——照抄敘事的 rides；對帳日由程式帶）")
    for key, limit in (("stake", BET_STAKE_MAX), ("doubling", BET_DOUBLING_MAX)):
        text = bet.get(key)
        where = f"故事〔{BET_LABELS['bet.' + key]}〕"
        out += story_problems("bet." + key, text, limit=limit)
        if not isinstance(text, str):
            continue
        for name in SIMPLE_PLACEHOLDER.findall(PARAM_PLACEHOLDER.sub("", text)):
            out.append(f"{where} 用了 {{{name}}}——賭注句不用佔位字（這一句也印在依層頁與日曆，那裡沒有值可填）："
                       "只寫門檻（到多少），現在是多少留在依據；價格與已定價的數字本來就不得出現（G3）")
        for word in BET_PRICE_WORDS:
            if word in text:
                out.append(f"{where} 含「{word}」——賭注句只講營業數字（營收、出貨、產能、毛利），不講價格")
    doubling = bet.get("doubling")
    if isinstance(doubling, str) and doubling.strip().startswith(BET_UNMEASURABLE_PREFIX):
        rest = doubling.strip()[len(BET_UNMEASURABLE_PREFIX):].lstrip("：:，, ")
        if "缺" not in rest or len(rest) < 3:
            out.append(f"故事〔{BET_LABELS['bet.doubling']}〕寫「無法量」要寫明缺什麼（例：無法量：缺產能與單價）")
    n = bet.get("disproof")
    if isinstance(n, bool) or not isinstance(n, int):
        out.append("bet.disproof 必須是整數——這一版敘事的第幾條反證（從 1 起）")
    elif not 1 <= n <= disproof_count:
        out.append(f"bet.disproof＝{n} 超出範圍——這一版敘事有 {disproof_count} 條反證（從 1 起）")
    return out


__all__ = [
    "BET_DOUBLING_MAX", "BET_KEYS", "BET_LABELS", "BET_PRICE_WORDS", "BET_STAKE_MAX",
    "BET_UNMEASURABLE_PREFIX", "DOUBLING_KINDS", "DOUBLING_KIND_LABELS", "bet_problems", "doubling_kind",
    "CANDIDATE_STORY_MAX", "MISSING_LABEL_MAX", "PLACEHOLDER_WIDTH", "STORY_DATE_PLACEHOLDERS", "STORY_MAX",
    "STORY_ONLY_KEYS", "STORY_ONLY_SLOTS", "STORY_RELATIVE_YEARS", "STORY_SLOT_KEYS", "STORY_SLOT_LABELS",
    "STORY_SYSTEM_WORDS",
    "fill_story", "missing_label_problems", "story_length", "story_problems", "story_values",
]
