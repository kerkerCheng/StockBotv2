"""Engine C 的唯讀 provider：財務、行情、共識。

## 三個必須誠實的地方

1. **`snapshot_date` 是 ETL 執行日（本機時區），`bar_date` 才是行情交易日。**
   兩者於 2026-08-14 拆開（F-27），但 `bar_date` 覆蓋只有 1,101/1,858（59%）——
   舊列全空。所以 `MarketSnapshot.bar_date` 可能是 `None`，那是誠實的缺料，
   **不得回填 `snapshot_date` 冒充**。
2. **`as_of` 目前只支援「取該日之前的最新一筆」**，因為 Engine C 是逐日 append 的
   時間序列——這一層**真的做得到** point-in-time，與 Engine A 不同。
3. **未上市公司（`research_ticker is None`）不是錯誤。** 它是 registry 的明確標記
   （L9），對應的財務欄位全部是 `None`，而**不是** 0，也不該讓整條管線失敗（F-03）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from engine_c.etl_yfinance import (
    SNAPSHOT_GROSS_MARGIN_PERIOD, SNAPSHOT_OPERATING_MARGIN_PERIOD,
)
from engine_c.estimates import (
    attach_forward_period, forward_eps_from, forward_period_candidates, revision_over,
)

from ..contracts import (
    ConsensusSnapshot, EvidenceRef, FreshnessState, FundamentalsSnapshot, MarketSnapshot,
)
from ..errors import ContractViolation
from ..fundamental.contracts import (
    ConsensusEstimate, FiscalPeriod, FiscalYearActuals, GuidanceObservation,
)
from ..identity import CompanyId, Ticker

#: Causal Fundamental Model 的兩個 Engine C 人工 ledger 欄位（`config/engine_c_observation_fields.json`）。
FISCAL_RESULTS_FIELD = "fiscal_year_results"
#: 目標年度已報導的 YTD 實績（2026-09-13）。**不進橋**，只為了讓它的 ref 進 evidence index。
INTERIM_RESULTS_FIELD = "interim_period_results"
#: 匯率觀測（2026-09-13）。`as_of` ＝ 那個匯率屬於哪一天。
FX_RATE_FIELD = "fx_rate"

#: `fiscal_year_results` payload 裡**有對應欄位**的鍵。其餘一律原樣進 `author_notes`——
#: **不得靜默丟棄作者寫下的東西**（INV-3）。這個集合是可測的，所以「新增欄位卻忘了接」
#: 會在 `tests/test_fundamental_model.py` 變紅，而不是安靜少一格。
_PARSED_FISCAL_KEYS: frozenset[str] = frozenset({
    "fiscal_year_end", "currency", "revenue", "segment_revenue", "gaap",
    "non_gaap", "exit_quarter", "source_filed_at", "coverage_note",
    "income_statement_shape",
})
GUIDANCE_FIELD = "company_guidance"


@dataclass(slots=True)
class EngineCFundamentalsProvider:
    """Engine C 唯讀 provider。不寫入任何 authority。"""

    conn: Any = None

    def _conn(self):
        if self.conn is None:
            from engine_c.db import get_conn

            self.conn = get_conn()
        return self.conn

    def _cursor(self):
        return self._conn().cursor()

    # ---- 內部：取 as-of 之前的最新一筆快照 --------------------------------
    def _snapshot_row(self, ticker: Ticker, as_of: date | None) -> Mapping[str, Any] | None:
        cur = self._cursor()
        # ⚠ 排序用 `bar_date` 優先、`snapshot_date` 兜底：前者是行情交易日，
        # 後者是 ETL 執行日。混用會讓 as-of 差一天（F-27）。
        if as_of is None:
            cur.execute(
                "SELECT * FROM financial_snapshots WHERE ticker = ? "
                "ORDER BY COALESCE(bar_date, snapshot_date) DESC LIMIT 1",
                (str(ticker),),
            )
        else:
            cur.execute(
                "SELECT * FROM financial_snapshots WHERE ticker = ? "
                "AND COALESCE(bar_date, snapshot_date) <= ? "
                "ORDER BY COALESCE(bar_date, snapshot_date) DESC LIMIT 1",
                (str(ticker), as_of.isoformat()),
            )
        row = cur.fetchone()
        return dict(row) if row is not None else None

    def _ref(self, ticker: Ticker, row: Mapping[str, Any], kind: str) -> EvidenceRef:
        bar = _as_date(row.get("bar_date"))
        snap = _as_date(row.get("snapshot_date"))
        return EvidenceRef(
            # ⚠ **ref 不含日期。** 第一版是 `.../{ticker}/{bar_date}`，於是同一個字串
            # 同時承載「這是哪一份資料」與「它屬於哪一天」（L12 一表兩義）——
            # 實測後果：2026-09-03 寫的判斷到 09-04 就對不上，而錯誤訊息誤導成
            # 「引用了不在 ResearchContext 裡的證據」，看起來像 authority laundering
            # 而不是資料更新。時間屬於 `published_at`／`retrieved_at`，不屬於身分。
            ref=f"engine_c://financial_snapshot/{ticker}",
            kind=kind,
            # ⚠ `origin_entity` 是**誰發出這份資料**，不是**這份資料在講誰**。
            # 第一版填了 ticker，於是 L8 獨立性把「一檔股票的行情」當成
            # 「一個獨立來源」，並讓它參與結構主張的佐證計數——那是類別錯誤。
            origin_entity="yfinance",
            # ⚠ `published_at`＝事實屬於哪一天（行情交易日）；
            #    `retrieved_at`＝我們何時取得（ETL 執行日）。永遠是兩個欄位（F-27）。
            published_at=bar,
            retrieved_at=snap,
            recorded_at=_as_datetime(row.get("fetched_at")),
        )

    # ---- 對外 --------------------------------------------------------------
    def fundamentals(
        self, ticker: Ticker | None, *, as_of: date | None = None
    ) -> tuple[FundamentalsSnapshot, FreshnessState]:
        if ticker is None:
            return FundamentalsSnapshot(), FreshnessState(
                as_of=None, age_days=None, status="missing",
                reason="未上市或 registry 無 research_ticker——是明確標記不是錯誤（L9）",
            )
        row = self._snapshot_row(ticker, as_of)
        if row is None:
            return FundamentalsSnapshot(), FreshnessState(
                as_of=None, age_days=None, status="missing",
                reason=f"Engine C 無 {ticker} 的快照",
            )
        ref = self._ref(ticker, row, "engine_c_snapshot")
        return (
            FundamentalsSnapshot(
                gross_margin=_num(row.get("gross_margin")),
                operating_margin=_num(row.get("operating_margin")),
                # 期間跟著值走（2026-09-13）：有值才有期間標籤，缺席就兩邊都缺席。
                operating_margin_period=(SNAPSHOT_OPERATING_MARGIN_PERIOD
                                         if _num(row.get("operating_margin")) is not None else None),
                gross_margin_period=(SNAPSHOT_GROSS_MARGIN_PERIOD
                                     if _num(row.get("gross_margin")) is not None else None),
                revenue_ttm=_num(row.get("revenue_ttm")),
                free_cash_flow_ttm=_num(row.get("free_cash_flow_ttm")),
                cash_and_equivalents=_num(row.get("cash_and_equivalents")),
                total_debt=_num(row.get("total_debt")),
                shares_outstanding=_num(row.get("shares_outstanding")),
                # Q3（earnings_exposure）的核心輸入。yfinance 沒有分部資料，只能從
                # 10-K／年報的分部附註人工讀入 Engine C manual ledger
                #（欄位已登記，2026-09-04 Phase 4b）。
                # ⚠ 讀不到就是 `None`——**不得用整體毛利率或 revenue_ttm 近似**，
                # 也不得回空 dict：`{}` 會被讀成「分部占比全是 0」。
                segment_revenue_share=self._segment_revenue_share(ticker),
                # 報表幣別（2026-09-13）。舊列是 NULL——照抄，不補值。
                financial_currency=(str(row.get("financial_currency")).upper()
                                    if row.get("financial_currency") else None),
                evidence=(ref,),
            ),
            _freshness(row, as_of),
        )

    def market(
        self, ticker: Ticker | None, *, as_of: date | None = None
    ) -> tuple[MarketSnapshot, FreshnessState]:
        if ticker is None:
            return MarketSnapshot(), FreshnessState(
                as_of=None, age_days=None, status="missing",
                reason="未上市，無行情",
            )
        row = self._snapshot_row(ticker, as_of)
        if row is None:
            return MarketSnapshot(), FreshnessState(
                as_of=None, age_days=None, status="missing", reason="無快照")
        price = _num(row.get("price"))
        shares = _num(row.get("shares_outstanding"))
        cap = (price * shares) if price and shares else None
        cap_absence = self._share_count_absence(ticker, shares, as_of) if cap is not None else None
        quote_unit, settlement, unit_absence = self._quote_unit(ticker)
        # 單位解析不了 → 市值缺席，理由和股數那側對稱（L17-3③：機制的對稱面）。
        # ⚠ 順序刻意：股數的理由優先，因為它是「至少一邊錯了」，比「不知道單位」更嚴重。
        if cap is not None and cap_absence is None and unit_absence is not None:
            cap_absence = unit_absence
        return (
            MarketSnapshot(
                price=price,
                # ⚠ 可能是 None——`bar_date` 覆蓋只有 59%（舊列全空）。
                # **不得回填 snapshot_date 冒充行情交易日**（F-27）。
                bar_date=_as_date(row.get("bar_date")),
                price_kind=row.get("price_kind"),
                quote_unit=quote_unit,
                settlement_currency=settlement,
                market_cap=None if cap_absence else cap,
                market_cap_absence_reason=cap_absence,
                evidence=(self._ref(ticker, row, "market_series"),),
            ),
            _freshness(row, as_of),
        )

    def _quote_unit(self, ticker: Ticker) -> tuple[str | None, str | None, str | None]:
        """→ (報價單位, ISO 結算幣別, 缺席理由)。**registry 是唯一權威，不從 ticker 猜。**

        ⚠ 為什麼是把 registry 已有的分類**帶到 packet 上**，而不是在這裡重算（L16）：
        `identity/registry.py` 早就把 `market_currency` 拆成 `market_quote_unit`（報價單位，
        可能是 `GBp` 這種 minor unit）與 `market_currency`（ISO 結算幣別）兩個欄位，
        但 packet 從來沒帶過任何一個——實測 2026-09-19，16/16 檔的單位欄是 `None`，
        於是下游拿到的是**裸數字**：IQE.L 56.8B（GBp）與 LITE 83.5B（USD）並排比較，
        而真實市值只有 0.57B GBP。**錯的方向最糟**：D11 的市值上限會把最像「邊緣小公司」
        的那一檔當成超大型股擋掉。

        ⚠ **這裡刻意不換算成 USD**：那需要 FX，而 FX 要打外部——放在 provider 裡就等於
        每次 materialize 都打外部。正規化的責任在需要跨標的比較的那一層
        （`alpha/providers/market_normalization.py`；Phase 3 候選板消費）。本函式只負責**讓單位跟著值走**。
        """
        from identity.registry import get_registry

        registry = get_registry()
        company_id = registry.company_id_for_ticker(str(ticker))
        if not company_id:
            return None, None, (f"市值拒絕輸出：registry 解析不到 {ticker} 的 company_id，"
                                "無從判斷報價單位（INV-1：ticker 不是 identity，不猜）。")
        company = registry.company(company_id)
        unit = getattr(company, "market_quote_unit", None)
        settlement = getattr(company, "market_currency", None)
        if not unit or not settlement:
            return unit, settlement, (
                f"市值拒絕輸出：registry 的 {company_id} 沒有可解析的 `market_currency`，"
                "不知道 price 是以什麼單位報價的。**未登記且非 ISO 形式一律 fail closed**"
                "——把 GBp 當成 GBP 會讓市值差 100 倍，而那個錯誤在比較時看起來完全正常。")
        return unit, settlement, None

    def _share_count_absence(
        self, ticker: Ticker, snapshot_shares: float | None, as_of: date | None
    ) -> str | None:
        """快照股數與財報稀釋股數差太多時，**拒絕輸出市值**並回傳理由。

        ⚠ 為什麼是拒絕而不是「照給但標記」（2026-09-13 使用者核准 ROADMAP 那一列時的選擇）：
        `market_cap` 的唯一用途是拿去比較，而**一個錯 5.25 倍的市值在比較時不會露出任何破綻**
        ——它看起來就是一個合理的數字。缺席會讓消費端停下來問為什麼；錯的值不會。
        實測 3105.TWO：快照 80,825,000 vs 財報約 424,267 仟股。
        ⚠ 容忍帶與 `closure-gate` 的常駐計數器**共用同一個常數**（不在兩處各寫一份，L16）。
        """
        from ..closure import SHARE_COUNT_TOLERANCE

        if not snapshot_shares:
            return None
        actuals, _reason = self.fiscal_year_results(ticker, as_of=as_of)
        if actuals is None:
            return None                       # 沒有對照物就不判——那不是錯，是比不了
        block = actuals.gaap or actuals.non_gaap or {}
        filed = block.get("diluted_shares") if isinstance(block, Mapping) else None
        if not filed:
            return None
        low, high = SHARE_COUNT_TOLERANCE
        ratio = float(filed) / float(snapshot_shares)
        if low <= ratio <= high:
            return None
        return (f"市值拒絕輸出：快照流通股數 {snapshot_shares:,.0f} 與財報稀釋加權平均 "
                f"{filed:,.0f} 的比值是 {ratio:.2f}，超出容忍帶 [{low}, {high}]"
                f"——差到這個程度不是口徑差異，是**至少一邊錯了**（觀測 {actuals.observation_id}）。"
                "`market_cap = price × shares_outstanding` 會跟著錯同樣的倍數，"
                "而一個錯 N 倍的市值在比較時看起來完全正常。**缺席不是 0，是拒答。**")

    def consensus(
        self, ticker: Ticker | None, *, as_of: date | None = None
    ) -> tuple[ConsensusSnapshot, FreshnessState]:
        if ticker is None:
            return ConsensusSnapshot(), FreshnessState(
                as_of=None, age_days=None, status="missing", reason="未上市，無共識資料")
        row = self._snapshot_row(ticker, as_of)
        if row is None:
            return ConsensusSnapshot(), FreshnessState(
                as_of=None, age_days=None, status="missing", reason="無快照")
        revision = self._revision(ticker, as_of)
        return (
            ConsensusSnapshot(
                analyst_count=_int(row.get("analyst_target_count")),
                target_mean=_num(row.get("analyst_target_mean")),
                forward_pe=_num(row.get("pe_forward")),
                trailing_pe=_num(row.get("pe_trailing")),
                ev_revenue=_num(row.get("ev_revenue")),
                # ⚠ **以報價單位計，不是結算幣別**——實測 IQE.L（`GBp` 報價）
                # 導出值是 yfinance `forwardEps` 的 100 倍。它只能用在同一標的的
                # 時間序列比值（單位會消掉），**不得跨標的比大小**。
                # 見 `engine_c/estimates.py` 的模組 docstring。
                forward_eps=forward_eps_from(row.get("price"), row.get("pe_forward")),
                # Phase 4c（2026-09-04）。⚠ ROADMAP 原本寫「yfinance 沒有絕對營收
                # 估計」——實測是假的，`revenue_estimate` 的 `+1y` 73/73 檔全覆蓋。
                # 絕對值以**報表幣別**計（同 `forward_eps` 的單位陷阱），
                # `..._growth` 才是可跨標的比的那一欄。
                revenue_estimate_next_fy=_num(row.get("revenue_estimate_next_fy")),
                revenue_estimate_next_fy_growth=_num(
                    row.get("revenue_estimate_next_fy_growth")),
                # ⚠ 只有**同一個 forward 會計年度**的兩點才叫修正；不可比一律 None（不是 0）。
                # 完整原因在 `estimate_revision()` 的 payload 裡（`not_comparable_reason`）。
                estimate_revision_30d=(
                    revision["eps_change"] if revision and revision.get("comparable") else None  # type: ignore[index]
                ),
                evidence=(self._ref(ticker, row, "engine_c_snapshot"),),
            ),
            _freshness(row, as_of),
        )

    def _segment_revenue_share(self, ticker: Ticker) -> Mapping[str, float] | None:
        """分部營收占比，取自 Engine C 的人工觀測投影 `manual_fields`。

        `value` 是 JSON 物件（分部名稱 → 佔總營收比例，0..1 小數），格式契約寫在
        `config/engine_c_observation_fields.json` 的 `why`。

        **四種情形都回 `None`，不回空 dict**（L12）：沒有這筆觀測、value 不是 JSON、
        不是物件、或物件裡沒有任何可用的數值。`{}` 會讓 Q3 看到「有分部資料，
        而每一塊都是 0」——那比誠實說不知道危險得多。
        """
        try:
            cur = self._cursor()
            cur.execute(
                "SELECT value FROM manual_fields WHERE ticker = ? AND field_name = ?",
                (str(ticker), "segment_revenue_share"),
            )
            row = cur.fetchone()
        except Exception:  # noqa: BLE001 — 缺表／舊 schema 只降級成「沒有這筆觀測」
            return None
        if row is None or not row[0]:
            return None
        try:
            payload = json.loads(row[0])
        except (TypeError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        shares = {
            str(name): float(value)
            for name, value in payload.items()
            # 只收數值；`fiscal_period`／出處等說明欄位不是分部占比。
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        return shares or None

    # ---- Causal Fundamental Model 的三個唯讀入口（Phase 2，2026-09-05）------------
    def fiscal_consensus_history(
        self, ticker: Ticker | None, *, metric: str, period_end: date, as_of: date | None = None,
    ) -> tuple[tuple[tuple[date, float, int | None], ...], str | None]:
        """某一會計期間的共識**時序**（V2 gap closure）：每個抓取日一筆 `(bar_date, estimate_avg, analyst_count)`，
        身分是 `fiscal_period_end`。同一天多筆取最晚 fetched。取不到回空 tuple ＋原因。"""
        if ticker is None:
            return (), "未上市，無共識資料"
        cur = self._cursor()
        sql = ("SELECT COALESCE(bar_date, snapshot_date) AS day, estimate_avg, analyst_count, fetched_at "
               "FROM consensus_estimates WHERE ticker = ? AND metric = ? AND fiscal_period_end = ? "
               "{cut} ORDER BY day ASC, fetched_at ASC")
        params: list[Any] = [str(ticker), str(metric), period_end.isoformat()]
        if as_of is not None:
            sql = sql.format(cut="AND COALESCE(bar_date, snapshot_date) <= ? ")
            params.append(as_of.isoformat())
        else:
            sql = sql.format(cut="")
        try:
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
        except Exception as exc:  # noqa: BLE001
            return (), f"consensus_estimates 讀取失敗：{type(exc).__name__}"
        by_day: dict[date, tuple[date, float, int | None]] = {}
        for row in rows:
            day = _as_date(row.get("day"))
            value = _num(row.get("estimate_avg"))
            if day is None or value is None:
                continue
            by_day[day] = (day, value, _int(row.get("analyst_count")))     # 同一天後 fetched 者覆蓋
        if not by_day:
            return (), "這個期間沒有共識抓取紀錄"
        return tuple(by_day[d] for d in sorted(by_day)), None

    def fiscal_consensus(
        self, ticker: Ticker | None, *, as_of: date | None = None
    ) -> tuple[tuple[ConsensusEstimate, ...], str | None]:
        """會計年度別的 EPS／營收共識（`consensus_estimates`），取 as-of 之前**最新一次抓取**的全部列。

        身分是 `fiscal_period_end`（抓取當下解析），不是 `0y`／`+1y`。取不到回空 tuple ＋原因，
        不回 0。⚠ 口徑不在這裡判：provider 只帶出 `year_ago_actual`，由 `alpha.fundamental.compare`
        與一手財報數字核對。
        """
        if ticker is None:
            return (), "未上市，無共識資料"
        cur = self._cursor()
        sql = ("SELECT * FROM consensus_estimates WHERE ticker = ? "
               "{cut} ORDER BY COALESCE(bar_date, snapshot_date) DESC, fetched_at DESC")
        params: list[Any] = [str(ticker)]
        if as_of is not None:
            sql = sql.format(cut="AND COALESCE(bar_date, snapshot_date) <= ? ")
            params.append(as_of.isoformat())
        else:
            sql = sql.format(cut="")
        try:
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
        except Exception as exc:  # noqa: BLE001 — 表尚未建立只降級成「沒有」
            return (), f"consensus_estimates 讀取失敗：{type(exc).__name__}"
        if not rows:
            return (), (f"Engine C 截至 {as_of.isoformat()} 無這檔的會計年度別共識" if as_of
                        else "Engine C 無這檔的會計年度別共識（consensus_estimates 尚無列；跑一次 ETL）")
        latest = rows[0].get("bar_date") or rows[0].get("snapshot_date")
        out: list[ConsensusEstimate] = []
        for row in rows:
            if (row.get("bar_date") or row.get("snapshot_date")) != latest:
                break
            end = _as_date(row.get("fiscal_period_end"))
            if end is None:
                continue
            captured = _as_date(row.get("bar_date")) or _as_date(row.get("snapshot_date"))
            ref = EvidenceRef(
                ref=f"engine_c://consensus_estimate/{ticker}/{row['metric']}/{end.isoformat()}",
                kind="engine_c_observation", origin_entity="yfinance",
                published_at=captured, retrieved_at=_as_date(row.get("snapshot_date")),
                recorded_at=_as_datetime(row.get("fetched_at")),
            )
            out.append(ConsensusEstimate(
                metric=str(row["metric"]), period=FiscalPeriod(end=end),
                value=_num(row.get("estimate_avg")), source=str(row.get("source") or ""),
                evidence=(ref,), low=_num(row.get("estimate_low")), high=_num(row.get("estimate_high")),
                analyst_count=_int(row.get("analyst_count")),
                year_ago_actual=_num(row.get("year_ago_actual")), growth=_num(row.get("growth")),
                currency=(str(row["currency"]) if row.get("currency") else None),
                captured_at=captured, fetched_at=_as_datetime(row.get("fetched_at")),
                relative_label=(str(row["relative_label"]) if row.get("relative_label") else None),
            ))
        return tuple(out), None

    def _ledger_rows(self, ticker: Ticker, field_name: str, as_of: date | None) -> list[dict[str, Any]]:
        """`manual_observations` 的歷史列（不是投影）：as-of 用 `recorded_at`（我們何時知道）與
        `as_of`（事實屬於哪一天）雙重過濾。投影 `manual_fields` 沒有歷史，這裡刻意不讀它。"""
        cur = self._cursor()
        try:
            cur.execute(
                "SELECT observation_id, value, source_ref, as_of, recorded_at, supersedes_id "
                "FROM manual_observations WHERE ticker = ? AND field_name = ? "
                "ORDER BY as_of DESC, recorded_at DESC",
                (str(ticker), field_name),
            )
            rows = [dict(r) for r in cur.fetchall()]
        except Exception:  # noqa: BLE001
            return []
        if as_of is None:
            return rows
        cutoff = as_of.isoformat()
        return [r for r in rows
                if str(r.get("as_of") or "")[:10] <= cutoff
                and str(r.get("recorded_at") or "")[:10] <= cutoff]

    def _superseded_refs(
        self, rows: Sequence[Mapping[str, Any]], live: Mapping[str, Any]
    ) -> tuple[EvidenceRef, ...]:
        """這一筆 live 觀測的**整條 supersession 祖先鏈**，每一筆都標明被誰取代。

        ⚠⚠ 為什麼需要它（2026-09-13）：假設層是用 `engine_c://manual_observation/<id>` 這個
        **字串**引用基期的。更正一筆基期觀測（append 新紀錄 ＋ `--supersedes`，L10 的正規做法）
        之後，舊 id 就不再出現在 evidence index 裡——於是**每一條引用它的假設都變成
        `unresolved_evidence`**，下游的表現是整檔一起消失，不是「這一條的證據過期了」。
        實測（同日兩次，都是更正 coverage_note 這種**數字一字未改**的更正）：
        AEVA 8 條 operating ＋ 1 條 valuation ＋ 1 條 horizon 共 **10 筆**要全部重寫；
        4971.TWO 6 條 ＋ 估值 ＋ horizon。而**「更正成功」與「更正成功但打掉十筆假設」在寫入端
        是同一個 `✓ 已寫入 mo_xxx`**（L13-2：成功與失敗在同一個訊號上同形）。

        ⚠ **這不是讓舊引用「看起來還有效」**：ref 的 `quote` 前面會加上
        「⚠ 已被 <新 id> 取代」，所以讀者看得到那條假設引用的是哪一版基期。
        它換來的是：**更正基期不再夾帶「重寫十筆假設」的成本**，而那個成本會讓人選擇不更正
        ——正好是 append-only 設計要防的事。
        """
        by_id = {str(r["observation_id"]): r for r in rows}
        out: list[EvidenceRef] = []
        seen = {str(live["observation_id"])}
        current, successor = live, str(live["observation_id"])
        while True:
            parent_id = current.get("supersedes_id")
            if not parent_id or str(parent_id) in seen:
                break
            parent = by_id.get(str(parent_id))
            seen.add(str(parent_id))
            if parent is None:
                # 祖先不在本次查詢的視窗裡（as-of 過濾掉了）——照樣給一個可解析的 ref，
                # 因為「解析不到」與「那一版在當時不存在」是兩件事（INV-3）。
                out.append(EvidenceRef(
                    ref=f"engine_c://manual_observation/{parent_id}",
                    kind="engine_c_observation", origin_entity="issuer_filing",
                    quote=f"⚠ 已被 {successor} 取代（superseded）；該版本不在本次 as-of 視窗內"))
                break
            ref = self._ledger_ref(parent, published_at=None)
            out.append(EvidenceRef(
                ref=ref.ref, kind=ref.kind, origin_entity=ref.origin_entity,
                quote=f"⚠ 已被 {successor} 取代（superseded）：{(ref.quote or '')[:200]}",
                published_at=ref.published_at, retrieved_at=ref.retrieved_at,
                recorded_at=ref.recorded_at))
            current, successor = parent, str(parent_id)
        return tuple(out)

    def _ledger_ref(self, row: Mapping[str, Any], *, published_at: date | None) -> EvidenceRef:
        return EvidenceRef(
            ref=f"engine_c://manual_observation/{row['observation_id']}",
            kind="engine_c_observation", origin_entity="issuer_filing",
            quote=str(row.get("source_ref") or "")[:240] or None,
            published_at=published_at, retrieved_at=_as_date(row.get("recorded_at")),
            recorded_at=_as_datetime(row.get("recorded_at")),
        )

    def fiscal_year_results(
        self, ticker: Ticker | None, *, as_of: date | None = None
    ) -> tuple[FiscalYearActuals | None, str | None]:
        """最近一個**已報告且在 T 時刻已寫進 ledger**的會計年度（`fiscal_year_results`）。"""
        if ticker is None:
            return None, "未上市，無財報"
        rows = self._ledger_rows(ticker, FISCAL_RESULTS_FIELD, as_of)
        if not rows:
            return None, (f"Engine C 截至 {as_of.isoformat()} 無 {ticker} 的 fiscal_year_results 觀測" if as_of
                          else f"Engine C 無 {ticker} 的 fiscal_year_results 觀測（scripts/record_mechanical_observation.py）")
        superseded = {r.get("supersedes_id") for r in rows if r.get("supersedes_id")}
        # ⚠ **同一年度有兩筆以上生效時不得靜默選第一筆**（2026-09-20）。
        # 實測（8 檔）分兩種形狀，而它們的正確處理相反——壓成一條規則兩邊都會錯（L12）：
        #   ①**同幣別的骨架 vs 補完**（6 檔）：08:26 批次先寫只有 revenue 的骨架，10:xx 補上
        #     EPS，而後寫那筆**沒有設 `supersedes_id`**。取「比較完整」的那一筆就是對的。
        #   ②**異幣別並存**（TSM：USD 121,423,000,000 與 TWD 3,809,054,000,000，差 31 倍）。
        #     這一種**沒有任何自動規則選得對**——選錯不是誤差，是量級錯誤（AGENTS.md：
        #     報價單位 ≠ 結算幣別，價格會差 100 倍）。所以它必須 fail closed。
        # 根因兩者相同（後寫的沒 supersede），但修資料要 append correction 到 append-only
        # ledger ＝ A2 authority，得人核准；這裡只負責**不要靜默挑一個**。
        live_rows = [r for r in rows if r["observation_id"] not in superseded]
        conflict_note: str | None = None
        if len(live_rows) > 1:
            by_currency: dict[str, int] = {}
            for r in live_rows:
                try:
                    by_currency[str(json.loads(r["value"]).get("currency") or "?")] = 1 +                         by_currency.get(str(json.loads(r["value"]).get("currency") or "?"), 0)
                except (TypeError, ValueError):
                    by_currency["?"] = by_currency.get("?", 0) + 1
            if len(by_currency) > 1:
                ids = "、".join(r["observation_id"][:20] for r in live_rows)
                return None, (
                    f"{ticker} 同一年度有 {len(live_rows)} 筆生效的 fiscal_year_results，"
                    f"而且**幣別不一致**（{'／'.join(f'{k}×{v}' for k, v in sorted(by_currency.items()))}）"
                    f"：{ids}。**沒有任何自動規則選得對**——選錯不是誤差是量級錯誤"
                    "（報價單位 ≠ 結算幣別）。請 append 一筆 correction record 讓後者 supersede 前者"
                    "（Engine C 是 append-only，兩筆都留在 ledger 裡），這一格就會自己恢復")
            # 同幣別：取**比較完整**的那一筆（有 gaap／non_gaap 區塊者優先，再同則取較晚 filed）。
            # ⚠ 用明確規則取代「排序碰巧」——今天取第一筆剛好都對，但那是運氣不是保證。
            def _completeness(r: dict) -> tuple[int, str]:
                try:
                    payload = json.loads(r["value"])
                except (TypeError, ValueError):
                    return (-1, "")
                score = sum(1 for k in ("gaap", "non_gaap", "segment_revenue", "exit_quarter")
                            if payload.get(k))
                return (score, str(payload.get("source_filed_at") or ""))
            live_rows.sort(key=_completeness, reverse=True)
            conflict_note = (
                f"⚠ 同一年度有 {len(live_rows)} 筆生效觀測（幣別一致）；已取欄位最完整的 "
                f"{live_rows[0]['observation_id'][:20]}。**根因是後寫那筆沒有設 supersedes_id**"
                "——要清乾淨請 append correction record，不是改這裡的排序")
        errors: list[str] = []
        for row in live_rows:
            try:
                payload = json.loads(row["value"])
                end = _as_date(payload.get("fiscal_year_end")) or _as_date(row.get("as_of"))
                if end is None:
                    raise ValueError("缺 fiscal_year_end")
                filed = _as_date(payload.get("source_filed_at"))
                ref = self._ledger_ref(row, published_at=filed or end)
                segments = payload.get("segment_revenue")
                # **不得靜默丟棄作者寫下的東西**：列舉式解析每多一個新鍵就多一次無聲遺失。
                # 已有對應欄位的鍵在這裡扣掉，其餘原樣進 author_notes（INV-3）。
                leftovers = {k: v for k, v in payload.items() if k not in _PARSED_FISCAL_KEYS}
                return FiscalYearActuals(
                    period=FiscalPeriod(end=end),
                    currency=str(payload.get("currency") or ""),
                    revenue=float(payload["revenue"]),
                    segment_revenue=({str(k): float(v) for k, v in segments.items()}
                                     if isinstance(segments, dict) and segments else None),
                    gaap=_numeric_block(payload.get("gaap")),
                    non_gaap=(_numeric_block(payload.get("non_gaap")) if payload.get("non_gaap") else None),
                    exit_quarter=(dict(payload["exit_quarter"]) if isinstance(payload.get("exit_quarter"), dict) else None),
                    evidence=(ref, *self._superseded_refs(rows, row)), source_filed_at=filed,
                    recorded_at=_as_datetime(row.get("recorded_at")),
                    observation_id=str(row["observation_id"]),
                    coverage_note=("；".join(x for x in (
                        (str(payload["coverage_note"]).strip() if payload.get("coverage_note") else None),
                        conflict_note) if x) or None),
                    income_statement_shape=(str(payload["income_statement_shape"])
                                            if payload.get("income_statement_shape") else None),
                    author_notes=leftovers,
                ), None
            except (KeyError, TypeError, ValueError, ContractViolation) as exc:
                errors.append(f"{row['observation_id']}: {exc}")
        return None, "fiscal_year_results 觀測無法解析：" + "；".join(errors[:2])

    def interim_period_results(
        self, ticker: Ticker | None, *, as_of: date | None = None
    ) -> tuple[tuple[Any, ...], str | None]:
        """目標年度已報導的 YTD 實績（`interim_period_results`），最新在前。

        ⚠ **它不進橋**（橋的基期是完整的上一個年度）。讀它的唯一理由是讓它的 evidence ref
        進到 index，於是假設的 `evidence_refs` 指得到它——**最硬的輸入要有 authority 載體**。
        """
        from ..fundamental.contracts import InterimPeriodResults

        if ticker is None:
            return (), "未上市，無期中財報"
        rows = self._ledger_rows(ticker, INTERIM_RESULTS_FIELD, as_of)
        if not rows:
            return (), None                # 沒有不是錯——多數標的的目標年度還沒報導
        superseded = {r.get("supersedes_id") for r in rows if r.get("supersedes_id")}
        out: list[Any] = []
        errors: list[str] = []
        for row in rows:
            if row["observation_id"] in superseded:
                continue
            try:
                payload = json.loads(row["value"])
                end = _as_date(payload.get("period_end")) or _as_date(row.get("as_of"))
                if end is None:
                    raise ValueError("缺 period_end")
                filed = _as_date(payload.get("source_filed_at"))
                out.append(InterimPeriodResults(
                    period_start=_as_date(payload.get("period_start")),
                    period_end=end,
                    periods_reported=(int(payload["periods_reported"])
                                      if payload.get("periods_reported") is not None else None),
                    currency=str(payload.get("currency") or ""),
                    revenue=_num(payload.get("revenue")),
                    gaap=_numeric_block(payload.get("gaap")),
                    non_gaap=(_numeric_block(payload.get("non_gaap")) if payload.get("non_gaap") else None),
                    evidence=(self._ledger_ref(row, published_at=filed or end),
                              *self._superseded_refs(rows, row)),
                    source_filed_at=filed,
                    observation_id=str(row["observation_id"]),
                ))
            except (KeyError, TypeError, ValueError, ContractViolation) as exc:
                errors.append(f"{row['observation_id']}: {exc}")
        reason = ("interim_period_results 觀測無法解析：" + "；".join(errors[:2])) if errors and not out else None
        return tuple(out), reason

    def fx_observations(
        self, ticker: Ticker | None, *, as_of: date | None = None
    ) -> tuple[tuple[Any, ...], str | None]:
        """這個標的可用的匯率觀測（`fx_rate`），最新在前。

        ⚠ **它不是本系統的判斷**，是一個帶日期的公告數字；方向由 payload 的 `base`／`quote` 決定。
        """
        from ..fx import parse_fx_observation

        if ticker is None:
            return (), "未上市，無匯率觀測"
        rows = self._ledger_rows(ticker, FX_RATE_FIELD, as_of)
        if not rows:
            return (), None
        superseded = {r.get("supersedes_id") for r in rows if r.get("supersedes_id")}
        out: list[Any] = []
        errors: list[str] = []
        for row in rows:
            if row["observation_id"] in superseded:
                continue
            try:
                payload = json.loads(row["value"])
                stamp = _as_date(row.get("as_of"))
                if stamp is None:
                    raise ValueError("缺 as_of——匯率沒有日期就不能用（那等於用今天的匯率換過去的價）")
                out.append(parse_fx_observation(
                    payload, as_of=stamp,
                    evidence=(self._ledger_ref(row, published_at=stamp), )))
            except (KeyError, TypeError, ValueError, ContractViolation) as exc:
                errors.append(f"{row['observation_id']}: {exc}")
        reason = ("fx_rate 觀測無法解析：" + "；".join(errors[:2])) if errors and not out else None
        return tuple(out), reason

    def company_guidance(
        self, ticker: Ticker | None, *, as_of: date | None = None
    ) -> tuple[tuple[GuidanceObservation, ...], str | None]:
        """公司公開指引（`company_guidance`），最新在前。它是「公司說了什麼」，不是本系統的假設。"""
        if ticker is None:
            return (), "未上市，無指引"
        rows = self._ledger_rows(ticker, GUIDANCE_FIELD, as_of)
        out: list[GuidanceObservation] = []
        for row in rows:
            try:
                payload = json.loads(row["value"])
                issued = _as_date(payload.get("issued_at")) or _as_date(row.get("as_of"))
                values = {str(k): float(v) for k, v in payload.items()
                          if isinstance(v, (int, float)) and not isinstance(v, bool)}
                out.append(GuidanceObservation(
                    period_label=str(payload.get("period_label") or "?"),
                    period_kind=str(payload.get("period_kind") or "?"),
                    period_end=_as_date(payload.get("period_end")),
                    basis=str(payload.get("basis") or "unverified"),
                    values=values, issued_at=issued,
                    evidence=(self._ledger_ref(row, published_at=issued),),
                    observation_id=str(row["observation_id"]),
                ))
            except (TypeError, ValueError, ContractViolation):
                continue
        if not out:
            return (), f"Engine C 無 {ticker} 的 company_guidance 觀測"
        return tuple(out), None

    # ---- Step 0.5（2026-09-06）：變更偵測用的兩個窄入口（唯讀；只回時序列，不判 impact）------
    def snapshot_series(
        self, ticker: Ticker | None, *, since: date, as_of: date | None = None
    ) -> list[dict[str, Any]]:
        """`since` 之後的快照時序（升冪）。每列帶 `bar_date`（行情日）、`snapshot_date`（ETL 日）與
        `fetched_at`（我們何時取得）——變更偵測用 `fetched_at` 判「判斷當時知不知道」（INV-6）。"""
        if ticker is None:
            return []
        cur = self._cursor()
        sql = ("SELECT bar_date, snapshot_date, fetched_at, price, pe_forward, analyst_target_mean "
               "FROM financial_snapshots WHERE ticker = ? AND COALESCE(bar_date, snapshot_date) >= ? ")
        params: list[Any] = [str(ticker), since.isoformat()]
        if as_of is not None:
            sql += "AND COALESCE(bar_date, snapshot_date) <= ? "
            params.append(as_of.isoformat())
        sql += "ORDER BY COALESCE(bar_date, snapshot_date) ASC, fetched_at ASC"
        try:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
        except Exception:  # noqa: BLE001 — 舊 schema 只降級成「沒有序列」
            return []

    def observation_history(
        self, ticker: Ticker | None, field_name: str, *, as_of: date | None = None
    ) -> list[dict[str, Any]]:
        """某個人工 ledger 欄位的**全部歷史列**（含被 supersede 的），payload 已解析。
        `recorded_at`＝我們何時知道；payload 內的 `source_filed_at`／`issued_at`＝世界何時知道。"""
        if ticker is None:
            return []
        out: list[dict[str, Any]] = []
        for row in self._ledger_rows(ticker, field_name, as_of):
            try:
                payload = json.loads(row["value"])
            except (TypeError, ValueError):
                payload = None
            out.append({"observation_id": str(row["observation_id"]), "as_of": _as_date(row.get("as_of")),
                        "recorded_at": _as_datetime(row.get("recorded_at")),
                        "supersedes_id": row.get("supersedes_id"),
                        "payload": payload if isinstance(payload, dict) else None})
        return out

    def estimate_revision(
        self, ticker: Ticker | None, *, as_of: date | None = None, sessions: int = 30
    ) -> dict[str, Any] | None:
        """估計修正與股價變動**分開**的 30 個觀測窗口。Q4 的原料。

        `consensus()` 只放得下一個 `estimate_revision_30d` 純量，但 Q4 真正要問的是
        「估計動了多少 vs 股價動了多少」——那是兩個數字。這裡把完整 payload 給出來
        （`eps_change`／`price_change`／`estimate_vs_price`）。
        """
        if ticker is None:
            return None
        return self._revision(ticker, as_of, sessions=sessions)

    def _revision(
        self, ticker: Ticker, as_of: date | None, *, sessions: int = 30
    ) -> dict[str, Any] | None:
        """forward EPS 的修正幅度——**與股價變動分開**。

        原版取的是 `pe_forward` 的 30 日變化，而倍數同時被「分析師改估計」與
        「股價漲跌」推動：一個表示兩種語意，下游無從分辨（L12）。原註解說真正的
        revision「要等 Phase 4 補 `forwardEps`」——**2026-09-04 實測後那個前提是錯的**：
        `forwardEps` 恆等於 `price / forwardPE`，而兩者我們每天都存，
        導出立刻有兩個月歷史（見 `engine_c/estimates.py`）。
        """
        cur = self._cursor()
        anchor = (as_of or date.today()).isoformat()
        cur.execute(
            "SELECT COALESCE(bar_date, snapshot_date) AS d, price, pe_forward "
            "FROM financial_snapshots WHERE ticker = ? "
            "AND price IS NOT NULL AND pe_forward IS NOT NULL "
            "AND COALESCE(bar_date, snapshot_date) <= ? "
            "ORDER BY d ASC",
            (str(ticker), anchor),
        )
        series = [
            {"as_of": str(r[0]), "forward_eps": eps, "price": float(r[1])}
            for r in cur.fetchall()
            if (eps := forward_eps_from(r[1], r[2])) is not None
        ]
        # ⚠ 先把 forward 會計年度身分補上再算修正——沒有身分就沒有「同一年的修正」這回事。
        # yfinance 的 forward 是相對標籤，公司報完年報就換一年（COHR 2026-08-13 一天跳 +62.3%）。
        series = attach_forward_period(
            series, forward_period_candidates(self._conn(), str(ticker), as_of=anchor))
        return revision_over(series, sessions=sessions)


def _freshness(row: Mapping[str, Any], as_of: date | None) -> FreshnessState:
    anchor = _as_date(row.get("bar_date")) or _as_date(row.get("snapshot_date"))
    if anchor is None:
        return FreshnessState(as_of=None, age_days=None, status="missing",
                              reason="快照沒有可用的日期欄位")
    reference = as_of or date.today()
    age = (reference - anchor).days
    status = "available" if age <= 14 else "stale"
    return FreshnessState(as_of=anchor, age_days=float(age), status=status,
                          reason=None if status == "available" else f"距 {reference} 已 {age} 天")


def _numeric_block(value: Any) -> dict[str, float]:
    """子物件裡只收數值（bool 不算）；說明文字不是損益項目。"""
    if not isinstance(value, dict):
        return {}
    return {str(k): float(v) for k, v in value.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)}


def _num(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _as_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
