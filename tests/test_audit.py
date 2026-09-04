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
    assert len(checks) == 12
    for check in checks:
        assert check.invariant.startswith("INV-"), check.name
        assert check.owner_phase.startswith("Phase "), check.name
        assert check.description


def test_unimplemented_checks_report_not_implemented_not_pass() -> None:
    """L13：成功與未實作若在同一個訊號上同形，讀的人會以為那項健全性有人在管。"""
    for check in audit.all_checks():
        if check.run is not None:
            continue
        result = check.execute()
        assert result.status is AuditStatus.SKIPPED, check.name
        assert result.summary == "not_implemented"


def test_the_remaining_skip_is_the_one_we_said_it_is() -> None:
    """剩下沒實作的必須**恰好**是 Phase 4 的 `GateDiscrimination`。

    ⚠ 這條擋的是「悄悄把一個實作不出來的 check 改回 `run=None`」——
    那會讓報表變綠，而變綠的原因是檢查被拿掉了。

    ⚠ `PointInTime` 已於 Phase 6 實作（2026-09-04），所以從這個集合移除。
    **移除一個名字必須伴隨它真的被實作**，不是為了讓這條通過而改清單：
    `check_point_in_time` 會實跑一次 as-of 投影驗它沒漏出未來。
    """
    pending = {c.name for c in audit.all_checks() if c.run is None}
    assert pending == {"GateDiscrimination"}


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
