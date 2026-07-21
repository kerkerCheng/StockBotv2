from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_skills_call_decision_lab_without_copying_policy_numbers_or_formulas() -> None:
    lead = (ROOT / "skills/lead-intake/SKILL.md").read_text(encoding="utf-8")
    research = (ROOT / "skills/investment-research/SKILL.md").read_text(encoding="utf-8")
    decision_sections = "\n".join(
        line for line in (lead + research).splitlines() if "Decision Lab" in line or "decision_lab" in line
    )

    assert "decision_lab" in decision_sections
    assert "Action Card" in decision_sections
    assert "0.5%" not in decision_sections
    assert "axis_ceilings" not in decision_sections
    assert "probe_book_nav_cap" not in decision_sections
