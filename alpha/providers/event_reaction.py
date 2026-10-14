"""事件的相對反應的取數（個股頁 S3e，2026-10-14）：交給 `alpha.event_reaction` 算。

- **事件**（使用者選 A）：這家公司名下已經醒過的等待（Event Watch registry；歸屬規則與候選板、敘事寫入端同一支
  `engine_b.narrative_watches.attributed_watches`，L16），只收三種：**日期到了**（研究定的那一天）、**條件判定觸及**（用叫醒它
  那則新聞的發布日）、**公司自己的申報到了**（用申報日）；＋thesis 已過的檢核點（頁上 research 面板照抄的那幾個），**只收日期
  確定的**——估計日期差一兩天就會把反應算到別的事件上。
  ⚠ **AI 層標旗、還沒判定的不算**：標旗只標不判（AGENTS「等待與心跳」），2026-10-14 實測 19 個標旗裡 7 個已判定「沒觸及」——
  例如一則穩懋的法說會公告叫醒六家公司的同一個條件；當成事件會讓六頁都長出一件跟自己無關的事。判定沒觸及的、其他醒法的同樣
  照數寫出來、不算（INV-3：不靜默丟）。
- **時點（INV-6）**：as-of T 只看 T 以前**系統已經知道醒了**的等待、T 以前的事件日、T 以前的日線。
- **日線**：Engine C `price_series`（調整後算報酬、原始價印「當時」）；組員的日線與三題同一支（`cohort_contexts`）。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence

from alpha.event_reaction import page_reactions


def ew_semantic_kind() -> str:
    from engine_b import event_watch as ew

    return str(ew.SEMANTIC_KIND)


def _lead_event(lead: Mapping[str, Any] | None, woken: Mapping[str, Any], *, fallback_key: str, seen: str,
                label: Any, kind: str) -> dict[str, Any]:
    """叫醒它的那則新聞（有發布日就用發布日，否則用系統發現它醒的那天、往晚估）。"""
    if lead is not None and lead.get("published_at"):
        return {"key": f"lead:{woken['lead_id']}", "kind": kind, "date": str(lead["published_at"])[:10],
                "date_basis": "lead_published_at",
                "label": " ".join(str(label or lead.get("title") or "").split())[:140], "url": lead.get("url"),
                "lead_title": " ".join(str(lead.get("title") or "").split())[:140]}
    return {"key": fallback_key, "kind": kind, "date": seen, "date_basis": "woken_at",
            "label": " ".join(str(label or "").split())[:140], "url": None}


def company_events(company_id: str, ticker: str, *, as_of: date, watches: Sequence[Mapping[str, Any]],
                   leads: Mapping[str, Mapping[str, Any]], brief_records: Sequence[Any], lifecycle: Mapping[str, Any] | None,
                   checkpoints: Sequence[Mapping[str, Any]] | None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """這一檔的事件（還沒去重）與不算的計數：`after_as_of`（T 以後才醒或事件日在 T 以後，回看時不算）、
    `flagged_unjudged`（AI 標旗、還沒判定）、`judged_not_touched`（判定沒觸及）、`other_wakes`（其他醒法）、
    `estimated_checkpoints`（已過、但只有估計日期的檢核點）。"""
    from engine_b.narrative_watches import attributed_watches

    current = next((r for r in reversed(list(brief_records)) if not r.retracted), None)
    mine = attributed_watches(company_id, ticker, watches=watches, lifecycle=lifecycle,
                              brief_ids=[r.brief_id for r in brief_records], current_brief=current)
    cutoff = as_of.isoformat()
    events: list[dict[str, Any]] = []
    counts = {"after_as_of": 0, "flagged_unjudged": 0, "judged_not_touched": 0, "other_wakes": 0,
              "estimated_checkpoints": 0}
    for watch in mine:
        woken = watch.get("woken_by") or {}
        if not woken:
            continue
        seen = str(woken.get("at") or "")[:10]
        watch_id = str(watch.get("watch_id"))
        lead = leads.get(str(woken.get("lead_id"))) if woken.get("lead_id") else None
        verdicts = [str(j.get("touches") or "") for j in watch.get("judgments") or () if isinstance(j, Mapping)]
        if str(woken.get("kind")) == "date" and watch.get("until"):
            event = {"key": f"watch:{watch_id}", "kind": "date", "date": str(watch["until"])[:10], "date_basis": "watch_date",
                     "label": " ".join(str(watch.get("note") or watch.get("condition") or "研究等的日子").split())[:140],
                     "url": None}
        elif str(watch.get("kind")) == ew_semantic_kind():
            if "yes" not in verdicts:
                counts["judged_not_touched" if verdicts and all(v == "no" for v in verdicts) else "flagged_unjudged"] += 1
                continue
            event = _lead_event(lead, woken, fallback_key=f"watch:{watch_id}", seen=seen,
                                label=watch.get("condition"), kind="touched")
        elif str(watch.get("kind")) == "entity_filing_signal" and lead is not None:
            event = _lead_event(lead, woken, fallback_key=f"watch:{watch_id}", seen=seen, label=None, kind="filing")
        else:
            counts["other_wakes"] += 1
            continue
        if not event["date"] or not seen or seen > cutoff or event["date"] > cutoff:
            counts["after_as_of"] += 1
            continue
        events.append({**event, "sources": [watch_id]})
    for checkpoint in checkpoints or ():
        day = str(checkpoint.get("date") or "")[:10]
        if not day or day > cutoff:
            continue
        if str(checkpoint.get("date_confidence")) != "confirmed":
            counts["estimated_checkpoints"] += 1
            continue
        what = " ".join(str(checkpoint.get("what") or "").split())
        events.append({"key": f"checkpoint:{day}:{what[:40]}", "kind": "checkpoint", "date": day,
                       "date_basis": "checkpoint_date", "label": what[:140], "url": None,
                       "sources": [str(checkpoint.get("source") or "thesis")]})
    return events, counts


def _price_inputs(conn: Any, ticker: str, company_id: str | None, *, as_of: date
                  ) -> tuple[list[tuple[date, float | None]], list[tuple[date, float | None]], str | None]:
    from engine_c.history import price_series
    from identity.registry import get_registry

    bars = price_series(conn, ticker, as_of=as_of)
    company = get_registry().company(company_id) if company_id else None
    unit = getattr(company, "market_quote_unit", None)
    return ([(date.fromisoformat(str(b["bar_date"])[:10]), b["close_adjusted"]) for b in bars],
            [(date.fromisoformat(str(b["bar_date"])[:10]), b["close_raw"]) for b in bars],
            str(unit) if unit else None)


def page_event_reaction(ticker: str, company_id: str | None, *, as_of: date, context: Mapping[str, Any],
                        brief_records: Sequence[Any], checkpoints: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    """一頁的 B5「相對同組的反應」。`context`＝一輪載一次的 `{watches, leads, lifecycle}`。"""
    from .three_questions import _conn_for, cohort_contexts

    events, counts = company_events(str(company_id or ""), ticker, as_of=as_of, watches=context.get("watches") or (),
                                    leads=context.get("leads") or {}, brief_records=brief_records,
                                    lifecycle=context.get("lifecycle"), checkpoints=checkpoints)
    if not events:
        out = page_reactions([], adjusted_bars=(), raw_bars=(), cohorts=None, cohort_absence=None, quote_unit=None)
        return {**out, "counts": counts}
    adjusted, raw, unit = _price_inputs(_conn_for("ro"), ticker, company_id, as_of=as_of)
    cohorts, absence, _errors = cohort_contexts(ticker, today=as_of)
    out = page_reactions(events, adjusted_bars=adjusted, raw_bars=raw, cohorts=cohorts,
                         cohort_absence=({"kind": absence.get("absence_kind"), "reason": absence.get("reason")}
                                         if absence else None), quote_unit=unit)
    return {**out, "counts": counts}


__all__ = ["company_events", "page_event_reaction"]
