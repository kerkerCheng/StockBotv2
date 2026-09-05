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

from engine_c.estimates import forward_eps_from, revision_over

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
GUIDANCE_FIELD = "company_guidance"


@dataclass(slots=True)
class EngineCFundamentalsProvider:
    """Engine C 唯讀 provider。不寫入任何 authority。"""

    conn: Any = None

    def _cursor(self):
        if self.conn is None:
            from engine_c.db import get_conn

            self.conn = get_conn()
        return self.conn.cursor()

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
        return (
            MarketSnapshot(
                price=price,
                # ⚠ 可能是 None——`bar_date` 覆蓋只有 59%（舊列全空）。
                # **不得回填 snapshot_date 冒充行情交易日**（F-27）。
                bar_date=_as_date(row.get("bar_date")),
                price_kind=row.get("price_kind"),
                market_cap=(price * shares) if price and shares else None,
                evidence=(self._ref(ticker, row, "market_series"),),
            ),
            _freshness(row, as_of),
        )

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
                estimate_revision_30d=(
                    revision["eps_change"] if revision else None  # type: ignore[index]
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
        errors: list[str] = []
        for row in rows:
            if row["observation_id"] in superseded:
                continue
            try:
                payload = json.loads(row["value"])
                end = _as_date(payload.get("fiscal_year_end")) or _as_date(row.get("as_of"))
                if end is None:
                    raise ValueError("缺 fiscal_year_end")
                filed = _as_date(payload.get("source_filed_at"))
                ref = self._ledger_ref(row, published_at=filed or end)
                segments = payload.get("segment_revenue")
                return FiscalYearActuals(
                    period=FiscalPeriod(end=end),
                    currency=str(payload.get("currency") or ""),
                    revenue=float(payload["revenue"]),
                    segment_revenue=({str(k): float(v) for k, v in segments.items()}
                                     if isinstance(segments, dict) and segments else None),
                    gaap=_numeric_block(payload.get("gaap")),
                    non_gaap=(_numeric_block(payload.get("non_gaap")) if payload.get("non_gaap") else None),
                    exit_quarter=(dict(payload["exit_quarter"]) if isinstance(payload.get("exit_quarter"), dict) else None),
                    evidence=(ref,), source_filed_at=filed,
                    recorded_at=_as_datetime(row.get("recorded_at")),
                    observation_id=str(row["observation_id"]),
                ), None
            except (KeyError, TypeError, ValueError, ContractViolation) as exc:
                errors.append(f"{row['observation_id']}: {exc}")
        return None, "fiscal_year_results 觀測無法解析：" + "；".join(errors[:2])

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
