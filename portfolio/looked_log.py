"""看了沒買（盲點修法第 17 條，2026-11-03；AGENTS「沒買也是決定」）——A5：「當時憑什麼沒買」。

決策時段看過的那一檔，使用者選了 **不要** 或 **等到條件**，連一句理由與當時的敘事版本記下來；選 **進** 的走成交
（`scripts/record_trade.py`，同一種研究收據）。三種選擇因此都留得下：進＝成交事件，其餘兩種＝這本。

- 住 `library/trades/looked_log.jsonl`——與 trade_log 同處、tracked、append-only；一列＝一次決定。寫入的唯一入口是
  `python scripts/record_trade.py looked`（與成交同一支、同一個收據組法 `portfolio.research_receipt.build_receipt`，
  `side`＝看了沒買：當時的敘事宣告＋當天候選板與個股頁的推導）。
- **寫入端拒收**：缺理由；缺敘事版本（現行不是 v2 敘事——「沒買」要指得出當時讀的是哪一版）；選擇不在封閉字彙；
  公司解析不到（INV-1）；同一筆重寫。
- **系統不由它產生任何動作、不由它算尺寸**（A3 不替 A5 做決定）。讀者只有計數：短版 ④ 每天一行「你的決定」——
  決定紀錄 §10.1 停止條件第一子句（可開名單非空、而使用者的決定為 0 筆）量的就是它。

一列的形狀（封閉）：`kind`（固定「看了沒買」）｜`decision_id`（`lk_`＋內容雜湊）｜`recorded_at`（UTC）｜`date`（排程時區的
那天）｜`symbol`（下指令時給的代號）｜`company_id`｜`research_ticker`｜`choice`（不要／等到條件）｜`why`（一句理由；等到條件
要寫等到什麼）｜`brief_id`（當時現行的 v2 敘事）｜`research_receipt`（整份收據）。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_ROOT = Path(__file__).resolve().parents[1]
LOOKED_LOG = _ROOT / "library" / "trades" / "looked_log.jsonl"

KIND = "看了沒買"
CHOICES: tuple[str, ...] = ("不要", "等到條件")
#: 「你的決定」那一行的三格：進（alpha 成交買進）＋這本的兩種。
DECISION_LABELS: tuple[str, ...] = ("進", *CHOICES)
FIELDS: tuple[str, ...] = ("kind", "decision_id", "recorded_at", "date", "symbol", "company_id", "research_ticker",
                           "choice", "why", "brief_id", "research_receipt")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True, slots=True)
class LookedEntry:
    decision_id: str
    recorded_at: datetime
    date: date
    symbol: str
    company_id: str
    research_ticker: str | None
    choice: str
    why: str
    brief_id: str


def _decision_id(*, day: str, company_id: str, choice: str, brief_id: str, why: str) -> str:
    body = json.dumps({"date": day, "company_id": company_id, "choice": choice, "brief_id": brief_id, "why": why},
                      ensure_ascii=False, sort_keys=True)
    return "lk_" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def build_entry(*, symbol: str, choice: str, why: str, today: date, recorded_at: str,
                receipt: Mapping[str, Any]) -> dict[str, Any]:
    """一次決定 → 一列。`receipt`：`research_receipt.build_receipt` 組好的那一份。不合就 `ValueError`（說哪裡不合）。"""
    if choice not in CHOICES:
        raise ValueError(f"選擇只收 {list(CHOICES)}（「進」走成交：record_trade.py --side buy）——收到 {choice!r}")
    text = " ".join(str(why or "").split())
    if not text:
        raise ValueError("缺理由：看了沒買要附一句為什麼（等到條件要寫等到什麼）")
    declared = receipt.get("declared") if isinstance(receipt.get("declared"), Mapping) else {}
    brief_id = str((declared or {}).get("brief_id") or "")
    if receipt.get("narrative") != "present" or not brief_id:
        raise ValueError(f"缺敘事版本：現行不是 v2 敘事（{receipt.get('narrative_label') or receipt.get('narrative')}）"
                         "——「沒買」要指得出當時讀的是哪一版；先寫敘事再記")
    company_id = str(receipt.get("company_id") or "")
    if not company_id:
        raise ValueError(f"{symbol} 解析不到公司（INV-1：不猜）")
    day = today.isoformat()
    entry = {"kind": KIND, "decision_id": _decision_id(day=day, company_id=company_id, choice=choice,
                                                       brief_id=brief_id, why=text),
             "recorded_at": recorded_at, "date": day, "symbol": str(symbol).strip(), "company_id": company_id,
             "research_ticker": receipt.get("research_ticker"), "choice": choice, "why": text, "brief_id": brief_id,
             "research_receipt": dict(receipt)}
    parse_entry(entry)
    return entry


def parse_entry(raw: Any) -> LookedEntry:
    """一列 → `LookedEntry`；任何一欄不合就 `ValueError`。"""
    if not isinstance(raw, Mapping):
        raise ValueError("這一列不是 object")
    extra, missing = sorted(set(raw) - set(FIELDS)), [k for k in FIELDS if k not in raw]
    if extra or missing:
        raise ValueError(f"欄位不合：多了 {extra}、少了 {missing}（形狀封閉）")
    if raw["kind"] != KIND:
        raise ValueError(f"kind 只收 {KIND!r}：{raw['kind']!r}")
    if raw["choice"] not in CHOICES:
        raise ValueError(f"choice 只收 {list(CHOICES)}：{raw['choice']!r}")
    for key in ("why", "symbol", "company_id"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise ValueError(f"{key} 不得是空的")
    if not str(raw["brief_id"]).startswith("ib_"):
        raise ValueError(f"brief_id 要是敘事版本（ib_…）：{raw['brief_id']!r}")
    if not str(raw["decision_id"]).startswith("lk_"):
        raise ValueError(f"decision_id 要以 lk_ 開頭：{raw['decision_id']!r}")
    day = str(raw["date"])
    if not _DATE.match(day):
        raise ValueError(f"date 要是 YYYY-MM-DD：{day!r}")
    receipt = raw["research_receipt"]
    if not isinstance(receipt, Mapping) or receipt.get("narrative") != "present":
        raise ValueError("research_receipt 要是整份收據、而且當時有現行 v2 敘事")
    try:
        recorded = datetime.fromisoformat(str(raw["recorded_at"]))
    except ValueError as exc:
        raise ValueError(f"recorded_at 讀不懂：{raw['recorded_at']!r}") from exc
    if recorded.tzinfo is None:
        raise ValueError("recorded_at 必須帶時區")
    return LookedEntry(decision_id=str(raw["decision_id"]), recorded_at=recorded, date=date.fromisoformat(day),
                       symbol=raw["symbol"], company_id=raw["company_id"],
                       research_ticker=raw.get("research_ticker"), choice=raw["choice"], why=raw["why"],
                       brief_id=str(raw["brief_id"]))


def load(path: Path | None = None) -> tuple[list[LookedEntry], list[str]]:
    """讀整本：(列, 問題)。檔案不存在＝還沒有任何一次決定（與 trade_log 同一個語意）；壞行不靜默丟（INV-3）；
    同一個 decision_id 出現兩次也是問題（重寫）。"""
    target = path or LOOKED_LOG
    if not target.is_file():
        return [], []
    entries: list[LookedEntry] = []
    problems: list[str] = []
    seen: set[str] = set()
    for number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = parse_entry(json.loads(line))
        except ValueError as exc:
            problems.append(f"looked_log 第 {number} 行：{exc}")
            continue
        if entry.decision_id in seen:
            problems.append(f"looked_log 第 {number} 行：{entry.decision_id} 重複（同一次決定寫了兩次）")
        seen.add(entry.decision_id)
        entries.append(entry)
    return entries, problems


def already_recorded(entry: Mapping[str, Any], path: Path | None = None) -> bool:
    entries, _problems = load(path)
    return any(e.decision_id == entry["decision_id"] for e in entries)


def append(entry: Mapping[str, Any], path: Path | None = None) -> Path:
    """append 一列（已由 `build_entry` 驗過）；只 append，永不改寫既有行。"""
    parse_entry(entry)
    target = path or LOOKED_LOG
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(entry), ensure_ascii=False, sort_keys=True) + "\n")
    return target


# ---------------------------------------------------------------------------
# 讀者：「你的決定」計數（停止條件第一子句）
# ---------------------------------------------------------------------------

def _local_day(stamp: Any) -> date | None:
    from portfolio.research_receipt import _local_date

    return _local_date(stamp)


def month_counts(entries: Iterable[LookedEntry], trade_events: Iterable[Mapping[str, Any]], month: str) -> dict[str, int]:
    """某個月的三種決定：進＝trade_log 裡帶研究收據的買進（alpha；beta 不帶收據）、其餘兩種＝這本。"""
    counts = {label: 0 for label in DECISION_LABELS}
    for event in trade_events:
        if event.get("side") == "buy" and isinstance(event.get("research_receipt"), Mapping):
            day = _local_day(event.get("executed_at"))
            if day is not None and day.strftime("%Y-%m") == month:
                counts["進"] += 1
    for entry in entries:
        if entry.date.strftime("%Y-%m") == month:
            counts[entry.choice] += 1
    return counts


def status_line(counts: Mapping[str, int], *, month: str, problems: Sequence[str] = ()) -> str:
    """短版 ④ 的一行（每天印；0 也印——L14 常駐）。"""
    line = (f"你的決定 {int(month.split('-')[1])} 月：" + "｜".join(f"{label} {counts.get(label, 0)}"
                                                               for label in DECISION_LABELS)
            + "（看了沒買照 record_trade.py looked 記；系統不由它產生動作）")
    if problems:
        line += f"｜⚠ 帳有 {len(problems)} 個問題（{problems[0]}）——可能少算"
    return line


def short_line(*, today: date, looked_path: Path | None = None, trade_path: Path | None = None) -> str:
    """短版 ④ 呼叫的入口：讀這本與 trade_log、組 `status_line`。"""
    entries, problems = load(looked_path)
    trade = trade_path or (_ROOT / "library" / "trades" / "trade_log.jsonl")
    events: list[Mapping[str, Any]] = []
    if trade.is_file():
        for number, line in enumerate(trade.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError:
                problems.append(f"trade_log 第 {number} 行解析失敗")
                continue
            if isinstance(event, Mapping):
                events.append(event)
    month = today.strftime("%Y-%m")
    return status_line(month_counts(entries, events, month), month=month, problems=problems)


__all__ = ["CHOICES", "DECISION_LABELS", "FIELDS", "KIND", "LOOKED_LOG", "LookedEntry", "already_recorded", "append",
           "build_entry", "load", "month_counts", "parse_entry", "short_line", "status_line"]
