"""engine_b.impact（雷達精進 C1，2026-10-21）：一則 lead 碰到哪幾份敘事、讀圖、在盯條件——確定性、零 LLM。"""
from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from engine_b import impact as im


def _co(cid, name, *aliases):
    return NS(company_id=cid, display_name=name, name_aliases=tuple(aliases))


COMPANIES = {c.company_id: c for c in (
    _co("co:kaori", "Kaori Heat Treatment Co., Ltd.", "Kaori"),
    _co("co:bloom", "Bloom Energy Corporation", "Bloom Energy"),
    _co("co:mtar", "MTAR Technologies Limited", "MTAR"),
    _co("co:hubco", "Hubco Corp.", "Hubco"),
)}


def _brief(ticker, cid, *, rides=(), slots=(("demand", "需求格沒有點名誰"),), disproof=()):
    return NS(brief_id=f"ib_{ticker}", ticker=ticker, company_id=cid,
              rides=tuple(NS(node=n, unit="layer", reading_id=rid) for n, rid in rides),
              slots=tuple(NS(key=k, text=t) for k, t in slots),
              disproof=tuple(NS(link_source_ref=r) for r in disproof))


READINGS = {
    "tech:hot_box": NS(reading_id="sr_hot", angles={
        "supply_side": (("co:mtar", "supplies_to", "tech:hot_box"),),
        "demand_side": (("co:bloom", "depends_on", "tech:hot_box"),)}),
    "tech:bphe": NS(reading_id="sr_bphe", angles={"supply_side": (("co:kaori", "supplies_to", "tech:bphe"),)}),
}
WATCHES = [
    {"watch_id": "ew_1", "kind": "semantic_condition", "status": "active", "entities": ["co:mtar"],
     "source_ref": "reading:sr_hot#1", "condition": "MTAR 熱箱份額下降"},
    {"watch_id": "ew_2", "kind": "semantic_condition", "status": "active", "entities": ["co:kaori"],
     "source_ref": "brief:ib_8996.TW#1", "condition": "高力 PHE 客戶流失", "condition_role": "confirm"},
]


def _ctx(briefs, *, watches=WATCHES, node_names=None, monkeypatch=None):
    return im.Context(briefs=list(briefs), readings=READINGS, watches=watches, companies=COMPANIES, shared=frozenset(),
                      node_names=node_names or {"tech:hot_box": "SOFC hot box (Hot Box)", "tech:bphe": "Brazed plate heat exchanger (BPHE)"},
                      lifecycle=None)


BRIEFS = [
    _brief("8996.TW", "co:kaori", rides=(("tech:bphe", "sr_bphe"),),
           slots=(("demand", "最大客戶是 Bloom Energy，占營收約三成"), ("position", "板式熱交換器"))),
    _brief("MTARTECH.NS", "co:mtar", rides=(("tech:hot_box", "sr_hot"),)),
    _brief("ZZZ", "co:zzz", rides=(("tech:hot_box", "sr_hot"),)),
]


def test_a_lead_touches_its_own_company_the_readings_it_sits_on_and_the_cells_that_name_it_in_that_order(monkeypatch) -> None:
    monkeypatch.setattr(im, "HUB_SHARE", 1.1)
    ctx = _ctx(BRIEFS)
    row = im.impact({"lead_id": "L1", "title": "MTAR wins larger SOFC hot box share from Bloom Energy"}, ctx)
    assert list(row["narratives"]) == ["MTARTECH.NS", "ZZZ", "8996.TW"]                      # own → rides → 只有某一格
    assert row["narratives"]["MTARTECH.NS"][0] == "own" and row["narratives"]["ZZZ"] == ["rides:tech:hot_box"]
    assert row["narratives"]["8996.TW"] == ["slot:demand<co:bloom>"]
    assert row["readings"] == {"tech:hot_box": ["co:bloom@demand_side", "co:mtar@supply_side", "name"]}
    assert [w["watch_id"] for w in row["watches"]] == ["ew_1"] and row["watches"][0]["role"] == "反證"
    assert row["watches"][0]["owners"] == ["MTARTECH.NS", "ZZZ"]       # 歸屬問 attributed_watches：騎 sr_hot 的兩份
    assert row["absence_kind"] is None


def test_given_and_scanned_entities_stay_in_two_columns(monkeypatch) -> None:
    monkeypatch.setattr(im, "HUB_SHARE", 1.1)
    row = im.impact({"lead_id": "L2", "title": "Kaori supplies Bloom Energy", "entities": {"company_ids": ["co:kaori"]},
                     "refs": {"radar_company_ids": ["co:mtar"]}}, _ctx(BRIEFS))
    assert row["entities_given"] == ["co:kaori", "co:mtar"] and row["entities_scanned"] == ["co:bloom"]


def test_a_hub_entity_is_only_counted_not_expanded(monkeypatch) -> None:
    """樞紐：單獨就碰到 ≥ HUB_SHARE 現行敘事——不展開，只印數字（不做會恆亮，L14-4）。"""
    many = [_brief(f"T{i}", f"co:t{i}", slots=(("demand", "客戶是 Hubco"),)) for i in range(10)]
    neutral = [_brief(f"N{i}", f"co:n{i}") for i in range(30)]          # 撐起現行敘事總數：門檻＝43×10%≈4.3 份
    ctx = _ctx(BRIEFS + many + neutral)
    assert "co:hubco" in ctx.hubs and "co:mtar" not in ctx.hubs
    row = im.impact({"lead_id": "L3", "title": "Hubco and MTAR sign hot box deal"}, ctx)
    assert row["hub_entities"] == ["co:hubco"] and not any(t.startswith("T") for t in row["narratives"])
    assert row["hub_only_counts"]["narratives"] == 10 and "MTARTECH.NS" in row["narratives"]
    only_hub = im.impact({"lead_id": "L4", "title": "Hubco reports quarterly results"}, ctx)
    assert only_hub["absence_kind"] == "hub_only" and not only_hub["narratives"]


def test_a_reading_disproof_entity_is_not_a_reading_touch() -> None:
    readings = {"tech:x": NS(reading_id="sr_x", angles={"supply_side": ()}, disproof=(NS(entities=("co:kaori",)),))}
    ctx = im.Context(briefs=[], readings=readings, watches=[], companies=COMPANIES, shared=frozenset(), node_names={})
    assert im.impact({"lead_id": "L5", "title": "Kaori"}, ctx)["readings"] == {}


@pytest.mark.parametrize("title, fact, gap", [
    ("Microsoft exits Nscale deal over UK power delays", "Microsoft 因英國電網延誤退出 Nscale 資料中心合作", False),   # 雷達：英文標題＋繁中事實
    ("关键就在内存控制器挪进了底层芯片", None, True),                                                             # 主要是中文、對不到節點
    ("关键是 SOFC hot box 的份额", None, False),                                                                         # 對到節點名就不算
])
def test_the_language_gap_flag_only_fires_when_the_text_is_mainly_cjk_and_no_node_matched(monkeypatch, title, fact, gap) -> None:
    monkeypatch.setattr(im, "HUB_SHARE", 1.1)
    lead = {"lead_id": "L6", "title": title, "refs": {"radar_fact": fact} if fact else {}}
    assert im.impact(lead, _ctx(BRIEFS))["language_gap"] is gap


def test_no_entities_and_untouched_are_declared_not_silent(monkeypatch) -> None:
    monkeypatch.setattr(im, "HUB_SHARE", 1.1)
    ctx = _ctx(BRIEFS)
    assert im.impact({"lead_id": "L7", "title": "A random headline about weather"}, ctx)["absence_kind"] == "no_entities"
    lines = im.render(im.impact({"lead_id": "L7", "title": "A random headline about weather"}, ctx))
    assert "沒有點名任何名冊公司或節點" in lines[-1]


def _parked(lead_id, at, reason, title="MTAR wins larger SOFC hot box share"):
    return {"lead_id": lead_id, "status": "parked", "title": title, "refs": {"parked_reason": reason},
            "transitions": [{"at": "2026-10-01T00:00:00+00:00", "to": "researching"}, {"at": at, "to": "parked"}]}


def test_a_lead_parked_since_c4_without_disposing_its_watches_is_counted_until_the_reason_names_them(monkeypatch) -> None:
    """C4：停放理由要逐條處置對照列出的在盯條件；寫簡寫 ew_1 也算（截掉日期尾綴，#92 同一件事），但 ew_12 不算 ew_1。"""
    monkeypatch.setattr(im, "HUB_SHARE", 1.1)
    ctx = _ctx(BRIEFS)
    store = {
        "L_new": _parked("L_new", "2026-10-21T03:00:00+00:00", "MTAR 自述、等一手"),
        "L_ok": _parked("L_ok", "2026-10-22T03:00:00+00:00", "對照：ew_1 不相關（講的是新廠，不是份額）"),
        "L_near": _parked("L_near", "2026-10-22T03:00:00+00:00", "對照：ew_12 等一手"),
        "L_old": _parked("L_old", "2026-10-19T03:00:00+00:00", "舊的，不回溯"),
    }
    rows = im.undisposed(store, ctx)
    assert {(r["lead_id"], r["watch_id"]) for r in rows} == {("L_new", "ew_1"), ("L_near", "ew_1")}


def test_no_recent_parked_lead_means_the_counter_does_not_even_load_the_context(monkeypatch) -> None:
    def boom():
        raise AssertionError("沒有 C4 之後停放的 lead，不該載入對照")

    monkeypatch.setattr(im, "load_context", boom)
    assert im.undisposed({"L_old": _parked("L_old", "2026-10-19T03:00:00+00:00", "x")}) == []


def test_the_heartbeat_line_prints_zero_or_the_pairs_with_a_way_to_fix_them(monkeypatch) -> None:
    from crons.heartbeat import _undisposed_line

    monkeypatch.setattr(im, "HUB_SHARE", 1.1)
    ctx = _ctx(BRIEFS)
    store = {"L_new": _parked("L_new", "2026-10-21T03:00:00+00:00", "MTAR 自述")}
    line = _undisposed_line(leads=store, ctx=ctx)
    assert line.startswith("**停放未處置對照 1 筆**") and "L_new×ew_1" in line and "engine_b.impact --lead" in line
    assert _undisposed_line(leads={}, ctx=ctx).startswith("停放未處置對照 0 筆")


def test_render_caps_each_list_and_says_how_many_more(monkeypatch) -> None:
    monkeypatch.setattr(im, "HUB_SHARE", 1.1)
    briefs = [_brief(f"R{i}", f"co:r{i}", rides=(("tech:hot_box", "sr_hot"),)) for i in range(5)]
    row = im.impact({"lead_id": "L8", "title": "MTAR"}, _ctx(briefs))
    text = "\n".join(im.render(row, limit=3))
    assert "另 2 份" in text and "R0" in text and "R4" not in text
