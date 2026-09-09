"""Phase 2 Step 4 — **Full-chain Adversarial Acceptance**（2026-09-07）。

問的不是「這條鏈算得出數字嗎」，而是：**故意把它弄壞的時候，它會 fail closed，
還是會產出一個看起來合理但語意錯誤的結果？**

```
Evidence → Research → Fundamental → Valuation → Horizon → Implied Return → Analyst View
```

## 三條寫法紀律

1. **不建第二份 dependency graph。** 每個 scenario 都用既有的 provenance
   （`assumption_ids`／`evidence_refs`／`alpha.refresh` 的 policy 表）去斷言，
   不在測試裡重新宣告誰依賴誰——那會變成一份會與程式漂移的影子圖。
2. **斷言寫成「該動的動了 **且** 不該動的沒動」。** 只斷言前者的話，一個把所有東西
   都標成 `review_required` 的實作會全綠——那正是 Step 0 抓到的 over-invalidation。
3. **Entry 是 optional，不是 completion gate**（Step 3 的立場）：任何 readiness 斷言
   都不得因為沒有 hurdle 而變成 blocked。

整合測試：需要本機 Neo4j＋Engine C＋Decision Store。沒有 runtime 就 skip，
**skip 會在報表上現形**（不是靜默通過）。
"""
from __future__ import annotations

import ast
import json
import os
import socket
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 7)
TICKER = "COHR"


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
    return ((ROOT / "library" / "private" / "decision_lab" / "decision_lab.db").is_file()
            and (ROOT / "library" / "private" / "alpha" / "assumptions" / f"{TICKER}.jsonl").is_file())


pytestmark = pytest.mark.skipif(
    not _runtime_available(),
    reason="需要本機 Neo4j＋Engine C＋Decision Store＋COHR 假設 ledger（full-chain 整合測試）")


# ---------------------------------------------------------------------------
# 取 view：同一組參數只建一次（每次建構要打 Neo4j，約 3.5 秒）
# ---------------------------------------------------------------------------

_CACHE: dict[tuple, Any] = {}


def view(**kwargs: Any):
    """預設 `as_of=TODAY`（PIT 投影），不是 `today=TODAY` 配當前資料。

    2026-09-09 實測：原本只釘 `today`，價格與 ledger 卻取**當前**——COHR 的 D&C 假設 09-08 re-append
    後，`today=09-07` 的選取把新紀錄（created 09-08）與被 supersede 的舊紀錄都排除，整條鏈缺席，
    17 條紅了兩天。「釘的是一個 authority 都沒有合法更新時的樣子」本來就該用 as-of 表達：
    as_of=09-07 的投影還原出完全相同的基準數字（223.6034／−0.2067／−0.2464），期望值一個都不用改。
    要看當前視角的 case 自己傳 `as_of=None`。
    """
    from briefing.alpha_view.sources import fetch_alpha_investment_view

    kwargs.setdefault("as_of", TODAY)
    key = tuple(sorted((k, str(v)) for k, v in kwargs.items()))
    if key not in _CACHE:
        _CACHE[key] = fetch_alpha_investment_view(
            TICKER, include_causal=False, today=TODAY, **kwargs)
    return _CACHE[key]


def analyst(**kwargs: Any):
    from briefing.analyst_view import build_analyst_view

    return build_analyst_view(view(**kwargs))


def states(v: Any) -> dict[str, str]:
    return {f"{i.artifact_type}:{i.artifact_id}": i.state for i in v.refresh_status.items}


def moved(base: dict[str, str], other: dict[str, str]) -> dict[str, tuple[str, str]]:
    """兩份 state 表的差集。消失的成果也算「動了」——它不得靜靜不見。"""
    return {k: (base.get(k, "—"), other.get(k, "—"))
            for k in set(base) | set(other) if base.get(k) != other.get(k)}


def _iter_values(node: Any, path: str = ""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield f"{path}.{k}", k, v
            yield from _iter_values(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _iter_values(v, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# 0. Baseline：authority 沒有合法更新時，這些數字不准漂
# ---------------------------------------------------------------------------

def test_baseline_numbers_are_pinned_and_each_traces_to_an_authority() -> None:
    """⚠ 這條紅了**不准直接改期望值**——先 trace provenance，說得出是哪一筆 authority 變了。

    釘的是「一個 authority 都沒有合法更新」時的樣子。每一格同時斷言它的**來源**，
    因為一個對的數字配一個錯的來源，下一次就會用錯的來源去解釋它。
    """
    v = view()
    va, ir = v.valuation, v.implied_return

    assert va.fair_value.value == pytest.approx(223.6034, abs=5e-4)
    assert va.fair_value.authority == "alpha://valuation/model"
    assert ir.current_price.value == pytest.approx(281.86, abs=1e-6)
    assert str(ir.value_date.value) == "2027-06-30"
    assert str(ir.horizon.value) == "2027-06-30"
    assert ir.price_return.value == pytest.approx(-0.2067, abs=5e-4)
    assert ir.annualized_price_return.value == pytest.approx(-0.2464, abs=5e-4)
    assert ir.price_return.authority == "alpha://implied_return/model"

    internal = {d.key: d for d in v.internal_fundamentals.items}
    assert internal["internal_eps"].value == pytest.approx(8.9441, abs=5e-4)
    assert internal["internal_eps"].authority == "alpha://fundamental/bridge"

    eps_gap = next(d for d in v.expectation_gap.numeric_comparisons if d.key.endswith("_eps"))
    assert eps_gap.value["consensus"] == pytest.approx(9.4163, abs=5e-4)
    assert eps_gap.value["relative_gap"] == pytest.approx(-0.0501, abs=5e-4)


def test_core_readiness_is_ready_and_entry_is_optional_not_a_blocker() -> None:
    a = analyst()
    assert a.readiness.state == "ready"
    assert a.readiness.blockers == ()
    assert a.entry.status == "missing"
    assert a.readiness.optional_unavailable == ("entry：missing",)


# ---------------------------------------------------------------------------
# 1. Refresh 依賴矩陣：**只影響該影響的**
#
# 每一列是 changed_input → 必須被影響的 ／ 必須沒被影響的。
# 「必須沒被影響」那一欄才是這張表的價值：少了它，一個把所有東西都標
# review_required 的實作會全綠（Step 0 實測到的 over-invalidation）。
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Row:
    scenario: str
    changed_input: str
    affected: tuple[str, ...]
    unaffected: tuple[str, ...]


MATRIX: tuple[Row, ...] = (
    Row("price_only", "Engine C 現價（bar_date 前進）",
        affected=("fair_value_gap:fair_value_gap", "implied_return:implied_return",
                  "market_implied:market_implied_eps_growth"),
        unaffected=("fair_value:fair_value", "axis:expectation_gap", "axis:value_capture",
                    "thesis:session_judgment", "valuation_assumption:va_07dcbc388c814a91",
                    "horizon_assumption:ha_586fe0ff9658a2d4")),
    Row("consensus_revision", "同期 FY2027 EPS 共識上修",
        affected=("expectation_comparison:eps", "axis:expectation_gap", "thesis:session_judgment"),
        unaffected=("axis:value_capture", "axis:structural", "modeled_metric:eps",
                    "fundamental_model:fundamental_model")),
    Row("graph_edge", "結構邊 substitutability／sole_source 改變",
        affected=("axis:structural",),
        unaffected=("horizon_assumption:ha_586fe0ff9658a2d4",)),
    Row("new_guidance", "新一季指引（營收／毛利率／稅率）",
        affected=("axis:value_capture", "axis:expectation_gap",
                  "fundamental_model:fundamental_model"),
        unaffected=("axis:structural", "horizon_assumption:ha_586fe0ff9658a2d4")),
    Row("new_actual", "新一季實際值",
        affected=("modeled_metric:revenue", "fair_value:fair_value", "implied_return:implied_return"),
        unaffected=("axis:structural", "axis:expectation_gap")),
    Row("disproof", "disproof 訊號觸發",
        affected=("fair_value:fair_value", "implied_return:implied_return"),
        unaffected=("axis:structural",)),
)


@pytest.mark.parametrize("row", MATRIX, ids=lambda r: r.scenario)
def test_each_change_touches_only_what_it_should(row: Row) -> None:
    base = states(view())
    after = states(view(scenario=row.scenario))
    changed = moved(base, after)

    for key in row.affected:
        assert key in changed, (
            f"{row.scenario}（{row.changed_input}）沒有影響到 {key}——"
            f"依賴斷了，或 policy 表漏了一格。實際變動：{sorted(changed)}")
    for key in row.unaffected:
        assert key not in changed, (
            f"{row.scenario}（{row.changed_input}）不該影響 {key}，"
            f"卻把它從 {changed[key][0]} 改成 {changed[key][1]}——"
            "over-invalidation 會讓「需要重看」失去意義")


def test_price_alone_never_stales_a_research_judgment() -> None:
    """v1 的 materiality 立場，寫成一條會紅的斷言。

    沒有任何經量測的門檻能說「漲 6.6% 就該重看 Q4」。假裝有一個統計上站得住的門檻
    比誠實說「價格不觸發複查」更危險（L14：未量測的機制不得享有默認信任）。
    """
    changed = moved(states(view()), states(view(scenario="price_only")))
    judgmental = [k for k in changed
                  if k.startswith(("axis:", "thesis:", "operating_assumption:",
                                   "valuation_assumption:", "horizon_assumption:"))]
    assert judgmental == [], f"價格變動動到了判斷型成果：{judgmental}"


@pytest.mark.xfail(
    strict=True,
    reason="ROADMAP 開放 backlog「full-chain rollover 兩條紅」：rollover 情境下假設因 unresolved consensus／observation refs "
           "被判 invalidated 而非 superseded（2026-09-09 實測；09-07 驗收報告時為綠）。strict：修好會變紅提醒拿掉本標記。",
)
def test_a_fiscal_rollover_does_not_let_old_period_numbers_pose_as_current() -> None:
    """會計期間推進：舊年度的假設全部 `superseded`，而**新年度沒有假設**。

    這是最容易產出「看起來合理但語意錯誤」的一格——把 FY2027 的假設沿用到 FY2028，
    數字照樣算得出來，而且長得很正常。正確行為是整條鏈 fail closed。
    """
    # rollover 情境把 today 推到目標期末之後，與 PIT 釘點互斥——這兩條走當前視角（as_of=None）
    v = view(scenario="fiscal_rollover", as_of=None)
    a = analyst(scenario="fiscal_rollover", as_of=None)
    s = states(v)

    assert all(state == "superseded"
               for key, state in s.items() if key.startswith("operating_assumption:"))
    assert s["valuation_assumption:va_07dcbc388c814a91"] == "superseded"
    assert s["horizon_assumption:ha_586fe0ff9658a2d4"] == "superseded"
    assert s["fundamental_model:fundamental_model"] == "review_required"

    # 目標期間已經前進，而所有下游都缺席——不得留下一個 FY2027 的數字冒充 FY2028
    assert str(v.internal_fundamentals.period_end) == "2028-06-30"
    assert v.valuation.fair_value.value is None
    assert v.implied_return.price_return.value is None
    assert a.readiness.state == "blocked"
    assert any("headline" in b for b in a.readiness.blockers)


def test_a_superseded_record_never_comes_back_as_current() -> None:
    """ledger 裡有被 supersede 的紀錄。它只能是歷史，不得參與任何當前計算。"""
    v = view()
    s = states(v)
    superseded = [k.split(":", 1)[1] for k, state in s.items() if state == "superseded"]
    assert superseded, "ledger 裡應有被 supersede 的紀錄——沒有的話這條是空跑"

    effective = {str((d.dependencies or {}).get("assumption_id"))
                 for d in v.valuation.assumptions}
    for record_id in superseded:
        assert record_id not in effective, f"{record_id} 已被 supersede 卻仍在生效清單裡"
    # 被篩掉的那一筆必須**被計數並說明理由**，不是靜默消失（INV-3）
    assert v.valuation.selection.filtered_count >= 1
    assert "superseded" in v.valuation.selection.reasons


# ---------------------------------------------------------------------------
# 2. Point-in-time：T 時刻不存在的東西不得出現在 T 的畫面上
# ---------------------------------------------------------------------------

def test_an_as_of_before_the_ledgers_existed_leaks_no_judgment_and_no_number() -> None:
    """as-of 2026-08-01：FY2026 財報（08-12）與三本 ledger（09-05 起）都還不存在。

    正確行為不是「用今天的假設回算 8 月的 fair value」，是**整段缺席並說出為什麼**。
    """
    as_of = date(2026, 8, 1)
    v = view(as_of=as_of)
    a = analyst(as_of=as_of)

    assert a.point_in_time_mode == "as_of" and a.as_of == as_of
    assert v.valuation.fair_value.value is None
    assert v.implied_return.price_return.value is None
    assert v.implied_return.horizon.value is None
    for datum in (v.valuation.fair_value, v.implied_return.price_return):
        assert datum.reason, "缺席必須帶原因——沉默的缺席與「值是 0」同形"


def test_no_evidence_in_an_as_of_view_was_published_after_the_cutoff() -> None:
    as_of = date(2026, 8, 15)
    v = view(as_of=as_of)
    late = [item.ref for item in v.evidence.index
            if item.published_at and item.published_at > as_of]
    assert late == [], f"as-of {as_of} 的證據索引漏出未來：{late[:3]}"


def test_the_return_starts_from_the_price_bar_date_not_from_the_etl_date() -> None:
    """`bar_date`（行情交易日）≠ `snapshot_date`（ETL 執行日）。混用會讓報酬差幾天。"""
    v = view()
    window = v.implied_return.horizon_window.value
    assert str(window["horizon_start"]) == "2026-09-04"
    assert str(window["horizon_start"]) != TODAY.isoformat()
    assert window["holding_period_days"] == (date(2027, 6, 30) - date(2026, 9, 4)).days


# ---------------------------------------------------------------------------
# 3. 上游缺失：任何一段缺料都不得靠舊的 derived value 繼續輸出乾淨的隱含報酬
# ---------------------------------------------------------------------------

class _Shim:
    """包住真 provider，只改一個方法。其餘全部照原樣轉發。"""

    def __init__(self, inner: Any, **overrides: Any) -> None:
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_overrides", overrides)

    def __getattr__(self, name: str) -> Any:
        overrides = object.__getattribute__(self, "_overrides")
        if name in overrides:
            return overrides[name]
        return getattr(object.__getattribute__(self, "_inner"), name)


def _fresh_view(**kwargs: Any):
    """不走快取（每個 adversarial case 的 provider／目錄都不同）。"""
    from alpha.providers.fundamentals import EngineCFundamentalsProvider
    from alpha.providers.graph_neo4j import open_default_provider
    from briefing.alpha_view.sources import fetch_alpha_investment_view

    kwargs.setdefault("graph_provider", open_default_provider())
    kwargs.setdefault("fundamentals_provider", EngineCFundamentalsProvider())
    kwargs.setdefault("as_of", TODAY)          # 同 view()：釘 PIT 視角，不釘「今天的當前資料」
    return fetch_alpha_investment_view(TICKER, include_causal=False, today=TODAY, **kwargs)


def _real_fundamentals():
    from alpha.providers.fundamentals import EngineCFundamentalsProvider

    return EngineCFundamentalsProvider()


def test_missing_base_actuals_blocks_the_whole_chain_and_says_why() -> None:
    shim = _Shim(_real_fundamentals(),
                 fiscal_year_results=lambda *a, **k: (None, "測試：基期觀測不存在"))
    v = _fresh_view(fundamentals_provider=shim)

    assert v.valuation.fair_value.value is None
    assert v.implied_return.price_return.value is None
    assert (v.internal_fundamentals.meta.reason or "") or (v.valuation.fair_value.reason or "")
    # 共識仍然看得到——上游缺的是我們自己的預測，不是市場的
    assert any(d.is_known for d in v.consensus.fiscal_items)


def test_missing_consensus_fails_closed_all_the_way_down_and_names_the_reason() -> None:
    """同期共識整段消失 → 數值 gap 消失，**而且整條內部預測也跟著缺席**。

    ⚠ 第二句是實測結果，不是原本的預期：D&C 成長假設把共識 ref 標成 `calibration`
    （「知道市場隱含 +65% 所以選 +60%」，刻意不當 supporting），但只要**任何一條宣告的
    ref 解析不到**，`select_assumptions` 就拒收整筆——於是內部營收→EPS→fair value 全部
    缺席。方向是 fail closed（正確的那一邊），但顆粒度值得記一筆：
    「supporting 解析不到」與「calibration 解析不到」目前是同一個判準。
    收緊或放寬都要先量（L14／L15），本次只**釘住現況並說出它**，不動它。
    """
    shim = _Shim(_real_fundamentals(), fiscal_consensus=lambda *a, **k: ((), "測試：無同期共識"))
    v = _fresh_view(fundamentals_provider=shim)

    internal = {d.key: d for d in v.internal_fundamentals.items}
    assert not v.expectation_gap.internal_vs_consensus.is_known
    assert all(not d.is_known for d in v.expectation_gap.numeric_comparisons)
    assert internal["internal_eps"].value is None
    assert v.valuation.fair_value.value is None
    assert v.implied_return.price_return.value is None
    # 缺席必須帶原因，而且是**逐項計數過的**原因（INV-3：不得靜默丟棄）
    assert "沒有成長假設" in (v.internal_fundamentals.meta.reason or "")
    assert v.valuation.fair_value.reason and "不是 0" in v.valuation.fair_value.reason


def test_a_quote_unit_mismatch_refuses_the_gap_instead_of_dividing_two_units() -> None:
    """報價單位 ≠ 結算幣別。硬算會差 100 倍，而那個數字看起來完全正常。"""
    real = _real_fundamentals()
    real_market = real.market

    def market(ticker, *, as_of=None):
        snapshot, freshness = real_market(ticker, as_of=as_of)
        return replace(snapshot, currency="GBp"), freshness

    v = _fresh_view(fundamentals_provider=_Shim(real, market=market))
    assert isinstance(v.implied_return.current_price.value, (int, float))
    assert v.valuation.fair_value_gap.value is None, "單位不相容仍算出 gap＝差 100 倍的數字"
    assert v.implied_return.price_return.value is None


@pytest.mark.parametrize("dir_attr,module,layer", [
    ("ASSUMPTION_DIR", "alpha.providers.assumptions", "fundamental"),
    ("VALUATION_DIR", "alpha.providers.valuation_assumptions", "valuation"),
    ("HORIZON_DIR", "alpha.providers.horizon_assumptions", "horizon"),
])
def test_a_missing_private_ledger_fails_closed_at_its_own_layer(
        monkeypatch, tmp_path, dir_attr, module, layer) -> None:
    """private authority 檔不見了 → 該層缺席，**下游一律跟著缺席**。

    ⚠ 這一組守的是 durability 的下半段：備份還沒跑、檔案沒了、或還原到舊版本時，
    系統不得靠上一次算好的 derived value 繼續輸出一個乾淨的隱含報酬。
    """
    import importlib

    monkeypatch.setattr(importlib.import_module(module), dir_attr, tmp_path)
    v = _fresh_view()

    if layer == "fundamental":
        internal = {d.key: d for d in v.internal_fundamentals.items}
        assert internal["internal_eps"].value is None
    if layer in ("fundamental", "valuation"):
        assert v.valuation.fair_value.value is None
    else:
        assert v.valuation.fair_value.value == pytest.approx(223.6034, abs=5e-4)
        assert v.implied_return.horizon.value is None
    assert v.implied_return.price_return.value is None, f"{layer} 缺席仍算得出隱含報酬"
    assert v.implied_return.price_return.reason, "缺席必須帶原因"


def test_a_malformed_ledger_line_is_counted_not_silently_dropped(monkeypatch, tmp_path) -> None:
    """半寫入／截斷的一行必須被**計數**。靜默丟棄會讓 fair value 用少一條假設算出來。"""
    import importlib

    from alpha.providers import valuation_assumptions as ledger

    real = ROOT / "library" / "private" / "alpha" / "valuation" / f"{TICKER}.jsonl"
    lines = [line for line in real.read_text(encoding="utf-8").splitlines() if line.strip()]
    broken = tmp_path / f"{TICKER}.jsonl"
    truncated = '{"assumption_id": "va_trunc", "ticke'
    broken.write_text("\n".join([*lines, truncated]) + "\n", encoding="utf-8")

    records, errors = ledger.read_valuation_assumption_records(TICKER, directory=tmp_path)
    assert len(records) == len(lines)
    assert len(errors) == 1
    assert "va_trunc" not in " ".join(r.assumption_id for r in records)

    monkeypatch.setattr(importlib.import_module("alpha.providers.valuation_assumptions"),
                        "VALUATION_DIR", tmp_path)
    v = _fresh_view()
    assert v.valuation.fair_value.value == pytest.approx(223.6034, abs=5e-4), \
        "好的行仍要算得出來——壞一行不得讓整層消失"
    assert v.valuation.selection.input_count > v.valuation.selection.accepted_count


def test_a_missing_or_corrupt_judgment_file_never_falls_back_to_an_older_one(tmp_path) -> None:
    """判斷檔不見了／壞了 → 研究段缺席並說原因，**不得回退成一份看起來 current 的舊判斷**。"""
    missing = _fresh_view(judgment_path=tmp_path / "nope.json")
    assert missing.variant_view.meta.status in ("missing", "insufficient_evidence")
    assert missing.variant_view.meta.reason

    corrupt = tmp_path / "broken.json"
    corrupt.write_text('{"axes": {"value_capture": ', encoding="utf-8")
    v = _fresh_view(judgment_path=corrupt)
    reasons = " ".join(str(x) for x in (v.variant_view.meta.reason,
                                        v.falsification.meta.reason, *v.warnings))
    assert any(token in reasons for token in ("判斷檔", "無法讀取", "契約")), reasons

    # 但**確定性那一段不受影響**——判斷壞了不代表財報數字壞了
    assert v.valuation.fair_value.value == pytest.approx(223.6034, abs=5e-4)


def test_a_stale_judgment_is_shown_as_mismatched_not_as_current() -> None:
    """舊判斷可以呈現（它有歷史價值），但**必須標成與目前 context 不一致**。"""
    from briefing.analyst_view import render_analyst_view_markdown

    a = analyst()
    text = render_analyst_view_markdown(a)
    matches = a.refresh.judged_context_matches
    assert matches is not None, "「有沒有對上」不得是未知——那會讓舊判斷看起來像 current"
    assert ("判斷與目前 context：一致" in text) is bool(matches)
    if not matches:
        assert "不一致" in text


# ---------------------------------------------------------------------------
# 4. 語意陷阱：算得出來，但不得被說成別的東西
# ---------------------------------------------------------------------------

def test_the_ordinal_q4_is_never_derived_from_the_numeric_gap() -> None:
    """Q4（ordinal，session）與 numeric gap（−5.0%，確定性）是**兩個 authority**。

    不得：用 −5% 自動映射 Q4 分數／用 Q4 取代 numeric comparison／因為方向相符就併成一格。
    """
    v = view()
    q4 = v.expectation_gap.session_judgment
    gap = next(d for d in v.expectation_gap.numeric_comparisons if d.key.endswith("_eps"))

    assert q4.basis == "session_judgment"
    assert gap.basis == "deterministic" and gap.authority == "alpha://fundamental/compare"
    assert q4.authority != gap.authority
    assert q4.value["effective"] == pytest.approx(0.25, abs=1e-9)
    assert gap.value["relative_gap"] == pytest.approx(-0.0501, abs=5e-4)
    # 兩者並存、各自標示；section reason 必須明說數值 gap 不取代 Q4
    assert "不取代" in (v.expectation_gap.meta.reason or "")
    assert q4.value["effective"] != pytest.approx(abs(gap.value["relative_gap"]), abs=1e-6)


def test_the_implied_return_is_attributed_to_the_multiple_not_to_an_earnings_view() -> None:
    """−20.7% 主要來自 target PE 25x，不是「我們預期 earnings 比市場差 20.7%」。

    consumer／epistemics 必須自己講得出這個歸因；講不出來，讀者只會照字面讀成盈餘觀點。
    """
    v = view()
    share = str((v.valuation.epistemics.value or {}).get("multiple_share_of_gap") or "")
    assert "target_pe" in share and "implied_multiple_at_price" in share

    gap = v.valuation.fair_value_gap.value
    from_multiple = 25.0 / gap["implied_multiple_at_price"] - 1.0
    assert from_multiple == pytest.approx(gap["relative_gap"], abs=5e-4), \
        "給定內部 EPS，整個 gap 就是倍數之差——這條紅了代表歸因說法與算術對不上"

    eps_gap = next(d for d in v.expectation_gap.numeric_comparisons if d.key.endswith("_eps"))
    assert abs(eps_gap.value["relative_gap"]) < abs(gap["relative_gap"]) / 3, \
        "盈餘觀點只解釋得了一小部分，不得被說成整個 gap"


def test_the_view_never_calls_the_implied_return_an_expected_earnings_shortfall() -> None:
    from briefing.analyst_view import render_analyst_view_markdown

    text = render_analyst_view_markdown(analyst()).replace("\\", "")
    for phrase in ("預期 earnings 比市場差", "預期盈餘比市場低"):
        assert phrase not in text, f"畫面上出現了會被讀成盈餘觀點的措辭：{phrase}"
    assert "不是 probability-weighted expected return" in text
    assert "不是 total return" in text


def test_the_thesis_claim_and_the_modeled_expression_are_both_visible() -> None:
    """variant view 說「未被定價的是 margin／FCF 轉換」，而內部模型：

    * 營益率與（條件式）共識隱含只差約 0.27pp；
    * FCF 是 `not_modeled`。

    系統必須**同時**呈現這個張力：既不自動改 thesis，也不得把文字 thesis 冒充成
    modeled expectation gap。
    """
    v = view()
    assert v.variant_view.meta.basis == "session_judgment"
    internal = {d.key: d for d in v.internal_fundamentals.items}
    assert internal["internal_fcf"].status == "not_modeled"
    assert internal["internal_fcf"].value is None

    margin_cmp = [d for d in v.expectation_gap.numeric_comparisons if "margin" in d.key]
    assert margin_cmp and all(not d.is_known for d in margin_cmp), \
        "營益率沒有共識可比——必須是明說的缺料，不得被 thesis 的文字補上"


def test_the_horizon_is_aligned_with_the_declared_value_date() -> None:
    """`aligned` 是一個**被宣告的判斷**，不是預設值。不對齊時算術可展示，但不得 clean。"""
    v = view()
    window = v.implied_return.horizon_window.value
    assert window["alignment"] == "aligned"
    assert str(window["horizon_end"]) == str(v.implied_return.value_date.value)
    assert v.implied_return.value_date.basis == "session_judgment"


def test_review_required_and_stale_are_never_rendered_as_clean() -> None:
    from briefing.analyst_view import render_analyst_view_markdown

    a = analyst(scenario="consensus_revision")
    text = render_analyst_view_markdown(a)
    assert a.refresh.overall == "review_required"
    assert a.readiness.state in ("ready_with_flags", "blocked")
    assert a.readiness.flags, "有段落被標記需要重看，readiness 卻沒有任何 flag"
    assert "review_required" in text


@pytest.mark.xfail(
    strict=True,
    reason="ROADMAP 開放 backlog「full-chain rollover 兩條紅」：rollover 情境下假設因 unresolved consensus／observation refs "
           "被判 invalidated 而非 superseded（2026-09-09 實測；09-07 驗收報告時為綠）。strict：修好會變紅提醒拿掉本標記。",
)
def test_a_scoped_no_attention_claim_states_its_scope_and_what_lies_outside() -> None:
    """「需要重看的研究成果：無」是一句斷言，它的**範圍**必須跟著印。

    2026-09-07 實測（`--scenario fiscal_rollover`）：畫面上方 `overall=review_required`，
    頭條卻寫「無」——兩句互相否定（L12：一個表示兩種語意）。
    """
    from briefing.analyst_view import render_analyst_view_markdown

    a = analyst(scenario="fiscal_rollover", as_of=None)      # rollover 與 PIT 釘點互斥，走當前視角
    text = render_analyst_view_markdown(a)
    assert a.headline.attention == () and a.headline.attention_total, \
        "這個情境應該是「頭條乾淨、別處不乾淨」——否則本條是空跑"
    assert "範圍：" in text
    assert "本節之外另有" in text


def test_a_forward_year_rollover_is_never_reported_as_an_analyst_revision() -> None:
    """yfinance 的 forward 是**相對標籤**，不是會計年度身分。

    2026-08-13 COHR 的導出 forward EPS 一天跳 +62.3%（FY2027 → FY2028）。
    30 個觀測的窗口跨過了它，於是 `estimate_revision_30d` 報 +68.3%——
    那不是分析師上修。現有 contract 分不出來時一律 `not_comparable`，**不猜**。
    """
    v = view()
    revision = next(d for d in v.consensus.items if d.key == "estimate_revision_30d")
    assert revision.value is None and not revision.is_known

    datum = next(d for d in v.price_implied_expectations.items
                 if d.key == "estimate_revision_vs_price")
    assert datum.status == "not_applicable" and datum.value is None
    assert "rollover" in (datum.reason or "")

    proxy = next(d for d in v.price_implied_expectations.items
                 if d.key == "market_implied_eps_growth")
    assert "forward 會計年度=" in (proxy.method or ""), \
        "proxy 必須說出它的 forward 指哪一個會計年度——否則換尺時讀者看不見"


# ---------------------------------------------------------------------------
# 5. 黑箱：從 `python -m briefing analyst-view COHR` 這一端驗
# ---------------------------------------------------------------------------

_CLI: dict[str, Any] = {}


def _cli_json() -> dict:
    if not _CLI:
        out = ROOT / ".pytest_tmp" / "full_chain_analyst_view.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "briefing", "analyst-view", TICKER,
                        "--format", "json", "-o", str(out)],
                       cwd=ROOT, check=True, capture_output=True, timeout=300)
        _CLI["payload"] = json.loads(out.read_text(encoding="utf-8"))
    return _CLI["payload"]


def test_black_box_cli_agrees_with_the_canonical_read_model_on_every_core_number() -> None:
    payload = _cli_json()
    # 子行程那一端沒有 --today，用的是真實今天；比對側必須用同一個時鐘——否則日曆一過 TODAY，
    # refresh（有到期日的判斷）就在兩側分歧（2026-09-08 實測：CLI review_required vs 凍結側 current）。
    from datetime import date as _date

    from briefing.alpha_view.sources import fetch_alpha_investment_view

    v = fetch_alpha_investment_view(TICKER, include_causal=False, today=_date.today())
    panels = [payload[name] for name in ("headline", "fundamental", "why", "research", "entry")]
    lines = {line["key"]: line["datum"] for panel in panels for line in panel["lines"]}

    assert lines["price_return"]["value"] == pytest.approx(v.implied_return.price_return.value)
    assert lines["annualized_price_return"]["value"] == pytest.approx(
        v.implied_return.annualized_price_return.value)
    assert lines["fair_value"]["value"] == pytest.approx(v.valuation.fair_value.value)
    assert lines["current_price"]["value"] == pytest.approx(v.implied_return.current_price.value)
    assert payload["refresh"]["overall"] == v.refresh_status.overall
    assert payload["source_schema_version"] == v.schema_version


def test_black_box_output_shows_no_zero_where_something_is_merely_absent() -> None:
    """Missing != Zero，從序列化那一端驗——JSON 裡帶值卻標 valueless status 是重罪。"""
    payload = _cli_json()
    valueless = {"missing", "insufficient_evidence", "not_modeled", "not_applicable"}
    bad = [path for path, _key, node in _iter_values(payload)
           if isinstance(node, dict) and node.get("status") in valueless
           and node.get("value") is not None]
    assert bad == [], f"缺席的格子帶了值：{bad[:3]}"


def test_black_box_output_carries_no_position_sizing_or_buy_sell_field() -> None:
    """比對**欄位名**不是全文。

    全文比對會誤報——畫面上刻意寫著「不是 portfolio permission」這種否定句，
    而一個會誤報的防呆本身就是 L16 明文禁止的東西。
    """
    from alpha.contracts import FORBIDDEN_POSITION_TOKENS

    banned = set(FORBIDDEN_POSITION_TOKENS) | {"target_weight", "supported_range", "nav_pct"}
    offenders = [key for _path, key, _node in _iter_values(_cli_json())
                 if set(str(key).lower().split("_")) & banned]
    assert not offenders, f"黑箱輸出出現部位／資本欄位：{sorted(set(offenders))}"


def test_the_consumer_makes_no_io_and_no_llm_call_of_its_own() -> None:
    """Consumer 只組裝、排序、貼標籤。寫入與 LLM 由 import 掃描守著。"""
    pkg = ROOT / "briefing" / "analyst_view"
    for path in sorted(pkg.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(("." * node.level) + (node.module or ""))
        for banned in ("sqlite3", "neo4j", "anthropic", "openai", "requests", "httpx",
                       "decision_lab.store", "engine_c.db"):
            assert banned not in imported, (path.name, banned)
