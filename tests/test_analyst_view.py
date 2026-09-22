"""Analyst Consumer v1（Phase 2 Step 3.5）的驗收——**這一層不得說謊，也不得偷偷變成第二個研究層**。

守的是 Step 3.5 的驗收條件：
1. Consumer 不重算 EPS／估值／報酬（用**物件同一性**證明，不是用「數字剛好一樣」證明）；
2. PIT／as-of；3. Missing != Zero；4. stale／review_required 清楚現形；
5. ~~Entry missing 不影響 core readiness~~（2026-09-23 Phase 0：`entry` panel 退役）；
   6. 上游 missing 時不造假結論；
7. renderer／compose 沒有 authority write；8. 沒有 LLM／buy-sell／sizing／portfolio 洩漏；
9. 可預先 materialize（確定性 ＋ JSON round-trip）。

⚠ **2026-09-23（Phase 0 Step 0b.1）：`why` 與 `entry` 兩個 panel 退役，`headline` 換主詞。**
守 1（物件同一性）、2（PIT）、3（Missing != Zero）、4（stale 現形）、6、7、8、9 **一條都沒變**，
只是主詞換了 panel。守 5 隨 `entry` 退役——取代它的是「`fundamental` 降選配後缺席不讓 readiness 變差」。
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
    assert all(item in view.evidence.index for item in analyst.argument.evidence)
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

def test_optional_panel_absence_does_not_change_core_readiness() -> None:
    """optional panel 缺席**不得**讓 readiness 變差。

    ⚠ 2026-09-23（Phase 0 Step 0b.1）：原本這條的主詞是 `entry`（進場門檻）——那個 panel 已退役
    （73 檔全 missing、從未用過）。守的判準一字未改，只是現在的 optional panel 是
    `fundamental`／`bet`／`downside`：**它們缺席只出現在 `optional_unavailable`，不進 blockers。**
    """
    analyst = build_analyst_view(_bare_view())
    assert set(OPTIONAL_PANELS) == {"fundamental", "bet", "downside"}
    for name in OPTIONAL_PANELS:
        assert getattr(analyst, name).optional is True, name
    # optional 的缺席一律不進 blockers／flags，只進 optional_unavailable。
    blocked_panels = {b.panel for b in analyst.readiness.blocker_details}
    flagged_panels = {f.panel for f in analyst.readiness.flag_details}
    assert not (blocked_panels & set(OPTIONAL_PANELS))
    assert not (flagged_panels & set(OPTIONAL_PANELS))
    unavailable = "｜".join(analyst.readiness.optional_unavailable)
    assert "fundamental" in unavailable and "bet" in unavailable and "downside" in unavailable
    # 而核心 panel 的缺席**必須**進 blockers——短評與歸零旗標 2026-09-23 起是核心。
    assert set(CORE_PANELS) == {"headline", "brief", "argument", "research", "wipeout"}
    assert "brief" in blocked_panels and "wipeout" in blocked_panels


def test_retired_panels_are_gone_from_every_closed_list() -> None:
    """`why` 與 `entry` 必須從**所有**封閉清單消失，不是只從 CORE_PANELS 拿掉。

    事發形狀（2026-09-18，D2）：panel 做好了但沒登記在 `PANEL_ORDER`，於是 artifact 的
    `absence_kind` 是 `None`——機制在、分類沒跟著資料走（L16）。**退役是同一件事的反面**：
    清單漏刪一處，就會有消費端還在找那個 panel。
    """
    from briefing.analyst_view.contracts import LINE_ROLES, PLAIN_PANEL_TITLES

    analyst = build_analyst_view(_bare_view())
    for retired in ("why", "entry"):
        assert retired not in CORE_PANELS and retired not in OPTIONAL_PANELS, retired
        assert retired not in analyst.PANEL_ORDER, retired
        assert not hasattr(analyst, retired), retired
        assert retired not in PLAIN_PANEL_TITLES, retired
    # `why` 專用的四個 line role 與 `entry` 的 role 一併退役（沒有 producer 的字彙不留）。
    for role in ("assumption", "sensitivity", "trace", "epistemics", "entry"):
        assert role not in LINE_ROLES, role
    # 三個退役問句不得留在 QUESTIONS（panel 的 questions 會對它驗封閉性）。
    for q in ("q4_implied_return", "q5_fragile", "q7_payoff"):
        assert q not in QUESTIONS, q


def test_missing_upstream_is_blocked_and_never_rendered_as_zero() -> None:
    analyst = build_analyst_view(_bare_view())
    assert analyst.readiness.state == BLOCKED
    assert analyst.readiness.blockers, "上游全缺卻沒有任何 blocker——那就是在假裝完整"
    payload = json.loads(json.dumps(analyst.to_dict(), ensure_ascii=False))
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：原本這裡驗頭條的 fair_value／price_return／
    # annualized_price_return／horizon 四格「是 null 不是 0」。那四格隨估值鏈退役。
    # **判準一字未改**，主詞換成核心 panel 自己的缺席：每個 blocker 都要說得出 status 與理由。
    for blocker in payload["readiness"]["blocker_details"]:
        assert blocker["status"] in ("missing", "not_modeled", "insufficient_evidence", "invalidated")
        assert blocker["absence_kind"], f"{blocker['panel']} 缺席卻沒宣告 absence_kind"
    # 現價那一格也不得被補成 0（它是 A2 觀測，缺就是缺）。
    head = {line["key"]: line["datum"] for line in payload["headline"]["lines"]}
    if "current_price" in head:
        assert head["current_price"]["value"] is None or head["current_price"]["value"] != 0
    text = render_analyst_view_markdown(analyst)
    assert "0.0%" not in text.split("## 現在多少錢", 1)[-1].split("##", 1)[0]


def test_absent_cells_still_occupy_a_row_so_the_gap_is_visible() -> None:
    """INV-3：看不見的缺口等於沒有缺口。not_modeled 的格子照樣印一列。"""
    analyst = build_analyst_view(_full_view(with_criterion=True))
    text = render_analyst_view_markdown(analyst).replace("\\", "")
    assert "內部 FCF 估計" in text and "尚未建模" in text
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：原本還驗「總報酬（含股利）」與「機率加權期望報酬」
    # 兩格 not_modeled 照樣印一列——它們住 `implied_return`，隨估值鏈退役。
    # **判準一字未改**（INV-3：看不見的缺口等於沒有缺口），上面那一格仍然守著它。


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
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：原本這裡還斷言 readiness 是 READY_WITH_FLAGS，
    # 因為**背 review_required 的那個 panel 是 `why`**（它的 status 取估值鏈三段最差）。
    # `why` 退役後，圖的邊變動不再讓任何核心 panel 的 status 翻成 review_required——
    # 它只走 refresh／attention 那條路。**本條守的「要現形」沒有放寬**，改問它真的出現的三個地方；
    # readiness 那條路要等 Phase 2 的讀圖 panel 升核心才接得回來（見 plan §0.6）。
    assert readiness_class("review_required") == READY_WITH_FLAGS
    assert any(item.state == "review_required" for item in analyst.refresh.attention)
    assert any(item.state == "review_required" for item in analyst.research.attention)
    text = render_analyst_view_markdown(analyst)
    assert "需要重看的研究成果" in text
    assert "review_required" in text


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
    # 沒有上游的歷史視角＝blocked，而不是拿當前值冒充
    assert historical.readiness.state == BLOCKED
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：原本驗頭條的 fair_value／price_return 是 None。
    # 兩格隨估值鏈退役。**判準一字未改**（不得拿當前值冒充 as-of），主詞換成 as-of 模式本身
    # 與每個 blocker 都說得出缺席語意。
    assert payload["point_in_time_mode"] == "as_of"
    assert payload["readiness"]["blocker_details"]
    for blocker in payload["readiness"]["blocker_details"]:
        assert blocker["absence_kind"], blocker["panel"]


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
    # `downside` 緊接在 `bet` 後面：同一把尺的兩端，讀的人要並排看（D2，2026-09-18）。
    # `wipeout` 再接在 `downside` 後面：下檔問「thesis 錯了值多少」，它問「公司會不會直接歸零」。
    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：`why` 與 `entry` 退役，`brief` 移到最前面
    # （首屏的單位是句不是格）。**封閉清單的相等斷言留著**——有人加回來或漏刪一處都會紅。
    assert first["panel_order"] == list(
        ("brief", "argument", "bet", "downside", "wipeout",
         "headline", "fundamental", "research"))
    assert set(first["questions"]) == set(QUESTIONS)


def test_every_consumer_question_is_answered_by_some_panel() -> None:
    analyst = build_analyst_view(_full_view(with_criterion=True))
    answered = {question for panel in analyst.panels for question in panel.questions}
    assert answered == set(QUESTIONS), set(QUESTIONS) - answered


def test_information_hierarchy_puts_the_sentence_before_the_cells() -> None:
    """**首屏的單位是句不是格**（AGENTS「APP」）：短評在最前、稽核區的格子在後。

    ⚠ 2026-09-23（Phase 0 Step 0b.1）：本條原名 `..._puts_the_implied_return_first`，
    守的是「主流程終點是 implied return，它必須是讀者看到的第一個東西，entry 在最後」。
    那條主流程整條退役（估值鏈＋進場門檻）。**新的層級是 ROADMAP 的三層骨架**：
    第一層短評、第二層論證、第三層才是格。
    """
    analyst = build_analyst_view(_full_view(with_criterion=True))
    order = list(analyst.PANEL_ORDER)
    assert order[0] == "brief" and order[1] == "argument", order
    # 稽核區的原始數字（fundamental）與現價排在論證之後，不搶在句子前面。
    assert order.index("fundamental") > order.index("argument")
    assert order.index("headline") > order.index("argument")
    # 頭條不再掛任何問句——它只答「現在多少錢」，不答「划不划算」。
    assert analyst.headline.questions == ()
    assert "隱含報酬" not in analyst.headline.title and "目標" not in analyst.headline.title


# ---------------------------------------------------------------------------
# 9. 脆弱輸入：列入規則是宣告好的，不是新判斷
# ---------------------------------------------------------------------------

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


def test_panel_reason_comes_from_the_section_that_caused_the_status() -> None:
    """panel 的 reason 必須由**造成這個 status 的那一段**說出來，不是固定綁第一段。

    事發（2026-09-13，HEXA-B.ST）：六格營運假設都寫好了、`earnings_bridge` 算成功，
    但估值假設還沒寫 → `valuation` 缺席。`why` panel 的 status 取三段最差 ＝ `missing`，
    而 reason 固定取 `earnings_bridge`（成功的那一段）＝ `None`。
    使用者端於是看到「why：missing」沒有下文，而 `absence_kind` 明明宣告了 `not_yet_recorded`。

    這是 `AGENTS.md` APP 呈現契約禁的形狀：**缺席由產生它的那段程式自己宣告**——
    讓一個沒有缺席的 section 替別人的缺席發言，等於沒有宣告。
    """
    view = _view(fundamental_model=_run(index=_index()), today=TODAY)
    analyst = build_analyst_view(view)

    # ⚠ 2026-09-23（Phase 0 Step 0b.1）：原本主詞是 `why`（它取 earnings_bridge／valuation／
    # implied_return 三段最差）。`why` 已退役，改用仍然「多段取最嚴」的 `fundamental`
    # （internal_fundamentals／consensus／expectation_gap 三段）。**判準一字未改。**
    panel = next(p for p in analyst.panels if p.key == "fundamental")
    statuses = panel.source_statuses
    worst = panel.status
    assert len(statuses) > 1, "本條要驗的是多段取最嚴，fixture 必須有多段"
    assert worst in statuses.values(), "panel status 必須等於某一段的 status，不得是新判斷"
    if panel.reason is not None:
        culprits = [name for name, st in statuses.items() if st == worst]
        reasons = {getattr(view, name).meta.reason for name in culprits}
        assert panel.reason in reasons, "理由必須出自造成這個 status 的那一段"

    # 每一個 panel 都適用同一條規則：reason 若存在，必須是某個 source section 自己說的。
    for panel in analyst.panels:
        if not panel.reason:
            continue
        said_by = {getattr(view, name).meta.reason for name in panel.source_statuses}
        assert panel.reason in said_by, f"{panel.key} 的 reason 不是任何 source section 說的"
