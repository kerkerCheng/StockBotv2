"""事件的相對反應（個股頁 S3e，2026-10-14；B5「相對同組的 1／5／20 日反應」）——**純函式**。取數住 `alpha/providers/event_reaction.py`。

**事件是什麼（使用者 2026-10-14 選 A）：研究自己說過「會改變信心」的事**——這家公司名下已經醒過的等待裡的三種：研究定的日子
到了、條件**判定觸及**（用叫醒它那則新聞的發布日）、公司自己的申報到了；＋thesis 已過的檢核點（只收日期確定的）。
AI 標旗還沒判定、判定沒觸及的不算（照數寫出來）——取數那一層有實測。不收「每一則新聞」：那會每天都亮（L14-4），也近似使用者
10-05 說的「股價＋事件看不出什麼」。

**反應怎麼算（plan S3e：事件日之後第一個收盤起算）**：基準＝事件日之前最後一個收盤（事件公開前的價）；第 n 日＝從事件日當天起
本檔第 n 個交易日的收盤；都用調整後收盤（分割與配息調整過）。相對同組＝本檔報酬 − 組員平均報酬——每個組員取「事件日之前最後一個
收盤」與「本檔第 n 日那天以前最後一個收盤」（交易日曆不同的市場照樣比得到；本檔不在自己的基準裡）；組員過半有這兩個收盤才算，
否則具名缺席。還沒滿 n 個交易日＝那一格寫「還沒滿」——是會自己補上的等待，不是缺資料。
⚠ 已知限制：事件日只到「日」——收盤後才公開的事件，反應會落在第 2 日（多數事件來源只有日期，不猜盤中時刻）。

不排序公司、不打分、不給燈號——只照實印每件事之後跟組比漲跌多少（相對水位一旦拿來排序就變成訊號，AGENTS「訊號的地位」）。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence

WINDOWS: tuple[int, ...] = (1, 5, 20)
#: 事件來源（封閉字彙）→ 頁面上那個字：研究定的日子到了、條件判定觸及、公司自己的申報到了、thesis 檢核點。
EVENT_KINDS: Mapping[str, str] = {"date": "研究等的日子", "touched": "判定觸及", "filing": "公司申報", "checkpoint": "檢核點"}
#: 事件日從哪裡來（封閉字彙）：新聞或申報的發布日、研究定的日子（事件本身可能早幾天）、系統發現它醒的那天（往晚估）、檢核點的確定日期。
DATE_BASES: tuple[str, ...] = ("lead_published_at", "watch_date", "woken_at", "checkpoint_date")
SHOWN = 8


def _clean(bars: Sequence[Any]) -> list[tuple[date, float]]:
    out = []
    for item in bars or ():
        d, v = item[0], item[1]
        if v is None:
            continue
        out.append((d if isinstance(d, date) else date.fromisoformat(str(d)[:10]), float(v)))
    return sorted(out)


def _last_before(bars: Sequence[tuple[date, float]], day: date, *, inclusive: bool) -> tuple[date, float] | None:
    hit = None
    for d, v in bars:
        if d < day or (inclusive and d == day):
            hit = (d, v)
        else:
            break
    return hit


def window_reaction(own_bars: Sequence[Any], member_bars: Mapping[str, Sequence[Any]], event_date: date, *,
                    windows: Sequence[int] = WINDOWS) -> dict[str, Any]:
    """一件事、一組：`{base_date, base_close, windows: [...]}`。每個 window 是
    `{n, end_date, own, cohort_mean, relative, members_used, members_total}`，或 `{n, pending}`（還沒滿 n 個交易日），
    或 `{n, absence}`（組員不足一半有兩個收盤）。本檔沒有事件日之前的收盤＝整件缺席。"""
    own = _clean(own_bars)
    base = _last_before(own, event_date, inclusive=False)
    if base is None:
        return {"base_date": None, "base_close": None, "windows": [],
                "absence": "事件日之前沒有這家的收盤（日線從事件之後才開始，或沒有日線）"}
    after = [(d, v) for d, v in own if d >= event_date]
    members = {t: _clean(b) for t, b in (member_bars or {}).items()}
    out: list[dict[str, Any]] = []
    for n in windows:
        if len(after) < n:
            out.append({"n": n, "pending": f"還沒滿 {n} 個交易日（事件之後才 {len(after)} 個）"})
            continue
        end_date, end_close = after[n - 1]
        own_return = end_close / base[1] - 1.0
        rets: dict[str, float] = {}
        for ticker, bars in members.items():
            m_base = _last_before(bars, event_date, inclusive=False)
            m_end = _last_before(bars, end_date, inclusive=True)
            if m_base is None or m_end is None or m_end[0] <= m_base[0] or m_base[1] == 0:
                continue
            rets[ticker] = m_end[1] / m_base[1] - 1.0
        if not members or len(rets) * 2 < len(members):
            out.append({"n": n, "end_date": end_date.isoformat(), "own": round(own_return, 4),
                        "absence": f"組員有這段收盤的 {len(rets)}／{len(members)}，不足一半"})
            continue
        mean = sum(rets.values()) / len(rets)
        out.append({"n": n, "end_date": end_date.isoformat(), "own": round(own_return, 4), "cohort_mean": round(mean, 4),
                    "relative": round(own_return - mean, 4), "members_used": len(rets), "members_total": len(members)})
    return {"base_date": base[0].isoformat(), "base_close": base[1], "windows": out, "absence": None}


def dedupe(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """同一件事（同一個 key：同一則新聞叫醒兩個 watch、同一個檢核點）只留一件，記下幾個等待指到它。新的在前。"""
    by_key: dict[str, dict[str, Any]] = {}
    for event in events:
        key = str(event["key"])
        if key in by_key:
            by_key[key]["sources"] = sorted(set(by_key[key]["sources"]) | set(event.get("sources") or ()))
            continue
        by_key[key] = {**event, "sources": sorted(set(event.get("sources") or ()))}
    return sorted(by_key.values(), key=lambda e: (str(e["date"]), str(e["key"])), reverse=True)


def page_reactions(events: Sequence[Mapping[str, Any]], *, adjusted_bars: Sequence[Any], raw_bars: Sequence[Any],
                   cohorts: Sequence[Mapping[str, Any]] | None, cohort_absence: Mapping[str, Any] | None,
                   quote_unit: str | None, shown: int = SHOWN) -> dict[str, Any]:
    """一頁的 B5「相對同組的反應」：每件事（新的在前、最多 `shown` 件）一列——日期、哪一種、說什麼、當時的收盤（原始價、
    報價單位）、每一組的 1／5／20 日相對報酬。`cohorts`＝本檔所屬每一組的 `{cohort: {record_id, theme}, member_bars}`；
    不在任何組＝`cohort_absence`（事件照列，反應那一格具名缺席）。"""
    items = dedupe(events)
    if not items:
        return {"events": [], "total": 0, "absence": {
            "kind": "not_yet_recorded",
            "reason": "這一檔名下還沒有算得上事件的：研究定的日子沒到、沒有判定觸及的條件或公司申報、也沒有已過的確定檢核點"}}
    raw = _clean(raw_bars)
    out = []
    for event in items[:shown]:
        day = date.fromisoformat(str(event["date"])[:10])
        reactions = []
        for ctx in cohorts or ():
            cohort = ctx.get("cohort") or {}
            reactions.append({"cohort_id": cohort.get("record_id"), "theme": cohort.get("theme"),
                              **window_reaction(adjusted_bars, ctx.get("member_bars") or {}, day)})
        price = _last_before(raw, day, inclusive=False)
        out.append({**event, "kind_label": EVENT_KINDS.get(str(event.get("kind")), str(event.get("kind"))),
                    "price_before": ({"date": price[0].isoformat(), "close": price[1], "unit": quote_unit} if price else None),
                    "reactions": reactions,
                    "reaction_absence": (dict(cohort_absence) if not cohorts and cohort_absence else None)})
    return {"events": out, "total": len(items), "absence": None}


__all__ = ["DATE_BASES", "EVENT_KINDS", "SHOWN", "WINDOWS", "dedupe", "page_reactions", "window_reaction"]
