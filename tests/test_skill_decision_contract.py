from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS = (
    ROOT / "skills" / "lead-intake" / "SKILL.md",
    ROOT / "skills" / "investment-research" / "SKILL.md",
)


def test_research_skills_share_the_same_operational_commands() -> None:
    texts = [path.read_text(encoding="utf-8") for path in SKILLS]
    for text in texts:
        for command in (
            "evaluate-signal",
            "reassess",
            "today",
            "card",
        ):
            assert command in text
        assert "context_digest" not in "\n".join(
            line for line in text.splitlines() if line.lstrip().startswith("python -m")
        )


def test_skills_do_not_duplicate_probe_policy_or_imply_automatic_live_execution() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in SKILLS)

    for forbidden in (
        "0.5%",
        "axis_ceilings",
        "probe_book_nav_cap",
        "single_probe_nav_cap =",
        "live_adv_fraction_cap =",
        "paper_nav =",
    ):
        assert forbidden not in combined
    assert "不連 broker" in combined
    assert "不得由 recommendation 推定" in combined


def test_only_canonical_skill_files_were_hand_edited_before_sync() -> None:
    for path in SKILLS:
        assert path.parts[-3] == "skills"
        assert path.name == "SKILL.md"
