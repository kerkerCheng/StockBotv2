"""非公司實體的 canonical-id registry（`config/entity_aliases.json` 的唯一 loader）。

公司走 `identity/registry.py`＋`config/company_identity.json`（INV-1）；**非公司實體
從前什麼都沒有**——每份抽取的 LLM 各猜各的 id，loader 照收，事後靠手寫 migration
腳本合併。三個 owner，沒有一個是 SSOT，於是同一層被安靜攤成 2～6 個節點。

本模組只做一件事：**把 alias id 解析成 canonical id**。它不判斷「這兩個東西是不是
同一個」——那是研究判斷，門檻與載體都在 pq2（L15：解析與權限分開，權限那一側永遠
deterministic 且要人核准）。這裡只接受**名稱逐字相同**這種機械可驗的登記。

載入時驗封閉性，任何衝突直接 raise——一個解析不到或互相打架的 registry 比沒有更糟。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Mapping

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "entity_aliases.json"

SCHEMA_VERSION = "entity-aliases-v1"

#: 允許登記的 id 前綴。公司刻意不在內——它有自己的 registry，兩套 identity authority
#: 混在一起就會出現「同一家公司在兩個地方有不同答案」。
ENTITY_PREFIXES = ("tech:", "mat:", "prod:", "std:")

#: 登記依據的封閉字彙。目前只有一種，且刻意只有一種：機械可驗。
#: 要放寬到語意判斷，必須先有一個帶核准 receipt 的載體，不是在這裡多加一個值。
ALLOWED_BASIS = frozenset({"name_identical"})


class EntityAliasError(ValueError):
    """registry 本身不合法（衝突、前綴不對、basis 未登記）。"""


def _validate(raw: Mapping) -> dict[str, dict]:
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise EntityAliasError(
            f"entity_aliases schema_version 必須是 {SCHEMA_VERSION}，"
            f"收到 {raw.get('schema_version')!r}"
        )
    canonical = raw.get("canonical")
    if not isinstance(canonical, dict):
        raise EntityAliasError("entity_aliases 缺少 canonical 區塊")

    seen: dict[str, str] = {}
    for canonical_id, entry in canonical.items():
        if not any(canonical_id.startswith(p) for p in ENTITY_PREFIXES):
            raise EntityAliasError(
                f"{canonical_id} 前綴不在 {ENTITY_PREFIXES}；公司走 company_identity.json"
            )
        if entry.get("basis") not in ALLOWED_BASIS:
            raise EntityAliasError(
                f"{canonical_id} 的 basis={entry.get('basis')!r} 未登記"
                f"（目前只接受 {sorted(ALLOWED_BASIS)}——語意判斷走 pq2，不在這裡）"
            )
        if canonical_id in seen:
            raise EntityAliasError(f"{canonical_id} 重複登記")
        seen[canonical_id] = canonical_id
        for alias in entry.get("aliases") or ():
            if not any(alias.startswith(p) for p in ENTITY_PREFIXES):
                raise EntityAliasError(f"alias {alias} 前綴不在 {ENTITY_PREFIXES}")
            if alias == canonical_id:
                raise EntityAliasError(f"{canonical_id} 不能是自己的 alias")
            if alias in seen:
                raise EntityAliasError(
                    f"alias {alias} 已經指向 {seen[alias]}——一個 id 不能有兩個 canonical"
                )
            seen[alias] = canonical_id
    return dict(canonical)


@lru_cache(maxsize=1)
def _load(path: str) -> tuple[dict[str, dict], dict[str, str]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    canonical = _validate(raw)
    lookup = {}
    for canonical_id, entry in canonical.items():
        lookup[canonical_id] = canonical_id
        for alias in entry.get("aliases") or ():
            lookup[alias] = canonical_id
    return canonical, lookup


def load(path: Path | None = None) -> dict[str, dict]:
    """canonical 區塊的 copy。"""

    canonical, _ = _load(str(path or CONFIG_PATH))
    return {k: dict(v) for k, v in canonical.items()}


def resolve(entity_id: str, *, path: Path | None = None) -> str:
    """alias → canonical。**未登記的 id 原樣回傳**，不是錯誤。

    ⚠ 這是刻意的（使用者 2026-09-10 定案）：擋下未登記的新實體等於停掉自動抽取，
    因為世界一直在長出新的 tech 節點。放行的代價是「可能又造了一個同義 id」，
    所以放行必須配一個看得見的補償控制——`unregistered_entity_ids()` 讓每一份載入
    都能報出它引入了哪些沒登記過的 id，而不是安靜沉底（AGENTS「放行與收緊必須同時發生」）。
    """

    _, lookup = _load(str(path or CONFIG_PATH))
    return lookup.get(entity_id, entity_id)


def is_registered(entity_id: str, *, path: Path | None = None) -> bool:
    _, lookup = _load(str(path or CONFIG_PATH))
    return entity_id in lookup


def unregistered_entity_ids(
    entity_ids, *, path: Path | None = None
) -> list[str]:
    """這批 id 裡有哪些沒在 registry 出現過（去重、排序）。

    它**不代表錯誤**——大多數是真的新實體。它的用途是讓「又造了一個同義 id」這件事
    有地方會說話；沒有這個報告，放行就等於安靜沉底。
    """

    _, lookup = _load(str(path or CONFIG_PATH))
    return sorted(
        {
            entity_id
            for entity_id in entity_ids
            if any(entity_id.startswith(p) for p in ENTITY_PREFIXES)
            and entity_id not in lookup
        }
    )


def resolve_document(doc: dict, *, path: Path | None = None) -> dict:
    """把一份抽取文件裡所有非公司實體 id 換成 canonical，回傳改寫紀錄。

    涵蓋 node id、edge 的 src/dst，以及指向 node 的 claim subject——**漏掉任何一處，
    節點會被合併但邊還指著舊 id**，那比不合併更糟（會產生指不到的端點）。
    claim 的 subject 也可能是 edge 的 local id，那個不動。
    """

    remapped: dict[str, str] = {}

    def _fix(value):
        if not isinstance(value, str):
            return value
        canonical_id = resolve(value, path=path)
        if canonical_id != value:
            remapped[value] = canonical_id
        return canonical_id

    node_local_ids = {n.get("id") for n in doc.get("nodes", []) or ()}
    for node in doc.get("nodes", []) or ():
        node["id"] = _fix(node.get("id"))
    for edge in doc.get("edges", []) or ():
        edge["src_id"] = _fix(edge.get("src_id"))
        edge["dst_id"] = _fix(edge.get("dst_id"))
    for claim in doc.get("claims", []) or ():
        subject = claim.get("subject_id")
        # 只改指向 node 的 subject；指向 edge local id 的不碰。
        if isinstance(subject, str) and subject in node_local_ids:
            claim["subject_id"] = _fix(subject)
        elif isinstance(subject, str) and any(
            subject.startswith(p) for p in ENTITY_PREFIXES
        ):
            claim["subject_id"] = _fix(subject)

    all_ids = [n.get("id") for n in doc.get("nodes", []) or ()]
    for edge in doc.get("edges", []) or ():
        all_ids += [edge.get("src_id"), edge.get("dst_id")]

    return {
        "doc": doc,
        "remapped": dict(remapped),
        "unregistered": unregistered_entity_ids(
            [i for i in all_ids if isinstance(i, str)], path=path
        ),
    }
