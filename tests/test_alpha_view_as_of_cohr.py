"""COHR 的歷史 as-of 卡（整合測試；需要本機 Neo4j、Engine C 與 Decision Store）。

守的是 INV-6 的端到端形式：`--as-of T` 的卡片裡**沒有任何一個 T 之後才存在的事實**——
不論它來自圖、Engine C、Decision Store 還是 thesis 檔。沒有 runtime 時 skip，
skip 會在報表上現形（不是靜默通過）。
"""
from __future__ import annotations

import os
import socket
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _runtime_available() -> bool:
    if not os.environ.get("NEO4J_PASSWORD"):
        try:
            from dotenv import load_dotenv

            load_dotenv(ROOT / ".env")
        except Exception:  # noqa: BLE001
            return False
    if not os.environ.get("NEO4J_PASSWORD"):
        return False
    try:
        with socket.create_connection(("127.0.0.1", 7687), timeout=1):
            pass
    except OSError:
        return False
    return (ROOT / "library" / "private" / "decision_lab" / "decision_lab.db").is_file()


pytestmark = pytest.mark.skipif(not _runtime_available(),
                                reason="需要本機 Neo4j＋Decision Store（整合測試）")


def _view(as_of: date):
    from briefing.alpha_view.sources import fetch_alpha_investment_view

    return fetch_alpha_investment_view("COHR", as_of=as_of, include_causal=False,
                                       today=date(2026, 9, 5))


def _walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield f"{path}.{k}".lstrip("."), k, v
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def test_cohr_as_of_2026_08_15_contains_no_fact_after_the_cutoff() -> None:
    """2026-08-15 那天：Engine D 有 decision（08-15 03:05）與 coverage（expiry 11-30），
    但**還沒有** 08-31 的那份；thesis 檢核點（12-01）與 lifecycle.json 沒有歷史 → not_applicable。"""
    as_of = date(2026, 8, 15)
    view = _view(as_of)
    assert view.identity.point_in_time_mode == "as_of" and view.identity.as_of == as_of
    lc = view.identity.lifecycle
    assert lc.decision_facts_as_of == "2026-08-15"
    assert lc.decision_effective_at is not None and lc.decision_effective_at[:10] <= "2026-08-15"
    # coverage／expiry 是 as_of 當時那份，不是今天最新那份
    assert view.catalysts.expiry.is_known and str(view.catalysts.expiry.value).startswith("2026-11-30")
    assert view.catalysts.expiry.as_of is not None and view.catalysts.expiry.as_of <= as_of
    assert view.catalysts.watch_state.as_of == as_of
    assert view.catalysts.checkpoints == ()
    assert view.falsification.thesis_status.status == "not_applicable"
    # 證據索引沒有任何晚於 as_of 的引用
    assert all(i.published_at is None or i.published_at <= as_of for i in view.evidence.index)
    # 整份 JSON 裡沒有任何 08-31 的 coverage 時間戳或 12-01 的檢核點日期
    payload = view.to_dict()
    leaked = [(p, v) for p, k, v in _walk(payload)
              if isinstance(v, str) and (v.startswith("2026-08-31") or v == "2026-12-01")]
    assert not leaked, f"歷史卡混進了 as_of 之後的事實：{leaked[:5]}"
    assert any("as-of 視角" in w for w in view.warnings)


def test_cohr_as_of_2026_06_30_has_no_engine_d_cohort_yet_and_no_engine_c_snapshot() -> None:
    """2026-06-30：COHR 的 cohort 07-22 才建立、Engine C 序列 07-08 才開始 → 兩者都是誠實的 missing，
    thesis 檔仍是 not_applicable，且沒有任何當前值滲入。"""
    as_of = date(2026, 6, 30)
    view = _view(as_of)
    assert view.identity.lifecycle.decision_effective_at is None
    assert "尚無" in (view.identity.lifecycle.reason or "")
    assert view.catalysts.narrative.status == "missing"
    assert view.fundamentals.meta.status == "missing"
    assert view.falsification.thesis_status.status == "not_applicable"
    assert view.catalysts.checkpoints == ()
    assert all(i.published_at is None or i.published_at <= as_of for i in view.evidence.index)
    assert view.structural_thesis.structural_score.is_known          # Engine A 投影仍算得出 Q1
