"""結構讀圖（`query/structure.py`）：五個角度、以及 digest 對什麼敏感。

**這份測試真正要守的是 digest 的語意。** 讀圖結論會安靜腐壞，而偵測腐壞的唯一機制就是
「重跑五條查詢、比對結果」。所以 digest 必須：
- 對「**多了一條我當初沒讀到的邊**」敏感 ← 最危險的那種變化
- 對「值變了」敏感
- 對「回傳順序」**不**敏感 ← 否則 staleness 恆亮，等於零鑑別力（L14-4）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from query.bottleneck import collapse_assertions  # noqa: E402
from query.structure import ANGLES, build_structure, render_markdown  # noqa: E402


def _row(src, relation, dst, sub=None, **attrs):
    payload = dict(attrs)
    if sub is not None:
        payload["substitutability"] = sub
    return {
        "src": src, "relation": relation, "dst": dst,
        "attributes": payload, "confidence": 0.8,
        "origin": "Someone", "source_type": "filing",
        "source_doc_id": f"doc_{src}_{relation}_{dst}", "published_at": "2026-01-01",
    }


#: CW laser 的形狀：技術繞不掉（需求側 4）、供應層競爭（5/3/2）、下一層更卡（5）、有反向路徑。
CW_ROWS = [
    _row("tech:pluggable_transceiver", "depends_on", "tech:cw_dfb_laser", 4),
    _row("tech:cw_dfb_laser", "is_component_of", "tech:cpo"),
    _row("co:coherent", "supplies_to", "tech:cw_dfb_laser", 5),
    _row("co:lumentum", "supplies_to", "tech:cw_dfb_laser", 3),
    _row("co:luxnet", "supplies_to", "tech:cw_dfb_laser", 2),
    _row("tech:cw_dfb_laser", "depends_on", "mat:inp_substrate", 5),
    _row("prod:blazar", "competes_with", "tech:cw_dfb_laser"),
]


def _edges(rows):
    return list(collapse_assertions(rows).values())


def _view(rows=None):
    return build_structure("tech:cw_dfb_laser", _edges(rows or CW_ROWS))


def test_five_angles_in_fixed_order() -> None:
    assert [name for name, _ in ANGLES] == [
        "demand_side", "supply_side", "next_layer", "counter_path", "anchor"]


def test_each_angle_picks_up_its_own_edges() -> None:
    view = _view()
    assert len(view.angles["demand_side"]) == 2      # depends_on 進來 ＋ is_component_of 出去
    assert len(view.angles["supply_side"]) == 3
    assert len(view.angles["next_layer"]) == 1
    assert len(view.angles["counter_path"]) == 1


def test_digest_changes_when_an_edge_i_never_read_appears() -> None:
    """**最危險的那種變化**：有人補了第四家供應商，供給側分布變了、A/B 判讀可能翻轉。

    只存「我讀過這三條」偵測不到它；存「這個查詢當時回這個集合」才偵測得到。
    空跑檢查：把 `result_digest()` 改成只 hash `node` → 這條會紅。
    """
    before = _view().result_digest()
    after = _view(CW_ROWS + [_row("co:vpec", "supplies_to", "tech:cw_dfb_laser", 2)])
    assert after.result_digest() != before


def test_digest_changes_when_a_value_changes() -> None:
    """有人把某條邊的 sub 由 2 改判成 5——邊沒有增減，但結論可能整個翻。"""
    before = _view().result_digest()
    mutated = [r for r in CW_ROWS if not (r["src"] == "co:luxnet")]
    mutated.append(_row("co:luxnet", "supplies_to", "tech:cw_dfb_laser", 5))
    assert _view(mutated).result_digest() != before


def test_digest_is_stable_against_row_order() -> None:
    """⚠ 對回傳順序敏感的話 staleness 會恆亮——恆亮＝零鑑別力（L14-4），
    而且會訓練人忽略它。"""
    assert _view(list(reversed(CW_ROWS))).result_digest() == _view().result_digest()


def test_digest_ignores_unrelated_edges() -> None:
    """圖裡別的地方改了，不該讓這個節點的讀圖變 stale（否則每天都在重讀）。"""
    noise = CW_ROWS + [_row("co:mp_materials", "supplies_to", "mat:rare_earth_magnets", 4)]
    assert _view(noise).result_digest() == _view().result_digest()


def test_output_states_a_distribution_not_a_single_max() -> None:
    """供給側要看**分布**：單一最大值會讓「一家獨大」與「大家都高」長得一樣。"""
    text = render_markdown(_view())
    assert "5／3／2" in text


def test_output_does_not_decide_a_or_b() -> None:
    """**零判斷**是契約：它給角度，不給結論（L15-2：LLM 可以解析與提議，不可以授權）。"""
    view = _view()
    assert "verdict" not in view.as_dict()
    assert "classification" not in view.as_dict()
    text = render_markdown(view)
    assert "由讀的人決定" in text
    # 界線也必須印出來，否則下一個讀者會以為 digest 沒變＝判斷還是對的
    assert "不是「結論對不對」" in text


def test_missing_anchor_is_said_out_loud() -> None:
    """走不到錨要明講，且要說出兩種可能——不得只印一句「無」（INV-3）。"""
    orphan = [_row("co:someone", "supplies_to", "tech:orphan", 5)]
    view = build_structure("tech:orphan", _edges(orphan))
    text = render_markdown(view)
    assert "走不到任何已登記的需求錨" in text


def test_constrained_by_answers_demand_side_and_next_layer_not_only_counter_path() -> None:
    """`constrained_by` 是 counter path，**但同時也是「誰需要它／它卡在誰身上」的答案**。

    這三個角度問的是方向，`counter_path` 問的是證據性質——同一條邊同時是兩者的答案，
    不是重複計算。事發（2026-09-18）：`_DEMAND_INBOUND` 與 `next_layer` 各自硬編
    `depends_on`，於是圖裡逐字寫著「co:coherent 受限於 tech:inp_dfb_laser」的那條邊，
    在 `tech:inp_dfb_laser` 的需求側是看不見的（L16：分類沒跟著資料走到消費端）。
    """
    rows = [
        _row("co:coherent", "constrained_by", "tech:inp_dfb_laser", 5),
        _row("co:macom", "supplies_to", "tech:inp_dfb_laser", 3),
    ]
    laser = build_structure("tech:inp_dfb_laser", _edges(rows))
    demand = [(e.src, e.relation) for e in laser.angles["demand_side"]]
    assert ("co:coherent", "constrained_by") in demand
    # 同一條邊照樣留在反向路徑——兩個角度問的不是同一件事。
    assert [e.relation for e in laser.angles["counter_path"]] == ["constrained_by"]

    coherent = build_structure("co:coherent", _edges(rows))
    assert [(e.relation, e.dst) for e in coherent.angles["next_layer"]] == [
        ("constrained_by", "tech:inp_dfb_laser")
    ]


def test_evidence_column_is_computed_not_a_dataclass_default() -> None:
    """證據欄必須真的算過——**預設值偽裝成觀測**是這一欄先前的實況（2026-09-18 實測）。

    `CanonicalEdge.evidence` 的 `"self_reported"` 是 dataclass 預設值，而賦值只寫在
    `rank_bottlenecks()` 裡；本模組不經過它，於是這張表的「證據」欄在**全圖每一條邊**上
    都印「供應商自報」——526 條 canonical 邊裡 **430 條（81.7%）印錯**，真實分布是
    外部印證 217（41.3%）／待判定 108／自報·filing 105／供應商自報 96。

    讀五個角度判 A 還是 B 的人會以為所有證據都是自報，而「還沒算」與「算出來就是自報」
    在畫面上完全同形（L12）。這條測試守的是：修法是**去用既有的唯一 owner**
    （`classify_evidence`），不是在這裡重造一套判定（L16）。
    """
    source = (ROOT / "query" / "structure.py").read_text(encoding="utf-8")
    assert "classify_evidence" in source, "證據欄必須走排序那邊的唯一 owner"
    # 不得自己重造判定：這些是 classify_evidence 內部的字彙，出現在這裡就代表抄了第二份
    for token in ("externally_corroborated", "counterparty_joint", "EVIDENCE_RANK"):
        assert token not in source, f"不得在本模組重造證據判定（{token}）"


def test_shares_collapse_assertions_with_the_ranking() -> None:
    """**不自己收斂**：兩邊對同一條邊必須給同一個值，否則消費端會各自偏離（L16）。"""
    source = (ROOT / "query" / "structure.py").read_text(encoding="utf-8")
    assert "collapse_assertions" in source
    # 同一條邊兩份文件、其中一份沒填 sub：收斂規則是「逐屬性取最高 confidence 那份」
    rows = [
        _row("co:coherent", "supplies_to", "tech:cw_dfb_laser", 5),
        _row("co:coherent", "supplies_to", "tech:cw_dfb_laser"),
    ]
    view = build_structure("tech:cw_dfb_laser", _edges(rows))
    assert view.angles["supply_side"][0].substitutability == 5


def test_is_component_of_answers_the_next_layer_from_the_container_side() -> None:
    """`A is_component_of B` ⇒ **B 卡在 A 身上**，所以它屬於 B 的「下一層」。

    事發（2026-09-18）：這個角度原本只收 `N depends_on／constrained_by X`，
    於是**全圖 68 條 `is_component_of` 在 dst 側 100% 看不見**——
    `tech:isolator` 的五個角度全空、`tech:cpo` 的下一層只有 4 條（實際 21 條）。
    與同日修掉的 `constrained_by` 同一族：角度的成員資格漏了一半，
    而漏掉的那一半不會讓任何東西變紅（L17-3 的對稱面）。
    """
    edges = list(collapse_assertions([
        _row("tech:els", "is_component_of", "tech:isolator"),
        _row("tech:isolator", "depends_on", "mat:garnet"),
    ]).values())

    view = build_structure("tech:isolator", edges)
    nxt = {(e.src, e.relation, e.dst) for e in view.angles["next_layer"]}
    assert ("tech:els", "is_component_of", "tech:isolator") in nxt, "容器側要看得到它的零件"
    assert ("tech:isolator", "depends_on", "mat:garnet") in nxt, "原本那一半不得被擠掉"

    # 零件側的視角不變：對 A 而言這條邊仍是需求側（「有人需要我」）。
    a = build_structure("tech:els", edges)
    assert ("tech:els", "is_component_of", "tech:isolator") in {
        (e.src, e.relation, e.dst) for e in a.angles["demand_side"]}
    assert not a.angles["next_layer"]


def test_quotes_reach_the_reader_and_absence_of_quotes_is_stated() -> None:
    """⚠ 這個工具存在的意義取決於它印不印得出逐字（L18）。

    2026-09-18 之前它的輸出裡**一個字都不是「當初那份文件實際寫的」**，
    於是用它讀圖的人結構上不可能發現 `external_laser_source is_component_of isolator`
    這種錯——那條邊的逐字只是列舉 Coherent 做的兩樣東西。
    ⚠ 沒有逐字時也必須明說，否則「這條邊沒有逐字」與「我沒印逐字」同形（L13-2）。
    """
    edges = list(collapse_assertions([
        _row("co:a", "supplies_to", "tech:x"),
        _row("co:b", "supplies_to", "tech:x"),
    ]).values())
    view = build_structure("tech:x", edges)

    quotes = {("co:a", "supplies_to", "tech:x"): [
        {"quote": "A ships X in volume today.", "locator": "p.3",
         "doc": "doc_a", "tier": 1, "origin": "A"}]}
    text = render_markdown(view, quotes)
    assert "A ships X in volume today." in text
    assert "doc_a" in text and "tier 1" in text
    assert "這條邊在圖裡沒有任何逐字" in text, "co:b 沒有逐字，必須明說"

    # 不要逐字時，輸出不得混進逐字欄
    plain = render_markdown(view)
    assert "A ships X in volume today." not in plain
    assert "這條邊在圖裡沒有任何逐字" not in plain
