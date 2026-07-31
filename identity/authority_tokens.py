"""Authority token 字彙的中立 loader。

刻意放在 `identity/`（既有的中立 registry 套件）而非 Engine C 或 Decision Lab
底下：Engine C 與 Decision Lab 都要讀它，而 `decision_lab` 不得依賴 Engine C 的
runtime authority。放中立處讓兩邊共用同一份定義，取代先前三份寫死的副本。

`config/authority_tokens.json` 是唯一權威。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PATH = _ROOT / "config" / "authority_tokens.json"


class AuthorityTokenError(ValueError):
    """未知 token 或 registry 不合法。"""


@dataclass(frozen=True)
class AuthorityToken:
    token: str
    owner: str
    label: str
    description: str


@dataclass(frozen=True)
class AuthorityTokenRegistry:
    version: int
    tokens: Mapping[str, AuthorityToken]

    @classmethod
    def from_path(cls, path: Path = _DEFAULT_PATH) -> "AuthorityTokenRegistry":
        return cls.from_payload(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "AuthorityTokenRegistry":
        raw = payload.get("tokens")
        if not isinstance(raw, list) or not raw:
            raise AuthorityTokenError("tokens must be a non-empty list")
        tokens: dict[str, AuthorityToken] = {}
        for item in raw:
            if not isinstance(item, Mapping):
                raise AuthorityTokenError("each token entry must be an object")
            name = str(item["token"]).strip()
            if not name:
                raise AuthorityTokenError("token must be non-empty")
            if name in tokens:
                raise AuthorityTokenError(f"duplicate token: {name}")
            tokens[name] = AuthorityToken(
                token=name,
                owner=str(item["owner"]),
                label=str(item["label"]),
                description=str(item["description"]),
            )
        return cls(version=int(payload["version"]), tokens=MappingProxyType(tokens))

    def all_tokens(self) -> frozenset[str]:
        return frozenset(self.tokens)

    def by_owner(self, *owners: str) -> frozenset[str]:
        """取得某些 owner 群組的 token 集合，供 payload 自報白名單使用。"""

        wanted = set(owners)
        unknown = wanted - {spec.owner for spec in self.tokens.values()}
        if unknown:
            raise AuthorityTokenError(f"unknown owner(s): {sorted(unknown)}")
        return frozenset(
            name for name, spec in self.tokens.items() if spec.owner in wanted
        )

    def validate(self, tokens: object, *, label: str = "authorities") -> tuple[str, ...]:
        """驗證一組 token 皆已登記；未登記即 raise。"""

        if not isinstance(tokens, (list, tuple)):
            raise AuthorityTokenError(f"{label} must be a list")
        parsed = tuple(str(t) for t in tokens)
        unknown = sorted(set(parsed) - self.all_tokens())
        if unknown:
            raise AuthorityTokenError(f"{label} references unknown tokens: {unknown}")
        return parsed


@lru_cache(maxsize=1)
def get_authority_token_registry() -> AuthorityTokenRegistry:
    return AuthorityTokenRegistry.from_path()


def all_authority_tokens() -> frozenset[str]:
    return get_authority_token_registry().all_tokens()


def tokens_for_owner(*owners: str) -> frozenset[str]:
    return get_authority_token_registry().by_owner(*owners)
