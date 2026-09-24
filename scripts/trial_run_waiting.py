"""試跑：用真實資料的暫存副本，把「今天」往前快轉，逐個有事發生的日子跑 daily 的等待相關步驟。

**為什麼有這支（2026-09-24 使用者要求）：** 單元測試只證明我想到的情境；R2-b 抓到的 B1 就是因為測試把對帳關掉了。
拿真實 registry／待辦池／leads 的副本快轉到下一個到期日跑一次，使用者會看到的心跳與 pq2 標題就擺在眼前——
第一次試跑就抓到「到期待決被算成未盯」與「同一份 thesis 的條件同一天到期、一次鑄 6 個編號」。
改到等待系統（event_watch／todo／leads 的到期與喚醒、反證登記、心跳段 2／3）時，交付前跑一次、讀輸出。

只寫暫存副本（`--out`，預設 `library/private/trial_runs/waiting/`），真檔一個 byte 都不動（結尾有檢查）；
thesis、讀圖 ledger、registry 設定照讀真的。每個模擬日：⑨ consume-fired（含追源到期結案）→ ⑩ todo sync
（先對帳再收集）→ 心跳第 2、3 段的相關行。第一次出現 watch_decision 時模擬使用者的三種回答（續等／放棄／
研究後判定觸及），看之後的日子長什麼樣子。**這是試跑不是驗收**：輸出不得當成「已生效」的證據（plan §0.3 #10）。
不在任何無人值守步驟裡（它會換掉模組的時鐘）。

用法：python scripts/trial_run_waiting.py [--until 2027-10-01] [--no-actions] [--out <目錄>]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
DEFAULT_OUT = REPO / "library" / "private" / "trial_runs" / "waiting"
OUT = DEFAULT_OUT

from crons import heartbeat as hb  # noqa: E402
from crons import thesis_freshness_check as tfc  # noqa: E402
from engine_b import disproof as dp  # noqa: E402
from engine_b import event_watch as ew  # noqa: E402
from engine_b import leads as leads_mod  # noqa: E402
from engine_b import todo  # noqa: E402

SIM = [date.today()]


class FakeDate(date):
    @classmethod
    def today(cls):
        d = SIM[0]
        return cls(d.year, d.month, d.day)


class FakeDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        d = SIM[0]
        base = cls(d.year, d.month, d.day, 6, 0, tzinfo=timezone.utc)
        return base.astimezone(tz) if tz else base.replace(tzinfo=None)


def install_clock() -> None:
    for mod in (ew, todo, leads_mod, dp, tfc, hb):
        if hasattr(mod, "datetime"):
            mod.datetime = FakeDatetime
        if hasattr(mod, "date"):
            mod.date = FakeDate


def install_copies() -> dict[str, Path]:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    paths = {
        "watches": OUT / "event_watches.json",
        "pool": OUT / "todo_pool.json",
        "leads": OUT / "pending_leads.json",
    }
    shutil.copy(REPO / "library/leads/event_watches.json", paths["watches"])
    shutil.copy(REPO / "library/leads/todo_pool.json", paths["pool"])
    shutil.copy(REPO / "library/leads/pending_leads.json", paths["leads"])
    ew.WATCHES_PATH = paths["watches"]
    real_leads_load, real_leads_save = leads_mod.load, leads_mod.save
    real_todo_load, real_todo_save = todo.load, todo.save
    leads_mod.load = lambda path=None: real_leads_load(path or paths["leads"])
    leads_mod.save = lambda store, path=None: real_leads_save(store, path or paths["leads"])
    todo.load = lambda path=None: real_todo_load(path or paths["pool"])
    todo.save = lambda pool, path=None: real_todo_save(pool, path or paths["pool"])
    return paths


def next_event_day(after: date, until: date) -> date | None:
    days = set()
    for w in ew.load_watches()["watches"]:
        if w.get("status") == "active":
            try:
                days.add(date.fromisoformat(str(w["expires"])) + timedelta(days=1))
            except ValueError:
                pass
    for entry in dp.load_lifecycle().values():
        if isinstance(entry, dict) and entry.get("next_check"):
            try:
                days.add(date.fromisoformat(str(entry["next_check"])))
            except ValueError:
                pass
    future = sorted(d for d in days if after < d <= until)
    return future[0] if future else None


def run_day(day: date) -> dict:
    SIM[0] = day
    report: dict = {"day": day.isoformat()}
    # ⑨ consume-fired（與 engine_b.cli._cmd_consume_fired 同一組呼叫）
    store = leads_mod.load()
    data = ew.load_watches()
    fired = leads_mod.consume_fired_lead_watches(store, data)
    newly = ew.mark_expired(data)
    closed = leads_mod.close_expired_trace_watches(store, data)
    leads_mod.save(store)
    ew.save_watches(data)
    report["expired_today"] = len(newly)
    report["trace"] = Counter(c["outcome"] for c in closed)
    report["fired_requeued"] = len(fired.get("requeued") or [])
    # ⑩ todo sync（與 CLI 同一順序：先對帳再收集）
    pool = todo.load()
    before = {i["n"] for i in pool["items"]}
    todo.retire_legacy_pq1_items(pool)
    reconciled = todo._reconcile_disproof()
    collected = todo.collect_all_with_health()
    result = todo.sync(pool, collected.rows, healthy_sources=collected.healthy, reconciled=reconciled)
    todo.save(pool)
    report["new_items"] = [(i["n"], i["type"], i["title"]) for i in pool["items"] if i["n"] not in before]
    report["reconcile"] = {k: len(v) for k, v in (reconciled or {}).items() if isinstance(v, list)}
    report["log_verbs"] = Counter(e["verb"] for e in pool["log"] if str(e.get("at", ""))[:10] == day.isoformat())
    # 心跳第 2、3 段（相關行）
    lines = []
    try:
        lines += hb._disproof_lines()
    except Exception as exc:  # noqa: BLE001
        lines.append(f"（反證行失敗：{type(exc).__name__}: {exc}）")
    try:
        section = hb.build_queue(now=FakeDatetime.now(timezone.utc))
        lines += [ln for ln in section.lines if "watch 到期" in ln or "球在你" in ln or "無到期的等待" in ln]
    except Exception as exc:  # noqa: BLE001
        lines.append(f"（段 3 失敗：{type(exc).__name__}: {exc}）")
    report["heartbeat"] = lines
    report["actionable"] = [(i["n"], i["type"]) for i in todo.actionable_items(pool)]
    report["result_added"] = result.get("added")
    return report


def simulate_user(pool_items: list[tuple], day: date) -> list[str]:
    """第一次出現 watch_decision 的那天，模擬使用者對前三個編號的三種回答。"""
    pool = todo.load()
    open_decisions = [i for i in pool["items"] if i["type"] == "watch_decision" and not i.get("resolved_at")]
    notes = []
    actions = [("pending", {"until": (day + timedelta(days=90)).isoformat(), "reason": "試跑：續等一季"}),
               ("drop", {"reason": "試跑：放棄"}),
               ("go", {"receipt": "outcome:touched;report:docs/reports/2026-09-24-phase1-baseline.md",
                       "quote": "（試跑用的假原文）", "reason": "試跑：研究後判定觸及"})]
    for item, (verb, kwargs) in zip(open_decisions, actions):
        try:
            done = todo.resolve(pool, item["n"], verb, **kwargs)
            notes.append(f"[{item['n']}] {verb} → resolution={done['resolution']}｜{item['title'][:60]}")
        except todo.TodoError as exc:
            notes.append(f"[{item['n']}] {verb} ✗ {exc}")
    todo.save(pool)
    return notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--until", default="2027-10-01")
    ap.add_argument("--no-actions", action="store_true")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="暫存副本與時間線輸出目錄（會先清空）")
    args = ap.parse_args()
    global OUT
    OUT = Path(args.out)
    if OUT.resolve() == (REPO / "library" / "leads").resolve():
        raise SystemExit("--out 不得是 library/leads（那是真檔）")
    until = date.fromisoformat(args.until)
    real = {p: (REPO / p).read_bytes() for p in ("library/leads/event_watches.json", "library/leads/todo_pool.json",
                                                  "library/leads/pending_leads.json")}
    install_copies()
    install_clock()
    out_lines = [f"# 試跑：等待系統快轉（起點 {SIM[0]}，到 {until}；真實資料的暫存副本）", ""]
    baseline = run_day(SIM[0])
    out_lines += [f"## {baseline['day']}（起點，今天）", *[f"- {ln}" for ln in baseline["heartbeat"]], ""]
    acted = args.no_actions
    day = SIM[0]
    while True:
        nxt = next_event_day(day, until)
        if nxt is None:
            break
        day = nxt
        rep = run_day(day)
        if not (rep["expired_today"] or rep["new_items"] or rep["trace"] or rep["log_verbs"]):
            continue
        out_lines.append(f"## {rep['day']}")
        out_lines.append(f"- 今天轉到期 {rep['expired_today']}｜追源結案 {dict(rep['trace']) or 0}"
                         f"｜對帳 {rep['reconcile']}｜池 log {dict(rep['log_verbs']) or 0}")
        for n, t, title in rep["new_items"]:
            out_lines.append(f"- 新編號 [{n}] {t}：{title}")
        out_lines += [f"- 心跳｜{ln}" for ln in rep["heartbeat"]]
        if not acted and any(t == "watch_decision" for _n, t, _ in rep["new_items"]):
            out_lines += [f"- 模擬使用者｜{ln}" for ln in simulate_user(rep["new_items"], day)]
            acted = True
        out_lines.append("")
    # 真檔一個 byte 都不能動
    for rel, blob in real.items():
        assert (REPO / rel).read_bytes() == blob, f"真檔被動到了：{rel}"
    out_lines.append("（檢查：三份真檔 byte 相同，未被動到）")
    text = "\n".join(out_lines)
    (OUT / "timeline.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
