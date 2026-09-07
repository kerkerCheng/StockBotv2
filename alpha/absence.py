"""缺席語意（Absence semantics）——**「沒有值」不是一種狀態，是至少六種**。

## 為什麼需要這一層

`status` 已經分得出 `missing`／`not_modeled`／`not_applicable`／`insufficient_evidence`，
但 `missing` 這一格自己就承載了四種完全不同的意思（L12：一個表示兩種語意）：

| 真實情況 | 使用者該做什麼 | 舊表示 |
|---|---|---|
| 還沒有人寫下來 | 去研究、去寫 | `missing` |
| **研究結論就是「現在沒有可辯護的假設，所以刻意不主張」** | **什麼都不做——這已經是答案** | `missing` |
| 上游缺一格，這一格本身沒問題 | 去補上游，不是補這一格 | `missing` |
| 外部來源不提供 | 換來源或人工建立觀測 | `missing` |

2026-09-07 Coverage Pilot 實測：6324.T 的估值 blocker 逐字是「尚未寫入任何估值假設」，
而真實狀態是**研究結論：無法錨定倍數，所以不寫**。兩者共用一句話，下一個讀者無從分辨——
而 APP 會把這句話直接放到使用者眼前。

## 這一層不做的事

- **不是新的 status。** `status` 回答「這一格能不能用」，`absence_kind` 回答「它為什麼沒有」。
  兩者正交：同一個 `missing` 可以是四種 kind，而 `available` 永遠沒有 kind。
- **不由散文推導。** 每個 kind 都由**產生缺席的那一段程式自己宣告**（它當下就知道走了哪個分支），
  或由 `default_absence_kind()` 這張**查表**給出 status 的預設。
  renderer／API 一律不得 parse `reason` 去猜（L16：分類要跟著資料走，不是讓每個消費端各猜一份）。
- **不放寬任何 gate。** 宣告「刻意不主張」需要一筆 append-only 的 `Abstention` 紀錄
  （`alpha/abstention/`），不是在呈現層打一個標籤。
"""
from __future__ import annotations

from typing import Mapping

#: 封閉字彙：一格「沒有值」到底是哪一種沒有。每個 kind 的字串同時是 API 契約的一部分。
ABSENCE_KINDS: Mapping[str, str] = {
    "not_yet_recorded": "能力存在、authority 也接受這一格，但目前沒有任何紀錄——還沒做",
    "deliberate_abstention": "已明示宣告不主張：現在沒有可辯護的假設，所以刻意不 assert（這是研究結論，不是待辦）",
    "method_not_applicable": "資料齊全，但這個方法套在這筆資料上沒有定義——補資料解不掉",
    "upstream_unavailable": "這一格本身沒問題，是它依賴的上游缺席——要補的是上游",
    "inputs_incompatible": "每個輸入都有值，但它們的身分（會計期間／口徑／單位）不相容，不得相乘或相減",
    "provider_missing": "外部來源不提供這一格；不是我們沒做",
    "capability_absent": "本層沒有這個能力（not_modeled）——需要新增能力，不是新增資料",
    "point_in_time_unavailable": "在 as-of 視角下這個來源沒有時點投影，不得以當前值冒充（INV-6）",
    "insufficient_evidence": "有資料，但證據不足以支撐主張",
    "invalidated": "曾經有值，已被判定失效",
    "not_applicable_unspecified": "已宣告不適用，但**沒有宣告是哪一種不適用**——這一格自己就是待補的語意",
}

#: `status` → 預設 kind 的**查表**。刻意讓 `not_applicable` 落到 `not_applicable_unspecified`：
#: 它今天同時被 PIT（沒有時點投影）與方法層（本益比法遇到虧損）使用，猜任何一邊都是造假。
#: 知道自己是哪一種的呼叫端要**明示**——那正是這張表存在的目的。
DEFAULT_ABSENCE_KIND: Mapping[str, str] = {
    "missing": "not_yet_recorded",
    "not_modeled": "capability_absent",
    "insufficient_evidence": "insufficient_evidence",
    "invalidated": "invalidated",
    "not_applicable": "not_applicable_unspecified",
}

#: 哪些 kind 表示「這已經是答案，不要去補」——APP 用它決定要不要把這一格算成待辦。
#: ⚠ 它**不**表示 readiness 變好：blocked 還是 blocked，只是理由不同。
SETTLED_ABSENCE_KINDS: frozenset[str] = frozenset({
    "deliberate_abstention", "method_not_applicable", "capability_absent",
})


class AbsenceVocabularyError(ValueError):
    """`absence_kind` 不在封閉字彙裡。"""


def check_absence_kind(kind: str, label: str = "absence_kind") -> str:
    if kind not in ABSENCE_KINDS:
        raise AbsenceVocabularyError(
            f"{label} 未登記：{kind!r}；已知 {sorted(ABSENCE_KINDS)}——"
            "缺席語意是封閉字彙，新增一種要同時說明消費端該怎麼處理它")
    return kind


def default_absence_kind(status: str) -> str | None:
    """一個 status 在沒有明示 kind 時該讀成哪一種缺席。**查表，不推論**；有值的 status 回 `None`。"""
    return DEFAULT_ABSENCE_KIND.get(status)


def describe_absence_kind(kind: str) -> str:
    return ABSENCE_KINDS[check_absence_kind(kind)]


__all__ = [
    "ABSENCE_KINDS", "AbsenceVocabularyError", "DEFAULT_ABSENCE_KIND", "SETTLED_ABSENCE_KINDS",
    "check_absence_kind", "default_absence_kind", "describe_absence_kind",
]
