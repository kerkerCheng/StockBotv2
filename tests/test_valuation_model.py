"""Valuation Model v1（`alpha/valuation`，Phase 2 Step 1）的測試——純邏輯＋read model 整合。

守的是 Step 1 的 12 條驗收：
1. explicit multiple × internal EPS → deterministic fair value；2. multiple 缺 → missing，不補 default；
3. internal EPS 缺 → fair value missing；4. 估值假設 supersede → 只用新版；5. historical as-of 不偷看未來假設；
6. GAAP／non-GAAP／期間不合不得混；7. EPS 變 → fair value 確定性重算；8. multiple 變 → 同上；
9. price-only → fair value 不變（gap 才變）；10. builder／renderer 不含估值公式；11. 不支援的公司 → 誠實 missing；
12. refresh state 正確傳播（EPS／假設／supporting evidence／price-only 四種）。
"""
from __future__ import annotations

import ast
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.fundamental import FiscalPeriod
from alpha.fundamental.assumptions import assumption_record, parse_assumption_record
from alpha.refresh import (
    ARTIFACT_FAIR_VALUE, ARTIFACT_FAIR_VALUE_GAP, ARTIFACT_VALUATION_ASSUMPTION, CURRENT, GRAPH_EDGE,
    MARKET_PRICE, OPERATING_ASSUMPTION, RECALCULATE, REVIEW_REQUIRED, VALUATION_ASSUMPTION, ChangeEvent,
    artifacts_from_model, artifacts_from_valuation, end_of_day, resolve_refresh,
)
from alpha.valuation import (
    FAIR_VALUE_FORMULA, CurrentPrice, ValuationAssumption, build_valuation,
    parse_valuation_assumption_record, valuation_assumption_record,
)
from tests.test_fundamental_model import ACT_REF, GRAPH_REF, INDEX, TARGET, TODAY, _assumption, _full_set, _run

UTC = timezone.utc
SNAP = "engine_c://financial_snapshot/COHR"
EDGE = GRAPH_REF.ref
CREATED = datetime(2026, 9, 6, 8, 0, tzinfo=UTC)
PRICE = CurrentPrice(value=281.86, bar_date=date(2026, 9, 4), unit="USD", evidence_refs=(SNAP,))
ROOT = Path(__file__).resolve().parents[1]


def _index():
    return {**INDEX, ACT_REF.ref: ACT_REF}


def _multiple(value: float = 25.0, *, basis: str = "session_judgment", accounting_basis: str = "non_gaap",
              period_end: date = TARGET.end, refs=(EDGE, ACT_REF.ref), created: datetime = CREATED,
              **kw) -> ValuationAssumption:
    record = valuation_assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=period_end, value=value, basis=basis,
        accounting_basis=accounting_basis, rationale=f"test target_pe {value}", evidence_refs=list(refs),
        created_at=created, **kw)
    return parse_valuation_assumption_record(record)


def _valuation(records=None, *, model=None, as_of: date | None = None, today: date = date(2026, 9, 7),
               price: CurrentPrice = PRICE, model_reason: str | None = None):
    if model is None and model_reason is None:
        model = _run(as_of=as_of, today=today, index=_index())
    return build_valuation(
        company_id="co:coherent", ticker="COHR", as_of=as_of, today=today, fundamental=model,
        fundamental_reason=model_reason, assumption_records=[_multiple()] if records is None else records,
        evidence_index=_index(), price=price)


# ---------------------------------------------------------------------------
# 1–3. 算術、缺倍數、缺 EPS
# ---------------------------------------------------------------------------

def test_explicit_multiple_times_internal_eps_is_a_deterministic_fair_value() -> None:
    model = _run(index=_index())
    result = _valuation(model=model)
    eps = model.metrics["eps"].value
    assert result.status == "available" and result.method == "forward_earnings_multiple"
    assert result.fair_value == pytest.approx(eps * 25.0)
    assert result.formula == FAIR_VALUE_FORMULA["forward_earnings_multiple"]
    assert result.calculation == "deterministic" and result.input_dependency == "session_judgment"
    assert result.currency == "USD" and result.accounting_basis == "non_gaap"
    assert result.target_period == TARGET
    assert set(result.assumption_ids) == set(model.metrics["eps"].assumption_ids) | {result.assumptions[0].assumption_id}
    kinds = {s.key: (s.kind, s.basis) for s in result.steps}
    assert kinds["internal_eps"] == ("fundamental_input", "deterministic")
    assert kinds["target_pe"] == ("assumption", "session_judgment")
    assert kinds["fair_value"] == ("derived", "deterministic")
    again = _valuation(model=model)
    assert again.fair_value == result.fair_value and again.digest == result.digest


def test_missing_multiple_is_missing_not_a_default() -> None:
    result = _valuation(records=[])
    assert result.status == "missing" and result.fair_value is None and result.input_dependency is None
    assert "不補預設" in (result.reason or "")
    assert result.fundamental_input is not None and result.fundamental_input.is_known    # EPS 仍在
    assert result.gap.status == "fair_value_missing" and result.gap.relative_gap is None
    assert result.selection.input_count == 0
    # 有紀錄但都被拒（證據解析不到）→ 一樣 missing，且理由帶計數
    unresolved = _multiple(refs=("graph://gone",))
    result2 = _valuation(records=[unresolved])
    assert result2.status == "missing" and "unresolved_evidence" in (result2.reason or "")


def test_missing_internal_eps_makes_fair_value_missing() -> None:
    partial = _run([a for a in _full_set() if a.scope != "Industrial"], index=_index())
    assert partial.metrics["eps"].value is None
    result = _valuation(model=partial)
    assert result.status == "missing" and result.fair_value is None
    assert "缺內部營收" in (result.reason or "") and "不是 0" in (result.reason or "")
    assert "Industrial" in (partial.metrics["revenue"].reason or "")          # 根因住營收那格
    assert result.assumptions and result.assumptions[0].value == 25.0     # 倍數存在也不能算
    none = _valuation(model=None, model_reason="provider 無 fiscal 能力")
    assert none.status == "missing" and "provider 無 fiscal 能力" in (none.reason or "")


# ---------------------------------------------------------------------------
# 4–5. supersede 只用新版；historical as-of 不偷看未來
# ---------------------------------------------------------------------------

def test_superseded_multiple_is_historical_and_only_the_newest_is_used() -> None:
    old = _multiple(25.0)
    new = _multiple(22.0, created=CREATED + timedelta(days=1), supersedes_id=old.assumption_id)
    model = _run(index=_index())
    result = _valuation([old, new], model=model)
    assert result.assumptions == (new,)
    assert result.fair_value == pytest.approx(model.metrics["eps"].value * 22.0)
    assert dict(result.selection.reasons) == {"superseded": 1}
    # 撤回最新一筆 → 沒有生效假設（撤回不讓舊值復活）
    retract = parse_valuation_assumption_record(valuation_assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, value=22.0, basis="session_judgment",
        accounting_basis="non_gaap", rationale="retracted", evidence_refs=[EDGE], supersedes_id=new.assumption_id,
        retracted=True, created_at=CREATED + timedelta(days=2)))
    gone = _valuation([old, new, retract], model=model, today=date(2026, 9, 10))
    assert gone.status == "missing" and "retracted=1" in (gone.reason or "")


def test_historical_as_of_does_not_see_future_valuation_assumptions() -> None:
    model_then = _run(as_of=date(2026, 9, 5), index=_index())        # 營運假設寫於 09-05 08:00 → 在
    assert model_then.metrics["eps"].is_known
    then = _valuation([_multiple(created=CREATED)], model=model_then, as_of=date(2026, 9, 5))
    assert then.status == "missing" and dict(then.selection.reasons) == {"created_after_as_of": 1}
    later = _valuation([_multiple(created=CREATED)], model=_run(as_of=date(2026, 9, 6), index=_index()),
                       as_of=date(2026, 9, 6))
    assert later.status == "available"
    # 估值視角與 fundamental 視角不符 → 拒用（INV-6）
    mismatch = _valuation([_multiple()], model=_run(index=_index()), as_of=date(2026, 9, 6))
    assert mismatch.status == "missing" and "INV-6" in (mismatch.reason or "")


# ---------------------------------------------------------------------------
# 6. 口徑與期間是身分
# ---------------------------------------------------------------------------

def test_basis_and_period_mismatch_never_multiply() -> None:
    model = _run(index=_index())                                        # 內部 EPS 是 non_gaap FY2027
    gaap = _valuation([_multiple(accounting_basis="gaap")], model=model)
    assert gaap.status == "missing" and "GAAP／non-GAAP 不得混算" in (gaap.reason or "")
    fy28 = _valuation([_multiple(period_end=TARGET.shifted(1).end)], model=model)
    assert fy28.status == "missing" and dict(fy28.selection.reasons) == {"other_period": 1}
    with pytest.raises(ContractViolation, match="accounting_basis"):
        _multiple(accounting_basis="unverified")
    with pytest.raises(ContractViolation, match="provenance 循環"):
        _multiple(refs=("engine_c://consensus_estimate/COHR/eps/2027-06-30",))
    with pytest.raises(ContractViolation, match="未登記"):
        _multiple(method="dcf")


# ---------------------------------------------------------------------------
# 7–9. EPS 變／倍數變 → 重算；price-only → fair value 不變
# ---------------------------------------------------------------------------

def test_changing_eps_or_multiple_recalculates_fair_value_deterministically() -> None:
    base_model = _run(index=_index())
    base = _valuation(model=base_model)
    higher_growth = [replace(a, value=0.70) if a.scope == "Datacenter & Communications" else a for a in _full_set()]
    bumped_model = _run(higher_growth, index=_index())
    bumped = _valuation(model=bumped_model)
    assert bumped.fair_value == pytest.approx(bumped_model.metrics["eps"].value * 25.0)
    assert bumped.fair_value > base.fair_value
    remultiplied = _valuation([_multiple(30.0)], model=base_model)
    assert remultiplied.fair_value == pytest.approx(base_model.metrics["eps"].value * 30.0)
    assert remultiplied.fair_value / base.fair_value == pytest.approx(30.0 / 25.0)
    # 倍數敏感度：×1.01 → fair value +1%
    own = next(s for s in remultiplied.sensitivities if s.assumption_id == remultiplied.assumptions[0].assumption_id)
    assert own.fair_value_relative == pytest.approx(0.01)


def test_price_only_change_moves_the_gap_but_not_fair_value() -> None:
    model = _run(index=_index())
    a = _valuation(model=model, price=PRICE)
    b = _valuation(model=model, price=replace(PRICE, value=300.0))
    assert a.fair_value == b.fair_value
    assert a.gap.relative_gap == pytest.approx(a.fair_value / 281.86 - 1)
    assert b.gap.relative_gap == pytest.approx(a.fair_value / 300.0 - 1)
    assert a.gap.implied_multiple_at_price == pytest.approx(281.86 / model.metrics["eps"].value)
    assert a.gap.relative_gap == pytest.approx(25.0 / a.gap.implied_multiple_at_price - 1)
    # 單位不同／不明 → 不算 gap（報價單位 ≠ 結算幣別，不猜）
    gbp = _valuation(model=model, price=replace(PRICE, unit="GBp"))
    assert gbp.gap.status == "incompatible_unit" and gbp.gap.relative_gap is None and gbp.fair_value == a.fair_value
    unknown = _valuation(model=model, price=replace(PRICE, unit=None))
    assert unknown.gap.status == "unverified_unit"
    no_price = _valuation(model=model, price=CurrentPrice(value=None, bar_date=None, unit="USD", evidence_refs=(), reason="無快照"))
    assert no_price.gap.status == "price_missing" and no_price.fair_value == a.fair_value


# ---------------------------------------------------------------------------
# 12. refresh state 傳播（純 refresh 引擎）
# ---------------------------------------------------------------------------

def _artifacts(valuation, model, records=()):
    build_at = end_of_day(date(2026, 9, 7))
    return (artifacts_from_model(model, build_at=build_at)
            + artifacts_from_valuation(valuation, build_at=build_at, assumption_records=records,
                                       base_period_end=model.base_period.end))


def _resolve(changes, *, valuation, model, records=(), today=date(2026, 9, 8)):
    return resolve_refresh(ticker="COHR", company_id="co:coherent", artifacts=_artifacts(valuation, model, records),
                           changes=changes, today=today)


def test_refresh_states_propagate_through_fair_value_and_gap() -> None:
    model = _run(index=_index())
    valuation = _valuation(model=model)
    va_id = valuation.assumptions[0].assumption_id
    later = datetime(2026, 9, 8, 12, tzinfo=UTC)
    # price-only → gap recalculate、fair value current、估值假設 current
    price = _resolve([ChangeEvent(change_type=MARKET_PRICE, ticker="COHR", authority="t", changed_ref=SNAP,
                                  observed_at=later, material_fields=("price",))], valuation=valuation, model=model)
    assert price.artifact(f"{ARTIFACT_FAIR_VALUE}:fair_value").state == CURRENT
    assert price.artifact(f"{ARTIFACT_FAIR_VALUE_GAP}:fair_value_gap").state == RECALCULATE
    assert price.artifact(f"{ARTIFACT_VALUATION_ASSUMPTION}:{va_id}").state == CURRENT
    # 內部 EPS 的營運假設被取代 → fair value 與 gap recalculate
    dc = next(a.assumption_id for a in model.assumptions if a.scope == "Datacenter & Communications")
    eps_changed = _resolve([ChangeEvent(change_type=OPERATING_ASSUMPTION, ticker="COHR", authority="t",
                                        changed_ref="oa_new", related_refs=(dc,), observed_at=later)],
                           valuation=valuation, model=model)
    assert eps_changed.artifact(f"{ARTIFACT_FAIR_VALUE}:fair_value").state == RECALCULATE
    assert eps_changed.artifact(f"{ARTIFACT_FAIR_VALUE_GAP}:fair_value_gap").state == RECALCULATE
    # 估值假設被取代 → fair value recalculate；營運假設不動
    va_changed = _resolve([ChangeEvent(change_type=VALUATION_ASSUMPTION, ticker="COHR", authority="t",
                                       changed_ref="va_new", related_refs=(va_id,), observed_at=later)],
                          valuation=valuation, model=model)
    assert va_changed.artifact(f"{ARTIFACT_FAIR_VALUE}:fair_value").state == RECALCULATE
    assert va_changed.artifact(f"operating_assumption:{dc}").state == CURRENT
    assert va_changed.artifact("modeled_metric:eps").state == CURRENT
    # 估值假設的 supporting evidence 變了 → 假設 review_required → fair value／gap 不得再當 current（傳播現形）
    edge = _resolve([ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", authority="t", changed_ref=EDGE,
                                 observed_at=later, material_fields=("substitutability",), detail="sub 5 → 3")],
                    valuation=valuation, model=model)
    assert edge.artifact(f"{ARTIFACT_VALUATION_ASSUMPTION}:{va_id}").state == REVIEW_REQUIRED
    fv = edge.artifact(f"{ARTIFACT_FAIR_VALUE}:fair_value")
    assert fv.state == REVIEW_REQUIRED and f"{ARTIFACT_VALUATION_ASSUMPTION}:{va_id}" in fv.propagated_from
    assert edge.artifact(f"{ARTIFACT_FAIR_VALUE_GAP}:fair_value_gap").state == REVIEW_REQUIRED
    # 只引用基期觀測的估值假設不因 graph edge 動搖
    obs_only = _valuation([_multiple(refs=(ACT_REF.ref,))], model=model)
    calm = _resolve([ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", authority="t", changed_ref=EDGE,
                                 observed_at=later, material_fields=("substitutability",))],
                    valuation=obs_only, model=model)
    assert calm.artifact(f"{ARTIFACT_VALUATION_ASSUMPTION}:{obs_only.assumptions[0].assumption_id}").state == CURRENT
    # 歷史紀錄：被取代的估值假設 superseded
    old = _multiple(25.0)
    new = _multiple(22.0, created=CREATED + timedelta(days=1), supersedes_id=old.assumption_id)
    two = _valuation([old, new], model=model)
    hist = _resolve([], valuation=two, model=model, records=[old, new])
    assert hist.artifact(f"{ARTIFACT_VALUATION_ASSUMPTION}:{old.assumption_id}").state == "superseded"


# ---------------------------------------------------------------------------
# 10–11. read model：builder／renderer 不含公式；不支援的公司誠實 missing
# ---------------------------------------------------------------------------

def test_builder_and_renderer_copy_fair_value_without_computing_it() -> None:
    from briefing.alpha_view import render_alpha_investment_view_markdown
    from briefing.alpha_view.contracts import CAP_DETERMINISTIC_FAIR_VALUE
    from tests.test_alpha_investment_view import _view

    model = _run(index=_index())
    valuation = _valuation(model=model)
    view = _view(fundamental_model=model, valuation=valuation, valuation_records=list(valuation.assumptions))
    section = view.valuation
    assert section.meta.status == "available" and section.meta.capability == CAP_DETERMINISTIC_FAIR_VALUE
    assert section.fair_value.value == valuation.fair_value                   # 逐位相同
    assert section.fair_value.method.startswith(FAIR_VALUE_FORMULA["forward_earnings_multiple"])
    assert section.fair_value.dependencies["price_in_formula"] is False
    assert section.fair_value.dependencies["input_dependency"] == "session_judgment"
    assert section.fair_value_gap.value["relative_gap"] == valuation.gap.relative_gap
    assert section.current_price.basis == "observation" and section.current_price.authority == "engine_c://financial_snapshots"
    assert section.assumptions[0].basis == "session_judgment" and section.assumptions[0].dependencies["assumption_id"].startswith("va_")
    assert view.capability_map()["valuation"]["status"] == "available"
    assert view.scenarios.target_valuation.value == valuation.fair_value       # 單點 fair value 照抄
    # Step 2／Step 3：兩層都**有能力**了，所以沒 horizon／沒判準是 missing（不是 not_modeled）
    assert view.implied_return.meta.status == "missing" and view.entry_logic.meta.status == "missing"
    assert "expected_return" not in {d.key for d in section.trace}
    assert view.valuation.value_date.status == "missing"                       # 未宣告 value_date_convention → 不猜
    # 竄改：builder 只抄，不重算
    tampered = replace(valuation, fair_value=123.456)
    tview = _view(fundamental_model=model, valuation=tampered, valuation_records=list(valuation.assumptions))
    assert tview.valuation.fair_value.value == 123.456
    assert tview.valuation.fair_value_gap.value["fair_value"] == 123.456
    text = render_alpha_investment_view_markdown(view)
    assert "## 13. 估值" in text and "gap 不是什麼" in text and "不是 expected return" in text
    fv_line = next(l for l in text.splitlines() if l.startswith("- Fair value（FY2027"))
    assert f"{valuation.fair_value:,.2f}" in fv_line
    # import／token 掃描：組裝層與 renderer 不得 import 估值算術、不得自己寫 × target_pe
    for rel in ("briefing/alpha_view/builder.py", "briefing/alpha_view/render.py"):
        source = (ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        assert "alpha.valuation.model" not in imported and "alpha.valuation" not in imported, rel
        assert "build_valuation" not in source and "× target_pe" not in source and "* target_pe" not in source, rel
        assert ".value * " not in source and "eps * " not in source, rel


def test_unsupported_company_is_honest_missing_in_the_view_and_card() -> None:
    from briefing.alpha_view import compact_card, render_alpha_cards
    from tests.test_alpha_investment_view import _view

    view = _view(fundamental_model=None, fundamental_model_reason="provider 無 fiscal 能力",
                 valuation=None, valuation_reason="本次未執行 valuation model（無內部 EPS）")
    assert view.valuation.meta.status == "missing" and view.valuation.fair_value.value is None
    assert "無內部 EPS" in (view.valuation.meta.reason or "")
    assert view.capability_map()["valuation"]["status"] == "missing"
    card = compact_card(view)
    assert card["valuation"]["status"] == "missing" and card["valuation"]["fair_value"] is None
    assert card["valuation"]["relative_gap"] is None and card["valuation"]["reason"]
    assert "valuation" not in card["not_modeled"]                             # 有能力沒資料 ≠ 尚未建模
    row = next(l for l in render_alpha_cards([card]) if l.startswith("| co:coherent"))
    assert "| 未知（本次未執行 valuation model" in row
    # 有 valuation 但 EPS 缺：section missing、現價仍呈現
    partial = _run([a for a in _full_set() if a.scope != "Industrial"], index=_index())
    view2 = _view(fundamental_model=partial, valuation=_valuation(model=partial))
    assert view2.valuation.meta.status == "missing" and view2.valuation.current_price.is_known
    payload = json.loads(json.dumps(view2.to_dict(), ensure_ascii=False))
    assert payload["valuation"]["fair_value"]["value"] is None


def test_view_refresh_state_reaches_the_valuation_datums_and_card() -> None:
    from briefing.alpha_view import compact_card
    from tests.test_alpha_investment_view import _view

    model = _run(index=_index())
    valuation = _valuation(model=model)
    va_id = valuation.assumptions[0].assumption_id
    day = date(2026, 9, 7)                                              # 估值假設寫於 09-06，view 要晚於它
    edge = ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", company_id="co:coherent",
                       authority="engine_a://graph_research_provider", changed_ref=EDGE,
                       observed_at=datetime(2026, 9, 7, 23, 59, 59, tzinfo=UTC), material_fields=("substitutability",))
    view = _view(fundamental_model=model, valuation=valuation, valuation_records=list(valuation.assumptions),
                 refresh_changes=[edge], today=day)
    assert view.valuation.assumptions[0].status == "review_required"
    assert view.valuation.fair_value.status == "review_required"
    # 那條邊同時是 D&C 營運假設與估值假設的 supporting——兩條都傳播到 fair value，且都指名
    assert f"valuation_assumption:{va_id}" in view.valuation.fair_value.dependencies["refresh_propagated_from"]
    assert any(p.startswith("operating_assumption:") for p in view.valuation.fair_value.dependencies["refresh_propagated_from"])
    assert view.valuation.meta.status == "review_required"
    assert compact_card(view)["valuation"]["status"] == "review_required"
    # price-only：fair value available、gap recalculate 也是 available（確定性、每次重算）
    price = ChangeEvent(change_type=MARKET_PRICE, ticker="COHR", company_id="co:coherent",
                        authority="engine_c://financial_snapshots", changed_ref=SNAP,
                        observed_at=datetime(2026, 9, 7, 23, 59, 59, tzinfo=UTC), material_fields=("price",))
    quiet = _view(fundamental_model=model, valuation=valuation, valuation_records=list(valuation.assumptions),
                  refresh_changes=[price], today=day)
    assert quiet.valuation.fair_value.status == "available"
    assert quiet.valuation.fair_value.dependencies["refresh_state"] == "current"
    assert quiet.valuation.fair_value_gap.dependencies["refresh_state"] == "recalculate"


def test_valuation_ledger_round_trips_and_rejects_duplicates(tmp_path: Path) -> None:
    from alpha.providers.valuation_assumptions import (
        append_valuation_assumption_record, read_valuation_assumption_records,
    )

    record = valuation_assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, value=25.0, basis="session_judgment",
        accounting_basis="non_gaap", rationale="r", evidence_refs=[EDGE],
        calibration_refs=["engine_c://consensus_estimate/COHR/eps/2027-06-30"], created_at=CREATED)
    path = append_valuation_assumption_record(record, directory=tmp_path)
    assert path.name == "COHR.jsonl"
    loaded, errors = read_valuation_assumption_records("COHR", directory=tmp_path)
    assert errors == [] and loaded[0].assumption_id == record["assumption_id"]
    assert loaded[0].calibration_refs == ("engine_c://consensus_estimate/COHR/eps/2027-06-30",)
    with pytest.raises(ContractViolation, match="重複"):
        append_valuation_assumption_record(record, directory=tmp_path)
    with pytest.raises(ContractViolation, match="supersedes_id"):
        append_valuation_assumption_record(valuation_assumption_record(
            company_id="co:coherent", ticker="COHR", period_end=TARGET.end, value=20.0, basis="session_judgment",
            accounting_basis="non_gaap", rationale="r", evidence_refs=[EDGE], supersedes_id="va_nope",
            created_at=CREATED), directory=tmp_path)
    # 壞行不靜默：計入 parse_errors
    path.write_text(path.read_text(encoding="utf-8") + '{"period_end": "2027-06-30"}\n', encoding="utf-8")
    loaded2, errors2 = read_valuation_assumption_records("COHR", directory=tmp_path)
    assert len(loaded2) == 1 and len(errors2) == 1


def test_valuation_core_never_imports_io_or_llm_clients() -> None:
    forbidden = {"anthropic", "openai", "requests", "httpx", "neo4j", "yfinance", "engine_c", "decision_lab",
                 "sqlite3", "subprocess", "briefing"}
    for path in (ROOT / "alpha" / "valuation").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
        assert not (roots & forbidden), (path, roots & forbidden)



# ---------------------------------------------------------------------------
# P6（2026-09-09）：ev_to_sales——虧損公司的第二種方法
# ---------------------------------------------------------------------------

def _ev_multiple(value: float = 8.0, *, created: datetime = CREATED, refs=(EDGE, ACT_REF.ref), **kw):
    from alpha.valuation import parse_valuation_assumption_record, valuation_assumption_record

    record = valuation_assumption_record(
        company_id="co:coherent", ticker="COHR", period_end=TARGET.end, value=value, basis="session_judgment",
        accounting_basis="not_applicable", rationale=f"test target_ev_to_sales {value}", evidence_refs=list(refs),
        created_at=created, method="ev_to_sales", parameter="target_ev_to_sales", **kw)
    return parse_valuation_assumption_record(record)


def _balance(debt: float | None = 3_540_000_000.0, cash: float | None = 1_990_000_000.0):
    from alpha.valuation import BalanceSheetInput

    return BalanceSheetInput(total_debt=debt, cash_and_equivalents=cash, as_of=PRICE.bar_date, evidence_refs=(SNAP,),
                             reason=None if (debt is not None and cash is not None) else "快照缺負債或現金")


def test_ev_to_sales_fair_value_is_revenue_times_multiple_minus_net_debt_per_share() -> None:
    model = _run(index=_index())
    result = build_valuation(
        company_id="co:coherent", ticker="COHR", as_of=None, today=date(2026, 9, 7), fundamental=model,
        fundamental_reason=None, assumption_records=[_ev_multiple(8.0)], evidence_index=_index(), price=PRICE,
        method="ev_to_sales", balance=_balance())
    revenue = model.metrics["revenue"].value
    shares = next(a.value for a in model.assumptions if a.driver == "diluted_shares")
    assert result.status == "available" and result.method == "ev_to_sales"
    assert result.fair_value == pytest.approx((revenue * 8.0 - (3_540_000_000.0 - 1_990_000_000.0)) / shares)
    assert result.formula == FAIR_VALUE_FORMULA["ev_to_sales"]
    keys = {s.key: (s.kind, s.basis) for s in result.steps}
    assert keys["internal_revenue"] == ("fundamental_input", "deterministic")
    assert keys["net_debt"] == ("fundamental_input", "observation")
    assert keys["diluted_shares"][0] == "assumption"
    assert result.gap.implied_multiple_at_price is None            # 本益比診斷對 EV/S 無定義
    assert result.input_dependency == "session_judgment"
    assert len(result.sensitivities) == 1 and result.sensitivities[0].driver.endswith("target_ev_to_sales")


def test_ev_to_sales_never_fills_missing_net_debt_or_shares_with_zero() -> None:
    model = _run(index=_index())
    common = dict(company_id="co:coherent", ticker="COHR", as_of=None, today=date(2026, 9, 7), fundamental=model,
                  fundamental_reason=None, assumption_records=[_ev_multiple(8.0)], evidence_index=_index(),
                  price=PRICE, method="ev_to_sales")
    no_balance = build_valuation(**common, balance=None)
    assert no_balance.status == "missing" and no_balance.absence_kind == "provider_missing"
    assert "淨負債" in (no_balance.reason or "") and "不是 0" in (no_balance.reason or "")
    half = build_valuation(**common, balance=_balance(cash=None))
    assert half.status == "missing" and half.absence_kind == "provider_missing"
    no_shares_model = _run([a for a in _full_set() if a.driver != "diluted_shares"], index=_index())
    no_shares = build_valuation(**{**common, "fundamental": no_shares_model}, balance=_balance())
    assert no_shares.status == "missing" and no_shares.absence_kind == "upstream_unavailable"
    assert "diluted_shares" in (no_shares.reason or "")


def test_ev_to_sales_assumption_must_be_not_applicable_basis_and_pe_message_points_to_it() -> None:
    from alpha.valuation import parse_valuation_assumption_record, valuation_assumption_record

    with pytest.raises(ContractViolation, match="not_applicable"):
        parse_valuation_assumption_record(valuation_assumption_record(
            company_id="co:coherent", ticker="COHR", period_end=TARGET.end, value=8.0, basis="session_judgment",
            accounting_basis="non_gaap", rationale="x", evidence_refs=[EDGE, ACT_REF.ref], created_at=CREATED,
            method="ev_to_sales", parameter="target_ev_to_sales"))
    from alpha.valuation.contracts import method_applicability

    msg = method_applicability("forward_earnings_multiple", -0.5) or ""
    assert "ev_to_sales" in msg and "target_ev_to_sales" in msg
    assert method_applicability("ev_to_sales", 0.0) is not None
    assert method_applicability("ev_to_sales", 1.0) is None


def test_pe_path_is_unchanged_by_the_new_method() -> None:
    """既有 COHR 本益比法的 baseline 一格都不動（P6 是加方法，不是改方法）。"""
    model = _run(index=_index())
    result = _valuation(model=model)
    assert result.method == "forward_earnings_multiple"
    assert result.fair_value == pytest.approx(model.metrics["eps"].value * 25.0)
    assert result.gap.implied_multiple_at_price is not None
    assert {s.key for s in result.steps}.isdisjoint({"net_debt", "diluted_shares"})


def test_read_model_switches_to_ev_to_sales_only_when_pe_is_abstained_or_not_applicable(monkeypatch) -> None:
    """2026-09-09 SOI.PA：本益比法被 append-only Abstention 宣告「刻意不主張」（谷底年 EPS 無可錨定倍數）且 ledger
    有 EV/S 假設 → read model 改跑 EV/S。只是「還沒寫 target_pe」**不**切——方法選擇是判斷，要由 abstention 明示。"""
    from alpha.abstention import abstention_record, parse_abstention_record
    from alpha.identity import CompanyId, Ticker
    from briefing.alpha_view import sources
    from tests.test_alpha_investment_view import _build

    build = _build()
    model = _run(today=date(2026, 9, 7), index=_index())          # abstention 建於 09-06，視角日要在其後
    ev = _ev_multiple(8.0)
    abstained = parse_abstention_record(abstention_record(
        company_id="co:coherent", ticker="COHR", layer="valuation", subject="forward_earnings_multiple.target_pe",
        period_end=TARGET.end, reason="FY2027 是谷底年：現價對內部 FY2027 EPS 超過 200 倍，市場錨在 FY2028，本益比法套在谷底 EPS 上沒有可錨定的倍數，任何倍數產出的 gap 都只反映倍數本身", revisit_when="FY2027 實際公布、目標期間 rollover 到 FY2028 後重評；每季業績後核查",
        created_at=CREATED))
    identity = {"market_currency": "USD", "market_quote_unit": "USD"}
    common = dict(as_of=None, today=date(2026, 9, 7), identity=identity)
    monkeypatch.setattr(sources.valuation_ledger, "read_valuation_assumption_records", lambda t: ([ev], []))

    monkeypatch.setattr(sources.abstention_ledger, "read_abstention_records", lambda t: ([abstained], []))
    result, reason, _ = sources._valuation_model(  # noqa: SLF001
        build, model, None, Ticker("COHR"), CompanyId("co:coherent"), **common)
    assert reason is None and result is not None and result.method == "ev_to_sales"

    monkeypatch.setattr(sources.abstention_ledger, "read_abstention_records", lambda t: ([], []))
    untouched, _, _ = sources._valuation_model(  # noqa: SLF001
        build, model, None, Ticker("COHR"), CompanyId("co:coherent"), **common)
    assert untouched.method == "forward_earnings_multiple"
    assert not untouched.is_known and untouched.absence_kind == "not_yet_recorded"
