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
"""
from __future__ import annotations

import re
from datetime import date
from typing import Mapping

from .contracts import FORBIDDEN_TERMS, PARAM_PLACEHOLDER, PLACEHOLDERS_V2, SIMPLE_PLACEHOLDER, SLOT_LABELS_V2

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

#: 會填出日期的 placeholder：故事不用（日期留在依據）。`next_checkpoint_date` 只准出現在「什麼時候知道」那一格——
#: 那一格本來就是在講哪一天。
STORY_DATE_PLACEHOLDERS: frozenset[str] = frozenset({"in_numbers_as_of", "in_numbers_mix_as_of", "next_checkpoint_date"})
STORY_DATE_SLOT = "when"

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
    """一句故事的問題清單（空＝可以寫）。`key` 是格名（`demand`…）或 `candidate`；只用來寫錯誤訊息與判
    `next_checkpoint_date` 准不准用。"""
    label = STORY_SLOT_LABELS.get(key, "候選理由" if key == "candidate" else key)
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
    if PARAM_PLACEHOLDER.search(text):
        out.append(f"{where} 用了帶參數的 placeholder——v2 沒有這種字彙")
    for name in SIMPLE_PLACEHOLDER.findall(PARAM_PLACEHOLDER.sub("", text)):
        if name not in PLACEHOLDERS_V2:
            out.append(f"{where} 用了未登記的 placeholder {{{name}}}；已知 {sorted(PLACEHOLDERS_V2)}")
        elif name in STORY_DATE_PLACEHOLDERS and not (name == "next_checkpoint_date" and key == STORY_DATE_SLOT):
            out.append(f"{where} 用了會填出日期的 {{{name}}}——日期留在依據"
                       + ("（{next_checkpoint_date} 只在「什麼時候知道」那一格用）" if name == "next_checkpoint_date" else ""))
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
    印成「11 月 14 日」（不同年才帶年份）。其他照抄。"""
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


__all__ = [
    "CANDIDATE_STORY_MAX", "MISSING_LABEL_MAX", "PLACEHOLDER_WIDTH", "STORY_DATE_PLACEHOLDERS", "STORY_MAX",
    "STORY_ONLY_KEYS", "STORY_ONLY_SLOTS", "STORY_RELATIVE_YEARS", "STORY_SLOT_KEYS", "STORY_SLOT_LABELS",
    "STORY_SYSTEM_WORDS",
    "fill_story", "missing_label_problems", "story_length", "story_problems", "story_values",
]
