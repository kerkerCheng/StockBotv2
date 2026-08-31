"""Event Watch 模組——系統裡所有「以後要回來看」的等待條件的統一 registry。

設計依 docs/brainstorms/2026-08-31-event-watch-module-requirements.md：
- 三層檢查成本階梯：T0 被動（新 triage PASS lead 具名標的比對，零 token）、
  T1 日期（sync 比對 until，零 token）、T2 主動輪詢（sweep 給出本輪該查的 K 個，
  由 agent 做 WebSearch；K 可調，調 0 即退回純被動且系統照常運作）。
- 喚醒是簿記：把 pq2 項的 waiting_on 翻回「等你決定」並留 woken_by 稽核，
  **不自動 go、不碰四個 authority gate**。
- 封閉字彙 kind（contract，不是 taxonomy）：`date`／`entity_filing_signal`／
  `fact_verification`／`related_entity_signal`。新增 kind＝承認有一類等待無法被表達，
  不是放寬既有 kind。
- 喚醒目標三選一：`wake_pq2`（翻醒待辦）／`hypothesis_ref`（假設對照）／
  `wake_lead`（把追源線索排回 pq1）。

2026-08-31（[321]）：trace 引擎併入本模組。原設計（brainstorm §動工切法 4）把它排在
最後並註明「那端現況健康，搬遷風險最高、收益最低」——**「現況健康」當時沒有被驗證過**。
實測推翻：50 筆非 terminal backlog 有 14 筆已不可能再被喚醒（10 筆標的全被 consumed-marker
消化、4 筆根本沒有具名標的），而 `auto_trigger_reachable` 對這 14 筆全回 true——它只答
「有沒有標的可比對」，不答「這些標的是不是都用完了」（L12 一個表示兩種語意）。

併入的真正收益不是整齊，是**讓 trace 繼承它缺的那道硬邊界：`expires` 必填**。
14 筆的死因是 consumed-marker（2026-08-12 為防止重複喚醒吃光 pq1 slot 而加的補丁）
沒有到期兜底，用完即靜默沉底。有 expires 之後，喚醒幾次都無所謂——等不到就會到期現形，
由人決定續等／改主動輪詢／放棄。consumed-marker 保留（它防的浪費是真的），只是不再是
唯一的終止條件。

同時消掉一組重複實作：`entity_filing_signal` 與 trace 的 `primary_source_signal` 判準
完全相同（tier ≤ 1 ＋ entities 交集），連 `PRIMARY_SOURCE_TIER = 1` 都各寫一份。
遷移時 `primary_source_signal` 一律映射到 `entity_filing_signal`（L16：分類要有單一 SSOT）。
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

WATCHES_PATH = Path("library/leads/event_watches.json")
CONFIG_PATH = Path("config/event_watch.json")

WATCH_KINDS = frozenset({
    "date",
    "entity_filing_signal",
    "fact_verification",
    "related_entity_signal",
})

# 需要 tier-1 一手來源才觸發的 kind：「等某實體的正式文件」不該被任何一則提到該實體的
# 推文觸發。`related_entity_signal` 刻意不在此列——它等的就是「同一標的有任何新動靜」。
PRIMARY_ONLY_KINDS = frozenset({"entity_filing_signal", "fact_verification"})

# 會做具名標的比對的 kind（T0 被動層）。
ENTITY_MATCH_KINDS = frozenset({
    "entity_filing_signal", "fact_verification", "related_entity_signal",
})

# tier-1 判斷的 SSOT 在 lead_refs（leads 與 event_watch 共用，放低層才不循環 import）。
from engine_b.lead_refs import PRIMARY_SOURCE_TIER, is_primary_source  # noqa: F401


class EventWatchError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> date:
    return datetime.now(timezone.utc).date()


# 一個財報週期（90 天）＋緩衝。最常見的等待模式是「下一份季報會不會揭露」；
# 等滿一輪還沒出現就該讓人重新決定續等／改輪詢／放棄，而不是無聲續等。
DEFAULT_TRACE_TTL_DAYS = 120


def load_config() -> dict[str, Any]:
    """T2 力度旋鈕。檔案缺席時 fail-soft 到保守預設（sweep 停用）。"""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "enabled": False, "sweep_budget_per_run": 0, "min_recheck_days": 3,
            "trace_ttl_days": DEFAULT_TRACE_TTL_DAYS,
        }
    return {
        "enabled": bool(cfg.get("enabled", True)),
        "sweep_budget_per_run": int(cfg.get("sweep_budget_per_run", 2)),
        "min_recheck_days": int(cfg.get("min_recheck_days", 3)),
        "trace_ttl_days": int(cfg.get("trace_ttl_days", DEFAULT_TRACE_TTL_DAYS)),
    }


def ensure_trace_watch(
    lead_id: str,
    *,
    kind: str,
    entities: Iterable[str],
    query_hint: str = "",
    note: str = "",
    consumed_entities: Iterable[str] = (),
    created_at: str | None = None,
    today: date | None = None,
) -> dict[str, Any] | None:
    """替一筆剛 park 的追源線索建立等待條件（沒有就建，有就沿用）。

    這是 [321] 的**入口端**：遷移只處理了既有 backlog，新 park 的若不建 watch，
    就會立刻變回沒有到期日、沒人管的等待——L13「管子只接了一頭」。
    """
    entities = sorted({str(e).strip() for e in entities if str(e).strip()})
    if not entities:
        return None  # 沒有具名標的就沒有觸發條件，不假裝在等（由 wake_state=unwatched 現形）
    data = load_watches()
    for watch in data.get("watches", []):
        if watch.get("wake_lead") == lead_id and watch.get("status") != "consumed":
            return watch
    today = today or _today()
    ttl = load_config()["trace_ttl_days"]
    watch = add_watch(
        data,
        kind="entity_filing_signal" if kind == "primary_source_signal" else kind,
        wake_lead=lead_id,
        expires=(today + timedelta(days=ttl)).isoformat(),
        entities=entities,
        consumed_entities=consumed_entities,
        poll_query_hint=query_hint[:200],
        note=note,
        # 等待從「這條線索被 park」那一刻起算，不是從 registry 寫入那一刻。
        # T0 比對用 `created_at` 判斷「這則 lead 是不是等待開始後才出現的」，
        # 用寫入時間會讓 park 當下已在佇列中的新 lead 被誤判成舊事件。
        created_at=created_at,
    )
    save_watches(data)
    return watch


def load_watches(path: Path | None = None) -> dict[str, Any]:
    # 路徑在呼叫時解析而非用預設參數綁定——預設參數在 import 時就固定了，
    # 測試無法用 monkeypatch 導向暫存檔（見 tests/conftest.py 的自動隔離）。
    path = Path(path) if path else WATCHES_PATH
    if not path.exists():
        return {"schema_version": 1, "watches": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("watches", [])
    return data


def save_watches(data: Mapping[str, Any], path: Path | None = None) -> None:
    path = Path(path) if path else WATCHES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
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
    wake_pq2: int | None = None,
    expires: str,
    until: str | None = None,
    entities: Iterable[str] = (),
    fact: str = "",
    fact_check_ref: str = "",
    poll_eligible: bool = False,
    poll_query_hint: str = "",
    hypothesis_ref: str = "",
    wake_lead: str = "",
    consumed_entities: Iterable[str] = (),
    note: str = "",
    created_at: str | None = None,
) -> dict[str, Any]:
    if kind not in WATCH_KINDS:
        raise EventWatchError(f"未知 watch kind：{kind}（封閉字彙 {sorted(WATCH_KINDS)}）")
    if kind == "date" and not until:
        raise EventWatchError("kind=date 必須帶 until")
    if kind in ENTITY_MATCH_KINDS and not list(entities):
        raise EventWatchError(f"kind={kind} 必須帶 entities")
    if kind == "fact_verification" and not fact:
        raise EventWatchError("kind=fact_verification 必須帶 fact")
    if not expires:
        raise EventWatchError("expires 必填——無限期等待會腐爛成事實（brainstorm 硬邊界）")
    # 喚醒目標三選一（[321] 由二選一擴充）：pq2 編號（翻醒 waiting 項）、假設 id
    # （fact-check 到點，agent 對照＋verify 後 consume）、或 lead id（追源線索排回 pq1）。
    targets = [bool(wake_pq2), bool(hypothesis_ref), bool(wake_lead)]
    if sum(targets) != 1:
        raise EventWatchError("wake_pq2／hypothesis_ref／wake_lead 必須恰好擇一")
    watch = {
        "watch_id": f"ew_{len(data['watches']) + 1:04d}_{_today().isoformat()}",
        "created_at": created_at or _now(),
        "expires": expires,
        "kind": kind,
        "until": until,
        "entities": sorted({str(e).strip() for e in entities if str(e).strip()}),
        "fact": fact,
        "fact_check_ref": fact_check_ref,
        "wake_pq2": int(wake_pq2) if wake_pq2 else None,
        "hypothesis_ref": hypothesis_ref,
        "wake_lead": wake_lead,
        # 同一標的觸發過就不再重複（防 2026-08-12 的「5 個 pq1 slot 被同批重排吃光」）。
        # 它不再是終止條件——expires 才是；標的用完只代表暫時停滯，到期仍會現形。
        "consumed_entities": sorted(
            {str(e).strip().upper() for e in consumed_entities if str(e).strip()}
        ),
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
        elif kind in ENTITY_MATCH_KINDS and leads:
            targets = set(watch.get("entities") or ())
            created = str(watch.get("created_at") or "")
            consumed = set(watch.get("consumed_entities") or ())
            for lead_id, lead in leads.items():
                if (lead.get("triage") or {}).get("decision") != "go":
                    continue
                # `related_entity_signal` 等的是「同一標的有任何新動靜」，不限一手；
                # 其餘 kind 等的是正式文件，不該被任何一則提及觸發。
                if kind in PRIMARY_ONLY_KINDS and not is_primary_source(lead):
                    continue
                if _lead_stamp(lead) <= created:
                    continue
                from engine_b.entities import lead_entities

                shared = sorted(targets & lead_entities(lead))
                if not shared:
                    continue
                # consumed-marker 只套用在 related_entity_signal：同一檔的第二則轉述
                # 不會帶來新事證。一手來源相反——下一季的 10-Q 本身就是新事件，
                # 故不以標的消化（沿用 leads._requeue_related_trace_backlog 的原判準）。
                if kind == "related_entity_signal":
                    novel = [s for s in shared if s.strip().upper() not in consumed]
                    if not novel:
                        continue
                    shared = novel
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
                if watch.get("wake_lead"):
                    woken["wake_lead"] = watch["wake_lead"]
                    watch["consumed_entities"] = sorted(
                        consumed | {s.strip().upper() for s in shared}
                    )
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


def is_stalled(watch: Mapping[str, Any]) -> bool:
    """標的全被消化，短期內不會再被動觸發——但**沒有死**，到期仍會現形。

    [321] 之前這個狀態沒有名字：`auto_trigger_reachable` 只答「有沒有標的可比對」，
    對 10 筆標的已全數消化的 lead 一律回 true，於是它們安靜沉底、無人知道
    （L12：一個表示承載兩種語意，下游被迫二選一而兩邊都錯）。
    現在它有名字、有計數器，且有 `expires` 兜底——停滯不等於死亡。
    """
    if watch.get("kind") != "related_entity_signal":
        return False
    entities = {str(e).strip().upper() for e in (watch.get("entities") or ())}
    if not entities:
        return True
    consumed = {str(e).strip().upper() for e in (watch.get("consumed_entities") or ())}
    return not (entities - consumed)


def counters(data: Mapping[str, Any]) -> dict[str, int]:
    """常駐計數器（L14：防呆要自己出現）。"""

    active = [w for w in data["watches"] if w.get("status") == "active"]
    return {
        "active": len(active),
        "t1_date": sum(1 for w in active if w["kind"] == "date"),
        "t0_passive": sum(1 for w in active if w["kind"] in ENTITY_MATCH_KINDS),
        "t2_pollable": sum(1 for w in active if (w.get("poll") or {}).get("eligible")),
        # 喚醒目標分佈：使用者的「在等什麼」有三種去處，混在一起看不出比例。
        "wake_pq2": sum(1 for w in active if w.get("wake_pq2")),
        "wake_lead": sum(1 for w in active if w.get("wake_lead")),
        "wake_hypothesis": sum(1 for w in active if w.get("hypothesis_ref")),
        # 停滯＝被動層短期不會再觸發，只剩 expires 與 T2 輪詢能救它。
        # 這個數字若持續攀升，代表被動喚醒的涵蓋率不足，不是「大家都在等」。
        "stalled": sum(1 for w in active if is_stalled(w)),
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


def reactivate(data: dict[str, Any], watch_id: str) -> None:
    """lead 型 watch 排回 pq1 後回到等待——同一份文件可能要等好幾輪才出現。

    與 `consume_fired` 的差別：pq2／hypothesis 型喚醒一次就結束（人接手了），
    lead 型的等待條件（「拿到那份原文」）在 pq1 重查未果時依然成立，所以回 active
    繼續等，只是標的已進 consumed。到期仍由 expires 收斂。
    """
    for watch in data["watches"]:
        if watch["watch_id"] == watch_id and watch.get("status") == "fired":
            watch["status"] = "active"
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
    target = (
        f"pq2 [{watch['wake_pq2']}]" if watch.get("wake_pq2")
        else f"假設 {watch.get('hypothesis_ref')}"
    )
    return (
        f"  {watch['watch_id']} [{watch['status']}] {kind}：{detail}"
        f" → 喚醒 {target}{poll}（expires {watch['expires']}）"
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Event Watch registry")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("counters")
    consume = sub.add_parser("consume", help="假設對照完成後收掉 fired watch")
    consume.add_argument("watch_id")
    sweep = sub.add_parser("sweep", help="列出本輪 T2 該查的 watch（agent 拿去 WebSearch）")
    sweep.add_argument("--mark-checked", action="store_true")
    add = sub.add_parser("add")
    add.add_argument("--kind", required=True, choices=sorted(WATCH_KINDS))
    add.add_argument("--wake-pq2", type=int)
    add.add_argument("--expires", required=True)
    add.add_argument("--until")
    add.add_argument("--entities", default="")
    add.add_argument("--fact", default="")
    add.add_argument("--fact-check-ref", default="")
    add.add_argument("--wake-hypothesis", default="", help="假設 id（與 --wake-pq2 擇一）")
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
    if args.cmd == "consume":
        consume_fired(data, args.watch_id)
        save_watches(data)
        print(f"✓ 已收 {args.watch_id}")
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
            hypothesis_ref=args.wake_hypothesis,
            poll_eligible=args.poll,
            poll_query_hint=args.query_hint,
            note=args.note,
        )
        save_watches(data)
        target = (
            f"pq2 [{watch['wake_pq2']}]" if watch.get('wake_pq2')
            else f"假設 {watch.get('hypothesis_ref')}"
        )
        print(f"✓ 已建 watch {watch['watch_id']} → {target}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
