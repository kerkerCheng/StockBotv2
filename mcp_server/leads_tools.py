"""Narrow MCP leads surface：讓 chat 驅動 pending leads 狀態（plan U2/R8）。

get_pending_leads（唯讀 priority 佇列）＋ record_lead_decision（triage/advance，
寫後由本機 MCP server 窄 pathset commit+push，cloud 每天讀到最新）。

不變式：leads 狀態只是**注意力 metadata**，永不影響 evidence tier、decision 或
圖。這裡的寫入只碰 leads.json，圖 admission 走 apply_research_action、provenance
帳本走本機 publisher。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from engine_b import leads, priority


def _tracked(value: Any) -> frozenset[str]:
    if isinstance(value, str):
        return frozenset(t.strip().upper() for t in value.split(",") if t.strip())
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(t).strip().upper() for t in value if str(t).strip())
    return frozenset()


def get_pending_leads_core(
    *,
    leads_path: Path | str | None = None,
    tracked_tickers: Any = None,
    limit: int = 50,
    loader: Callable[[Any], dict] | None = None,
) -> dict[str, Any]:
    """回 priority 排序的佇列摘要 + harvest_log + 狀態計數（redacted）。"""
    load = loader or leads.load
    store = load(leads_path or leads.DEFAULT_LEADS_PATH)
    tracked = _tracked(tracked_tickers)
    ranked = priority.rank_leads(store["leads"].values(), tracked_tickers=tracked)
    items = [
        {
            "lead_id": l["lead_id"],
            "priority": rank.label,
            "status": l["status"],
            "source": l["source"],
            "title": l.get("title") or "",
            "url": l.get("url") or "",
            "published_at": l.get("published_at"),
            "triage": l.get("triage"),
        }
        for rank, l in ranked[: max(0, int(limit))]
    ]
    return {
        "counts": leads.status_counts(store),
        "classification_health": {
            "status": "ok" if not (gaps := leads.classification_gaps(store)) else "error",
            "active_unclassified_count": len(gaps),
            "items": gaps,
        },
        "leads": items,
        "harvest_log": store.get("harvest_log", [])[-10:],
        "unresolved_harvest_failures": leads.unresolved_harvest_failures(store),
    }


def record_lead_decision_core(
    *,
    lead_id: str,
    op: str,
    go: bool = True,
    tier: int = 4,
    reason: str = "",
    priority_flags: Mapping[str, Any] | None = None,
    content_type: str = "",
    decision_impact: str = "",
    payment_direction: str = "",
    classification_reason: str = "",
    to_status: str = "",
    ref: str | None = None,
    leads_path: Path | str | None = None,
    loader: Callable[[Any], dict] | None = None,
    saver: Callable[[dict, Any], None] | None = None,
    committer: Callable[..., dict] | None = None,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """triage 或 advance 一則 lead，寫檔後窄 pathset commit+push。

    op="triage"（PASS 另需 content_type／decision_impact；capital_commitment 需
    payment_direction）｜op="advance"（用 to_status/ref）。
    committer 可注入供測試（預設 leads_git.commit_and_push_leads）。
    """
    path = leads_path or leads.DEFAULT_LEADS_PATH
    load = loader or leads.load
    save = saver or leads.save
    store = load(path)
    try:
        if op == "triage":
            classification = None
            supplied = any((content_type, decision_impact, payment_direction, classification_reason))
            if go:
                if not content_type or not decision_impact:
                    raise ValueError(
                        "PASS 必須附 content_type 與 decision_impact"
                    )
                classification = {
                    "content_type": content_type,
                    "decision_impact": decision_impact,
                }
                if payment_direction:
                    classification["payment_direction"] = payment_direction
                if classification_reason:
                    classification["reason"] = classification_reason
            elif supplied:
                raise ValueError("FILTER／no-go 不接受 classification")
            lead = leads.triage(
                store, lead_id, go=bool(go), tier=int(tier),
                reason=str(reason), priority_flags=dict(priority_flags or {}),
                classification=classification,
            )
        elif op == "advance":
            refs = None
            if ref:
                key, _, value = str(ref).partition("=")
                if key:
                    refs = {key: value}
            lead = leads.advance(store, lead_id, str(to_status), ref=refs)
        else:
            return {"status": "invalid_op", "note": "op 必須是 triage 或 advance"}
    except leads.LeadStateError:
        return {"status": "illegal_transition", "lead_id": lead_id}
    except (ValueError, KeyError):
        return {"status": "invalid_request"}

    save(store, path)

    commit = committer
    if commit is None:
        from mcp_server import leads_git

        commit = leads_git.commit_and_push_leads
    root = repo_root or Path(__file__).resolve().parent.parent
    git_result = commit(root, message=f"chore(leads): {op} {lead_id[:16]} (via MCP)")
    return {
        "status": "recorded",
        "lead_id": lead_id,
        "new_status": lead["status"],
        "sync": git_result,
    }
