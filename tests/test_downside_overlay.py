"""D2「判斷錯了值多少」（downside scenario，2026-09-18）的純邏輯測試——不需要 Neo4j／Engine C。

**這份測試守的是「對稱」本身。** D2 的全部內容就是一句話：反證成真時的假設套**同一條橋**。
一邊要證據、另一邊隨便寫，就是 bear case 換個名字；一邊用同一條橋、另一邊自己算一套，
「賭對了值多少」與「判斷錯了值多少」就不可比，而那兩個數字並排才是短評那把尺的兩端。

五件事：
1. **型別層規則完全對稱**：downside 也只能是核心 driver、必須 independent、必須有 supporting 證據。
2. **同一段程式碼**：兩個 scenario 走同一個 `_payoff_section`／`_overlay_panel`，不是兩份手寫。
3. **兩種缺席分開，且不得互相頂替**：`bet/variant.overlay` 的 Abstention 不能冒充成
   「說不出下檔」——那會把一筆待辦讀成答案（Q2 在估值層踩過的形狀）。
4. **下檔不再是 `not_modeled`**：它現在是「有能力、還沒寫」（`missing`＋`not_yet_recorded`），
   而這兩者的下一步完全不同——`not_modeled` 沒有人該去補，`missing` 有。
5. **尺的另一端缺席是 `None` 不是 0**：畫一個 0% 的下檔等於替使用者做一個沒人做過的主張。
"""
from __future__ import annotations

from datetime import timezone

import pytest

from alpha.errors import ContractViolation
from alpha.fundamental import (
    ASSUMPTION_SCENARIOS, BASE_SCENARIO, DOWNSIDE_SCENARIO, OVERLAY_SCENARIOS,
    SCENARIO_LABELS, VARIANT_SCENARIO,
)
from tests.test_fundamental_model import _assumption

UTC = timezone.utc


def _downside(driver: str = "operating_margin_delta", scope: str = "mix_and_utilization",
              value: float = -0.06, **kw):
    return _assumption(driver, scope, value, created="2026-09-05T09:00:00+00:00",
                       scenario=DOWNSIDE_SCENARIO, **kw)


# ---------------------------------------------------------------------------
# 1. 型別層：與賭注**完全同一組**規則
# ---------------------------------------------------------------------------

def test_downside_is_registered_as_an_overlay_next_to_variant() -> None:
    """字彙加一個值就要加一條 payoff 算術——所以它必須在這裡被看見。"""
    assert ASSUMPTION_SCENARIOS == (BASE_SCENARIO, VARIANT_SCENARIO, DOWNSIDE_SCENARIO)
    assert OVERLAY_SCENARIOS == (VARIANT_SCENARIO, DOWNSIDE_SCENARIO)
    assert BASE_SCENARIO not in OVERLAY_SCENARIOS, "base 不是 overlay：它是被覆蓋的那一份"
    assert SCENARIO_LABELS[DOWNSIDE_SCENARIO] == "判斷錯了"


def test_downside_accepts_a_negative_value_on_a_core_driver_with_evidence() -> None:
    """下檔就是「同一條假設的另一個值」，值往下不改變它的身分。"""
    item = _downside()
    assert item.scenario == DOWNSIDE_SCENARIO
    assert item.value == pytest.approx(-0.06)
    assert item.supporting_refs, "沒有 supporting 證據的話下一條測試就白測了"


def test_downside_rejects_the_same_three_things_variant_rejects() -> None:
    """**對稱是 D2 的全部內容**：一邊要證據、另一邊隨便寫，就是 bear case 換個名字。

    第三條（至少一條 supporting 證據）就是「這不是 bear case」的那道閘門——
    bear case 的毛病不是它悲觀，是它指不出根據。
    """
    # ① 只能是核心 driver：稅率的差異是校準，不是主張
    with pytest.raises(ContractViolation) as tax:
        _downside("tax_rate", "total", 0.30, basis="heuristic_proxy")
    assert "核心 driver" in str(tax.value)

    # ② 必須 independent：抄公司指引或由共識反解的值，結構上不可能與市場不同
    with pytest.raises(ContractViolation) as derived:
        _downside(derivation="company_guidance")
    assert "independent" in str(derived.value)

    # ③ 必須指得出至少一條 **supporting** 證據——只引用校準用的共識不算。
    # 這一條就是「這不是 bear case」的閘門：bear case 的毛病不是它悲觀，是它指不出根據。
    consensus_ref = "engine_c://consensus_estimate/COHR/eps/2027-06-30"
    with pytest.raises(ContractViolation):
        _downside(refs=(), calibration_refs=(consensus_ref,))


def test_downside_valuation_assumption_also_needs_its_own_evidence() -> None:
    """倍數收縮也是一個主張：de-rating 說不出證據就是偏差，不是審慎（2026-09-09 原則）。

    ⚠ 這裡斷言的是**估值層也套 overlay 規則**，不是某一句錯誤訊息的措辭。
    """
    import inspect

    from alpha.valuation import contracts as vc

    src = inspect.getsource(vc)
    # ⚠ **正向斷言**：檢查 gate 長什麼樣，不是檢查某個字串「不存在」。
    # 第一版寫成 `"self.scenario == VARIANT_SCENARIO" not in src`，立刻誤報——
    # 那兩處命中是**文案的三元運算**（賭注／下檔用不同措辭），不是 gate。
    # 做一個會誤報的防呆來防止過度工程，本身就是過度工程（L16-4）。
    assert "if self.scenario in OVERLAY_SCENARIOS and not self.retracted:" in src,         "估值層的 gate 必須吃 OVERLAY_SCENARIOS——只擋 variant 會讓 downside 漏過去"


# ---------------------------------------------------------------------------
# 2. 同一段程式碼：不是兩份手寫
# ---------------------------------------------------------------------------

def test_both_scenarios_go_through_the_same_section_builder() -> None:
    """兩份各自手寫的渲染會在某次改動後悄悄長出不同的格，而使用者要並排讀它們。"""
    import inspect

    from briefing.alpha_view import builder

    src = inspect.getsource(builder)
    assert src.count("def _payoff_section(") == 1, "只能有一個 overlay section builder"
    assert "copy=_VARIANT_COPY" in src and "copy=_DOWNSIDE_COPY" in src
    # 兩個 copy 的欄位一一對應——少一個欄位就代表有一邊要走特例
    assert set(vars(builder._VARIANT_COPY).keys() if hasattr(builder._VARIANT_COPY, "__dict__")
               else builder._OverlayCopy.__dataclass_fields__.keys()) == \
           set(builder._OverlayCopy.__dataclass_fields__.keys())
    assert builder._DOWNSIDE_COPY.scenario == DOWNSIDE_SCENARIO
    assert builder._VARIANT_COPY.scenario == VARIANT_SCENARIO


def test_downside_is_not_what_it_says_it_is_not() -> None:
    """第一句必須逐字擋掉 bear case——那是這個 scenario 最容易被讀錯的方向。"""
    from briefing.alpha_view.builder import DOWNSIDE_IS_NOT

    assert any("bear case" in line for line in DOWNSIDE_IS_NOT)
    assert any("停損" in line or "出場" in line for line in DOWNSIDE_IS_NOT)
    assert any("機率" in line for line in DOWNSIDE_IS_NOT)


# ---------------------------------------------------------------------------
# 3. 兩種缺席分開，且不得互相頂替
# ---------------------------------------------------------------------------

def test_bet_abstention_does_not_stand_in_for_a_missing_downside() -> None:
    """「沒有可辯護的賭注」≠「說不出可辯護的下檔」——前者是不下注，後者是連認錯的門檻都畫不出來。"""
    from datetime import date as _date

    from alpha.abstention.contracts import ABSTENTION_SUBJECTS
    from briefing.alpha_view.sources import downside_absence, variant_absence

    assert ABSTENTION_SUBJECTS["bet"] == ("variant.overlay", "downside.overlay")

    from datetime import datetime as _dt

    from alpha.abstention.contracts import abstention_record, parse_abstention_record

    # ⚠ 用**真的** Abstention，不用假物件：假物件會漏掉 `created_on` 這類由型別自己
    # 導出的欄位，於是測試守的其實是我手寫的那份形狀（L17：機制只認得當初那個案例）。
    declared = parse_abstention_record(abstention_record(
        company_id="co:coherent", ticker="COHR", layer="bet", subject="variant.overlay",
        reason="這一檔的供應鏈結構還沒看懂，現在寫任何賭注都只是把猜測寫成數字",
        revisit_when="下一次法說會揭露客戶集中度時重看",
        created_at=_dt(2026, 9, 5, tzinfo=UTC)))

    today = _date(2026, 9, 18)
    # variant 那一側讀得到它
    v_reason, v_kind = variant_absence([declared], as_of=None, today=today)
    # downside 那一側**讀不到**——它問的不是同一個問題
    d_reason, d_kind = downside_absence([declared], as_of=None, today=today)
    assert d_kind == "not_yet_recorded", "variant 的 abstention 不得頂替 downside"
    assert "還沒寫" in d_reason
    assert (v_reason, v_kind) != (d_reason, d_kind)


def test_no_abstention_at_all_is_not_yet_recorded_on_both_sides() -> None:
    from datetime import date as _date

    from briefing.alpha_view.sources import downside_absence

    reason, kind = downside_absence([], as_of=None, today=_date(2026, 9, 18))
    assert kind == "not_yet_recorded"
    assert "不是 0" in reason


# ---------------------------------------------------------------------------
# 4. 端到端：同一條橋真的算得出「認錯時值多少」
# ---------------------------------------------------------------------------

def test_downside_runs_the_same_bridge_and_lands_below_base() -> None:
    """**驗收不是「函式回傳成功」，是「數字真的出現在下游」**（L13-1）。

    這一條走完整條鏈：downside 假設 → 同一個 bridge → 同一個 valuation → 同一個
    implied_return，並斷言它落在 base 之下。⚠ 斷言「低於 base」不是要求下檔一定是負的
    （那要看假設值），而是要求**同一條算術真的吃到了那個較差的假設**——若它悄悄沿用
    base，兩個數字會一模一樣，而畫面上會出現兩個相同的目標價卻標著不同的標籤。
    """
    from alpha.fundamental import build_fundamental_model
    from alpha.implied_return import build_implied_return
    from alpha.valuation import build_valuation
    from tests.test_fundamental_model import CONSENSUS, TODAY, _actuals, _full_set
    from tests.test_implied_return import TODAY as IR_TODAY, _horizon
    from tests.test_valuation_model import PRICE, _index, _multiple

    def _model(records, *, scenario):
        return build_fundamental_model(
            company_id="co:coherent", ticker="COHR", as_of=None, today=TODAY, actuals=_actuals(),
            actuals_reason=None, consensus=CONSENSUS, guidance=(), assumption_records=records,
            evidence_index=_index(), scenario=scenario)

    base = _full_set()
    down = _downside(value=-0.06)                      # base 是 +0.025，這裡往下 8.5pp
    base_model = _model(base, scenario=BASE_SCENARIO)
    down_model = _model([*base, down], scenario=DOWNSIDE_SCENARIO)

    assert down_model.scenario == DOWNSIDE_SCENARIO
    assert down_model.overrides == (down,), "downside 必須是 overlay：只覆蓋有差異的那一條"
    assert down_model.metrics["revenue"].value == base_model.metrics["revenue"].value, "營收沒被覆蓋"
    assert down_model.metrics["eps"].value < base_model.metrics["eps"].value
    # base 一個位元不變——寫下檔不會動到基準（既有 ledger 的 id 也因此不變）
    assert base_model.metrics["eps"].value == _model(base, scenario=BASE_SCENARIO).metrics["eps"].value

    valuation = build_valuation(
        company_id="co:coherent", ticker="COHR", as_of=None, today=IR_TODAY, fundamental=down_model,
        fundamental_reason=None, assumption_records=[_multiple(value_date_convention="target_period_end")],
        evidence_index=_index(), price=PRICE, scenario=DOWNSIDE_SCENARIO)
    assert valuation.fair_value == pytest.approx(down_model.metrics["eps"].value * 25.0)

    result = build_implied_return(
        company_id="co:coherent", ticker="COHR", as_of=None, today=IR_TODAY, valuation=valuation,
        valuation_reason=None, horizon_records=[_horizon()], evidence_index=_index(), price=PRICE,
        eps_comparison=down_model.comparisons.get("eps"))
    assert result.is_known
    assert result.price_return == pytest.approx(valuation.fair_value / PRICE.value - 1)


def test_written_but_rejected_never_looks_like_not_yet_written() -> None:
    """**「還沒寫」與「寫了但一條都沒生效」是相反的結論，不得共用一句話**（L12）。

    事發 2026-09-19（[631] 寫 COHR 的 downside 時親身踩到）：那筆假設引用了
    `graph://edge/co:sumitomo_electric/supplies_to/co:nvidia`——那條邊確實存在且
    externally_corroborated，但**不在 COHR 的 ResearchContext 內**（context 以本檔為中心建），
    於是整筆被判 `unresolved_evidence` 拒用。`downside` section 仍然 `status=available`、
    數字逐位等於 base、`overrides` 空——**看起來就像「還沒寫」**。
    被拒的理由 `selection.rejected` 一直都在，只是沒有人把它講出來（L16）。
    """
    from alpha.fundamental import build_fundamental_model
    from tests.test_fundamental_model import CONSENSUS, TODAY, _actuals, _full_set
    from tests.test_valuation_model import _index

    def _model(records):
        return build_fundamental_model(
            company_id="co:coherent", ticker="COHR", as_of=None, today=TODAY, actuals=_actuals(),
            actuals_reason=None, consensus=CONSENSUS, guidance=(), assumption_records=records,
            evidence_index=_index(), scenario=DOWNSIDE_SCENARIO)

    base = _full_set()

    # (a) 真的沒寫 → 那句話要說「還沒寫」
    nothing = _model(base)
    assert nothing.overrides == ()
    said_nothing = "｜".join(nothing.warnings)
    assert "還沒寫" in said_nothing

    # (b) 寫了，但引用一個不在 evidence_index 裡的 ref → **不得**說「還沒寫」
    ghost = _downside(value=-0.06, refs=("graph://edge/co:ghost/supplies_to/co:nobody",))
    rejected = _model([*base, ghost])
    assert rejected.overrides == (), "前提：這一筆確實沒生效"
    said_rejected = "｜".join(rejected.warnings)
    # ⚠ 這裡**不能**斷言「還沒寫」這三個字不出現——文案本身含一句否定（「這不是『還沒寫』」），
    # 用 `not in` 會把正確的訊息判成錯的。要驗的是**它下了哪個結論**，不是它有沒有提到那個詞。
    assert "寫了而沒被採用" in said_rejected, said_rejected
    assert "寫了而沒被採用" not in said_nothing, said_nothing
    # 被拒的那一筆與它的理由都要講出來，否則寫的人無從知道是哪個字錯了
    assert ghost.assumption_id in said_rejected, said_rejected
    assert "unresolved_evidence" in said_rejected, said_rejected

    # (c) 兩句話不得是同一句
    assert said_nothing != said_rejected
