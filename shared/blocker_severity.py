"""Coverage blocker 嚴重度分類——唯一權威。

這份分類刻意住在一個不依賴 store／coverage 的模組裡，因為它有多個消費者，
而它們分屬不同層：

- ``sizing.calculate_probe_limits``：決定 ``research_status``（研究完整度三態）。
- ``coverage.assess_coverage`` 與 ``coverage.apply_execution_intent``：決定 lane 的
  ``context_ready``。
- ``store.get_coverage_result``：從持久化狀態重建同一個 ``context_ready``。
- ``action_card.build_action_card``：決定要不要強制 ``REVIEW``。

先前它只住在 ``coverage.py``，而 ``coverage`` 依賴 ``store``，於是 store 想用就會
循環 import——結果是只有 sizing 真的套用了分類，其餘三處各自用
``status == "analyzable"``（⟺ 零 blocker）這個更粗的判準。分類本身沒錯，錯在它
沒有一個所有層都拿得到的家。

⚠ ``status`` 的 ``analyzable`` ⟺ 零 blocker 是持久化 invariant（見
``store.record_coverage_assessment``），不得為了放行研究不完整的案例而鬆動；
需要嚴重度時一律呼叫本模組，不要拿 ``status`` 當代理指標。

2026-08-13 的兩個改變（實測依據見
``docs/brainstorms/2026-08-13-capital-expression-direction-requirements.md``）：

1. **分類搬進 ``config/decision_blockers.json`` 的 ``severity`` 欄位。**
   先前這裡是硬編碼 frozenset，而 config 另有一套 51 項的 ``resolution_mode``
   分類——兩套分類互不知道，一套給人看、一套決定資本（L12）。現在只有一套。
   ``severity`` 與 ``resolution_mode`` 正交：前者是「能不能動錢」，後者是「誰能解」。

2. **新增 lane 維度與 ``diagnostic`` 級。** 先前 ``sizing`` 對 lane blocker 是
   ``if paper_blockers: paper_max = 0.0``——不分嚴重度無條件歸零，於是
   ``execution_intent_research_only``（觸發率 80.6%、config 自述「此項不是缺口」）
   與 ``holdings_unconfirmed``（66.7%、自述「對研究用途是必然結果而非缺口」）
   把 live lane 擋掉 71/72 次。這兩者現在是 ``diagnostic``，永遠不歸零；
   而持股與執行 context 缺失改為只對 live 致命——paper 在 0.2% 尺度不需要 NAV。

**未登記的 code 一律 fail closed 當 fatal。** ``tests/test_coverage_severity.py``
會在出現未登記 code 時失敗，強迫做出分類決定，而不是靠預設安靜放行。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _ROOT / "config" / "decision_blockers.json"

FATAL = "fatal"
SIZING = "sizing"
DIAGNOSTIC = "diagnostic"
_SEVERITIES = frozenset({FATAL, SIZING, DIAGNOSTIC})

LANES = ("paper", "live")

# 財務核驗清單五項；coverage 匯入本常數，維持在此以免它去 import sizing。
CHECKLIST_ITEMS = (
    "gross_margin_trend",
    "customer_concentration",
    "backlog",
    "dilution",
    "valuation_pressure",
)


class BlockerRegistryError(ValueError):
    """``config/decision_blockers.json`` 不可安全載入。"""


class _Rule:
    __slots__ = ("key", "is_prefix", "severity", "fatal_lanes")

    def __init__(self, key: str, is_prefix: bool, severity: str, fatal_lanes: tuple[str, ...]):
        self.key = key
        self.is_prefix = is_prefix
        self.severity = severity
        self.fatal_lanes = fatal_lanes


@lru_cache(maxsize=1)
def _rules() -> tuple[tuple[_Rule, ...], tuple[_Rule, ...]]:
    """回傳 (exact code 規則, prefix 規則)；prefix 依長度由長到短排序。"""
    try:
        payload = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - 設定損毀
        raise BlockerRegistryError(f"cannot load {_CONFIG_PATH}: {exc}") from exc

    exact: list[_Rule] = []
    prefix: list[_Rule] = []
    for item in payload.get("blockers", ()):
        severity = item.get("severity")
        if severity not in _SEVERITIES:
            key = item.get("code") or item.get("prefix") or "?"
            raise BlockerRegistryError(
                f"blocker {key!r} has invalid severity {severity!r}; "
                f"must be one of {sorted(_SEVERITIES)}"
            )
        lanes = tuple(item.get("fatal_lanes") or LANES)
        if severity == FATAL and not set(lanes) <= set(LANES):
            raise BlockerRegistryError(f"blocker {item!r} has unknown fatal_lanes {lanes!r}")
        if "code" in item:
            exact.append(_Rule(str(item["code"]), False, severity, lanes))
        elif "prefix" in item:
            prefix.append(_Rule(str(item["prefix"]), True, severity, lanes))
        else:
            raise BlockerRegistryError(f"blocker entry needs code or prefix: {item!r}")
    prefix.sort(key=lambda rule: -len(rule.key))
    return tuple(exact), tuple(prefix)


def _match(blocker: str) -> _Rule | None:
    """先比對 exact code；未命中則取最長的 prefix 命中（與 config 的 _matching 一致）。"""
    exact, prefix = _rules()
    for rule in exact:
        if rule.key == blocker:
            return rule
    for rule in prefix:
        if blocker.startswith(rule.key):
            return rule
    return None


def severity_of(blocker: str) -> str:
    """未登記一律 fail closed 當 fatal——不猜測新 code 的意圖。"""
    rule = _match(blocker)
    return rule.severity if rule is not None else FATAL


def fatal_lanes_of(blocker: str) -> tuple[str, ...]:
    rule = _match(blocker)
    if rule is None:
        return LANES  # fail closed
    return rule.fatal_lanes if rule.severity == FATAL else ()


def is_fatal(blocker: str, *, lane: str | None = None) -> bool:
    """``lane=None`` 表示「在任一 lane 致命」——供非 lane-scoped 的 coverage.blockers 使用。"""
    lanes = fatal_lanes_of(blocker)
    if not lanes:
        return False
    return True if lane is None else lane in lanes


def fatal_blockers(
    blockers: Sequence[str] | Iterable[str], *, lane: str | None = None
) -> tuple[str, ...]:
    """回傳應使資本歸零的 blocker。

    ``lane=None`` 沿用舊語意（任一 lane 致命即算），供 ``coverage.blockers`` 這種
    非 lane-scoped 的清單使用；``lane="paper"``／``"live"`` 用於 lane blocker，
    只有對該 lane 致命的才會歸零。
    """
    return tuple(b for b in blockers if is_fatal(b, lane=lane))


def sizing_blockers(blockers: Sequence[str] | Iterable[str]) -> tuple[str, ...]:
    """研究／資料不完整：不阻擋，只讓最弱軸落到較低等級、影響排序。"""
    return tuple(b for b in blockers if severity_of(b) == SIZING)


def diagnostic_blockers(blockers: Sequence[str] | Iterable[str]) -> tuple[str, ...]:
    """完全不影響資本，只出現在報表。"""
    return tuple(b for b in blockers if severity_of(b) == DIAGNOSTIC)


def is_incomplete_research(blocker: str) -> bool:
    """向後相容：舊語意的「研究不完整」＝今天的 sizing 或 diagnostic（都不歸零）。"""
    return severity_of(blocker) != FATAL


def registered_keys() -> tuple[str, ...]:
    exact, prefix = _rules()
    return tuple(rule.key for rule in exact) + tuple(rule.key for rule in prefix)


__all__ = [
    "CHECKLIST_ITEMS",
    "DIAGNOSTIC",
    "FATAL",
    "LANES",
    "SIZING",
    "BlockerRegistryError",
    "diagnostic_blockers",
    "fatal_blockers",
    "fatal_lanes_of",
    "is_fatal",
    "is_incomplete_research",
    "registered_keys",
    "severity_of",
    "sizing_blockers",
]
