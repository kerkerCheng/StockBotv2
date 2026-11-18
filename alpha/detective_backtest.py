"""偵探回溯（起漲點前看）的純規則：起漲點、對照、封存順序、遮名、偏多強度、配對分辨。

使用者 2026-11-18「做吧」＋四題作答；設計與先登記的評分在 `docs/plans/2026-11-18-001-dev-detective-backtest-plan.md` §3。
- 起漲點＝「之後 182 個日曆天內最高收盤 ≥ 2 × 當天收盤」的連續合格日裡，收盤最低的那一天（§3.1）。
- 回溯日（§3.3、§3.4）：起漲點 − 4 週若 ≥ 2026-07-01 → 清淨組、回溯日取它；否則遮名組、回溯日＝起漲點 − 8 週。
  （2026-11-18 實跑：照原定一律 8 週，清淨組 0 檔——8 月初那群起漲往前推 8 週落在 6 月；使用者同日選清淨組改 4 週。）
- 對照＝同一個主題等權組、回溯日後（提前週數＋182 天）內最高收盤 < 1.3 倍（§3.2）。原本多一條「附近沒有起漲點」，
  讓遮名組對照從 33 個掉到 1 個（這個題材 2023–2026 幾乎每檔都有過一段 2 倍），同日拿掉。

本模組沒有 I/O。**呼叫端只准印代號、日期、組別**——價格、比值、誰是贏家只住封存檔（§3.2）；
偏多強度與配對分辨是開封之後才算的東西。不寫任何 authority、不跑 LLM、不對外連線。
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Mapping, Sequence

from .detective import DRAWERS

RALLY_WINDOW_DAYS = 182
RALLY_MULTIPLE = 2.0
#: 提前幾天（組別 → 天數）：清淨組 4 週、遮名組 8 週（§3.3；2026-11-18 使用者選清淨組改 4 週）。
LEAD_DAYS: Mapping[str, int] = {"clean": 28, "masked": 56}
CONTROL_CEILING = 1.3
CONTROL_JITTER_DAYS = 14
CLEAN_FROM = date(2026, 7, 1)
GROUPS = ("clean", "masked")
GROUP_LABELS = {"clean": "清淨組", "masked": "遮名組"}
QUOTA: Mapping[str, int] = {"winner": 3, "control": 2}
#: 回溯日那根收盤最多可以早幾天（連假、停牌）；更早就當作那天沒有價格，不收。
BASE_TOLERANCE_DAYS = 7
#: 偏多的三個抽屜；窗口提早關是偏空。
BULL_DRAWERS = frozenset(DRAWERS[:3])
BEAR_DRAWERS = frozenset(DRAWERS[3:])

Bars = Sequence[tuple[date, float]]


def _usable(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value > 0


def clean_bars(bars: Iterable[tuple[date, object]]) -> list[tuple[date, float]]:
    """升序、只留可用收盤（數字、非 NaN、正數）。"""
    return sorted((d, float(v)) for d, v in bars if _usable(v))


# ---- 起漲點 ------------------------------------------------------------------------------------------
def rally_starts(bars: Bars, *, window_days: int = RALLY_WINDOW_DAYS, multiple: float = RALLY_MULTIPLE) -> list[date]:
    """起漲點（§3.1）。合格日＝之後 `window_days` 個日曆天內（不含當天）最高收盤 ≥ `multiple` × 當天收盤；
    連續的合格日（照這條序列的 K 棒順序）是一段，每段取收盤最低的那一天（同價取最早）。
    ⚠ 序列尾端的窗口沒走完：只有「已經到過 2 倍」的才合格——沒到的不是「沒漲」，是還不知道。"""
    pts = clean_bars(bars)
    n = len(pts)
    qualifying = [False] * n
    j = 0
    for i, (day, close) in enumerate(pts):
        end = day + timedelta(days=window_days)
        j = max(j, i + 1)
        while j < n and pts[j][0] <= end:
            j += 1
        future = pts[i + 1:j]
        qualifying[i] = bool(future) and max(v for _, v in future) >= multiple * close
    starts: list[date] = []
    i = 0
    while i < n:
        if not qualifying[i]:
            i += 1
            continue
        k = i
        while k + 1 < n and qualifying[k + 1]:
            k += 1
        low = min(pts[i:k + 1], key=lambda p: (p[1], p[0]))
        starts.append(low[0])
        i = k + 1
    return starts


def base_close(bars: Bars, day: date, *, tolerance_days: int = BASE_TOLERANCE_DAYS) -> tuple[date, float] | None:
    """`day` 或之前最近的一根收盤，最多早 `tolerance_days` 天（INV-6：不用之後的價）。"""
    best = None
    for d, v in clean_bars(bars):
        if d > day:
            break
        best = (d, v)
    if best is None or (day - best[0]).days > tolerance_days:
        return None
    return best


def control_window(bars: Bars, as_of: date, *, lead_days: int, ceiling: float = CONTROL_CEILING
                   ) -> tuple[bool, int, str]:
    """對照（§3.2）：[as_of, as_of + 提前天數 + 182 天] 內最高收盤 < `ceiling` × as_of 收盤。
    回（成立嗎, 實際走了幾天, 不成立的理由）——窗口沒走完照實回天數（清淨組常見，2027-05 重算）。"""
    base = base_close(bars, as_of)
    if base is None:
        return False, 0, "回溯日沒有收盤"
    horizon = as_of + timedelta(days=lead_days + RALLY_WINDOW_DAYS)
    window = [(d, v) for d, v in clean_bars(bars) if as_of < d <= horizon]
    if not window:
        return False, 0, "回溯日之後沒有收盤"
    observed = (window[-1][0] - as_of).days
    if max(v for _, v in window) >= ceiling * base[1]:
        return False, observed, "窗口內漲超過門檻"
    return True, observed, ""


def group_of(as_of: date) -> str:
    return "clean" if as_of >= CLEAN_FROM else "masked"


def case_as_of(rally_start: date) -> tuple[str, date]:
    """起漲點 → （組別, 回溯日）：提前 4 週還在截點之後就是清淨組，否則遮名組提前 8 週（§3.3、§3.4）。"""
    clean = rally_start - timedelta(days=LEAD_DAYS["clean"])
    if clean >= CLEAN_FROM:
        return "clean", clean
    return "masked", rally_start - timedelta(days=LEAD_DAYS["masked"])


def order_key(ticker: str, as_of: date) -> str:
    """封存順序（§3.2）：雜湊由小到大——不是分數、不是排序依據，只是讓挑案例不經手。"""
    return hashlib.sha256(f"{ticker}|{as_of.isoformat()}".encode()).hexdigest()


def jitter_days(ticker: str, as_of: date, *, span: int = CONTROL_JITTER_DAYS) -> int:
    """對照回溯日的偏移（±`span` 天，由代號雜湊決定）：不讓「同一天」洩漏配對。"""
    digest = hashlib.sha256(f"jitter|{ticker}|{as_of.isoformat()}".encode()).hexdigest()
    return int(digest[:8], 16) % (2 * span + 1) - span


def case_id(group: str, ticker: str, as_of: date) -> str:
    return f"{'C' if group == 'clean' else 'M'}-{order_key(ticker, as_of)[:6]}"


@dataclass(frozen=True)
class UniverseMember:
    ticker: str
    company_id: str
    cohorts: frozenset[str]     # cohort_id


def find_cases(universe: Sequence[UniverseMember], bars: Mapping[str, Bars], *, excluded: Iterable[str] = ()
               ) -> tuple[list[dict[str, object]], dict[str, int]]:
    """宇宙（主題等權組成員 − 排除）→ 贏家與對照的案例（未選、全部）＋計數（不含任何價格）。
    每檔每組最多一個贏家（最早的一段）；對照每檔每組最多一筆（雜湊最小的那筆）。
    一檔可以同時是某一段的贏家與另一段的對照（案例是「代號＋回溯日」，不是代號）；同一檔同一組只收一次由 `next_case` 擋。"""
    skip = {t.upper() for t in excluded}
    counts = Counter()
    members = []
    for m in universe:
        if m.ticker.upper() in skip:
            counts["excluded"] += 1
            continue
        if len(clean_bars(bars.get(m.ticker) or ())) < 2:
            counts["no_bars"] += 1
            continue
        members.append(m)
    counts["universe"] = len(members)
    starts = {m.ticker: rally_starts(bars[m.ticker]) for m in members}
    winners: dict[tuple[str, str], dict[str, object]] = {}
    for m in members:
        for start in starts[m.ticker]:
            group, as_of = case_as_of(start)
            if base_close(bars[m.ticker], as_of) is None:
                counts["winner_before_data"] += 1
                continue
            key = (m.ticker, group)
            if key in winners:
                continue
            winners[key] = {"case_id": case_id(group, m.ticker, as_of), "ticker": m.ticker, "company_id": m.company_id,
                            "group": group, "label": "winner", "as_of": as_of.isoformat(), "rally_start": start.isoformat(),
                            "cohorts": sorted(m.cohorts), "key": order_key(m.ticker, as_of)}
    controls: dict[tuple[str, str], dict[str, object]] = {}
    for w in sorted(winners.values(), key=lambda c: str(c["key"])):
        group = str(w["group"])
        w_as_of = date.fromisoformat(str(w["as_of"]))
        for m in members:
            if m.ticker == w["ticker"] or not (m.cohorts & set(w["cohorts"])):
                continue
            as_of = w_as_of + timedelta(days=jitter_days(m.ticker, w_as_of))
            as_of = max(as_of, CLEAN_FROM) if group == "clean" else min(as_of, CLEAN_FROM - timedelta(days=1))
            ok, observed, _why = control_window(bars[m.ticker], as_of, lead_days=LEAD_DAYS[group])
            if not ok:
                continue
            key = order_key(m.ticker, as_of)
            prev = controls.get((m.ticker, group))
            if prev is not None and str(prev["key"]) <= key:
                continue
            controls[(m.ticker, group)] = {
                "case_id": case_id(group, m.ticker, as_of), "ticker": m.ticker, "company_id": m.company_id,
                "group": group, "label": "control", "as_of": as_of.isoformat(), "paired_with": w["ticker"],
                "window_days": observed, "cohorts": sorted(m.cohorts), "key": key}
    cases = sorted([*winners.values(), *controls.values()], key=lambda c: (str(c["group"]), str(c["key"])))
    for g in GROUPS:
        counts[f"{g}_winners"] = sum(1 for c in cases if c["group"] == g and c["label"] == "winner")
        counts[f"{g}_controls"] = sum(1 for c in cases if c["group"] == g and c["label"] == "control")
    return cases, dict(counts)


# ---- 湊滿（主 session 不知道誰是誰）---------------------------------------------------------------
def next_case(cases: Sequence[Mapping[str, object]], group: str, *, quota: Mapping[str, int] = QUOTA
              ) -> Mapping[str, object] | None:
    """照封存順序給下一個要組包的案例；那一類（贏家／對照）湊滿了、或同一檔這一組已經收過，就跳過——
    跳過的不印、不說是哪一類。"""
    accepted = Counter(str(c["label"]) for c in cases if c["group"] == group and c.get("status") == "accepted")
    taken = {str(c["ticker"]) for c in cases if c["group"] == group and c.get("status") == "accepted"}
    for c in sorted((c for c in cases if c["group"] == group), key=lambda c: str(c["key"])):
        if c.get("status") in ("accepted", "skipped") or str(c["ticker"]) in taken:
            continue
        if accepted[str(c["label"])] >= quota.get(str(c["label"]), 0):
            continue
        return c
    return None


def still_needed(cases: Sequence[Mapping[str, object]], group: str, *, quota: Mapping[str, int] = QUOTA) -> int:
    accepted = Counter(str(c["label"]) for c in cases if c["group"] == group and c.get("status") == "accepted")
    return sum(max(0, n - accepted[label]) for label, n in quota.items())


# ---- 遮名（§3.5）-------------------------------------------------------------------------------------
def mask_letter(index: int) -> str:
    """0 → A、25 → Z、26 → AA…"""
    out = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


@dataclass(frozen=True)
class MaskEntry:
    company_id: str
    code: str                       # 「A」「B」…
    names: tuple[str, ...]          # 名冊的名字與別名（company_name_forms）＋英文多字本體
    tickers: tuple[str, ...] = ()
    stems: tuple[str, ...] = ()     # 中文名的本體（去掉科技、股份有限公司…）：子公司名「南京大量數控」靠它遮

    @property
    def name_code(self) -> str:
        return f"公司{self.code}"

    @property
    def ticker_code(self) -> str:
        return f"代號{self.code}"

    @property
    def stem_code(self) -> str:
        # 名字片段用另一種記號：「大量」也是普通詞，換成「公司A」會把「大量採購」讀成「公司A採購」
        return f"〔{self.code}〕"


_CJK = re.compile(r"[㐀-鿿]")
_CJK_SUFFIXES = ("股份有限公司", "有限公司", "-KY", "公司", "科技", "電子", "工業", "光電", "精密", "材料", "集團",
                 "控股", "企業", "國際", "實業", "半導體", "電機", "電路")
_ASCII_SUFFIXES = re.compile(r"(?:[\s,.]+(?:Technology|Technologies|Holding|Holdings|Limited|Ltd|Co|Inc|Corp|Corporation"
                             r"|Group|International|Industries|Industrial|Electronics|Company|plc|AG|SA|NV|AB|ASA))+[\s,.]*$",
                             re.I)


def derive_stems(names: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """名冊的寫法 → （英文多字本體, 中文本體）。名冊只登「大量科技」時，財報裡的子公司「南京大量數控科技」
    要靠本體「大量」才遮得到（2026-11-18 3167.TW 遮名包實測漏網）。英文本體只收兩個字以上（「Zhen Ding」）——
    單字的本體多半已在 `company_name_forms` 的核心名稱裡，單字普通詞（Applied、General）遮了會亂。"""
    names = [str(n).strip() for n in names if n and str(n).strip()]
    known = {n.casefold() for n in names}
    ascii_out: set[str] = set()
    cjk_out: set[str] = set()
    for n in names:
        if _CJK.search(n):
            stem = n
            changed = True
            while changed:
                changed = False
                for suf in _CJK_SUFFIXES:
                    if stem.endswith(suf) and len(stem) - len(suf) >= 2:
                        stem = stem[: -len(suf)].strip()
                        changed = True
            if stem != n and stem.casefold() not in known:
                cjk_out.add(stem)
        else:
            stem = _ASCII_SUFFIXES.sub("", n).strip()
            if stem != n and len(stem.split()) >= 2 and stem.casefold() not in known:
                ascii_out.add(stem)
    return tuple(sorted(ascii_out)), tuple(sorted(cjk_out))


def _ascii(text: str) -> bool:
    return any("a" <= ch.lower() <= "z" or ch.isdigit() for ch in text)


def _body(form: str) -> str:
    """寫法 → 正則本體；字與字之間的空白容許任意多個（PDF 轉文字常是「Zhen  Ding」兩格，2026-11-18 實測漏網）。"""
    return r"\s+".join(re.escape(part) for part in form.split())


def _ticker_forms(ticker: str) -> set[str]:
    """代號的寫法：整串（3081.TWO）＋去掉交易所尾綴的本體（3081、IQE）。"""
    t = ticker.strip()
    forms = {t}
    base = t.split(".")[0]
    if base and base != t:
        forms.add(base)
    return {f for f in forms if len(f) >= 2}


def _patterns(entries: Sequence[MaskEntry]) -> list[tuple[re.Pattern[str], str]]:
    items: list[tuple[str, str, str]] = []     # (寫法, 換成, 種類)
    for e in entries:
        items.append((e.company_id, e.name_code, "id"))
        items += [(n, e.name_code, "name") for n in e.names if n and len(n.strip()) >= 2]
        for t in e.tickers:
            items += [(f, e.ticker_code, "ticker") for f in _ticker_forms(t)]
        items += [(s, e.stem_code, "name") for s in e.stems if s and len(s.strip()) >= 2]
    items.sort(key=lambda x: -len(x[0]))      # 長的先換：全名先於本體
    out = []
    for form, repl, kind in items:
        form = unicodedata.normalize("NFKC", form.strip())
        body = _body(form)
        if kind == "ticker":
            if form.isdigit():
                pat = re.compile(rf"(?<!\d){body}(?!\d)")
            else:
                pat = re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])")
        elif _ascii(form):
            pat = re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I)
        else:
            pat = re.compile(body)
        out.append((pat, repl))
    return out


def mask_text(text: str, entries: Sequence[MaskEntry], *, normalize: bool = True) -> str:
    """NFKC 正規化（全形字母變半形，免得「ＡＸＴ」漏網）後，把每家的 company_id、名字與別名、代號換成代碼。
    長的寫法先換（「AXT Inc」先於「AXT」）。遮過頭只會少給資訊、不會洩漏——寧可多遮。
    `normalize=False` 給我們自己寫的 MANIFEST／PROMPT（名字來自名冊、本來就是半形；不動提示的全形標點）。"""
    out = unicodedata.normalize("NFKC", text) if normalize else text
    for pat, repl in _patterns(entries):
        out = pat.sub(repl, out)
    return out


def residual_forms(text: str, entries: Sequence[MaskEntry]) -> dict[str, int]:
    """遮名之後還找得到的寫法 → 次數（同一套寫法、不分大小寫、全半形正規化）。應該是空的。"""
    norm = unicodedata.normalize("NFKC", text)
    hits: dict[str, int] = {}
    for e in entries:
        for form in {e.company_id, *e.names, *e.stems, *(f for t in e.tickers for f in _ticker_forms(t))}:
            form = unicodedata.normalize("NFKC", (form or "").strip())
            if len(form) < 2:
                continue
            body = _body(form)
            if form.isdigit():
                pat = re.compile(rf"(?<!\d){body}(?!\d)")
            elif _ascii(form):
                pat = re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I)
            else:
                pat = re.compile(body)
            n = len(pat.findall(norm))
            if n:
                hits[form] = hits.get(form, 0) + n
    return hits


# ---- 偏多強度（§3.8，機械；開封之前就能算，但只在評分時印）-------------------------------------------
_CONF = re.compile(r"信心\**\s*[:：]\s*\**\s*(高|中|低)")
_DRAWER_FIELD = re.compile(r"抽屜\**\s*[:：]\s*\**\s*(" + "|".join(DRAWERS) + ")")
_DRAWER_ANY = re.compile("(" + "|".join(DRAWERS) + ")")
_SECTION = re.compile(r"^(#{2,4})\s*線索", re.M)


def lean_tally(report: str) -> dict[str, object]:
    """回報的「線索」段 → 每條的抽屜與信心。一條線索以它的「信心：」欄結束；抽屜取這一條裡的「抽屜：」欄，
    沒有欄位才退回這一條裡最後一個抽屜字樣（標題寫「線索 1｜漲價」型）。抽不到抽屜的數成 unparsed（INV-3）。
    偏多強度＝信心「高」的線索中，量超前／漲價／撐更久的條數 − 窗口提早關的條數；「中」另算、不併。"""
    m = _SECTION.search(report)
    if not m:
        return {"clues": 0, "unparsed": 0, "by": {}, "lean_high": None, "lean_mid": None, "section_found": False}
    rest = report[m.end():]
    # 段落到下一個同級或更高級的標題為止（線索底下的「#### 1」小標題不算）
    nxt = re.compile(rf"^#{{1,{len(m.group(1))}}}(?!#)", re.M).search(rest)
    section = rest[:nxt.start()] if nxt else rest
    by: dict[str, Counter] = {d: Counter() for d in DRAWERS}
    clues = unparsed = 0
    chunk_start = 0
    for c in _CONF.finditer(section):
        chunk = section[chunk_start:c.start()]
        chunk_start = c.end()
        clues += 1
        fields = _DRAWER_FIELD.findall(chunk)
        drawer = fields[-1] if fields else (_DRAWER_ANY.findall(chunk) or [None])[-1]
        if drawer is None:
            unparsed += 1
            continue
        by[drawer][c.group(1)] += 1

    def lean(level: str) -> int:
        return (sum(by[d][level] for d in BULL_DRAWERS) - sum(by[d][level] for d in BEAR_DRAWERS))

    return {"clues": clues, "unparsed": unparsed, "by": {d: dict(v) for d, v in by.items()},
            "lean_high": lean("高"), "lean_mid": lean("中"), "section_found": True}


def pair_wins(winner_scores: Sequence[float], control_scores: Sequence[float]) -> tuple[float, int]:
    """贏家 × 對照兩兩配對：贏家的分數大於對照的對數（平手算半對）。回（對數, 總對數）。"""
    wins = 0.0
    for w in winner_scores:
        for c in control_scores:
            wins += 1.0 if w > c else 0.5 if w == c else 0.0
    return wins, len(winner_scores) * len(control_scores)


def separation_verdict(wins: float, total: int) -> str:
    """§3.8 先寫死的判讀線（6 對時：≥ 5 有跡象、≤ 3 看不出；其他對數照比例）。"""
    if total == 0:
        return "沒有配對（贏家或對照是 0）"
    if wins >= total * 5 / 6:
        return "有分辨的跡象（樣本太小、不是證據，只決定要不要擴大）"
    if wins <= total / 2:
        return "看不出分辨"
    return "不確定"


# ---- 回溯日當時的鄰居（§3.6）--------------------------------------------------------------------------
def edge_known(doc_ids: Iterable[str] | None, doc_dates: Mapping[str, date | None], as_of: date) -> bool:
    """一條邊至少有一份來源文件的發布日 ≤ 回溯日才算當時知道。沒有來源、或來源都沒有日期 → 不算（INV-6）。"""
    return any((d := doc_dates.get(str(i))) is not None and d <= as_of for i in (doc_ids or ()))


def known_rows(rows: Iterable[Mapping[str, object]], doc_dates: Mapping[str, date | None], as_of: date
               ) -> tuple[list[dict[str, object]], int]:
    """查圖的列（多帶 `edge_docs`＝路徑上每條邊的 source_doc_ids）→ 回溯日當時知道的列；回（列, 拿掉幾列）。
    路徑上每一條邊都要當時知道（第二跳兩條都要）。"""
    keep: list[dict[str, object]] = []
    dropped = 0
    for row in rows:
        paths = row.get("edge_docs") or []
        if paths and all(edge_known(ids, doc_dates, as_of) for ids in paths):     # type: ignore[union-attr]
            keep.append(dict(row))
        else:
            dropped += 1
    return keep, dropped


__all__ = [
    "BEAR_DRAWERS", "BULL_DRAWERS", "CLEAN_FROM", "CONTROL_CEILING", "GROUPS", "GROUP_LABELS", "LEAD_DAYS", "MaskEntry",
    "QUOTA", "RALLY_MULTIPLE", "RALLY_WINDOW_DAYS", "UniverseMember", "base_close", "case_as_of", "case_id", "clean_bars",
    "control_window", "derive_stems", "edge_known", "find_cases", "group_of", "jitter_days", "known_rows", "lean_tally",
    "mask_letter",
    "mask_text", "next_case", "order_key", "pair_wins", "rally_starts", "residual_forms", "separation_verdict",
    "still_needed",
]
