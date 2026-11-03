"""`ConfigBoundaries`（盲點修法 §1 第 5 條）：ARCHITECTURE §8.2 純讀 config 的四條邊界。

守的是：真實 config 四條都過；每一條各自破了都 FAIL、而且 finding 點名是哪一條；讀不到不算通過；
beta 的訊號鍵整鍵比對（`policy_version` 含 rsi 不得誤報）。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from audit import AuditStatus
from audit import checks

REAL_CONFIG = Path(__file__).resolve().parent.parent / "config"
FILES = ("target_allocation.json", "investment_policy.json", "beta_policy.json", "standing_authorization.json")


@pytest.fixture
def config_root(tmp_path, monkeypatch) -> Path:
    (tmp_path / "config").mkdir()
    for name in FILES:
        shutil.copy(REAL_CONFIG / name, tmp_path / "config" / name)
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    return tmp_path / "config"


def _edit(config: Path, name: str, change) -> None:
    payload = json.loads((config / name).read_text(encoding="utf-8"))
    change(payload)
    (config / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_the_real_config_passes_all_four() -> None:
    result = checks.check_config_boundaries()
    assert result.status is AuditStatus.PASS, result.findings
    assert result.examined == 4


def test_the_copied_config_passes_too(config_root) -> None:
    assert checks.check_config_boundaries().status is AuditStatus.PASS


@pytest.mark.parametrize("name, change, needle", [
    ("target_allocation.json", lambda p: p["sleeves"]["alpha"].update(observed_only=False), "observed_only"),
    ("target_allocation.json", lambda p: p["sleeves"]["alpha"].update(target=0.1), "只觀測的格子不得有目標"),
    ("investment_policy.json", lambda p: p.update(single_position_nav_cap=0.08), "0.05"),
    ("investment_policy.json", lambda p: p["probe_lane"].update(axis_ceilings={"unknown": 0.0}), "axis_ceilings"),
    ("investment_policy.json", lambda p: p["probe_lane"].update(probe_book_nav_cap=0.02), "probe_book_nav_cap"),
    # 不在 U7 清單裡的新名字：尺寸語意換個名字回來也要擋
    ("investment_policy.json", lambda p: p["probe_lane"].update(tranche_nav_cap=0.01), "tranche_nav_cap"),
    ("investment_policy.json", lambda p: p["probe_lane"].update(evidence_ceiling={"x": 1}), "evidence_ceiling"),
    ("beta_policy.json", lambda p: p.update(signal={"rsi": 30}), "signal"),
    ("beta_policy.json", lambda p: p["risk"].update(pace=1), "pace"),          # 任何深度都算
    ("standing_authorization.json", lambda p: (p["never"].pop("ra_admission"), p["authorized"].update(ra_admission={})),
     "ra_admission"),
    ("standing_authorization.json", lambda p: p["never"].pop("watch_decision"), "loader 拒絕載入"),
])
def test_each_boundary_fails_on_its_own(config_root, name, change, needle) -> None:
    _edit(config_root, name, change)
    result = checks.check_config_boundaries()
    assert result.status is AuditStatus.FAIL
    assert len(result.findings) == 1 and needle in result.findings[0] and name in result.findings[0]


def test_version_keys_are_not_mistaken_for_rsi(config_root) -> None:
    """整鍵比對：`policy_version`／`schema_version` 含 rsi，子字串比對就會誤報（L16：不用會誤報的 linter）。"""
    _edit(config_root, "beta_policy.json", lambda p: p.update(tier_version="x", pacer_note="y"))
    assert checks.check_config_boundaries().status is AuditStatus.PASS


@pytest.mark.parametrize("name", FILES)
def test_an_unreadable_file_is_skipped_not_passed(config_root, name) -> None:
    (config_root / name).unlink()
    result = checks.check_config_boundaries()
    assert result.status is AuditStatus.SKIPPED and name in str(result.reason)


def test_a_violation_still_fails_when_another_file_is_unreadable(config_root) -> None:
    (config_root / "beta_policy.json").unlink()
    _edit(config_root, "investment_policy.json", lambda p: p.update(single_position_nav_cap=0.1))
    result = checks.check_config_boundaries()
    assert result.status is AuditStatus.FAIL
    assert any("未讀到" in f and "beta_policy.json" in f for f in result.findings)
