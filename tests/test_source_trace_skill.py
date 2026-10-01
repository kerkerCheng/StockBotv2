from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_access_recovery_never_bypasses_access_controls() -> None:
    text = (ROOT / "skills" / "source-trace" / "SKILL.md").read_text(encoding="utf-8")

    assert "公開內容的 access recovery 梯子" in text
    assert "txtify.it" in text
    assert "原本即公開" in text
    assert "遇到 paywall、login、CAPTCHA" in text
    assert "不得使用外洩鏡像" in text


def test_access_helpers_do_not_create_independent_evidence() -> None:
    text = (ROOT / "skills" / "source-trace" / "SKILL.md").read_text(encoding="utf-8")

    assert "same_origin" in text
    assert "代理輸出本身不是新的 origin" in text
    assert "搜尋摘要只供 discovery" in text
    assert "origin_linkage" in text


def test_layer_input_section_comes_after_the_transcript_rule_and_keeps_its_order() -> None:
    """Phase 4 Step 4.5c：層文件那一節**不改 claim 路由頂階**——「直接去 transcript」對 claim 仍成立、仍在它之前；
    節內四級順序固定（客戶端 → 產業報告 → 規格書／teardown → 供應商自己）。"""
    text = (ROOT / "skills" / "source-trace" / "SKILL.md").read_text(encoding="utf-8")
    transcript = text.index("直接去 transcript")
    layer = text.index("### 2b. 輸入是層／節點時")
    assert transcript < layer < text.index("### 3. access boundary")
    section = text[layer:text.index("### 3. access boundary")]
    order = [section.index(s) for s in ("客戶端申報的供應商段", "**產業報告**", "**規格書／teardown**", "**供應商自己的文件**")]
    assert order == sorted(order)
    assert "layer_enumerations" in section and "awaiting_named_disclosure" in section


def test_obtaining_original_tier_three_report_does_not_upgrade_evidence() -> None:
    text = (ROOT / "skills" / "source-trace" / "SKILL.md").read_text(encoding="utf-8")

    assert "tier 3 仍維持 tier 3" in text
    assert "不因「找到原報告」升級" in text
