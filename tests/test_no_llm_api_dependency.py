"""production 碼不得呼叫 LLM API（2026-09-04 使用者定案：不再使用 API）。

⚠ **這條剎車守的不是「省錢」，是「產出來源可稽核」。** 實際流程早就是
session-in-the-loop：`assessment-scaffold` → session 寫判斷 → `reassess --assessment`
（268 筆紀錄佐證）。留著 API 分支的代價是**同一個產出有兩條來源**，而其中一條
不留 receipt——下游無從分辨這份 memo 是誰寫的（L12：一個表示兩種語意）。
"""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: 掃描的 production 套件與腳本。⚠ **不含 `tests/`**——測試提到套件名是正當的。
_PRODUCTION = (
    "alpha", "engine_b", "engine_c", "engine_d_runtime", "decision_lab", "loader",
    "query", "thesis", "fetchers", "portfolio", "risk", "shared", "identity",
    "crons", "scripts", "briefing", "intake", "storage", "audit", "mcp_server",
)

#: 已知的 LLM SDK。新增一個 provider 就加一項——這是白名單的反面，
#: 但它的失效方式是「漏掉新 provider」而不是「誤報」，所以可以接受。
_LLM_SDKS = frozenset({"anthropic", "openai", "google.generativeai", "cohere", "mistralai"})


def _python_files():
    for name in _PRODUCTION:
        base = ROOT / name
        if base.is_dir():
            yield from base.rglob("*.py")
    for script in ROOT.glob("*.py"):
        yield script


def _imported_roots(path: pathlib.Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):  # pragma: no cover
        return set()
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module)
    return roots


def test_no_production_module_imports_an_llm_sdk() -> None:
    """**production 碼一個 LLM SDK import 都不得有。**

    空跑檢查：在 `extract.py` 加回 `from anthropic import Anthropic` → 這條會紅。
    """
    offenders = [
        f"{path.relative_to(ROOT).as_posix()} → {module}"
        for path in _python_files()
        for module in _imported_roots(path)
        if module.split(".")[0] in _LLM_SDKS
    ]
    assert not offenders, (
        "production 碼不得呼叫 LLM API（2026-09-04 定案，改走 session-in-the-loop）：\n"
        + "\n".join(offenders)
    )


def test_no_production_module_reads_an_llm_api_key() -> None:
    """連 API key 都不該讀——讀得到就代表還有一條走得通的 API 路徑。

    ⚠ 只看 `os.environ` 的**實際取值**，不看註解與 docstring：那兩個地方刻意留著
    「已移除」的紀錄（同 beta 訊號、luna-reviewer 的處理），把它們也算違規會讓
    這條測試逼人刪掉移除理由——而那正是下次被原樣加回來的原因。
    """
    keys = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY")
    offenders: list[str] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in keys:
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    assert not offenders, (
        "production 碼不得讀 LLM API key（註解／docstring 的移除紀錄不算）：\n"
        + "\n".join(offenders)
    )


def test_the_two_retired_entry_points_kept_their_deterministic_half() -> None:
    """⚠ 拔 API 時**不得順手拔掉後處理**——那才是這兩支不可替代的部分。

    `extract.py` 的 source id 前綴是 L6 的教訓（局部 ID 跨文件 MERGE 會命名空間衝突）；
    `generate_lane_memo.py` 的 envelope 驗證與 evidence gate 是 L8 的執行點。
    兩者都與「哪個模型產出 JSON」完全無關，所以拔 API 時它們必須原封不動。
    """
    extract_src = (ROOT / "extract.py").read_text(encoding="utf-8")
    assert "_prefix_source_ids" in extract_src
    assert "def ingest_response" in extract_src
    assert "def write_scaffold" in extract_src

    memo_src = (ROOT / "thesis" / "generate_lane_memo.py").read_text(encoding="utf-8")
    assert "validate_envelope" in memo_src
    assert "evaluate_evidence_gates" in memo_src
    assert "scaffold_path" in memo_src


def test_scaffold_and_response_are_mutually_exclusive() -> None:
    """兩段必須擇一，**不得預設走某一段**。

    沉默地挑一段會讓使用者以為抽取完成了——而它其實只產了一份提示（L13：
    成功與未完成不得在同一個訊號上同形）。
    """
    extract_src = (ROOT / "extract.py").read_text(encoding="utf-8")
    assert "必須且只能擇一" in extract_src
    memo_src = (ROOT / "thesis" / "generate_lane_memo.py").read_text(encoding="utf-8")
    assert "必須且只能擇一" in memo_src
