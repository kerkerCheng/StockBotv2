"""Alpha Investment Read Model × Engine C 會計年度別資料：builder 只選取、renderer 只排版。

⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：本檔原本守 Phase 2 的 read-model 整合契約——
`internal_fundamentals`／`earnings_bridge`／`expectation_gap.internal_vs_consensus` 由 `alpha.fundamental`
的 FY+1 因果橋填入。那條鏈整組退役，14 條測試裡 10 條跟著退役（守的是內部預測、橋、數值 gap、
as-of 拒收模型、卡片的 gap 欄）。留下的判準一字未改，只是主詞換成 Engine C 的資料：

1. **會計年度別共識由 Engine C 填入、builder 不自算**，身分是 fiscal_period_end，口徑由核實結果宣告。
2. **沒有資料是 `missing`＋原因，不是 `not_modeled`、不是靜默**——取數層的原因要出現在 section 裡。
3. **取數層 fail-soft**：provider 沒能力／讀取炸掉都只讓那幾格缺席，不讓整份 view 失敗。
4. **證據索引**：共識與基期觀測的 evidence ref 要進卡片自己的 index。
5. **報表幣別身分來自財報**（基期觀測的 currency），不得回退到報價幣別。
"""
from __future__ import annotations

from datetime import date

import pytest

from briefing.alpha_view import compact_card, render_alpha_cards, render_alpha_investment_view_markdown
from tests.test_alpha_investment_view import TODAY, _view
from tests.test_alpha_view_brief import _card
from tests.fixtures_fundamental import CONSENSUS, TARGET, _actuals

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

BASES = {f"eps:{TARGET.end.isoformat()}": "non_gaap", f"revenue:{TARGET.end.isoformat()}": "not_applicable"}


def _with_engine_c(**kwargs):
    actuals = _actuals()
    evidence = (*actuals.evidence, *(ref for c in CONSENSUS for ref in c.evidence))
    return _view(base_actuals=actuals, fiscal_consensus=CONSENSUS, consensus_bases=BASES,
                 financial_evidence=evidence, target_period=TARGET, **kwargs)


def test_consensus_section_lists_fy_identified_items_from_engine_c_without_recomputing() -> None:
    view = _with_engine_c()
    fiscal = {d.key: d for d in view.consensus.fiscal_items}
    assert "consensus_eps_FY2027" in fiscal and fiscal["consensus_eps_FY2027"].basis == "observation"
    assert fiscal["consensus_eps_FY2027"].authority == "engine_c://consensus_estimates"
    assert fiscal["consensus_eps_FY2027"].value["avg"] == CONSENSUS[0].value            # 逐位相同：沒有重算
    assert fiscal["consensus_eps_FY2027"].value["accounting_basis"] == "non_gaap"   # 口徑由核實結果宣告
    assert fiscal["consensus_revenue_FY2027"].value["accounting_basis"] == "not_applicable"
    assert "FY2027" in (view.consensus.meta.reason or "")
    forward = next(d for d in view.consensus.items if d.key == "forward_eps")
    assert forward.authority == "engine_c://estimates"                    # 導出值，另一個 authority
    # ⚠ 估值鏈退役後 read model 沒有任何「內部 vs 共識」的格——共識只呈現，不相減
    assert not hasattr(view, "internal_fundamentals") and not hasattr(view, "earnings_bridge")
    assert not hasattr(view.expectation_gap, "numeric_comparisons")


def test_unverified_basis_is_declared_not_guessed() -> None:
    """沒有核實結果的那筆共識標 `unverified`——不猜 gaap、不猜 non_gaap（L11-5）。"""
    view = _view(fiscal_consensus=CONSENSUS, consensus_bases={})
    fiscal = {d.key: d for d in view.consensus.fiscal_items}
    assert fiscal["consensus_eps_FY2027"].value["accounting_basis"] == "unverified"
    assert "unverified" in (fiscal["consensus_eps_FY2027"].reason or "")


def test_without_engine_c_rows_the_section_is_missing_with_the_upstream_reason() -> None:
    view = _view(financials_reason="測試：provider 無 fiscal 能力")
    assert view.consensus.fiscal_items == ()
    assert "provider 無 fiscal 能力" in (view.consensus.meta.reason or "")
    assert view.consensus.meta.status == "partial"        # 快照仍在；缺的只有會計年度別的列


def test_sources_fail_soft_when_the_provider_has_no_fiscal_capability() -> None:
    from alpha.identity import Ticker
    from briefing.alpha_view import sources
    from tests.test_alpha_investment_view import _FakeFundamentals

    out = sources._engine_c_financials(_FakeFundamentals(), Ticker("COHR"), as_of=None, today=TODAY)  # noqa: SLF001
    assert out["actuals"] is None and out["consensus"] == () and "沒有" in out["reason"]

    class _Exploding(_FakeFundamentals):
        def fiscal_year_results(self, ticker, *, as_of=None):
            raise RuntimeError("boom")

        def fiscal_consensus(self, ticker, *, as_of=None):
            return (), None

    out = sources._engine_c_financials(_Exploding(), Ticker("COHR"), as_of=None, today=TODAY)  # noqa: SLF001
    assert out["actuals"] is None and "讀取失敗" in out["reason"] and "boom" in out["reason"]


def test_sources_keep_the_point_in_time_checks_the_model_used_to_do() -> None:
    """INV-6：模型退役了，它做的 PIT 自我核對不能跟著消失——基期觀測寫入晚於 T 拒用、共識抓取晚於 T 排除。"""
    from alpha.identity import Ticker
    from briefing.alpha_view import sources
    from tests.test_alpha_investment_view import _FakeFundamentals
    from tests.fixtures_fundamental import _consensus

    class _Provider(_FakeFundamentals):
        def fiscal_year_results(self, ticker, *, as_of=None):
            return _actuals(), None                                          # recorded_at 2026-09-05

        def fiscal_consensus(self, ticker, *, as_of=None):
            return (_consensus("eps", 9.4, year_ago=5.61, captured=date(2026, 9, 4)),
                    _consensus("eps", 9.9, year_ago=5.61, captured=date(2026, 9, 10))), None

    early = sources._engine_c_financials(_Provider(), Ticker("COHR"), as_of=date(2026, 9, 1), today=TODAY)  # noqa: SLF001
    assert early["actuals"] is None and "lookahead" in early["reason"]
    assert [c.captured_at for c in early["consensus"]] == []                 # 兩筆都晚於 09-01
    assert "2 筆共識晚於 as_of" in early["reason"]
    later = sources._engine_c_financials(_Provider(), Ticker("COHR"), as_of=date(2026, 9, 6), today=TODAY)  # noqa: SLF001
    assert later["actuals"] is not None and [c.captured_at for c in later["consensus"]] == [date(2026, 9, 4)]
    assert later["target_period"].end == TARGET.end                         # 基期 FY2026 → 目標 FY2027
    assert later["bases"][f"eps:{TARGET.end.isoformat()}"] == "non_gaap"


def test_evidence_index_resolves_engine_c_citations() -> None:
    """共識與基期觀測的 evidence ref 必須出現在卡片自己的 evidence index，否則讀者拿著卡片對不回引用
    （Phase 2 驗收 2026-09-06 抓到的 provenance 缺口；模型退役後這條路改由取數層直接供應）。"""
    view = _with_engine_c()
    indexed = {item.ref for item in view.evidence.index}
    assert "engine_c://manual_observation/mo_fy2026" in indexed
    assert all(r in indexed for c in CONSENSUS for r in c.refs)
    # 沒有 Engine C 列時 evidence index 不受影響
    assert "engine_c://manual_observation/mo_fy2026" not in {i.ref for i in _view().evidence.index}


def test_reporting_currency_label_comes_from_the_filing_not_from_the_quote_currency() -> None:
    """`reporting_currency（X）` 的 X 必須是**財報幣別**，不是報價幣別。

    事發（2026-09-13，XFAB.PA）：這個標籤一直是用 registry 的 `market_currency` 組的，
    而它掛的是法定財報幣別的數字。兩者相同的美股看不出來；不同的 5 檔全部標錯——最危險的是
    **IQE.L（GBP 財報／GBp 報價）**，把報表數字標成 minor unit 會差 100 倍（`AGENTS.md`「報價單位 ≠ 結算幣別」）。
    ⚠ 不得回退到 `market_currency`：答不出報表幣別就寫「未知」（L11-5）。
    """
    view = _with_engine_c(identity={"market_currency": "SEK", "market_quote_unit": "SEK"})
    units = {item.unit for item in (*view.fundamentals.items, *view.consensus.fiscal_items)
             if item.unit and item.unit.startswith("reporting_currency")}
    assert units, "沒有任何 reporting_currency 欄位——這個測試會變成恆真"
    for unit in units:
        assert "USD" in unit, f"{unit} 沒有用財報幣別"
        assert "SEK" not in unit, "報價幣別漏進了報表幣別的標籤"
    unknown = _view(identity={"market_currency": "SEK", "market_quote_unit": "SEK"})
    assert all("SEK" not in (item.unit or "") for item in unknown.fundamentals.items
               if (item.unit or "").startswith("reporting_currency"))


def test_assumption_basis_vocabulary_is_a_subset_of_the_read_model_vocabulary() -> None:
    """假設的知識種類是 read model `Basis` 的**子集**，刻意沒有 `deterministic`——輸入假設永遠不是確定性事實。
    （原本住在 `test_fundamental_model.py`；橋退役，這條守 ledger 契約的判準留下。）"""
    from alpha.fundamental import ASSUMPTION_BASES
    from briefing.alpha_view.contracts import BASES

    assert set(ASSUMPTION_BASES) <= set(BASES)
    assert "deterministic" not in ASSUMPTION_BASES


def test_daily_brief_card_row_has_no_valuation_columns() -> None:
    """卡片摘要的三個估值欄（市場隱含 EPS 成長／內部 vs 共識 EPS／Fair value vs 現價）退役後，
    表頭、資料列與舊 fixture 的列必須同寬——少一欄的列會讓整張表錯位。"""
    card = compact_card(_with_engine_c())
    for retired in ("market_implied_eps_growth", "internal_vs_consensus", "valuation", "implied_return",
                    "internal_fundamentals_status"):
        assert retired not in card, retired
    lines = render_alpha_cards([card, _card()])
    head = next(l for l in lines if l.startswith("| 標的"))
    rows = [l for l in lines if l.startswith("| co:coherent")]
    assert len(rows) == 2 and all(r.count("|") == head.count("|") == 9 for r in rows)
    assert "Fair value" not in head and "隱含" not in head
    text = render_alpha_investment_view_markdown(_with_engine_c())
    assert "會計年度別共識" in text and "FY2027 EPS 共識" in text
