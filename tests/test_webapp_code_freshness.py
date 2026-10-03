"""APP 自己偵測「跑的是舊程式」（Phase 6 Step 6.7b；plan 2026-10-02-002 §8 b，Phase 5 #11）。

事發：Phase 5 Step 5.2 發現長駐 APP（09-10 起跑）一路用 09-10 的程式——新頁面全回 404、positions 回 503，畫面上沒有任何
東西說「我是舊的」。守三件事：
1. 啟動時記一次程式指紋（`webapp/**/*.py` 與 `webapp/static/*` 的最大 mtime＋檔數），`/health` 每次比對；改了任何一支、
   多了一支（即使 mtime 是舊的）就是 stale；`__pycache__` 與 static 以外的非 .py 不算。
2. 只做本機 stat：不透露路徑、不寫任何東西（request path 規則由 tests/test_webapp_request_path.py 守著）。
3. 首頁頂端的橫幅：stale 印「APP 跑的是 <啟動時間> 的程式，之後程式有更新——請重啟」；health 沒有 `code` 那一格
   （伺服器比畫面舊）也要印。
"""
from __future__ import annotations

import os
from pathlib import Path

from starlette.testclient import TestClient

from webapp.api import create_app

ROOT = Path(__file__).resolve().parents[1]


def _code_root(tmp_path: Path) -> Path:
    root = tmp_path / "code"
    (root / "static").mkdir(parents=True)
    (root / "api.py").write_text("# api\n", encoding="utf-8")
    (root / "store.py").write_text("# store\n", encoding="utf-8")
    (root / "static" / "app.js").write_text("// app\n", encoding="utf-8")
    return root


def _health(tmp_path: Path, root: Path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    client = TestClient(create_app(artifacts, code_root=root))
    return client, lambda: client.get("/api/v1/health").json()["code"]


def test_right_after_start_the_code_is_not_stale(tmp_path) -> None:
    root = _code_root(tmp_path)
    _client, code = _health(tmp_path, root)
    got = code()
    assert got["stale"] is False
    assert got["loaded"]["files"] == got["current"]["files"] == 3
    assert got["started_at"] and got["loaded"]["newest_at"]


def test_a_python_file_changed_after_start_makes_health_stale(tmp_path) -> None:
    root = _code_root(tmp_path)
    _client, code = _health(tmp_path, root)
    later = os.stat(root / "api.py").st_mtime + 120
    os.utime(root / "api.py", (later, later))
    got = code()
    assert got["stale"] is True
    assert got["loaded"]["newest_at"] != got["current"]["newest_at"]


def test_a_new_file_with_an_old_mtime_still_counts(tmp_path) -> None:
    """從別處複製進來的新模組 mtime 可能比啟動時還舊——檔數抓得到。"""
    root = _code_root(tmp_path)
    _client, code = _health(tmp_path, root)
    new = root / "contracts.py"
    new.write_text("# new\n", encoding="utf-8")
    old = os.stat(root / "store.py").st_mtime - 3600
    os.utime(new, (old, old))
    got = code()
    assert got["stale"] is True and got["current"]["files"] == 4


def test_static_assets_count_but_caches_and_other_files_do_not(tmp_path) -> None:
    root = _code_root(tmp_path)
    _client, code = _health(tmp_path, root)
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "api.cpython-314.pyc").write_bytes(b"\0")
    (root / "notes.txt").write_text("not code\n", encoding="utf-8")
    assert code()["stale"] is False                       # 快取與 static 以外的非 .py 不算
    later = os.stat(root / "static" / "app.js").st_mtime + 120
    os.utime(root / "static" / "app.js", (later, later))
    assert code()["stale"] is True                        # static 裡的任何一個檔都算


def test_the_code_block_reveals_no_paths(tmp_path) -> None:
    root = _code_root(tmp_path)
    client, _code = _health(tmp_path, root)
    text = client.get("/api/v1/health").text
    assert str(root) not in text and str(root).replace("\\", "/") not in text and str(tmp_path) not in text


def test_the_default_root_is_the_webapp_package(tmp_path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    got = TestClient(create_app(artifacts)).get("/api/v1/health").json()["code"]
    py = [p for p in (ROOT / "webapp").rglob("*.py") if "__pycache__" not in p.parts]
    static = [p for p in (ROOT / "webapp" / "static").iterdir() if p.is_file()]
    assert got["loaded"]["files"] == len(py) + len(static)
    assert got["stale"] is False


def test_the_front_page_banner_reads_health_and_also_covers_an_older_server() -> None:
    """前端：每次換頁問一次 health；stale 印重啟句；health 沒有 `code`（伺服器比畫面舊）也印。不排序、不算術。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    body = source.split("async function checkCodeFreshness()", 1)[1].split("\n}\n", 1)[0]
    assert "`${API}/health`" in body
    assert "的程式，之後程式有更新——請重啟" in body
    assert "if (!code)" in body and "健康檢查沒有程式指紋" in body
    route = source.split("async function route()", 1)[1].split("\n}\n", 1)[0]
    assert "checkCodeFreshness();" in route
