"""Engine C 人工觀測欄位的中立 registry。

`config/engine_c_observation_fields.json` 是唯一權威，照 `schema/vocab.json` 的先例
把字彙留在 config、不寫死在 Python：新增一類財務事實只要在該檔加一項。

兩條硬契約：

1. **Gate 凍結。** `gate_member=true` 的五項就是 L9 前置條件 #3 的財務核驗清單，
   `thesis/preconditions.py` 依賴它。`GATE_FIELDS` 的長度在測試中被鎖住——新增欄位
   一律 `gate_member=false`，否則 `engine_c/checklist.py` 的 `gate_pass`（對 items
   全體取 all）會讓所有既有標的退化。
2. **拒絕未登記欄位。** 開放寫入的真正風險不是欄位不夠，而是同一個概念被不同 session
   寫成不同名字（contingent_claims / contingent_liquidity_claims）造成同義詞漂移，
   使查詢與引用都失效。因此 `validate_field_name` 直接 raise，要新增就先改 config。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field as _dc_field
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_REGISTRY_PATH = _ROOT / "config" / "engine_c_observation_fields.json"

# Engine D 的 reference index 認得的 authority token；與 decision_lab/sizing.py 的
# AXIS_REFERENCE_AUTHORITIES 對齊。此處只驗證拼寫，不反向依賴 decision_lab。
KNOWN_AUTHORITIES = frozenset(
    {
        "engine_c_financial",
        "engine_c_manual",
        "engine_c_customer",
        "engine_c_backlog",
        "engine_c_valuation",
    }
)


class ObservationFieldError(ValueError):
    """未登記的欄位名或 registry 本身不合法。"""


@dataclass(frozen=True)
class ObservationField:
    """一個人工觀測欄位的定義。"""

    field_name: str
    category: str
    label: str
    gate_member: bool
    authorities: tuple[str, ...]
    auto_source: str | None = None
    why: str | None = None

    @property
    def is_manual(self) -> bool:
        """auto_source 為空即需人工從一手來源填入。"""

        return self.auto_source is None


@dataclass(frozen=True)
class ObservationFieldRegistry:
    """只讀 lookup；缺值不猜測。"""

    version: int
    categories: Mapping[str, Mapping[str, str]]
    fields: Mapping[str, ObservationField]
    _order: tuple[str, ...] = _dc_field(default=())

    @classmethod
    def from_path(cls, path: Path) -> "ObservationFieldRegistry":
        return cls.from_payload(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ObservationFieldRegistry":
        version = int(payload["version"])
        if version < 1:
            raise ObservationFieldError("observation field registry version must be positive")
        raw_categories = payload.get("categories")
        if not isinstance(raw_categories, dict) or not raw_categories:
            raise ObservationFieldError("registry categories must be a non-empty object")
        raw_fields = payload.get("fields")
        if not isinstance(raw_fields, list) or not raw_fields:
            raise ObservationFieldError("registry fields must be a non-empty list")

        categories = {
            str(key): MappingProxyType({str(k): str(v) for k, v in value.items()})
            for key, value in raw_categories.items()
        }
        fields: dict[str, ObservationField] = {}
        order: list[str] = []
        for item in raw_fields:
            name = str(item["field_name"]).strip()
            if not name:
                raise ObservationFieldError("field_name must be non-empty")
            if name in fields:
                raise ObservationFieldError(f"duplicate field_name: {name}")
            category = str(item["category"]).strip()
            if category not in categories:
                raise ObservationFieldError(
                    f"field {name!r} references unknown category {category!r}"
                )
            authorities = tuple(str(a) for a in (item.get("authorities") or ()))
            unknown = sorted(set(authorities) - KNOWN_AUTHORITIES)
            if unknown:
                raise ObservationFieldError(
                    f"field {name!r} references unknown authorities: {unknown}"
                )
            if not authorities:
                raise ObservationFieldError(f"field {name!r} must declare authorities")
            fields[name] = ObservationField(
                field_name=name,
                category=category,
                label=str(item["label"]),
                gate_member=bool(item.get("gate_member")),
                authorities=authorities,
                auto_source=(
                    str(item["auto_source"])
                    if item.get("auto_source") is not None
                    else None
                ),
                why=str(item["why"]) if item.get("why") is not None else None,
            )
            order.append(name)
        return cls(
            version=version,
            categories=MappingProxyType(categories),
            fields=MappingProxyType(fields),
            _order=tuple(order),
        )

    def get(self, field_name: str) -> ObservationField | None:
        return self.fields.get(field_name.strip())

    def has(self, field_name: str) -> bool:
        return field_name.strip() in self.fields

    @property
    def gate_field_names(self) -> tuple[str, ...]:
        return tuple(n for n in self._order if self.fields[n].gate_member)

    @property
    def extended_field_names(self) -> tuple[str, ...]:
        """非 gate 欄位；這些是可自由擴充的開放表面。"""

        return tuple(n for n in self._order if not self.fields[n].gate_member)

    def manual_field_names(self) -> tuple[str, ...]:
        return tuple(n for n in self._order if self.fields[n].is_manual)

    def by_category(self) -> Mapping[str, tuple[str, ...]]:
        grouped: dict[str, list[str]] = {key: [] for key in self.categories}
        for name in self._order:
            grouped[self.fields[name].category].append(name)
        return MappingProxyType({k: tuple(v) for k, v in grouped.items()})

    def describe(self) -> str:
        """人類可讀的階層式清單，供 CLI 錯誤訊息使用。"""

        lines: list[str] = []
        for category, names in self.by_category().items():
            label = self.categories[category].get("label", category)
            lines.append(f"  {category}（{label}）")
            for name in names:
                spec = self.fields[name]
                mark = "[gate]" if spec.gate_member else "      "
                auto = "（自動）" if not spec.is_manual else ""
                lines.append(f"    {mark} {name}{auto} — {spec.label}")
        return "\n".join(lines)


@lru_cache(maxsize=1)
def get_observation_field_registry() -> ObservationFieldRegistry:
    """載入版本控制內的唯一 registry。"""

    return ObservationFieldRegistry.from_path(_DEFAULT_REGISTRY_PATH)


def validate_field_name(field_name: str) -> ObservationField:
    """回傳欄位定義；未登記即 raise，避免同義詞漂移。"""

    registry = get_observation_field_registry()
    spec = registry.get(field_name)
    if spec is None:
        raise ObservationFieldError(
            f"未登記的觀測欄位：{field_name!r}。\n"
            f"要新增請先在 config/engine_c_observation_fields.json 加一項"
            f"（gate_member 必須為 false）。目前已登記：\n{registry.describe()}"
        )
    return spec


def authorities_for(field_name: str) -> tuple[str, ...]:
    """欄位對應的 Engine D reference authority token。"""

    return validate_field_name(field_name).authorities
