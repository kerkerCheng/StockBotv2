"""截圖假設層（hypothesis overlay）——追不到原檔的 lead 的「假設為真」機制。

設計依 docs/brainstorms/2026-08-31-unverified-screenshot-leads-requirements.md：
- 假設**物理隔離**於 canonical graph（本檔案儲存，不進 Neo4j）——provisional flag
  會被社會化稀釋（L11 假交叉驗證），隔離必須是不同儲存、不同查詢入口。
- 唯一消費入口＝what-if（`query.bottleneck --what-if`）：回答「若為真，結構排序會變嗎」。
  會大變的才值得花力氣追平行證據；不會變的安心 park。
- 硬邊界：假設**永不**參與 evidence 分級、L8 計數、五軸 assessment；永不出現在預設排序；
  入圖唯一路徑仍是可稽核一手的 admission。
- `expires` 必填——無限期假設會腐爛成事實；到期自動歸檔留稽核。
- 帳號級 credibility：fact-check 命中/未中記在 per-source ledger——某帳號連續命中，
  其後續 lead 值得升權；連續失敗自動降權。這是從 C 類（匿名爆料）擠 alpha 的唯一誠實路。
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

HYPOTHESES_PATH = Path("library/leads/hypotheses.json")

HYPOTHESIS_STATUSES = frozenset({"active", "verified", "refuted", "expired", "archived"})

# what-if overlay 合成 assertion 的固定 origin 標記：一眼可辨、永不解析為 registry 公司。
HYPOTHESIS_ORIGIN = "(hypothesis)"


class HypothesisError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_store(path: Path = HYPOTHESES_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "hypotheses": [], "source_credibility": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("hypotheses", [])
    data.setdefault("source_credibility", {})
    return data


def save_store(data: Mapping[str, Any], path: Path = HYPOTHESES_PATH) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def add_hypothesis(
    data: dict[str, Any],
    *,
    source_handle: str,
    expires: str,
    statement: str,
    lead_id: str = "",
    edges: Iterable[Mapping[str, Any]] = (),
    facts: Iterable[Mapping[str, Any]] = (),
    skeleton_ref: str = "",
    watch_id: str = "",
    note: str = "",
) -> dict[str, Any]:
    """建立一筆假設。`edges` 供 what-if overlay；`facts` 供 fact-check trigger 對照；
    `skeleton_ref` 指向 A 類預寫 RA 骨架（action_drafts 路徑）。"""

    if not source_handle.strip():
        raise HypothesisError("source_handle 必填（帳號級 credibility 的鍵）")
    if not expires:
        raise HypothesisError("expires 必填——無限期假設會腐爛成事實")
    if not statement.strip():
        raise HypothesisError("statement 必填")
    cleaned_edges = []
    for edge in edges:
        src, rel, dst = edge.get("src_id"), edge.get("relation"), edge.get("dst_id")
        if not (src and rel and dst):
            raise HypothesisError(f"edge 缺 src_id/relation/dst_id：{edge}")
        cleaned_edges.append({
            "src_id": str(src),
            "relation": str(rel),
            "dst_id": str(dst),
            "attributes": dict(edge.get("attributes") or {}),
        })
    record = {
        "hypothesis_id": f"hy_{len(data['hypotheses']) + 1:04d}_{date.today().isoformat()}",
        "created_at": _now(),
        "expires": expires,
        "status": "active",
        "source_handle": source_handle.strip(),
        "lead_id": lead_id,
        "statement": statement.strip(),
        "edges": cleaned_edges,
        "facts": [dict(f) for f in facts],
        "skeleton_ref": skeleton_ref,
        "watch_id": watch_id,
        "note": note,
        "verified_by": None,
    }
    data["hypotheses"].append(record)
    return record


def expire_stale(data: dict[str, Any], *, today: date | None = None) -> int:
    today = today or datetime.now(timezone.utc).date()
    expired = 0
    for hyp in data["hypotheses"]:
        if hyp.get("status") != "active":
            continue
        try:
            if date.fromisoformat(str(hyp["expires"])) < today:
                hyp["status"] = "expired"
                expired += 1
        except ValueError:
            continue
    return expired


def record_verification(
    data: dict[str, Any],
    hypothesis_id: str,
    *,
    outcome: str,
    receipt: str,
) -> dict[str, Any]:
    """fact-check 落地：hit＝被一手證實（入圖走正式來源，不是本記錄）；miss＝被否證。
    同步更新帳號級 credibility ledger。"""

    if outcome not in {"hit", "miss"}:
        raise HypothesisError("outcome 只能是 hit 或 miss")
    if not receipt.strip():
        raise HypothesisError("receipt 必填（指向證實/否證它的一手，例如 doc_id）")
    for hyp in data["hypotheses"]:
        if hyp["hypothesis_id"] == hypothesis_id:
            if hyp.get("status") not in {"active", "expired"}:
                raise HypothesisError(f"假設狀態 {hyp.get('status')} 不可再驗證")
            hyp["status"] = "verified" if outcome == "hit" else "refuted"
            hyp["verified_by"] = {"outcome": outcome, "receipt": receipt, "at": _now()}
            ledger = data["source_credibility"].setdefault(
                hyp["source_handle"], {"hits": 0, "misses": 0}
            )
            ledger["hits" if outcome == "hit" else "misses"] += 1
            return hyp
    raise HypothesisError(f"假設不存在：{hypothesis_id}")


def overlay_assertions(
    data: Mapping[str, Any], *, hypothesis_ids: Iterable[str] | None = None
) -> list[dict[str, Any]]:
    """把 active 假設的 edges 合成 what-if 用的 assertion rows
    （shape 對齊 query.bottleneck.fetch_assertions 的輸出）。

    origin 固定為 ``(hypothesis)``——在任何輸出裡一眼可辨，且永不被 registry 解析、
    永不參與 evidence 升級。呼叫端（bottleneck --what-if）只拿它算**純結構**排序 diff。
    """

    wanted = set(hypothesis_ids or ())
    rows: list[dict[str, Any]] = []
    for hyp in data.get("hypotheses") or ():
        if hyp.get("status") != "active":
            continue
        if wanted and hyp["hypothesis_id"] not in wanted:
            continue
        for i, edge in enumerate(hyp.get("edges") or (), 1):
            rows.append({
                "src": edge["src_id"],
                "relation": edge["relation"],
                "dst": edge["dst_id"],
                "attributes": json.dumps(edge.get("attributes") or {}),
                "confidence": 0.5,
                "origin": HYPOTHESIS_ORIGIN,
                "source_type": "hypothesis",
                "_hypothesis_id": hyp["hypothesis_id"],
            })
    return rows


def counters(data: Mapping[str, Any]) -> dict[str, Any]:
    hyps = data.get("hypotheses") or ()
    by_status: dict[str, int] = {}
    for hyp in hyps:
        by_status[hyp.get("status", "?")] = by_status.get(hyp.get("status", "?"), 0) + 1
    return {"total": len(hyps), "by_status": by_status,
            "sources": dict(data.get("source_credibility") or {})}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="截圖假設層 registry")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    add = sub.add_parser("add", help="從 JSON 檔建立假設（欄位見 add_hypothesis）")
    add.add_argument("file")
    verify = sub.add_parser("verify")
    verify.add_argument("hypothesis_id")
    verify.add_argument("--outcome", required=True, choices=["hit", "miss"])
    verify.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    data = load_store()
    if args.cmd == "list":
        expired = expire_stale(data)
        if expired:
            save_store(data)
        for hyp in data["hypotheses"]:
            print(
                f"  {hyp['hypothesis_id']} [{hyp['status']}] @{hyp['source_handle']}"
                f"：{hyp['statement'][:80]}"
                f"（edges {len(hyp.get('edges') or ())}／facts {len(hyp.get('facts') or ())}"
                f"，expires {hyp['expires']}）"
            )
        print(json.dumps(counters(data), ensure_ascii=False))
        return 0
    if args.cmd == "add":
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        record = add_hypothesis(data, **payload)
        save_store(data)
        print(f"✓ 已建假設 {record['hypothesis_id']}（唯一消費入口：bottleneck --what-if）")
        return 0
    if args.cmd == "verify":
        record = record_verification(
            data, args.hypothesis_id, outcome=args.outcome, receipt=args.receipt
        )
        save_store(data)
        ledger = data["source_credibility"][record["source_handle"]]
        print(
            f"✓ {args.hypothesis_id} → {record['status']}；"
            f"@{record['source_handle']} credibility {ledger['hits']}hit/{ledger['misses']}miss"
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
