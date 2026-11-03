"""入圖包隨機抽查（盲點修法第 20 條，2026-11-03；使用者 11-02：「隨機抽查 開subagent這件事 其實你就當成我是開綠燈吧」）。

使用者問「我很相信你的建議，你該怎麼替我把關?」——把關四層：①apply 入口的程式檢查（既有）②每包第一行只寫要你判斷的
一句（`engine_b.todo.judgment_text`）③**抽樣**④**計數器**。後兩層住這裡：

- **抽樣**：每個 `ra_admission` 編號抽不抽中由編號本身決定（`sampled`）——種子是編號，可重現、誰都挑不了哪一包被核。
  每 `EVERY` 包抽 1；上個月「事後抓到包內缺陷 K>0 而偏離 M=0」（使用者照建議走、包裡卻有錯）這個月就加密成每 `EVERY_DENSE`
  包抽 1（加密時抽中的集合只變大、不換人）。`RULE_START` 之前鑄的包不在母體（不回溯）。
- **核**：抽中的包交乾淨 context 的唯讀 reviewer 從頭核（AGENTS 研究側唯一的常規 opt-in；流程住 skills/research-drain），
  回 review packet；互動 session 把結果 `record` 成帳上一列（`docs/feedback/admission-audit.jsonl`，tracked、append-only）。
  使用者 drop 掉的包不必再核（gate 已經說不）。抽中、還沒核的是 ⑤ 一格（`todo.admission_audit`）。
- **計數器**：本月照建議 N／偏離 M／沒寫建議 U——讀 `todo_pool.json` 既有的 `recommendation.verb` 與 `resolution`
  （零 schema 變更），全部入圖包、不限抽樣母體——／事後抓到包內缺陷 K（這本帳裡當月有缺陷的列：抽查核出的，加上任何人
  事後發現的）。短版 ④ 每天一行。

**抽中與否、核出什麼都不改 gate**：入圖仍是人工 `go`；reviewer 不寫任何東西、不核准（AGENTS「四個人工 gate」）。
帳的一列（形狀封閉）：`n`（入圖包的 pq2 編號）｜`date`（核完或發現的那天）｜`found_by`（`抽查`：抽中的那一次；`事後`：
任何時候發現包裡有錯）｜`verdict`（`乾淨`／`有缺陷`）｜`defects`（缺陷逐條；乾淨就是空 list）｜`note`（乾淨：核了什麼；
有缺陷：怎麼處理、記在哪——取代的新編號、commit、failure log）。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = _ROOT / "docs" / "feedback" / "admission-audit.jsonl"

#: 規則起算日：之前鑄的入圖包不在抽樣母體（不回溯）。
RULE_START = date(2026, 11, 3)
EVERY = 10
EVERY_DENSE = 5
ADMISSION_TYPE = "ra_admission"
FOUND_BY: tuple[str, ...] = ("抽查", "事後")
VERDICTS: tuple[str, ...] = ("乾淨", "有缺陷")
FIELDS: tuple[str, ...] = ("n", "date", "found_by", "verdict", "defects", "note")
#: 每個入圖包在抽查上的狀態（封閉字彙；`engine_b.todo_ledger.COVERAGE` 逐一登記去處）。
AUDIT_STATES: tuple[str, ...] = ("not_sampled", "sampled_unreviewed", "reviewed", "dropped")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True, slots=True)
class AuditRow:
    n: int
    date: date
    found_by: str
    verdict: str
    defects: tuple[str, ...]
    note: str


def sampled(n: int, every: int) -> bool:
    """編號 n 在「每 every 包抽 1」下是否抽中。種子是編號：可重現、誰都挑不了；every 變小時集合只變大
    （每 10 抽中的，每 5 一定也抽中）。"""
    return random.Random(f"admission-audit:{int(n)}").random() < 1.0 / every


def _local_day(stamp: Any) -> date | None:
    """pool 的時戳是 UTC ISO；月份與起算日照本機日期算（使用者看的是本機的「今天」）。讀不懂回 None。"""
    text = str(stamp or "").strip()
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.astimezone().date() if moment.tzinfo else moment.date()


def _month(day: date | None) -> str | None:
    return day.strftime("%Y-%m") if day else None


def _previous_month(month: str) -> str:
    year, mon = (int(part) for part in month.split("-"))
    return f"{year - 1}-12" if mon == 1 else f"{year}-{mon - 1:02d}"


# ---------------------------------------------------------------------------
# 帳：合約與讀寫
# ---------------------------------------------------------------------------

def parse_row(raw: Any) -> AuditRow:
    """一列 → `AuditRow`；任何一欄不合就 `ValueError`，訊息說哪一欄、為什麼。"""
    if not isinstance(raw, Mapping):
        raise ValueError("這一列不是 object")
    extra, missing = sorted(set(raw) - set(FIELDS)), [k for k in FIELDS if k not in raw]
    if extra or missing:
        raise ValueError(f"欄位不合：多了 {extra}、少了 {missing}（形狀封閉）")
    n = raw["n"]
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError(f"n 要是入圖包的 pq2 編號（正整數）：{n!r}")
    day = str(raw["date"])
    if not _DATE.match(day):
        raise ValueError(f"date 要是 YYYY-MM-DD：{day!r}")
    try:
        parsed_day = date.fromisoformat(day)
    except ValueError as exc:
        raise ValueError(f"date 讀不懂：{day!r}") from exc
    if raw["found_by"] not in FOUND_BY:
        raise ValueError(f"found_by 只收 {list(FOUND_BY)}：{raw['found_by']!r}")
    if raw["verdict"] not in VERDICTS:
        raise ValueError(f"verdict 只收 {list(VERDICTS)}：{raw['verdict']!r}")
    defects = raw["defects"]
    if not isinstance(defects, list) or not all(isinstance(d, str) and d.strip() for d in defects):
        raise ValueError("defects 要是字串 list（每條非空）")
    if (raw["verdict"] == "有缺陷") != bool(defects):
        raise ValueError("verdict 與 defects 不一致：有缺陷要逐條寫，乾淨就是空 list")
    note = raw["note"]
    if not isinstance(note, str) or not note.strip():
        raise ValueError("note 不得是空的（乾淨：核了什麼；有缺陷：怎麼處理、記在哪）")
    return AuditRow(n=n, date=parsed_day, found_by=raw["found_by"], verdict=raw["verdict"],
                    defects=tuple(d.strip() for d in defects), note=note.strip())


def load_ledger(path: Path | None = None) -> tuple[list[AuditRow], list[str]]:
    """讀整本：(解析得到的列, 問題清單)。**壞行不靜默丟**（INV-3）；另驗日期不倒退（append-only）、
    同一包的抽查只能一列。檔案不存在是問題、不是空帳（未讀到 ≠ 0）。"""
    target = path or LEDGER_PATH
    if not target.is_file():
        return [], [f"{target.name} 不存在"]
    rows: list[AuditRow] = []
    problems: list[str] = []
    for number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            problems.append(f"第 {number} 行是空行（append-only 的一本不該有空行）")
            continue
        try:
            rows.append(parse_row(json.loads(line)))
        except ValueError as exc:
            problems.append(f"第 {number} 行：{exc}")
    for prev, row in zip(rows, rows[1:]):
        if row.date < prev.date:
            problems.append(f"[{row.n}] 的日期 {row.date} 早於前一列 {prev.date}（append-only 不倒退）")
    seen: set[int] = set()
    for row in rows:
        if row.found_by == "抽查":
            if row.n in seen:
                problems.append(f"[{row.n}] 抽查記了兩次（一包只核一次；之後發現的寫 事後）")
            seen.add(row.n)
    return rows, problems


# ---------------------------------------------------------------------------
# 抽樣、狀態與計數
# ---------------------------------------------------------------------------

def _admissions(items: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [i for i in items if str(i.get("type") or "") == ADMISSION_TYPE]


def month_counts(items: Iterable[Mapping[str, Any]], rows: Sequence[AuditRow], month: str) -> dict[str, int]:
    """某個月：照建議 followed／偏離 deviated／沒寫建議 unrecommended（當月結案的入圖包；全部、不限母體）＋
    事後抓到包內缺陷 defects（帳上當月有缺陷的列）。"""
    counts = {"followed": 0, "deviated": 0, "unrecommended": 0, "defects": 0}
    for item in _admissions(items):
        if _month(_local_day(item.get("resolved_at"))) != month:
            continue
        verb = (item.get("recommendation") or {}).get("verb")
        if verb not in ("go", "drop", "pending"):
            counts["unrecommended"] += 1
        elif verb == item.get("resolution"):
            counts["followed"] += 1
        else:
            counts["deviated"] += 1
    counts["defects"] = sum(1 for r in rows if r.verdict == "有缺陷" and _month(r.date) == month)
    return counts


def every_for(month: str, items: Sequence[Mapping[str, Any]], rows: Sequence[AuditRow]) -> int:
    """這個月每幾包抽 1：上個月 K>0 而 M=0 → `EVERY_DENSE`，否則 `EVERY`。"""
    prev = month_counts(items, rows, _previous_month(month))
    return EVERY_DENSE if prev["defects"] > 0 and prev["deviated"] == 0 else EVERY


def audit_states(items: Sequence[Mapping[str, Any]], rows: Sequence[AuditRow]) -> list[dict[str, Any]]:
    """母體（`RULE_START` 起鑄的入圖包）每一包的抽查狀態：抽不抽中照它鑄號那個月的比例算。"""
    reviewed = {r.n for r in rows if r.found_by == "抽查"}
    out: list[dict[str, Any]] = []
    for item in _admissions(items):
        added = _local_day(item.get("added_at"))
        if added is None or added < RULE_START:
            continue
        n = int(item["n"])
        every = every_for(_month(added) or "", items, rows)
        if not sampled(n, every):
            state = "not_sampled"
        elif n in reviewed:
            state = "reviewed"
        elif item.get("resolved_at") and item.get("resolution") == "drop":
            state = "dropped"
        else:
            state = "sampled_unreviewed"
        out.append({"n": n, "state": state, "every": every, "title": str(item.get("title") or ""),
                    "resolved": bool(item.get("resolved_at"))})
    return out


def status(items: Sequence[Mapping[str, Any]], rows: Sequence[AuditRow], *, today: date) -> dict[str, Any]:
    """心跳與 CLI 共用的一份：本月計數、本月比例、母體每一包的狀態、抽中待核的編號。"""
    month = _month(today) or ""
    states = audit_states(items, rows)
    return {"month": month, "every": every_for(month, items, rows), "counts": month_counts(items, rows, month),
            "states": states, "unreviewed": [s["n"] for s in states if s["state"] == "sampled_unreviewed"]}


def status_line(report: Mapping[str, Any], problems: Sequence[str] = ()) -> str:
    """短版 ④ 的一行（每天印；0 也印——L14 常駐）。帳讀不到就說讀不到，計數照印（它們來自 pool）。"""
    c = report["counts"]
    month = int(str(report["month"]).split("-")[1])
    unreviewed = report["unreviewed"]
    tail = f"抽中待核 {len(unreviewed)}（{'、'.join(f'[{n}]' for n in unreviewed)}）" if unreviewed else "抽中待核 0"
    line = (f"入圖包 {month} 月：照建議 {c['followed']}｜偏離 {c['deviated']}｜沒寫建議 {c['unrecommended']}｜"
            f"事後抓到包內缺陷 {c['defects']}｜每 {report['every']} 包抽 1、{tail}")
    if problems:
        line += f"｜⚠ 抽查帳有 {len(problems)} 個問題（{problems[0]}）——缺陷數可能少算"
    return line


def short_line(*, today: date, pool_path: Path | None = None, ledger_path: Path | None = None) -> str:
    """短版 ④ 呼叫的入口：讀 pool 與帳、組 `status_line`。"""
    from engine_b import todo as todo_mod

    pool = todo_mod.load(pool_path) if pool_path else todo_mod.load()
    rows, problems = load_ledger(ledger_path)
    return status_line(status(pool.get("items") or [], rows, today=today), problems)


# ---------------------------------------------------------------------------
# 寫：互動 session 核完記一列
# ---------------------------------------------------------------------------

def record(*, n: int, found_by: str, verdict: str, defects: Sequence[str], note: str, today: date,
           items: Sequence[Mapping[str, Any]], path: Path | None = None) -> AuditRow:
    """append 一列。拒收：不是入圖包的編號；`抽查` 卻不在母體或沒抽中（常規 opt-in 只涵蓋抽中的包——沒抽中的包要
    reviewer 是另一次委派，要使用者逐次 opt-in）；同一包抽查第二次；帳本身有問題（先修帳再寫）。"""
    target = path or LEDGER_PATH
    item = next((i for i in _admissions(items) if int(i.get("n") or 0) == int(n)), None)
    if item is None:
        raise ValueError(f"[{n}] 不是入圖包（ra_admission）的編號")
    rows, problems = load_ledger(target)
    if problems:
        raise ValueError(f"抽查帳有問題、先修再寫：{problems[0]}")
    if found_by == "抽查":
        state = next((s for s in audit_states(items, rows) if s["n"] == int(n)), None)
        if state is None or state["state"] == "not_sampled":
            raise ValueError(f"[{n}] 沒有抽中（或在 {RULE_START} 前鑄號）：抽查只收抽中的包；"
                             "事後發現的缺陷寫 --found-by 事後")
        if state["state"] == "reviewed":
            raise ValueError(f"[{n}] 已經抽查過；之後發現的缺陷寫 --found-by 事後")
    raw = {"n": int(n), "date": today.isoformat(), "found_by": found_by, "verdict": verdict,
           "defects": [" ".join(d.split()) for d in defects], "note": " ".join(str(note or "").split())}
    row = parse_row(raw)
    if rows and row.date < rows[-1].date:
        raise ValueError(f"日期 {row.date} 早於帳上最後一列 {rows[-1].date}（append-only 不倒退）")
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(raw, ensure_ascii=False) + "\n")
    return row


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m engine_b.admission_audit", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p_status = sub.add_parser("status", help="本月計數、比例、抽中待核的編號")
    p_status.add_argument("--json", action="store_true")
    p_rec = sub.add_parser("record", help="核完記一列（互動 session；reviewer 本身不寫）")
    p_rec.add_argument("n", type=int)
    p_rec.add_argument("--found-by", required=True, choices=FOUND_BY)
    p_rec.add_argument("--verdict", required=True, choices=VERDICTS)
    p_rec.add_argument("--defect", action="append", default=[], help="缺陷一條（可重複）；乾淨就不給")
    p_rec.add_argument("--note", required=True, help="乾淨：核了什麼；有缺陷：怎麼處理、記在哪")
    args = ap.parse_args(argv)

    from engine_b import todo as todo_mod

    items = todo_mod.load().get("items") or []
    today = date.today()
    if args.command == "status":
        rows, problems = load_ledger()
        report = status(items, rows, today=today)
        if args.json:
            print(json.dumps({**report, "problems": problems}, ensure_ascii=False, indent=2))
            return 0
        print(status_line(report, problems))
        for state in report["states"]:
            if state["state"] != "not_sampled":
                print(f"  [{state['n']}] {state['state']}（每 {state['every']} 抽 1）{state['title'][:60]}")
        for problem in problems:
            print(f"  ⚠ {problem}")
        return 1 if problems else 0
    try:
        row = record(n=args.n, found_by=args.found_by, verdict=args.verdict, defects=args.defect, note=args.note,
                     today=today, items=items)
    except ValueError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    print(f"✓ [{row.n}] {row.found_by}：{row.verdict}" + (f"（{len(row.defects)} 條缺陷）" if row.defects else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["ADMISSION_TYPE", "AUDIT_STATES", "AuditRow", "EVERY", "EVERY_DENSE", "FIELDS", "FOUND_BY", "LEDGER_PATH",
           "RULE_START", "VERDICTS", "audit_states", "every_for", "load_ledger", "month_counts", "parse_row", "record",
           "sampled", "short_line", "status", "status_line"]
