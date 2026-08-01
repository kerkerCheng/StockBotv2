"""Engine B lead ``refs`` 的封閉字彙 registry。

``refs`` 是可擴充 taxonomy，但寫入端必須先登記名稱，否則 ``park_reason``
這類拼錯會成功落盤、所有讀取端卻只看 ``parked_reason``。既有資料保持可讀；
新增用途只需先改 ``config/lead_ref_keys.json``，不必改 Python。
"""
from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_REGISTRY_PATH = _ROOT / "config" / "lead_ref_keys.json"
_VALUE_TYPES = frozenset({"string", "string_list"})


class LeadRefError(ValueError):
    """未登記的 ref key、錯誤 value type 或 registry 格式錯誤。"""


@dataclass(frozen=True)
class LeadRefSpec:
    key: str
    category: str
    value_type: str
    description: str


@dataclass(frozen=True)
class LeadRefRegistry:
    version: int
    keys: Mapping[str, LeadRefSpec]

    @classmethod
    def from_path(cls, path: Path) -> "LeadRefRegistry":
        return cls.from_payload(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "LeadRefRegistry":
        version = int(payload["version"])
        if version < 1:
            raise LeadRefError("lead ref registry version must be positive")
        categories = payload.get("categories")
        if not isinstance(categories, dict) or not categories:
            raise LeadRefError("lead ref registry categories must be non-empty")
        specs: dict[str, LeadRefSpec] = {}
        for raw_category, raw_keys in categories.items():
            category = str(raw_category).strip()
            if not category or not isinstance(raw_keys, dict) or not raw_keys:
                raise LeadRefError("每個 lead ref category 必須是非空 object")
            for raw_key, raw_spec in raw_keys.items():
                key = str(raw_key).strip()
                if not key or key in specs or not isinstance(raw_spec, dict):
                    raise LeadRefError(f"非法或重複的 lead ref key：{key!r}")
                value_type = str(raw_spec.get("value_type") or "").strip()
                description = str(raw_spec.get("description") or "").strip()
                if value_type not in _VALUE_TYPES:
                    raise LeadRefError(
                        f"lead ref {key!r} 使用未知 value_type：{value_type!r}"
                    )
                if not description:
                    raise LeadRefError(f"lead ref {key!r} 必須說明用途")
                specs[key] = LeadRefSpec(
                    key=key,
                    category=category,
                    value_type=value_type,
                    description=description,
                )
        return cls(version=version, keys=MappingProxyType(specs))

    def validate_updates(self, updates: Mapping[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for raw_key, value in updates.items():
            key = str(raw_key).strip()
            if not key:
                raise LeadRefError("ref key 不可為空")
            spec = self.keys.get(key)
            if spec is None:
                suggestion = difflib.get_close_matches(key, self.keys, n=1, cutoff=0.65)
                hint = f"；你是否要寫 {suggestion[0]!r}？" if suggestion else ""
                raise LeadRefError(
                    f"未登記的 lead ref key：{key!r}{hint}"
                    "；請先在 config/lead_ref_keys.json 登記用途"
                )
            if value is None:
                raise LeadRefError(f"ref {key} 不可為 null")
            if spec.value_type == "string":
                if not isinstance(value, str):
                    raise LeadRefError(f"ref {key} 必須是 string")
                cleaned[key] = value
            else:
                if not isinstance(value, list) or any(
                    not isinstance(item, str) or not item.strip() for item in value
                ):
                    raise LeadRefError(f"ref {key} 必須是非空字串 list")
                cleaned[key] = list(value)
        return cleaned


@lru_cache(maxsize=1)
def get_lead_ref_registry() -> LeadRefRegistry:
    return LeadRefRegistry.from_path(_DEFAULT_REGISTRY_PATH)


def validate_ref_updates(updates: Mapping[str, Any]) -> dict[str, Any]:
    return get_lead_ref_registry().validate_updates(updates)


__all__ = [
    "LeadRefError",
    "LeadRefRegistry",
    "LeadRefSpec",
    "get_lead_ref_registry",
    "validate_ref_updates",
]
