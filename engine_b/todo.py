"""統一待辦池（廣義 pq2）——所有需要使用者決策的事，一個編號空間。

設計原則（2026-07-26 校正）：
- **單一核准收件匣：** prepared Research Action 入圖、決策複查、thesis 到期、
  Sheet-only 持股與手動 authority 問題收斂到這一個池。Raw／triaged leads 屬 pq1 工作佇列，
  routine 先自動 trace＋extract；只有 prepared 結果才進 pq2，避免同一題問使用者兩次。
- **編號持久：** `n` 在項目首次進池時指派，直到 resolve 才釋放。**不因排序或當日
  狀態重算**——否則你隔天回「3 go」會指到別的東西（正確性風險，不只是體驗問題）。
- **池是狀態，report 是敘事：** daily brief 不留檔；稽核價值由本池的 append-only
  `log`（何時提出、你怎麼決定、理由）承擔。
- 本模組只做池的機制（純標準庫）；各來源的蒐集在 CLI／composer 層注入，避免
  engine_b 反向依賴 Engine A/C/D。

pq1／pq2 定義見 CONCEPTS.md。
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "1"

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POOL_PATH = _ROOT / "library" / "leads" / "todo_pool.json"

# 項目類型 → 該類型的 `go` 代表什麼動作（type-aware dispatch 的權威對照）。
ITEM_TYPES: dict[str, str] = {
    "lead_research": "（legacy）已移回自動 pq1，不再建立新項目",
    "ra_admission": "核准入圖（apply_research_action）",
    "decision_review": "重新評估該 probe（reassess）",
    "thesis_lifecycle": "本機複查 thesis 並手動更新 lifecycle.json",
    "sheet_only_holding": "評估這筆 Sheet 持股（evaluate-signal 或 onboard）",
    "manual": "依 hint 執行",
}

VERBS = ("go", "drop", "pending")


class TodoError(ValueError):
    """未知編號、未知類型或非法操作。"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_pool() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "next_n": 1, "items": [], "log": []}


def load(path: Path | str = DEFAULT_POOL_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return empty_pool()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "items" not in data:
        raise ValueError(f"todo pool 格式非法：{p}")
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("next_n", 1)
    data.setdefault("items", [])
    data.setdefault("log", [])
    return data


def save(pool: Mapping[str, Any], path: Path | str = DEFAULT_POOL_PATH) -> None:
    """Atomic 寫檔，沿用 repo 慣例（tempfile + fsync + os.replace）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=p.parent,
        prefix=f".{p.name}.", suffix=".tmp", delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(pool, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, p)
    finally:
        temp_path.unlink(missing_ok=True)


def active_items(pool: Mapping[str, Any]) -> list[dict[str, Any]]:
    """未 resolve 的項目，依編號排序。"""
    return sorted(
        (i for i in pool["items"] if not i.get("resolved_at")),
        key=lambda i: i["n"],
    )


def _key(item_type: str, ref_id: str) -> tuple[str, str]:
    return (item_type, ref_id)


def upsert(
    pool: dict[str, Any],
    *,
    item_type: str,
    ref_id: str,
    title: str,
    hint: str = "",
    source: str = "",
    at: str | None = None,
) -> dict[str, Any]:
    """加入或更新一個項目。冪等：同 (type, ref_id) 已在池中且未 resolve 就只更新
    顯示欄位、**保留原編號**（編號持久是本池的核心不變式）。"""
    if item_type not in ITEM_TYPES:
        raise TodoError(f"未知項目類型：{item_type}")
    if not str(ref_id).strip():
        raise TodoError("ref_id 不可為空")
    for item in pool["items"]:
        if _key(item["type"], item["ref_id"]) == _key(item_type, ref_id) and not item.get("resolved_at"):
            item["title"] = title or item["title"]
            if hint:
                item["hint"] = hint
            return item
    item = {
        "n": int(pool["next_n"]),
        "type": item_type,
        "ref_id": str(ref_id),
        "title": title,
        "hint": hint or ITEM_TYPES[item_type],
        "source": source,
        "added_at": at or _now(),
        "resolved_at": None,
        "resolution": None,
        "reason": None,
    }
    pool["next_n"] = int(pool["next_n"]) + 1
    pool["items"].append(item)
    return item


def get(pool: Mapping[str, Any], n: int) -> dict[str, Any]:
    for item in pool["items"]:
        if item["n"] == int(n) and not item.get("resolved_at"):
            return item
    raise TodoError(f"編號 {n} 不存在或已處理")


def resolve(
    pool: dict[str, Any],
    n: int,
    verb: str,
    *,
    reason: str = "",
    at: str | None = None,
) -> dict[str, Any]:
    """以動詞處理一個編號。`pending` 不 resolve（明確 defer，留在池中）。"""
    if verb not in VERBS:
        raise TodoError(f"未知動詞：{verb}（可用：{', '.join(VERBS)}）")
    item = get(pool, n)
    stamp = at or _now()
    if verb == "pending":
        item["deferred_at"] = stamp
    else:
        item["resolved_at"] = stamp
        item["resolution"] = verb
        item["reason"] = reason or None
    pool["log"].append({
        "at": stamp, "n": item["n"], "type": item["type"],
        "ref_id": item["ref_id"], "verb": verb, "reason": reason or None,
    })
    return item


def apply_batch(
    pool: dict[str, Any],
    parsed: Mapping[str, Iterable[int]],
    *,
    reason: str = "",
    at: str | None = None,
) -> dict[str, list[int]]:
    """套用 `engine_b.batch.parse_batch_reply` 的結果。

    回 {"applied": [...], "failed": [...]}；單一編號失敗不中斷其餘（部分成功是
    可接受的——未處理的仍留在池裡，下次 brief 會再出現）。
    """
    applied: list[int] = []
    failed: list[int] = []
    for verb, numbers in parsed.items():
        for n in numbers:
            try:
                resolve(pool, n, verb, reason=reason, at=at)
                applied.append(int(n))
            except TodoError:
                failed.append(int(n))
    return {"applied": sorted(applied), "failed": sorted(failed)}


def retire_legacy_pq1_items(
    pool: dict[str, Any], *, at: str | None = None
) -> int:
    """把舊版 raw lead／Weekly research topic 移回 pq1；保留稽核。"""
    stamp = at or _now()
    retired = 0
    for item in active_items(pool):
        legacy_lead = item["type"] == "lead_research"
        legacy_weekly = (
            item["type"] == "manual"
            and str(item.get("title") or "").startswith("Weekly topic：")
        )
        if not (legacy_lead or legacy_weekly):
            continue
        item["resolved_at"] = stamp
        item["resolution"] = "migrated_to_pq1"
        item["reason"] = "triage PASS 後由 routine 自動 trace/extract；prepared RA 才進 pq2"
        pool["log"].append({
            "at": stamp,
            "n": item["n"],
            "type": item["type"],
            "ref_id": item["ref_id"],
            "verb": "migrated_to_pq1",
            "reason": item["reason"],
        })
        retired += 1
    return retired


# 舊 import 相容；新程式使用語意較完整的名稱。
retire_legacy_lead_research = retire_legacy_pq1_items


def sync(
    pool: dict[str, Any],
    incoming: Iterable[Mapping[str, Any]],
    *,
    at: str | None = None,
) -> dict[str, int]:
    """把各來源蒐集到的項目 upsert 進池。

    `incoming` 每筆需有 type／ref_id／title，可選 hint／source。已 resolve 的
    (type, ref_id) 會重新進池（代表它又出現了，例如新的 evidence-delta）——這是
    刻意的：resolve 表示「當時處理過」，不是永久黑名單。
    """
    added = 0
    for row in incoming:
        before = len(pool["items"])
        upsert(
            pool,
            item_type=str(row["type"]),
            ref_id=str(row["ref_id"]),
            title=str(row.get("title") or ""),
            hint=str(row.get("hint") or ""),
            source=str(row.get("source") or ""),
            at=at,
        )
        if len(pool["items"]) > before:
            added += 1
    return {"added": added, "active": len(active_items(pool))}


# ── 來源蒐集（lazy import，避免 engine_b 反向依賴 Engine A/C/D）─────────────

def collect_from_leads() -> list[dict[str, Any]]:
    """Raw／triaged leads 不屬 pq2；保留函式作相容面，永遠回空。"""
    return []


def collect_from_research_actions() -> list[dict[str, Any]]:
    """等核准入圖的 Research Action → 經典 pq2。"""
    try:
        from mcp_server.research_actions import iter_actions
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    for action in iter_actions():
        if action.get("state") in {"ready_for_approval", "partial_apply"}:
            rows.append({
                "type": "ra_admission",
                "ref_id": str(action.get("action_id") or action.get("id") or ""),
                "title": str(action.get("slug") or action.get("title") or "Research Action"),
                "source": "research_action",
            })
    return [r for r in rows if r["ref_id"]]


def collect_from_lifecycle() -> list[dict[str, Any]]:
    """到期／review_required 的 thesis → 本機複查待辦。"""
    try:
        from crons.thesis_freshness_check import lifecycle_due
    except Exception:
        return []
    return [
        {
            "type": "thesis_lifecycle",
            "ref_id": tid,
            "title": f"thesis {tid}：{why}",
            "source": "lifecycle",
        }
        for tid, why in lifecycle_due()
    ]


def collect_from_decisions() -> list[dict[str, Any]]:
    """需要動作的 Engine D 決策項（REVIEW／TRADE／HEDGE）→ 複查待辦。

    需要本機 private Decision Store 與外部 authority；失敗時回空（不讓池因為
    Neo4j/網路不通就整個壞掉）。
    """
    try:
        from mcp_server.decision_tools import get_decision_brief_core

        brief = get_decision_brief_core()
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    items = brief.get("items") or []
    for item in items:
        action = str(item.get("recommended_action") or "")
        if action in {"NO ACTION", ""}:
            continue
        ref = str(item.get("cohort_id") or item.get("decision_id") or "")
        if not ref:
            continue
        company = item.get("company_id") or "unknown"
        rows.append({
            "type": "sheet_only_holding" if item.get("sheet_only") else "decision_review",
            "ref_id": ref,
            "title": f"{action} — {company}",
            "source": "decision_lab",
        })
    # Engine D 也可能因 portfolio authority 全域失效而要求 REVIEW，這時沒有
    # cohort item（例如 Google Sheet holdings 完全讀不到）。這仍是需要使用者
    # 處理的 pq2，不能因 items=[] 就從統一待辦池消失。
    if brief.get("action_needed") and not items:
        action = str(brief.get("recommended_action") or "REVIEW")
        blockers = sorted(str(b) for b in (brief.get("blockers") or []) if b)
        reason = str(brief.get("reason") or "Engine D 全域狀態需要複查")
        ref = "global:" + ("|".join(blockers) or action.lower())
        rows.append({
            "type": "decision_review",
            "ref_id": ref,
            "title": f"{action} — {reason}",
            "hint": "修復全域 authority blocker 後重跑 decision_lab today",
            "source": "decision_lab",
        })
    return rows


def collect_all(*, include_decisions: bool = True) -> list[dict[str, Any]]:
    rows = collect_from_research_actions() + collect_from_lifecycle()
    if include_decisions:
        rows += collect_from_decisions()
    return rows


# ── CLI ────────────────────────────────────────────────────────────────────

def _render(pool: Mapping[str, Any]) -> str:
    items = active_items(pool)
    if not items:
        return "（待辦池已清空）"
    lines = ["待辦事項統整（回覆用編號；`<編號…> go｜drop｜pending`）", ""]
    by_type: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_type.setdefault(item["type"], []).append(item)
    for item_type, group in by_type.items():
        lines.append(f"## {item_type} — {ITEM_TYPES[item_type]}")
        for item in group:
            flag = "（已 defer）" if item.get("deferred_at") else ""
            lines.append(f"  [{item['n']}] {item['title']}{flag}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="統一待辦池（廣義 pq2）")
    ap.add_argument("--pool", default=str(DEFAULT_POOL_PATH))
    sub = ap.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="列出待辦（不同步）")
    p_list.add_argument("--json", action="store_true")

    p_sync = sub.add_parser("sync", help="從各來源同步後列出")
    p_sync.add_argument("--no-decisions", action="store_true",
                        help="跳過 Engine D 決策佇列（免外部連線）")
    p_sync.add_argument("--json", action="store_true")

    p_res = sub.add_parser("resolve", help="處理編號：go／drop／pending")
    p_res.add_argument("numbers", nargs="+")
    p_res.add_argument("--verb", required=True, choices=VERBS)
    p_res.add_argument("--reason", default="")

    p_batch = sub.add_parser("batch", help="套用批次語法，如 '1 3 go 4 drop'")
    p_batch.add_argument("reply")

    p_add = sub.add_parser("add", help="手動加入待辦")
    p_add.add_argument("title")
    p_add.add_argument("--hint", default="")
    p_add.add_argument("--ref", default="")

    args = ap.parse_args(argv)
    pool = load(args.pool)

    if args.command == "list":
        print(json.dumps(active_items(pool), ensure_ascii=False, indent=2)
              if args.json else _render(pool))
        return 0

    if args.command == "sync":
        retired = retire_legacy_pq1_items(pool)
        result = sync(pool, collect_all(include_decisions=not args.no_decisions))
        save(pool, args.pool)
        if args.json:
            print(json.dumps({**result, "items": active_items(pool)},
                             ensure_ascii=False, indent=2))
        else:
            migration = f"；移回 pq1 {retired}" if retired else ""
            print(f"（新增 {result['added']}，目前 {result['active']} 項待辦{migration}）\n")
            print(_render(pool))
        return 0

    if args.command == "resolve":
        for raw in args.numbers:
            try:
                resolve(pool, int(raw), args.verb, reason=args.reason)
                print(f"✓ [{raw}] → {args.verb}")
            except (TodoError, ValueError) as exc:
                print(f"✗ [{raw}]：{exc}", file=sys.stderr)
        save(pool, args.pool)
        return 0

    if args.command == "batch":
        from engine_b.batch import parse_batch_reply

        parsed = parse_batch_reply(args.reply)
        if not parsed:
            print("無法解析批次語法（需要「數字…動詞」配對）", file=sys.stderr)
            return 1
        outcome = apply_batch(pool, parsed)
        save(pool, args.pool)
        print(json.dumps(outcome, ensure_ascii=False))
        return 0 if not outcome["failed"] else 1

    if args.command == "add":
        item = upsert(
            pool, item_type="manual",
            ref_id=args.ref or f"manual:{pool['next_n']}",
            title=args.title, hint=args.hint, source="manual",
        )
        save(pool, args.pool)
        print(f"✓ 已加入 [{item['n']}] {item['title']}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
