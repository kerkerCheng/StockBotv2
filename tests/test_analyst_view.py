"""Analyst Consumer v1（Phase 2 Step 3.5）的驗收——**這一層不得說謊，也不得偷偷變成第二個研究層**。

守的是 Step 3.5 的驗收條件：
1. Consumer 不重算 EPS／估值／報酬（用**物件同一性**證明，不是用「數字剛好一樣」證明）；
2. PIT／as-of；3. Missing != Zero；4. stale／review_required 清楚現形；
5. **Entry missing 不影響 core readiness**；6. 上游 missing 時不造假結論；
7. renderer／compose 沒有 authority write；8. 沒有 LLM／buy-sell／sizing／portfolio 洩漏；
9. 可預先 materialize（確定性 ＋ JSON round-trip）。
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any, Iterator

import pytest

from alpha.contracts import FORBIDDEN_POSITION_TOKENS
from briefing.alpha_view.contracts import AlphaInvestmentView, Datum, RefreshItem
from briefing.analyst_view import (
    CORE_PANELS, OPTIONAL_PANELS, QUESTIONS, SCHEMA_VERSION, AnalystLine,
    AnalystViewContractViolation, build_analyst_view, render_analyst_view_markdown,
)
from briefing.analyst_view.contracts import (
    BLOCKED, READY, READY_WITH_FLAGS, WEAK_INPUT_RULES, readiness_class, worst_status,
)
from tests.test_alpha_investment_view import _view
from tests.test_entry_logic import _criterion, _entry
from tests.test_fundamental_model import _run
from tests.test_implied_return import TODAY, _return, _valued
from tests.test_valuation_model import _index

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "briefing" / "analyst_view"


# ---------------------------------------------------------------------------
# fixtures：一份「上游齊備」的 view（含估值／報酬），entry 可有可無
# ---------------------------------------------------------------------------

def _full_view(*, with_criterion: bool, **kwargs: Any) -> AlphaInvestmentView:
    model = _run(index=_index())
    valuation = _valued(model)
    implied = _return(valuation)
    criteria = [_criterion()] if with_criterion else []
    entry = _entry(implied, criteria)
    return _view(fundamental_model=model, valuation=valuation,
                 valuation_records=list(valuation.assumptions), implied_return=implied,
                 horizon_records=[implied.horizon], entry=entry, entry_records=criteria,
                 today=TODAY, **kwargs)


def _bare_view(**kwargs: Any) -> AlphaInvestmentView:
    """完全沒有估值／報酬／判準的 view——上游缺席時 consumer 該怎麼講話。"""
    return _view(today=TODAY, **kwargs)


def _datum_ids(view: AlphaInvestmentView) -> set[int]:
    """read model 裡每一個 `Datum` 的 `id()`。consumer 的每一格都必須落在這個集合裡。"""
    found: set[int] = set()

    def walk(node: Any) -> None:
        if isinstance(node, Datum):
            found.add(id(node))
            return
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
            return
        if hasattr(node, "__dataclass_fields__"):
            for name in node.__dataclass_fields__:
                walk(getattr(node, name))

    walk(view)
    return found


def _all_lines(analyst: Any) -> Iterator[Any]:
    for panel in analyst.panels:
        yield from panel.lines
        yield from panel.weak_inputs


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.add(("." * node.level) + (node.module or ""))
    return out


# ---------------------------------------------------------------------------
# 1. Consumer 不重算：用物件同一性證明
# ---------------------------------------------------------------------------

def test_every_consumer_cell_is_the_same_object_as_the_read_model_cell() -> None:
    """空跑檢查：讓 compose 自己 `Datum(...)` 生一格（哪怕值一模一樣），這條會紅。"""
    view = _full_view(with_criterion=True)
    analyst = build_analyst_view(view)
    allowed = _datum_ids(view)
    lines = list(_all_lines(analyst))
    assert lines, "沒有任何一行——這條測試會變成空跑"
    for line in lines:
        assert id(line.datum) in allowed, (
            f"{line.key} 的 datum 不是 read model 裡的物件——consumer 自己造了一格"
        )
    # 證據／催化劑／disproof／refresh item 也一樣是參照，不是重建
    assert all(item in view.evidence.index for item in analyst.why.evidence)
    assert analyst.research.disproofs == view.falsification.conditions
    assert analyst.research.catalysts == view.catalysts.structured
    assert all(item in view.refresh_status.items for item in analyst.research.attention)


def test_consumer_carries_no_formula_and_no_numeric_literal_of_its_own() -> None:
    """沒有公式常數（365.25／0.15／100）、沒有 float 字面值、不 import 任何 alpha 模型模組。"""
    model_modules = ("alpha.entry", "alpha.entry.model", "alpha.valuation", "alpha.valuation.model",
                     "alpha.implied_return", "alpha.implied_return.model", "alpha.fundamental",
                     "alpha.refresh", "alpha.refresh.resolver")
    for name in ("contracts.py", "compose.py", "render.py"):
        path = PKG / name
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        floats = {n.value for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, float)}
        assert not floats, (name, floats)
        imported = _imports(path)
        assert not (imported & set(model_modules)), (name, imported & set(model_modules))
        for token in ("365.25", "build_entry_assessment", "build_valuation", "build_implied_return",
                      "fair_value =", "price_return =", "entry_price ="):
            assert token not in source, (name, token)


def test_module_import_allowlists_keep_the_layer_presentation_independent() -> None:
    allowed = {
        # `alpha.absence` 是缺席語意的封閉字彙 SSOT，本身零相依（見
        # tests/test_alpha_view_render.py::test_contracts_module_is_pure_stdlib 的同步斷言）。
        # 允許它是為了**不要**在呈現層複製第二份字彙表——L16 記過三次的形狀。
        "contracts.py": {"__future__", "dataclasses", "datetime", "typing",
                         "alpha.absence", "briefing.alpha_view.contracts"},
        "compose.py": {"__future__", "typing", "briefing.alpha_view.contracts", ".contracts"},
        "render.py": {"__future__", "typing", "briefing.alpha_view.contracts",
                      "briefing.alpha_view.render", "shared.markdown", ".contracts"},
    }
    for name, permitted in allowed.items():
        extra = _imports(PKG / name) - permitted
        assert not extra, f"{name} 多了不該有的相依：{sorted(extra)}"


def test_a_fabricated_cell_is_rejected_at_the_type_layer() -> None:
    with pytest.raises(AnalystViewContractViolation):
        AnalystLine(key="k", display_label="偽造", datum={"value": 1.0}, role="internal")  # type: ignore[arg-type]
    with pytest.raises(AnalystViewContractViolation):
        AnalystLine(key="k", display_label="角色未登記",
                    datum=Datum(key="x", label="x"), role="recommendation")


# ---------------------------------------------------------------------------
# 2. Entry 是 optional：缺席不得影響 core readiness
# ---------------------------------------------------------------------------

def test_missing_entry_criterion_does_not_change_core_readiness() -> None:
    with_hurdle = build_analyst_view(_full_view(with_criterion=True))
    without = build_analyst_view(_full_view(with_criterion=False))
    assert with_hurdle.entry.status == "available"
    assert without.entry.status == "missing"
    # 核心 readiness 逐欄相同——差的只有 optional 那一欄
    assert with_hurdle.readiness.state == without.readiness.state
    assert with_hurdle.readiness.flags == without.readiness.flags
    assert with_hurdle.readiness.blockers == without.readiness.blockers
    assert without.readiness.optional_unavailable == ("entry：missing",)
    assert with_hurdle.readiness.optional_unavailable == ()
    # 核心四段的 status 一格不動
    assert ({p: getattr(with_hurdle, p).status for p in CORE_PANELS}
            == {p: getattr(without, p).status for p in CORE_PANELS})
    assert "entry" in OPTIONAL_PANELS and "entry" not in CORE_PANELS


def test_missing_entry_is_shown_as_optional_unavailable_not_as_incomplete_research() -> None:
    analyst = build_analyst_view(_full_view(with_criterion=False))
    text = render_analyst_view_markdown(analyst).replace("\\", "")
    assert "Not set (optional)" in text
    assert "不影響 core readiness" in text
    # 缺的是「投資門檻判斷」，不是研究不完整、更不是 ETL 缺口
    assert "投資門檻判斷" in text and "不是資料 ETL 缺口" in text
    # 頭條照樣完整：主流程終點是 implied return，不是 entry
    assert analyst.headline.status == "available"
    assert analyst.headline.context["period"] == "FY2027"
    # 而且**不得**補一個預設 hurdle
    payload = analyst.to_dict()
    entry_values = {line["key"]: line["datum"]["value"] for line in payload["entry"]["lines"]}
    assert entry_values["required_annualized_return"] is None
    assert entry_values["entry_price"] is None
    assert entry_values["hurdle_comparison"] is None
    # 上游照抄值仍看得見（要先知道現在隱含幾 %，才知道該不該宣告 hurdle）
    assert entry_values["current_annualized_implied_return"] is not None


# ---------------------------------------------------------------------------
# 3. Missing != Zero；4. 上游缺席時不造假結論
# ---------------------------------------------------------------------------

def test_missing_upstream_is_blocked_and_never_rendered_as_zero() -> None:
    analyst = build_analyst_view(_bare_view())
    assert analyst.readiness.state == BLOCKED
    assert analyst.readiness.blockers, "上游全缺卻沒有任何 blocker——那就是在假裝完整"
    payload = json.loads(json.dumps(analyst.to_dict(), ensure_ascii=False))
    head = {line["key"]: line["datum"] for line in payload["headline"]["lines"]}
    for key in ("fair_value", "price_return", "annualized_price_return", "horizon"):
        assert head[key]["value"] is None                       # null，不是 0
        assert head[key]["status"] in ("missing", "not_modeled", "insufficient_evidence")
        assert head[key]["reason"], f"{key} 缺席卻沒說為什麼"
    text = render_analyst_view_markdown(analyst)
    headline = next(line for line in text.splitlines() if " simple ／ " in line)
    assert "0.0%" not in headline and "+0%" not in headline
    assert "缺料" in headline or "尚未建模" in headline


def test_absent_cells_still_occupy_a_row_so_the_gap_is_visible() -> None:
    """INV-3：看不見的缺口等於沒有缺口。not_modeled 的格子照樣印一列。"""
    analyst = build_analyst_view(_full_view(with_criterion=True))
    text = render_analyst_view_markdown(analyst).replace("\\", "")
    assert "內部 FCF 估計" in text and "尚未建模" in text
    assert "總報酬（含股利）" in text
    assert "機率加權期望報酬" in text


# ---------------------------------------------------------------------------
# 5. stale／review_required 現形
# ---------------------------------------------------------------------------

def test_review_required_upstream_surfaces_in_readiness_attention_and_markdown() -> None:
    from datetime import datetime, timezone

    from alpha.refresh import GRAPH_EDGE, ChangeEvent
    from tests.test_valuation_model import EDGE

    edge = ChangeEvent(change_type=GRAPH_EDGE, ticker="COHR", company_id="co:coherent",
                       authority="engine_a://graph_research_provider", changed_ref=EDGE,
                       observed_at=datetime(2026, 9, 7, 23, 59, 59, tzinfo=timezone.utc),
                       material_fields=("substitutability",))
    analyst = build_analyst_view(_full_view(with_criterion=True, refresh_changes=[edge]))
    assert analyst.refresh.overall in ("review_required", "invalidated")
    assert analyst.refresh.attention, "refresh 說有東西要重看，consumer 卻沒有列出來"
    assert analyst.readiness.state == READY_WITH_FLAGS
    assert any("review_required" in flag for flag in analyst.readiness.flags)
    text = render_analyst_view_markdown(analyst)
    assert "需要重看的研究成果" in text
    assert any(item.state == "review_required" for item in analyst.research.attention)
    # 頭條也看得到（估值／報酬鏈上的成果）
    assert analyst.headline.attention


def test_clean_state_says_nothing_needs_action_instead_of_staying_silent() -> None:
    analyst = build_analyst_view(_full_view(with_criterion=True))
    text = render_analyst_view_markdown(analyst)
    assert "無**（範圍：" in text and "本節其餘成果 current 或屬歷史" in text


def test_headline_no_attention_states_its_scope_and_the_count_outside_it() -> None:
    """「無」是一句斷言，它的**範圍**必須跟著印。

    2026-09-07 實測（`--scenario fiscal_rollover`）：畫面上方寫 `overall=review_required`，
    頭條卻寫「需要重看的研究成果：無」——兩句互相否定。原因是頭條只看
    `HEADLINE_ARTIFACTS`，卻用一句全域措辭把它說出來（L12：一個表示兩種語意）。
    """
    from briefing.analyst_view.compose import HEADLINE_ARTIFACTS

    view = _full_view(with_criterion=True)
    outside = RefreshItem(artifact_type="axis", artifact_id="expectation_gap", label="Q4 預期落差",
                          state="review_required", reasons=("consensus 變了",), changed_refs=(),
                          dependency_refs=(), detected_at=None, established_at=None,
                          required_action="reassess in a session", propagated_from=(), kind="judgment")
    view = replace(view, refresh_status=replace(view.refresh_status, overall="review_required",
                                                items=(*view.refresh_status.items, outside)))
    analyst = build_analyst_view(view)
    assert analyst.headline.attention == ()                       # 頭條那幾格確實乾淨
    assert analyst.headline.attention_scope is not None
    assert all(t in analyst.headline.attention_scope for t in HEADLINE_ARTIFACTS)
    assert analyst.headline.attention_total == 1                  # 但整份 view 有 1 項

    text = render_analyst_view_markdown(analyst)
    assert "本節之外另有 **1** 項需要動作" in text


# ---------------------------------------------------------------------------
# 6. PIT／as-of
# ---------------------------------------------------------------------------

def test_as_of_view_keeps_the_point_in_time_mode_and_does_not_leak_future_values() -> None:
    from tests.test_alpha_investment_view import _as_of_build

    as_of = date(2026, 8, 15)
    build = _as_of_build(as_of)
    view = _view(today=TODAY)                                   # current 視角當對照
    current = build_analyst_view(view)
    assert current.point_in_time_mode == "current" and current.as_of is None
    from briefing.alpha_view import build_alpha_investment_view

    historical = build_analyst_view(build_alpha_investment_view(build=build, today=TODAY))
    assert historical.point_in_time_mode == "as_of" and historical.as_of == as_of
    payload = historical.to_dict()
    assert payload["as_of"] == as_of.isoformat()
    # 沒有估值／報酬的歷史視角＝blocked，而不是拿當前值冒充
    assert historical.readiness.state == BLOCKED
    head = {line["key"]: line["datum"]["value"] for line in payload["headline"]["lines"]}
    assert head["fair_value"] is None and head["price_return"] is None


# ---------------------------------------------------------------------------
# 7. 沒有 authority write、沒有 LLM、沒有 buy／sell／sizing／portfolio
# ---------------------------------------------------------------------------

def test_consumer_never_writes_any_authority() -> None:
    forbidden = ("open(", "write_text", ".write(", "append_", "record_", "commit", "Path(",
                 "store.", "todo_pool", "os.environ")
    for name in ("contracts.py", "compose.py", "render.py", "__init__.py"):
        source = (PKG / name).read_text(encoding="utf-8")
        hits = [token for token in forbidden if token in source]
        assert not hits, f"{name} 出現寫入型 token：{hits}"


def test_no_llm_api_dependency_anywhere_in_the_consumer() -> None:
    for name in ("contracts.py", "compose.py", "render.py", "__init__.py"):
        imported = {module.split(".")[0] for module in _imports(PKG / name)}
        assert not (imported & {"anthropic", "openai", "google", "cohere", "mistralai", "ollama"})
        source = (PKG / name).read_text(encoding="utf-8")
        assert "ANTHROPIC_API_KEY" not in source and "messages.create" not in source


def test_no_position_sizing_or_portfolio_field_leaks_into_the_projection() -> None:
    analyst = build_analyst_view(_full_view(with_criterion=True))
    payload = json.loads(json.dumps(analyst.to_dict(), ensure_ascii=False))

    def keys(node: Any) -> Iterator[str]:
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from keys(value)
        elif isinstance(node, list):
            for item in node:
                yield from keys(item)

    # 用 `_` 切詞比對，不用子字串——`optional_unavailable` 的 "u-nav-ailable" 會讓子字串比對誤報，
    # 而一個會誤報的防呆本身就是 L16 明文禁止的東西。
    banned = set(FORBIDDEN_POSITION_TOKENS) | {"target_weight", "supported_range", "nav_pct", "held"}
    offenders = [key for key in keys(payload) if set(str(key).lower().split("_")) & banned]
    assert not offenders, f"analyst view 出現部位欄位：{sorted(set(offenders))}"


def test_the_comparison_is_never_translated_into_an_action() -> None:
    """`meets_analytical_hurdle` 只是算術；consumer 不得把它印成「可以買」。"""
    analyst = build_analyst_view(_full_view(with_criterion=True))
    text = render_analyst_view_markdown(analyst).replace("\\", "")
    # 行動語彙**可以**出現，但只准出現在否定句裡（authority 的 `is_not` 逐字就寫著
    # 「不得把門檻價讀成『該買的價格』」）。攔掉整個字會攔到那句警告本身——
    # 那是 L15 的「gate 攔錯東西」，所以判準是**這一行有沒有否定**。
    for line in text.splitlines():
        if any(word in line for word in ("建議買", "建議賣", "可以買", "該買", "買進", "賣出",
                                         "加碼", "減碼", "下單", "buy", "sell")):
            assert any(neg in line for neg in ("不是", "不得", "不給", "this_is_not", "is_not")), line
    assert "本畫面不給買賣建議、不給部位尺寸" in text


# ---------------------------------------------------------------------------
# 8. 可預先 materialize：確定性 ＋ JSON round-trip ＋ 六問全覆蓋
# ---------------------------------------------------------------------------

def test_projection_is_deterministic_and_json_round_trips_with_nulls_preserved() -> None:
    first = build_analyst_view(_full_view(with_criterion=True)).to_dict()
    second = build_analyst_view(_full_view(with_criterion=True)).to_dict()
    text = json.dumps(first, ensure_ascii=False, sort_keys=True)
    assert text == json.dumps(second, ensure_ascii=False, sort_keys=True)
    assert json.loads(text) == first                            # null 保留為 null
    assert first["schema_version"] == SCHEMA_VERSION
    assert first["panel_order"] == list(("headline", "fundamental", "why", "research", "entry"))
    assert set(first["questions"]) == set(QUESTIONS)


def test_every_consumer_question_is_answered_by_some_panel() -> None:
    analyst = build_analyst_view(_full_view(with_criterion=True))
    answered = {question for panel in analyst.panels for question in panel.questions}
    assert answered == set(QUESTIONS), set(QUESTIONS) - answered


def test_information_hierarchy_puts_the_implied_return_first() -> None:
    """主流程終點是 implied return——它必須是讀者看到的第一個東西，entry 在最後且標 optional。"""
    analyst = build_analyst_view(_full_view(with_criterion=False))
    order = [panel.key for panel in analyst.panels]
    assert order[0] == "headline" and order[-1] == "entry"
    assert analyst.headline.questions == ("q4_implied_return",)
    text = render_analyst_view_markdown(analyst)
    positions = [text.index(marker) for marker in
                 ("## 頭條", "## 1. 我們預測什麼", "## 2. 市場預測什麼", "## 3. 差異在哪",
                  "## 4. 怎麼算到這裡", "## 5. 什麼 evidence 會改變答案", "## Entry threshold（optional）")]
    assert positions == sorted(positions), positions


# ---------------------------------------------------------------------------
# 9. 脆弱輸入：列入規則是宣告好的，不是新判斷
# ---------------------------------------------------------------------------

def test_weak_inputs_declare_the_rule_that_listed_them_and_order_by_existing_sensitivity() -> None:
    view = _full_view(with_criterion=True)
    analyst = build_analyst_view(view)
    weak = analyst.why.weak_inputs
    assert weak, "有假設卻沒有任何脆弱輸入——那代表列入規則沒跑"
    for item in weak:
        assert item.rule in WEAK_INPUT_RULES and item.why == WEAK_INPUT_RULES[item.rule]
    assert weak[0].rule == "largest_modeled_sensitivity"
    assert {item.rule for item in weak} <= set(WEAK_INPUT_RULES)
    # 敏感度只被排序，數字一位都沒動
    shown = [line.datum for line in analyst.why.lines if line.role == "sensitivity"]
    assert set(map(id, shown)) == set(map(id, view.valuation.sensitivities))
    magnitudes = [abs(d.value["fair_value_relative"]) for d in shown]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_unknown_axis_is_listed_as_unknown_not_as_a_passing_grade() -> None:
    analyst = build_analyst_view(_full_view(with_criterion=True))
    unknown = [item for item in analyst.why.weak_inputs if item.rule == "unknown_axis"]
    assert unknown, "有未知軸卻沒有現形"
    for item in unknown:
        assert item.datum.value is None and not item.datum.is_known


# ---------------------------------------------------------------------------
# 10. status roll-up 與 readiness 是查表，不是新判斷
# ---------------------------------------------------------------------------

def test_worst_status_and_readiness_class_are_declared_lookups() -> None:
    assert worst_status(["available", "partial"]) == "partial"
    assert worst_status(["available", "review_required", "partial"]) == "review_required"
    assert worst_status(["missing", "review_required"]) == "missing"
    assert worst_status(["missing", "invalidated"]) == "invalidated"
    assert readiness_class("available") == READY
    assert readiness_class("partial") == READY
    assert readiness_class("stale") == READY_WITH_FLAGS
    assert readiness_class("not_modeled") == BLOCKED
    with pytest.raises(AnalystViewContractViolation):
        worst_status([])
    with pytest.raises(AnalystViewContractViolation):
        readiness_class("looks_fine")


def test_panel_status_is_copied_from_the_source_sections_not_invented() -> None:
    view = _full_view(with_criterion=True)
    analyst = build_analyst_view(view)
    for panel in analyst.panels:
        for section, status in panel.source_statuses.items():
            assert getattr(view, section).meta.status == status
        assert panel.status == worst_status(list(panel.source_statuses.values()))


# ---------------------------------------------------------------------------
# 11. CLI 掛得上（dispatch 是具名函式，不是 lazy lambda）
# ---------------------------------------------------------------------------

def test_cli_exposes_analyst_view_with_as_of_and_both_formats() -> None:
    from briefing.cli import build_parser, cmd_analyst_view

    args = build_parser().parse_args(["analyst-view", "COHR", "--as-of", "2026-09-06",
                                      "--format", "json"])
    assert args.func is cmd_analyst_view
    assert args.ticker == "COHR" and args.as_of == "2026-09-06" and args.format == "json"
    assert build_parser().parse_args(["analyst-view", "COHR"]).format == "markdown"


def test_markdown_escapes_external_text_and_stays_single_line_per_row() -> None:
    analyst = build_analyst_view(_full_view(with_criterion=True))
    text = render_analyst_view_markdown(analyst)
    for line in text.splitlines():
        if line.startswith("|"):
            assert line.count("\n") == 0
    assert not re.search(r"\|\s*\|\s*\|\s*\|\s*\|\s*$", text)   # 沒有整列空白格
