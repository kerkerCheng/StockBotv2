"""同一年度有兩筆以上生效的基期觀測時，**不得靜默選第一筆**（2026-09-20）。

## 事發

Phase 7 的「橋契約舊帳」之一（2026-09-13 記的是「8 檔 14 組」）。2026-09-20 重量，
**仍然是 8 檔**，而且逐筆看過之後發現它是**兩種形狀被壓在一起**（L12）：

| 形狀 | 檔數 | 正確處理 |
|---|---|---|
| 同幣別的「骨架 vs 補完」 | 6 | 取比較完整的那一筆 |
| 同幣別的「初步 vs 正式財報」 | 1（000660.KS） | 同上 |
| **異幣別並存** | **1（TSM）** | **fail closed——沒有規則選得對** |

TSM 的兩筆是 USD 121,423,000,000 與 TWD 3,809,054,000,000，**差 31 倍**。
AGENTS.md 逐字：「報價單位 ≠ 結算幣別……價格會差 100 倍」。選錯不是誤差，是量級錯誤。

而 08:26 那批骨架與 10:xx 那批補完是同一天寫的，**後寫那筆沒有設 `supersedes_id`**
——根因兩種形狀相同，但**修法相反**：所以規則必須分開，不能取兩者的下限。

⚠ 這裡只負責「不要靜默挑一個」。清資料要 append correction record 到 append-only
ledger ＝ A2 authority，得人核准（L10：Engine C ledger 只能 append，兩筆都留著）。
"""
from __future__ import annotations

import json

import pytest

from alpha.contracts import Ticker
from alpha.providers.fundamentals import EngineCFundamentalsProvider


class _FakeProvider(EngineCFundamentalsProvider):
    """只換掉 `_ledger_rows`，其餘走真正的解析路徑。"""

    def __init__(self, rows):
        self._rows = rows

    def _ledger_rows(self, ticker, field_name, as_of):  # noqa: D102
        return list(self._rows)


def _row(obs_id: str, *, currency: str, revenue: float, filed: str | None = None,
         gaap: dict | None = None, supersedes: str | None = None) -> dict:
    payload = {"fiscal_year_end": "2025-12-31", "currency": currency, "revenue": revenue}
    if filed:
        payload["source_filed_at"] = filed
    if gaap:
        payload["gaap"] = gaap
    return {"observation_id": obs_id, "value": json.dumps(payload),
            "as_of": "2025-12-31", "recorded_at": "2026-09-10T08:26:00",
            "supersedes_id": supersedes, "source": "test", "evidence_ref": None}


def test_a_single_live_row_is_unchanged() -> None:
    """一筆的情況**行為一個位元都不該變**（L11-6）。"""
    prov = _FakeProvider([_row("mo_a", currency="USD", revenue=100.0)])
    actuals, why = prov.fiscal_year_results(Ticker("TEST"))
    assert why is None and actuals is not None
    assert actuals.revenue == 100.0
    assert actuals.coverage_note is None      # 沒有衝突就不該多一句話


def test_conflicting_currencies_fail_closed_instead_of_picking_one() -> None:
    """異幣別並存＝**沒有任何自動規則選得對**。31 倍的差距不是誤差。"""
    prov = _FakeProvider([
        _row("mo_usd", currency="USD", revenue=121_423_000_000.0, filed="2026-04-16"),
        _row("mo_twd", currency="TWD", revenue=3_809_054_000_000.0),
    ])
    actuals, why = prov.fiscal_year_results(Ticker("TSM"))
    assert actuals is None, "幣別衝突時必須 fail closed，不得挑一個"
    assert "幣別不一致" in (why or "")
    assert "correction record" in (why or ""), "要說出怎麼修，不然它只是一個壞掉的格子"


def test_same_currency_takes_the_most_complete_row_by_rule_not_by_luck() -> None:
    """同幣別時取**欄位最完整**的那一筆——用明確規則取代「排序碰巧」。

    實測那 6 檔今天取第一筆剛好都對，但那是 ledger 回傳順序的運氣，不是保證。
    """
    skeleton = _row("mo_skeleton", currency="USD", revenue=88_326_000.0)
    complete = _row("mo_complete", currency="USD", revenue=88_326_000.0,
                    filed="2026-02-20", gaap={"diluted_eps": -0.49})
    for order in ([skeleton, complete], [complete, skeleton]):
        actuals, why = _FakeProvider(order).fiscal_year_results(Ticker("AXTI"))
        assert why is None and actuals is not None
        assert actuals.observation_id == "mo_complete", "順序不該改變結果"
        assert actuals.gaap.get("diluted_eps") == -0.49


def test_the_conflict_is_stated_not_swallowed() -> None:
    """選了一筆之後**要說出來**——靜默選取正是這個舊帳當初沒被發現的原因（INV-3）。"""
    prov = _FakeProvider([
        _row("mo_a", currency="USD", revenue=100.0, gaap={"diluted_eps": 1.0}),
        _row("mo_b", currency="USD", revenue=100.0),
    ])
    actuals, _why = prov.fiscal_year_results(Ticker("TEST"))
    assert actuals is not None
    note = actuals.coverage_note or ""
    assert "2 筆生效觀測" in note
    assert "supersedes_id" in note, "要指出根因，否則下次只會再修一次排序"


def test_an_existing_coverage_note_is_not_overwritten() -> None:
    """既有的 `coverage_note` 是作者寫的，**不得被衝突註記蓋掉**（L17-3 第②問）。"""
    payload = {"fiscal_year_end": "2025-12-31", "currency": "USD", "revenue": 100.0,
               "coverage_note": "作者原註：非 GAAP 只調整 SBC", "gaap": {"diluted_eps": 1.0}}
    rows = [{"observation_id": "mo_a", "value": json.dumps(payload), "as_of": "2025-12-31",
             "recorded_at": "2026-09-10T10:00:00", "supersedes_id": None,
             "source": "test", "evidence_ref": None},
            _row("mo_b", currency="USD", revenue=100.0)]
    actuals, _why = _FakeProvider(rows).fiscal_year_results(Ticker("TEST"))
    assert actuals is not None
    assert "作者原註" in (actuals.coverage_note or "")
    assert "2 筆生效觀測" in (actuals.coverage_note or "")


def test_superseded_rows_still_drop_out_first() -> None:
    """已經正確設了 `supersedes_id` 的就不該進入衝突判斷——那是這個機制本來就對的路。"""
    prov = _FakeProvider([
        _row("mo_new", currency="USD", revenue=200.0, supersedes="mo_old"),
        _row("mo_old", currency="TWD", revenue=6_000.0),
    ])
    actuals, why = prov.fiscal_year_results(Ticker("TEST"))
    assert why is None and actuals is not None, "正確 supersede 之後不該再報幣別衝突"
    assert actuals.revenue == 200.0
    assert actuals.coverage_note is None
