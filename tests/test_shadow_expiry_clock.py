"""入圖後自動追蹤 cohort 的到期時鐘，必須與 probe 複查節奏分開（L12）。

事發（2026-08-31）：`ensure_shadow_for_company` 不帶 expiry，落到 `_default_expiry` 的
`probe_lane.review_hours`＝72 小時。於是每家新入圖公司三天後就拿到一個**沒有催化劑、
沒有證偽條件**的到期提醒。L7 說「欄位有填但沒有後續流程等於警報永遠不會響」，這是它的
反面且更吵：警報會響，但響了不知道要看什麼。實測 22 個追蹤標的有 6 個如此
（Schaeffler、上詮、MP、台積電、奇景、Lynas），全庫 30 個 cohort 有 24 個由這條路徑建立。

驗收條件寫成「兩個時鐘互不影響」，不是「函式回得出一個日期」——後者在修好之前就已經成立。
"""

from __future__ import annotations

import json

from decision_lab import workflow
from risk.policy import POLICY_PATH, load_policy

AT = "2026-08-31T00:00:00+00:00"


def test_shadow_and_probe_clocks_are_driven_by_different_policy_keys() -> None:
    policy = {
        "probe_lane": {"review_hours": 72},
        "shadow_lane": {"tracking_expiry_days": 90},
    }
    assert workflow._default_expiry(AT, policy).startswith("2026-09-03")
    assert workflow._shadow_expiry(AT, policy).startswith("2026-11-29")

    # 分開之後必須是真的分開：動 probe 的複查節奏不得影響 shadow 的追蹤期限。
    faster_probe = {
        "probe_lane": {"review_hours": 1},
        "shadow_lane": {"tracking_expiry_days": 90},
    }
    assert workflow._shadow_expiry(AT, faster_probe) == workflow._shadow_expiry(AT, policy)
    assert workflow._default_expiry(AT, faster_probe) != workflow._default_expiry(AT, policy)


def test_real_policy_declares_both_clocks_and_shadow_is_the_longer_one() -> None:
    policy = load_policy()
    review_hours = float(policy["probe_lane"]["review_hours"])
    tracking_days = float(policy["shadow_lane"]["tracking_expiry_days"])
    assert tracking_days * 24 > review_hours, "追蹤期限短於複查節奏＝又退回假警報"


def test_ensure_shadow_passes_an_explicit_expiry_instead_of_falling_back(monkeypatch) -> None:
    """真正會壞的地方是呼叫端忘了傳——所以驗的是 request 上的值，不是函式本身。"""

    captured: dict[str, object] = {}

    class NoCohorts:
        def list_operational_cohorts(self, *, as_of):  # noqa: ARG002
            return []

    def fake_evaluate_signal(store, provider, request, **kwargs):  # noqa: ARG001
        captured["expiry"] = request.expiry
        return {"cohort_id": "dc_test", "decision_id": "pd_test"}

    monkeypatch.setattr(workflow, "evaluate_signal", fake_evaluate_signal)
    result = workflow.ensure_shadow_for_company(
        NoCohorts(), object(), company_id="co:example", ticker="EX", as_of=AT
    )

    assert result["created"] is True
    policy = load_policy()
    assert captured["expiry"] == workflow._shadow_expiry(AT, policy)
    assert captured["expiry"] != workflow._default_expiry(AT, policy)


def test_policy_rejects_a_tracking_horizon_short_enough_to_be_a_fake_alarm() -> None:
    """把追蹤期限調回「幾天」＝退回舊行為，必須 fail closed 而不是安靜生效。

    邊界刻意訂在 7 天：`probe_lane.review_hours` 上限是 72 小時（3 天），所以只要
    追蹤期限不得低於一週，兩個時鐘的範圍就不可能重疊——不需要再寫一條永遠為真的
    交叉斷言（那會是 L14 第 4 點的恆滅 gate）。
    """

    import pytest

    from risk.policy import PolicyError, validate_policy

    for bad in (2, 3, 6):
        base = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        base["shadow_lane"]["tracking_expiry_days"] = bad
        with pytest.raises(PolicyError, match="tracking_expiry_days"):
            validate_policy(base)
