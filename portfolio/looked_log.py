"""看了沒買（盲點修法第 17 條，2026-11-03；AGENTS「沒買也是決定」）——A5：「當時憑什麼沒買」。

決策時段看過的那一檔，使用者選了 **不要** 或 **等到條件**，連一句理由與當時的敘事版本記下來；選 **進** 的走成交
（`scripts/record_trade.py`，同一種研究收據）。三種選擇因此都留得下：進＝成交事件，其餘兩種＝這本。

- 住 `library/trades/looked_log.jsonl`——與 trade_log 同處、tracked、append-only；一列＝一次決定。寫入的唯一入口是
  `python scripts/record_trade.py looked`（與成交同一支、同一個收據組法 `portfolio.research_receipt.build_receipt`，
  `side`＝看了沒買：當時的敘事宣告＋當天候選板與個股頁的推導）。
- **寫入端拒收**：缺理由；公司解析不到（INV-1）；缺敘事版本（現行不是 v2 敘事——「沒買」要指得出當時讀的是哪一版）；
  **候選板上那一列不是現行那一版**（板讀不到、不是今天的、板上沒有這一檔、或那一列的敘事版本 ≠ 現行——2026-11-04 R2 B1：
  記下的必須是你在板上讀的那一版，否則「可開待你選」會把你沒看過的新版當成選過；INV-6）；選擇不在封閉字彙；「不要」帶到期；
  等到的日子不在今天之後；同一版敘事的同一個選擇還在生效時重記（`repeat_of`）。
- **等到條件有到期**（11-04 R2；INV-2「每個等待都必須有到期」）：`until`，不給＝`WAIT_DEFAULT_DAYS` 天後。到期那天起
  「可開待你選」把它列回來重問（附上次等的是什麼）；敘事換版也重問。這筆等待住這本帳、**不進等待 registry**——registry 的
  喚醒目標是封閉字彙，為它加一種要動 contract（2026-11-04 使用者核准的例外）；補償是短版 ③ 每天一句「等到條件 M 檔在等」。
- **系統不由它產生任何動作、不由它算尺寸**（A3 不替 A5 做決定）。讀者兩個：①短版 ④ 每天一行「你的決定」——決定紀錄 §10.1
  停止條件第一子句（可開名單非空、而使用者的決定為 0 筆）量的就是它，所以**只數當時是可開的**（收據裡候選板那一列的組；
  11-04 R2：加碼買進、對缺 X 的「不要」混進來會蓋掉它），其餘另列、不藏（INV-3）；②「可開待你選」
  （`crons.heartbeat.open_choice_rows`）讀 `standing`／`hides`。

一列的形狀（封閉）：`kind`（固定「看了沒買」）｜`decision_id`（`lk_`＋內容雜湊）｜`recorded_at`（UTC）｜`date`（排程時區的
那天）｜`symbol`（下指令時給的代號）｜`company_id`｜`research_ticker`｜`choice`（不要／等到條件）｜`why`（一句理由；等到條件
要寫等到什麼）｜`until`（等到條件重問的那天；不要＝null）｜`brief_id`（當時現行、也是候選板上那一版的 v2 敘事）｜
`research_receipt`（整份收據）。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_ROOT = Path(__file__).resolve().parents[1]
LOOKED_LOG = _ROOT / "library" / "trades" / "looked_log.jsonl"

KIND = "看了沒買"
CHOICES: tuple[str, ...] = ("不要", "等到條件")
#: 「你的決定」那一行的三格：進（alpha 成交買進）＋這本的兩種。
DECISION_LABELS: tuple[str, ...] = ("進", *CHOICES)
#: 等到條件沒給日子時等幾天（INV-2：每個等待都有到期；到期是重問、不是丟）。
WAIT_DEFAULT_DAYS = 30
FIELDS: tuple[str, ...] = ("kind", "decision_id", "recorded_at", "date", "symbol", "company_id", "research_ticker",
                           "choice", "why", "until", "brief_id", "research_receipt")
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
    until: date | None
    brief_id: str
    #: 當時候選板那一列在不在「可開」組（收據的 `derived.candidate.group`）；收據沒有那一列＝None（分不出，不猜）。
    was_open: bool | None


def receipt_was_open(receipt: Any) -> bool | None:
    """收據記下的候選板那一列在不在「可開」組——成交與看了沒買共用（「你的決定」只數當時是可開的）。沒有那一列＝None。"""
    derived = receipt.get("derived") if isinstance(receipt, Mapping) else None
    row = derived.get("candidate") if isinstance(derived, Mapping) else None
    if not isinstance(row, Mapping):
        return None
    return row.get("group") == "open"


def board_problem(receipt: Mapping[str, Any], brief_id: str) -> str | None:
    """候選板上那一列是不是現行那一版（11-04 R2 B1；INV-6）——回拒收理由，None＝是。看了沒買不是成交，擋下不卡任何錢，
    所以這裡 fail closed（成交的收據遇到同一件事只記 upstream_unavailable、不擋，plan §0 第 13 條）。"""
    derived = receipt.get("derived") if isinstance(receipt.get("derived"), Mapping) else {}
    row = derived.get("candidate")
    if not isinstance(row, Mapping):
        why = (derived.get("candidate_note") if "candidate_as_of" in derived
               else f"候選板讀不到或不是今天的：{derived.get('reason') or '缺席'}")
        return (f"候選板上找不到你讀的那一版（{why}）——看了沒買記的是你在候選板（短版 ③／APP）上讀的那一版敘事；"
                "先跑 python -m webapp materialize --candidates、讀過再記")
    if row.get("brief_id") != brief_id:
        return (f"候選板上那一列是敘事 {row.get('brief_id') or '（無）'}、現行是 {brief_id}——你讀到的是舊版"
                "（候選板早於這次敘事寫入）；先重跑 python -m webapp materialize --candidates、讀新版再記")
    return None


def _decision_id(*, day: str, company_id: str, choice: str, brief_id: str, why: str, until: str | None) -> str:
    body = json.dumps({"date": day, "company_id": company_id, "choice": choice, "brief_id": brief_id, "why": why,
                       "until": until}, ensure_ascii=False, sort_keys=True)
    return "lk_" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def build_entry(*, symbol: str, choice: str, why: str, today: date, recorded_at: str,
                receipt: Mapping[str, Any], until: date | None = None) -> dict[str, Any]:
    """一次決定 → 一列。`receipt`：`research_receipt.build_receipt` 組好的那一份；`until`：等到條件重問的那天（不給＝
    `WAIT_DEFAULT_DAYS` 天後）。不合就 `ValueError`（說哪裡不合）。"""
    if choice not in CHOICES:
        raise ValueError(f"選擇只收 {list(CHOICES)}（「進」走成交：record_trade.py --side buy）——收到 {choice!r}")
    text = " ".join(str(why or "").split())
    if not text:
        raise ValueError("缺理由：看了沒買要附一句為什麼（等到條件要寫等到什麼）")
    company_id = str(receipt.get("company_id") or "")
    if not company_id:
        raise ValueError(f"{symbol} 解析不到公司（INV-1：不猜）——先在名冊登記這個代號，或改用研究 ticker")
    declared = receipt.get("declared") if isinstance(receipt.get("declared"), Mapping) else {}
    brief_id = str((declared or {}).get("brief_id") or "")
    if receipt.get("narrative") != "present" or not brief_id:
        raise ValueError(f"缺敘事版本：現行不是 v2 敘事（{receipt.get('narrative_label') or receipt.get('narrative')}）"
                         "——「沒買」要指得出當時讀的是哪一版；先寫敘事再記")
    stale = board_problem(receipt, brief_id)
    if stale:
        raise ValueError(stale)
    if choice == "不要":
        if until is not None:
            raise ValueError("--until 只給等到條件——「不要」沒有在等（這一版敘事不再問，換版再問）")
        until_text = None
    else:
        until = until or today + timedelta(days=WAIT_DEFAULT_DAYS)
        if until <= today:
            raise ValueError(f"等到的日子要在今天（{today.isoformat()}）之後：{until.isoformat()}")
        until_text = until.isoformat()
    day = today.isoformat()
    entry = {"kind": KIND, "decision_id": _decision_id(day=day, company_id=company_id, choice=choice,
                                                       brief_id=brief_id, why=text, until=until_text),
             "recorded_at": recorded_at, "date": day, "symbol": str(symbol).strip(), "company_id": company_id,
             "research_ticker": receipt.get("research_ticker"), "choice": choice, "why": text, "until": until_text,
             "brief_id": brief_id, "research_receipt": dict(receipt)}
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
    until = raw["until"]
    if raw["choice"] == "不要":
        if until is not None:
            raise ValueError(f"「不要」沒有到期（until 要是 null）：{until!r}")
        until_day = None
    else:
        if not isinstance(until, str) or not _DATE.match(until):
            raise ValueError(f"等到條件要有到期（until：YYYY-MM-DD；INV-2）：{until!r}")
        until_day = date.fromisoformat(until)
        if until_day <= date.fromisoformat(day):
            raise ValueError(f"until（{until}）要在 date（{day}）之後")
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
                       until=until_day, brief_id=str(raw["brief_id"]), was_open=receipt_was_open(receipt))


def load(path: Path | None = None) -> tuple[list[LookedEntry], list[str]]:
    """讀整本：(列, 問題)。檔案不存在＝還沒有任何一次決定（與 trade_log 同一個語意）；壞行不靜默丟（INV-3）；
    同一個 decision_id 出現兩次也是問題（重寫）——只收第一次，計數不會算兩次。整本讀不到（編碼、權限）照樣 raise，
    由讀者說讀不到。"""
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
            problems.append(f"looked_log 第 {number} 行：{entry.decision_id} 重複（同一次決定寫了兩次）——只算一次")
            continue
        seen.add(entry.decision_id)
        entries.append(entry)
    return entries, problems


def standing(entries: Iterable[LookedEntry]) -> dict[tuple[str, str], LookedEntry]:
    """每個（公司, 敘事版本）最後一次的選擇（照 recorded_at；同一刻照帳上順序）——選擇可以改，最後一次算數。"""
    out: dict[tuple[str, str], LookedEntry] = {}
    for entry in sorted(entries, key=lambda e: e.recorded_at):
        out[(entry.company_id, entry.brief_id)] = entry
    return out


def hides(entry: LookedEntry, *, today: date) -> bool:
    """這個選擇還讓那一列不必再問嗎：不要＝這一版不再問（換版再問）；等到條件＝到期那天（含）起重問。"""
    return entry.choice == "不要" or (entry.until is not None and today < entry.until)


def repeat_of(entry: Mapping[str, Any], entries: Iterable[LookedEntry], *, today: date,
              until_given: bool = False) -> LookedEntry | None:
    """重記只擋這一種：同一版敘事、同一個選擇、還在生效 → 回那一列（不寫）。11-04 R2：原本的鍵含日期與理由，隔天重跑或
    改一個標點就多一列、計兩次（L17：key 真的唯一嗎）。換了選擇、等到條件到期後重問、或明給了不同的 `--until`（改日子）
    → None（照寫：那是新的一次決定）。"""
    last = standing(entries).get((str(entry["company_id"]), str(entry["brief_id"])))
    if last is None or last.choice != entry["choice"] or not hides(last, today=today):
        return None
    if until_given and last.until is not None and last.until.isoformat() != entry.get("until"):
        return None
    return last


def append(entry: Mapping[str, Any], path: Path | None = None) -> Path:
    """append 一列（已由 `build_entry` 驗過）；只 append，永不改寫既有行。檔尾若是上次寫到一半留下的半行（沒有換行），
    先補一個換行再寫——半行照樣是壞行（`load` 報出來），新的一列不會黏上去一起壞掉（11-04 R2）。"""
    parse_entry(entry)
    target = path or LOOKED_LOG
    target.parent.mkdir(parents=True, exist_ok=True)
    lead = ""
    if target.is_file() and target.stat().st_size:
        with target.open("rb") as handle:
            handle.seek(-1, 2)
            if handle.read(1) != b"\n":
                lead = "\n"
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(lead + json.dumps(dict(entry), ensure_ascii=False, sort_keys=True) + "\n")
    return target


def today_local(now: datetime | None = None) -> date:
    """`now`（不給＝現在）落在排程時區的哪一天——`until` 與 `date` 用同一本日曆。呼叫端手上有 `now` 就要傳（心跳、短版
    都收 `now`；不傳會悄悄改用真實時鐘，2026-11-04 R2 覆核）。設定讀不到退回本機時區——與 record_trade 的退回一致。"""
    try:
        from engine_b import event_watch as ew

        return ew._today(now)
    except Exception:  # noqa: BLE001 — 排程時區讀不到：退回本機時區
        return now.astimezone().date() if now is not None else date.today()


# ---------------------------------------------------------------------------
# 讀者：「你的決定」計數（停止條件第一子句）
# ---------------------------------------------------------------------------

#: 另列那一格的字：當時不是可開的買進多半是加碼，不叫「進」。
_OTHER_LABELS: Mapping[str, str] = {"進": "買進", "不要": "不要", "等到條件": "等到條件"}


@dataclass(frozen=True, slots=True)
class MonthCounts:
    """某個月的決定，照「當時是不是可開」分三格（每格都是進／不要／等到條件）。"""
    decided: dict[str, int]                   # 當時是可開的——「你的決定」數的就是這一格
    not_open: dict[str, int]                  # 當時不是可開的（加碼買進、對缺 X 的不要……）
    unknown: dict[str, int]                   # 分不出（收據沒有候選板那一列：板讀不到、回填的舊成交）
    problems: list[str] = field(default_factory=list)


def _local_day(stamp: Any) -> date | None:
    from portfolio.research_receipt import _local_date

    return _local_date(stamp)


def month_counts(entries: Iterable[LookedEntry], trade_events: Iterable[Mapping[str, Any]], month: str) -> MonthCounts:
    """某個月的三種決定：進＝trade_log 裡帶研究收據的買進（alpha；beta 不帶收據）、其餘兩種＝這本。照收據裡候選板那一列
    分「當時是可開／不是／分不出」——停止條件問的是可開非空時有沒有決定。讀不懂日期的買進不算、但報出來（INV-3）。"""
    buckets: dict[bool | None, dict[str, int]] = {flag: {label: 0 for label in DECISION_LABELS}
                                                  for flag in (True, False, None)}
    problems: list[str] = []
    for event in trade_events:
        if event.get("side") != "buy" or not isinstance(event.get("research_receipt"), Mapping):
            continue
        day = _local_day(event.get("executed_at"))
        if day is None:
            problems.append(f"trade_log 有一筆買進的 executed_at 讀不懂（{event.get('executed_at')!r}）")
            continue
        if day.strftime("%Y-%m") == month:
            buckets[receipt_was_open(event["research_receipt"])]["進"] += 1
    for entry in entries:
        if entry.date.strftime("%Y-%m") == month:
            buckets[entry.was_open][entry.choice] += 1
    return MonthCounts(decided=buckets[True], not_open=buckets[False], unknown=buckets[None], problems=problems)


def status_line(counts: MonthCounts, *, month: str, problems: Sequence[str] = ()) -> str:
    """短版 ④ 的一行（每天印；0 也印——L14 常駐）。另列與分不出的只在有的時候印。"""
    line = (f"你的決定 {int(month.split('-')[1])} 月：" + "｜".join(f"{label} {counts.decided.get(label, 0)}"
                                                               for label in DECISION_LABELS)
            + "（只數當時是可開的；看了沒買照 record_trade.py looked 記；系統不由它產生動作）")
    other = sum(counts.not_open.values())
    if other:
        line += (f"｜另 {other} 筆當時不是可開（"
                 + "、".join(f"{_OTHER_LABELS[k]} {n}" for k, n in counts.not_open.items() if n) + "）")
    unknown = sum(counts.unknown.values())
    if unknown:
        line += f"｜{unknown} 筆分不出當時是不是可開（收據沒有候選板那一列）"
    every = [*problems, *counts.problems]
    if every:
        line += f"｜⚠ 帳有 {len(every)} 個問題（{every[0]}）——讀不懂的沒算、重複的只算一次"
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
            if not isinstance(event, Mapping):
                problems.append(f"trade_log 第 {number} 行不是 object")
                continue
            events.append(event)
    month = today.strftime("%Y-%m")
    return status_line(month_counts(entries, events, month), month=month, problems=problems)


__all__ = ["CHOICES", "DECISION_LABELS", "FIELDS", "KIND", "LOOKED_LOG", "LookedEntry", "MonthCounts",
           "WAIT_DEFAULT_DAYS", "append", "board_problem", "build_entry", "hides", "load", "month_counts", "parse_entry",
           "receipt_was_open", "repeat_of", "short_line", "standing", "status_line", "today_local"]
