"""缺席語意（Step 5 語意債 A／B）：**「沒有值」是至少六種不同的事。**

事發（2026-09-07 Coverage Pilot）：6324.T 的估值 blocker 逐字是「尚未寫入任何估值假設」，
而真實狀態是研究結論「126x 錨不住任何可辯護的倍數，所以不寫」。兩種語意共用一句話（L12），
下一個讀者——包括 APP 的使用者——無從分辨「還沒做」與「這已經是答案」。

本檔守三件事：
1. **字彙是封閉的**，且 `status → kind` 的預設是**查表**不是推論。
2. **`Abstention` 結構上不可能攜帶數字**——不能用它偷渡一個估值。
3. **模型層自己宣告走了哪個分支**，消費端不必 parse 散文（L16）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, fields
from datetime import date, datetime, timezone

import pytest

from alpha.absence import (
    ABSENCE_KINDS, DEFAULT_ABSENCE_KIND, SETTLED_ABSENCE_KINDS, AbsenceVocabularyError,
    check_absence_kind, default_absence_kind,
)
from alpha.abstention.contracts import (
    ABSTENTION_LAYERS, ABSTENTION_SUBJECTS, FORBIDDEN_VALUE_TOKENS, Abstention,
    abstention_record, parse_abstention_record, select_abstention,
)
from alpha.errors import ContractViolation
from alpha.providers.abstentions import append_abstention_record, read_abstention_records
from alpha.valuation.contracts import method_applicability
from briefing.alpha_view.contracts import Datum, SectionMeta, ViewContractViolation, missing
from briefing.analyst_view.contracts import (
    ACCOUNTING_BASIS_DISPLAY, AnalystBlocker, accounting_basis_display,
)


# ---------------------------------------------------------------------------
# 1. 封閉字彙 ＋ 查表預設
# ---------------------------------------------------------------------------

def test_absence_vocabulary_is_closed() -> None:
    with pytest.raises(AbsenceVocabularyError):
        check_absence_kind("probably_fine")


def test_every_kind_explains_what_the_consumer_should_do() -> None:
    for kind, text in ABSENCE_KINDS.items():
        assert len(text) >= 10, kind


def test_default_kind_is_a_lookup_not_an_inference() -> None:
    assert default_absence_kind("missing") == "not_yet_recorded"
    assert default_absence_kind("not_modeled") == "capability_absent"
    assert default_absence_kind("available") is None
    for status, kind in DEFAULT_ABSENCE_KIND.items():
        assert kind in ABSENCE_KINDS, status


def test_not_applicable_defaults_to_unspecified_because_it_carries_two_meanings() -> None:
    """`not_applicable` 今天同時被 PIT 與方法層用。猜任何一邊都是造假——所以預設就是「沒說」。"""
    assert default_absence_kind("not_applicable") == "not_applicable_unspecified"


def test_settled_kinds_are_a_subset_of_the_vocabulary() -> None:
    assert SETTLED_ABSENCE_KINDS <= set(ABSENCE_KINDS)
    assert "not_yet_recorded" not in SETTLED_ABSENCE_KINDS      # 「還沒寫」永遠是待辦
    assert "upstream_unavailable" not in SETTLED_ABSENCE_KINDS  # 上游缺料也是待辦


def test_datum_rejects_an_absence_kind_on_a_value_bearing_cell() -> None:
    with pytest.raises(ViewContractViolation, match="卻帶缺席語意"):
        Datum(key="k", label="l", value=1.0, status="available", basis="deterministic",
              absence_kind="not_yet_recorded")


def test_datum_effective_kind_prefers_the_explicit_declaration() -> None:
    assert missing("k", "l", "why").effective_absence_kind == "not_yet_recorded"
    assert missing("k", "l", "why", absence_kind="deliberate_abstention"
                   ).effective_absence_kind == "deliberate_abstention"
    assert Datum(key="k", label="l", value=1, status="available",
                 basis="deterministic").effective_absence_kind is None


def test_section_meta_carries_the_same_vocabulary() -> None:
    assert SectionMeta(status="missing", basis="none").effective_absence_kind == "not_yet_recorded"
    with pytest.raises(ViewContractViolation):
        SectionMeta(status="available", basis="deterministic", absence_kind="not_yet_recorded")


# ---------------------------------------------------------------------------
# 2. Abstention 結構上不可能帶數字
# ---------------------------------------------------------------------------

def test_abstention_has_no_field_that_could_carry_a_number() -> None:
    for field in fields(Abstention):
        assert not (set(field.name.lower().split("_")) & FORBIDDEN_VALUE_TOKENS), field.name


def test_growing_a_value_field_is_an_import_time_failure() -> None:
    """空跑檢查：在 `Abstention` 加一個 `target_value` 欄位 → import 失敗（不是 lint 警告）。"""
    from alpha.abstention.contracts import _assert_no_value_fields

    @dataclass(frozen=True)
    class Sneaky:
        abstention_id: str
        target_value: float

    with pytest.raises(ContractViolation, match="數值主張語意"):
        _assert_no_value_fields(Sneaky)


def test_layer_and_subject_are_contracts_not_free_text() -> None:
    with pytest.raises(ContractViolation, match="layer 未登記"):
        abstention_record(company_id="co:x", ticker="X", layer="anything_i_like",
                          subject="forward_earnings_multiple.target_pe",
                          reason="a" * 30, revisit_when="b" * 20)
    with pytest.raises(ContractViolation, match="沒有 subject"):
        abstention_record(company_id="co:x", ticker="X", layer="valuation",
                          subject="dcf.wacc", reason="a" * 30, revisit_when="b" * 20)
    # 2026-09-11：加 research 層（使用者核准）。**這條刻意繼續數**——層數是 contract，
    # 多一層就要多一段消費端語意，偷偷長出第三層必須變紅。
    assert ABSTENTION_LAYERS == ("valuation", "research")
    assert set(ABSTENTION_SUBJECTS) == set(ABSTENTION_LAYERS)
    # research 只開一個 subject：general 到資料支持的那一格為止（L17-4）
    assert ABSTENTION_SUBJECTS["research"] == ("axis.catalyst",)
    with pytest.raises(ContractViolation, match="沒有 subject"):
        abstention_record(company_id="co:x", ticker="X", layer="research",
                          subject="axis.structural", reason="a" * 30, revisit_when="b" * 20)


def test_an_abstention_without_a_revisit_condition_is_rejected() -> None:
    """沒有「什麼證據出現才會改寫」的 abstention 是一個永遠不會響的火警警報（L7）。"""
    with pytest.raises(ContractViolation):
        abstention_record(company_id="co:x", ticker="X", layer="valuation",
                          subject="forward_earnings_multiple.target_pe",
                          reason="a" * 30, revisit_when="")
    with pytest.raises(ContractViolation, match="火警警報"):
        abstention_record(company_id="co:x", ticker="X", layer="valuation",
                          subject="forward_earnings_multiple.target_pe",
                          reason="a" * 30, revisit_when="看情況")


def test_an_abstention_must_say_why_it_cannot_be_anchored() -> None:
    with pytest.raises(ContractViolation, match="說得出為什麼錨不住"):
        abstention_record(company_id="co:x", ticker="X", layer="valuation",
                          subject="forward_earnings_multiple.target_pe",
                          reason="不寫", revisit_when="等更多證據出現時重評")


def _record(**kw):
    base = dict(company_id="co:x", ticker="X", layer="valuation",
                subject="forward_earnings_multiple.target_pe",
                reason="現價對內部 EPS 是 126x，任何合理區間的倍數都只反映隨手選的那個數",
                revisit_when="出現 FY2029+ 的獲利能力證據足以錨定倍數時改寫；每季決算後核查",
                created_at=datetime(2026, 9, 7, tzinfo=timezone.utc))
    base.update(kw)
    return abstention_record(**base)


def test_content_addressed_id_detects_a_duplicate_append(tmp_path) -> None:
    record = _record()
    append_abstention_record(record, directory=tmp_path)
    with pytest.raises(ContractViolation, match="不得重複 append"):
        append_abstention_record(record, directory=tmp_path)


def test_ledger_is_append_only_and_retraction_is_a_new_row(tmp_path) -> None:
    first = _record()
    append_abstention_record(first, directory=tmp_path)
    retraction = _record(supersedes_id=first["abstention_id"], retracted=True,
                         created_at=datetime(2026, 9, 8, tzinfo=timezone.utc))
    append_abstention_record(retraction, directory=tmp_path)
    records, errors = read_abstention_records("X", directory=tmp_path)
    assert len(records) == 2 and not errors           # 舊行仍在（L10）
    chosen = select_abstention(records, layer="valuation",
                               subject="forward_earnings_multiple.target_pe",
                               period_end=None, as_of=None, today=date(2026, 9, 8))
    assert chosen is None                              # 但已撤回 ＝ 等於沒有


def test_selection_respects_point_in_time(tmp_path) -> None:
    append_abstention_record(_record(), directory=tmp_path)
    records, _ = read_abstention_records("X", directory=tmp_path)
    kw = dict(layer="valuation", subject="forward_earnings_multiple.target_pe", period_end=None)
    assert select_abstention(records, as_of=date(2026, 9, 6), today=date(2026, 9, 8), **kw) is None
    assert select_abstention(records, as_of=date(2026, 9, 7), today=date(2026, 9, 8), **kw) is not None


def test_a_broken_ledger_line_is_reported_not_dropped(tmp_path) -> None:
    """INV-3：壞掉的行不得靜默消失。"""
    append_abstention_record(_record(), directory=tmp_path)
    path = tmp_path / "X.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + '{"abstention_id": "ab_bad"}\n', encoding="utf-8")
    records, errors = read_abstention_records("X", directory=tmp_path)
    assert len(records) == 1 and len(errors) == 1


def test_supersedes_must_point_at_an_existing_record(tmp_path) -> None:
    with pytest.raises(ContractViolation, match="不在 ledger 中"):
        append_abstention_record(_record(supersedes_id="ab_nonexistent"), directory=tmp_path)


def test_display_projection_leaks_no_path(tmp_path) -> None:
    record = parse_abstention_record(_record())
    payload = json.dumps(record.to_display(), ensure_ascii=False)
    assert "library" not in payload and "C:" not in payload


# ---------------------------------------------------------------------------
# 3. 模型層自己宣告分支（method not applicable 是既有能力，這裡確認它有 kind）
# ---------------------------------------------------------------------------

def test_method_applicability_is_still_a_separate_semantic_from_missing_data() -> None:
    assert method_applicability("forward_earnings_multiple", None) is None      # 缺料走別條路
    assert method_applicability("forward_earnings_multiple", 1.0) is None
    reason = method_applicability("forward_earnings_multiple", -0.02)
    assert reason and "方法不適用" in reason


def test_valuation_declares_deliberate_abstention_instead_of_not_yet_recorded() -> None:
    """端到端（純邏輯，不連 DB）：ledger 有 abstention → 缺席語意改變，**fair value 仍然缺席**。"""
    from alpha.fundamental.contracts import AssumptionSelection
    from alpha.valuation.contracts import CurrentPrice
    from alpha.valuation.model import build_valuation

    price = CurrentPrice(value=5970.0, bar_date=date(2026, 9, 7), unit="JPY",
                         evidence_refs=("engine_c://financial_snapshot/X",))
    common = dict(company_id="co:x", ticker="X", as_of=None, today=date(2026, 9, 7),
                  fundamental=None, fundamental_reason=None, assumption_records=[],
                  evidence_index={}, price=price)

    plain = build_valuation(**common)
    assert plain.fair_value is None
    assert plain.effective_absence_kind == "upstream_unavailable"

    declared = parse_abstention_record(_record())
    with_abstention = build_valuation(**common, abstention_records=[declared])
    # 上游本來就缺 → 缺席理由仍是上游，**不因為有 abstention 就改口**
    assert with_abstention.effective_absence_kind == "upstream_unavailable"


def test_abstention_changes_why_but_never_produces_a_number() -> None:
    """內部 EPS 齊全、只差目標倍數時：有 abstention → `deliberate_abstention`；沒有 → `not_yet_recorded`。

    **兩種情況的 `fair_value` 都是 None。** abstention 改變的只有那句「為什麼沒有」。
    """
    from alpha.valuation.model import build_valuation
    from tests.test_fundamental_model import ACT_REF, INDEX, _run
    from tests.test_valuation_model import PRICE

    index = {**INDEX, ACT_REF.ref: ACT_REF}
    model = _run(index=index)
    common = dict(company_id="co:coherent", ticker="COHR", as_of=None, today=date(2026, 9, 7),
                  fundamental=model, fundamental_reason=None, assumption_records=[],
                  evidence_index=index, price=PRICE)

    plain = build_valuation(**common)
    assert plain.fair_value is None
    assert plain.effective_absence_kind == "not_yet_recorded"
    assert "尚未寫入任何估值假設" in (plain.reason or "")

    declared = parse_abstention_record(_record(
        ticker="COHR", company_id="co:coherent", period_end=model.target_period.end))
    abstained = build_valuation(**common, abstention_records=[declared])
    assert abstained.fair_value is None                 # ← 沒有偷偷長出一個數字
    assert abstained.effective_absence_kind == "deliberate_abstention"
    assert "刻意不主張目標倍數" in abstained.reason
    assert "什麼會改寫它" in abstained.reason           # revisit 條件必須跟著出現在使用者眼前
    assert declared.abstention_id in abstained.reason   # 可稽核回那一筆紀錄


def test_a_retracted_abstention_falls_back_to_not_yet_recorded() -> None:
    """撤回之後語意必須回到「還沒寫」——否則撤回就是一個不會生效的動作（L13-2）。"""
    from alpha.valuation.model import build_valuation
    from tests.test_fundamental_model import ACT_REF, INDEX, _run
    from tests.test_valuation_model import PRICE

    index = {**INDEX, ACT_REF.ref: ACT_REF}
    model = _run(index=index)
    first = parse_abstention_record(_record(ticker="COHR", company_id="co:coherent",
                                            period_end=model.target_period.end))
    retraction = parse_abstention_record(_record(
        ticker="COHR", company_id="co:coherent", period_end=model.target_period.end,
        supersedes_id=first.abstention_id, retracted=True,
        created_at=datetime(2026, 9, 8, tzinfo=timezone.utc)))
    result = build_valuation(
        company_id="co:coherent", ticker="COHR", as_of=None, today=date(2026, 9, 9),
        fundamental=model, fundamental_reason=None, assumption_records=[],
        evidence_index=index, price=PRICE, abstention_records=[first, retraction])
    assert result.effective_absence_kind == "not_yet_recorded"


def test_available_valuation_never_carries_an_absence_kind() -> None:
    from alpha.valuation.contracts import CurrentPrice, FairValueGap, ValuationResult
    from alpha.fundamental.contracts import AssumptionSelection

    with pytest.raises(ContractViolation, match="有 fair value 就沒有缺席語意"):
        ValuationResult(
            company_id="co:x", ticker="X", as_of=None, method="forward_earnings_multiple",
            status="available", reason=None, target_period=None, accounting_basis="gaap",
            fundamental_input=None, assumptions=(),
            selection=AssumptionSelection(input_count=0, accepted_count=0, reasons={}),
            fair_value=10.0, currency="USD", formula="f", input_dependency="session_judgment",
            steps=(), current_price=CurrentPrice(value=1.0, bar_date=date(2026, 9, 7), unit="USD",
                                                 evidence_refs=()),
            gap=FairValueGap(status="comparable", absolute_gap=9.0, relative_gap=9.0,
                             implied_multiple_at_price=None, unit="USD", reason=None),
            absence_kind="not_yet_recorded")


# ---------------------------------------------------------------------------
# 4. 語意債 B：accounting basis 的呈現別名
# ---------------------------------------------------------------------------

def test_display_alias_never_claims_a_standard_the_authority_cannot_support() -> None:
    """Lynas（AASB／IFRS）、HDS（日本基準）、IQE（IFRS）在 ledger 裡全都是 `gaap`。"""
    for raw, entry in ACCOUNTING_BASIS_DISPLAY.items():
        for forbidden in ("US GAAP", "IFRS", "AASB", "日本基準", "J-GAAP", "台灣 IFRS"):
            assert forbidden not in entry["label"], (raw, forbidden)


def test_display_alias_keeps_the_contract_value_for_audit() -> None:
    out = accounting_basis_display("gaap")
    assert out["raw"] == "gaap"
    assert "法定" in out["label"] or "as reported" in out["label"].lower()


def test_unregistered_basis_is_shown_verbatim_not_invented() -> None:
    out = accounting_basis_display("ifrs_full")
    assert out["raw"] == "ifrs_full" and out["label"] == "ifrs_full"


def test_missing_basis_says_undeclared_rather_than_guessing() -> None:
    assert accounting_basis_display(None)["label"] == "未宣告"


# ---------------------------------------------------------------------------
# 5. blocker 的結構化形式與字串形式必須是同一份判斷
# ---------------------------------------------------------------------------

def test_blocker_detail_vocabulary_is_checked() -> None:
    with pytest.raises(Exception):
        AnalystBlocker(panel="headline", status="missing", absence_kind="made_up",
                       settled=False, reason=None)


def test_blockers_and_blocker_details_must_have_the_same_length() -> None:
    from briefing.analyst_view.contracts import AnalystReadiness, AnalystViewContractViolation

    with pytest.raises(AnalystViewContractViolation, match="一一對應"):
        AnalystReadiness(state="blocked", core_panels=("headline",), optional_panels=("entry",),
                         flags=(), blockers=("a", "b"), optional_unavailable=(), rule="r",
                         blocker_details=(AnalystBlocker(panel="headline", status="missing",
                                                         absence_kind=None, settled=False, reason=None),))


# ---------------------------------------------------------------------------
# 4. research 層（2026-09-11）：「已研究、結論是沒有可監看事件」
# ---------------------------------------------------------------------------

def _catalyst_abstention(created: date = date(2026, 9, 11)) -> Abstention:
    return parse_abstention_record(abstention_record(
        company_id="co:globalfoundries", ticker="GFS", layer="research", subject="axis.catalyst",
        reason="bounded source-trace 找到的兩則具名事件都正確地不具入圖資格：一則是資本事件、"
               "一則無金額無產能無最低採購量。沒有可監看的具名事件，不是還沒查。",
        revisit_when="出現帶金額／產能／最低採購量的客戶端承諾，或 registry 內公司具名的長約公告",
        created_at=datetime(created.year, created.month, created.day, tzinfo=timezone.utc)))


def test_a_research_abstention_is_selected_like_any_other_layer() -> None:
    """選取規則與估值層**同一套**——不為新層另寫一份（L16）。"""
    rec = _catalyst_abstention()
    kwargs = dict(period_end=None, as_of=None, today=date(2026, 9, 12))
    assert select_abstention([rec], layer="research", subject="axis.catalyst", **kwargs) is rec
    # 宣告日之前的視角看不到它——PIT 與估值層同一條規則
    assert select_abstention([rec], layer="research", subject="axis.catalyst",
                             period_end=None, as_of=date(2026, 9, 10),
                             today=date(2026, 9, 12)) is None
    # 別層／別 subject 拿不到它
    assert select_abstention([rec], layer="valuation",
                             subject="forward_earnings_multiple.target_pe", **kwargs) is None


def test_a_settled_catalyst_axis_is_not_a_todo_but_readiness_stays_blocked() -> None:
    """**settled 不讓 readiness 變好**（AGENTS「APP 呈現契約」）——它只回答「該不該去補」。"""
    from briefing.analyst_view.contracts import AnalystPanel

    def _panel(catalyst_kind: str | None) -> AnalystPanel:
        return AnalystPanel(
            key="research", title="研究現況", questions=("q6_change",), status="missing", optional=False,
            source_sections=("catalysts",), source_statuses={"catalysts": "missing"},
            source_absence_kinds={"catalysts": catalyst_kind}, lines=())

    not_yet = _panel("not_yet_recorded")
    assert not_yet.absence_is_settled is False, "沒宣告過就是待辦"

    settled = _panel("deliberate_abstention")
    assert settled.absence_is_settled is True
    assert settled.status == "missing", "宣告之後那一格仍然缺席——abstention 型別上不可能帶內容"
    blocker = AnalystBlocker(panel="research", status=settled.status,
                             absence_kind=settled.absence_kind, settled=settled.absence_is_settled,
                             reason=None)
    assert blocker.settled is True and blocker.status == "missing"


def test_the_catalyst_section_only_goes_settled_when_a_record_says_so() -> None:
    """呈現層不得自己打標籤——`deliberate_abstention` 只能來自 append-only 紀錄。

    這條會在有人把「沒有催化劑」直接寫成 settled 時變紅。
    """
    import inspect

    from briefing.alpha_view import builder

    src = inspect.getsource(builder)
    marker = 'absence_kind=("deliberate_abstention" if catalyst_abstention is not None else None)'
    assert marker in src, "catalysts 的 settled 必須綁在 select_abstention 的結果上"
