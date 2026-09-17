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
