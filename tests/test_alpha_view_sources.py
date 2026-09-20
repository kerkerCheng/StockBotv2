"""估值方法的選取（`_select_method` / `_has_method_records`）。

method 是**判斷不是預設值**：ledger 裡寫了哪一筆估值假設，就決定走哪一條估值路徑。
兩種並存時直接拒絕並要求撤回一條，不由程式代選。
"""
from __future__ import annotations

def test_retracting_a_method_actually_removes_it_from_method_selection() -> None:
    """⚠⚠ **撤回必須讓 `_select_method` 看得見**（2026-09-20 修的 bug）。

    撤回的寫法是 append 一筆 `retracted=True` 的新紀錄去 supersede 舊筆
    （append-only ledger，舊筆原地不動、它自己的 `retracted` 永遠是 `False`）。
    原本的 `_has_method_records` 只看每筆自己的 `retracted`——**等於完全看不到撤回**。

    實測（pq2 [637] 執行當天）：AXTI 依核准 append 了 `target_ev_to_sales` 並
    `--retract` 了 `target_pe`，而 `_select_method` 仍回報「兩種 method 並存」並拒絕選。
    這條路先前沒被走過：9 檔 ev_to_sales 都是一開始就只有那一種，
    AXTI 是第一檔真的做「本益比法 → EV／Sales」切換的。
    """
    from briefing.alpha_view.sources import _has_method_records

    class _R:
        def __init__(self, aid, method, retracted=False, supersedes=None):
            self.assumption_id, self.method = aid, method
            self.retracted, self.supersedes_id = retracted, supersedes

    # 舊筆自己的 retracted 是 False，被一筆 retracted=True 的新紀錄 supersede。
    records = [
        _R("va_old", "forward_earnings_multiple"),
        _R("va_retract", "forward_earnings_multiple", retracted=True, supersedes="va_old"),
        _R("va_new", "ev_to_sales"),
    ]
    assert not _has_method_records(records, "forward_earnings_multiple"), \
        "被 supersede 的那筆不算生效——否則撤回等於沒做"
    assert _has_method_records(records, "ev_to_sales")


def test_a_live_method_is_still_detected() -> None:
    """**這個機制必須會亮**（L14-4）：沒被撤回的照舊算數，不能修成恆滅。"""
    from briefing.alpha_view.sources import _has_method_records

    class _R:
        def __init__(self, aid, method):
            self.assumption_id, self.method = aid, method
            self.retracted, self.supersedes_id = False, None

    assert _has_method_records([_R("va_a", "forward_earnings_multiple")],
                               "forward_earnings_multiple")
