"""**Request path 是不是真的只是一次讀檔？** 四種互相獨立的證明。

產品 invariant：**LLM changes cognition; APP reads cognition.**
一條 HTTP request **不得**跑 LLM、寫 authority、抓外部資料、跑任何金融模型，
也不得因為 cache miss／stale 就偷偷重建。

四種證明刻意不同源——任何一種單獨都會被繞過：

1. **import 靜態掃描**：serve 端三個模組的 import 清單是 allowlist。
2. **runtime 模組哨兵**：實際打一輪 request，斷言 `sys.modules` **沒有**多出任何模型模組。
   （靜態掃描擋不掉函式內的延遲 import。）
3. **檔案系統快照**：request 前後對 artifact 目錄與 private ledger 取雜湊，斷言一格未動。
   （這條擋的是「寫入」與「cache miss 自動重建」——兩者都會改到檔案。）
4. **socket 封殺**：request 期間 `socket.socket` 直接 raise，斷言回應照樣正確。
   （這條擋的是「打 API 抓現價／共識」與「連 Neo4j」。）
"""
from __future__ import annotations

import ast
import hashlib
import socket
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from webapp.api import create_app
from webapp.materialize import materialize_view
from webapp.store import ArtifactStore, StateArtifactStore

from test_webapp_materialize import fake_view
from test_webapp_ranking import fake_ranking_payload

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "webapp"

#: serve 端的三個模組。`materialize.py` 與 `__main__.py` **不在此列**——它們本來就會跑模型。
SERVE_MODULES = ("api.py", "store.py", "contracts.py")

SERVE_IMPORT_ALLOWLIST = {
    "api.py": {
        "__future__", "json", "os", "pathlib", "typing",
        "starlette.applications", "starlette.exceptions", "starlette.requests",
        "starlette.responses", "starlette.routing",
        ".contracts", ".store",
    },
    "store.py": {"__future__", "json", "os", "tempfile", "datetime", "pathlib", "typing", ".contracts"},
    "contracts.py": {"__future__", "hashlib", "json", "os", "dataclasses", "datetime", "typing"},
}

#: 一條 request 走完之後**絕對不該**出現在 `sys.modules` 裡的東西。
FORBIDDEN_RUNTIME_MODULES = (
    "anthropic", "openai", "neo4j", "yfinance", "requests", "psycopg2", "sqlite3",
    "alpha.valuation.model", "alpha.implied_return.model", "alpha.fundamental.model",
    "alpha.entry.model", "alpha.models.session_assessor", "alpha.refresh.resolver",
    "alpha.context", "alpha.providers.graph_neo4j", "alpha.providers.fundamentals",
    "briefing.alpha_view.builder", "briefing.alpha_view.sources", "briefing.analyst_view.compose",
    "webapp.materialize", "engine_c", "decision_lab", "fetchers",
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


@pytest.fixture()
def app_dir(tmp_path):
    """一個裝了三檔 artifact 的目錄（READY／ABSTAIN／PENCE，涵蓋三種缺席語意）。"""
    store = ArtifactStore(tmp_path)
    store.write(materialize_view(fake_view("READY")))
    store.write(materialize_view(fake_view(
        "ABSTAIN", fair_value=None, absence_kind="deliberate_abstention", readiness_state="blocked",
        blockers=["headline：missing"], reason="刻意不主張目標倍數：無法錨定")))
    store.write(materialize_view(fake_view(
        "PENCE", price=47.518, quote_unit="GBp", fair_value=None, readiness_state="blocked",
        absence_kind="upstream_unavailable", blockers=["headline：missing"], reason="上游缺內部 EPS")))
    # 跨標的 state artifact（ranking）住 analyst 目錄旁的 state/——與 create_app 的解析規則一致。
    StateArtifactStore(tmp_path / "state").write(fake_ranking_payload())
    return tmp_path


@pytest.fixture()
def served(app_dir):
    return TestClient(create_app(app_dir)), app_dir


# ---------------------------------------------------------------------------
# 證明 1：import 靜態掃描
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", SERVE_MODULES)
def test_serve_modules_import_nothing_that_can_recompute(name: str) -> None:
    """空跑檢查：在 `api.py` 加一行 `from alpha.valuation.model import build_valuation` → 這條會紅。"""
    extra = _imports(PKG / name) - SERVE_IMPORT_ALLOWLIST[name]
    assert not extra, f"{name} 多了不該在 request path 的相依：{sorted(extra)}"


def test_serve_modules_never_reach_the_materializer() -> None:
    """serve 端不得 import materialize——那是唯一會跑模型的模組。"""
    for name in SERVE_MODULES:
        source = (PKG / name).read_text(encoding="utf-8")
        assert "from .materialize" not in source and "import materialize" not in source, name


def _code_without_prose(path: Path) -> str:
    """只留**會執行的**原始碼：拿掉 docstring 與註解。

    ⚠ 這一步是必要的，不是方便：`api.py` 的 docstring 逐字列出「這裡不准出現什麼」，
    而那份清單本身會命中 token 掃描——一個把說明文字讀成違規的檢查，攔下的不是它想攔的
    東西（L15-1：該修的是它問問題的方式）。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)                     and isinstance(body[0].value.value, str):
                body[0].value.value = ""
    return ast.unparse(tree)


def test_serve_modules_contain_no_model_tokens() -> None:
    """空跑檢查：在 `store.py` 的**程式碼**（非註解）寫下 `build_valuation` → 這條會紅。"""
    forbidden = ("build_valuation", "build_implied_return", "build_fundamental_model",
                 "fetch_alpha_investment_view", "build_analyst_view", "resolve_refresh",
                 "anthropic", "Anthropic", "messages.create")
    for name in SERVE_MODULES:
        code = _code_without_prose(PKG / name)
        hits = [token for token in forbidden if token in code]
        assert not hits, (name, hits)


# ---------------------------------------------------------------------------
# 證明 2：runtime 模組哨兵（擋函式內的延遲 import）
# ---------------------------------------------------------------------------

def test_a_full_request_round_imports_no_model_module(served) -> None:
    client, _ = served
    before = set(sys.modules)
    for path in ("/api/v1/health", "/api/v1/meta", "/api/v1/stocks",
                 "/api/v1/stocks/READY", "/api/v1/stocks/ABSTAIN", "/api/v1/stocks/PENCE",
                 "/api/v1/stocks/NOPE", "/api/v1/ranking", "/", "/static/app.js"):
        client.get(path)
    added = set(sys.modules) - before
    leaked = sorted(m for m in added
                    if any(m == f or m.startswith(f + ".") for f in FORBIDDEN_RUNTIME_MODULES))
    assert not leaked, f"request path 載入了模型／IO 模組：{leaked}"


# ---------------------------------------------------------------------------
# 證明 3：檔案系統快照（擋寫入與 cache-miss 自動重建）
# ---------------------------------------------------------------------------

def _tree_digest(root: Path) -> str:
    parts = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            parts.append(f"{path.relative_to(root)}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def test_tree_digest_actually_notices_a_change(tmp_path) -> None:
    """守衛的守衛：`_tree_digest` 若對任何改動都回同一個值，下面兩條就是空跑。"""
    before = _tree_digest(tmp_path)
    (tmp_path / "x.json").write_text("{}", encoding="utf-8")
    after = _tree_digest(tmp_path)
    assert after != before
    (tmp_path / "x.json").write_text('{"a":1}', encoding="utf-8")
    assert _tree_digest(tmp_path) != after


def test_requests_change_not_a_single_byte_on_disk(served) -> None:
    client, directory = served
    before = _tree_digest(directory)
    for path in ("/api/v1/stocks", "/api/v1/stocks/READY", "/api/v1/stocks/ABSTAIN", "/api/v1/ranking"):
        assert client.get(path).status_code == 200
    assert _tree_digest(directory) == before


def test_cache_miss_returns_503_instead_of_rebuilding(served) -> None:
    """**cache miss 不得偷偷重建。** 沒有 artifact 就誠實說沒有，並指出重建是別條責任鏈的事。"""
    client, directory = served
    before = _tree_digest(directory)
    response = client.get("/api/v1/stocks/NEVERBUILT")
    assert response.status_code == 503
    body = response.json()["error"]
    assert body["kind"] == "artifact_unavailable"
    assert "materialize" in body["remedy"]
    # 「讀不到」與「這檔沒有研究結論」不得同形（L12）
    assert "沒有研究結論" in body["note"]
    assert _tree_digest(directory) == before
    assert not (directory / "NEVERBUILT.json").exists()


def test_stale_artifact_is_served_not_rebuilt(served, monkeypatch) -> None:
    client, directory = served
    monkeypatch.setenv("STOCKBOT_APP_MAX_AGE_HOURS", "0.0000001")
    before = _tree_digest(directory)
    body = client.get("/api/v1/stocks/READY").json()
    assert body["freshness"]["state"] == "stale"
    assert body["overview"]["future_target"]["value"] == 100.0     # 照樣回內容
    assert _tree_digest(directory) == before                        # 但沒有重建


def test_private_authority_is_never_touched_by_a_request(served) -> None:
    """request path 不得碰 private ledger——連讀都不該。"""
    client, _ = served
    ledger = ROOT / "library" / "private"
    before = _tree_digest(ledger) if ledger.is_dir() else None
    client.get("/api/v1/stocks")
    after = _tree_digest(ledger) if ledger.is_dir() else None
    assert after == before


# ---------------------------------------------------------------------------
# 證明 4：socket 封殺（擋外部抓取與 DB 連線）
# ---------------------------------------------------------------------------

def test_requests_still_work_with_networking_completely_disabled(app_dir, monkeypatch) -> None:
    """封殺**對外連線**後，request 仍然完整正確——所以它從來沒有靠網路拿過任何東西。

    ⚠ 攔的是 `connect`／`create_connection` 而不是 socket 建構子：TestClient 的 event loop
    自己要用一對 loopback socket，攔建構子會攔到測試腳手架本身而不是被測物
    （L15-1：gate 攔下的必須是它想攔的東西）。連線一律 raise，涵蓋 yfinance／EDGAR／Neo4j
    bolt／任何 HTTP provider。
    """
    with TestClient(create_app(app_dir)) as client:
        client.get("/api/v1/health")          # 先讓 event loop 建好自己的 self-pipe

        def refuse(*args, **kwargs):
            raise AssertionError("request path 嘗試開對外連線——不得抓現價／共識，也不得連 Neo4j")

        monkeypatch.setattr(socket.socket, "connect", refuse)
        monkeypatch.setattr(socket, "create_connection", refuse)
        # gate 自我量測（L14：未量測的機制不得享有默認信任）——先證明封殺真的生效，
        # 否則「網路關掉還是綠的」可能只是因為根本沒關掉。
        with pytest.raises(AssertionError):
            socket.create_connection(("127.0.0.1", 9))

        body = client.get("/api/v1/stocks/READY").json()
        assert body["overview"]["implied_return"]["simple"]["value"] == -0.2
        assert client.get("/api/v1/stocks").json()["count"] == 3
        assert client.get("/api/v1/ranking").json()["kind"] == "ranking"
        assert client.get("/api/v1/stocks/NEVERBUILT").status_code == 503


# ---------------------------------------------------------------------------
# 只讀：沒有任何寫入端點
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("path", ["/api/v1/stocks", "/api/v1/stocks/READY", "/api/v1/ranking", "/"])
def test_no_mutation_verb_is_routed_anywhere(served, method: str, path: str) -> None:
    client, _ = served
    assert getattr(client, method)(path).status_code == 405


def test_api_response_is_semantically_equal_to_the_artifact(served) -> None:
    """API 不是第二份投影：回的就是 artifact 本身 ＋ 兩個唯讀附註。"""
    client, directory = served
    body = client.get("/api/v1/stocks/READY").json()
    stored, _ = ArtifactStore(directory).read("READY")
    extra = set(body) - set(stored)
    assert extra == {"freshness", "correlation_warning"}
    for key in stored:
        assert body[key] == stored[key], key
