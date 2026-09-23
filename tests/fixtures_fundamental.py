"""基期觀測／營運假設／會計年度別共識的**資料夾具**——沒有模型。

⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：這裡原本是 `tests/test_fundamental_model.py`——FY+1 因果橋
（`build_fundamental_model`）的 45 條純邏輯測試＋這組夾具。橋退役、測試一併退役；存活的測試
（refresh 引擎、共識口徑核實、read model 的共識 section、overlay ledger 閘門）仍需要同一組
基期觀測、假設與共識，所以夾具搬到這個**不以 `test_` 開頭**的模組（pytest 不收集它）。
`_run()`（跑模型）不在了：沒有東西可以跑。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from alpha.contracts import EvidenceRef
from alpha.fundamental import ConsensusEstimate, FiscalPeriod, FiscalYearActuals, OperatingAssumption
from alpha.fundamental.assumptions import assumption_record, parse_assumption_record

UTC = timezone.utc
BASE = FiscalPeriod(end=date(2026, 6, 30))
TARGET = BASE.shifted(1)                                # FY2027，至 2027-06-30
TODAY = date(2026, 9, 5)

ACT_REF = EvidenceRef(ref="engine_c://manual_observation/mo_fy2026", kind="engine_c_observation",
                      origin_entity="issuer_filing", published_at=date(2026, 8, 12),
                      retrieved_at=TODAY, recorded_at=datetime(2026, 9, 5, 4, 0, tzinfo=UTC))
GRAPH_REF = EvidenceRef(ref="graph://edge/co:coherent/supplies_to/co:nvidia", kind="graph_edge",
                        published_at=date(2026, 3, 2))
INDEX = {GRAPH_REF.ref: GRAPH_REF}

# 基期（COHR FY2026，8-K EX-99.1 的印刷數字，USD 絕對金額）
REVENUE = 7_118_200_000.0
DC = 5_274_600_000.0
IND = 1_843_600_000.0
NG_OI = 1_456_900_000.0


def _actuals(**over) -> FiscalYearActuals:
    base = dict(
        period=BASE, currency="USD", revenue=REVENUE,
        segment_revenue={"Datacenter & Communications": DC, "Industrial": IND},
        gaap={"operating_income": 897_900_000.0, "diluted_eps": 4.12, "diluted_shares": 195_400_000.0},
        non_gaap={"operating_income": NG_OI, "diluted_eps": 5.61, "diluted_shares": 195_400_000.0,
                  "interest_and_other_net": 118_100_000.0},
        evidence=(ACT_REF,), recorded_at=datetime(2026, 9, 5, 4, 0, tzinfo=UTC),
        source_filed_at=date(2026, 8, 12),
    )
    base.update(over)
    return FiscalYearActuals(**base)


def _assumption(driver: str, scope: str, value: float, *, basis: str = "session_judgment",
                created: str = "2026-09-05T08:00:00+00:00", refs=(GRAPH_REF.ref,),
                period_end: date = TARGET.end, derivation: str = "independent",
                **kw) -> OperatingAssumption:
    record = assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=period_end, driver=driver, scope=scope,
        value=value, basis=basis, rationale=f"test {driver}[{scope}]", evidence_refs=list(refs),
        created_at=datetime.fromisoformat(created), derivation=derivation, **kw)
    return parse_assumption_record(record)


def _full_set() -> list[OperatingAssumption]:
    return [
        _assumption("revenue_growth", "Datacenter & Communications", 0.60),
        _assumption("revenue_growth", "Industrial", -0.03),
        _assumption("operating_margin_delta", "mix_and_utilization", 0.025),
        _assumption("interest_and_other_net", "total", 118_100_000.0, basis="heuristic_proxy",
                    refs=(ACT_REF.ref,)),
        _assumption("tax_rate", "total", 0.19, basis="heuristic_proxy", refs=(ACT_REF.ref,)),
        _assumption("nci_attribution", "total", 12_200_000.0, basis="heuristic_proxy", refs=(ACT_REF.ref,)),
        _assumption("diluted_shares", "total", 203_400_000.0, basis="heuristic_proxy", refs=(ACT_REF.ref,)),
    ]


def _consensus(metric: str, value: float | None, *, period: FiscalPeriod = TARGET,
               year_ago: float | None = None, currency: str | None = "USD",
               captured: date = date(2026, 9, 4), analysts: int = 22) -> ConsensusEstimate:
    ref = EvidenceRef(ref=f"engine_c://consensus_estimate/COHR/{metric}/{period.end.isoformat()}",
                      kind="engine_c_observation", origin_entity="yfinance", published_at=captured)
    return ConsensusEstimate(metric=metric, period=period, value=value,
                             source=f"yfinance.{'earnings' if metric == 'eps' else 'revenue'}_estimate",
                             evidence=(ref,), analyst_count=analysts, year_ago_actual=year_ago,
                             currency=currency, captured_at=captured)


CONSENSUS = (_consensus("eps", 9.41634, year_ago=5.61), _consensus("revenue", 10_618_193_080.0))
