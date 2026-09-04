from __future__ import annotations

import subprocess
from pathlib import Path

import json

from scripts.publish_daily_state import (
    EVIDENCE_PREFIX, MAX_EVIDENCE_PER_RUN, STATE_PATHS, publish_daily_state,
)


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(tmp_path, "init", "-b", "master", str(work))
    _git(work, "config", "user.name", "Test")
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "remote", "add", "origin", str(remote))
    for relpath in (*STATE_PATHS, "README.md"):
        path = work / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("initial\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "initial")
    _git(work, "push", "-u", "origin", "master")
    return work, remote


def test_publishes_only_daily_state_and_preserves_unrelated_changes(tmp_path: Path) -> None:
    work, remote = _repo(tmp_path)
    (work / STATE_PATHS[0]).write_text("changed\n", encoding="utf-8")
    (work / "README.md").write_text("user work\n", encoding="utf-8")

    result = publish_daily_state(work)

    assert result == {"status": "pushed", "committed": True, "pushed": True}
    assert _git(work, "show", "--name-only", "--pretty=format:", "HEAD") == STATE_PATHS[0]
    assert "README.md" in _git(work, "status", "--porcelain")
    assert _git(remote, "show", "master:library/leads/pending_leads.json") == "changed"


def test_pathset_contract_is_exactly_four_leads_state_files() -> None:
    """2026-09-02 sandbox impact review ④：明確斷言允許項全集與順序無關的邊界。

    pathset 由二擴四（event watch registry＋假設對照）；擴充只可發生在
    `library/leads/` 的 state 檔，且必須逐一列名——不允許 glob 或整目錄。"""
    assert STATE_PATHS == (
        "library/leads/pending_leads.json",
        "library/leads/todo_pool.json",
        "library/leads/event_watches.json",
        "library/leads/hypotheses.json",
    )


def test_publishes_watch_state_but_not_adjacent_leads_file(tmp_path: Path) -> None:
    """相鄰排除：同目錄的非 state 檔（如 backfill 快照）不得被 publisher 帶走。"""
    work, remote = _repo(tmp_path)
    adjacent = work / "library" / "leads" / "backfill_snapshot.json"
    adjacent.write_text("initial\n", encoding="utf-8")
    _git(work, "add", str(adjacent))
    _git(work, "commit", "-m", "user snapshot")
    _git(work, "push", "origin", "master")

    (work / "library" / "leads" / "event_watches.json").write_text(
        "watch changed\n", encoding="utf-8"
    )
    adjacent.write_text("user work in progress\n", encoding="utf-8")

    result = publish_daily_state(work)

    assert result == {"status": "pushed", "committed": True, "pushed": True}
    committed = _git(work, "show", "--name-only", "--pretty=format:", "HEAD")
    assert committed == "library/leads/event_watches.json"
    assert "backfill_snapshot.json" in _git(work, "status", "--porcelain")
    assert (
        _git(remote, "show", "master:library/leads/event_watches.json")
        == "watch changed"
    )


def test_refuses_to_push_unrelated_existing_commit(tmp_path: Path) -> None:
    work, _ = _repo(tmp_path)
    (work / "README.md").write_text("committed user work\n", encoding="utf-8")
    _git(work, "commit", "-am", "user commit")
    (work / STATE_PATHS[1]).write_text("changed\n", encoding="utf-8")

    assert publish_daily_state(work)["status"] == "guard_unpushed_commits"


def test_refuses_when_index_is_not_empty(tmp_path: Path) -> None:
    work, _ = _repo(tmp_path)
    (work / "README.md").write_text("staged\n", encoding="utf-8")
    _git(work, "add", "README.md")

    assert publish_daily_state(work)["status"] == "guard_staged_changes"


# ---------------------------------------------------------------------------
# 追源證據隨引用一起發布（2026-09-04 sandbox impact review）
# ---------------------------------------------------------------------------

def _write_leads(work: Path, *refs: str) -> None:
    """把 refs 寫成 lead 的 `trace_attempts_ref`。"""
    (work / STATE_PATHS[0]).write_text(json.dumps({
        "schema_version": 1,
        "leads": {f"lead_{i}": {"status": "parked", "trace_attempts_ref": ref}
                  for i, ref in enumerate(refs)},
    }, ensure_ascii=False), encoding="utf-8")


def _raw(work: Path, name: str, body: str = "filing text\n") -> str:
    ref = f"{EVIDENCE_PREFIX}{name}"
    path = work / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return ref


def test_referenced_evidence_ships_with_the_state_that_references_it(tmp_path: Path) -> None:
    """**引用與被引用的檔案必須在同一筆提交裡。**

    分兩筆提交會留下一個「引用已推、檔案未推」的窗口；完全不提交就是
    2026-09-04 實測的那個結果——3 筆 `trace_attempts_ref` 有 2 筆永久消失。
    """
    work, remote = _repo(tmp_path)
    ref = _raw(work, "nvda_8_k_20260903.txt")
    _write_leads(work, ref)

    result = publish_daily_state(work)

    assert result == {"status": "pushed", "committed": True, "pushed": True}
    committed = set(_git(work, "show", "--name-only", "--pretty=format:", "HEAD").split())
    assert committed == {STATE_PATHS[0], ref}
    assert _git(remote, "show", f"master:{ref}") == "filing text"


def test_unreferenced_files_in_the_same_directory_stay_local(tmp_path: Path) -> None:
    """**相鄰排除**：`library/raw/` 不是整目錄放行。

    只有即將發布的 state 指名引用的檔案會被帶走；同目錄其他下載內容留在本機。
    這是本次擴充與「把 library/raw/ 加進 pathset」的關鍵差別。
    """
    work, _ = _repo(tmp_path)
    referenced = _raw(work, "cited.txt")
    orphan = _raw(work, "downloaded_but_not_cited.txt")
    _write_leads(work, referenced)

    assert publish_daily_state(work)["status"] == "pushed"
    committed = set(_git(work, "show", "--name-only", "--pretty=format:", "HEAD").split())
    assert referenced in committed
    assert orphan not in committed
    assert "downloaded_but_not_cited.txt" in _git(work, "status", "--porcelain")


def test_private_and_traversal_references_are_never_shipped(tmp_path: Path) -> None:
    """`library/private/` 與路徑穿越一律不收——前者刻意不進 Git，後者是逃逸。"""
    work, _ = _repo(tmp_path)
    private = work / "library" / "private" / "secret.txt"
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text("secret\n", encoding="utf-8")
    escape = _raw(work, "ok.txt")
    _write_leads(work, "library/private/secret.txt",
                 f"{EVIDENCE_PREFIX}../README.md", escape)

    assert publish_daily_state(work)["status"] == "pushed"
    committed = set(_git(work, "show", "--name-only", "--pretty=format:", "HEAD").split())
    assert committed == {STATE_PATHS[0], escape}


def test_dangling_reference_does_not_block_publishing(tmp_path: Path) -> None:
    """引用指向不存在的檔案時**照常發布 state**，只是帶不走那一份。

    fail closed 在這裡是錯的：擋住整輪 publish 會讓 daily 的產出全部留在本機，
    代價遠大於一個 audit 抓得到的斷鏈（`audit invariants` 的 Orphans 守著它）。
    """
    work, _ = _repo(tmp_path)
    _write_leads(work, f"{EVIDENCE_PREFIX}never_downloaded.txt")

    assert publish_daily_state(work)["status"] == "pushed"
    assert _git(work, "show", "--name-only", "--pretty=format:", "HEAD") == STATE_PATHS[0]


def test_only_existing_files_enter_the_derived_set(tmp_path: Path) -> None:
    """直接測推導函式本身：不存在的引用**不得進入集合**。

    ⚠ 這條看似與上一條重複，其實不是——上一條測的是 `publish_daily_state` 的
    最終結果，而斷鏈引用就算誤入集合，`git status -- <不存在的路徑>` 也回空，
    最終結果**完全相同**。於是上一條在突變下綠著通過（實測 #35 空跑）。
    要看見差別，必須直接觀察推導出來的集合。
    """
    from scripts.publish_daily_state import _referenced_evidence

    work, _ = _repo(tmp_path)
    real = _raw(work, "exists.txt")
    _write_leads(work, real, f"{EVIDENCE_PREFIX}never_downloaded.txt")

    assert _referenced_evidence(work) == [real]


def test_evidence_volume_is_capped(tmp_path: Path) -> None:
    """一輪帶太多檔代表發生了別的事——fail closed，不照單全收。"""
    work, _ = _repo(tmp_path)
    refs = [_raw(work, f"f{i}.txt") for i in range(MAX_EVIDENCE_PER_RUN + 1)]
    _write_leads(work, *refs)

    assert publish_daily_state(work)["status"] == "guard_evidence_volume"


def test_evidence_is_still_not_part_of_the_pathset(tmp_path: Path) -> None:
    """擴充的是**推導出來的集合**，不是 pathset 本身。

    `STATE_PATHS` 仍是四個逐一列名的檔案；`library/raw/` 沒有被加進去，
    所以「state 沒提到的檔案」在任何情況下都不會被無人值守排程提交。
    """
    assert all(not p.startswith(EVIDENCE_PREFIX) for p in STATE_PATHS)
    assert EVIDENCE_PREFIX not in STATE_PATHS
