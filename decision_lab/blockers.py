"""Blocker 字彙的中立 registry（讀側分類層）。

Blocker code 是承重字串：由 `coverage.py`／`sizing.py`／`engine_d_runtime/adapters.py`
產生，再被 brief、待辦池與人類消費，其間還有 `context.py` 的前綴改寫
（`market_` → `execution_market_`）與 `sizing.py` 的前綴比對。本模組不改變任何 code
的產生方式——那會動到已凍結的 decision payload——只回答三個問題：

1. 這個 code 是什麼意思（中文 label）？
2. 它需要使用者現在做決定，還是在等世界發生某件事？
3. 下一步具體要做什麼？

第 2 點是把「等決定」與「等事件」分離的判準來源：一個項目只有在它**所有** blocker
都不是 `user_decision` 時，才可以離開決策佇列轉為等待項。這個保守規則會偏向多問一次，
而不是安靜地把需要你決定的事藏起來。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PATH = _ROOT / "config" / "decision_blockers.json"

RESOLUTION_MODES = ("user_decision", "awaiting_external", "system_internal")


class BlockerRegistryError(ValueError):
    """registry 本身不合法。"""


@dataclass(frozen=True)
class BlockerSpec:
    """一個 blocker code（或前綴族）的說明。"""

    label: str
    category: str
    resolution_mode: str
    next_step: str
    code: str | None = None
    prefix: str | None = None

    @property
    def key(self) -> str:
        return self.code or f"{self.prefix}*"

    @property
    def needs_user(self) -> bool:
        return self.resolution_mode == "user_decision"

    @property
    def is_waiting(self) -> bool:
        return self.resolution_mode == "awaiting_external"


UNKNOWN = BlockerSpec(
    label="未登記的 blocker",
    category="unknown",
    resolution_mode="user_decision",
    next_step=(
        "此 code 不在 config/decision_blockers.json。未知一律當成需要人看，"
        "並請補登記——未登記代表字彙已漂移。"
    ),
    code=None,
)


@dataclass(frozen=True)
class BlockerRegistry:
    version: int
    _exact: Mapping[str, BlockerSpec]
    _prefixes: tuple[BlockerSpec, ...]
    _axis_suffix: BlockerSpec | None

    @classmethod
    def from_path(cls, path: Path = _DEFAULT_PATH) -> "BlockerRegistry":
        return cls.from_payload(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "BlockerRegistry":
        version = int(payload["version"])
        raw = payload.get("blockers")
        if not isinstance(raw, list) or not raw:
            raise BlockerRegistryError("blockers must be a non-empty list")
        exact: dict[str, BlockerSpec] = {}
        prefixes: list[BlockerSpec] = []
        for item in raw:
            spec = cls._parse(item)
            if spec.code is not None:
                if spec.code in exact:
                    raise BlockerRegistryError(f"duplicate blocker code: {spec.code}")
                exact[spec.code] = spec
            else:
                prefixes.append(spec)
        axis_raw = payload.get("_axis_unknown_suffix")
        axis_spec = None
        if isinstance(axis_raw, Mapping):
            axis_spec = BlockerSpec(
                label=str(axis_raw["label"]),
                category=str(axis_raw["category"]),
                resolution_mode=cls._mode(axis_raw["resolution_mode"]),
                next_step=str(axis_raw["next_step"]),
                prefix=None,
                code=None,
            )
        # 長前綴優先，避免 financial_ 蓋掉 financial_checklist_
        prefixes.sort(key=lambda s: len(s.prefix or ""), reverse=True)
        return cls(
            version=version,
            _exact=exact,
            _prefixes=tuple(prefixes),
            _axis_suffix=axis_spec,
        )

    @staticmethod
    def _mode(value: object) -> str:
        mode = str(value)
        if mode not in RESOLUTION_MODES:
            raise BlockerRegistryError(f"unknown resolution_mode: {mode}")
        return mode

    @classmethod
    def _parse(cls, item: object) -> BlockerSpec:
        if not isinstance(item, Mapping):
            raise BlockerRegistryError("each blocker entry must be an object")
        code = item.get("code")
        prefix = item.get("prefix")
        if bool(code) == bool(prefix):
            raise BlockerRegistryError(
                "each blocker entry needs exactly one of code / prefix"
            )
        return BlockerSpec(
            label=str(item["label"]),
            category=str(item["category"]),
            resolution_mode=cls._mode(item["resolution_mode"]),
            next_step=str(item["next_step"]),
            code=str(code) if code else None,
            prefix=str(prefix) if prefix else None,
        )

    def describe(self, blocker: str) -> BlockerSpec:
        """exact → 最長 prefix → 軸 _unknown 後綴 → UNKNOWN。"""

        code = str(blocker).strip()
        if code in self._exact:
            return self._exact[code]
        for spec in self._prefixes:
            if spec.prefix and code.startswith(spec.prefix):
                return spec
        if self._axis_suffix is not None and code.endswith("_unknown"):
            return self._axis_suffix
        return UNKNOWN

    def is_registered(self, blocker: str) -> bool:
        return self.describe(blocker) is not UNKNOWN

    def classify(self, blockers: Iterable[str]) -> dict[str, list[str]]:
        """把一組 blocker 依 resolution_mode 分堆。"""

        grouped: dict[str, list[str]] = {mode: [] for mode in RESOLUTION_MODES}
        for blocker in blockers:
            grouped[self.describe(blocker).resolution_mode].append(str(blocker))
        return grouped

    def needs_user_decision(self, blockers: Iterable[str]) -> bool:
        """保守規則：只要有一個 blocker 需要人決定，整個項目就留在決策佇列。"""

        return any(self.describe(b).needs_user for b in blockers)

    def waiting_reasons(self, blockers: Iterable[str]) -> list[str]:
        """回傳造成「等待」的 blocker 的人類可讀理由（去重、保序）。"""

        seen: dict[str, None] = {}
        for blocker in blockers:
            spec = self.describe(blocker)
            if spec.is_waiting:
                seen.setdefault(spec.label, None)
        return list(seen)


@lru_cache(maxsize=1)
def get_blocker_registry() -> BlockerRegistry:
    return BlockerRegistry.from_path()


def describe_blocker(blocker: str) -> BlockerSpec:
    return get_blocker_registry().describe(blocker)
