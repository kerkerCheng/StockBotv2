"""Event Watch 模組——系統裡所有「以後要回來看」的等待條件的統一 registry。

設計依 docs/brainstorms/2026-08-31-event-watch-module-requirements.md：
- 三層檢查成本階梯：T0 被動（新 triage PASS lead 具名標的比對，零 token）、
  T1 日期（sync 比對 until，零 token）、T2 主動輪詢（sweep 給出本輪該查的 K 個，
  由 agent 做 WebSearch；K 可調，調 0 即退回純被動且系統照常運作）。
- 喚醒是簿記：把 pq2 項的 waiting_on 翻回「等你決定」並留 woken_by 稽核，
  **不自動 go、不碰四個 authority gate**。
- 封閉字彙 kind（contract，不是 taxonomy）：`date`／`entity_filing_signal`／
  `fact_verification`。新增 kind＝承認有一類等待無法被表達，不是放寬既有 kind。
- trace backlog 的 related_entity_signal／primary_source_signal 引擎維持原位
  （engine_b/leads.py），本模組不搬家——那端現況健康，搬遷風險最高、收益最低。
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

WATCHES_PATH = Path("library/leads/event_watches.json")
CONFIG_PATH = Path("config/event_watch.json")

WATCH_KINDS = frozenset({"date", "entity_filing_signal", "fact_verification"})

# entity_filing_signal 只被 tier-1 一手來源觸發（沿用 leads.PRIMARY_SOURCE_TIER 的語意）：
# 「等某實體的正式文件」不該被任何一則提到該實體的推文觸發。
PRIMARY_SOURCE_TIER = 1


class EventWatchError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> date:
    return datetime.now(timezone.utc).date()


def load_config() -> dict[str, Any]:
    """T2 力度旋鈕。檔案缺席時 fail-soft 到保守預設（sweep 停用）。"""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False, "sweep_budget_per_run": 0, "min_recheck_days": 3}
    return {
        "enabled": bool(cfg.get("enabled", True)),
        "sweep_budget_per_run": int(cfg.get("sweep_budget_per_run", 2)),
        "min_recheck_days": int(cfg.get("min_recheck_days", 3)),
    }


def load_watches(path: Path = WATCHES_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "watches": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("watches", [])
    return data


def save_watches(data: Mapping[str, Any], path: Path = WATCHES_PATH) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def add_watch(
    data: dict[str, Any],
    *,
    kind: str,
    wake_pq2: int,
    expires: str,
    until: str | None = None,
    entities: Iterable[str] = (),
    fact: str = "",
    fact_check_ref: str = "",
    poll_eligible: bool = False,
    poll_query_hint: str = "",
    hypothesis_ref: str = "",
    note: str = "",
) -> dict[str, Any]:
    if kind not in WATCH_KINDS:
        raise EventWatchError(f"未知 watch kind：{kind}（封閉字彙 {sorted(WATCH_KINDS)}）")
    if kind == "date" and not until:
        raise EventWatchError("kind=date 必須帶 until")
    if kind == "entity_filing_signal" and not list(entities):
        raise EventWatchError("kind=entity_filing_signal 必須帶 entities")
    if kind == "fact_verification" and not (fact and list(entities)):
        raise EventWatchError("kind=fact_verification 必須帶 fact 與 entities")
    if not expires:
        raise EventWatchError("expires 必填——無限期等待會腐爛成事實（brainstorm 硬邊界）")
    watch = {
        "watch_id": f"ew_{len(data['watches']) + 1:04d}_{_today().isoformat()}",
        "created_at": _now(),
        "expires": expires,
        "kind": kind,
        "until": until,
        "entities": sorted({str(e).strip() for e in entities if str(e).strip()}),
        "fact": fact,
        "fact_check_ref": fact_check_ref,
        "wake_pq2": int(wake_pq2),
        "hypothesis_ref": hypothesis_ref,
        "poll": {
            "eligible": bool(poll_eligible),
            "last_checked": None,
            "query_hint": poll_query_hint,
        },
        "note": note,
        "status": "active",
        "woken_by": None,
    }
    data["watches"].append(watch)
    return watch


def _lead_stamp(lead: Mapping[str, Any]) -> str:
    triage = lead.get("triage") or {}
    return str(triage.get("decided_at") or lead.get("first_seen") or "")


def _is_primary(lead: Mapping[str, Any]) -> bool:
    try:
        return int((lead.get("triage") or {}).get("tier")) <= PRIMARY_SOURCE_TIER
    except (TypeError, ValueError):
        return False


def check_watches(
    data: dict[str, Any],
    *,
    leads: Mapping[str, Any] | None = None,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """跑 T0＋T1 檢查，回傳觸發清單（呼叫端負責喚醒 pq2 與存檔）。

    T1：until <= 今天 → 觸發（kind=date）。
    T0：kind=entity_filing_signal／fact_verification 的 watch，若有 watch 建立後
        新 triage PASS 且 tier-1 的 lead 與 entities 有交集 → 觸發。
    到期（expires < 今天）的 watch 標 `expired`，不觸發——過期歸檔留稽核。
    """

    today = today or _today()
    fired: list[dict[str, Any]] = []
    for watch in data["watches"]:
        if watch.get("status") != "active":
            continue
        try:
            if date.fromisoformat(str(watch["expires"])) < today:
                watch["status"] = "expired"
                continue
        except ValueError:
            pass
        kind = watch["kind"]
        if kind == "date":
            try:
                due = date.fromisoformat(str(watch.get("until")))
            except (TypeError, ValueError):
                continue
            if due <= today:
                watch["status"] = "fired"
                watch["woken_by"] = {"kind": "date", "at": _now()}
                fired.append(dict(watch))
        elif kind in {"entity_filing_signal", "fact_verification"} and leads:
            targets = set(watch.get("entities") or ())
            created = str(watch.get("created_at") or "")
            for lead_id, lead in leads.items():
                if (lead.get("triage") or {}).get("decision") != "go":
                    continue
                if not _is_primary(lead):
                    continue
                if _lead_stamp(lead) <= created:
                    continue
                from engine_b.entities import lead_entities

                shared = sorted(targets & lead_entities(lead))
                if shared:
                    watch["status"] = "fired"
                    woken: dict[str, Any] = {
                        "kind": kind,
                        "lead_id": lead_id,
                        "shared_entities": shared,
                        "at": _now(),
                    }
                    # fact_verification 喚醒必帶對照欄位——醒來的人（agent）要直接
                    # 拿 fact 去對觸發 lead 的一手數字，不必回頭翻 watch（L16：
                    # 分類跟著資料走到消費端）。
                    if kind == "fact_verification":
                        woken["fact"] = watch.get("fact")
                        woken["fact_check_ref"] = watch.get("fact_check_ref")
                    if watch.get("hypothesis_ref"):
                        woken["hypothesis_ref"] = watch["hypothesis_ref"]
                    watch["woken_by"] = woken
                    fired.append(dict(watch))
                    break
    return fired


def sweep_due(data: Mapping[str, Any], *, today: date | None = None) -> list[dict[str, Any]]:
    """T2：回傳本輪該主動查的 watch（最多 sweep_budget_per_run 個）。

    只回清單不做查詢——WebSearch 是 agent 的工作；budget=0 或 enabled=false 時
    回空清單，系統退回 T0＋T1 純被動（退化路徑）。
    """

    cfg = load_config()
    if not cfg["enabled"] or cfg["sweep_budget_per_run"] <= 0:
        return []
    today = today or _today()
    candidates = []
    for watch in data["watches"]:
        if watch.get("status") != "active" or not (watch.get("poll") or {}).get("eligible"):
            continue
        last = (watch.get("poll") or {}).get("last_checked")
        if last:
            try:
                days = (today - date.fromisoformat(str(last)[:10])).days
                if days < cfg["min_recheck_days"]:
                    continue
            except ValueError:
                pass
        waited = 0
        try:
            waited = (today - date.fromisoformat(str(watch["created_at"])[:10])).days
        except ValueError:
            pass
        candidates.append((waited, watch))
    candidates.sort(key=lambda pair: -pair[0])
    return [dict(w) for _, w in candidates[: cfg["sweep_budget_per_run"]]]


def mark_checked(data: dict[str, Any], watch_id: str, *, today: date | None = None) -> None:
    today = today or _today()
    for watch in data["watches"]:
        if watch["watch_id"] == watch_id:
            watch.setdefault("poll", {})["last_checked"] = today.isoformat()
            return
    raise EventWatchError(f"watch 不存在：{watch_id}")


def counters(data: Mapping[str, Any]) -> dict[str, int]:
    """常駐計數器（L14：防呆要自己出現）。"""

    active = [w for w in data["watches"] if w.get("status") == "active"]
    return {
        "active": len(active),
        "t1_date": sum(1 for w in active if w["kind"] == "date"),
        "t0_passive": sum(
            1 for w in active if w["kind"] in {"entity_filing_signal", "fact_verification"}
        ),
        "t2_pollable": sum(1 for w in active if (w.get("poll") or {}).get("eligible")),
        "fired_unconsumed": sum(1 for w in data["watches"] if w.get("status") == "fired"),
        "expired": sum(1 for w in data["watches"] if w.get("status") == "expired"),
    }


def consume_fired(data: dict[str, Any], watch_id: str) -> None:
    """喚醒動作完成後把 fired 收掉（稽核保留）。"""

    for watch in data["watches"]:
        if watch["watch_id"] == watch_id and watch.get("status") == "fired":
            watch["status"] = "consumed"
            return
    raise EventWatchError(f"沒有待消化的 fired watch：{watch_id}")


def _render_watch(watch: Mapping[str, Any]) -> str:
    kind = watch["kind"]
    detail = {
        "date": f"until {watch.get('until')}",
        "entity_filing_signal": f"等 {','.join(watch.get('entities') or [])} 的一手文件",
        "fact_verification": f"對照 {watch.get('fact', '')[:50]}",
    }[kind]
    poll = "｜可輪詢" if (watch.get("poll") or {}).get("eligible") else ""
    return (
        f"  {watch['watch_id']} [{watch['status']}] {kind}：{detail}"
        f" → 喚醒 pq2 [{watch['wake_pq2']}]{poll}（expires {watch['expires']}）"
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Event Watch registry")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("counters")
    sweep = sub.add_parser("sweep", help="列出本輪 T2 該查的 watch（agent 拿去 WebSearch）")
    sweep.add_argument("--mark-checked", action="store_true")
    add = sub.add_parser("add")
    add.add_argument("--kind", required=True, choices=sorted(WATCH_KINDS))
    add.add_argument("--wake-pq2", required=True, type=int)
    add.add_argument("--expires", required=True)
    add.add_argument("--until")
    add.add_argument("--entities", default="")
    add.add_argument("--fact", default="")
    add.add_argument("--fact-check-ref", default="")
    add.add_argument("--poll", action="store_true")
    add.add_argument("--query-hint", default="")
    add.add_argument("--note", default="")
    args = parser.parse_args(argv)

    data = load_watches()
    if args.cmd == "list":
        for watch in data["watches"]:
            print(_render_watch(watch))
        print(json.dumps(counters(data), ensure_ascii=False))
        return 0
    if args.cmd == "counters":
        print(json.dumps(counters(data), ensure_ascii=False))
        return 0
    if args.cmd == "sweep":
        due = sweep_due(data)
        for watch in due:
            print(_render_watch(watch))
            hint = (watch.get("poll") or {}).get("query_hint")
            if hint:
                print(f"      query hint：{hint}")
            if args.mark_checked:
                mark_checked(data, watch["watch_id"])
        if args.mark_checked and due:
            save_watches(data)
        if not due:
            cfg = load_config()
            print(f"（本輪無 T2 待查；enabled={cfg['enabled']} budget={cfg['sweep_budget_per_run']}）")
        return 0
    if args.cmd == "add":
        watch = add_watch(
            data,
            kind=args.kind,
            wake_pq2=args.wake_pq2,
            expires=args.expires,
            until=args.until,
            entities=[e for e in args.entities.split(",") if e.strip()],
            fact=args.fact,
            fact_check_ref=args.fact_check_ref,
            poll_eligible=args.poll,
            poll_query_hint=args.query_hint,
            note=args.note,
        )
        save_watches(data)
        print(f"✓ 已建 watch {watch['watch_id']} → pq2 [{watch['wake_pq2']}]")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
