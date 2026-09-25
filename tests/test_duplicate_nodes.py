"""重複節點候選偵測器（L18 的 L2 層）的守門測試。

守的是四件事，每一件都對應一個踩過的坑：
① 規則只有兩條——第三條（同 token 數、只差一個）被真實資料當場推翻，不得回來；
② 逐字必須到得了輸出——這個偵測器存在的全部理由就是「不必繞過自己的工具」（L18）；
③ `mentioned` 只說「registry 提過」，不得升格成「已決定不併」（宣稱 authority 沒有的東西）；
④ 只提名不合併——本模組不得寫任何東西、不得解析 canonical id。
"""
from __future__ import annotations

from pathlib import Path

from query.duplicate_nodes import (
    MATCH_RULES, QUOTES_PER_NODE, bucketize, pair_candidates, registry_mentions, render_markdown,
)


def _row(node: str, name: str = "", *, level: str = "device_chip", degree: int = 2,
         quotes: list[str] | None = None) -> dict:
    return {
        "node": node, "name": name, "abstraction_level": level, "degree": degree,
        "quotes": [{"quote": q, "locator": "loc", "doc": "doc:1"} for q in (quotes or [])],
    }


def test_id_token_subset_is_the_inp_eml_case() -> None:
    """`tech:eml` ⊂ `tech:inp_eml`——2026-09-18 真的被判為同一個東西的那一對。"""

    pairs = pair_candidates([_row("tech:eml", "EML"), _row("tech:inp_eml", "Indium Phosphide EML")])
    assert len(pairs) == 1
    assert pairs[0]["pair"] == ("tech:eml", "tech:inp_eml")
    assert pairs[0]["rules"] == ["id_token_subset"]


def test_name_identical_catches_cross_prefix_duplicates() -> None:
    """`prod:` 與 `tech:` 的同名節點也要抓到——重複不會只發生在同一個前綴裡。"""

    pairs = pair_candidates([
        _row("prod:optical_interposer", "POET Optical Interposer™"),
        _row("tech:poet_optical_interposer", "POET Optical Interposer", level="module_subsystem"),
    ])
    assert len(pairs) == 1
    assert pairs[0]["rules"] == ["id_token_subset", "name_identical"]
    # 同一對命中兩條規則時**兩條都要留著**：壓成一個值會讓「兩條都說是」與「只有一條」同形。
    assert pairs[0]["same_abstraction_level"] is False


def test_the_rejected_third_rule_never_comes_back() -> None:
    """⚠ 2026-09-18 實測：「同 token 數、只差一個 token」讓所有單 token id 互相全配。

    `prod:reliant` 與 `mat:photoresist` 各只有一個 token，對稱差是 1——規則會把它們配成
    候選。那不是門檻沒調好，是規則本身零鑑別力（L16-4：會誤報的防呆本身就是過度工程）。
    這條測試守的是**它不得以任何形式回來**。
    """

    pairs = pair_candidates([_row("prod:reliant", "Reliant"), _row("mat:photoresist", "Photoresist")])
    assert pairs == []
    assert set(MATCH_RULES) == {"id_token_subset", "name_identical"}


def test_different_names_that_share_nothing_are_not_candidates() -> None:
    """`tech:ocs`／`tech:optical_circuit_switch` 抓不到——這是已知限制，明寫在輸出裡。

    抓不到不是 bug，是這兩條規則的射程。誠實寫出來，比用一條會誤報的規則假裝抓得到好。
    """

    pairs = pair_candidates([
        _row("tech:ocs", "Optical Circuit Switch"),
        _row("tech:optical_circuit_switch", "Optical circuit switching"),
    ])
    assert pairs == []
    out = "\n".join(render_markdown([], node_total=2))
    assert "tech:optical_circuit_switch" in out  # 限制要說出來，不能只是沒有


def test_quotes_reach_the_output_or_the_detector_is_pointless() -> None:
    """逐字沒到輸出，用它的人就跟 2026-09-18 之前一樣只能相信 label（L18）。"""

    pairs = pair_candidates([
        _row("prod:reliant", "Reliant", quotes=["our Reliant® product line offers new and refurbished"]),
        _row("prod:reliant_product_line", "Reliant Product Line",
             quotes=["our Reliant® product line offers new and refurbished"]),
    ])
    out = "\n".join(render_markdown(bucketize(pairs, {})["unmentioned"], node_total=2))
    assert out.count("our Reliant® product line offers new and refurbished") == 2


def test_truncated_quotes_say_so_and_empty_ones_say_so_louder() -> None:
    """截斷要說話（INV-3）；一段逐字都沒有的節點要被標出來——它可能根本不是實體。"""

    many = [f"quote {i}" for i in range(QUOTES_PER_NODE + 3)]
    pairs = pair_candidates([_row("tech:eml", "EML", quotes=many), _row("tech:inp_eml", "InP EML")])
    out = "\n".join(render_markdown(bucketize(pairs, {})["unmentioned"], node_total=2))
    assert f"另有 {3} 段逐字" in out
    assert "一段逐字都沒有" in out


def test_registry_mention_needs_both_ids_and_never_claims_a_verdict() -> None:
    """`mentioned` 只是「這段 note 同時提到這兩個 id」——**不是**「已決定不併」。

    同一個 registry 裡「刻意不併」與「留待研究判斷」長得一模一樣（兩者 2026-09-18 都在
    `config/entity_aliases.json` 裡真實存在）。機械讀得出前者、讀不出後者，所以只端逐字。
    """

    canonical = {
        "tech:nand": {"basis": "semantic_reviewed", "approval_receipt": "todo:505",
                      "note": "tech:3d_nand_manufacturing 刻意不併：它的唯一 quote 完全沒提 3D NAND"},
        "tech:dram_manufacturing": {"basis": "name_identical",
                                    "note": "tech:dram／tech:dram_technology 名稱不同，留待研究判斷"},
    }
    assert registry_mentions(("tech:nand", "tech:3d_nand_manufacturing"), canonical)[0]["canonical"] \
        == "tech:nand"
    # ⚠ 首版用裸的 `in` 判 note，`tech:nand` 命中了 `tech:nand_flash` 的子字串——本測試抓到的。
    # 現在 `tech:nand` 是靠「它是 canonical」命中，不是靠子字串。
    assert registry_mentions(("tech:nand", "tech:hbm"), canonical) == []
    assert registry_mentions(("tech:dram", "tech:dram_technology"), canonical)[0]["canonical"] \
        == "tech:dram_manufacturing"

    pairs = pair_candidates([_row("tech:nand", "NAND"), _row("tech:3d_nand_manufacturing", "3D NAND")])
    buckets = bucketize(pairs, canonical)
    assert len(buckets["mentioned"]) == 1 and buckets["unmentioned"] == []
    lines = render_markdown(buckets["mentioned"], node_total=2)
    # 判決字眼只准出現在免責段（`>` 開頭）裡——替 note 下結論不行，照抄 note 可以。
    assert [ln for ln in lines if "已決定不併" in ln and not ln.startswith(">")] == []
    assert any("刻意不併" in ln for ln in lines)  # 但 note 自己說的那句要看得到


def test_pair_order_is_deterministic() -> None:
    """任何人重跑得到同一組——通用的那一端在前，等長取字母序（與 registry 的 canonical 選法同源）。"""

    a, b = _row("tech:inp_eml", "InP EML"), _row("tech:eml", "EML")
    assert pair_candidates([a, b])[0]["pair"] == pair_candidates([b, a])[0]["pair"]
    assert pair_candidates([a, b])[0]["pair"] == ("tech:eml", "tech:inp_eml")


def test_module_only_nominates() -> None:
    """只提名不合併：本模組不得寫檔、不得解析 canonical id（那是 identity/entities.py 的事）。"""

    src = Path("query/duplicate_nodes.py").read_text(encoding="utf-8")
    for forbidden in ("entities.resolve", "resolve_document", "open(", "write_text", "MERGE"):
        assert forbidden not in src, f"偵測器不該碰 {forbidden}"


def test_the_app_page_prints_the_verbatim_not_just_the_ids() -> None:
    """APP 那一區塊若只印 id 與 name，它就跟 2026-09-18 之前的工具一樣沒有判斷依據。"""

    source = Path("webapp/static/app.js").read_text(encoding="utf-8")
    # Step 2.6：重複節點成為走圖第 9 型，APP 在走圖頁逐對印兩端的逐字（不再是獨立區塊）。
    assert "function duplicateSide" in source and "function walkHitList" in source
    assert "q.quote" in source, "APP 區塊必須印出逐字本身"
    assert "duplicateSide(hit.left)" in source and "duplicateSide(hit.right)" in source


def test_the_queue_segment_points_at_a_consumer_that_really_mentions_it() -> None:
    """INV-4：producer 指得出 consumer。consumer 欄寫了 research-drain，那份 skill 就必須真的提到它。"""

    from engine_b.queue_segments import SEGMENT_BY_KEY

    # Step 2.6：`duplicate_node_candidates` 段併進 `graph_holes`（走圖第 9 型）——consumer 跟著搬。
    seg = SEGMENT_BY_KEY["graph_holes"]
    assert seg.cost == "research" and "query.graph_walk" in seg.consumer
    skill = Path("skills/research-drain/SKILL.md").read_text(encoding="utf-8")
    assert "query.graph_walk" in skill, "consumer 指到的 skill 沒提到它＝那個 consumer 是說謊"
    assert "query.duplicate_nodes" in skill, "判定同一個之後的逐字檢視仍走 duplicate_nodes"
