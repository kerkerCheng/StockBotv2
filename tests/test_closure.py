"""每檔閉環（alpha/closure.py；2026-09-09 研究閉環 P3）：終局判定、下一檔排序、摘要。

守的是「做完必須是機器查得出來的」與「下一檔選誰不是自由心證」。
"""
from __future__ import annotations

from alpha import closure
from alpha.closure import BacklogRow


def _row(ticker, readiness="blocked", open_panels=("headline",), settled=(), **kw):
    return BacklogRow(ticker=ticker, readiness=readiness, open_panels=tuple(open_panels),
                      settled_panels=tuple(settled), **kw)


def test_terminal_is_ready_or_all_settled_nothing_else() -> None:
    assert _row("A", readiness="ready", open_panels=()).terminal == "ready"
    assert _row("B", readiness="ready_with_flags", open_panels=()).terminal == "ready"
    assert _row("C", readiness="blocked", open_panels=(), settled=("headline", "why")).terminal == "settled"
    assert _row("D", readiness="blocked", open_panels=("why",), settled=("headline",)).terminal is None
    assert _row("E", readiness="blocked", open_panels=(), settled=()).terminal is None   # 沒有 blocker 卻 blocked：不算終局，現形


def test_row_from_artifact_copies_blocker_details_without_parsing_prose() -> None:
    payload = {"generated_at": "2026-09-09T00:00:00+00:00", "readiness": {"state": "blocked", "blocker_details": [
        {"panel": "headline", "absence_kind": "upstream_unavailable", "settled": False, "reason": "x"},
        {"panel": "why", "absence_kind": "deliberate_abstention", "settled": True, "reason": "y"},
    ]}}
    row = closure.row_from_artifact("6324.T", payload)
    assert row.open_panels == ("headline",) and row.settled_panels == ("why",)
    assert row.absence_kinds == {"headline": "upstream_unavailable", "why": "deliberate_abstention"}
    assert row.terminal is None


def test_next_pick_follows_the_five_rules_in_order() -> None:
    rows = [
        _row("READY1", readiness="ready", open_panels=(), sector="AI 光互連／CPO", bottleneck_rank=1),
        # 1. 有共識 > 沒共識
        _row("NOCONS", has_consensus=False, forward_eps_positive=None, sector="機器人", bottleneck_rank=2),
        # 2. EPS 為正 > 非正
        _row("LOSS", has_consensus=True, forward_eps_positive=False, sector="機器人", bottleneck_rank=3),
        # 3. 產業能加一（機器人尚無 ready）> 已有 ready 的產業（AI）
        _row("AI2", has_consensus=True, forward_eps_positive=True, sector="AI 光互連／CPO", bottleneck_rank=4),
        _row("ROBOT", has_consensus=True, forward_eps_positive=True, sector="機器人", bottleneck_rank=9),
        # 4. 名次：同產業、同條件時名次前者先
        _row("ROBOT_EARLY", has_consensus=True, forward_eps_positive=True, sector="機器人", bottleneck_rank=5),
        # 不在排序內排最後
        _row("UNRANKED", has_consensus=True, forward_eps_positive=True, sector=None, bottleneck_rank=None),
        # 讀不到（None）排在 False 之後、True 之前
        _row("UNKNOWN_CONS", has_consensus=None, forward_eps_positive=None, sector="機器人", bottleneck_rank=1),
    ]
    order = [r.ticker for r in closure.rank_backlog(rows)]
    assert order == ["ROBOT_EARLY", "ROBOT", "AI2", "UNRANKED", "LOSS", "UNKNOWN_CONS", "NOCONS"]
    assert "READY1" not in order                       # 到終局的不在佇列裡


def test_summary_counts_terminal_and_names_the_next_pick_with_reasons() -> None:
    rows = [
        _row("COHR", readiness="ready", open_panels=(), sector="AI 光互連／CPO", bottleneck_rank=2),
        _row("6324.T", readiness="blocked", open_panels=(), settled=("headline",), sector="機器人", bottleneck_rank=26),
        _row("SHA0.DE", has_consensus=True, forward_eps_positive=True, sector="機器人", bottleneck_rank=30),
        _row("NVDA", has_consensus=True, forward_eps_positive=True, sector="AI 光互連／CPO", bottleneck_rank=8),
    ]
    s = closure.summarize(rows)
    assert s["total"] == 4 and s["terminal_count"] == 2
    assert s["ready"] == ["COHR"] and s["settled"] == ["6324.T"]
    assert s["open_count"] == 2
    assert s["sectors_with_ready"] == ["AI 光互連／CPO"]
    assert s["next"]["ticker"] == "SHA0.DE"                  # 機器人尚無 ready 檔 → 先於 NVDA
    assert "尚無 ready 檔" in s["next"]["why"]
    text = closure.render_summary(s)
    assert "到終局 2" in text and "下一檔：SHA0.DE" in text
    assert s["rule"] == list(closure.NEXT_PICK_RULE)


def test_render_says_unread_instead_of_zero() -> None:
    s = closure.summarize([])
    assert s["next"] is None and s["terminal_count"] == 0
    text = closure.render_summary(s, notes=["Engine C 共識讀不到：OperationalError"])
    assert "未讀到：Engine C 共識讀不到" in text and "全部到終局" in text


def test_consensus_flags_prefer_next_year_and_latest_snapshot() -> None:
    class _Conn:
        def execute(self, _sql):
            class _Cur:
                def fetchall(self_inner):
                    return [
                        ("AAA", "2026-09-01", "0y", 1.0), ("AAA", "2026-09-01", "+1y", -0.5),   # 舊快照
                        ("AAA", "2026-09-08", "0y", 1.2), ("AAA", "2026-09-08", "+1y", 2.0),    # 最新
                        ("BBB", "2026-09-08", "0y", -1.0),                                        # 只有 0y 且為負
                        ("CCC", "2026-09-08", "+1y", None),                                       # 有列沒值
                    ]
            return _Cur()

    flags = closure._consensus_flags(["AAA", "BBB", "CCC", "DDD"], _Conn())
    assert flags["AAA"] == (True, True)
    assert flags["BBB"] == (True, False)
    assert flags["CCC"] == (True, None)
    assert flags["DDD"] == (False, None)


def test_sector_and_rank_use_row_order_and_registry_ticker() -> None:
    class _Reg:
        def research_ticker(self, company_id):
            return {"co:a": "AAA", "co:b": "BBB"}.get(company_id)

    payload = {
        "rows": [{"company_id": "co:a"}, {"company_id": "co:b"}, {"company_id": "co:a"}, {"company_id": "co:private"}],
        "sectors": [{"sector": "X", "actionable_ranks": [1, 3]}, {"sector": "Y", "actionable_ranks": [2]}],
    }
    got = closure._sector_and_rank(payload, _Reg())
    assert got["AAA"] == ("X", 1)        # 同一檔多列取最佳名次
    assert got["BBB"] == ("Y", 2)
    assert "co:private" not in got and len(got) == 2


# ---------------------------------------------------------------------------
# 閉包 gate（P7-c）——這幾條守的是「做完了沒」不再由執行者自稱
# ---------------------------------------------------------------------------

def _gate_row(ticker: str, readiness: str = "blocked", open_panels=("why",)) -> closure.BacklogRow:
    return closure.BacklogRow(ticker=ticker, readiness=readiness,
                              open_panels=tuple(open_panels), settled_panels=())


def test_gate_open_while_any_ticker_can_still_move() -> None:
    """做完一檔**不算**閉包——這正是 2026-09-09 的失敗（+1 就收工，還剩 67 檔）。"""
    rows = [_gate_row("AAA", "ready", ()), _gate_row("BBB"), _gate_row("CCC")]
    got = closure.closure_gate(rows)
    assert got.state == "open"
    assert got.open_count == 2 and got.actionable == ("BBB", "CCC")
    assert got.next_ticker == "BBB"


def test_gate_closed_only_when_nothing_left() -> None:
    rows = [_gate_row("AAA", "ready", ()), _gate_row("BBB", "ready", ())]
    got = closure.closure_gate(rows)
    assert got.state == "closed" and got.open_count == 0 and got.next_ticker is None


def test_gate_closed_when_remaining_are_explicitly_skipped() -> None:
    """卡 pq2／卡世界要由呼叫端**顯式**宣告——gate 不 parse 散文去猜（L16）。"""
    rows = [_gate_row("AAA", "ready", ()), _gate_row("BBB"), _gate_row("CCC")]
    got = closure.closure_gate(rows, skip=["bbb", "CCC"])   # 大小寫不敏感
    assert got.state == "closed"
    assert got.skipped == ("BBB", "CCC") and got.actionable == ()
    assert got.open_count == 2          # 仍誠實回報還有 2 檔沒到終局，不假裝歸零


def test_gate_partial_skip_still_open() -> None:
    rows = [_gate_row("BBB"), _gate_row("CCC")]
    got = closure.closure_gate(rows, skip=["BBB"])
    assert got.state == "open" and got.next_ticker == "CCC" and got.skipped == ("BBB",)


def test_gate_unknown_when_no_artifact_is_not_closed() -> None:
    """讀不到 ≠ 做完。fail closed（INV-3：「查不到了」不是合法 lifecycle）。"""
    got = closure.closure_gate([])
    assert got.state == "unknown"
    assert got.state != "closed"


def test_gate_states_are_a_closed_vocabulary() -> None:
    assert closure.GATE_STATES == ("closed", "open", "unknown")
    for rows, skip in (([], ()), ([_gate_row("A")], ()), ([_gate_row("A")], ("A",))):
        assert closure.closure_gate(rows, skip=skip).state in closure.GATE_STATES


# ---------------------------------------------------------------------------
# 品質計數器（P7-b）——守的是「衝檔數不會讓品質靜默退化」
# ---------------------------------------------------------------------------

def _artifact(implied: float | None, multiple: float | None = None,
              status: str = "available") -> dict:
    view: dict = {"headline": {"lines": [{"datum": {"value": {}}}]}}
    if multiple is not None:
        view["headline"]["lines"][0]["datum"]["value"] = {
            "eps_contribution": 0.1, "multiple_contribution": multiple, "status": "available"}
    return {
        "overview": {"implied_return": {"simple": {
            "status": status, "value": implied}}},
        "view": view,
    }


def test_quality_splits_implied_return_by_sign() -> None:
    score = closure.score_quality({
        "AAA": _artifact(0.09), "BBB": _artifact(-0.20), "CCC": _artifact(-0.05)})
    assert score.positive == ("AAA",) and score.negative == ("BBB", "CCC")
    assert score.scored == 3


def test_quality_separates_neutral_multiple_from_a_priced_one() -> None:
    """`AGENTS.md`「隱含報酬的兩個桿」：沒有 re-rating 證據時目標倍數＝校準倍數。"""
    score = closure.score_quality({
        "NEUTRAL": _artifact(0.05, multiple=-0.001),
        "PRICED": _artifact(-0.30, multiple=-0.20)})
    assert score.multiple_neutral == ("NEUTRAL",)
    assert score.multiple_priced == (("PRICED", -0.20),)


def test_quality_unreadable_is_not_counted_as_zero() -> None:
    """讀不到 ≠ 隱含報酬是 0。混進來會讓分布看起來比實際好（INV-3）。"""
    score = closure.score_quality({
        "OK": _artifact(0.05), "GONE": _artifact(None, status="missing")})
    assert score.unreadable == ("GONE",)
    assert score.scored == 1 and "GONE" not in score.positive + score.negative


def test_quality_warns_only_when_everything_is_negative() -> None:
    """全負時要能分辨「方法偏空」與「市場太貴」——那正是 ROADMAP 研究閉環 P0 的 goal。"""
    all_negative = closure.render_quality(closure.score_quality({
        "A": _artifact(-0.1, multiple=-0.2), "B": _artifact(-0.2, multiple=-0.2),
        "C": _artifact(-0.3, multiple=-0.2)}))
    assert any("方法偏空" in line and "市場太貴" in line for line in all_negative)

    mixed = closure.render_quality(closure.score_quality({
        "A": _artifact(0.1), "B": _artifact(-0.2), "C": _artifact(-0.3)}))
    assert not any("方法偏空" in line for line in mixed)


def test_quality_says_nothing_rather_than_printing_a_fake_zero() -> None:
    lines = closure.render_quality(closure.score_quality({}))
    assert len(lines) == 1 and "尚無可評分" in lines[0]


def test_attribution_is_found_structurally_not_by_a_hardcoded_path() -> None:
    """兩欄拆解住在 `view.headline.lines[*].datum.value`，那個索引會隨呈現層調整而變。"""
    deep = {"overview": {"implied_return": {"simple": {"status": "available", "value": -0.1}}},
            "view": {"a": {"b": [{"c": [{"eps_contribution": 0.0,
                                         "multiple_contribution": -0.3}]}]}}}
    score = closure.score_quality({"DEEP": deep})
    assert score.multiple_priced == (("DEEP", -0.3),)


# ---------------------------------------------------------------------------
# 未到終局那批卡在哪（2026-09-11）——計數器要自己出現，不能靠人記得去查（L14）
# ---------------------------------------------------------------------------

def test_open_profile_counts_only_open_rows_and_honours_skip() -> None:
    rows = [
        _row("READY", readiness="ready", open_panels=(), bottleneck_rank=None),
        _row("SETTLED", open_panels=(), settled=("why",), bottleneck_rank=None),
        _row("OPEN1", bottleneck_rank=None),
        _row("OPEN2", bottleneck_rank=3),
        _row("SKIPPED", bottleneck_rank=None),
    ]
    prof = closure.open_profile(rows, skip=["skipped"])   # 大小寫不該影響 skip 比對
    assert prof["open_count"] == 2
    # 終局檔與 skip 檔都不進計數——它們不是「還推得動」的那批
    assert prof["no_bottleneck_edge"] == ["OPEN1"]


def test_open_profile_treats_none_as_unread_not_as_no() -> None:
    """`None` 是讀不到，不是「否」。把它算進去等於 Missing != Zero 那個毛病（L12）。"""
    rows = [
        _row("A", has_consensus=None, forward_eps_positive=None),
        _row("B", has_consensus=False, forward_eps_positive=False),
    ]
    prof = closure.open_profile(rows)
    assert prof["no_consensus"] == ["B"]
    assert prof["forward_eps_not_positive"] == ["B"]


def test_open_profile_render_prints_every_field_even_at_zero() -> None:
    """0 也是資訊：某一項歸零時那一行仍要在，否則「沒印」與「沒發生」同形（L12／L13）。"""
    rows = [_row("A", bottleneck_rank=1, has_consensus=True, forward_eps_positive=True)]
    lines = closure.render_open_profile(closure.open_profile(rows))
    assert len(lines) == len(closure.OPEN_PROFILE_FIELDS)
    assert all("0／1 檔" in line for line in lines)


def test_open_profile_says_nothing_left_when_everything_is_terminal() -> None:
    rows = [_row("A", readiness="ready", open_panels=())]
    assert closure.render_open_profile(closure.open_profile(rows)) == ["未到終局 0 檔"]


def test_consensus_flag_requires_both_periods_positive(tmp_path) -> None:
    """0y 與 +1y 必須同時為正（2026-09-11 改）。

    事發（2026-09-10 實測 MP）：舊規則「+1y 優先、0y 兜底」會把虧損年的檔選成「可以做」，
    而它存在的理由正是要避開那些檔——MP 的 +1y 是 +0.89562，實際建模的 0y 是 −0.00374，
    整檔只能走 Abstention。實測改完有 2 檔旗標翻轉（MP、XPEV），兩檔的 0y 都是負的。
    """
    import sqlite3

    from alpha import closure

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE consensus_estimates(ticker TEXT, snapshot_date TEXT, "
                 "relative_label TEXT, estimate_avg REAL, metric TEXT)")
    conn.executemany(
        "INSERT INTO consensus_estimates VALUES (?,?,?,?, 'eps')",
        [("MPX", "2026-09-10", "0y", -0.004), ("MPX", "2026-09-10", "+1y", 0.90),
         ("GOODX", "2026-09-10", "0y", 1.1), ("GOODX", "2026-09-10", "+1y", 1.4),
         ("ONLYFARX", "2026-09-10", "+1y", 2.0)],
    )
    flags = closure._consensus_flags(["MPX", "GOODX", "ONLYFARX", "NOPEX"], conn)
    assert flags["MPX"] == (True, False), "虧損的 0y 不得被 +1y 蓋過"
    assert flags["GOODX"] == (True, True)
    # 0y 缺值時退回 +1y——方向一致地偏保守，不是把缺值當成負
    assert flags["ONLYFARX"] == (True, True)
    assert flags["NOPEX"] == (False, None)
