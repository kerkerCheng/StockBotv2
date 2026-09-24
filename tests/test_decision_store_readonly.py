"""舊 Decision Store 的唯讀入口（Phase 1 Step 1.1）：凍結由連線層強制，不靠讀取端的用法。

守的機制：A5 舊店凍結後（G12），所有讀取端都走 `mode=ro`——寫入在連線層就被拒絕、
DB 不存在時明確缺席而不是建空庫、讀完關閉不會把 `-wal` checkpoint 回 `.db`（sha256 不變）。
"""
from __future__ import annotations

import ast
import hashlib
import sqlite3
from pathlib import Path

import pytest

from decision_lab.bootstrap import default_store_path, open_readonly_store
from decision_lab.store import DecisionStore, DecisionStoreAbsent
from storage.relational import initialize_private_root

ROOT = Path(__file__).resolve().parents[1]


def _seeded_db(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    db_path = private_root / "decision_lab" / "decision_lab.db"
    store = DecisionStore.open(db_path, private_root=private_root, repo_root=repo)
    try:
        store.ensure_cohort(
            dedupe_key="claim:cw-laser",
            company_id="co:sivers_semiconductors",
            research_ticker="SIVE.ST",
        )
    finally:
        store.close()
    return repo, db_path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_readonly_store_rejects_every_write_at_the_connection(tmp_path: Path) -> None:
    _repo, db_path = _seeded_db(tmp_path)
    store = DecisionStore.open_readonly(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            store.ensure_cohort(
                dedupe_key="claim:another",
                company_id="co:coherent",
                research_ticker="COHR",
            )
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            store._conn.execute(  # noqa: SLF001 — 繞過方法直接寫，連線層仍要擋
                "UPDATE decision_store_meta SET value = 'x' WHERE key = 'schema_version'"
            )
    finally:
        store.close()


def test_readonly_store_reads_and_leaves_the_db_bytes_unchanged(tmp_path: Path) -> None:
    _repo, db_path = _seeded_db(tmp_path)
    before = _sha(db_path)
    store = DecisionStore.open_readonly(db_path)
    try:
        assert "decision_cohorts" in store.table_names()
        assert store.table_count("decision_cohorts") == 1
        store.capital_expression_counters()
        store.list_operational_cohorts(as_of="2026-09-24T00:00:00+00:00")
    finally:
        store.close()
    assert _sha(db_path) == before


def _snapshot_with_pending_wal(tmp_path: Path, name: str) -> Path:
    """複製一份「`-wal` 裡還有未併回的交易、且沒有任何連線開著」的庫——就是本機舊店的樣子
    （`library/private/decision_lab/` 下 `.db-wal` 與 `.db` 並存）。"""
    repo, db_path = _seeded_db(tmp_path / name)
    writer = DecisionStore.open(
        db_path, private_root=repo / "library" / "private", repo_root=repo
    )
    target_dir = tmp_path / f"{name}_snapshot"
    target_dir.mkdir()
    try:
        writer.ensure_cohort(
            dedupe_key="claim:pending-in-wal",
            company_id="co:coherent",
            research_ticker="COHR",
        )
        for suffix in ("", "-wal", "-shm"):
            source = Path(f"{db_path}{suffix}")
            (target_dir / f"decision_lab.db{suffix}").write_bytes(source.read_bytes())
    finally:
        writer.close()
    assert (target_dir / "decision_lab.db-wal").stat().st_size > 0
    return target_dir / "decision_lab.db"


def test_readonly_store_does_not_checkpoint_pending_wal_into_the_db(tmp_path: Path) -> None:
    """可寫連線在最後一個 handle 關閉時把 `-wal` 併回 `.db`；唯讀連線不得這樣做。"""
    db = _snapshot_with_pending_wal(tmp_path, "ro")
    before = _sha(db)
    reader = DecisionStore.open_readonly(db)
    try:
        assert reader.table_count("decision_cohorts") == 2  # 讀得到 WAL 裡那筆
    finally:
        reader.close()
    assert _sha(db) == before

    # 對照組：同樣的庫以可寫連線讀一次再關，`.db` 就變了——上面的斷言不是恆綠。
    control = _snapshot_with_pending_wal(tmp_path, "rw")
    control_before = _sha(control)
    conn = sqlite3.connect(control)
    conn.execute("SELECT COUNT(*) FROM decision_cohorts").fetchone()
    conn.close()
    assert _sha(control) != control_before


def test_missing_db_is_an_explicit_absence_and_creates_nothing(tmp_path: Path) -> None:
    missing = tmp_path / "repo" / "library" / "private" / "decision_lab" / "decision_lab.db"
    with pytest.raises(DecisionStoreAbsent):
        DecisionStore.open_readonly(missing)
    with pytest.raises(DecisionStoreAbsent):
        open_readonly_store(repo_root=tmp_path / "repo")
    assert not (tmp_path / "repo").exists()
    assert default_store_path(tmp_path / "repo") == missing.resolve()


def test_no_production_code_opens_the_frozen_store_writable() -> None:
    """凍結後寫入路徑只剩測試：非測試程式不得呼叫 `DecisionStore.open(`，
    bootstrap 也不再提供可寫入口（原 `open_default_store`）。"""
    offenders: list[str] = []
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith((".venv/", "tests/", ".pytest_tmp/", ".pytest_cache/")) or "/__pycache__/" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "DecisionStore" not in text and "open_default_store" not in text:
            continue
        for node in ast.walk(ast.parse(text)):
            if (isinstance(node, ast.Attribute) and node.attr == "open"
                    and isinstance(node.value, ast.Name) and node.value.id == "DecisionStore"):
                offenders.append(f"{rel}:{node.lineno} DecisionStore.open")
            elif isinstance(node, ast.Name) and node.id == "open_default_store":
                offenders.append(f"{rel}:{node.lineno} open_default_store")
            elif isinstance(node, ast.alias) and node.name == "open_default_store":
                offenders.append(f"{rel} import open_default_store")
    assert offenders == [], offenders

    tree = ast.parse((ROOT / "decision_lab" / "bootstrap.py").read_text(encoding="utf-8"))
    public = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")}
    assert public == {"default_store_path", "open_readonly_store"}
