"""overlay 的 `scope` 未命中 base 時，寫入端拒收（2026-09-19 使用者核准方案 (a)）。

## 缺陷（2026-09-19 實測，寫 LITE 賭注時親自踩到）

overlay 的覆蓋鍵是 `(driver, scope)`。`select_scenario_assumptions` 做的是
`merged = {base keys}; merged.update({variant keys})`——**variant 的 key 不在 base 裡時，
它不是覆蓋，是被當成第三條假設一起生效**。LITE 的 base 營益率 scope 是
`guided_q1_margin_held_flat`，overlay 寫成 `total`，於是 29.8＋10.2＋10.7 ＝ **50.7%**，
產出假的 variant EPS 29.71／目標價 1,343.12／隱含報酬 **+50.3%**（真值 23.86／1,078.72／+20.7%）。

## 為什麼測試抓不到（這份測試存在的理由）

**錯誤的方向永遠是「對自己有利」**——多疊一個正的 delta。而且 `alpha-card` 每一格照常印、
`audit invariants` 照常 PASS、既有 43 條賭注測試照常綠：**測試問的是「程式有沒有照標籤做」，
不是「標籤對不對」**（L18-1）。當時唯一的偵測手段是寫入前先手算一次三情境，
而那不是可例行化的紀律（L18-4：深挖若需要繞過自己的工具，它就不會例行發生）。

## 為什麼是寫入端拒收，不是印一行提醒

L18-3：**根解是拿掉資訊落差，不是在落差上面加一層提醒。** 打錯 scope 與「真的要引入
base 沒有的新切分」在資料上**長得一模一樣**，所以唯一能分開兩者的時點是寫的人還在的時候。

## L11-6「如果這個修法是錯的，最先壞掉的是哪一筆現有資料？」

寫這道閘門前先量過全部 62 檔 ledger：有 overlay 的只有 3 檔、11 條紀錄，其中 **7 條命中 base、
4 條未命中且全部是 LITE 那個已知 bug 的 `scope='total'`——合法引入新 scope 的有 0 條**。
所以這道閘門在現有資料上只會擋下它該擋的那些。第二個會壞的是**撤回路徑**（見下），已明文放行。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from alpha.errors import ContractViolation
from alpha.fundamental.assumptions import live_base_keys, parse_assumption_record
from alpha.fundamental.contracts import FiscalPeriod
from alpha.providers.assumptions import append_assumption_record, read_assumption_records
from tests.test_fundamental_model import TARGET, _assumption

UTC = timezone.utc
OTHER = FiscalPeriod(end=date(TARGET.end.year + 1, TARGET.end.month, TARGET.end.day),
                     kind=TARGET.kind)


def _write(tmp_path, record, **kw):
    return append_assumption_record(dict(record), directory=tmp_path, **kw)


def _base(scope: str = "mix_and_utilization", value: float = 0.025, **kw):
    return _assumption("operating_margin_delta", scope, value, **kw)


def _overlay(scope: str, *, scenario: str = "variant", value: float = 0.05, **kw):
    return _assumption("operating_margin_delta", scope, value,
                       created="2026-09-06T08:00:00+00:00", scenario=scenario, **kw)


def _seed_base(tmp_path, scope: str = "mix_and_utilization"):
    record = _base(scope)
    _write(tmp_path, _raw(record))
    return record


def _raw(parsed):
    """把 parse 過的紀錄還原成可 append 的 dict（測試只需要欄位齊全）。"""
    from alpha.fundamental.assumptions import assumption_record
    return assumption_record(
        company_id=parsed.company_id, ticker=parsed.ticker, period_end=parsed.period.end,
        driver=parsed.driver, scope=parsed.scope, value=parsed.value, basis=parsed.basis,
        rationale=parsed.rationale, evidence_refs=list(parsed.evidence_refs),
        accounting_basis=parsed.accounting_basis, supersedes_id=parsed.supersedes_id,
        retracted=parsed.retracted, created_at=parsed.created_at, author=parsed.author,
        derivation=parsed.derivation, scenario=parsed.scenario,
        legacy_roles=not parsed.evidence_refs or parsed.retracted or None,
    )


# ---------------------------------------------------------------------------
# 1. 閘門本身：擋該擋的，放行該放的
# ---------------------------------------------------------------------------

def test_overlay_with_matching_scope_is_accepted(tmp_path) -> None:
    """命中 base 的 overlay 照常寫得進去——這是 11 條現有紀錄裡的 7 條。"""
    _seed_base(tmp_path)
    _write(tmp_path, _raw(_overlay("mix_and_utilization")))
    records, errors = read_assumption_records("COHR", directory=tmp_path)
    assert errors == []
    assert {r.scenario for r in records} == {"base", "variant"}


@pytest.mark.parametrize("scenario", ["variant", "downside"])
def test_overlay_with_unmatched_scope_is_rejected(tmp_path, scenario: str) -> None:
    """未命中 base 的 overlay 被拒——**兩個 overlay scenario 一視同仁**。

    LITE 那次真正寫進去的就是這一形：base 是 `guided_q1_margin_held_flat`，overlay 寫 `total`。
    """
    _seed_base(tmp_path, "guided_q1_margin_held_flat")
    with pytest.raises(ContractViolation) as exc:
        _write(tmp_path, _raw(_overlay("total", scenario=scenario,
                                       value=0.05 if scenario == "variant" else -0.05)))
    message = str(exc.value)
    # 錯誤訊息必須講出**機制**與**可選值**，否則寫的人只會換個字再試一次。
    assert "同時生效" in message
    assert "guided_q1_margin_held_flat" in message, "必須列出該 driver 在 base 的可選 scope"
    assert "allow_new_scope" in message


def test_rejection_happens_before_any_write(tmp_path) -> None:
    """拒收必須發生在 append 之前——半寫進去的 ledger 比擋不住更糟（append-only 救不回）。"""
    _seed_base(tmp_path, "guided_q1_margin_held_flat")
    before = read_assumption_records("COHR", directory=tmp_path)[0]
    with pytest.raises(ContractViolation):
        _write(tmp_path, _raw(_overlay("total")))
    assert read_assumption_records("COHR", directory=tmp_path)[0] == before


# ---------------------------------------------------------------------------
# 2. L11-6：最先壞掉的那兩筆
# ---------------------------------------------------------------------------

def test_retracting_a_bad_overlay_is_never_blocked(tmp_path) -> None:
    """⚠ **這是本修法最先會壞掉的東西。**

    撤回紀錄沿用被撤回那筆的 `driver`／`scope`，所以一條 scope 打錯的 overlay，它的撤回紀錄
    也一定未命中 base。若閘門連撤回一起擋，結果是**寫錯的 overlay 永遠撤不回**——正是
    2026-09-19 當天才修好的那個 bug，不能由這道閘門把它裝回去。
    """
    _seed_base(tmp_path, "guided_q1_margin_held_flat")
    bad = _overlay("total")
    _write(tmp_path, _raw(bad), allow_new_scope=True)      # 模擬閘門存在之前寫進去的舊資料
    retraction = _assumption(
        "operating_margin_delta", "total", bad.value, created="2026-09-07T08:00:00+00:00",
        scenario="variant", supersedes_id=bad.assumption_id, retracted=True)
    _write(tmp_path, _raw(retraction))                     # 不得丟 ContractViolation
    records, _ = read_assumption_records("COHR", directory=tmp_path)
    assert [r.retracted for r in records if r.scenario == "variant"] == [False, True]


def test_new_scope_is_possible_but_must_be_explicit(tmp_path) -> None:
    """合法的新切分沒有被封死，只是變成 opt-in——現有資料裡這種紀錄有 0 條。"""
    _seed_base(tmp_path, "guided_q1_margin_held_flat")
    _write(tmp_path, _raw(_overlay("total")), allow_new_scope=True)
    assert len(read_assumption_records("COHR", directory=tmp_path)[0]) == 2


# ---------------------------------------------------------------------------
# 3. `live_base_keys` 的語意：與 select_assumptions 的 supersede／retract 一致
# ---------------------------------------------------------------------------

def test_live_base_keys_ignores_retracted_and_other_periods() -> None:
    """撤回不讓舊值復活；別的期間不算數（兩者都會讓閘門放行不該放行的 scope）。"""
    live = _base("mix_and_utilization")
    dropped = _assumption("operating_margin_delta", "cycle_pricing", 0.01,
                          created="2026-09-05T09:00:00+00:00")
    retraction = _assumption("operating_margin_delta", "cycle_pricing", 0.01,
                             created="2026-09-05T10:00:00+00:00",
                             supersedes_id=dropped.assumption_id, retracted=True)
    other_period = _assumption("revenue_growth", "Industrial", 0.1, period_end=OTHER.end)
    keys = live_base_keys([live, dropped, retraction, other_period], period=TARGET)
    assert set(keys) == {("operating_margin_delta", "mix_and_utilization")}


def test_live_base_keys_excludes_overlay_records() -> None:
    """overlay 不得替自己背書：一條 variant 不能讓下一條 variant 的 scope 變成『命中 base』。"""
    keys = live_base_keys([_base("mix_and_utilization"), _overlay("total")], period=TARGET)
    assert ("operating_margin_delta", "total") not in keys
