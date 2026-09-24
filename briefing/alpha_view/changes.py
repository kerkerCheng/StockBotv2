"""變更偵測（I/O）：把各 authority 的**時序**讀成 `ChangeEvent`，交給 `alpha.refresh` 判 impact。

這一支只做「什麼變了」，**不判影響誰**——impact 的單一 authority 是 `alpha.refresh.resolve_refresh`。
它也**不做 digest diff**：每個事件都指得出 class、authority、物件、時間、欄位。

| class | 來源時序 | 「判斷當時知不知道」用哪個時間 |
|---|---|---|
| market_price／consensus | Engine C `financial_snapshots`（逐日）＋`consensus_estimates`（逐次抓取） | `fetched_at`（session 只看得到 packet 快照） |
| graph_edge | `GraphResearchProvider.get_structural_changes_since`（投影差集） | 文件 `published_at`（世界時間） |
| financial_actual／company_guidance | Engine C 人工 ledger 歷史列 | payload 的 `source_filed_at`／`issued_at`（世界時間；系統 `recorded_at` 只管 as-of 可見性） |
| operating_assumption | private ledger `created_at` | `created_at`（⚠ 2026-09-23：估值／horizon／entry 三本 ledger 的事件隨估值鏈退役） |
| thesis_review_due | `thesis/lifecycle.json` 的 `is_due` | 到期日 |
| disproof_signal | Event Watch 已 fired 且 `hypothesis_ref` 指向 `oa_*`／`signal:<TICKER>` | `woken_by.at` |

**同一身分、不同值才算變化。** 「第一次出現」（例：consensus_estimates 表在判斷後才建）是我們的
資料覆蓋變了，不是世界變了——記 note，不發事件（同 `documents` 不參與排序的理由）。
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from alpha.refresh import (
    COMPANY_GUIDANCE, CONSENSUS, CONSENSUS_NOISE_FLOOR_REL, DISPROOF_SIGNAL, FINANCIAL_ACTUAL,
    GRAPH_EDGE, MARKET_PRICE, OPERATING_ASSUMPTION, THESIS_ARTIFACT_ID, THESIS_REVIEW_DUE,
    ChangeEvent, MetricObservation, end_of_day, start_of_day,
)

_ROOT = Path(__file__).resolve().parents[2]
WATCHES_PATH = _ROOT / "library" / "leads" / "event_watches.json"

A_SNAP = "engine_c://financial_snapshots"
A_CONS_FY = "engine_c://consensus_estimates"
A_LEDGER = "engine_c://manual_observations"
A_GRAPH = "engine_a://graph_research_provider"
A_ASSUMPTIONS = "alpha://fundamental/assumptions"
# ⚠ 2026-09-23（Phase 0 Step 0b.1b）：A_VALUATION_ASSUMPTIONS／A_HORIZON_ASSUMPTIONS（C／H 組）與
# A_ENTRY_CRITERIA（F 組）隨三本 ledger 的變更事件退役。
A_LIFECYCLE = "thesis://lifecycle.json"
A_WATCH = "engine_b://event_watch"


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _d(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rel_change(old: float | None, new: float | None) -> float | None:
    if old is None or new is None or old == 0:
        return None
    return abs(new / old - 1.0)


# ---------------------------------------------------------------------------
# 各來源
# ---------------------------------------------------------------------------

def single_analyst_view(count: Any, low: Any, high: Any) -> str | None:
    """**「一個人的看法不是共識」**——是的話回理由，不是回 None（2026-09-19，七缺陷之 2）。

    這個判準系統裡早就有，只是沒機械化：POET 的 Abstention `ab_42838d2eec25b735` 逐字寫著
    「**僅 1 位分析師，high＝low，區間寬度為零——那不是共識，是一個人的看法**」，
    而 packet 的 `valuation_market_implied.method` 也已對 rollover fail closed。
    **同一個問題，估值層 fail closed、refresh 層照報**（L12 一表兩義；L16 分類沒跟著資料走）。

    事發（2026-09-19）：LITE 的 +1y（FY2028）由 33.3012 → 39.70（+19.2%），**同時 `analyst_count`
    由 22 崩到 1、`low`＝`high`＝39.70**；而 thesis 真正校準的 FY2027 只動了 +0.13%。
    **base 完全沒有被推翻，訊號卻說它需要重做。**

    實測 16 檔有 2 檔命中（LITE +1y、POET 兩年都是）＝12.5%——**有鑑別力、不恆亮**（L14-4）。
    """
    number = _num(count)
    if number is not None and number <= 1:
        return f"僅 {number:.0f} 位分析師"
    lo, hi = _num(low), _num(high)
    if lo is not None and hi is not None and lo == hi:
        return "估計區間寬度為零（high＝low）"
    return None


def market_and_consensus_changes(
    rows: Sequence[Mapping[str, Any]], *, ticker: str, company_id: str | None, since: datetime,
    forward_coverage: Any = None,
) -> tuple[list[ChangeEvent], list[str]]:
    """逐日快照：價格變 → market_price；forward EPS（price/pe_forward）或目標價變 → consensus。

    ⚠ `forward_eps_from(price, pe_forward)` 推出來的是 **+1y**，而實測 15/15 有假設的檔
    **base 全部校準在 0y**——所以每次 forward year rollover（每年必然發生一次），每一檔都會
    收到一個**與自己 base 無關的年度**觸發的複查要求。`forward_coverage` 傳入那個年度的共識
    覆蓋，覆蓋崩塌時這個代理量**不發事件、改發 note**：它量到的是覆蓋變了，不是共識變了。
    """
    from engine_c.estimates import forward_eps_from

    events: list[ChangeEvent] = []
    notes: list[str] = []
    coverage_reason = (
        single_analyst_view(getattr(forward_coverage, "analyst_count", None),
                            getattr(forward_coverage, "low", None),
                            getattr(forward_coverage, "high", None))
        if forward_coverage is not None else None
    )
    ref = f"engine_c://financial_snapshot/{ticker}"
    prev: Mapping[str, Any] | None = None
    for row in rows:
        observed = _dt(row.get("fetched_at")) or end_of_day(_d(row.get("snapshot_date")) or _d(row.get("bar_date")) or since.date())
        bar = _d(row.get("bar_date"))
        if prev is not None and observed > since:
            old_price, new_price = _num(prev.get("price")), _num(row.get("price"))
            if old_price is not None and new_price is not None and old_price != new_price:
                events.append(ChangeEvent(
                    change_type=MARKET_PRICE, ticker=ticker, company_id=company_id, authority=A_SNAP,
                    changed_ref=ref, observed_at=observed, effective_at=bar,
                    old_version=f"{old_price:g}", new_version=f"{new_price:g}", material_fields=("price",),
                    detail=f"price {old_price:g} → {new_price:g}（bar {bar}）"))
            old_eps = forward_eps_from(prev.get("price"), prev.get("pe_forward"))
            new_eps = forward_eps_from(row.get("price"), row.get("pe_forward"))
            rel = _rel_change(old_eps, new_eps)
            if rel is not None and rel >= CONSENSUS_NOISE_FLOOR_REL:
                if coverage_reason is not None:
                    # 覆蓋崩塌：量到的是「誰還在看」變了，不是「他們怎麼看」變了。
                    # 比照本檔既有的「首次出現＝資料覆蓋變了，不是共識變了——不發事件」。
                    notes.append(
                        f"forward EPS（price/pe_forward，**+1y**）{old_eps:.4g} → {new_eps:.4g}（{rel:+.1%}）"
                        f"**未發事件**：該年度{coverage_reason}——那不是共識，是一個人的看法。"
                        "⚠ base 假設校準在 0y，這個代理量是 +1y 的，兩者本來就不是同一年")
                else:
                    events.append(ChangeEvent(
                        change_type=CONSENSUS, ticker=ticker, company_id=company_id, authority=A_SNAP,
                        changed_ref=ref, observed_at=observed, effective_at=bar,
                        old_version=f"{old_eps:.4g}", new_version=f"{new_eps:.4g}",
                        material_fields=("forward_eps",),
                        fiscal_relative_label="+1y",      # `pe_forward` 對應的就是 forward year
                        detail=(f"forward EPS（price/pe_forward，**+1y** 代理量）{old_eps:.4g} → "
                                f"{new_eps:.4g}（{rel:+.1%}）")))
            old_t, new_t = _num(prev.get("analyst_target_mean")), _num(row.get("analyst_target_mean"))
            rel_t = _rel_change(old_t, new_t)
            if rel_t is not None and rel_t >= CONSENSUS_NOISE_FLOOR_REL:
                events.append(ChangeEvent(
                    change_type=CONSENSUS, ticker=ticker, company_id=company_id, authority=A_SNAP,
                    changed_ref=ref, observed_at=observed, effective_at=bar,
                    old_version=f"{old_t:g}", new_version=f"{new_t:g}", material_fields=("target_mean",),
                    detail=f"分析師目標均價 {old_t:g} → {new_t:g}"))
        prev = row
    if not rows:
        notes.append("Engine C 沒有這段期間的快照序列——行情／共識變化無法偵測")
    return events, notes


def fiscal_consensus_changes(
    old: Sequence[Any], new: Sequence[Any], *, ticker: str, company_id: str | None, since: datetime,
) -> tuple[list[ChangeEvent], list[str]]:
    """會計年度別共識：同 (metric, period) 值變了才是變化；第一次出現只記 note。"""
    events: list[ChangeEvent] = []
    notes: list[str] = []
    before = {(c.metric, c.period.end): c for c in old}
    for item in new:
        key = (item.metric, item.period.end)
        observed = _dt(item.fetched_at) or end_of_day(item.captured_at or since.date())
        prior = before.get(key)
        if prior is None:
            if observed > since:
                notes.append(f"FY 別共識 {item.metric} {item.period.label} 於 {observed.date()} 首次出現"
                             "（資料覆蓋變了，不是共識變了——不發事件）")
            continue
        rel = _rel_change(prior.value, item.value)
        if rel is not None and rel >= CONSENSUS_NOISE_FLOOR_REL and observed > since:
            coverage_reason = single_analyst_view(item.analyst_count, item.low, item.high)
            if coverage_reason is not None:
                notes.append(
                    f"{item.period.label} {item.metric} 共識 {prior.value:.6g} → {item.value:.6g}"
                    f"（{rel:+.1%}）**未發事件**：{coverage_reason}"
                    f"（覆蓋 {prior.analyst_count} → {item.analyst_count} 人）"
                    "——那不是共識，是一個人的看法")
                continue
            events.append(ChangeEvent(
                change_type=CONSENSUS, ticker=ticker, company_id=company_id, authority=A_CONS_FY,
                changed_ref=item.refs[0] if item.refs else f"engine_c://consensus_estimate/{ticker}/{item.metric}/{item.period.end}",
                observed_at=observed, effective_at=item.captured_at,
                old_version=f"{prior.value:.6g}", new_version=f"{item.value:.6g}", material_fields=(item.metric,),
                fiscal_relative_label=item.relative_label,
                detail=(f"{item.period.label}（{item.relative_label or '年度未標'}）{item.metric} 共識 "
                        f"{prior.value:.6g} → {item.value:.6g}（{rel:+.1%}；覆蓋 "
                        f"{prior.analyst_count} → {item.analyst_count} 人）")))
    return events, notes


def structural_changes(
    events_in: Sequence[Any], *, ticker: str, company_id: str | None,
) -> list[ChangeEvent]:
    out: list[ChangeEvent] = []
    for event in events_in:
        refs = [r.ref for r in event.evidence]
        edge = next((r for r in event.evidence if r.kind == "graph_edge"), None)
        out.append(ChangeEvent(
            change_type=GRAPH_EDGE, ticker=ticker, company_id=company_id, authority=A_GRAPH,
            changed_ref=(edge.ref if edge else (refs[0] if refs else str(event.subject_id))),
            observed_at=end_of_day(event.observed_at), effective_at=event.observed_at,
            published_at=event.observed_at,
            material_fields=(event.kind, event.direction), detail=event.description,
            related_refs=tuple(r for r in refs if not edge or r != edge.ref)))
    return out


def ledger_changes(
    rows: Sequence[Mapping[str, Any]], *, field_name: str, ticker: str, company_id: str | None,
    since: datetime,
) -> list[ChangeEvent]:
    """人工 ledger 歷史列 → financial_actual／company_guidance。`published_at`＝一手文件日。"""
    change_type = FINANCIAL_ACTUAL if field_name == "fiscal_year_results" else COMPANY_GUIDANCE
    out: list[ChangeEvent] = []
    for row in rows:
        recorded = _dt(row.get("recorded_at")) or end_of_day(row.get("as_of") or since.date())
        payload = row.get("payload") or {}
        published = _d(payload.get("source_filed_at") or payload.get("issued_at")) or _d(row.get("as_of"))
        known = end_of_day(published) if published else recorded
        if known <= since and recorded <= since:
            continue
        numeric = tuple(sorted(k for k, v in payload.items()
                               if isinstance(v, (int, float)) and not isinstance(v, bool)))
        if change_type == FINANCIAL_ACTUAL:
            period = _d(payload.get("fiscal_year_end")) or _d(row.get("as_of"))
            fields = ("revenue", "segment_revenue", "gaap", "non_gaap", "exit_quarter")
            detail = f"會計年度實際值（至 {period}）"
        else:
            period = _d(payload.get("period_end"))
            fields = numeric
            detail = f"公司指引 {payload.get('period_label') or '?'}（{payload.get('period_kind') or '?'}，發布 {published}）"
        out.append(ChangeEvent(
            change_type=change_type, ticker=ticker, company_id=company_id, authority=A_LEDGER,
            changed_ref=f"engine_c://manual_observation/{row['observation_id']}",
            observed_at=recorded, effective_at=period, published_at=published,
            new_version=str(row["observation_id"]), material_fields=tuple(fields), detail=detail,
            related_refs=((f"engine_c://manual_observation/{row['supersedes_id']}",) if row.get("supersedes_id") else ())))
    return out


def assumption_changes(
    records: Sequence[Any], *, ticker: str, company_id: str | None, since: datetime,
    change_type: str = OPERATING_ASSUMPTION, authority: str = A_ASSUMPTIONS,
) -> list[ChangeEvent]:
    """ledger 新紀錄：新建／取代／撤回都是「內部觀點變了」。2026-09-23 起只剩營運假設一本。"""
    def _value_text(value: Any) -> str:
        return value.isoformat() if isinstance(value, date) else f"{value:g}"

    ordered = sorted(records, key=lambda r: (r.created_at, r.assumption_id))
    # V0（2026-09-15）：scenario 進 key。variant 是 base 的 overlay，不是 base 的下一版——
    # 少了這一格，一條新寫的 variant 會被當成「取代」同 key 的 base 假設，把 base 的成果誤標 superseded。
    latest_before: dict[tuple[str, str, str, date], str] = {}
    out: list[ChangeEvent] = []
    for record in ordered:
        scenario = str(getattr(record, "scenario", "base") or "base")
        key = (scenario, record.driver, record.scope, record.period.end)
        predecessor = record.supersedes_id or latest_before.get(key)
        if record.created_at > since:
            kind = "撤回" if record.retracted else ("取代" if predecessor else "新增")
            tag = "" if scenario == "base" else f"〔{scenario}〕"
            out.append(ChangeEvent(
                change_type=change_type, ticker=ticker, company_id=company_id, authority=authority,
                changed_ref=record.assumption_id, observed_at=record.created_at,
                effective_at=record.period.end, new_version=_value_text(record.value),
                old_version=None, material_fields=(record.driver, record.scope),
                detail=f"{kind}假設{tag} {record.driver}[{record.scope}] {record.period.label} = {_value_text(record.value)}（{record.basis}）",
                related_refs=((predecessor,) if predecessor else ())))
        latest_before[key] = record.assumption_id
    return out


# ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`criterion_changes`（entry criterion ledger 的變更事件，F 組）退役。


def lifecycle_due_changes(
    entry: Mapping[str, Any] | None, *, ticker: str, company_id: str | None, today: date,
) -> list[ChangeEvent]:
    if not entry:
        return []
    from thesis.lifecycle_schedule import effective_next_check, is_due

    due, reason = is_due(entry, today=today)
    if not due:
        return []
    when, source, _cp = effective_next_check(entry, today=today)
    return [ChangeEvent(
        change_type=THESIS_REVIEW_DUE, ticker=ticker, company_id=company_id, authority=A_LIFECYCLE,
        changed_ref=f"thesis://lifecycle/{entry.get('ticker') or ticker}",
        observed_at=end_of_day(when or today), effective_at=when,
        material_fields=(source or "unscheduled",), detail=f"thesis lifecycle 到期：{reason}",
        target_artifact=THESIS_ARTIFACT_ID)]


def watch_changes(
    watches: Sequence[Mapping[str, Any]], *, ticker: str, company_id: str | None,
    assumption_ids: Sequence[str],
) -> list[ChangeEvent]:
    """已 fired 的 Event Watch，`hypothesis_ref` 指向假設 id（`oa_*`；`va_*`／`ha_*` 的 ledger 已於 2026-09-23 退役）或 `signal:<TICKER>` → disproof_signal。
    一般 `hy_*` 假設層 watch 不在此列（那是 what-if overlay 的事）。"""
    out: list[ChangeEvent] = []
    wanted = {ticker.upper(), str(company_id or "").lower()}
    known = set(assumption_ids)
    for watch in watches:
        if watch.get("status") not in ("fired", "consumed"):
            continue
        # ⚠ 語意條件 watch（Phase 1 Step 1.4，`disproof_ref`）刻意不在這裡轉成 disproof_signal：
        # 它醒來只是「待檢」，觸及與否在互動 session 判定；本 Phase 不動個股頁（結案 gate 3）。
        # 它的家是 APP 的 watches 頁與 `event_watch semantic-queue`。
        if watch.get("disproof_ref"):
            continue
        target = str(watch.get("hypothesis_ref") or "")
        entities = {str(e).upper() for e in (watch.get("entities") or ())} | {str(e).lower() for e in (watch.get("entities") or ())}
        if not (entities & wanted):
            continue
        if (target.startswith("oa_") or target.startswith("va_") or target.startswith("ha_")) and target in known:
            artifact = target
        elif target.lower() == f"signal:{ticker.lower()}":
            artifact = THESIS_ARTIFACT_ID
        else:
            continue
        woken = watch.get("woken_by") or {}
        out.append(ChangeEvent(
            change_type=DISPROOF_SIGNAL, ticker=ticker, company_id=company_id, authority=A_WATCH,
            changed_ref=f"library://event_watches/{watch.get('watch_id')}",
            observed_at=_dt(woken.get("at")) or _dt(watch.get("created_at")) or datetime.now(timezone.utc),
            material_fields=(str(watch.get("kind") or ""),),
            detail=f"Event Watch {watch.get('watch_id')} 喚醒：{watch.get('fact') or watch.get('note') or ''}",
            target_artifact=artifact, on_trigger="review_required",
            related_refs=((str(woken.get("lead_id")),) if woken.get("lead_id") else ())))
    return out


def metric_observations(rows: Sequence[Mapping[str, Any]]) -> list[MetricObservation]:
    """把 `fiscal_year_results` 的歷史列攤平成可對照 `ReviewCondition` 的觀測（年度＋exit quarter）。"""
    out: list[MetricObservation] = []
    for row in rows:
        payload = row.get("payload") or {}
        observed = _dt(row.get("recorded_at")) or end_of_day(row.get("as_of") or date.today())
        ref = f"engine_c://manual_observation/{row['observation_id']}"
        fy_end = _d(payload.get("fiscal_year_end")) or _d(row.get("as_of"))
        if fy_end is not None:
            if _num(payload.get("revenue")) is not None:
                out.append(MetricObservation("revenue", "total", fy_end, "fiscal_year", float(payload["revenue"]), ref, observed))
            for name, value in (payload.get("segment_revenue") or {}).items():
                if _num(value) is not None:
                    out.append(MetricObservation("segment_revenue", str(name), fy_end, "fiscal_year", float(value), ref, observed))
        exit_q = payload.get("exit_quarter") or {}
        q_end = _d(exit_q.get("period_end"))
        if q_end is not None:
            if _num(exit_q.get("revenue")) is not None:
                out.append(MetricObservation("revenue", "total", q_end, "fiscal_quarter", float(exit_q["revenue"]), ref, observed))
            for name, value in (exit_q.get("segment_revenue") or {}).items():
                if _num(value) is not None:
                    out.append(MetricObservation("segment_revenue", str(name), q_end, "fiscal_quarter", float(value), ref, observed))
    return out


def load_watches(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or WATCHES_PATH
    if not target.is_file():
        return []
    try:
        return list(json.loads(target.read_text(encoding="utf-8")).get("watches") or [])
    except (OSError, ValueError):
        return []


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def detect_changes(
    *,
    ticker: str,
    company_id: str | None,
    since: datetime,
    today: date,
    as_of: date | None,
    fundamentals_provider: Any,
    graph_provider: Any,
    assumption_records: Sequence[Any],
    lifecycle_entry: Mapping[str, Any] | None,
    watches: Sequence[Mapping[str, Any]],
    ticker_obj: Any = None,
) -> tuple[list[ChangeEvent], list[MetricObservation], list[str]]:
    """把 `since` 之後各 authority 的變化收成一份 `ChangeEvent` 清單（每段各自 fail-soft，原因進 notes）。"""
    events: list[ChangeEvent] = []
    notes: list[str] = []
    observations: list[MetricObservation] = []
    t = ticker_obj if ticker_obj is not None else ticker
    window_start = since.date() - timedelta(days=10)      # 多抓幾天讓第一筆有前一筆可比

    # ⚠ 順序刻意：先取會計年度別共識，因為 `price/pe_forward` 那個代理量要靠它的 `analyst_count`
    # 才知道自己量到的是「共識變了」還是「覆蓋崩了」（2026-09-19，七缺陷之 2）。
    fy_fn = getattr(fundamentals_provider, "fiscal_consensus", None)
    forward_coverage: Any = None
    new_rows: Sequence[Any] = ()
    if callable(fy_fn):
        try:
            old_rows, _r1 = fy_fn(t, as_of=since.date())
            new_rows, _r2 = fy_fn(t, as_of=as_of)
            forward_coverage = next(
                (c for c in new_rows if c.metric == "eps" and c.relative_label == "+1y"), None)
            got, more = fiscal_consensus_changes(old_rows, new_rows, ticker=ticker, company_id=company_id, since=since)
            events += got
            notes += more
        except Exception as exc:  # noqa: BLE001
            notes.append(f"FY 別共識變化偵測失敗：{type(exc).__name__}")

    series_fn = getattr(fundamentals_provider, "snapshot_series", None)
    if callable(series_fn):
        try:
            rows = series_fn(t, since=window_start, as_of=as_of)
            got, more = market_and_consensus_changes(
                rows, ticker=ticker, company_id=company_id, since=since,
                forward_coverage=forward_coverage)
            events += got
            notes += more
        except Exception as exc:  # noqa: BLE001
            notes.append(f"行情／共識變化偵測失敗：{type(exc).__name__}")
    else:
        notes.append("provider 沒有 snapshot_series——行情／共識變化未偵測")

    hist_fn = getattr(fundamentals_provider, "observation_history", None)
    if callable(hist_fn):
        for field_name in ("fiscal_year_results", "company_guidance"):
            try:
                rows = hist_fn(t, field_name, as_of=as_of)
            except Exception as exc:  # noqa: BLE001
                notes.append(f"{field_name} 歷史讀取失敗：{type(exc).__name__}")
                continue
            events += ledger_changes(rows, field_name=field_name, ticker=ticker, company_id=company_id, since=since)
            if field_name == "fiscal_year_results":
                observations += metric_observations(rows)
    else:
        notes.append("provider 沒有 observation_history——實際值／指引變化未偵測")

    if graph_provider is not None and company_id:
        try:
            from alpha.identity import CompanyId

            raw = graph_provider.get_structural_changes_since(since.date(), company_id=CompanyId(company_id))
            events += structural_changes(raw, ticker=ticker, company_id=company_id)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"結構事件偵測失敗：{type(exc).__name__}: {str(exc)[:80]}")

    events += assumption_changes(assumption_records, ticker=ticker, company_id=company_id, since=since)
    events += lifecycle_due_changes(lifecycle_entry, ticker=ticker, company_id=company_id, today=as_of or today)
    events += watch_changes(watches, ticker=ticker, company_id=company_id,
                            assumption_ids=[r.assumption_id for r in assumption_records])
    events.sort(key=lambda e: (e.observed_at, e.change_type, e.changed_ref))
    return events, observations, notes


def baseline_since(judged_on: date | None, records: Sequence[Any]) -> datetime:
    """偵測窗的起點＝最早的研究成果建立時點（判斷日或最早假設）；沒有任何成果就看最近 30 天。"""
    candidates: list[datetime] = []
    if judged_on is not None:
        candidates.append(start_of_day(judged_on))
    candidates += [r.created_at for r in records]
    if not candidates:
        return datetime.combine(date.today() - timedelta(days=30), time(0, 0), tzinfo=timezone.utc)
    return min(candidates)


__all__ = [
    "WATCHES_PATH", "assumption_changes", "baseline_since", "detect_changes", "fiscal_consensus_changes",
    "ledger_changes", "lifecycle_due_changes", "load_watches", "market_and_consensus_changes",
    "single_analyst_view",
    "metric_observations", "structural_changes", "watch_changes",
]
