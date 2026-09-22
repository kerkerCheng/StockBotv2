from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS = (
    ROOT / "skills" / "lead-intake" / "SKILL.md",
    ROOT / "skills" / "investment-research" / "SKILL.md",
)


def test_research_skills_no_longer_call_the_retired_engine_d_workflow() -> None:
    """兩個研究 skill **不得再有** Engine D workflow 的可執行呼叫。

    ⚠ 2026-09-22（Phase 0 Step 0a.3）：原本這條測試要求兩檔都**必須**出現
    `evaluate-signal`／重新評估／`today`／`card` 四支命令——它守的是「兩個 skill 走同一條
    operational workflow，不各自造一份」。**那條 workflow 整組退役**（ROADMAP Phase 0／G12），
    所以斷言翻面：問的是**可執行的命令行**（`python -m` 開頭），不是整份檔案有沒有出現那些字
    ——退役註記本身寫得出它們的名字，用字串比對會讓退役與沒退役同形（L13）。
    """
    for path in SKILLS:
        text = path.read_text(encoding="utf-8")
        runnable = [line.strip() for line in text.splitlines()
                    if line.lstrip().startswith(("python -m", "python ", "& '.venv"))]
        joined = "\n".join(runnable)
        for retired in ("evaluate-signal", "decision_lab reassess", "decision_lab today",
                        "decision_lab card", "record-choice", "record-fill"):
            assert retired not in joined, f"{path.name} 仍有可執行的 {retired}"
        assert "context_digest" not in joined
        # 活的那半：兩檔都要指得出「今天有什麼」的新入口（零 LLM 心跳）。
        assert "crons.heartbeat" in text, f"{path.name} 沒有指出心跳"


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
    # ⚠ 2026-09-22（Step 0a.3）：原句「任何一步都不得由 recommendation 推定」住在
    # `record-choice`／`record-fill` 那一段，整段隨 Engine D 退役。**判準沒有退役**——
    # 它現在的主詞是成交路徑：系統不下單、不給尺寸，live 永遠人工（AGENTS 五條 authority）。
    assert "不給尺寸" in combined
    assert "永遠人工" in combined


def test_only_canonical_skill_files_were_hand_edited_before_sync() -> None:
    for path in SKILLS:
        assert path.parts[-3] == "skills"
        assert path.name == "SKILL.md"
