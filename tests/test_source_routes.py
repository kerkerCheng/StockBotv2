"""一手取得路徑登記表（`sourcing/routes.py` ＋ `config/source_routes.json`）。

守的是一句話：**「我沒試」不得被講成「拿不到」。**
2026-09-11 一個 session 內三次犯這個錯（深交所 API、pypdf、MOPS fetcher 都早就可用）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sourcing import routes


def test_applicability_uses_registry_not_a_guess_from_the_ticker() -> None:
    """交易所路徑由 ticker 後綴與 registry 決定，不從公司名或印象猜（INV-1）。"""
    reg = routes.load()
    got = {t: {r.key for r in reg.applicable(ticker=t, venue=routes.venue_for(t))}
           for t in ("002472.SZ", "3081.TWO", "000660.KS", "AVGO")}
    assert "szse" in got["002472.SZ"] and "mops" not in got["002472.SZ"]
    assert "mops" in got["3081.TWO"] and "szse" not in got["3081.TWO"]
    assert "dart" in got["000660.KS"]
    assert "sec_edgar" in got["AVGO"]


def test_sec_route_does_not_depend_on_execution_venue() -> None:
    """`execution_venue` 只有 43/100 家有值（它是「能不能下單」不是「在哪申報」）。

    AVGO 與 NVDA 的 venue 都是 None——拿它判 SEC 會把美國申報大戶漏掉，
    而漏一條路的代價正是本表要防的那件事。
    """
    assert routes.venue_for("AVGO") is None
    assert routes.venue_for("NVDA") is None
    reg = routes.load()
    for ticker in ("AVGO", "NVDA"):
        keys = {r.key for r in reg.applicable(ticker=ticker, venue=None)}
        assert "sec_edgar" in keys


def test_every_ticker_has_at_least_the_always_routes() -> None:
    """沒有任何標的可以「一條路都沒有」——那會讓檢查靜默通過。"""
    reg = routes.load()
    for ticker in ("SIVE.ST", "XFAB.PA", "6680.HK", "UNKNOWN"):
        keys = {r.key for r in reg.applicable(ticker=ticker, venue=None)}
        assert {"local_library", "issuer_site", "alternate_primary"} <= keys


def test_unverified_routes_are_listed_not_hidden() -> None:
    """未驗證的路徑要列出來讓缺口**具名**——『這條路還沒建』與『這檔拿不到』是兩回事。

    ⚠ 這條原本釘死 `{"dart", "edinet", "sse", "hkex"} <= unverified`，於是 2026-09-11
    把 dart 實測跑通、順手把 verified 改成 true 之後它就變紅——**而那是進展不是回歸**。
    釘現況的測試會自己腐壞（同 commit c067b51 的形狀）。改法：守的是 `render` 的行為
    「未驗證不得被靜默隱藏」，而那件事與『今天哪幾條未驗證』無關，所以用**資料驅動**：
    每一條 verified=False 的路徑都必須在 render 裡帶上未驗證標記。
    """
    reg = routes.load()
    for route in reg.routes:
        rendered = "\n".join(routes.render((route,)))
        if route.verified:
            assert "未驗證" not in rendered, f"{route.key} 已驗證卻被標成未驗證"
        else:
            assert "未驗證" in rendered, f"{route.key} 未驗證卻沒有標記——缺口被隱藏了"


def test_unverified_marker_is_not_vacuous() -> None:
    """上一條在「全部都已驗證」時會變成空轉，所以用合成 route 直接證明標記邏輯活著。"""
    unverified = routes.Route(
        key="fixture_unverified", label="合成路徑", rung=9, applies_to="always",
        tier_cap=3, verified=False, how="（合成）", why="（合成）",
    )
    rendered = "\n".join(routes.render((unverified,)))
    assert "fixture_unverified" in rendered
    assert "未驗證" in rendered


def test_receipt_names_the_routes_not_walked() -> None:
    """收據的價值在於**逐條寫出沒走的**，而不是宣稱走過了。"""
    receipt = routes.build_receipt("002472.SZ", ["local_library"])
    assert "已走=local_library" in receipt
    assert "szse" in receipt and "未走=" in receipt


def test_park_gate_only_fires_for_did_not_get_it_statuses() -> None:
    """終局型不受約束：拿到了、或判定不研究，都不是取得失敗。"""
    reg = routes.load()
    for status in ("lead_only_tier_4", "isolated_tier_3", "partial",
                   "awaiting_named_disclosure"):
        assert reg.requires_receipt(status)
    for status in ("original_obtained", "contradicts", "not_pursued",
                   "tier_1_2_honest_passthrough"):
        assert not reg.requires_receipt(status)


def test_park_auto_stamps_the_receipt_instead_of_crashing_unattended_routines() -> None:
    """park 缺收據時自動蓋章，**不 raise**。

    第一版寫成 raise，實測打紅 9 條測試，其中包含 `consume_fired` 這類無人值守
    routine 會走的路徑——讓 daily 在 park 時崩潰是用硬擋掩蓋設計問題；而且 raise
    只會逼呼叫端塞一個假收據過關，等於又回到自陳。

    自動蓋章的默認值是「已走=無」——**什麼都不做時，紀錄自己說出你什麼都沒做。**
    """
    from engine_b import leads as L

    store = L.empty_store()
    lead_id, _ = L.register(store, source="x:test", url="https://x.io/1",
                            title="$AAOI 某個轉述")
    L.triage(store, lead_id, go=True, tier=3, reason="t",
             classification={"content_type": "structural_fact",
                             "decision_impact": "ranking"})
    L.advance(store, lead_id, "researching")
    L.advance(store, lead_id, "parked", ref={
        "trace_status": "isolated_tier_3",
        "parked_reason": "只有三手轉述",
        "trace_requires_user": "false",
    })
    receipt = store["leads"][lead_id]["refs"].get("source_routes_receipt") or ""
    assert "已走=無" in receipt, receipt
    assert "sec_edgar" in receipt          # 沒走的路逐條具名
    assert "自動蓋章" in receipt


def test_registry_refuses_configurations_that_would_disable_the_gate(tmp_path) -> None:
    """空的 routes 或空的 park gate 都等於「永遠不必交代」——載入就該拒絕。"""
    base = json.loads(Path("config/source_routes.json").read_text(encoding="utf-8"))

    empty_routes = dict(base, routes=[])
    path = tmp_path / "a.json"
    path.write_text(json.dumps(empty_routes, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(routes.SourceRouteError, match="非空"):
        routes.load(path)

    no_gate = dict(base, park_requires_receipt_when_trace_status_in=[])
    path2 = tmp_path / "b.json"
    path2.write_text(json.dumps(no_gate, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(routes.SourceRouteError, match="不得為空"):
        routes.load(path2)


def test_park_gate_vocabulary_is_validated_against_the_trace_status_registry(tmp_path) -> None:
    """gate 列的 trace_status 必須是登記過的——打錯字會讓 gate 靜默失效（L16-3）。"""
    base = json.loads(Path("config/source_routes.json").read_text(encoding="utf-8"))
    bad = dict(base, park_requires_receipt_when_trace_status_in=["isolated_tier_three"])
    path = tmp_path / "c.json"
    path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Exception):
        routes.load(path)
