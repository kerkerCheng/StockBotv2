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
_TRACE_STATUS_PATH = _ROOT / "config" / "lead_trace_status.json"
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


@dataclass(frozen=True)
class TraceStatusRegistry:
    """``trace_status`` 的封閉字彙。

    ⚠ 這個字彙**有行為後果**，不只是命名整潔：``trace_backlog`` 用 ``terminal``
    決定一筆 parked lead 該不該留在追源 backlog。寫成未登記的同義詞不會報錯，
    只會靜默地讓已完成的 lead 永遠掛著、或讓真的在等的 lead 消失。
    """

    version: int
    terminal: frozenset[str]
    non_terminal: frozenset[str]
    labels: Mapping[str, str]
    aliases: Mapping[str, str]

    @property
    def known(self) -> frozenset[str]:
        return self.terminal | self.non_terminal

    @classmethod
    def from_path(cls, path: Path) -> "TraceStatusRegistry":
        return cls.from_payload(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "TraceStatusRegistry":
        version = int(payload["version"])
        if version < 1:
            raise LeadRefError("trace status registry version must be positive")
        raw_statuses = payload.get("statuses")
        if not isinstance(raw_statuses, dict) or not raw_statuses:
            raise LeadRefError("trace status registry statuses must be non-empty")
        terminal: set[str] = set()
        non_terminal: set[str] = set()
        labels: dict[str, str] = {}
        for raw_name, raw_spec in raw_statuses.items():
            name = str(raw_name).strip()
            if not name or not isinstance(raw_spec, dict):
                raise LeadRefError(f"非法的 trace_status：{name!r}")
            if not str(raw_spec.get("description") or "").strip():
                raise LeadRefError(f"trace_status {name!r} 必須說明用途")
            is_terminal = raw_spec.get("terminal")
            if not isinstance(is_terminal, bool):
                raise LeadRefError(f"trace_status {name!r} 的 terminal 必須是 boolean")
            (terminal if is_terminal else non_terminal).add(name)
            labels[name] = str(raw_spec.get("label") or name)
        aliases: dict[str, str] = {}
        for raw_alias, raw_target in (payload.get("aliases") or {}).items():
            alias = str(raw_alias).strip()
            target = str(raw_target).strip()
            if target not in labels:
                raise LeadRefError(
                    f"trace_status alias {alias!r} 指向未登記的值：{target!r}"
                )
            if alias in labels:
                raise LeadRefError(f"trace_status alias {alias!r} 與登記值同名")
            aliases[alias] = target
        return cls(
            version=version,
            terminal=frozenset(terminal),
            non_terminal=frozenset(non_terminal),
            labels=MappingProxyType(labels),
            aliases=MappingProxyType(aliases),
        )

    def resolve(self, value: str, *, allow_alias: bool = True) -> str:
        """正規化成登記值。

        ``allow_alias=True`` 供**既有資料遷移**使用：歷史同義詞靜默轉成 canonical。
        ``allow_alias=False`` 供**新寫入**使用：同義詞一律拒絕。

        兩者刻意不同，是因為 2026-08-25 實測過放行的代價——alias 在寫入端被靜默
        接受時，`primary_source_obtained` 會變成終結的 `original_obtained`，
        而作者真正要表達的是非終結的 `awaiting_named_disclosure`。**同義詞之所以
        危險，不是拼法不整齊，是它讓寫的人以為自己表達了一個沒被記錄的區別。**
        拒絕並指名 canonical 值，才會逼出那個選擇。
        """

        name = str(value).strip()
        if name in self.labels:
            return name
        if name in self.aliases:
            if allow_alias:
                return self.aliases[name]
            raise LeadRefError(
                f"trace_status {name!r} 是已淘汰的同義詞；"
                f"請明確改寫成 {self.aliases[name]!r} 或其他登記值"
                f"（合法值：{', '.join(sorted(self.labels))}）"
            )
        suggestion = difflib.get_close_matches(name, self.labels, n=1, cutoff=0.5)
        hint = f"；你是否要寫 {suggestion[0]!r}？" if suggestion else ""
        raise LeadRefError(
            f"未登記的 trace_status：{name!r}{hint}"
            f"；合法值：{', '.join(sorted(self.labels))}"
            "。要新增請先改 config/lead_trace_status.json"
        )

    def is_terminal(self, value: str) -> bool:
        try:
            return self.resolve(value) in self.terminal
        except LeadRefError:
            # 未登記值一律當非終結：寧可讓它留在 backlog 被看見，
            # 也不要因為拼錯而靜默消失。
            return False


@lru_cache(maxsize=1)
def get_lead_ref_registry() -> LeadRefRegistry:
    return LeadRefRegistry.from_path(_DEFAULT_REGISTRY_PATH)


@lru_cache(maxsize=1)
def get_trace_status_registry() -> TraceStatusRegistry:
    return TraceStatusRegistry.from_path(_TRACE_STATUS_PATH)


def validate_ref_updates(updates: Mapping[str, Any]) -> dict[str, Any]:
    cleaned = get_lead_ref_registry().validate_updates(updates)
    if "trace_status" in cleaned:
        # 寫入端不接受同義詞：見 TraceStatusRegistry.resolve 的理由。
        cleaned["trace_status"] = get_trace_status_registry().resolve(
            cleaned["trace_status"], allow_alias=False
        )
    return cleaned


__all__ = [
    "LeadRefError",
    "LeadRefRegistry",
    "LeadRefSpec",
    "TraceStatusRegistry",
    "get_lead_ref_registry",
    "get_trace_status_registry",
    "validate_ref_updates",
]
