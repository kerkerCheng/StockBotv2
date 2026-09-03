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

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from ..contracts import (
    ConsensusSnapshot, EvidenceRef, FreshnessState, FundamentalsSnapshot, MarketSnapshot,
)
from ..identity import CompanyId, Ticker


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
                # ⚠ **Engine C 沒有 segment revenue 欄位**——Q3 的核心輸入缺席。
                # 這是 Phase 4 的第一個補洞項，不得用其他欄位近似。
                segment_revenue_share=None,
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
        price = _num(row.get("price"))
        forward_pe = _num(row.get("pe_forward"))
        return (
            ConsensusSnapshot(
                analyst_count=_int(row.get("analyst_target_count")),
                target_mean=_num(row.get("analyst_target_mean")),
                forward_pe=forward_pe,
                trailing_pe=_num(row.get("pe_trailing")),
                ev_revenue=_num(row.get("ev_revenue")),
                # ⚠ **由 price / forward_pe 反推的 implied EPS，不是分析師的估計值。**
                # 它分不出「估計被下修」與「股價漲了」。真正的 forwardEps 是
                # Phase 4 的補洞項（yfinance.info 直接有）。
                forward_eps=(price / forward_pe) if price and forward_pe else None,
                revenue_estimate_next_fy=None,   # Engine C 無此欄位（Phase 4）
                estimate_revision_30d=self._revision(ticker, as_of),
                evidence=(self._ref(ticker, row, "engine_c_snapshot"),),
            ),
            _freshness(row, as_of),
        )

    def _revision(self, ticker: Ticker, as_of: date | None) -> float | None:
        """`pe_forward` 的 30 日變化——**estimate revision 的雛形**。

        每日快照已跑了兩個月（2026-07-08 起），所以「forward 倍數在動」是量得到的。
        ⚠ 但它**混合了估計調整與股價變動**——真正的 revision 要等 Phase 4 補
        `forwardEps` 之後才算得準。這裡先給出來，並在 `ValuationSnapshot.method`
        標明它是 proxy。
        """
        cur = self._cursor()
        anchor = (as_of or date.today()).isoformat()
        cur.execute(
            "SELECT pe_forward FROM financial_snapshots WHERE ticker = ? "
            "AND pe_forward IS NOT NULL AND COALESCE(bar_date, snapshot_date) <= ? "
            "ORDER BY COALESCE(bar_date, snapshot_date) DESC LIMIT 30",
            (str(ticker), anchor),
        )
        values = [_num(r[0]) for r in cur.fetchall()]
        values = [v for v in values if v]
        if len(values) < 2:
            return None
        return (values[0] - values[-1]) / values[-1]


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
