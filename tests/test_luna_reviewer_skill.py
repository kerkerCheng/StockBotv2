"""Luna reviewer 必須明確 opt-in，且只包裝既有唯讀 custom agent。"""

from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "luna-reviewer" / "SKILL.md"
OPENAI_YAML = ROOT / "skills" / "luna-reviewer" / "agents" / "openai.yaml"
AGENT = ROOT / ".codex" / "agents" / "luna-operator.toml"


def test_luna_reviewer_is_explicit_and_non_sticky() -> None:
    text = SKILL.read_text(encoding="utf-8")
    for trigger in ("$luna-reviewer", "Luna reviewer：", "Luna reviewer:"):
        assert trigger in text
    assert "每次明確觸發只授權該次指令" in text
    assert "完成後自動退出" in text
    assert "沒有觸發前綴時" in text
    assert "不自行派 Luna" in text


def test_implicit_invocation_is_disabled() -> None:
    text = OPENAI_YAML.read_text(encoding="utf-8")
    assert 'default_prompt: "使用 $luna-reviewer ' in text
    assert "allow_implicit_invocation: false" in text


def test_skill_wraps_the_existing_read_only_luna_agent() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert ".codex/agents/luna-operator.toml" in text
    assert "不建立第二個 agent" in text
    assert 'agent_type="luna_operator"' in text
    assert "主代理是唯一 writer" in text

    config = tomllib.loads(AGENT.read_text(encoding="utf-8"))
    assert config["model"] == "gpt-5.6-luna"
    assert config["model_reasoning_effort"] == "max"
    assert config["sandbox_mode"] == "read-only"


def test_luna_unavailable_does_not_silently_use_an_expensive_agent() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "不得靜默改派較昂貴的其他 subagent" in text
