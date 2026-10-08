"""Phase 7 Step 7.0e：個股頁首屏五題＋「是不是新賭注」（和持有的 alpha 檔共用需求錨／層）。

使用者 2026-10-04 A1（首屏照五題排）、A3（共用需求錨）。兩件事都**只呈現**：不排序、不打分、不加權、不進候選狀態前提
（plan §0 第 3 條）。五題的標題與「哪一格放哪一題」只有 contracts 一份，經 `.meta.json` 給 APP（L16）；
共用需求錨的需求錨只取結構表的逐列錨（`demand_anchor`／`anchor_basis`，唯一來源），層與插槽只取 `seats_from_edges`。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from alpha.narrative.contracts import SLOT_KEYS_V2
from alpha.providers.candidates import bet_index, shared_bet
from alpha.providers.structure_readings import seats_from_edges
from briefing.analyst_view.contracts import FIRST_SCREEN_PARTS
from briefing.analyst_view.page_schema import BLOCK_READINGS, BLOCKS, FIRST_SCREEN_SECTIONS

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "webapp" / "static" / "app.js"

A, B, C, D = "co:alpha", "co:bravo", "co:charlie", "co:delta"
TICKERS = {A: "AAA", B: "BBB", C: "CCC", D: "DDD"}
REG = SimpleNamespace(research_ticker=lambda cid: TICKERS.get(cid))
LAYER, OTHER, SOCKET = "tech:cw_dfb", "mat:inp_substrate", "tech:socket_x"
ANCHOR, ANCHOR2 = "anchor:ai_datacenter", "anchor:telecom"
STAMP = "2026-10-04T05:32:00+00:00"


def _held(*cids: str) -> dict:
    return {"status": "ok", "reason": None, "unresolved": [], "beta_excluded": 0, "zero_shares": 0,
            "by_company": {c: {"sheet_ticker": TICKERS[c], "source": "registry"} for c in cids}}


def _structure(*rows: tuple) -> dict:
    """結構表 artifact 的逐列錨（只帶這一步讀的欄位）：(company_id, bottleneck, demand_anchor, anchor_basis)。"""
    return {"rows": [{"company_id": c, "bottleneck": b, "demand_anchor": a, "anchor_basis": basis,
                      "demand_anchor_name": (f"錨{a[-3:]}" if a else None), "bottleneck_name": None}
                     for c, b, a, basis in rows], "generated_at": STAMP}


SEATS = {A: [LAYER], B: [LAYER, OTHER], C: [SOCKET], D: [OTHER]}


# ---------------------------------------------------------------------------
# 首屏：對照只有一份（2026-10-08 個股頁 S5 起住 page_schema；五題退役，①→論點、②③④⑤→清單）
# ---------------------------------------------------------------------------

def test_the_first_screen_places_every_v2_slot_and_part_exactly_once() -> None:
    assert [s["key"] for s in FIRST_SCREEN_SECTIONS] == ["thesis", "essay", "deep", "checklist"]
    slots = [s for r in BLOCK_READINGS for s in r.slots]
    assert sorted(slots) == sorted(SLOT_KEYS_V2) and len(slots) == len(set(slots))     # 七格各放一次，不漏不重
    parts = [p for r in BLOCK_READINGS for p in r.parts]
    assert sorted(parts) == sorted(FIRST_SCREEN_PARTS) and len(parts) == len(set(parts))
    by_block = {r.block: r for r in BLOCK_READINGS}
    # 原五題的對照照搬到塊（brainstorm §5 回饋 #11 的首屏形式）：①押什麼→論點 B1；②夠大嗎→B7（demand 進深入的 B2、priced_in 進短文的 B6）；
    # ③錯了怎麼知道→B8（when 進接下來看什麼 B11）；④會不會死→B9；⑤是不是新賭注→B10
    assert by_block["B1"].slots == ("our_bet", "bottleneck", "position")
    # 2026-10-08 使用者：「對我來說都是營收，一起看最好」——「出現在數字裡了嗎」從 B7 搬到 B3 營收從哪來
    assert by_block["B7"].slots == ("what_must_be_true",) and by_block["B7"].parts == ()
    assert by_block["B3"].parts == ("in_numbers",) and by_block["B3"].pending
    assert by_block["B2"].slots == ("demand",) and by_block["B6"].slots == ("priced_in",)
    assert by_block["B6"].parts == ("priced_in",)
    assert by_block["B8"].parts == ("disproof", "confirm") and by_block["B11"].slots == ("when",)
    assert by_block["B9"].parts == ("will_it_die", "wipeout") and by_block["B10"].parts == ("shared_bet",)
    # 沒有句子來源的塊照合約印 pending（規則 7）；S3 的塊寫「還沒做」
    assert all(r.pending for r in BLOCK_READINGS if not (r.slots or r.parts))
    assert "還沒做" in by_block["B12"].pending


def test_the_meta_carries_the_one_copy_and_app_js_keeps_none(tmp_path: Path) -> None:
    from webapp.materialize import write_vocabularies
    from webapp.store import ArtifactStore

    meta = json.loads(write_vocabularies(ArtifactStore(tmp_path)).read_text(encoding="utf-8"))
    assert "first_screen_questions" not in meta                                 # 退役的那一份不再出貨
    screen = meta["page_schema"]["first_screen"]
    assert [s["key"] for s in screen["sections"]] == [s["key"] for s in FIRST_SCREEN_SECTIONS]
    assert screen["readings"]["B1"]["slots"] == ["our_bet", "bottleneck", "position"]
    import re

    source = APP_JS.read_text(encoding="utf-8")
    assert "schema.first_screen" in source and "first_screen_questions" not in source
    code = re.sub(r"(?m)//.*$", "", re.sub(r"/\*.*?\*/", "", source, flags=re.S))   # 註解裡提到塊名不算第二份
    for block in BLOCKS:
        assert block.title not in code, block.title                            # 塊名不在前端（不留第二份，L16）
    for section in FIRST_SCREEN_SECTIONS:
        if len(section["title"]) > 4:
            assert section["title"] not in code, section["title"]
    body = source.split("function questionPart(", 1)[1].split("\n}\n", 1)[0]
    for part in FIRST_SCREEN_PARTS:
        assert f"'{part}'" in body, part                                       # 每個元件前端都認得
    assert "還不認得" in body                                                   # 認不得的照印，不靜默略過（INV-3）
    # v1 短評（格不同）照舊版面：帶齊合約放的每一格才用新首屏
    gate = source.split("function schemaFirstScreen(", 1)[1].split("\n}\n", 1)[0]
    assert ".every(" in gate and "'brief:' + slot" in gate


# ---------------------------------------------------------------------------
# 是不是新賭注：共用的需求錨與層
# ---------------------------------------------------------------------------

def test_seats_are_one_function_shared_with_the_readings_panel() -> None:
    edges = [SimpleNamespace(src=A, relation="supplies_to", dst=LAYER),
             SimpleNamespace(src=A, relation="develops", dst=SOCKET),
             SimpleNamespace(src=A, relation="supplies_to", dst=B),             # 公司對公司不是坐的層
             SimpleNamespace(src=A, relation="depends_on", dst=OTHER),           # 不是坐的關係
             SimpleNamespace(src="tech:x", relation="supplies_to", dst=LAYER)]   # 不是公司
    assert seats_from_edges(edges) == {A: [LAYER, SOCKET]}                     # 排序後（cw_dfb < socket_x）
    source = (ROOT / "alpha" / "providers" / "structure_readings.py").read_text(encoding="utf-8")
    context = source.split("def seat_readings_context(", 1)[1].split("\ndef ", 1)[0]
    assert "seats_from_edges(edges)" in context                                # 讀圖面板同一個函式（L16）


def test_two_held_companies_on_one_layer_list_each_other_with_the_anchor_basis() -> None:
    bets = bet_index(_structure((A, LAYER, ANCHOR, "row"), (B, LAYER, ANCHOR, "company")), SEATS)
    held = _held(A, B)
    a = shared_bet(A, "AAA", held=held, bets=bets, registry=REG)
    b = shared_bet(B, "BBB", held=held, bets=bets, registry=REG)
    assert [r["ticker"] for r in a["rows"]] == ["BBB"] and [r["ticker"] for r in b["rows"]] == ["AAA"]
    assert a["rows"][0]["state"] == "held" and a["absence"] is None
    assert a["rows"][0]["shared_layers"] == [{"node": LAYER, "name": None}]
    assert a["rows"][0]["shared_anchors"] == [{"node": ANCHOR, "name": "錨ter", "basis": {"this": "row",
                                                                                          "other": "company"}}]
    # 錨的來處跟著值走（L12）：有一邊是退回公司才走到的，句子標「公司層」
    assert any("BBB" in line and "錨ter（公司層）" in line and LAYER in line for line in a["lines"])


def test_a_row_level_anchor_wins_over_a_company_fallback_for_the_same_company() -> None:
    bets = bet_index(_structure((A, LAYER, ANCHOR, "company"), (A, OTHER, ANCHOR, "row")), SEATS)
    assert bets["anchors"][A] == {ANCHOR: "row"}


def test_rows_follow_ticker_letters_not_how_much_is_shared() -> None:
    # BBB 只共用一層、DDD 共用一個錨加兩層——照共用多寡排會是 DDD 在前；字母序是 BBB 在前
    bets = bet_index(_structure((A, LAYER, ANCHOR, "row"), (D, LAYER, ANCHOR, "row")),
                     {A: [LAYER, OTHER], B: [OTHER], D: [LAYER, OTHER]})
    out = shared_bet(A, "AAA", held=_held(D, B), bets=bets, registry=REG)
    assert [len(r["shared_anchors"]) + len(r["shared_layers"]) for r in out["rows"]] == [1, 3]
    assert [r["ticker"] for r in out["rows"]] == ["BBB", "DDD"]               # 字母序是索引，不是名次


def test_the_company_itself_is_never_its_own_peer_and_a_peer_without_overlap_is_not_listed() -> None:
    bets = bet_index(_structure((A, LAYER, ANCHOR, "row"), (C, SOCKET, ANCHOR2, "row")), SEATS)
    out = shared_bet(A, "AAA", held=_held(A, C), bets=bets, registry=REG)
    assert out["rows"] == [] and out["absence"] is None
    assert any("沒有共用" in line for line in out["lines"])                      # 沒有共用是答案，不是缺席


def test_sheet_unreadable_suspends_the_comparison_instead_of_saying_new_bet() -> None:
    bets = bet_index(_structure((A, LAYER, ANCHOR, "row")), SEATS)
    held = {"status": "upstream_unavailable", "reason": "持股未讀到，已持有判定暫停（讀取失敗）", "by_company": {}}
    out = shared_bet(A, "AAA", held=held, bets=bets, registry=REG)
    assert out["absence"]["kind"] == "upstream_unavailable" and out["rows"] == []
    assert any("持有判定暫停" in line or "比不出來" in line for line in out["lines"])
    assert not any("沒有共用" in line for line in out["lines"])                  # 沒讀到持股≠沒有共用（L12）


def test_structure_table_unreadable_still_compares_layers_and_says_which_half_is_missing() -> None:
    bets = bet_index({"absence": {"kind": "upstream_unavailable", "reason": "結構表讀不到（尚未 materialize）"}}, SEATS)
    out = shared_bet(A, "AAA", held=_held(B), bets=bets, registry=REG)
    assert out["anchors_absence"]["kind"] == "upstream_unavailable"
    assert out["rows"][0]["shared_layers"] == [{"node": LAYER, "name": None}] and out["rows"][0]["shared_anchors"] == []
    assert any("需求錨這半邊沒比" in line for line in out["lines"])


def test_no_reachable_anchor_is_said_plainly() -> None:
    bets = bet_index(_structure((B, LAYER, ANCHOR, "row")), SEATS)              # A 在結構表走不到任何錨
    out = shared_bet(A, "AAA", held=_held(B), bets=bets, registry=REG)
    assert any("走不到任何需求錨" in line for line in out["lines"])
    assert out["rows"][0]["shared_layers"] and out["rows"][0]["shared_anchors"] == []


def test_no_inputs_loaded_is_an_absence_not_an_empty_answer() -> None:
    out = shared_bet(A, "AAA", held=_held(B), bets=None, registry=REG)
    assert out["absence"]["kind"] == "upstream_unavailable" and out["rows"] == []


def test_the_output_has_no_score_rank_weight_or_position_field_names() -> None:
    from alpha.contracts import FORBIDDEN_COMPOSITE_FIELDS, FORBIDDEN_POSITION_TOKENS

    bets = bet_index(_structure((A, LAYER, ANCHOR, "row"), (B, LAYER, ANCHOR, "row")), SEATS)
    out = shared_bet(A, "AAA", held=_held(B), bets=bets, registry=REG)

    def keys(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from keys(value)
        elif isinstance(node, list):
            for item in node:
                yield from keys(item)

    banned = set(FORBIDDEN_POSITION_TOKENS) | {"held", "holdings", "rank", "score", "weight"}
    assert not [k for k in keys(out) if set(str(k).lower().split("_")) & banned or k in FORBIDDEN_COMPOSITE_FIELDS]


def test_the_board_and_the_stock_page_carry_the_same_shared_bet(monkeypatch: pytest.MonkeyPatch) -> None:
    import alpha.providers.briefs as briefs_mod
    from alpha.providers import candidates as cand
    from tests.test_stock_page_phase3 import CO, T, TODAY, _brief, _context, _tq

    brief = _brief()
    monkeypatch.setattr(briefs_mod, "read_brief_records", lambda ticker: ([brief], []))
    other = "co:peer"
    held = {"status": "ok", "reason": None, "unresolved": [], "beta_excluded": 0, "zero_shares": 0,
            "by_company": {other: {"sheet_ticker": "PEER", "source": "registry"}}}
    bets = bet_index(_structure((CO, LAYER, ANCHOR, "row"), (other, LAYER, ANCHOR, "row")),
                     {CO: [LAYER], other: [LAYER]})
    registry = SimpleNamespace(research_ticker=lambda cid: {CO: T, other: "PEER"}.get(cid))
    ctx = _context(held=held, bets=bets, registry=registry)
    page = cand.page_input(ctx, T, CO, three_questions=_tq())
    board = cand.derive_row(T, CO, records=[brief], today=TODAY, reading_rows=ctx["reading_rows"], watches=[],
                            lifecycle={}, edge=ctx["edges"][T], three_questions=_tq(), held=held, bets=bets,
                            registry=registry)
    assert page["row"]["shared_bet"] == board["shared_bet"]
    assert [r["ticker"] for r in board["shared_bet"]["rows"]] == ["PEER"]
    assert board["group"] == "priced_wait"                                     # 候選狀態照宣告，不被它改（G1、G6）


def test_bet_structure_reads_the_structure_table_artifact_and_declares_when_it_cannot() -> None:
    from webapp.contracts import ArtifactUnavailable
    from webapp.materialize import bet_structure

    rows = [{"company_id": A, "bottleneck": LAYER, "demand_anchor": ANCHOR, "anchor_basis": "row",
             "demand_anchor_name": "AI 資料中心", "bottleneck_name": "CW DFB", "chain": [ANCHOR], "evidence": "x"}]
    ok = SimpleNamespace(read=lambda kind: ({"rows": rows, "generated_at": STAMP}, None))
    got = bet_structure(ok)
    assert got["generated_at"] == STAMP and got["rows"][0]["demand_anchor"] == ANCHOR
    assert "evidence" not in got["rows"][0]                                   # 只帶這一步讀的欄位

    def missing(kind):
        raise ArtifactUnavailable(kind, "尚未 materialize")

    absent = bet_structure(SimpleNamespace(read=missing))
    assert absent["absence"]["kind"] == "upstream_unavailable" and "尚未 materialize" in absent["absence"]["reason"]
