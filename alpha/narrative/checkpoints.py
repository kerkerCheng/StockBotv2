"""「什麼時候知道」那一格寫的裁決點過了沒（2026-11-10，failure log #150；使用者「#150 … 照推薦做」）。

PSIX 的何時格 10-28 寫「最近的裁決點是第三季 10-Q（約 2026 年 11 月上旬）」，10-Q 11-05 交了、11-06 人工讀過判反證沒觸及，
這一格照舊到 11-10 換版；EFXT 10-31 的重述版仍寫「等第三季 6-K」——6-K 10-29 已交。何時格答的是「最近的裁決點」：
它一過，這一格就是舊的。

三種「過了」，只從那段文字、一手申報與名冊的日期判，不判斷文字的意思：
①日期：段落裡寫的日子中，**寫下這段文字那天還沒開始的**最近一個——今天已經過了它（寫「11 月 14 日前」的，11-15 起算過了；
  只寫到旬的是一段：「約 11 月初」＝11-01～11-10，11-11 起算過了）；
②申報：段落點名的 SEC 定期報告（10-Q／10-K／20-F／40-F）在寫下這段文字之後交了（lead 池的 edgar 申報；只有被監看的公司有）；
③佔位字：段落把 `{next_checkpoint_date}` 寫成某件事的日子（「{next_checkpoint_date} 的第三季財報」），而寫下那天名冊上的下一個
  檢核點已過——佔位字每天換成名冊上**今天**的下一個日子，那件事一過，句子就指著別的日子（AAOI、HIMX、6268.T 11-10 都是這樣，
  名冊上沒有更晚的日子時畫面印「最近的裁決點是（尚無）的第三季財報」）。單獨寫的佔位字（「…。{next_checkpoint_date}。」）
  會自己更新，不核。
「寫下這段文字那天」＝何時格這段文字最早出現的那一版（只換騎、只改別格的版本沿用，`when_text_since`）。

只叫重寫、不判斷：進候選列 `rewrite[]`，⑤「敘事該重寫」照名字去改；文字是不是真的舊了，由寫的人讀過再改。
⚠ 抓不到的：沒寫日期、點名的又不是 SEC 定期報告（「等第三季財報」「等法說」「等第三季 6-K」）——那一半要等台股財報上架
與公司 IR 的 feed（failure log #142、#147）。EFXT 那一例屬於這一半：6-K 有事就交，分不出哪一份是季報（見 `WHEN_FORMS`）。
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Mapping, Sequence

#: 候選列 `rewrite[]` 那一條的開頭——寫的一方（`alpha.providers.candidates.derive_row`）與分類的一方（`REWRITE_WHY`）共用（L16）。
CHECKPOINT_PASSED_PREFIX = "何時格的裁決點已過"
#: 三種「過了」（`checkpoint_passed` 回傳的 `kind`）。
CHECKPOINT_KINDS: tuple[str, ...] = ("date", "filing", "placeholder")

#: 何時格點名就核的 SEC 表單（/A 修正版算同一種）——只收定期報告。8-K 與 6-K 不在內：有事就交（EFXT 8 月到 10 月交了
#: 8 份 6-K、lead 標題沒有內容），點名它們的句子在等某一件特定的事，任何一份交了就叫重寫會變成恆亮（L14）。
WHEN_FORMS: tuple[str, ...] = ("10-Q", "10-K", "20-F", "40-F")
_FORM_IN_TEXT = re.compile(r"(?<![A-Za-z0-9-])(" + "|".join(map(re.escape, WHEN_FORMS)) + r")(?![A-Za-z0-9])")

_ISO = re.compile(r"(?<!\d)(20\d{2})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})(?!\d)")
_YMD = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_MD = re.compile(r"(?<![\d年])(\d{1,2})\s*月\s*(\d{1,2})\s*日")
#: 「11-14」「（10-29）」：前後不能是數字、字母或連字號（不吃 ISO 的尾巴、2027-2029、Q3-4）；後面接量詞或英文單位的是區間
#: （「2-3 家」「1-3 月」「3-5 GW」）不是日期。
_M_D = re.compile(r"(?<![\dA-Za-z\-–./])(\d{1,2})-(\d{1,2})(?![\d\-–./])"
                  r"(?!\s*(?:[家倍條季年月日週周天個位成名項人次座台片噸萬億元股吋%％]|[A-Za-z]))")
#: 只寫到月份（「2027 年 2 月上旬」「約 2027 年 4 月」）：上旬／初＝10 日、中旬／中＝20 日、其餘＝月底。
_YM = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月(?!\s*\d{1,2}\s*日)(上旬|中旬|下旬|初|中|底)?")
#: 沒寫年份、寫到旬的（「約 11 月初，日期以公司公告為準」「10 月底到 11 月初」）：年份照沒寫年份的月日推。只寫「11 月」的不收——
#: 「11 月營收」是哪個月的數字，不是日子。「月中」後面接「國、文…」是別的詞。
_MPART = re.compile(r"(?<![\d年])(\d{1,2})\s*月\s*(上旬|中旬|下旬|初|中(?![國文心華資型期])|底)")
#: 佔位字寫成某件事的日子：「{next_checkpoint_date} 的…」（中間可夾一個短括號）。
PLACEHOLDER = "{next_checkpoint_date}"
_PLACEHOLDER_AS_EVENT = re.compile(r"\{next_checkpoint_date\}\s*(?:[（(][^）)]{0,30}[）)])?\s*的")

#: 沒寫年份的月日落在「寫下那天往回 2 個月、往前 10 個月」的那一年——何時格回頭講的多半是剛讀過的（「10 月 27 日的季報
#: 已讀」），往前講的可以遠到明年年中（11-06 寫的「到 7 月 10 日 6 月營收公布為止」是 2027 年；取最近的一年會讀成今年、已過）。
#: 窗偏向未來是因為兩種讀錯的代價不對稱：把過去的讀成明年，只多一個排在後面的日子（最早的那一個照樣先過）；把明年的讀成
#: 過去，就少了一個裁決點。
YEARLESS_BACK_DAYS = 60


def _safe(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _year_for(month: int, day: int, written_on: date) -> date | None:
    """沒寫年份的月日 → 落在 [寫下那天 − 60 天, + 305 天] 的那一年（一年的窗，剛好一個）。"""
    lo = written_on - timedelta(days=YEARLESS_BACK_DAYS)
    for year in (written_on.year - 1, written_on.year, written_on.year + 1):
        d = _safe(year, month, day)
        if d is not None and lo <= d < lo + timedelta(days=365):
            return d
    return None


def when_spans(text: str, *, written_on: date) -> list[tuple[date, date]]:
    """何時格寫到的日子，一個一段 `(開始, 結束)`（排序、去重）：寫到日的開始＝結束；只寫到旬或月的是一段（「11 月初」＝11-01～11-10）。
    年月日、ISO、月日、月-日、年月（旬）、月＋旬都收；沒寫年份的照 `written_on` 推。"""
    text = text or ""
    found: set[tuple[date, date]] = set()
    spans: list[tuple[int, int]] = []

    def taken(m: re.Match) -> bool:
        return any(a <= m.start() < b for a, b in spans)

    for pattern in (_ISO, _YMD):
        for m in pattern.finditer(text):
            d = _safe(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if d is not None:
                found.add((d, d))
                spans.append(m.span())
    for pattern in (_MD, _M_D):
        for m in pattern.finditer(text):
            if taken(m):
                continue
            month, day = int(m.group(1)), int(m.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                d = _year_for(month, day, written_on)
                if d is not None:
                    found.add((d, d))
    for m in _YM.finditer(text):
        year, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            found.add(_part_span(year, month, m.group(3)))
            spans.append(m.span())
    for m in _MPART.finditer(text):
        month = int(m.group(1))
        if taken(m) or not 1 <= month <= 12:
            continue
        anchor = _year_for(month, 15, written_on)            # 用月中定年（窗只看月份），再換成那一旬
        if anchor is not None:
            found.add(_part_span(anchor.year, month, m.group(2)))
    return sorted(found)


def when_dates(text: str, *, written_on: date) -> list[date]:
    """何時格寫到的日子的最後一天（排序、去重）——「過了沒」比這一天。"""
    return sorted({end for _, end in when_spans(text, written_on=written_on)})


def _part_span(year: int, month: int, part: str | None) -> tuple[date, date]:
    """上旬／初＝1～10 日、中旬／中＝11～20 日、下旬／底＝21 日～月底、沒寫＝整個月。"""
    last = calendar.monthrange(year, month)[1]
    first, end = {"上旬": (1, 10), "初": (1, 10), "中旬": (11, 20), "中": (11, 20),
                  "下旬": (21, last), "底": (21, last)}.get(part or "", (1, last))
    return date(year, month, first), date(year, month, end)


def when_forms(text: str) -> list[str]:
    """何時格點名的 SEC 定期報告（`WHEN_FORMS`，照第一次出現的順序）。"""
    out: list[str] = []
    for m in _FORM_IN_TEXT.finditer(text or ""):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def placeholder_as_event(text: str) -> bool:
    """何時格有沒有把 `{next_checkpoint_date}` 寫成某件事的日子（「{next_checkpoint_date} 的第三季財報」）。"""
    return bool(_PLACEHOLDER_AS_EVENT.search(text or ""))


def _day(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def checkpoint_passed(text: str, *, written_on: date, today: date,
                      filings: Iterable[Mapping[str, Any]] = (),
                      calendar_checkpoints: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any] | None:
    """何時格的裁決點過了 → `{kind, since, …}`（`kind` ∈ `CHECKPOINT_KINDS`）；沒過（或段落裡找不到裁決點）→ None。

    `filings`：這家公司的一手申報 `{form, filed, lead_id}`（lead 池的 edgar 申報）。
    `calendar_checkpoints`：名冊上這一檔的檢核點 `{date, what}`（`thesis.lifecycle_schedule.checkpoints_by_ticker`，
    `{next_checkpoint_date}` 的來源之一）。幾種都過了，回最早過的那一件。"""
    found: list[dict[str, Any]] = []
    since = written_on.isoformat()
    # 開始那天嚴格晚於寫下那天才算在等：何時格常記「查到 2026-11-09」——寫下當天的日子多半是查過的那一刻；只寫到旬的，
    # 寫下時已在那一旬裡（MOD 11-07 寫「照前兩季 7 月底、11 月初的節奏」）講的是剛過的那一次。過了沒比那一段的最後一天
    ahead = sorted(end for start, end in when_spans(text, written_on=written_on) if start > written_on)
    if ahead and ahead[0] < today:
        found.append({"kind": "date", "since": since, "checkpoint": ahead[0].isoformat(), "at": ahead[0]})
    forms = set(when_forms(text))
    if forms:
        arrived = []
        for f in filings:
            base = str(f.get("form") or "").upper().split("/")[0]
            filed = _day(f.get("filed"))
            if base in forms and filed is not None and written_on < filed <= today:
                arrived.append((filed, base, str(f.get("lead_id") or "")))
        if arrived:
            filed, form, lead_id = min(arrived)
            found.append({"kind": "filing", "since": since, "form": form, "filed": filed.isoformat(),
                          "lead_id": lead_id or None, "at": filed})
    if placeholder_as_event(text):
        # 佔位字的值＝名冊上 ≥ 那一天的最早日子（`briefing.alpha_view.builder._brief_values`）——寫下那天它指的是這一件
        then = sorted((d, str(c.get("what") or "")) for c in calendar_checkpoints
                      if (d := _day(c.get("date"))) is not None and d >= written_on)
        if then and then[0][0] < today:
            found.append({"kind": "placeholder", "since": since, "checkpoint": then[0][0].isoformat(),
                          "what": then[0][1] or None, "at": then[0][0]})
    if not found:
        return None
    first = min(found, key=lambda x: x["at"])
    return {k: v for k, v in first.items() if k != "at"}


def checkpoint_reason(passed: Mapping[str, Any]) -> str:
    """候選列 `rewrite[]` 那一句：寫於哪天、哪個日子過了或哪份申報交了（L18：指得回 lead id 與名冊那一條）。"""
    head = f"{CHECKPOINT_PASSED_PREFIX}：何時格（{passed['since']} 寫）"
    if passed.get("kind") == "filing":
        lead = f"（{passed['lead_id']}）" if passed.get("lead_id") else ""
        return f"{head}點名的 {passed['form']} 已在 {passed['filed']} 交了{lead}——讀過再改這一格"
    if passed.get("kind") == "placeholder":
        what = f"「{passed['what']}」" if passed.get("what") else "那一件"
        return (f"{head}把 {PLACEHOLDER} 寫成某件事的日子，寫下那天它指名冊上 {passed['checkpoint']} 的{what}——已過，"
                f"佔位字現在指的是別的日子；改寫這一格")
    return f"{head}寫的 {passed['checkpoint']} 已過——改寫這一格"


def _when_text(brief: Any) -> str | None:
    slot = brief.slot("when") if hasattr(brief, "slot") else None
    return slot.text if slot is not None else None


def when_text_since(records: Sequence[Any], brief: Any) -> datetime:
    """何時格這段文字最早出現的那一版的寫入時刻：沿 supersedes 往回走，只要上一版沒撤回、何時格一字不差就沿用。"""
    by_id = {r.brief_id: r for r in records}
    text = _when_text(brief)
    origin, cur, seen = brief, brief, {brief.brief_id}
    while cur.supersedes_id and cur.supersedes_id in by_id and cur.supersedes_id not in seen:
        prev = by_id[cur.supersedes_id]
        seen.add(prev.brief_id)
        if prev.retracted or _when_text(prev) != text:
            break
        origin = cur = prev
    return origin.created_at


__all__ = ["CHECKPOINT_KINDS", "CHECKPOINT_PASSED_PREFIX", "PLACEHOLDER", "WHEN_FORMS", "YEARLESS_BACK_DAYS",
           "checkpoint_passed", "checkpoint_reason", "placeholder_as_event", "when_dates", "when_forms",
           "when_spans", "when_text_since"]
