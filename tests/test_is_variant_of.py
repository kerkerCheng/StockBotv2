"""`is_variant_of`（2026-09-19，[613] 選項 B）的守門測試。

它守的是一句話：**加這個 relation 的目的是讓那 17 條從不該在的地方離開，
不是給它們一個新位置。** 所以測試的重點不是「它存在」，而是「它沒有偷偷進到
任何走訪清單裡」——那正是下一個人最容易順手做、而且做了不會有東西變紅的事。

事發（2026-09-18 逐條重判 92 條 `is_component_of`）：17 條（18.5%）其實是
「A 是 B 的一種」。後果不是分類潔癖——`query/structure.py` 把 `A is_component_of B`
讀成「B 卡在 A 身上」，於是全圖最核心的 `tech:cpo`，那個角度 24 條裡有 5 條
其實是「CPO 有哪些變體」。改判後 25 → 20。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOCAB = json.loads((ROOT / "schema" / "vocab.json").read_text(encoding="utf-8"))


def test_is_variant_of_is_a_registered_relation() -> None:
    assert "is_variant_of" in VOCAB["relation"]


def test_it_never_leaks_into_a_traversal_list() -> None:
    """**這一條是本檔的重點。**

    變體不是替代路線（counter_path）、不是上游（UPSTREAM_RELATIONS）、
    不帶 sole_source 語意、也不是五個結構角度之一。把它加進任何一個，
    就等於把剛移走的那 17 條又搬回去——而那不會讓任何既有測試變紅。
    """
    assert "is_variant_of" not in VOCAB["counter_path_relation"]
    assert "is_variant_of" not in VOCAB["sole_source_beneficiary_end"]

    structure = (ROOT / "query" / "structure.py").read_text(encoding="utf-8")
    bottleneck = (ROOT / "query" / "bottleneck.py").read_text(encoding="utf-8")
    assert "is_variant_of" not in structure, (
        "結構讀圖的五個角度是封閉清單；加第六個要先答出「它在哪個實際案例裡改變過結論」（L17-4）")
    assert "is_variant_of" not in bottleneck, (
        "變體不是上游，也不該參與需求鏈走訪")


def test_the_extraction_prompt_teaches_the_distinction_not_just_the_name() -> None:
    """抽取端只列名字沒有用——會再造出同一批錯邊。要有可操作的判準與反例。"""
    prompt = (ROOT / "prompts" / "extract_system.md").read_text(encoding="utf-8")
    assert "`is_variant_of`" in prompt
    # 可操作的問句（不是形容詞）
    assert "would removing A leave B incomplete" in prompt
    # 正反例都要有——只給正例時，邊界情況仍然會落回 is_component_of
    assert "glass_cpo is_variant_of cpo" in prompt
    assert "cw_dfb_laser is_variant_of external_laser_source" in prompt  # ❌ 反例


def test_the_rejudged_verdicts_use_the_explicit_vocabulary() -> None:
    """判決字彙必須自己說清楚「換型」與「對調」是兩件事。

    舊腳本的 `retype_is_component_of`（只換型）與 `retype_depends_on`（換型又對調）
    **看名字分不出來**——那是 L12 在字彙層的小型版本。新的判決檔用
    `retype:<rel>` 與 `reverse_retype:<rel>`。
    """
    import sys

    sys.path.insert(0, str(ROOT))
    from loader.migrate_relation_rejudge import _ACTIONS, _apply

    assert set(_ACTIONS) == {"reverse", "delete", "retype:", "reverse_retype:"}

    edge = {"id": "e1", "src_id": "a", "dst_id": "b", "relation": "is_component_of"}
    assert _apply(edge, "reverse")["src_id"] == "b"
    assert _apply(edge, "retype:is_variant_of") == {**edge, "relation": "is_variant_of"}
    # 換型與對調是正交的——`reverse_retype:` 兩件事都做，`retype:` 只做一件
    both = _apply(edge, "reverse_retype:develops")
    assert (both["src_id"], both["dst_id"], both["relation"]) == ("b", "a", "develops")
    assert _apply(edge, "delete") is None
