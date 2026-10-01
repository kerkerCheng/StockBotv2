"""Durable, server-owned Research Actions for cross-session mobile intake.

The immutable payload is the approval boundary. Mutable execution and Git
publication receipts live beside it, but never participate in its digest.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import secrets
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from intake.provenance import (
    MAX_EXTRACTION_CHARS,
    MAX_REPORT_CHARS,
    ROOT,
    validate_action_slug,
    validate_doc_id,
    validate_storage_permission,
)


ACTION_PAYLOAD_SCHEMA = "research-action/v1"
ACTION_RECORD_SCHEMA = "research-action-record/v1"
ACTION_ID_RE = re.compile(r"^ra_[0-9a-f]{32}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
REPORT_FIELDS = (
    "title",
    "why_now",
    "findings",
    "search_summary",
    "l8_notes",
    "counterevidence_and_gaps",
)
REPORT_HEADINGS = {
    "why_now": "為何此時入圖",
    "findings": "研究發現",
    "search_summary": "搜尋過程摘要",
    "l8_notes": "L8 確認備註",
    "counterevidence_and_gaps": "反向證據與缺口",
}
REQUEST_FIELDS = {"schema_version", "action_slug", "report", "documents"}
# 選填：這個 graph delta 完成後，唯一要建立／沿用哪個 Decision cohort。
# 從 lead 來的 RA 由綁定 lead 的 refs.focus_company_id 提供；從 decision gap
# work order 來的 RA 沒有 lead 可綁，必須在這裡自己聲明。
# `layer_enumerations`（2026-10-01 Phase 4 Step 4.2a）：「這一包列舉了哪一層的供應商集合、發文者是誰」。
# ⚠ **頂層選填，不進 `report`**——`report` 是 exact fields，放進去會讓既有 138 筆紀錄的 `_validate_record` 全部失效。
REQUEST_OPTIONAL_FIELDS = {"focus_company_id", "layer_enumerations"}
LAYER_ENUMERATION_FIELDS = {"node", "suppliers", "relation", "origin_role"}
MAX_LAYER_ENUMERATIONS = 20
DOCUMENT_REQUIRED_FIELDS = {
    "extraction_json",
    "storage_permission",
    "permission_basis",
}
DOCUMENT_OPTIONAL_FIELDS = {"raw_text", "raw_url", "raw_excerpt"}
NORMALIZED_DOCUMENT_FIELDS = {
    "doc_id",
    "extraction",
    "raw_payload",
    "storage_permission",
    "permission_basis",
    "validation_warnings",
}

MAX_DOCUMENTS = 10
MAX_ACTION_BYTES = 5 * 1024 * 1024
MAX_STAGED_BYTES = 100 * 1024 * 1024
MAX_NONTERMINAL_ACTIONS = 50
MAX_REPORT_FIELD_CHARS = 80_000
MAX_TITLE_CHARS = 500
READY_TTL = timedelta(days=30)
LOCK_TTL = timedelta(minutes=15)
LIST_LIMIT = 25
NONTERMINAL_STATES = {"ready", "applying", "partial"}
ACTIONABLE_STATES = {
    "ready",
    "applying",
    "partial",
    "applied",
    "committed_not_pushed",
}


class ActionBusyError(RuntimeError):
    """Raised when another process owns a live Research Action lock."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_action_digest(payload: dict) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def validate_action_id(action_id: str) -> str:
    if not isinstance(action_id, str) or not ACTION_ID_RE.fullmatch(action_id):
        raise ValueError("invalid action_id")
    return action_id


def validate_action_digest(action_digest: str) -> str:
    if not isinstance(action_digest, str) or not DIGEST_RE.fullmatch(action_digest):
        raise ValueError("invalid action_digest: expected 64 lowercase hex characters")
    return action_digest


def _require_exact_fields(value: dict, expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"unknown={extra}")
        raise ValueError(f"{label} fields invalid: {'; '.join(details)}")


def _require_allowed_fields(
    value: dict, required: set[str], optional: set[str], label: str
) -> None:
    """必填欄位一個不能少，另外只接受明確登記的選填欄位。"""

    missing = sorted(required - set(value))
    extra = sorted(set(value) - required - optional)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"unknown={extra}")
        raise ValueError(f"{label} fields invalid: {'; '.join(details)}")


def _validate_focus_company_id(value: object, *, check_registry: bool = True) -> str:
    """只接受 registry 登記過的 company_id；不接受自由字串。

    `check_registry=False`：讀**已存的紀錄**時只驗形狀——名冊日後改了，舊紀錄不得因此讀不出來
    （R2-a N4 的對稱面：讀舊紀錄不依賴當下的設定檔）。"""

    from identity.registry import get_registry

    if not isinstance(value, str) or not value.strip():
        raise ValueError("focus_company_id must be a non-empty string")
    company_id = value.strip()
    if check_registry and not get_registry().has_company(company_id):
        raise ValueError(f"focus_company_id 未在 registry 登記：{company_id}")
    return company_id


def _vocab_values(key: str) -> tuple[str, ...]:
    """`schema/vocab.json` 的封閉字彙（唯一來源；未登記一律拒收，L16）。讀不到就 fail closed。"""

    try:
        vocab = json.loads((ROOT / "schema" / "vocab.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"schema/vocab.json 讀不到——{key} 無從核對：{exc}") from exc
    values = vocab.get(key)
    if not isinstance(values, list) or not values:
        raise ValueError(f"schema/vocab.json 缺 {key}——無從核對（fail closed）")
    return tuple(str(value) for value in values)


def _validate_layer_enumerations(value: object, *, check_vocab: bool = True) -> list[dict]:
    """`layer_enumerations[]` 的形狀與封閉字彙。**不查圖、不查名冊**——「在本包」的核對依賴當下的名冊，
    只在 prepare 跑一次（`check_layer_enumerations`），否則名冊一改，舊紀錄的驗證就會失敗。

    `check_vocab=False`：讀**已存的紀錄**時只驗形狀（R2-a N4）——字彙檔日後改名或移除某個值，帶著它的舊紀錄
    不得因此讀不出來（publish／status／complete-ra 都讀紀錄）。字彙核對在建立紀錄那一刻做過一次。"""

    if not isinstance(value, list) or not value:
        raise ValueError("layer_enumerations must be a non-empty list")
    if len(value) > MAX_LAYER_ENUMERATIONS:
        raise ValueError(f"layer_enumerations exceeds the {MAX_LAYER_ENUMERATIONS}-item limit")
    relations = _vocab_values("layer_enumeration_relations") if check_vocab else None
    roles = _vocab_values("origin_role") if check_vocab else None
    normalized: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(value):
        label = f"layer_enumerations[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} must be an object")
        _require_exact_fields(item, LAYER_ENUMERATION_FIELDS, label)
        node = item["node"]
        if not isinstance(node, str) or ":" not in node or node.startswith("co:"):
            raise ValueError(f"{label}.node must be a layer node id (prefix:slug, not co:*)")
        suppliers = item["suppliers"]
        if (not isinstance(suppliers, list) or not suppliers
                or not all(isinstance(s, str) and s.startswith("co:") for s in suppliers)):
            raise ValueError(f"{label}.suppliers must be a non-empty list of co:* ids")
        if len(set(suppliers)) != len(suppliers):
            raise ValueError(f"{label}.suppliers has duplicates")
        for field in ("relation", "origin_role"):
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(f"{label}.{field} must be a non-empty string")
        if relations is not None and item["relation"] not in relations:
            raise ValueError(f"{label}.relation 未登記：{item['relation']!r}"
                             f"（schema/vocab.json layer_enumeration_relations：{list(relations)}）")
        if roles is not None and item["origin_role"] not in roles:
            raise ValueError(f"{label}.origin_role 未登記：{item['origin_role']!r}"
                             f"（schema/vocab.json origin_role：{list(roles)}）")
        key = (node, item["relation"])
        if key in seen:
            raise ValueError(f"{label} 與前面一筆重複列舉 {node}（{item['relation']}）")
        seen.add(key)
        normalized.append({"node": node, "suppliers": list(suppliers), "relation": item["relation"],
                           "origin_role": item["origin_role"]})
    return normalized


def check_layer_enumerations(payload: dict, *, registry=None) -> dict:
    """prepare 當下的「在本包」核對（2026-10-01 Phase 4 Step 4.2a）——**不查 Neo4j**，只看這一包的抽取內容。

    每一筆列舉：node 與每家 supplier 都在本包的 nodes；每家至少一條 supplier→node、relation 相符的邊；那條邊
    `source_ids` 指到的任一段引文以 `query.bottleneck.quote_names_company`（名字比對唯一 owner）具名那一家。
    失敗分三種原因報（INV-3，不壓成一個布林）：
    - **名冊無名可比**（那家不在名冊，或沒有 display_name／name_aliases）→ 列進 packet 前置清單，**不拒收**；
    - **名冊的每個寫法都與另一家共用**（`shared_name_forms`；例：`co:openlight`／`co:openlight_photonics` 是同一家的
      兩個 id，plan §14 #11）→ 名字比對對兩家都不算，所以同樣是前置（identity 待決），**不拒收**（R2-a N1：
      原本被當成「引文沒具名」拒收——L12 的形狀）；
    - **引文真的沒具名** → 拒收。
    origin_role 與那份文件 origin 的解析結果不符 → **只警告**。
    ⚠ 結果依賴當下的名冊，所以只在 prepare 跑一次、存成紀錄的收據（`layer_enumeration_check`）；**不得**放進
    `_validate_record`。這是 A1 的機械輔助，**不授權任何入圖**（L15）：入圖仍經 pq2 `ra_admission`。
    """

    from identity.registry import get_registry
    from query.bottleneck import company_id_for_origin, company_name_forms, quote_names_company, shared_name_forms

    reg = registry if registry is not None else get_registry()
    shared = shared_name_forms(reg)
    enumerations = payload.get("layer_enumerations") or []
    documents = payload.get("documents") or []
    nodes = {str(n.get("id")) for d in documents for n in (d["extraction"].get("nodes") or []) if n.get("id")}
    rejections: list[str] = []
    prerequisites: list[str] = []
    warnings: list[str] = []
    results: list[dict] = []
    for index, enum in enumerate(enumerations):
        label = f"layer_enumerations[{index}]（{enum['node']}，{enum['relation']}）"
        if enum["node"] not in nodes:
            rejections.append(f"{label}：node 不在本包的 nodes 裡")
        rows: list[dict] = []
        enum_docs: dict[str, dict] = {}
        for supplier in enum["suppliers"]:
            row: dict = {"company_id": supplier, "edges": [], "status": None}
            if supplier not in nodes:
                rejections.append(f"{label}：{supplier} 不在本包的 nodes 裡")
                row["status"] = "not_in_package"
                rows.append(row)
                continue
            company = reg.company(supplier)
            forms = company_name_forms(company) if company is not None else ()
            has_names = bool(forms)
            # 比對時共用寫法不算（`quote_names_company(..., registry=reg)`）；只剩共用寫法的公司永遠比不到。
            has_own_names = any(form.casefold() not in shared for form in forms)
            for document in documents:
                extraction = document["extraction"]
                quotes = {str(s.get("id")): str(s.get("quote") or "") for s in extraction.get("sources") or []}
                for edge in extraction.get("edges") or []:
                    if (edge.get("src_id") == supplier and edge.get("dst_id") == enum["node"]
                            and edge.get("relation") == enum["relation"]):
                        named = has_own_names and any(quote_names_company(quotes.get(str(sid)), company, registry=reg)
                                                      for sid in edge.get("source_ids") or [])
                        row["edges"].append({"doc_id": document["doc_id"], "edge_id": edge.get("id"), "named": named})
                        enum_docs[document["doc_id"]] = extraction.get("source_doc") or {}
            if not row["edges"]:
                rejections.append(f"{label}：本包沒有 {supplier} —{enum['relation']}→ {enum['node']} 的邊")
                row["status"] = "no_edge"
            elif any(edge["named"] for edge in row["edges"]):
                row["status"] = "named"
            elif not has_names:
                prerequisites.append(f"{label}：{supplier} 在名冊沒有名字可比（不在名冊或沒有 display_name／name_aliases）"
                                     "——先補名冊再核對；不拒收")
                row["status"] = "registry_has_no_name"
            elif not has_own_names:
                prerequisites.append(f"{label}：{supplier} 在名冊的每個寫法都與另一家共用（同一家公司兩個 id？）"
                                     "——名字比對對兩家都不算；先解決 identity 再核對；不拒收")
                row["status"] = "registry_names_shared"
            else:
                docs = "、".join(sorted({edge["doc_id"] for edge in row["edges"]}))
                rejections.append(f"{label}：{supplier} 那條邊的引文沒有具名它（{docs}）")
                row["status"] = "quote_does_not_name"
            rows.append(row)
        suppliers = set(enum["suppliers"])
        origins = []
        for doc_id, source_doc in sorted(enum_docs.items()):
            origin = source_doc.get("origin_entity")
            resolved = company_id_for_origin(origin, reg) if origin else None
            origins.append({"doc_id": doc_id, "origin_entity": origin, "resolved": resolved})
            if enum["origin_role"] == "supplier_self":
                if resolved not in suppliers:
                    warnings.append(f"{label}：origin_role=supplier_self，但 {doc_id} 的 origin「{origin}」"
                                    f"沒有解析到列舉的任一家（{resolved or '解析不到'}）")
            elif resolved in suppliers:
                warnings.append(f"{label}：origin_role={enum['origin_role']}，但 {doc_id} 的 origin「{origin}」"
                                f"就是列舉的供應商 {resolved}——那是供應商自己的文件")
        results.append({"node": enum["node"], "relation": enum["relation"], "origin_role": enum["origin_role"],
                        "suppliers": rows, "origins": origins})
    return {"status": "rejected" if rejections else "ok", "rejections": rejections,
            "prerequisites": prerequisites, "warnings": warnings, "results": results}


def check_sub_language(payload: dict, *, language=None) -> dict | None:
    """prepare 當下：本包每條帶 `substitutability` 的邊，引文含不含可替代性語言（Phase 4 Step 4.4b）。

    **只警告、不拒收**（旗標只印不放閘，L14）；判定問 `query.sub_language`（唯一 owner）。結果依賴當下的字表，
    所以與層列舉同一個規矩：只在建立紀錄時跑一次、存成收據（`sub_language_check`），舊紀錄 render 不變。
    本包沒有任何帶 sub 的邊 → None（不加這一欄）。
    """
    from query.sub_language import get_language, matched_terms, quote_has_sub_language

    lang = language or get_language()
    edges: list[dict] = []
    for document in payload.get("documents") or []:
        extraction = document["extraction"]
        quotes = {str(s.get("id")): str(s.get("quote") or "") for s in extraction.get("sources") or []}
        for edge in extraction.get("edges") or []:
            value = (edge.get("attributes") or {}).get("substitutability")
            if value is None or isinstance(value, bool):
                continue
            texts = [quotes.get(str(sid), "") for sid in edge.get("source_ids") or []]
            edges.append({"doc_id": document["doc_id"], "edge_id": edge.get("id"), "src": edge.get("src_id"),
                          "relation": edge.get("relation"), "dst": edge.get("dst_id"), "substitutability": value,
                          "has_language": quote_has_sub_language(texts, language=lang),
                          "matched": sorted({t for text in texts for t in matched_terms(text, language=lang)})})
    if not edges:
        return None
    warnings = [f"`{e['doc_id']}` 的 {e['src']} —{e['relation']}→ {e['dst']}（sub {e['substitutability']}）："
                "引文不含可替代性語言——只警告、不拒收；請確認這一段真的在談可替代性／替代品認證／排他性"
                for e in edges if not e["has_language"]]
    return {"language": lang.label, "edges": edges, "warnings": warnings}


def _render_sub_language(record: dict) -> list[str]:
    """packet 與 apply 報告共用的「sub 引文核對」一節（沒有收據就整節不印——舊紀錄 render 不變）。"""

    check = record.get("sub_language_check")
    if not check:
        return []
    edges = check.get("edges") or []
    lines = ["", "## sub 引文核對（只警告、不拒收）", ""]
    if check.get("warnings"):
        lines += [f"- ⚠ {warning}" for warning in check["warnings"]]
    else:
        lines.append(f"- 帶 sub 的邊 {len(edges)} 條，引文都含可替代性語言（字表 {check.get('language')}）。")
    lines.append("- 量的是引文措辭，不是 sub 對不對；它**不授權入圖**，也不改任何值。")
    return lines


def _validate_report(report: object) -> dict[str, str]:
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    _require_exact_fields(report, set(REPORT_FIELDS), "report")
    normalized: dict[str, str] = {}
    for field in REPORT_FIELDS:
        value = report[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"report.{field} must be a non-empty string")
        limit = MAX_TITLE_CHARS if field == "title" else MAX_REPORT_FIELD_CHARS
        if len(value) > limit:
            raise ValueError(f"report.{field} exceeds {limit:,} characters")
        normalized[field] = value.strip()
    if sum(len(value) for value in normalized.values()) > MAX_REPORT_CHARS - 10_000:
        raise ValueError("combined report fields exceed the safe rendered report limit")
    return normalized


def parse_action_request(action_json: str) -> dict:
    """Parse the strict external v1 request without performing graph validation."""

    if not isinstance(action_json, str):
        raise ValueError("action_json must be a JSON string")
    if len(action_json.encode("utf-8")) > MAX_ACTION_BYTES:
        raise ValueError("action_json exceeds 5 MiB")
    try:
        request = json.loads(action_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"action_json is not valid JSON: {exc}") from exc
    if not isinstance(request, dict):
        raise ValueError("action_json must decode to an object")
    _require_allowed_fields(request, REQUEST_FIELDS, REQUEST_OPTIONAL_FIELDS, "action")
    if request["schema_version"] != ACTION_PAYLOAD_SCHEMA:
        raise ValueError(
            f"unsupported action schema: expected {ACTION_PAYLOAD_SCHEMA!r}"
        )
    action_slug = validate_action_slug(request["action_slug"])
    report = _validate_report(request["report"])
    focus_company_id = (
        _validate_focus_company_id(request["focus_company_id"])
        if request.get("focus_company_id") is not None
        else None
    )
    layer_enumerations = (
        _validate_layer_enumerations(request["layer_enumerations"])
        if request.get("layer_enumerations") is not None
        else None
    )
    documents = request["documents"]
    if not isinstance(documents, list) or not documents:
        raise ValueError("documents must be a non-empty list")
    if len(documents) > MAX_DOCUMENTS:
        raise ValueError(f"documents exceeds the {MAX_DOCUMENTS}-document limit")

    normalized_documents = []
    allowed = DOCUMENT_REQUIRED_FIELDS | DOCUMENT_OPTIONAL_FIELDS
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise ValueError(f"documents[{index}] must be an object")
        missing = sorted(DOCUMENT_REQUIRED_FIELDS - set(document))
        extra = sorted(set(document) - allowed)
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing={missing}")
            if extra:
                details.append(f"unknown={extra}")
            raise ValueError(
                f"documents[{index}] fields invalid: {'; '.join(details)}"
            )
        extraction_json = document["extraction_json"]
        if not isinstance(extraction_json, str):
            raise ValueError(f"documents[{index}].extraction_json must be a string")
        if len(extraction_json) > MAX_EXTRACTION_CHARS:
            raise ValueError(
                f"documents[{index}].extraction_json exceeds 1,000,000 characters"
            )
        validate_storage_permission(
            document["storage_permission"], document["permission_basis"]
        )
        for key in DOCUMENT_OPTIONAL_FIELDS:
            value = document.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"documents[{index}].{key} must be a string or null")
        normalized_documents.append(copy.deepcopy(document))

    parsed = {
        "schema_version": ACTION_PAYLOAD_SCHEMA,
        "action_slug": action_slug,
        "report": report,
        "documents": normalized_documents,
    }
    if focus_company_id is not None:
        parsed["focus_company_id"] = focus_company_id
    if layer_enumerations is not None:
        parsed["layer_enumerations"] = layer_enumerations
    return parsed


def validate_normalized_payload(payload: object, *, stored: bool = False) -> dict:
    """Validate the canonical internal payload produced by shared intake validation.

    `stored=True`：驗的是**已存紀錄**裡的 payload——只驗形狀，不依賴當下的名冊與字彙檔（R2-a N4）。"""

    if not isinstance(payload, dict):
        raise ValueError("normalized action payload must be an object")
    _require_allowed_fields(
        payload, REQUEST_FIELDS, REQUEST_OPTIONAL_FIELDS, "normalized action"
    )
    if payload["schema_version"] != ACTION_PAYLOAD_SCHEMA:
        raise ValueError("unsupported normalized action schema")
    validate_action_slug(payload["action_slug"])
    _validate_report(payload["report"])
    if payload.get("focus_company_id") is not None:
        _validate_focus_company_id(payload["focus_company_id"], check_registry=not stored)
    if payload.get("layer_enumerations") is not None:
        _validate_layer_enumerations(payload["layer_enumerations"], check_vocab=not stored)
    documents = payload["documents"]
    if not isinstance(documents, list) or not 1 <= len(documents) <= MAX_DOCUMENTS:
        raise ValueError("normalized documents count is invalid")
    seen = set()
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise ValueError(f"normalized documents[{index}] must be an object")
        _require_exact_fields(
            document, NORMALIZED_DOCUMENT_FIELDS, f"normalized documents[{index}]"
        )
        doc_id = validate_doc_id(document["doc_id"])
        if doc_id in seen:
            raise ValueError(f"duplicate document doc_id: {doc_id}")
        seen.add(doc_id)
        extraction = document["extraction"]
        if not isinstance(extraction, dict):
            raise ValueError(f"normalized documents[{index}].extraction must be an object")
        source_doc = extraction.get("source_doc")
        if not isinstance(source_doc, dict) or source_doc.get("doc_id") != doc_id:
            raise ValueError(f"normalized documents[{index}] doc_id mismatch")
        permission = validate_storage_permission(
            document["storage_permission"], document["permission_basis"]
        )
        if source_doc.get("storage_permission") != permission:
            raise ValueError(f"normalized documents[{index}] permission mismatch")
        if source_doc.get("permission_basis") != document["permission_basis"]:
            raise ValueError(f"normalized documents[{index}] permission basis mismatch")
        raw_payload = document["raw_payload"]
        if not isinstance(raw_payload, dict) or set(raw_payload) - DOCUMENT_OPTIONAL_FIELDS:
            raise ValueError(f"normalized documents[{index}].raw_payload is invalid")
        warnings = document["validation_warnings"]
        if not isinstance(warnings, list) or not all(
            isinstance(item, str) for item in warnings
        ):
            raise ValueError(
                f"normalized documents[{index}].validation_warnings is invalid"
            )
    if len(_canonical_bytes(payload)) > MAX_ACTION_BYTES:
        raise ValueError("normalized action exceeds 5 MiB")
    return copy.deepcopy(payload)


def _action_root(root: Path) -> Path:
    return root / "library" / "private" / "research_actions"


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _relative(path: Path, root: Path) -> str:
    if not _inside(path, root):
        raise ValueError(f"path escapes repository root: {path}")
    return path.resolve().relative_to(root.resolve()).as_posix()


def _action_path(action_id: str, root: Path) -> Path:
    validate_action_id(action_id)
    parent = _action_root(root)
    path = parent / f"{action_id}.json"
    if not _inside(path, parent):
        raise ValueError("action path escapes private action root")
    return path


def _atomic_replace_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _write_new_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise RuntimeError("Research Action ID collision") from exc


def _lock_is_stale(path: Path, now: datetime) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        acquired_at = _parse_time(payload["acquired_at"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        except OSError:
            return True
        return now - modified > LOCK_TTL
    return now - acquired_at > LOCK_TTL


@contextmanager
def _exclusive_lock(path: Path, *, now: datetime | None = None) -> Iterator[str]:
    current = now or _now()
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(16)
    payload = json.dumps(
        {"token": token, "pid": os.getpid(), "acquired_at": _iso(current)},
        sort_keys=True,
    )
    for attempt in range(2):
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if attempt == 0 and _lock_is_stale(path, current):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                continue
            raise ActionBusyError("Research Action is already being processed")
        else:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            break
    try:
        yield token
    finally:
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if existing.get("token") == token:
            path.unlink(missing_ok=True)


@contextmanager
def action_lock(
    action_id: str, *, root: Path = ROOT, now: datetime | None = None
) -> Iterator[str]:
    validate_action_id(action_id)
    lock_path = _action_root(root) / "locks" / f"{action_id}.lock"
    with _exclusive_lock(lock_path, now=now) as token:
        yield token


def _validate_record(record: object) -> dict:
    if not isinstance(record, dict):
        raise ValueError("Research Action record must be an object")
    if record.get("schema_version") != ACTION_RECORD_SCHEMA:
        raise ValueError("unsupported Research Action record schema")
    validate_action_id(record.get("action_id"))
    validate_action_digest(record.get("action_digest"))
    if record.get("state") not in {
        "ready",
        "applying",
        "partial",
        "applied",
        "committed_not_pushed",
        "pushed",
        "expired",
    }:
        raise ValueError("unsupported Research Action state")
    _parse_time(record.get("created_at"))
    _parse_time(record.get("updated_at"))
    _parse_time(record.get("expires_at"))
    if not isinstance(record.get("revision"), int) or record["revision"] < 1:
        raise ValueError("invalid Research Action revision")
    if record.get("payload") is not None:
        validate_normalized_payload(record["payload"], stored=True)
        if canonical_action_digest(record["payload"]) != record["action_digest"]:
            raise ValueError("Research Action payload digest mismatch")
    review = record.get("review")
    if review is not None:
        if not isinstance(review, dict):
            raise ValueError("Research Action review must be an object or null")
        if set(review) == {"title"}:
            if not isinstance(review["title"], str) or not review["title"].strip():
                raise ValueError("Research Action tombstone title is invalid")
        else:
            _validate_report(review)
    # apply 後 payload 會被壓縮掉；層列舉與 prepare 當下的核對收據留在紀錄上（Phase 4 Step 4.2a）——
    # 驗收「至少 1 份 applied RA 帶 layer_enumerations 且核對通過」數的就是這兩欄。
    if record.get("layer_enumerations") is not None:
        _validate_layer_enumerations(record["layer_enumerations"], check_vocab=False)
    check = record.get("layer_enumeration_check")
    if check is not None and (not isinstance(check, dict) or check.get("status") != "ok"):
        raise ValueError("Research Action layer enumeration check receipt is invalid")
    sub_check = record.get("sub_language_check")
    if sub_check is not None and (
            not isinstance(sub_check, dict) or not isinstance(sub_check.get("language"), str)
            or not isinstance(sub_check.get("edges"), list) or not isinstance(sub_check.get("warnings"), list)):
        raise ValueError("Research Action sub language check receipt is invalid")

    manifest = record.get("document_manifest")
    if not isinstance(manifest, list) or not manifest:
        raise ValueError("Research Action document manifest is invalid")
    for item in manifest:
        if not isinstance(item, dict):
            raise ValueError("Research Action document manifest item is invalid")
        required = {
            "doc_id",
            "title",
            "url",
            "storage_permission",
            "permission_basis",
            "node_count",
            "edge_count",
            "claim_count",
            "validation_warnings",
        }
        if required - set(item):
            raise ValueError("Research Action document manifest fields are incomplete")
        validate_doc_id(item["doc_id"])
        validate_storage_permission(
            item["storage_permission"], item["permission_basis"]
        )
        if not isinstance(item["title"], str) or not item["title"]:
            raise ValueError("Research Action document title is invalid")
        if item["url"] is not None and not isinstance(item["url"], str):
            raise ValueError("Research Action document URL is invalid")
        if any(
            not isinstance(item[key], int) or item[key] < 0
            for key in ("node_count", "edge_count", "claim_count")
        ):
            raise ValueError("Research Action document counts are invalid")
        if not isinstance(item["validation_warnings"], list) or not all(
            isinstance(warning, str) for warning in item["validation_warnings"]
        ):
            raise ValueError("Research Action document warnings are invalid")

    execution = record.get("execution")
    if not isinstance(execution, dict):
        raise ValueError("Research Action execution receipt is invalid")
    execution_documents = execution.get("documents")
    if not isinstance(execution_documents, list) or len(execution_documents) != len(
        manifest
    ):
        raise ValueError("Research Action execution document receipts are invalid")
    for expected, item in zip(manifest, execution_documents, strict=True):
        if not isinstance(item, dict) or item.get("doc_id") != expected["doc_id"]:
            raise ValueError("Research Action execution document identity is invalid")
        if item.get("status") not in {"pending", "complete", "failed"}:
            raise ValueError("Research Action execution document status is invalid")
        if item.get("result") is not None and not isinstance(item["result"], dict):
            raise ValueError("Research Action execution document result is invalid")
    report_receipt = execution.get("report")
    if not isinstance(report_receipt, dict) or report_receipt.get("status") not in {
        "pending",
        "failed",
        "complete",
    }:
        raise ValueError("Research Action report receipt is invalid")
    if execution.get("last_error") is not None and not isinstance(
        execution["last_error"], dict
    ):
        raise ValueError("Research Action last error is invalid")

    git = record.get("git")
    if not isinstance(git, dict) or git.get("status") not in {
        "waiting_for_apply",
        "not_required",
        "pending",
        "committed_not_pushed",
        "pushed",
    }:
        raise ValueError("Research Action Git receipt is invalid")
    # ⚠ 封閉字彙：一筆 RA 的產出**怎麼進版本庫的**是稽核事實，不是自由字串。
    # `action_commit`＝publisher 自己建的一筆一 commit（帶 Research-Action-ID trailer）；
    # `out_of_band`＝產出已由別的 commit 帶進版本庫（例如一次手動 migration 順手 commit
    # 了 intake 報告），因此**不會有 trailer**。兩者都是已發布，但只有前者可用 trailer
    # 反查——分開記錄，稽核才不必猜。缺值時視為 action_commit（既有紀錄的相容值）。
    if git.get("commit_provenance") is not None and git["commit_provenance"] not in {
        "action_commit",
        "out_of_band",
    }:
        raise ValueError("Research Action commit provenance is invalid")
    if git.get("out_of_band_commits") is not None and not (
        isinstance(git["out_of_band_commits"], list)
        and all(isinstance(item, str) for item in git["out_of_band_commits"])
    ):
        raise ValueError("Research Action out-of-band commit receipt is invalid")
    if not isinstance(git.get("eligible_paths"), list) or not all(
        isinstance(path, str) for path in git["eligible_paths"]
    ):
        raise ValueError("Research Action eligible paths are invalid")
    if git.get("commit") is not None and not isinstance(git["commit"], str):
        raise ValueError("Research Action commit receipt is invalid")
    if record.get("final_result") is not None and not isinstance(
        record["final_result"], dict
    ):
        raise ValueError("Research Action final result is invalid")
    return record


def read_action(action_id: str, *, root: Path = ROOT) -> dict:
    path = _action_path(action_id, root)
    if not path.exists():
        raise FileNotFoundError(f"Research Action not found: {action_id}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Research Action record is not valid JSON") from exc
    return copy.deepcopy(_validate_record(record))


def save_action(record: dict, *, root: Path = ROOT, now: datetime | None = None) -> dict:
    record = copy.deepcopy(_validate_record(record))
    record["revision"] += 1
    record["updated_at"] = _iso(now or _now())
    _validate_record(record)
    _atomic_replace_json(_action_path(record["action_id"], root), record)
    return record


#: 文件清單每行多印的發文者三欄（Phase 4 Step 4.2a）——取值與 `engine_b/todo.py::_ra_graph_impact` 同一條路
#: （抽取 JSON 的 `source_doc`）。只有新紀錄的 manifest 帶這三個 key；舊紀錄沒有，packet 照原樣渲染（不印「未記錄」）。
MANIFEST_PROVENANCE_FIELDS = ("origin_entity", "source_type", "evidence_tier")


def _document_summary(document: dict) -> dict:
    source_doc = document["extraction"].get("source_doc") or {}
    return {
        "doc_id": document["doc_id"],
        "title": source_doc.get("title") or document["doc_id"],
        "url": source_doc.get("url"),
        "storage_permission": document["storage_permission"],
        "permission_basis": document["permission_basis"],
        "node_count": len(document["extraction"].get("nodes") or []),
        "edge_count": len(document["extraction"].get("edges") or []),
        "claim_count": len(document["extraction"].get("claims") or []),
        "validation_warnings": list(document["validation_warnings"]),
        **{field: source_doc.get(field) for field in MANIFEST_PROVENANCE_FIELDS},
    }


def _effective_state(record: dict, now: datetime) -> str:
    if record["state"] == "ready" and now >= _parse_time(record["expires_at"]):
        return "expired"
    return record["state"]


def _age_seconds(record: dict, now: datetime) -> int:
    return max(0, int((now - _parse_time(record["created_at"])).total_seconds()))


def _next_action(state: str, git_status: str | None = None) -> str:
    if state == "ready":
        return "Review the exact packet; apply only after explicit user approval."
    if state in {"applying", "partial"}:
        return "Inspect status and retry the same action ID and digest."
    if state == "expired":
        return "Prepare a fresh Research Action before approval."
    if state == "applied" and git_status == "pending":
        return "Open a local Codex or Claude Code session and publish pending intake."
    if state == "applied" and git_status == "not_required":
        return "No action required; this local-only action is complete."
    if state == "committed_not_pushed":
        return "Retry the local publish command after verifying origin/master."
    if state == "pushed":
        return "No action required."
    if state == "applied" and git_status == "committed_out_of_band":
        return "Already in origin/master via an out-of-band commit; no action required."
    return "Inspect the local Research Action record."


_LAYER_STATUS_LABELS = {
    "named": "引文具名 ✓",
    "registry_has_no_name": "名冊無名可比（前置：先補名冊）",
    "registry_names_shared": "名冊寫法都與另一家共用（前置：identity 待決）",
}


def _provenance_lines(document: dict) -> list[str]:
    """文件清單的「發文者」一行（packet 與 apply 報告共用——R2-a N8：兩處各寫一份就會不一致）。
    只在 manifest 帶這些鍵時印（Step 4.2 之後的新紀錄）；舊紀錄 render 逐字不變。"""

    if not any(field in document for field in MANIFEST_PROVENANCE_FIELDS):
        return []
    return ["  - 發文者：origin=" + " ｜ ".join(
        [str(document.get("origin_entity") or "未記錄"),
         f"source_type={document.get('source_type') or '未記錄'}",
         f"tier={document.get('evidence_tier') or '未記錄'}"])]


def _render_layer_enumerations(record: dict) -> list[str]:
    """packet 的「層列舉」一節：宣告了什麼、prepare 當下核對的結果（沒有宣告就整節不印——舊紀錄 render 不變）。"""

    enumerations = (record.get("payload") or {}).get("layer_enumerations") or record.get("layer_enumerations")
    if not enumerations:
        return []
    check = record.get("layer_enumeration_check") or {}
    by_key = {(r.get("node"), r.get("relation")): r for r in check.get("results") or []}
    lines = ["", "## 層列舉（這一包列舉了哪一層的供應商集合）", ""]
    for enum in enumerations:
        result = by_key.get((enum["node"], enum["relation"])) or {}
        status = {row.get("company_id"): row.get("status") for row in result.get("suppliers") or []}
        suppliers = "、".join(
            f"`{s}`（{_LAYER_STATUS_LABELS.get(status.get(s), status.get(s) or '未核對')}）" for s in enum["suppliers"])
        lines.append(f"- `{enum['node']}` ← {enum['relation']}：{suppliers}；發文者角色 `{enum['origin_role']}`")
        for origin in result.get("origins") or []:
            lines.append(f"  - `{origin.get('doc_id')}` origin「{origin.get('origin_entity') or '未記錄'}」"
                         f"→ {origin.get('resolved') or '解析不到'}")
    for prerequisite in check.get("prerequisites") or []:
        lines.append(f"- 前置：{prerequisite}")
    for warning in check.get("warnings") or []:
        lines.append(f"- ⚠ {warning}")
    lines.append("- 核對只看本包、不查圖；它是機械輔助，**不授權入圖**——入圖仍要這個編號的明確核准。")
    return lines


def render_review_packet(record: dict, *, now: datetime | None = None) -> str | None:
    payload = record.get("payload")
    report = payload.get("report") if payload else record.get("review")
    if not isinstance(report, dict) or set(REPORT_FIELDS) - set(report):
        return None
    documents = record.get("document_manifest") or []
    lines = [
        f"# {report['title']}",
        "",
        f"- Research Action: `{record['action_id']}`",
        f"- Digest: `{record['action_digest']}`",
        f"- Prepared (UTC): `{record['created_at']}`",
        f"- Approval expires (UTC): `{record['expires_at']}`",
    ]
    for field in ("why_now", "findings"):
        lines.extend(["", f"## {REPORT_HEADINGS[field]}", "", report[field]])
    lines.extend(["", "## 文件清單", ""])
    for document in documents:
        counts = (
            f"nodes={document['node_count']}, edges={document['edge_count']}, "
            f"claims={document['claim_count']}"
        )
        lines.append(
            f"- `{document['doc_id']}` — {document['title']}; "
            f"storage=`{document['storage_permission']}`; {counts}"
        )
        lines.extend(_provenance_lines(document))
        if document.get("url"):
            lines.append(f"  - URL: {document['url']}")
        for warning in document.get("validation_warnings") or []:
            lines.append(f"  - Validation warning: {warning}")
    lines.extend(_render_layer_enumerations(record))
    lines.extend(_render_sub_language(record))
    for field in ("search_summary", "l8_notes", "counterevidence_and_gaps"):
        lines.extend(["", f"## {REPORT_HEADINGS[field]}", "", report[field]])
    lines.extend(
        [
            "",
            "## 核准指示",
            "",
            f"若核准，請明確回覆同意套用 `{record['action_id']}`；"
            "session 必須使用上方完整 digest 呼叫 apply。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _compact_expired_actions(root: Path, now: datetime) -> int:
    parent = _action_root(root)
    if not parent.exists():
        return 0
    compacted = 0
    lock_root = parent / "locks"
    for path in sorted(parent.glob("ra_*.json")):
        action_id = path.stem
        if (lock_root / f"{action_id}.lock").exists():
            continue
        try:
            record = read_action(action_id, root=root)
        except (OSError, ValueError):
            continue
        if (
            record["state"] == "ready"
            and record.get("payload") is not None
            and now >= _parse_time(record["expires_at"])
        ):
            report = record["payload"]["report"]
            record["state"] = "expired"
            record["review"] = {"title": report["title"]}
            record["payload"] = None
            record["compacted_at"] = _iso(now)
            save_action(record, root=root, now=now)
            compacted += 1
    return compacted


def cleanup_expired_actions(
    *, root: Path = ROOT, now: datetime | None = None
) -> dict:
    """Compact expired, never-applied payloads without touching graph or Git."""

    current = now or _now()
    parent = _action_root(root)
    with _exclusive_lock(parent / "locks" / ".store.lock", now=current):
        compacted = _compact_expired_actions(root, current)
    return {"status": "ok", "compacted_count": compacted}


def _quota_usage(root: Path) -> tuple[int, int]:
    count = 0
    total_bytes = 0
    parent = _action_root(root)
    if not parent.exists():
        return count, total_bytes
    for path in parent.glob("ra_*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            _validate_record(record)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if record["state"] in NONTERMINAL_STATES and record.get("payload") is not None:
            count += 1
            total_bytes += len(_canonical_bytes(record["payload"]))
    return count, total_bytes


def create_action(
    payload: dict, *, root: Path = ROOT, now: datetime | None = None
) -> dict:
    """Persist a validated immutable action and return its full record."""

    current = now or _now()
    normalized = validate_normalized_payload(payload)
    # sub 引文核對（Phase 4 Step 4.4b）：只警告、不拒收；依賴當下字表，所以同樣在這一刻跑一次、存成收據。
    sub_check = check_sub_language(normalized)
    layer_check = None
    if normalized.get("layer_enumerations"):
        # 「在本包」核對在建立紀錄的這一刻跑一次、存成收據（依賴當下名冊，不得放進 `_validate_record`）。
        layer_check = check_layer_enumerations(normalized)
        if layer_check["status"] != "ok":
            raise ValueError("layer_enumerations 核對失敗：" + "；".join(layer_check["rejections"]))
    payload_bytes = len(_canonical_bytes(normalized))
    parent = _action_root(root)
    with _exclusive_lock(parent / "locks" / ".store.lock", now=current):
        _compact_expired_actions(root, current)
        active_count, staged_bytes = _quota_usage(root)
        if active_count >= MAX_NONTERMINAL_ACTIONS:
            raise ValueError(
                "Research Action staging is full (50 nonterminal actions); "
                "apply pending actions or run "
                "`python scripts/commit_pending_intake.py --cleanup-expired` first"
            )
        if staged_bytes + payload_bytes > MAX_STAGED_BYTES:
            raise ValueError(
                "Research Action staging exceeds 100 MiB; apply pending actions or run "
                "`python scripts/commit_pending_intake.py --cleanup-expired` before "
                "preparing another"
            )
        action_id = f"ra_{secrets.token_hex(16)}"
        created_at = _iso(current)
        expires_at = _iso(current + READY_TTL)
        manifest = [_document_summary(item) for item in normalized["documents"]]
        has_repo = any(
            item["storage_permission"] != "local_only" for item in manifest
        )
        record = {
            "schema_version": ACTION_RECORD_SCHEMA,
            "action_id": action_id,
            "action_digest": canonical_action_digest(normalized),
            "state": "ready",
            "created_at": created_at,
            "updated_at": created_at,
            "expires_at": expires_at,
            "revision": 1,
            "payload": normalized,
            "review": None,
            "document_manifest": manifest,
            "execution": {
                "documents": [
                    {
                        "doc_id": item["doc_id"],
                        "status": "pending",
                        "result": None,
                    }
                    for item in manifest
                ],
                "report": {"status": "pending"},
                "last_error": None,
            },
            "git": {
                "status": "waiting_for_apply" if has_repo else "not_required",
                "eligible_paths": [],
                "commit": None,
            },
        }
        if layer_check is not None:
            record["layer_enumeration_check"] = layer_check
        if sub_check is not None:
            record["sub_language_check"] = sub_check
        _write_new_json(_action_path(action_id, root), record)
    return copy.deepcopy(record)


def compact_applied_payload(record: dict) -> dict:
    """Drop duplicated source bodies after durable apply receipts exist."""

    if record.get("state") != "applied":
        raise ValueError("only an applied action can compact its payload")
    payload = record.get("payload")
    if payload is None:
        return record
    if record.get("execution", {}).get("report", {}).get("status") != "complete":
        raise ValueError("cannot compact before report publication completes")
    if any(
        item.get("status") != "complete"
        for item in record.get("execution", {}).get("documents", [])
    ):
        raise ValueError("cannot compact before every document completes")
    record["review"] = copy.deepcopy(payload["report"])
    # focus_company_id 是 Decision handoff 的收據，不是可重建的來源正文——compaction
    # 丟掉它，pq2 結案時就再也查不到「這批 delta 要沿用哪個 cohort」。從 lead 來的
    # RA 還能回頭問 lead，decision gap 來的 RA 沒有 lead 可問，會直接卡死。
    if payload.get("focus_company_id"):
        record["focus_company_id"] = payload["focus_company_id"]
    # 同一個理由：層列舉是「這一包列舉了哪一層」的收據，壓縮掉就再也驗不了 Phase 4 的驗收（packet 那一列）。
    if payload.get("layer_enumerations"):
        record["layer_enumerations"] = copy.deepcopy(payload["layer_enumerations"])
    record["payload"] = None
    record["compacted_at"] = _iso(_now())
    return record


def _safe_execution(record: dict) -> dict:
    return {
        "documents": [
            {
                "doc_id": item.get("doc_id"),
                "status": item.get("status"),
                "open_conflict_ids": (
                    (item.get("result") or {}).get("open_conflict_ids") or []
                ),
            }
            for item in record.get("execution", {}).get("documents", [])
        ],
        "report": copy.deepcopy(record.get("execution", {}).get("report") or {}),
        "last_error": copy.deepcopy(record.get("execution", {}).get("last_error")),
    }


def action_status(
    action_id: str, *, root: Path = ROOT, now: datetime | None = None
) -> dict:
    current = now or _now()
    record = read_action(action_id, root=root)
    state = _effective_state(record, current)
    completed = sum(
        item.get("status") == "complete"
        for item in record.get("execution", {}).get("documents", [])
    )
    return {
        "status": "ok",
        "action_id": action_id,
        "action_digest": record["action_digest"],
        "state": state,
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "expires_at": record["expires_at"],
        "age_seconds": _age_seconds(record, current),
        "title": (
            (record.get("payload") or {}).get("report", {}).get("title")
            or (record.get("review") or {}).get("title")
        ),
        "document_count": len(record.get("document_manifest") or []),
        "completed_document_count": completed,
        "documents": copy.deepcopy(record.get("document_manifest") or []),
        "execution": _safe_execution(record),
        "git": copy.deepcopy(record.get("git") or {}),
        "next_action": _next_action(state, (record.get("git") or {}).get("status")),
        "review_packet": render_review_packet(record, now=current),
    }


def list_action_statuses(
    *, root: Path = ROOT, now: datetime | None = None, limit: int = LIST_LIMIT
) -> dict:
    current = now or _now()
    if not isinstance(limit, int) or not 1 <= limit <= LIST_LIMIT:
        raise ValueError(f"limit must be between 1 and {LIST_LIMIT}")
    rows = []
    parent = _action_root(root)
    for path in parent.glob("ra_*.json") if parent.exists() else []:
        try:
            record = read_action(path.stem, root=root)
            state = _effective_state(record, current)
        except (OSError, ValueError):
            continue
        if state not in ACTIONABLE_STATES:
            continue
        git_status = (record.get("git") or {}).get("status")
        if state == "applied" and git_status != "pending":
            continue
        title = (
            (record.get("payload") or {}).get("report", {}).get("title")
            or (record.get("review") or {}).get("title")
        )
        completed = sum(
            item.get("status") == "complete"
            for item in record.get("execution", {}).get("documents", [])
        )
        rows.append(
            {
                "action_id": record["action_id"],
                "title": title,
                "state": state,
                "created_at": record["created_at"],
                "updated_at": record["updated_at"],
                "age_seconds": _age_seconds(record, current),
                "digest_prefix": record["action_digest"][:12],
                "document_count": len(record.get("document_manifest") or []),
                "completed_document_count": completed,
                "next_action": _next_action(
                    state, git_status
                ),
            }
        )
    rows.sort(key=lambda item: item["updated_at"], reverse=True)
    return {"status": "ok", "count": min(len(rows), limit), "actions": rows[:limit]}


def count_action_states(*, root: Path = ROOT, now: datetime | None = None) -> dict:
    current = now or _now()
    counts = {
        "ready_for_approval": 0,
        "partial_apply": 0,
        "uncommitted": 0,
        "committed_not_pushed": 0,
    }
    parent = _action_root(root)
    for path in parent.glob("ra_*.json") if parent.exists() else []:
        try:
            record = read_action(path.stem, root=root)
            state = _effective_state(record, current)
        except (OSError, ValueError):
            continue
        if state == "ready":
            counts["ready_for_approval"] += 1
        elif state in {"applying", "partial"}:
            counts["partial_apply"] += 1
        elif state == "applied" and record.get("git", {}).get("status") == "pending":
            counts["uncommitted"] += 1
        elif state == "committed_not_pushed":
            counts["committed_not_pushed"] += 1
    counts["total"] = sum(counts.values())
    return counts


def _write_exact(path: Path, content: str) -> tuple[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != content:
            raise ValueError(f"no-clobber report conflict at {path.name}")
    else:
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if path.read_text(encoding="utf-8") != content:
                raise ValueError(f"no-clobber report conflict at {path.name}")
    return path.as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()


def _full_report(record: dict) -> str:
    payload = record.get("payload")
    report = payload.get("report") if payload else record.get("review")
    if not isinstance(report, dict) or set(REPORT_FIELDS) - set(report):
        raise ValueError("Research Action review fields are unavailable")
    lines = [
        f"# {report['title']}",
        "",
        f"- Research Action: `{record['action_id']}`",
        f"- Approved digest: `{record['action_digest']}`",
        f"- Prepared (UTC): `{record['created_at']}`",
    ]
    for field in ("why_now", "findings"):
        lines.extend(["", f"## {REPORT_HEADINGS[field]}", "", report[field]])
    lines.extend(["", "## 文件清單", ""])
    for document in record.get("document_manifest") or []:
        counts = (
            f"nodes={document['node_count']}, edges={document['edge_count']}, "
            f"claims={document['claim_count']}"
        )
        lines.append(
            f"- `{document['doc_id']}` — {document['title']}; "
            f"storage=`{document['storage_permission']}`; {counts}"
        )
        lines.extend(_provenance_lines(document))
        if document.get("url"):
            lines.append(f"  - URL: {document['url']}")
        for warning in document.get("validation_warnings") or []:
            lines.append(f"  - Validation warning: {warning}")
    lines.extend(_render_layer_enumerations(record))
    lines.extend(_render_sub_language(record))
    for field in ("search_summary", "l8_notes", "counterevidence_and_gaps"):
        lines.extend(["", f"## {REPORT_HEADINGS[field]}", "", report[field]])

    conflict_ids = sorted(
        {
            conflict_id
            for item in record["execution"]["documents"]
            for conflict_id in ((item.get("result") or {}).get("open_conflict_ids") or [])
        }
    )
    lines.extend(["", "## Server-verified apply receipt", ""])
    lines.append(f"- Applied documents: {len(record['document_manifest'])}")
    lines.append(
        "- Open graph conflict IDs: "
        + (", ".join(f"`{item}`" for item in conflict_ids) if conflict_ids else "none")
    )
    for document, execution in zip(
        record["document_manifest"], record["execution"]["documents"], strict=True
    ):
        result = execution.get("result") or {}
        lines.append(
            f"- `{document['doc_id']}` — graph status=`{result.get('status')}`; "
            f"storage=`{document['storage_permission']}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def _redacted_stub(record: dict) -> str:
    eligible = [
        item
        for item in record["document_manifest"]
        if item["storage_permission"] != "local_only"
    ]
    lines = [
        f"# Research Action {record['action_id']}",
        "",
        "This server-generated ledger stub intentionally omits all client-authored "
        "report text because the action also contains local-only material.",
        "",
        f"- Action digest: `{record['action_digest']}`",
        f"- Created (UTC): `{record['created_at']}`",
        "- Repo-eligible document IDs:",
    ]
    lines.extend(
        f"  - `{item['doc_id']}` (`{item['storage_permission']}`)" for item in eligible
    )
    return "\n".join(lines).rstrip() + "\n"


def publish_action_reports(record: dict, *, root: Path = ROOT) -> dict:
    """Publish deterministic full/private reports and a mixed-action safe stub."""

    _validate_record(record)
    if record["state"] not in {"applying", "partial"}:
        raise ValueError("reports can only publish while an action is applying or partial")
    if any(item.get("status") != "complete" for item in record["execution"]["documents"]):
        raise ValueError("reports cannot publish before every document completes")
    permissions = {
        item["storage_permission"] for item in record["document_manifest"]
    }
    has_local = "local_only" in permissions
    has_repo = bool(permissions - {"local_only"})
    date = _parse_time(record["created_at"]).date().isoformat()
    filename = f"{date}-{record['action_id']}.md"
    result = {
        "status": "complete",
        "public_path": None,
        "public_sha256": None,
        "private_path": None,
        "private_sha256": None,
    }
    full = _full_report(record)
    if has_local:
        private_path = root / "library" / "private" / "intake" / filename
        _, digest = _write_exact(private_path, full)
        result["private_path"] = _relative(private_path, root)
        result["private_sha256"] = digest
    else:
        public_path = root / "library" / "intake" / filename
        _, digest = _write_exact(public_path, full)
        result["public_path"] = _relative(public_path, root)
        result["public_sha256"] = digest
    if has_local and has_repo:
        public_path = root / "library" / "intake" / filename
        _, digest = _write_exact(public_path, _redacted_stub(record))
        result["public_path"] = _relative(public_path, root)
        result["public_sha256"] = digest
    return result


def verify_action_reports(record: dict, *, root: Path = ROOT) -> None:
    report = record.get("execution", {}).get("report") or {}
    if report.get("status") != "complete":
        raise ValueError("Research Action report receipt is incomplete")
    for path_key, digest_key in (
        ("public_path", "public_sha256"),
        ("private_path", "private_sha256"),
    ):
        relative = report.get(path_key)
        expected = report.get(digest_key)
        if not relative:
            continue
        path = root / relative
        if not _inside(path, root) or not path.exists():
            raise ValueError(f"Research Action report is missing: {path_key}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Research Action report receipt is stale: {path_key}")


def eligible_action_paths(record: dict) -> list[str]:
    paths = []
    for document, execution in zip(
        record.get("document_manifest") or [],
        record.get("execution", {}).get("documents") or [],
        strict=True,
    ):
        if document["storage_permission"] == "local_only":
            continue
        paths.extend((execution.get("result") or {}).get("resolved_paths") or [])
    public_report = (record.get("execution", {}).get("report") or {}).get("public_path")
    if public_report:
        paths.append(public_report)
    return sorted(set(paths))


def iter_actions(*, root: Path = ROOT) -> Iterator[dict]:
    parent = _action_root(root)
    paths = sorted(parent.glob("ra_*.json")) if parent.exists() else []
    for path in paths:
        try:
            yield read_action(path.stem, root=root)
        except (OSError, ValueError):
            continue
