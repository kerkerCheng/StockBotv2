"""Runtime invariant audit 本身的測試。

## 這組測試的重點不是「check 會通過」

一個永遠通過的 audit 與沒有 audit 是同一件事。本組守的是**它失敗的方式**：
讀不到要說讀不到、沒實作要說沒實作、看了 0 筆不准說通過、自己爆掉算 FAIL。

理由是這個 audit 自己也受 INV-5 約束（模組 docstring 已寫）：
一個看了 0 筆資料的檢查，鑑別力與恆滅的閘門一樣是零，
但它會在報表上顯示成一個綠色的 PASS——**那是本 audit 存在要防的形狀本身**。
"""
from __future__ import annotations

import pytest

import audit
from audit import AuditCheck, AuditResult, AuditStatus, fail, ok, skip
from audit.sources import SourceUnavailable


# ---------------------------------------------------------------------------
# 註冊表
# ---------------------------------------------------------------------------

def test_every_check_names_an_invariant_and_an_owner() -> None:
    """沒有 owner 的檢查＝沒有人會實作它（L13 的「管子只接一頭」）。"""
    checks = audit.all_checks()
    assert len(checks) == 13
    for check in checks:
        assert check.invariant.startswith("INV-"), check.name
        assert check.owner_phase.startswith("Phase "), check.name
        assert check.description


def test_unimplemented_checks_report_not_implemented_not_pass() -> None:
    """L13：成功與未實作若在同一個訊號上同形，讀的人會以為那項健全性有人在管。

    ⚠ 這條**自己造一個 `run=None` 的 check**，不從註冊表裡撈。
    2026-09-07 實測：最後一個未實作的 check（`GateDiscrimination`）落地後，原本
    「掃註冊表找 run is None」的寫法就變成空跑——一個永遠不會執行迴圈體的守衛。
    守的是「未實作的路徑不得回 PASS」這條規則本身，而它與註冊表現在有幾個空缺無關。
    """
    from audit import AuditCheck

    placeholder = AuditCheck("Placeholder", "INV-0", (), "Phase X", "尚未實作")
    result = placeholder.execute()
    assert result.status is AuditStatus.SKIPPED
    assert result.summary == "not_implemented"
    assert "Phase X" in str(result.reason)

    for check in audit.all_checks():        # 註冊表裡若還有空缺，同一條規則照樣適用
        if check.run is None:
            assert check.execute().status is AuditStatus.SKIPPED, check.name


def test_every_registered_check_is_actually_implemented() -> None:
    """13/13 都有 `run`。**這條擋的是「悄悄把一個實作不出來的 check 改回 `run=None`」**
    ——那會讓報表變綠，而變綠的原因是檢查被拿掉了。

    歷史：`PointInTime` 於 Phase 6（2026-09-04）實作、`GateDiscrimination` 於
    2026-09-07 實作（Phase 2 Step 4 的 full-chain 驗收）。**移除一個名字必須伴隨它
    真的被實作**，不是為了讓這條通過而改清單。
    """
    pending = {c.name for c in audit.all_checks() if c.run is None}
    assert pending == set()


def test_output_says_skipped_is_not_pass() -> None:
    """輸出必須自己講清楚，不能只靠讀的人知道。"""
    text = audit.render((
        AuditResult("X", AuditStatus.SKIPPED, "not_implemented", reason="r"),))
    assert "SKIPPED 不是 PASS" in text


# ---------------------------------------------------------------------------
# 「看了 0 筆」不得算通過
# ---------------------------------------------------------------------------

def test_passing_with_zero_examined_is_downgraded_to_skipped() -> None:
    """**這是本 audit 最重要的一條自我約束。**

    空跑檢查：把 `ok()` 的 `examined <= 0` 分支拿掉 → 這條會紅。
    """
    result = ok("X", "一切正常", examined=0)
    assert result.status is AuditStatus.SKIPPED
    assert result.summary == "no_data"
    assert "0 筆" in (result.reason or "")


def test_passing_with_data_stays_pass() -> None:
    """反向：真的看了東西就要能通過，否則上一條會讓 audit 永遠無法變綠。"""
    result = ok("X", "一切正常", examined=3)
    assert result.status is AuditStatus.PASS and result.ok
    assert result.examined == 3


def test_render_shows_how_many_rows_each_check_examined() -> None:
    """筆數要**出現在報表上**——L14：防呆要會自己出現，不是要人去查。"""
    text = audit.render((ok("X", "ok", examined=42),))
    assert "[42 筆]" in text
    assert "共檢查 42 筆" in text


# ---------------------------------------------------------------------------
# 「讀不到」不得算通過
# ---------------------------------------------------------------------------

def test_unavailable_source_becomes_skipped_never_pass() -> None:
    """L11-5：「我找不到」與「它不存在」是兩個不同的 claim。"""
    result = skip("X", "Neo4j 連不上")
    assert result.status is AuditStatus.SKIPPED
    assert "Neo4j" in (result.reason or "")


def test_sources_raise_rather_than_return_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """資料源讀不到時**丟例外**，不回空集合。

    空集合會讓呼叫端寫出「檢查了 0 筆，通過」——正是 L13-2 說的
    「成功與失敗在同一個訊號上同形」。
    """
    from audit import sources

    monkeypatch.setattr(sources, "LEADS_DIR", sources.ROOT / "does" / "not" / "exist")
    with pytest.raises(SourceUnavailable, match="不存在"):
        sources.leads()

    # ⚠ `match="不存在"` 不是裝飾。少了它，`_load_json` 改成回 `{}` 之後
    # `leads()` **仍然**會拋 `SourceUnavailable`——只是理由變成「`leads` 不是 dict」，
    # 於是這條測試綠著通過，而它宣稱要守的東西已經壞了（突變 #33 實測）。
    # 型別對了不代表原因對了。
    with pytest.raises(SourceUnavailable, match="不存在"):
        sources._load_json(sources.ROOT / "no" / "such" / "file.json")


def test_check_that_raises_is_a_failure_not_a_skip() -> None:
    """**跑不起來的檢查等於沒有檢查，而它偽裝成有。**

    所以 check 自己爆掉算 FAIL——若算 SKIPPED，一個壞掉的 audit 會安靜地
    退化成「12 項全部沒在管」而報表只多兩行灰字。
    """
    def boom() -> AuditResult:
        raise RuntimeError("裡面炸了")

    check = AuditCheck("X", "INV-1", (), "Phase 3", "d", run=boom)
    result = check.execute()
    assert result.status is AuditStatus.FAIL
    assert result.summary == "check_raised"
    assert "裡面炸了" in result.findings[0]


# ---------------------------------------------------------------------------
# 輸出契約
# ---------------------------------------------------------------------------

def test_findings_are_clipped_but_the_total_survives() -> None:
    """輸出要能讀完，但**不得靜默截斷**——剩幾筆必須寫出來（INV-3）。"""
    from audit.checks import _MAX_FINDINGS, _clip

    clipped = _clip([f"f{i}" for i in range(_MAX_FINDINGS + 5)])
    assert len(clipped) == _MAX_FINDINGS + 1
    assert "另有 5 筆" in clipped[-1]


def test_exit_code_is_nonzero_only_on_failure() -> None:
    """排程要能靠 exit code 知道有沒有事——SKIPPED 不算事。"""
    results = (ok("A", "fine", examined=1), skip("B", "讀不到"))
    assert not any(r.status is AuditStatus.FAIL for r in results)
    assert any(r.status is AuditStatus.FAIL
               for r in (*results, fail("C", "壞了", ("x",), 1)))


def test_run_all_can_select_a_subset() -> None:
    results = audit.run_all(only="GateDiscrimination")
    assert len(results) == 1 and results[0].check == "GateDiscrimination"
    with pytest.raises(SystemExit):
        audit.run_all(only="NoSuchCheck")


# ---------------------------------------------------------------------------
# GateDiscrimination（INV-5／F-26，2026-09-07 實作）
#
# ⚠ 這個 check 自己就是一個 gate，所以它得先過自己的三個測試：它抓得到恆亮、
# 抓得到不會滅、而且**樣本不足時不亂判**。合成 history 直接餵進去（monkeypatch
# 資料源），因為真實 Decision Store 現在剛好三種都沒有——用真實資料寫這三條
# 會得到一個永遠不會響的測試，那正是 F-26 記過的形狀。
# ---------------------------------------------------------------------------

def _history(rows):
    """`rows` 是 `(cohort, [gate...])` 的序列，依序當成時間順序的 assessment。"""
    return [{"assessment_id": f"ca_{i}", "cohort_id": cohort, "created_at": f"2026-01-{i + 1:02d}",
             "lanes": {"coverage": frozenset(gates), "paper": frozenset(), "live": frozenset()}}
            for i, (cohort, gates) in enumerate(rows)]


def _run_gate_check(monkeypatch, history):
    from audit import checks as checks_module

    monkeypatch.setattr(checks_module.sources, "coverage_gate_history", lambda: history)
    return checks_module.check_gate_discrimination()


def test_gate_that_fires_on_everything_is_caught_as_always_on(monkeypatch) -> None:
    """觸發率近 100% ＝零鑑別力：它不是閘門，是行政流程。"""
    rows = [(f"c{i // 3}", ["disproof_missing", "catalyst_missing"] if i % 4 else ["disproof_missing"])
            for i in range(40)]
    result = _run_gate_check(monkeypatch, _history(rows))
    assert result.status is AuditStatus.FAIL
    assert any("disproof_missing" in f and "恆亮" in f for f in result.findings)


def test_gate_that_never_clears_is_caught_as_a_wall(monkeypatch) -> None:
    """曾響過、之後**還有評估機會**卻從未清除 ＝那是牆不是閘門。"""
    rows = []
    for cohort in range(6):                       # 6 個 cohort ≥ GATE_MIN_COHORTS
        rows += [(f"c{cohort}", ["catalyst_missing"])] * 3
    rows += [(f"filler{i}", []) for i in range(20)]   # 稀釋觸發率，免得同時撞到恆亮
    result = _run_gate_check(monkeypatch, _history(rows))
    assert result.status is AuditStatus.FAIL
    assert any("catalyst_missing" in f and "不會滅" in f for f in result.findings)


def test_a_gate_with_too_few_cohorts_is_insufficient_data_not_a_verdict(monkeypatch) -> None:
    """⚠ 這條是本 check 自己的 fail-safe。

    2026-09-07 實測：`identity_unresolved` 的 9 個 cohort 只有 3 個被評估過第二次，
    「0% 清除率」其實是「從來沒有清除的機會」。把沒發生讀成失敗正是 L13-2 的形狀。
    """
    rows: list = [("thin", ["causal_path_missing"])] * 2
    for cohort in range(6):        # 一個樣本夠的 gate，讓 check 有東西可判
        rows += [(f"c{cohort}", ["disproof_missing"]), (f"c{cohort}", [])]
    rows += [(f"filler{i}", []) for i in range(30)]
    result = _run_gate_check(monkeypatch, _history(rows))
    assert result.status is AuditStatus.PASS
    assert any("樣本不足" in f and "causal_path_missing" in f for f in result.findings)
    assert "不當作通過也不當作失敗" in " ".join(result.findings)


def test_a_check_that_cannot_judge_a_single_gate_is_skipped_not_passed(monkeypatch) -> None:
    """模組 docstring ③ 的同一條：**判不動任何一個 gate 的鑑別力檢查，鑑別力自己是零。**

    它必須是 SKIPPED，不得是一個綠色的 PASS——那正是本 audit 存在要防的形狀。
    """
    rows = [("thin", ["causal_path_missing"])] * 2 + [(f"c{i}", []) for i in range(40)]
    result = _run_gate_check(monkeypatch, _history(rows))
    assert result.status is AuditStatus.SKIPPED
    assert "清除率一個都量不到" in str(result.reason)


def test_an_unregistered_blocker_code_is_a_finding(monkeypatch) -> None:
    """L16：有行為後果的字彙必須被強制——沒登記的 code 打錯不會報錯，只會靜默沉底。"""
    rows = [(f"c{i}", ["totally_made_up_blocker"]) for i in range(4)]
    rows += [(f"c{i}", []) for i in range(40)]
    result = _run_gate_check(monkeypatch, _history(rows))
    assert result.status is AuditStatus.FAIL
    assert any("totally_made_up_blocker" in f and "decision_blockers.json" in f
               for f in result.findings)


def test_gate_check_skips_when_there_is_no_assessment_history(monkeypatch) -> None:
    """讀不到 ≠ 沒問題（sources 層的唯一轉換路徑）。"""
    from audit import checks as checks_module
    from audit.sources import SourceUnavailable

    def boom():
        raise SourceUnavailable("coverage_assessments 沒有任何列——gate 從未被評估過")

    monkeypatch.setattr(checks_module.sources, "coverage_gate_history", boom)
    result = checks_module.check_gate_discrimination()
    assert result.status is AuditStatus.SKIPPED and "從未被評估" in str(result.reason)
