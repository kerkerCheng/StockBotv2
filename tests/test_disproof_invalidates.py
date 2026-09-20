"""反證指得出它會推翻哪一條假設（2026-09-20）。

## 為什麼這一格值得存在，而 `Catalyst.resolves` 的教訓正好相反

Phase 4b 的驗收行是「多年橋算得出倍率與它的前提鏈，且**每一格配 disproof**」。
2026-09-20 量了才知道它機械上驗不了的原因**不是研究層沒做**：

| | |
|---|---|
| 判斷檔有 `disproof_conditions` | 63/63 |
| L7 三件套全齊 | 63/63（100%） |
| **散文已逐字指名它會推翻哪個 driver** | **60 檔（95%）** |

例（AXTI）：「supersede `revenue_growth` 與 `operating_margin_delta` 兩筆假設」。
**內容早就在，缺的是一個程式讀得到的欄位**——L16 的形狀。

⚠ 刻意**不**沿用 `Catalyst.resolves` 的 `assumption_id` 形狀，兩個理由：
①`resolves` 實測只有 4/106，而那 4 條全在 LITE／COHR（session 當下手上剛好有 id）；
②`assumption_id` 會被 supersede 換掉，driver 名稱不會——用 id 的連結改一次假設就斷。

⚠ 同時記下一個**被自己的量測否證的假說**：原本推論「`resolves` 填不起來純粹是介面問題」。
但催化劑散文指名 driver 只有 26%（28/106）——若純粹是介面問題，散文指名率該一樣高。
**disproof 與 catalyst 不是同一種東西**（前者天然在講「什麼會推翻哪個假設」，後者天然在
講「什麼時候發生什麼事」），所以不該套同一個修法。
"""
from __future__ import annotations

import pytest

from alpha.contracts import Catalyst, DisproofCondition
from alpha.errors import ContractViolation


def _disproof(**kwargs) -> DisproofCondition:
    base = dict(condition="連兩季毛利率跌破 40%",
                check_frequency="每季財報後 5 個工作日內",
                action_within_48h="supersede 營益率假設並重新 materialize")
    base.update(kwargs)
    return DisproofCondition(**base)


def test_driver_names_are_accepted_with_and_without_scope() -> None:
    d = _disproof(invalidates=("revenue_growth",
                               "operating_margin_delta[mix_and_utilization]"))
    assert d.invalidates == ("revenue_growth", "operating_margin_delta[mix_and_utilization]")


def test_an_assumption_id_is_refused_on_purpose() -> None:
    """`oa_*` 會被 supersede 換掉——用它當連結，改一次假設就斷。"""
    with pytest.raises(ContractViolation, match="invalidates"):
        _disproof(invalidates=("oa_3b91ca406107e9a4",))


def test_a_typo_fails_loudly_instead_of_sinking_silently() -> None:
    """L16-3：自由字串卻決定去留，打錯不報錯、只是靜默沉底。"""
    with pytest.raises(ContractViolation, match="已登記的 driver"):
        _disproof(invalidates=("revene_growth",))          # 少一個 u


def test_empty_stays_legal_because_63_existing_files_would_otherwise_break() -> None:
    """空的＝**還沒有人寫**，不是「這條反證不推翻任何假設」。

    不設必填是刻意的（沿用 `Catalyst.resolves` 的先例）：必填會讓 63 個既有判斷檔
    一次全部變成非法，而它們的內容其實是好的——95% 已經在散文裡指名了 driver。
    """
    assert _disproof().invalidates == ()


def test_the_l7_three_part_requirement_is_untouched() -> None:
    """新增一格**不得**鬆動 L7：三件套仍然缺一即拒收。"""
    for missing in ("condition", "check_frequency", "action_within_48h"):
        with pytest.raises(ContractViolation):
            _disproof(**{missing: ""}, invalidates=("revenue_growth",))


def test_catalyst_still_wants_assumption_ids_not_driver_names() -> None:
    """兩個欄位刻意不同形——**不要順手把它們統一**。

    `Catalyst.resolves` 問的是「這個**事件**會裁決哪幾條假設」，事件與假設是多對多且
    與時點綁定，用 id 才指得準；`DisproofCondition.invalidates` 問的是「這條**反證**
    推翻哪一類判斷」，那是 driver 層級的語意。
    """
    with pytest.raises(ValueError, match="resolves"):
        Catalyst(kind="margin_inflection", description="Q3 財報", resolves=("revenue_growth",))
