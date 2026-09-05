"""Alpha Card renderer 的純度：只排版、不決策、不取數、不把缺席印成 0。"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from briefing.alpha_view import render_alpha_cards, render_alpha_investment_view_markdown
from tests.test_alpha_investment_view import _FakeFundamentals, _view

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "briefing" / "alpha_view" / "render.py"
CONTRACTS = ROOT / "briefing" / "alpha_view" / "contracts.py"
BUILDER = ROOT / "briefing" / "alpha_view" / "builder.py"

#: renderer 只准依賴這些。多一個 import 就代表「view 已 presentation-independent」是假的。
RENDER_ALLOWED_IMPORTS = {"__future__", "datetime", "typing", "shared.markdown",
                          "briefing.alpha_view.contracts", ".contracts"}
#: 這些 token 出現在 renderer 就是業務邏輯回流：重排、重算、重新決策。
RENDER_FORBIDDEN_TOKENS = (
    "sorted(", ".sort(", "min(", "max(", "sum(", "ordering_key", "rank_bottlenecks",
    "actionable_now", "compose_signal", "build_research_context", "assess_entry",
    "expected_return =", "import engine_c", "import neo4j", "decision_lab",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.add(("." * node.level) + (node.module or ""))
    return out


def test_renderer_only_imports_contracts_and_markdown_primitives() -> None:
    """空跑檢查：在 render.py 加一行 `from engine_c.db import get_conn` → 這條會紅。"""
    extra = _imports(RENDER) - RENDER_ALLOWED_IMPORTS
    assert not extra, f"renderer 多了不該有的相依：{sorted(extra)}"


def test_contracts_module_is_pure_stdlib() -> None:
    stdlib = {"dataclasses", "datetime", "enum", "typing", "__future__"}
    assert _imports(CONTRACTS) <= stdlib, _imports(CONTRACTS)


def test_builder_does_not_touch_io_layers() -> None:
    """builder 是純函式：所有 authority 輸出由 sources 注入，它自己不開任何連線。"""
    forbidden_roots = {"neo4j", "sqlite3", "engine_c", "decision_lab", "identity", "fetchers", "query"}
    roots = {name.split(".")[0] for name in _imports(BUILDER)}
    assert not (roots & forbidden_roots), roots & forbidden_roots


def test_renderer_contains_no_ranking_or_business_tokens() -> None:
    source = RENDER.read_text(encoding="utf-8")
    hits = [token for token in RENDER_FORBIDDEN_TOKENS if token in source]
    assert not hits, f"renderer 出現業務邏輯 token：{hits}"
    # 沒有任何「拿分數／成長率做數值比較」的敘述
    assert not re.search(r"\b(effective|declared|growth|gap|score)\b\s*[<>]=?\s*\d", source)


def test_missing_and_not_modeled_render_as_words_not_zero() -> None:
    text = render_alpha_investment_view_markdown(_view())
    eps_line = next(line for line in text.splitlines() if "內部稀釋 EPS 估計" in line)
    assert "缺料" in eps_line                                   # 有能力、本次沒資料
    assert not re.search(r"[：:]\s*0(\.0+)?%?(\s|$)", eps_line)
    fcf_line = next(line for line in text.splitlines() if "內部 FCF 估計" in line)
    assert "尚未建模" in fcf_line                               # bridge v1 沒有現金流量表
    margin_line = next(line for line in text.splitlines() if "市場隱含利潤率" in line)
    assert "尚未建模" in margin_line and "0%" not in margin_line.replace("不是 0%", "")
    q3_line = next(line for line in text.splitlines() if "Q3 盈餘曝險" in line)
    assert "缺料" in q3_line and "不是 0" in q3_line


def _unescape(text: str) -> str:
    """`shared.markdown.markdown_text` 會把 `_`／`.` 轉義；比對語意時先還原。"""
    return text.replace("\\", "")


def test_loss_making_company_renders_reason_not_zero_growth() -> None:
    text = render_alpha_investment_view_markdown(_view(fundamentals=_FakeFundamentals(trailing_pe=None)))
    line = _unescape(next(line for line in text.splitlines() if "市場隱含 EPS 成長" in line))
    assert "pe_trailing_missing" in line
    assert "+0.0%" not in line and "0.0%" not in line


def test_renderer_labels_each_datum_with_its_knowledge_kind() -> None:
    text = render_alpha_investment_view_markdown(_view())
    assert "〔確定性規則｜`alpha://context/structural_score`" in text
    assert "〔session 判斷｜`alpha://session_assessor`" in text
    assert "〔粗略代理｜`alpha://context/implied_valuation`" in text
    assert "〔散文｜`decision_lab://coverage_assessments`" in text
    assert "structural_causal_model" in text and "不是 financial causal model" in text
    assert "scenario_type=narrative" in text
    assert "圖例" in text


def test_renderer_is_deterministic_and_covers_every_section() -> None:
    view = _view()
    first = render_alpha_investment_view_markdown(view)
    assert first == render_alpha_investment_view_markdown(view)
    for heading in ("## 0. 能力地圖", "## 1. Variant view", "## 2. 結構 thesis", "## 3. 因果路徑",
                    "## 4. 財務觀測", "## 5. 共識", "## 6. 價格隱含預期", "## 7. 內部基本面",
                    "## 8. Earnings bridge", "## 9. Expectation gap", "## 10. 催化劑",
                    "## 11. 證偽條件", "## 12. 情境", "## 13a. 預期報酬", "## 13b. 下檔",
                    "## 13c. 進場邏輯", "## 14. 證據與 provenance", "## 15. 新鮮度總表"):
        assert heading in first, heading


def test_alpha_cards_distinguish_absent_none_and_empty() -> None:
    assert render_alpha_cards(None, present=False) == []
    absent = "\n".join(render_alpha_cards(None))
    assert "未提供" in absent and "不是「沒有候選」" in absent
    empty = "\n".join(render_alpha_cards([]))
    assert "無候選可摘要" in empty and "未提供" not in empty


def test_alpha_cards_render_unknowns_as_unknown_not_zero() -> None:
    from briefing.alpha_view import compact_card

    card = compact_card(_view(fundamentals=_FakeFundamentals(trailing_pe=None)))
    text = "\n".join(render_alpha_cards([card]))
    row = _unescape(next(line for line in text.splitlines() if line.startswith("| co:coherent")))
    assert "未知（pe_trailing_missing" in row
    assert "+0.0%" not in row
    assert "未知" in row                                   # Q3／Q5 unknown
    unavailable = "\n".join(render_alpha_cards([{"ticker": "XYZ", "status": "unavailable", "reason": "TimeoutError"}]))
    assert "讀不到" in unavailable and "TimeoutError" in unavailable
