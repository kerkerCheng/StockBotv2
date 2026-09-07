"""Audit 的資料源存取層。

## 唯一的設計重點：**「讀不到」不得長得像「沒問題」**

每個 loader 要嘛回傳資料，要嘛丟 `SourceUnavailable`（帶**具體**原因）。
**沒有第三種**——不回空 list、不回 None、不吞例外。

L11-5：「我找不到」與「它不存在」是兩個不同的 claim，後者舉證責任高得多。
L13-2：最危險的是成功與失敗在同一個訊號上同形——空集合正是那種訊號。

實測依據：`audit invariants` 骨架期 12 個 check 全 SKIPPED，報表底部靠一行
「⚠ SKIPPED 不是 PASS」提醒人。那行字是對的，但它是**要人讀的段落**（L14）。
本層把它變成型別：讀不到就丟例外，呼叫端**沒有辦法**把它寫成 PASS。
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent.parent
LEADS_DIR = ROOT / "library" / "leads"


class SourceUnavailable(RuntimeError):
    """資料源讀不到。**呼叫端必須把它轉成 SKIPPED，不得轉成 PASS。**"""


# ---------------------------------------------------------------------------
# leads state（tracked JSON）
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Any:
    if not path.exists():
        raise SourceUnavailable(f"{path.relative_to(ROOT)} 不存在")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceUnavailable(f"{path.relative_to(ROOT)} 不是合法 JSON：{exc}") from exc


def leads() -> dict[str, dict]:
    """`lead_id → lead`。"""
    data = _load_json(LEADS_DIR / "pending_leads.json")
    got = data.get("leads")
    if not isinstance(got, dict):
        raise SourceUnavailable("pending_leads.json 的 `leads` 不是 dict——schema 變了")
    return got


def todo_items() -> list[dict]:
    data = _load_json(LEADS_DIR / "todo_pool.json")
    got = data.get("items")
    if not isinstance(got, list):
        raise SourceUnavailable("todo_pool.json 的 `items` 不是 list——schema 變了")
    return got


def event_watches() -> list[dict]:
    data = _load_json(LEADS_DIR / "event_watches.json")
    got = data.get("watches")
    if not isinstance(got, list):
        raise SourceUnavailable("event_watches.json 的 `watches` 不是 list——schema 變了")
    return got


def hypotheses() -> list[dict]:
    data = _load_json(LEADS_DIR / "hypotheses.json")
    got = data.get("hypotheses")
    if not isinstance(got, list):
        raise SourceUnavailable("hypotheses.json 的 `hypotheses` 不是 list——schema 變了")
    return got


# ---------------------------------------------------------------------------
# identity registry
# ---------------------------------------------------------------------------

def registry() -> Any:
    try:
        from identity.registry import get_registry
    except ImportError as exc:  # pragma: no cover
        raise SourceUnavailable(f"identity.registry 不可用：{exc}") from exc
    try:
        return get_registry()
    except Exception as exc:  # noqa: BLE001
        raise SourceUnavailable(f"registry 載入失敗：{exc}") from exc


# ---------------------------------------------------------------------------
# Engine A（Neo4j）
# ---------------------------------------------------------------------------

@contextmanager
def graph_session() -> Iterator[Any]:
    """Neo4j session。**沒開就丟例外**——不要退回「圖是空的」。

    ⚠ 這正是 F-05 的形狀：連不上被讀成「圖裡沒有這家公司」，
    於是 identity 檢查靜默通過。
    """
    try:
        from dotenv import load_dotenv
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise SourceUnavailable(f"neo4j driver 未安裝：{exc}") from exc

    load_dotenv(ROOT / ".env")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise SourceUnavailable("NEO4J_PASSWORD 未設定（.env 未載入？）")
    try:
        driver = GraphDatabase.driver(
            os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
        )
        driver.verify_connectivity()
    except Exception as exc:  # noqa: BLE001
        raise SourceUnavailable(f"Neo4j 連不上：{type(exc).__name__}: {exc}") from exc
    try:
        with driver.session() as session:
            yield session
    finally:
        driver.close()


def graph_rows(cypher: str, **params: Any) -> list[dict]:
    with graph_session() as session:
        return [dict(record) for record in session.run(cypher, **params)]


# ---------------------------------------------------------------------------
# Engine C（private SQLite）
# ---------------------------------------------------------------------------

def engine_c_conn() -> sqlite3.Connection:
    pointer = ROOT / "library" / "private" / "runtime_pointer.json"
    if not pointer.exists():
        raise SourceUnavailable("library/private/runtime_pointer.json 不存在——"
                                "private authority 未掛載")
    data = _load_json(pointer)
    rel = data.get("engine_c")
    if not rel:
        raise SourceUnavailable("runtime_pointer.json 沒有 `engine_c` 指標")
    db = ROOT / "library" / "private" / rel
    if not db.exists():
        raise SourceUnavailable(f"Engine C DB 不存在：{rel}")
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Engine D（Decision Store）
# ---------------------------------------------------------------------------

@contextmanager
def decision_store() -> Iterator[Any]:
    try:
        from decision_lab.bootstrap import open_default_store
    except ImportError as exc:  # pragma: no cover
        raise SourceUnavailable(f"decision_lab 不可用：{exc}") from exc
    try:
        store = open_default_store()
    except Exception as exc:  # noqa: BLE001
        raise SourceUnavailable(f"Decision Store 打不開：{exc}") from exc
    try:
        yield store
    finally:
        store.close()


def decision_rows(sql: str, *params: Any) -> list[dict]:
    """⚠ 唯讀。audit **永遠不寫** append-only authority（L10）。"""
    with decision_store() as store:
        return [dict(row) for row in store._conn.execute(sql, params)]  # noqa: SLF001


def coverage_gate_history() -> list[dict]:
    """每一份 coverage assessment 的三條 lane blockers，依時序排好。

    這是 `GateDiscrimination`（INV-5）唯一的資料源：**gate 實際上有沒有響過、響完
    有沒有被清掉**，只有這張表答得出來。schema 讀不到就丟例外（不回空 list）。
    """
    rows = decision_rows(
        "select assessment_id, cohort_id, created_at, blockers_json, "
        "       paper_blockers_json, live_blockers_json "
        "from coverage_assessments order by created_at, assessment_id")
    if not rows:
        raise SourceUnavailable("coverage_assessments 沒有任何列——gate 從未被評估過")
    out: list[dict] = []
    for row in rows:
        lanes: dict[str, frozenset[str]] = {}
        for lane, column in (("coverage", "blockers_json"), ("paper", "paper_blockers_json"),
                             ("live", "live_blockers_json")):
            raw = row.get(column)
            try:
                items = (json.loads(raw) or {}).get("items") if raw else []
            except json.JSONDecodeError as exc:
                raise SourceUnavailable(
                    f"assessment {row.get('assessment_id')} 的 {column} 不是合法 JSON：{exc}") from exc
            if items is None:
                items = []
            if not isinstance(items, list):
                raise SourceUnavailable(f"{column}.items 不是 list——schema 變了")
            lanes[lane] = frozenset(str(x) for x in items)
        out.append({"assessment_id": row.get("assessment_id"), "cohort_id": row.get("cohort_id"),
                    "created_at": row.get("created_at"), "lanes": lanes})
    return out


# ---------------------------------------------------------------------------
# 已產出的 AlphaSignal（private）
# ---------------------------------------------------------------------------

def alpha_signals() -> list[tuple[str, dict]]:
    """`library/private/alpha/*.alpha_signal.json` 與 `*_signal.json`。"""
    base = ROOT / "library" / "private" / "alpha"
    if not base.exists():
        raise SourceUnavailable("library/private/alpha/ 不存在——尚未產出任何 AlphaSignal")
    found: list[tuple[str, dict]] = []
    for path in sorted(base.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and (
            "scores" in payload or "structural_score" in payload
        ):
            found.append((path.name, payload))
    return found
