from pathlib import Path


SKILL = Path(__file__).resolve().parent.parent / "skills" / "signal-triage" / "SKILL.md"


def test_pass_runs_pq1_and_only_prepared_action_enters_pq2() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "PASS 後可自動研究" in text
    assert "prepared Research Action 後，才以完整核准包進 pq2" in text
    assert "使用者 `go` 的語意是核准" in text
    assert "不必在研究前先回答一次" in text


def test_scoped_campaign_relaxes_only_tracked_relevance() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "使用者指定的新領域探索 campaign" in text
    assert "只放寬關聯性" in text
    assert "可引用性不放寬" in text
    assert "candidate events" in text
    assert "raw posts 的比例沒有判讀價值" in text
    assert "50–70%" in text
