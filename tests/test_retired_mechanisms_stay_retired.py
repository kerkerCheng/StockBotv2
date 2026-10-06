"""退役機制殭屍 grep 的三個驗收數字常駐化（2026-10-06 使用者指示；Phase 7 failure log #30）。

事發：7.0f（`docs/OPERATIONS.md` 把 CLI 的外部工具設定寫成 I 組的 token）與多主題等權組 S1（`alpha/theme_cohort.py` 的 L12 註解用了 B 組的舊詞）
兩週內各帶進一筆回流，
ROADMAP Phase 0 退役清單原寫「不做成常駐 linter、每季跑一次」——季檢看不到。改成每次 pytest 跑；仍不進 daily、不進 hook。

誤報的處理方式不變（L16-4 的顧慮由 keep-list 的合法類別承擔）：改字，或在 `scripts/retired_mechanism_grep.py` 的 keep-list
列那一筆並寫出類別與理由。本測試只重現腳本的 verdict，不另寫一份 regex（L16：同一個分類只住一處）。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "retired_mechanism_grep.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("retired_mechanism_grep", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_retired_mechanisms_have_not_crept_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """三個數字都要是 0：未列 keep-list 的命中、腐壞條目、理由類別不合法。"""
    monkeypatch.chdir(ROOT)  # 腳本以 repo 根目錄為相對路徑走訪（含 `git ls-files`）
    mod = _load_script()
    idx = mod.build_index()
    mcp_hits = mod._mcp_hits()
    unlisted, stale, bad = mod.verdict_data(idx, mcp_hits)
    assert not unlisted, (
        "退役機制回流（命中但不在 keep-list）："
        + "；".join(f"{letter} {area} {path} ({n})" for letter, area, path, n in sorted(unlisted))
        + "——改字，或列 keep-list 並寫出類別與理由（不是放寬 regex）"
    )
    assert not stale, f"keep-list 腐壞條目（已列但不再命中）：{stale}"
    assert not bad, f"keep-list 理由類別不合法：{bad}"


def test_importing_the_script_does_not_run_the_scan(capsys: pytest.CaptureFixture[str]) -> None:
    """腳本必須能被 import 而不自己跑起來印輸出——否則每個 import 都是一次全 repo 掃描。"""
    _load_script()
    assert capsys.readouterr().out == ""
