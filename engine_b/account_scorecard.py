"""帳號計分表（D5 五欄）——ROADMAP Phase 3。

回答漏斗最上游那一題：**哪個來源歷史上產出贏家。**

## 五欄

| 欄 | 問什麼 | 算得回來嗎 |
|---|---|---|
| 點名後 30／90 天對 QQQ 與 SOXX 的超額報酬中位數 | 點名之後標的走得比大盤好嗎 | 30 天可以；90 天看樣本期夠不夠 |
| 點名前 30 天漲幅中位數 | 是不是都在漲完之後才點名（追高） | 可以 |
| 追源成功率 | 點名追得到一手嗎 | 可以（`refs.trace_status`） |
| 假設命中率 | 點名的主張後來被 filing 證實了嗎 | **算不回來**——需要 filing 裁決，本系統今天沒有這個裁決紀錄 |
| no-go 率 | 有多少比例連 triage 都過不了 | 可以 |

## ⚠ 三件刻意不做的事

1. **算不回來的欄位宣告 `absence_kind`，不填 0。** 「還沒建」與「算出來是 0」是兩件事，
   壓成同一格就是 L12（一個表示承載兩種語意）。`hypothesis_hit_rate` 永遠回
   `capability_absent`，直到有 filing 裁決紀錄為止。
2. **不解析 registry 以外的 ticker。** lead 的 `entities.tickers` 是抽取結果（`SIVE` 而不是
   `SIVE.ST`），拿它直接查價會撞號。解析走 `identity.registry` 的 `company_ids`；
   解析不到的**列進 filtered 與 reasons**（INV-3），不猜、也不靜默丟掉。
3. **不動 tier。** 本模組只算數字。tier 升降是一季一次的 pq2 manual（D5）——
   計分表是那個決定的輸入，不是那個決定。

## ⚠ 三個已知偏差（必須印在表上，D5／§6）

- **倖存者**：帳號是因為「感覺對過」才被選進登記表的，計分表量的是一個已經被選過的樣本。
- **後見之明**：回溯評分用的是今天才知道的價格序列。
- **單邊上漲**：2026 年光互連整體單邊上漲，所以**必須同時對 SOXX 算超額**，只對 QQQ 會高估。
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEADS_PATH = ROOT / "library" / "leads" / "pending_leads.json"

#: 超額報酬的比較基準。**兩個都算、都印**——只對 QQQ 算會被 2026 年光互連的單邊上漲高估。
BENCHMARKS: tuple[str, ...] = ("QQQ", "SOXX")

#: 點名後要看的持有期（日曆天）。
HORIZONS_DAYS: tuple[int, ...] = (30, 90)

#: 點名前要看的回顧期（日曆天）——回答「是不是漲完才點名」。
LOOKBACK_DAYS = 30

#: 三個已知偏差，逐字印在表上。**不是註腳，是欄位。**
KNOWN_BIASES: tuple[str, ...] = (
    "倖存者偏差：帳號是因為「感覺對過」才被選進登記表的，這裡量的是一個已經被選過的樣本。",
    "後見之明偏差：回溯評分用的是今天才知道的價格序列，當時並沒有這些後續資料。",
    "單邊上漲偏差：2026 年光互連整體單邊上漲——所以同時對 SOXX 算超額，只看 QQQ 會高估。",
)

#: 一輪最多對幾檔取價。**這是無人值守的網路 surface 上限，不是效能參數**：
#: `python -m webapp materialize` 是 prefix rule，所以 `--scorecard` 自動被無人值守放行；
#: 放行與收緊必須同時發生（L15），而這裡收緊的就是「它最多會打幾個外部請求」。
#: 今天實際用到 40 檔；上限留餘裕但有界，帳號變多時會先撞到它並**在報表上現形**，
#: 不會安靜地長成一個沒人注意的爬蟲。
MAX_PRICED_SYMBOLS = 200

#: 缺席種類。與心跳／APP 用的是同一套字彙（`absence_kind` 由產生缺席的程式自己宣告，L16）。
ABSENCE_CAPABILITY = "capability_absent"
ABSENCE_INSUFFICIENT = "insufficient_sample"


@dataclass
class FilterReport:
    """INV-3：每個 filter 都能報 input／accepted／filtered／reasons。"""

    input_count: int = 0
    accepted_count: int = 0
    reasons: dict[str, int] = field(default_factory=dict)

    def reject(self, reason: str) -> None:
        self.reasons[reason] = self.reasons.get(reason, 0) + 1

    @property
    def filtered_count(self) -> int:
        return self.input_count - self.accepted_count

    def as_dict(self) -> dict[str, Any]:
        return {
            "input": self.input_count,
            "accepted": self.accepted_count,
            "filtered": self.filtered_count,
            "reasons": dict(sorted(self.reasons.items(), key=lambda kv: -kv[1])),
        }


@dataclass(frozen=True)
class NamedCall:
    """一則「帳號在某天點名了某個標的」——計分表的原子。"""

    lead_id: str
    source: str
    company_id: str
    symbol: str
    called_on: date
    status: str
    trace_status: str | None

    def stamp(self, prices: "Mapping[str, Mapping[date, float]]") -> dict[str, Any]:
        """D5 的「每則貼文蓋章」：貼文時間＋當日收盤價＋具名實體。

        ⚠ **第一次跑是回溯蓋章，不是當時蓋的**——價格是今天去查的歷史收盤。
        這是後見之明偏差的一部分，已經印在 `KNOWN_BIASES` 裡。
        蓋章落在 artifact 裡之後，後續就有一份不必重抓的紀錄。
        """
        series = prices.get(self.symbol) or {}
        candidates = [d for d in series if d <= self.called_on]
        close = series[max(candidates)] if candidates else None
        return {
            "lead_id": self.lead_id, "company_id": self.company_id, "symbol": self.symbol,
            "called_on": self.called_on.isoformat(), "close_on_call": close,
            "close_absent_kind": None if close is not None else "upstream_missing",
            "status": self.status, "trace_status": self.trace_status,
        }


@dataclass
class Metric:
    """一個數字，或一個「為什麼沒有這個數字」。**兩者不得壓成同一格。**"""

    value: float | None = None
    n: int = 0
    absence_kind: str | None = None
    reason: str = ""
    #: `insufficient_sample` 專用：**什麼時候該回來再看**。等時間的缺席必須有到期，
    #: 否則它與「要建能力才會有」在讀者眼裡同形——而兩者的下一步完全相反（INV-2）。
    revisit_after: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"value": self.value, "n": self.n}
        if self.absence_kind:
            out["absence_kind"] = self.absence_kind
            out["reason"] = self.reason
        if self.revisit_after:
            out["revisit_after"] = self.revisit_after
        return out


def _parse_day(raw: Any) -> date | None:
    if not raw:
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def collect_named_calls(
    leads: Mapping[str, Mapping[str, Any]],
    *,
    harvest_key: str,
    ticker_map: Mapping[str, str | None],
) -> tuple[list[NamedCall], FilterReport]:
    """某個帳號的 lead → 可計分的具名點名。

    ⚠ 解析**只走 registry 的 `company_ids`**。lead 的 `entities.tickers` 是抽取結果，
    `SIVE` 這種沒有交易所後綴的字串拿去查價會撞到別家公司（INV-1：ticker 不是 identity）。
    解析不到的列進 reasons，讓「registry 覆蓋不足」這個真實缺口現形，而不是被平均掉。
    """
    report = FilterReport()
    calls: list[NamedCall] = []
    for lead in leads.values():
        if str(lead.get("source") or "") != harvest_key:
            continue
        report.input_count += 1
        called_on = _parse_day(lead.get("published_at")) or _parse_day(lead.get("first_seen"))
        if called_on is None:
            report.reject("no_published_at")
            continue
        entities = lead.get("entities") or {}
        company_ids = [str(c) for c in (entities.get("company_ids") or [])]
        if not company_ids:
            report.reject("no_named_company" if not (entities.get("tickers") or [])
                          else "ticker_without_registry_company_id")
            continue
        resolved = [(cid, ticker_map.get(cid)) for cid in company_ids]
        usable = [(cid, sym) for cid, sym in resolved if sym]
        if not usable:
            report.reject("registry_has_no_quote_symbol")
            continue
        report.accepted_count += 1
        refs = lead.get("refs") or {}
        for company_id, symbol in usable:
            calls.append(NamedCall(
                lead_id=str(lead.get("lead_id") or ""),
                source=harvest_key,
                company_id=company_id,
                symbol=str(symbol),
                called_on=called_on,
                status=str(lead.get("status") or ""),
                trace_status=(str(refs.get("trace_status")) if refs.get("trace_status") else None),
            ))
    return calls, report


def _pct_change(series: Mapping[date, float], start: date, end: date) -> float | None:
    """`start` 與 `end` 之間的簡單報酬。兩端都取**該日或之前最近的**收盤。"""
    def at(day: date) -> float | None:
        candidates = [d for d in series if d <= day]
        return series[max(candidates)] if candidates else None

    begin, finish = at(start), at(end)
    if begin is None or finish is None or begin == 0:
        return None
    return finish / begin - 1.0


def score_account(
    calls: Sequence[NamedCall],
    *,
    prices: Mapping[str, Mapping[date, float]],
    today: date,
    no_go_rate: Metric,
    trace_metric: Metric,
) -> dict[str, Any]:
    """具名點名 → 五欄。價格序列由呼叫端注入（測試不打網路）。"""
    # 等時間的缺席要算得出到期日，靠的是**最早那一則點名**：它走完 horizon 的那天，
    # 這一格就該有第一個值。沒有任何點名時留 None（那時缺的不是時間，是樣本）。
    first_call_day = min((call.called_on for call in calls), default=None)
    excess: dict[str, Metric] = {}
    horizon_reports: dict[str, dict[str, Any]] = {}
    for horizon in HORIZONS_DAYS:
        for benchmark in BENCHMARKS:
            key = f"excess_{horizon}d_vs_{benchmark}"
            report = FilterReport()
            values: list[float] = []
            for call in calls:
                report.input_count += 1
                end = call.called_on + timedelta(days=horizon)
                if end > today:
                    report.reject("horizon_not_elapsed")
                    continue
                own = prices.get(call.symbol)
                base = prices.get(benchmark)
                if not own:
                    report.reject("no_price_series")
                    continue
                if not base:
                    report.reject("no_benchmark_series")
                    continue
                own_return = _pct_change(own, call.called_on, end)
                base_return = _pct_change(base, call.called_on, end)
                if own_return is None or base_return is None:
                    report.reject("price_gap_at_endpoint")
                    continue
                report.accepted_count += 1
                values.append(own_return - base_return)
            horizon_reports[key] = report.as_dict()
            if values:
                excess[key] = Metric(value=statistics.median(values), n=len(values))
            else:
                horizon_not_elapsed = (
                    report.reasons.get("horizon_not_elapsed") == report.input_count)
                excess[key] = Metric(
                    n=0, absence_kind=ABSENCE_INSUFFICIENT,
                    # 「持有期還沒走完」是**等時間**，而等時間必須有到期日：
                    # 最早的那一則點名走完 horizon 的那天，就是這一格該有值的日子。
                    revisit_after=((first_call_day + timedelta(days=horizon)).isoformat()
                                   if horizon_not_elapsed and first_call_day else None),
                    reason=(f"{horizon} 天持有期在樣本裡一次都沒有走完"
                            if horizon_not_elapsed
                            else "沒有任何一則點名同時有標的與基準的價格"))

    prior_report = FilterReport()
    prior_values: list[float] = []
    for call in calls:
        prior_report.input_count += 1
        own = prices.get(call.symbol)
        if not own:
            prior_report.reject("no_price_series")
            continue
        move = _pct_change(own, call.called_on - timedelta(days=LOOKBACK_DAYS), call.called_on)
        if move is None:
            prior_report.reject("price_gap_before_call")
            continue
        prior_report.accepted_count += 1
        prior_values.append(move)
    prior = (Metric(value=statistics.median(prior_values), n=len(prior_values)) if prior_values
             else Metric(n=0, absence_kind=ABSENCE_INSUFFICIENT, reason="沒有任何一則點名取得到點名前的價格"))

    return {
        "excess_returns": {k: v.as_dict() for k, v in excess.items()},
        "excess_return_filters": horizon_reports,
        "prior_30d_move": prior.as_dict(),
        "prior_30d_filter": prior_report.as_dict(),
        "trace_success_rate": trace_metric.as_dict(),
        "hypothesis_hit_rate": Metric(
            n=0, absence_kind=ABSENCE_CAPABILITY,
            reason=("需要 filing 裁決才算得出來，本系統今天沒有「這則點名的主張後來被哪份 filing 證實／推翻」"
                    "的紀錄。⚠ 這一格不得填 0——「還沒建」與「命中率是 0」是兩件事。"
                    "要有值得先建那份裁決紀錄（把 lead 的具名主張接到後續 filing 的逐字核對結果），"
                    "那是一個獨立的 ROADMAP 項，不是等時間。"),
        ).as_dict(),
        "no_go_rate": no_go_rate.as_dict(),
    }


def first_call_per_symbol(calls: Sequence[NamedCall]) -> list[NamedCall]:
    """每檔只留**最早一次**點名。

    ⚠ 為什麼需要它：SIVE 在樣本裡被點名 94 次，LITE 72 次。用全部點名算中位數，
    量到的是「這個帳號多常提某一檔」與「那一檔那段期間怎麼走」的乘積——
    **一檔走得好就能把中位數拉起來**。去重之後量的才比較接近「選股」。
    兩個都印、都標 n：重複點名本身也是資訊（它是持續追蹤，不是雜訊），
    **但兩個數字不得互相取代**（L12：一個表示不該承載兩種語意）。
    """
    earliest: dict[str, NamedCall] = {}
    for call in calls:
        current = earliest.get(call.symbol)
        if current is None or call.called_on < current.called_on:
            earliest[call.symbol] = call
    return sorted(earliest.values(), key=lambda c: (c.called_on, c.symbol))


def trace_success(calls: Sequence[NamedCall]) -> Metric:
    """追源成功率：分母是**真的進過追源的**（有 `trace_status`），不是全部點名。

    把沒追過的算進分母會讓「沒去追」看起來像「追不到」——那是兩件事。
    """
    traced = [c for c in calls if c.trace_status]
    if not traced:
        return Metric(n=0, absence_kind=ABSENCE_INSUFFICIENT, reason="沒有任何一則點名進過追源")
    obtained = [c for c in traced if c.trace_status == "original_obtained"]
    return Metric(value=len(obtained) / len(traced), n=len(traced))


def no_go_share(leads: Mapping[str, Mapping[str, Any]], *, harvest_key: str) -> Metric:
    """no-go 率：分母是該帳號**全部**已 triage 的 lead（含沒有具名標的的）。

    ⚠ 刻意與其他四欄的分母不同，而且必須講出來：no-go 率問的是「這個帳號有多少雜訊」，
    那個問題的分母就是全部貼文；超額報酬問的是「點名的標的後來如何」，分母只能是具名點名。
    """
    decided = [lead for lead in leads.values()
               if str(lead.get("source") or "") == harvest_key
               and str(lead.get("status") or "") not in ("", "pending")]
    if not decided:
        return Metric(n=0, absence_kind=ABSENCE_INSUFFICIENT, reason="這個帳號還沒有任何已 triage 的貼文")
    no_go = [lead for lead in decided if str(lead.get("status")) == "triaged_no_go"]
    return Metric(value=len(no_go) / len(decided), n=len(decided))


def build_scorecard(
    *,
    leads_path: Path | None = None,
    today: date | None = None,
    price_loader: Callable[[Sequence[str], date, date], Mapping[str, Mapping[date, float]]] | None = None,
) -> dict[str, Any]:
    """整張計分表。`price_loader` 可注入——測試不打網路，正式跑用 yfinance。"""
    from identity.registry import get_registry

    from .signal_source_registry import load as load_sources

    day = today or datetime.now(timezone.utc).date()
    path = leads_path or DEFAULT_LEADS_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    leads: Mapping[str, Mapping[str, Any]] = payload.get("leads") or {}
    registry = load_sources()
    ticker_map = dict(get_registry().ticker_map)

    accounts: list[dict[str, Any]] = []
    all_symbols: set[str] = set()
    per_account_calls: dict[str, list[NamedCall]] = {}
    per_account_filter: dict[str, FilterReport] = {}
    for source in sorted(registry.sources.values(), key=lambda s: s.source_id):
        calls, report = collect_named_calls(
            leads, harvest_key=source.harvest_key, ticker_map=ticker_map)
        per_account_calls[source.source_id] = calls
        per_account_filter[source.source_id] = report
        all_symbols.update(c.symbol for c in calls)

    earliest = min((c.called_on for calls in per_account_calls.values() for c in calls), default=None)
    prices: Mapping[str, Mapping[date, float]] = {}
    price_note = ""
    price_budget = {"requested": 0, "fetched": 0, "cap": MAX_PRICED_SYMBOLS, "truncated": []}
    if all_symbols and earliest is not None:
        loader = price_loader or _yfinance_closes
        start = earliest - timedelta(days=LOOKBACK_DAYS + 10)
        wanted = sorted(all_symbols | set(BENCHMARKS))
        price_budget["requested"] = len(wanted)
        if len(wanted) > MAX_PRICED_SYMBOLS:
            # 基準永遠留著（沒有基準就算不出超額），其餘按字母序截斷並**把被截掉的印出來**。
            keep = [s for s in wanted if s in BENCHMARKS]
            keep += [s for s in wanted if s not in BENCHMARKS][:MAX_PRICED_SYMBOLS - len(keep)]
            price_budget["truncated"] = [s for s in wanted if s not in keep]
            wanted = keep
            price_note = (f"取價檔數上限 {MAX_PRICED_SYMBOLS} 已觸及："
                          f"{len(price_budget['truncated'])} 檔沒有取價，"
                          f"它們的點名會以 no_price_series 出現在 filter reasons 裡")
        price_budget["fetched"] = len(wanted)
        try:
            prices = loader(wanted, start, day)
        except Exception as exc:  # noqa: BLE001 — 取價失敗不得讓整張表消失
            price_note = f"價格取得失敗（{type(exc).__name__}: {exc}）——超額報酬與點名前漲幅因此無值"

    for source in sorted(registry.sources.values(), key=lambda s: s.source_id):
        calls = per_account_calls[source.source_id]
        no_go = no_go_share(leads, harvest_key=source.harvest_key)
        scored = score_account(
            calls, prices=prices, today=day, no_go_rate=no_go,
            trace_metric=trace_success(calls))
        deduped = first_call_per_symbol(calls)
        scored_first = score_account(
            deduped, prices=prices, today=day, no_go_rate=no_go,
            trace_metric=trace_success(deduped))
        called_days = [c.called_on for c in calls]
        accounts.append({
            "source_id": source.source_id,
            "harvest_key": source.harvest_key,
            "tier": source.tier,
            "tier_since": source.tier_since,
            "pq1_priority_bonus": source.pq1_priority_bonus,
            "status": source.status,
            "measurement_start": min(called_days).isoformat() if called_days else None,
            "measurement_end": max(called_days).isoformat() if called_days else None,
            "named_calls": len(calls),
            "distinct_symbols": len({c.symbol for c in calls}),
            "lead_filter": per_account_filter[source.source_id].as_dict(),
            "metrics": scored,
            "metrics_first_call_per_symbol": scored_first,
            "stamps": [c.stamp(prices) for c in calls],
        })

    payload: dict[str, Any] = {
        "kind": "account_scorecard",
        "schema_version": "stockbot-app/account_scorecard/1",
        "title": "帳號計分表：哪個來源歷史上產出贏家",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": day.isoformat(),
        # 計分表**沒有 point-in-time 視角**：它算的就是「今天回頭看」，
        # 而那正是後見之明偏差的來源，已逐字印在 KNOWN_BIASES。不假裝有 as-of 投影。
        "point_in_time": {"as_of": None, "mode": "current"},
        "authority": {
            "function": "engine_b.account_scorecard.build_scorecard",
            "command": "python -m webapp materialize --scorecard",
            "note": ("登記表是 config/signal_sources.json（唯一 loader：engine_b.signal_source_registry）；"
                     "價格是 yfinance 歷史收盤。**本表不改 tier**——tier 升降是一季一次的 pq2 manual。"),
        },
        "materializer": {
            "version": "account-scorecard/1",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
        "benchmarks": list(BENCHMARKS),
        "horizons_days": list(HORIZONS_DAYS),
        "lookback_days": LOOKBACK_DAYS,
        "known_biases": list(KNOWN_BIASES),
        "price_note": price_note,
        "price_budget": price_budget,
        "tier_counts": dict(registry.tier_counts()),
        "accounts": accounts,
        "this_is_not": (
            "這不是勝率、也不是投資建議。它量的是「這個來源點名的標的後來相對大盤如何」，"
            "樣本以個位數月計，且三個已知偏差都還在。"
            "⚠ tier 升降是一季一次的 pq2 manual——本表是那個決定的輸入，不是那個決定。"
        ),
    }
    from webapp.contracts import canonical_digest, state_freshness_identity

    payload["freshness_identity"] = state_freshness_identity(
        kind="account_scorecard", as_of=payload["as_of"],
        # 認知狀態＝每個帳號的 tier、可計分點名數、五欄各自有沒有值。
        # ⚠ 報酬數字本身的小數變動**不算**認知變化——否則每天重抓價格都會讓它看起來「變了」。
        identity={"accounts": [[a["source_id"], a["tier"], a["named_calls"], a["distinct_symbols"],
                                sorted((a["metrics"].get("excess_returns") or {}).keys()),
                                [k for k, v in (a["metrics"].get("excess_returns") or {}).items()
                                 if v.get("value") is not None]]
                               for a in accounts]})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def _yfinance_closes(
    symbols: Sequence[str], start: date, end: date
) -> dict[str, dict[date, float]]:
    """yfinance 日線收盤。**逐檔抓**（批次 API 的欄位形狀會隨檔數變，逐檔比較好除錯）。"""
    import yfinance as yf

    out: dict[str, dict[date, float]] = {}
    for symbol in symbols:
        try:
            frame = yf.Ticker(symbol).history(
                start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=True)
        except Exception:  # noqa: BLE001 — 單檔失敗不得讓整張表消失
            continue
        if frame is None or frame.empty or "Close" not in frame:
            continue
        series: dict[date, float] = {}
        for stamp, value in frame["Close"].items():
            try:
                series[stamp.date()] = float(value)
            except (AttributeError, TypeError, ValueError):
                continue
        if series:
            out[symbol] = series
    return out


def render(scorecard: Mapping[str, Any]) -> str:
    """計分表 → 給人讀的 Markdown。心跳第 5 段與 weekly 報告共用。"""
    lines = [f"# 帳號計分表（as-of {scorecard['as_of']}）"]
    counts = scorecard.get("tier_counts") or {}
    lines.append("tier 分佈：" + "／".join(f"{k} {v}" for k, v in counts.items()))
    if scorecard.get("price_note"):
        lines.append(f"⚠ {scorecard['price_note']}")
    for account in scorecard.get("accounts") or []:
        metrics = account["metrics"]
        lines.append("")
        lines.append(
            f"## {account['harvest_key']}｜tier `{account['tier']}`"
            f"（pq1 加分 +{account['pq1_priority_bonus']}）")
        lines.append(
            f"- 量測期間 **{account['measurement_start']} → {account['measurement_end']}**｜"
            f"具名點名 **{account['named_calls']}** 則／**{account['distinct_symbols']}** 檔"
            f"（貼文 {account['lead_filter']['input']} 則，"
            f"可計分 {account['lead_filter']['accepted']}、"
            f"濾掉 {account['lead_filter']['filtered']}）")
        for reason, count in (account["lead_filter"]["reasons"] or {}).items():
            lines.append(f"    - 濾掉 {count}：{reason}")
        first = account.get("metrics_first_call_per_symbol") or {}
        first_excess = (first.get("excess_returns") or {})
        for key, cell in (metrics["excess_returns"] or {}).items():
            lines.append(f"- {key}：{_cell(cell)}")
            if key in first_excess:
                lines.append(f"    ↳ 每檔只算最早一次：{_cell(first_excess[key])}")
        lines.append(f"- 點名前 {LOOKBACK_DAYS} 天漲幅中位數：{_cell(metrics['prior_30d_move'])}")
        if first.get("prior_30d_move"):
            lines.append(f"    ↳ 每檔只算最早一次：{_cell(first['prior_30d_move'])}")
        lines.append(f"- 追源成功率：{_cell(metrics['trace_success_rate'])}")
        lines.append(f"- 假設命中率：{_cell(metrics['hypothesis_hit_rate'])}")
        lines.append(f"- no-go 率：{_cell(metrics['no_go_rate'])}")
    lines.append("")
    lines.append("**三個已知偏差（不是註腳，是這張表的一部分）：**")
    for bias in scorecard.get("known_biases") or []:
        lines.append(f"- {bias}")
    lines.append(f"⚠ {scorecard.get('this_is_not', '')}")
    return "\n".join(lines)


def _cell(cell: Mapping[str, Any]) -> str:
    if cell.get("value") is None:
        return f"**沒有值**（{cell.get('absence_kind')}）——{cell.get('reason', '')}"
    return f"{cell['value'] * 100:+.2f}%（n={cell['n']}）"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="帳號計分表（D5 五欄）")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--no-network", action="store_true",
                        help="不抓價格（超額報酬與點名前漲幅會誠實回報沒有值）")
    parser.add_argument("--out", default=None, help="同時寫一份 JSON 到這個路徑")
    args = parser.parse_args(argv)

    loader = (lambda *_: {}) if args.no_network else None
    card = build_scorecard(price_loader=loader)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✓ {target}")
    print(json.dumps(card, ensure_ascii=False, indent=2) if args.format == "json" else render(card))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
