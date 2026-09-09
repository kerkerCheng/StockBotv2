"""常規授權類別的唯一 loader（`config/standing_authorization.json`）——2026-09-09 研究閉環 P3。

哪些 pq2 類型的 `go` 只是注意力 gate、使用者已預先授權，由 config 決定；本模組只負責
**載入、驗證封閉性、回答 is_authorized**。它不 dispatch 任何東西——consumer 是
`engine_b.todo.standing_go`。

封閉性：`engine_b.todo.ITEM_TYPES` 的每一種都必須落在 `authorized` 或 `never` 其中之一，
兩邊交集必須為空；否則載入就失敗。新增 pq2 類型時，這裡會逼你先回答「它攔的是注意力
還是 authority」。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "config" / "standing_authorization.json"


class StandingAuthorizationError(ValueError):
    """config 缺漏或違反封閉性。"""


@dataclass(frozen=True)
class StandingAuthorization:
    authorized: Mapping[str, Mapping[str, Any]]
    never: Mapping[str, str]
    path: Path = DEFAULT_PATH
    schema_version: int = 1
    _skip_hints: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def is_authorized(self, item_type: str) -> bool:
        return item_type in self.authorized

    def skip_hint_tokens(self, item_type: str) -> tuple[str, ...]:
        return tuple(self._skip_hints.get(item_type, ()))

    def why_never(self, item_type: str) -> str | None:
        return self.never.get(item_type)


def load(path: Path | str | None = None, *, item_types: Mapping[str, Any] | None = None) -> StandingAuthorization:
    """載入並驗證。`item_types` 預設取 `engine_b.todo.ITEM_TYPES`（延遲 import，避免循環）。"""
    target = Path(path) if path else DEFAULT_PATH
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StandingAuthorizationError(f"{target} 不存在——常規授權清單缺席時一律視為未授權") from exc
    except json.JSONDecodeError as exc:
        raise StandingAuthorizationError(f"{target} 不是合法 JSON：{exc}") from exc
    if payload.get("schema_version") != 1:
        raise StandingAuthorizationError("standing_authorization schema_version 必須是 1")
    authorized = payload.get("authorized")
    never = payload.get("never")
    if not isinstance(authorized, dict) or not isinstance(never, dict):
        raise StandingAuthorizationError("authorized 與 never 都必須是 object")
    overlap = set(authorized) & set(never)
    if overlap:
        raise StandingAuthorizationError(f"同一類型不得同時 authorized 與 never：{sorted(overlap)}")
    if item_types is None:
        from engine_b.todo import ITEM_TYPES

        item_types = ITEM_TYPES
    unclassified = sorted(set(item_types) - set(authorized) - set(never))
    if unclassified:
        raise StandingAuthorizationError(
            f"pq2 類型未分類（必須明寫 authorized 或 never，回答它攔的是注意力還是 authority）：{unclassified}")
    unknown = sorted((set(authorized) | set(never)) - set(item_types))
    if unknown:
        raise StandingAuthorizationError(f"config 列了 ITEM_TYPES 沒有的類型：{unknown}")
    skip_hints = {
        key: tuple(str(t) for t in (value.get("skip_when_hint_mentions") or ()))
        for key, value in authorized.items() if isinstance(value, dict)
    }
    return StandingAuthorization(
        authorized={k: dict(v) for k, v in authorized.items()},
        never={k: str(v) for k, v in never.items()},
        path=target, _skip_hints=skip_hints,
    )


__all__ = ["DEFAULT_PATH", "StandingAuthorization", "StandingAuthorizationError", "load"]
