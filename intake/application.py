"""Research Action 與圖寫入的 **application service**。

## 為什麼它不在 `mcp_server/`

實測（2026-09-03）：`mcp_server/` 4,016 行有 **79% 不是 MCP**。這一整組
（prepare／apply／finalize／load extraction、圖寫入就緒檢查、provenance 驗證）
是 domain 與 application 邏輯，只是歷史上因為第一個入口是遠端而住進 transport
package——於是 5 個 core 消費端被迫 import 它，其中包含 pq2 待辦池本身。

## 保留的 domain semantics（**不因 MCP 降級而丟掉**）

bounded research mutation｜provenance（storage_permission／canonical hash）｜
immutable review packet｜**content digest ＝ identity**（stale／tampered payload 在
graph mutation 前拒絕）｜**explicit approval before graph mutation**（四個人工 gate 之一）｜
idempotent apply ＋ 逐文件 checkpoint ＋ filesystem-first｜Research Action state machine。

## 降級為 transport 的（**不得升格為 domain invariant**）

MCP server ID｜remote provider session｜action quota／30 天過期／5 MiB 上限｜
mobile two-call workflow｜遠端 Git 限制。它們是 ops 限制，不是 domain 規則。

⚠ **本模組不 import `mcp`**——`tests/test_layer_separation.py` 守著。
"""
from __future__ import annotations
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
import neo4j
from query.graph_context import build_context
from loader.validate import validate as validate_extraction
from loader.load_to_neo4j import (
    DuplicateUrlError,
    check_duplicate_url,
    edge_key,
    evidence_id,
    load as load_to_graph,
)
from loader.edge_resolution import project_edge_keys
from intake.provenance import (
    MAX_EXTRACTION_CHARS,
    ROOT as INTAKE_ROOT,
    canonical_extraction_hash,
    commit_and_push,
    git_preflight,
    inspect_provenance,
    mark_graph_complete,
    pending_intake_files,
    publish_provenance,
    resolve_action_paths,
    sanitize_source_url,
    validate_action_slug,
    validate_doc_id,
    verify_graph_complete,
    write_report,
)
from intake import actions as research_actions

sys.path.insert(0, str(ROOT))

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")

USER = os.environ.get("NEO4J_ROUTINE_USER")

PASSWORD = os.environ.get("NEO4J_ROUTINE_PASSWORD")

TOKEN = os.environ.get("GRAPH_MCP_TOKEN")

PORT = int(os.environ.get("GRAPH_MCP_PORT", "8788"))

GRAPH_SCHEMA_VERSION = "2026-07-16-u3b"

SOURCE_TRACE_MANUAL = ROOT / "skills" / "source-trace" / "SKILL.md"

def _check_server_config() -> None:
    """Fail at server start, while keeping read-only helpers import-testable."""

    if not (USER and PASSWORD):
        raise RuntimeError(
            "需要 .env 設定 NEO4J_ROUTINE_USER / NEO4J_ROUTINE_PASSWORD（最小權限帳號）"
        )
    if not TOKEN or len(TOKEN) < 16:
        raise RuntimeError(
            "需要 .env 設定 GRAPH_MCP_TOKEN（≥16 字元強隨機字串，將內嵌於 URL 路徑）"
        )

def _driver() -> neo4j.Driver:
    return neo4j.GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def _check_graph_write_readiness(driver) -> None:
    """Fail closed before graph writes when migration/materialization is incomplete."""

    with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
        state = session.run(
            """
            OPTIONAL MATCH (state:GraphSchemaState {id: 'stockbotv2'})
            RETURN state.version AS version
            """
        ).single()
        unprojected = session.run(
            """
            MATCH ()-[r]->()
            WHERE r.edge_key IS NOT NULL AND r.projected_at IS NULL
            RETURN count(r) AS count
            """
        ).single()["count"]
        legacy = session.run(
            """
            MATCH ()-[r]->()
            WHERE NOT type(r) IN ['CITES', 'ABOUT'] AND r.edge_key IS NULL
            RETURN count(r) AS count
            """
        ).single()["count"]
        orphaned = session.run(
            """
            MATCH (e)
            WHERE (e:EdgeAssertion OR e:Claim) AND NOT (e)-[:CITES]->(:SourceDoc)
            RETURN count(e) AS count
            """
        ).single()["count"]
    version = state["version"] if state else None
    if version != GRAPH_SCHEMA_VERSION:
        raise RuntimeError(
            f"graph schema is not ready: expected {GRAPH_SCHEMA_VERSION}, got {version!r}"
        )
    if unprojected or legacy or orphaned:
        raise RuntimeError(
            "graph reconciliation is incomplete: "
            f"unprojected={unprojected}, legacy={legacy}, orphaned_evidence={orphaned}"
        )

def _read_source_trace_manual(path: Path = SOURCE_TRACE_MANUAL) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return (
            "追源手冊目前不可用；不要在缺少規則時繼續抽取或入圖。"
            f"請檢查 skills/source-trace/SKILL.md（{type(exc).__name__}: {exc}）。"
        )

def _prepare_extraction_impl(
    extraction_json: str,
    storage_permission: str,
    permission_basis: str,
    *,
    raw_text: str | None = None,
    raw_url: str | None = None,
    raw_excerpt: str | None = None,
    root: Path = INTAKE_ROOT,
) -> dict:
    """Run the complete deterministic intake gate without publishing or writing graph."""

    if not isinstance(extraction_json, str):
        return {"status": "rejected", "error": "extraction_json 必須是 JSON 字串"}
    if len(extraction_json) > MAX_EXTRACTION_CHARS:
        return {"status": "rejected", "error": "extraction 超過 1,000,000 字元限制"}
    try:
        doc = json.loads(extraction_json)
    except json.JSONDecodeError as e:
        return {"status": "rejected", "error": f"不是合法 JSON：{e}"}

    if not isinstance(doc, dict):
        return {"status": "rejected", "error": "extraction JSON 必須是 object"}

    source_doc = doc.get("source_doc")
    if not isinstance(source_doc, dict):
        return {"status": "rejected", "error": "source_doc 是必填 object"}
    doc_id = source_doc.get("doc_id")
    try:
        validate_doc_id(doc_id)
    except ValueError as exc:
        return {"status": "rejected", "error": str(exc)}
    source_doc["storage_permission"] = storage_permission
    source_doc["permission_basis"] = permission_basis
    try:
        if raw_url:
            source_doc["url"] = sanitize_source_url(raw_url)
        elif source_doc.get("url"):
            source_doc["url"] = sanitize_source_url(source_doc["url"])
    except ValueError as exc:
        return {"status": "rejected", "doc_id": doc_id, "error": str(exc)}

    # 驗證（validate() 吃檔案路徑，寫入 temp 檔重用其完整邏輯）
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    try:
        json.dump(doc, tmp, ensure_ascii=False)
        tmp.close()
        try:
            problems = validate_extraction(tmp.name)
        except Exception as e:
            # 驗證器自身異常也必須回成清楚的拒載訊息，不能炸穿成框架錯誤
            return {
                "status": "rejected",
                "doc_id": doc_id,
                "error": (
                    f"驗證器異常（{type(e).__name__}: {e}）；"
                    "請先呼叫 get_extraction_rules 核對格式後重試"
                ),
            }
    finally:
        os.unlink(tmp.name)

    hard_errors = [p for p in problems if not p.startswith("WARN")]
    warnings = [p for p in problems if p.startswith("WARN")]
    if hard_errors:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": "驗證未通過",
            "problems": hard_errors,
        }

    # 公司 registry fail-closed（2026-09-02 對齊 enforcement ①）：validate 對未登記
    # co:* 刻意只 WARN（typo vs 未 onboard 由人分流）——但 openlight 實測證明 WARN
    # 沒人讀。prepare 是核准前最後一站：onboard 契約本來就要求 registry 條目隨包
    # staged（co:proterial／co:jl_mag 先例），這裡把慣例變 enforcement。
    _reg_path = Path(__file__).resolve().parent.parent / "config" / "company_identity.json"
    _registry_ids = {
        str(c.get("company_id"))
        for c in json.loads(_reg_path.read_text(encoding="utf-8")).get("companies") or []
    }
    _unregistered = sorted(
        {
            str(n.get("id"))
            for n in doc.get("nodes") or []
            if str(n.get("id") or "").startswith("co:")
            and str(n.get("id")) not in _registry_ids
        }
    )
    if _unregistered:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": (
                f"公司未登記 registry：{_unregistered}——join-key 契約要求先補 "
                "`config/company_identity.json` 條目（private 公司用 research_ticker null，"
                "見 co:proterial 先例）再 prepare；onboard 包的 registry 條目隨包 staged"
            ),
        }

    # 同 URL 多段驗證提前到 prepare（2026-09-02 ROADMAP 交付）：loader 的
    # DuplicateUrlError 原本在 apply 才炸，而 payload 已凍結、只能重 prepare＋
    # 重新請求核准（2026-09-01～02 實測連踩三次：原 [360][361]、[376]、[394]）。
    # 這裡用 loader 同一套判準先擋；Neo4j 不可用時降級放行——apply 端仍是最終防線，
    # prepare 不因需要圖連線而阻斷離線流程。
    try:
        dup_driver = _driver()
        try:
            with dup_driver.session() as dup_session:
                check_duplicate_url(doc.get("source_doc") or {}, dup_session)
        finally:
            dup_driver.close()
    except DuplicateUrlError as exc:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": (
                "同 URL 多段驗證未通過（prepare 端先擋，免得核准後 apply 才發現）："
                f"{exc}"
            ),
        }
    except Exception:  # noqa: BLE001 — 圖連線不可用時降級，apply 端仍會擋
        pass

    raw_payload = {
        key: value
        for key, value in {
            "raw_text": raw_text,
            "raw_url": raw_url,
            "raw_excerpt": raw_excerpt,
        }.items()
        if value is not None
    }
    try:
        provenance = inspect_provenance(
            doc_id,
            doc,
            raw_payload,
            root=root,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": f"provenance validation rejected: {exc}",
            "finalize_eligible": False,
        }
    if provenance["status"] == "conflict":
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": f"provenance validation rejected: conflicts={provenance['conflicts']}",
            "finalize_eligible": False,
        }
    return {
        "status": "prepared",
        "doc_id": doc_id,
        "document": doc,
        "raw_payload": provenance["normalised_raw"],
        "provenance_status": provenance["status"],
        "warnings": warnings,
    }

def _load_extraction_impl(
    extraction_json: str,
    storage_permission: str,
    permission_basis: str,
    *,
    raw_text: str | None = None,
    raw_url: str | None = None,
    raw_excerpt: str | None = None,
    root: Path = INTAKE_ROOT,
) -> dict:
    prepared = _prepare_extraction_impl(
        extraction_json,
        storage_permission,
        permission_basis,
        raw_text=raw_text,
        raw_url=raw_url,
        raw_excerpt=raw_excerpt,
        root=root,
    )
    if prepared["status"] != "prepared":
        return prepared
    doc_id = prepared["doc_id"]
    doc = prepared["document"]
    raw_payload = prepared["raw_payload"]
    warnings = prepared["warnings"]
    try:
        provenance = publish_provenance(doc_id, doc, raw_payload, root=root)
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": f"provenance publish rejected: {exc}",
            "finalize_eligible": False,
        }

    driver = _driver()
    try:
        _check_graph_write_readiness(driver)
        with driver.session() as session:
            session.execute_write(lambda tx: load_to_graph(doc, tx))
        _verify_loaded_doc(driver, doc)
        affected_edge_keys = {
            edge_key(edge["src_id"], edge["relation"], edge["dst_id"])
            for edge in doc.get("edges", [])
        }
        projection = project_edge_keys(driver, affected_edge_keys)
        mark_graph_complete(doc_id, doc, root=root)
    except Exception as e:
        return {
            "status": "pending_graph",
            "doc_id": doc_id,
            "error": f"{type(e).__name__}: {e}",
            "resolved_paths": provenance["paths"],
            "finalize_eligible": False,
            "warnings": warnings,
        }
    finally:
        driver.close()

    return {
        "status": "loaded_or_already_complete",
        "doc_id": doc_id,
        "resolved_paths": provenance["paths"],
        "open_conflict_ids": projection["open_conflict_ids"],
        "stale_resolution_ids": projection["stale_resolution_ids"],
        "finalize_eligible": provenance["finalize_eligible"],
        "extraction_sha256": canonical_extraction_hash(doc),
        "counts": {
            "nodes": len(doc.get("nodes", [])),
            "edges": len(doc.get("edges", [])),
            "claims": len(doc.get("claims", [])),
        },
        "warnings": warnings,
    }

def _safe_error_message(value: object) -> str:
    message = str(value)
    if TOKEN:
        message = message.replace(TOKEN, "[redacted]")
    message = message.replace("\r", " ").replace("\n", " ")
    return message[:2_000]

def _safe_load_result(result: dict) -> dict:
    """Persist only bounded operational fields, never caller payloads."""

    safe = {
        key: result[key]
        for key in (
            "status",
            "doc_id",
            "resolved_paths",
            "open_conflict_ids",
            "stale_resolution_ids",
            "finalize_eligible",
            "extraction_sha256",
            "counts",
            "warnings",
        )
        if key in result
    }
    if result.get("error"):
        safe["error"] = _safe_error_message(result["error"])
    if result.get("problems"):
        safe["problems"] = [
            _safe_error_message(item) for item in (result.get("problems") or [])[:50]
        ]
    return safe

def _prepare_research_action_impl(
    action_json: str, *, root: Path = INTAKE_ROOT
) -> dict:
    try:
        request = research_actions.parse_action_request(action_json)
    except (ValueError, TypeError) as exc:
        return {"status": "rejected", "error": _safe_error_message(exc)}

    normalized_documents = []
    for index, document in enumerate(request["documents"]):
        prepared = _prepare_extraction_impl(
            document["extraction_json"],
            document["storage_permission"],
            document["permission_basis"],
            raw_text=document.get("raw_text"),
            raw_url=document.get("raw_url"),
            raw_excerpt=document.get("raw_excerpt"),
            root=root,
        )
        if prepared["status"] != "prepared":
            return {
                "status": "rejected",
                "document_index": index,
                "doc_id": prepared.get("doc_id"),
                "error": _safe_error_message(
                    prepared.get("error") or "document validation failed"
                ),
                "problems": [
                    _safe_error_message(item)
                    for item in (prepared.get("problems") or [])[:50]
                ],
            }
        normalized_documents.append(
            {
                "doc_id": prepared["doc_id"],
                "extraction": prepared["document"],
                "raw_payload": prepared["raw_payload"],
                "storage_permission": document["storage_permission"],
                "permission_basis": document["permission_basis"],
                "validation_warnings": prepared["warnings"],
            }
        )

    payload = {
        "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
        "action_slug": request["action_slug"],
        "report": request["report"],
        "documents": normalized_documents,
    }
    if request.get("focus_company_id") is not None:
        payload["focus_company_id"] = request["focus_company_id"]
    try:
        record = research_actions.create_action(payload, root=root)
    except (OSError, RuntimeError, ValueError) as exc:
        return {"status": "rejected", "error": _safe_error_message(exc)}
    return {
        "status": "ready",
        "action_id": record["action_id"],
        "action_digest": record["action_digest"],
        "created_at": record["created_at"],
        "expires_at": record["expires_at"],
        "document_count": len(record["document_manifest"]),
        "review_packet": research_actions.render_review_packet(record),
        "next_action": (
            "Show this exact server-rendered packet to the user. Do not call apply "
            "until the user explicitly approves this action ID."
        ),
    }

def _get_research_action_status_impl(
    action_id: str = "", *, root: Path = INTAKE_ROOT
) -> dict:
    try:
        if not action_id:
            return research_actions.list_action_statuses(root=root)
        return research_actions.action_status(action_id, root=root)
    except FileNotFoundError:
        return {"status": "not_found", "action_id": action_id}
    except (OSError, ValueError) as exc:
        return {
            "status": "rejected",
            "action_id": action_id,
            "error": _safe_error_message(exc),
        }

def _stored_extraction_for_action(document: dict, *, root: Path) -> dict:
    doc_id = validate_doc_id(document["doc_id"])
    if document["storage_permission"] == "local_only":
        path = root / "library" / "private" / "extractions" / f"{doc_id}.json"
    else:
        path = root / "extractions" / f"{doc_id}.json"
    if not path.exists():
        raise ValueError(f"stored extraction missing for completed doc_id: {doc_id}")
    try:
        extraction = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"stored extraction invalid for completed doc_id: {doc_id}") from exc
    if extraction.get("source_doc", {}).get("doc_id") != doc_id:
        raise ValueError(f"stored extraction doc_id mismatch: {doc_id}")
    return extraction

def _verify_action_document_receipt(
    document: dict, execution: dict, *, root: Path
) -> None:
    if execution.get("status") != "complete":
        raise ValueError(f"document checkpoint is incomplete: {document['doc_id']}")
    result = execution.get("result") or {}
    extraction = _stored_extraction_for_action(document, root=root)
    expected_hash = result.get("extraction_sha256")
    if expected_hash != canonical_extraction_hash(extraction):
        raise ValueError(f"document checkpoint hash mismatch: {document['doc_id']}")
    verify_graph_complete(document["doc_id"], extraction, root=root)

def _verify_completed_action(record: dict, *, root: Path) -> None:
    for document, execution in zip(
        record["document_manifest"], record["execution"]["documents"], strict=True
    ):
        _verify_action_document_receipt(document, execution, root=root)
    research_actions.verify_action_reports(record, root=root)

def _apply_response(record: dict, *, replayed: bool = False) -> dict:
    result = dict(record.get("final_result") or {})
    if not result:
        result = {
            "status": record["state"],
            "action_id": record["action_id"],
            "action_digest": record["action_digest"],
        }
    result["state"] = record["state"]
    result["git_status"] = record.get("git", {}).get("status")
    if replayed:
        result["replayed"] = True
    return result

def _sync_source_leads_after_apply(record: Mapping[str, Any]) -> None:
    """apply 成功後把 digest／focus 回寫到綁定的 leads 並推進 applied。

    L16 交付（2026-09-02）：complete-ra 要求 applied lead 帶 `action_digest` 與
    `focus_company_id`，但這兩個值一直只在 apply 端手上——每次都要人手動
    annotate＋advance，漏一次就撞「applied lead 的 action_digest 缺失」。
    分類（digest/focus）從此跟著資料走到消費端。best-effort：leads 檔異常不
    回滾 apply（graph 寫入已 durable），失敗留給既有的手動路徑。
    """
    try:
        from engine_b import leads as leads_mod

        action_id = str(record.get("action_id") or "")
        digest = str(record.get("action_digest") or "")
        payload = record.get("payload") or {}
        focus = str(
            payload.get("focus_company_id") or record.get("focus_company_id") or ""
        )
        if not action_id or not digest:
            return
        store = leads_mod.load()
        touched = False
        for lead in store["leads"].values():
            refs = lead.get("refs") or {}
            if str(refs.get("research_action_id") or "") != action_id:
                continue
            if lead.get("status") != "action_prepared":
                continue
            leads_mod.annotate_refs(
                store,
                lead["lead_id"],
                refs={
                    "action_digest": digest,
                    **({"focus_company_id": focus} if focus else {}),
                },
            )
            leads_mod.advance(store, lead["lead_id"], "applied")
            touched = True
        if touched:
            leads_mod.save(store)
    except Exception as exc:  # noqa: BLE001 — 回寫失敗不動搖 durable apply
        _write_log = logging.getLogger(__name__)
        _write_log.warning("lead sync after apply failed: %s", exc, exc_info=True)

def _apply_research_action_impl(
    action_id: str,
    action_digest: str,
    *,
    root: Path = INTAKE_ROOT,
    load_document=None,
) -> dict:
    try:
        research_actions.validate_action_id(action_id)
        research_actions.validate_action_digest(action_digest)
    except ValueError as exc:
        return {"status": "rejected", "error": _safe_error_message(exc)}
    loader = load_document or _load_extraction_impl

    try:
        lock = research_actions.action_lock(action_id, root=root)
        with lock:
            try:
                record = research_actions.read_action(action_id, root=root)
            except FileNotFoundError:
                return {"status": "not_found", "action_id": action_id}
            except (OSError, ValueError):
                return {
                    "status": "rejected",
                    "action_id": action_id,
                    "error": "Research Action record failed integrity validation",
                }

            if record["action_digest"] != action_digest:
                return {
                    "status": "rejected",
                    "action_id": action_id,
                    "error": "action_digest mismatch; no graph mutation occurred",
                }

            if record["state"] in {"applied", "committed_not_pushed", "pushed"}:
                try:
                    _verify_completed_action(record, root=root)
                except (OSError, ValueError) as exc:
                    return {
                        "status": "rejected",
                        "action_id": action_id,
                        "error": _safe_error_message(exc),
                    }
                return _apply_response(record, replayed=True)

            if record["state"] == "expired":
                return {
                    "status": "expired",
                    "action_id": action_id,
                    "error": "prepare a fresh Research Action before approval",
                }
            if record["state"] == "ready" and _parse_action_time(
                record["expires_at"]
            ) <= datetime.now(timezone.utc):
                return {
                    "status": "expired",
                    "action_id": action_id,
                    "error": "prepare a fresh Research Action before approval",
                }
            if record.get("payload") is None:
                return {
                    "status": "rejected",
                    "action_id": action_id,
                    "error": "Research Action payload is unavailable",
                }

            if record["state"] == "applying":
                record["state"] = (
                    "partial"
                    if any(
                        item.get("status") == "complete"
                        for item in record["execution"]["documents"]
                    )
                    else "ready"
                )
            record["state"] = "applying"
            record["execution"]["last_error"] = None
            record = research_actions.save_action(record, root=root)

            for index, document in enumerate(record["payload"]["documents"]):
                execution = record["execution"]["documents"][index]
                if execution.get("status") == "complete":
                    try:
                        _verify_action_document_receipt(
                            record["document_manifest"][index], execution, root=root
                        )
                    except (OSError, ValueError):
                        execution["status"] = "pending"
                        execution["result"] = None
                    else:
                        continue
                try:
                    result = loader(
                        json.dumps(document["extraction"], ensure_ascii=False),
                        document["storage_permission"],
                        document["permission_basis"],
                        root=root,
                        **document["raw_payload"],
                    )
                except Exception as exc:
                    result = {
                        "status": "internal_error",
                        "doc_id": document["doc_id"],
                        "error": type(exc).__name__,
                    }
                safe_result = _safe_load_result(result)
                execution["result"] = safe_result
                if result.get("status") == "loaded_or_already_complete":
                    execution["status"] = "complete"
                    execution["completed_at"] = datetime.now(timezone.utc).isoformat()
                    record = research_actions.save_action(record, root=root)
                    continue
                execution["status"] = "failed"
                record["state"] = "partial"
                record["execution"]["last_error"] = {
                    "code": "document_not_complete",
                    "doc_id": document["doc_id"],
                    "message": safe_result.get("error") or result.get("status"),
                }
                record = research_actions.save_action(record, root=root)
                return {
                    "status": "partial",
                    "action_id": action_id,
                    "action_digest": action_digest,
                    "completed_document_count": sum(
                        item.get("status") == "complete"
                        for item in record["execution"]["documents"]
                    ),
                    "document_count": len(record["execution"]["documents"]),
                    "failed_doc_id": document["doc_id"],
                    "error": record["execution"]["last_error"],
                    "next_action": "Retry the same action ID and digest after recovery.",
                }

            try:
                for manifest_document, execution in zip(
                    record["document_manifest"],
                    record["execution"]["documents"],
                    strict=True,
                ):
                    _verify_action_document_receipt(
                        manifest_document, execution, root=root
                    )
            except (OSError, ValueError) as exc:
                record["state"] = "partial"
                record["execution"]["last_error"] = {
                    "code": "document_receipt_invalid",
                    "message": _safe_error_message(exc),
                }
                research_actions.save_action(record, root=root)
                return {
                    "status": "partial",
                    "action_id": action_id,
                    "action_digest": action_digest,
                    "completed_document_count": sum(
                        item.get("status") == "complete"
                        for item in record["execution"]["documents"]
                    ),
                    "document_count": len(record["execution"]["documents"]),
                    "error": record["execution"]["last_error"],
                    "next_action": "Repair the durable document receipt, then retry exactly.",
                }

            try:
                report = research_actions.publish_action_reports(record, root=root)
            except (OSError, RuntimeError, ValueError) as exc:
                record["state"] = "partial"
                record["execution"]["report"] = {"status": "failed"}
                record["execution"]["last_error"] = {
                    "code": "report_publish_failed",
                    "message": _safe_error_message(exc),
                }
                research_actions.save_action(record, root=root)
                return {
                    "status": "partial",
                    "action_id": action_id,
                    "action_digest": action_digest,
                    "completed_document_count": len(record["execution"]["documents"]),
                    "document_count": len(record["execution"]["documents"]),
                    "error": record["execution"]["last_error"],
                    "next_action": "Retry the same action; completed documents will not reload.",
                }

            record["execution"]["report"] = report
            research_actions.verify_action_reports(record, root=root)
            eligible_paths = research_actions.eligible_action_paths(record)
            record["git"]["eligible_paths"] = eligible_paths
            record["git"]["status"] = "pending" if eligible_paths else "not_required"
            record["state"] = "applied"
            record["applied_at"] = datetime.now(timezone.utc).isoformat()
            conflict_ids = sorted(
                {
                    conflict_id
                    for item in record["execution"]["documents"]
                    for conflict_id in (
                        (item.get("result") or {}).get("open_conflict_ids") or []
                    )
                }
            )
            record["final_result"] = {
                "status": "applied",
                "action_id": action_id,
                "action_digest": action_digest,
                "document_count": len(record["execution"]["documents"]),
                "open_conflict_ids": conflict_ids,
                "report": report,
                "git_status": record["git"]["status"],
                "next_action": (
                    "Open a local session and publish pending intake."
                    if eligible_paths
                    else "No Git publication is required for this local-only action."
                ),
            }
            record = research_actions.compact_applied_payload(record)
            record = research_actions.save_action(record, root=root)
            _sync_source_leads_after_apply(record)
            return _apply_response(record)
    except research_actions.ActionBusyError:
        return {
            "status": "busy",
            "action_id": action_id,
            "error": "another apply is in progress; query status before retrying",
        }
    except Exception as exc:
        message = (
            _safe_error_message(exc)
            if isinstance(exc, (OSError, RuntimeError, ValueError, KeyError, TypeError))
            else type(exc).__name__
        )
        return {
            "status": "partial",
            "action_id": action_id,
            "action_digest": action_digest,
            "error": {"code": "action_apply_internal", "message": message},
            "next_action": "Query status, then retry the same action ID and digest.",
        }

def _parse_action_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Research Action timestamp has no timezone")
    return parsed.astimezone(timezone.utc)

def _verify_loaded_doc(driver, doc: dict) -> None:
    """Fail closed unless this document's graph identity is observable."""

    doc_id = doc["source_doc"]["doc_id"]
    expected_assertions = {
        evidence_id(doc_id, edge["id"]) for edge in doc.get("edges", [])
    }
    expected_claims = {
        evidence_id(doc_id, claim["id"]) for claim in doc.get("claims", [])
    }
    expected_edges = {
        edge_key(edge["src_id"], edge["relation"], edge["dst_id"])
        for edge in doc.get("edges", [])
    }
    with driver.session() as session:
        source_doc_count = session.run(
            "MATCH (sd:SourceDoc {id: $id}) RETURN count(sd) AS count",
            id=doc_id,
        ).single()["count"]
        assertions = {
            row["id"]
            for row in session.run(
                "MATCH (a:EdgeAssertion) WHERE a.id IN $ids RETURN a.id AS id",
                ids=sorted(expected_assertions),
            )
        }
        claims = {
            row["id"]
            for row in session.run(
                "MATCH (c:Claim) WHERE c.id IN $ids RETURN c.id AS id",
                ids=sorted(expected_claims),
            )
        }
        edges = {
            row["edge_key"]
            for row in session.run(
                """
                MATCH ()-[r]->()
                WHERE r.edge_key IN $edge_keys
                RETURN r.edge_key AS edge_key
                """,
                edge_keys=sorted(expected_edges),
            )
        }
    problems = []
    if source_doc_count != 1:
        problems.append(f"SourceDoc count={source_doc_count}")
    if assertions != expected_assertions:
        problems.append(f"missing EdgeAssertions={sorted(expected_assertions - assertions)}")
    if claims != expected_claims:
        problems.append(f"missing Claims={sorted(expected_claims - claims)}")
    if edges != expected_edges:
        problems.append(f"missing canonical edges={sorted(expected_edges - edges)}")
    if problems:
        raise RuntimeError("graph reconciliation failed: " + "; ".join(problems))

_REQUIRED_REPORT_SECTIONS = (
    "為何此時入圖",
    "文件清單",
    "搜尋過程摘要",
    "L8 確認備註",
)

def _finalize_research_action_impl(
    report_markdown: str,
    action_slug: str,
    commit_headline: str,
    doc_ids: list[str],
    *,
    root: Path = INTAKE_ROOT,
    enabled: bool,
) -> dict:
    if not enabled:
        return {
            "git_status": "not_committed",
            "reason": "remote_finalize_disabled",
            "action": (
                "Set ENABLE_REMOTE_FINALIZE=true only after accepting the remote-push "
                "security boundary and configuring this MCP tool as Needs approval."
            ),
        }
    try:
        validate_action_slug(action_slug)
    except ValueError as exc:
        return {"git_status": "not_committed", "reason": str(exc)}
    if not isinstance(commit_headline, str) or not commit_headline.strip():
        return {"git_status": "not_committed", "reason": "commit_headline is required"}
    if "\n" in commit_headline or "\r" in commit_headline:
        return {
            "git_status": "not_committed",
            "reason": "commit_headline must be one line",
        }
    if not isinstance(doc_ids, list):
        return {"git_status": "not_committed", "reason": "doc_ids must be a list"}
    try:
        manifest = resolve_action_paths(doc_ids, root=root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"git_status": "not_committed", "reason": str(exc)}
    if not manifest["paths"]:
        return {
            "git_status": "not_committed",
            "reason": "no_pending_files",
            "manifest": [],
        }
    missing_sections = [
        section for section in _REQUIRED_REPORT_SECTIONS if section not in report_markdown
    ]
    if missing_sections:
        return {
            "git_status": "not_committed",
            "reason": f"report missing required sections: {missing_sections}",
        }

    preflight = git_preflight(root=root)
    if not preflight["ok"]:
        return {
            "git_status": "not_committed",
            "reason": preflight["reason"],
            "detail": preflight.get("detail"),
        }
    pending = pending_intake_files(root=root)
    manifest_paths = set(manifest["paths"])
    modified_manifest = sorted(manifest_paths & set(pending.get("modified") or []))
    if modified_manifest:
        return {
            "git_status": "not_committed",
            "reason": f"manifest contains modified tracked files: {modified_manifest}",
        }
    pending_warning = {
        "untracked": sorted(set(pending.get("untracked") or []) - manifest_paths),
        "modified": sorted(set(pending.get("modified") or []) - manifest_paths),
        "error": pending.get("error"),
    }

    verified_lines = ["## Server-verified provenance manifest", ""]
    for document in manifest["documents"]:
        verified_lines.append(
            f"- `{document['doc_id']}` — storage_permission=`{document['storage_permission']}`; "
            f"URL={document.get('url') or 'n/a'}; permission_basis: "
            f"{document['permission_basis']}"
        )
    final_report = report_markdown.rstrip() + "\n\n" + "\n".join(verified_lines) + "\n"
    try:
        report_path = write_report(action_slug, final_report, root=root)
        report_relative = report_path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, RuntimeError, ValueError) as exc:
        return {"git_status": "not_committed", "reason": f"report write failed: {exc}"}

    git_result = commit_and_push(
        [*manifest["paths"], report_relative],
        commit_headline,
        root=root,
    )
    secondary_preflight = git_result.get("preflight") or {}
    return {
        "git_status": git_result["status"],
        "commit": git_result.get("commit"),
        "push_error": git_result.get("push_error"),
        "error": git_result.get("error") or secondary_preflight.get("reason"),
        "detail": git_result.get("detail") or secondary_preflight.get("detail"),
        "report_path": report_relative,
        "manifest": manifest["documents"],
        "committed_paths": git_result.get("paths") or [],
        "pending_warning": pending_warning,
    }
