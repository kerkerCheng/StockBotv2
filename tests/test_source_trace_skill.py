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


def test_obtaining_original_tier_three_report_does_not_upgrade_evidence() -> None:
    text = (ROOT / "skills" / "source-trace" / "SKILL.md").read_text(encoding="utf-8")

    assert "tier 3 仍維持 tier 3" in text
    assert "不因「找到原報告」升級" in text
