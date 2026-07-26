from pathlib import Path


SKILL = Path(__file__).resolve().parent.parent / "skills" / "lead-intake" / "SKILL.md"


def test_prepare_is_the_automatic_boundary_and_apply_needs_pq2_approval() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "Step 5 — 驗證並準備 Research Action" in text
    assert "自動化終點是 `prepare_research_action`" in text
    assert "只有 Research Action 進入廣義 pq2" in text
    assert "同一輪不得 prepare 後自行 apply" in text
    assert "自動寫入圖" not in text
