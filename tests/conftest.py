"""Shared pytest fixtures for StockBotv2."""

from __future__ import annotations

import getpass
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FALLBACK_TEMPROOT = _REPO_ROOT / ".pytest_tmp" / "temproot"


def _default_temproot_is_usable() -> bool:
    """預設的 pytest temp root 能不能真的列出內容。

    pytest 在 `getbasetemp()` 會對 `<tempdir>/pytest-of-<user>` 做 `os.scandir`。
    該目錄若存在但當前使用者無權限，scandir 直接 PermissionError，於是**所有**用到
    `tmp_path` 的測試都在 setup 階段 error——本機實測 361 個（約全套四成）。

    只探測、不修復：`mkdir(exist_ok=True)` 會成功，所以「目錄能不能建」不是有效訊號，
    必須驗真正會被執行的那個動作（L13：驗產出，不驗回傳）。
    """
    root = Path(tempfile.gettempdir()) / f"pytest-of-{getpass.getuser() or 'unknown'}"
    if not root.exists():
        return True
    try:
        with os.scandir(root) as entries:
            next(iter(entries), None)
    except OSError:
        return False
    return True


def _ensure_usable_temproot() -> None:
    """預設 temp root 不可用時改道到 ignored 的 repo 內目錄。

    刻意寫成「偵測到不可用才改道」而不是無條件重導：本機那個目錄是被某次較高權限的
    行程建立的，帳號非系統管理員時無法刪除或改 ACL。之後若以系統管理員清掉它，
    這裡會自動回到 pytest 預設行為，不留下永久的隱性設定。
    """
    if os.environ.get("PYTEST_DEBUG_TEMPROOT") or _default_temproot_is_usable():
        return
    _FALLBACK_TEMPROOT.mkdir(parents=True, exist_ok=True)
    os.environ["PYTEST_DEBUG_TEMPROOT"] = str(_FALLBACK_TEMPROOT)


_ensure_usable_temproot()


@pytest.fixture(autouse=True)
def _isolate_event_watch_registry(tmp_path_factory, monkeypatch):
    """把 Event Watch registry 導向暫存檔。

    [321] 起 `leads.advance(..., "parked")` 會自動建立 watch（park 的當下就給它
    到期日，否則新線索又變回沒人管的等待）。那條路徑寫的是固定的
    `library/leads/event_watches.json`——若不隔離，任何 park 相關測試都會污染
    真實 registry。autouse 是刻意的：忘記隔離不會有錯誤訊息，只會靜默寫進真檔。
    """
    from engine_b import event_watch as ew

    target = tmp_path_factory.mktemp("event_watch") / "event_watches.json"
    monkeypatch.setattr(ew, "WATCHES_PATH", target)
    return target


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create an isolated Git repository with a deterministic identity."""

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "--initial-branch=master"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "StockBotv2 Tests"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@stockbot.invalid"],
        cwd=repo,
        check=True,
    )
    return repo
