"""投資人短評 ledger 的 I/O：`library/private/alpha/briefs/<TICKER>.jsonl`。

與 `alpha/providers/abstentions.py` 同一個位置慣例與同一套規則：private、append-only、
content-addressed id 拒絕重複、secret 拒絕、`supersedes_id` 必須指到既有紀錄。
純邏輯（解析、選取、驗證）在 `alpha/narrative/contracts.py`；這裡只讀寫檔。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from shared.redaction import sensitive_payload_path

from ..narrative.contracts import LINKABLE_SOURCE_PREFIXES, InvestorBrief, parse_brief_record
from ..errors import ContractViolation

_ROOT = Path(__file__).resolve().parents[2]
BRIEF_DIR = _ROOT / "library" / "private" / "alpha" / "briefs"


def ledger_path(ticker: str, *, directory: Path | None = None) -> Path:
    return (directory or BRIEF_DIR) / f"{ticker.strip().upper()}.jsonl"


def read_brief_records(ticker: str, *, directory: Path | None = None) -> tuple[list[InvestorBrief], list[str]]:
    """讀一檔的全部紀錄。壞掉的行**不靜默丟棄**——回在第二個 list 裡，消費端計數（INV-3）。"""
    path = ledger_path(ticker, directory=directory)
    if not path.is_file():
        return [], []
    records: list[InvestorBrief] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(parse_brief_record(json.loads(text)))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def append_brief_record(record: Mapping[str, Any], *, directory: Path | None = None) -> Path:
    """append 一筆（已由 `brief_record()` 驗證過的）紀錄；只 append，永不改寫既有行。"""
    parsed = parse_brief_record(record)
    sensitive = sensitive_payload_path(dict(record), "brief")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing brief rejected at {sensitive}")
    path = ledger_path(parsed.ticker, directory=directory)
    existing, _ = read_brief_records(parsed.ticker, directory=directory)
    if any(r.brief_id == parsed.brief_id for r in existing):
        raise ContractViolation(f"brief {parsed.brief_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id and not any(r.brief_id == parsed.supersedes_id for r in existing):
        raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在 ledger 中")
    if parsed.supersedes_id and not parsed.retracted and existing:
        # 2026-10-08（Phase 7 failure log #56，讀圖那一側的對稱面）：換版只取代最新那一筆（select_brief 的規則），
        # 取代更舊的一版會讓取代鏈分岔。
        head = max(existing, key=lambda r: (r.created_at, r.brief_id))
        if head.brief_id != parsed.supersedes_id:
            raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不是 {parsed.ticker} 最新的一筆"
                                    f"（最新是 {head.brief_id}）——換版只取代現行那一份，否則取代鏈會分岔")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


# ---------------------------------------------------------------------------
# v2 的寫入端（Phase 3 Step 3.4）：寫入當下才成立的檢查只放這裡，不放 parse 路徑（plan §13）
# ---------------------------------------------------------------------------

#: 「可開」要求騎的讀圖判讀是護城河或量（`undecided` 不行）。
OPEN_READING_KINDS: frozenset[str] = frozenset({"moat", "volume"})
#: 讀圖「現行」＝這兩態：`stale_low` 只有低等級變動、不進重讀佇列——不算現行的話，可開會被一個修不回來的狀態打掉。
CURRENT_READING_STATUSES: frozenset[str] = frozenset({"current", "stale_low"})
#: 已定價那一格引用的稽核行。相對組漲幅（③）2026-09-30 起只在稽核區、不上首屏，所以不在這裡——它有值不強迫答 yes／no。
_PRICED_IN_LINES = ("own_history_pctile", "cohort_median")
_IN_NUMBERS_LINES = ("in_numbers_series",)


class WriteContext:
    """寫入當下的世界（讀圖狀態、讀圖紀錄、三題、watch registry、thesis lifecycle）。正式入口由 `load()` 讀真實資料；
    測試直接注入。**這裡的每一樣都是 as-of 今天的**——所以這些檢查只放寫入端。"""

    def __init__(self, *, today: Any, reading_rows: Sequence[Mapping[str, Any]],
                 readings_by_id: Mapping[str, Any], three_questions: Mapping[str, Any] | None,
                 watches: dict[str, Any], lifecycle: Mapping[str, Any] | None, registry: Any = None,
                 three_questions_reload: Any = None) -> None:
        self.today = today
        self.reading_rows = list(reading_rows)
        self.readings_by_id = dict(readings_by_id)
        self.three_questions = three_questions
        self.watches = watches
        self.lifecycle = lifecycle
        self.registry = registry
        #: `history_not_comparable` → 重算三題（R2-a N3：敘事宣告「歷史不可比」時，驗 unmeasurable 要用宣告後的
        #: 稽核區，否則自家歷史那一行有值、宣告了反而被拒收）。測試注入時為 None＝不重算。
        self.three_questions_reload = three_questions_reload

    @classmethod
    def load(cls, ticker: str, *, today: Any = None) -> "WriteContext":
        """`today` 沒給＝排程時區的今天（`event_watch._today()`，與 daily 的到期判定同一個定義）。"""
        from engine_b import event_watch as ew
        from engine_b.disproof import load_lifecycle
        from query.structure import _load_edges

        from .structure_readings import known_nodes, read_reading_records, reading_status_rows
        from .three_questions import three_questions_for

        today = today or ew._today()

        watches = ew.load_watches()
        edges = _load_edges()
        rows, _errors = reading_status_rows(edges, today=today, watches=watches.get("watches") or ())
        readings = {}
        for node in known_nodes():
            for rec in read_reading_records(node)[0]:
                readings[rec.reading_id] = rec
        try:
            tq = three_questions_for(ticker, today=today, wipeout=None, wipeout_reason="（寫入端只看已定價與出現在數字裡）")
        except Exception:  # noqa: BLE001 — 讀不到三題時 answers 的 unmeasurable 檢查會 fail closed
            tq = None
        def reload(history_not_comparable: Mapping[str, Any]) -> Mapping[str, Any] | None:
            try:
                return three_questions_for(ticker, today=today, wipeout=None,
                                           wipeout_reason="（寫入端只看已定價與出現在數字裡）",
                                           history_not_comparable=history_not_comparable)
            except Exception:  # noqa: BLE001 — 讀不到就讓 unmeasurable 的檢查 fail closed
                return None

        return cls(today=today, reading_rows=rows, readings_by_id=readings, three_questions=tq, watches=watches,
                   lifecycle=load_lifecycle(), three_questions_reload=reload)


def _registry(ctx: WriteContext) -> Any:
    if ctx.registry is None:
        from identity.registry import get_registry

        ctx.registry = get_registry()
    return ctx.registry


def _supply_side(reading: Any) -> set[str]:
    return {str(edge[0]) for edge in ((getattr(reading, "angles", {}) or {}).get("supply_side") or ())
            if isinstance(edge, (list, tuple)) and edge and str(edge[0]).startswith("co:")}


def _demand_side(reading: Any) -> set[str]:
    return {str(edge[0]) for edge in ((getattr(reading, "angles", {}) or {}).get("demand_side") or ())
            if isinstance(edge, (list, tuple)) and edge and str(edge[0]).startswith("co:")}


def v2_write_problems(parsed: InvestorBrief, *, ctx: WriteContext, existing: Sequence[InvestorBrief]) -> list[str]:
    """v2 寫入當下的前提（plan §5 第 4–6 點）。回問題清單；空＝可以寫。"""
    from engine_b import event_watch as ew
    from engine_b.disproof import normalize
    from engine_b.narrative_watches import blocking_for_open, pending_rewrite

    problems: list[str] = []
    company, ticker = parsed.company_id, parsed.ticker
    watches = list(ctx.watches.get("watches") or ())
    brief_ids = [r.brief_id for r in existing] + [parsed.brief_id]
    status_by_ride = {(r.get("node"), r.get("unit")): r for r in ctx.reading_rows if r.get("reading_id")}

    # ① rides：現行（current／stale_low）、而且本公司在那份讀圖快照的**供給側**
    for ride in parsed.rides:
        row = status_by_ride.get((ride.node, ride.unit))
        if row is None or row.get("reading_id") != ride.reading_id:
            problems.append(f"rides：{ride.node}（{ride.unit}）的現行讀圖不是 {ride.reading_id}"
                            f"（現行是 {row.get('reading_id') if row else '沒有'}）")
            continue
        if row.get("status") not in CURRENT_READING_STATUSES:
            problems.append(f"rides：{ride.reading_id} 的狀態是 {row.get('status')}——只有 current／stale_low 算現行")
        reading = ctx.readings_by_id.get(ride.reading_id)
        if reading is None or company not in _supply_side(reading):
            side = ("需求側" if reading is not None and company in _demand_side(reading) else "兩側都不在")
            problems.append(f"rides：{company} 不在 {ride.reading_id}（{ride.node}）的供給側——它在{side}；"
                            "只能押自己在供給側的讀圖")

    # ② disproof：到期、實體、出處、已在盯的只連結
    live_by_condition = {}
    for w in watches:
        if w.get("kind") == ew.SEMANTIC_KIND and w.get("status") in ("active", "fired") \
                and str(w.get("source_ref") or "").startswith(LINKABLE_SOURCE_PREFIXES):
            live_by_condition[normalize(w.get("condition"))] = str(w.get("source_ref"))
    live_refs = {str(w.get("source_ref")) for w in watches if w.get("status") in ("active", "fired")}
    #: 同一版敘事內正規化後相同的條件（Phase 4 Step 4.7d）：判準同 `register-disproof` 的去重（`engine_b.disproof.normalize`）
    #: ——同一個條件登記兩次就會被叫醒兩次、複查兩筆一起續盯。只比本版自己的 disproof[]，跨公司不比。
    first_seen: dict[str, int] = {}
    for n, item in enumerate(parsed.disproof, 1):
        key = normalize(item.condition)
        if key in first_seen:
            problems.append(f"disproof[{n}]：與 disproof[{first_seen[key]}] 是同一個條件（正規化後相同）——同一版敘事不登記兩次")
        else:
            first_seen[key] = n
        if item.expires <= ctx.today:
            problems.append(f"disproof[{n}]：expires {item.expires} 必須晚於今天")
        written = ew.condition_dates(item.condition)
        if written and item.expires < max(written):
            problems.append(f"disproof[{n}]：expires {item.expires} 早於條件自己寫的日期 {max(written)}")
        unknown = [e for e in item.entities if str(e).startswith("co:") and not _registry(ctx).has_company(e)]
        if unknown:
            problems.append(f"disproof[{n}]：entities 有 registry 解析不到的 co:*（INV-1）：{unknown}")
        if item.source.startswith("sr_") and item.source not in ctx.readings_by_id:
            problems.append(f"disproof[{n}]：source {item.source} 不是任何讀圖 id")
        if item.link_source_ref:
            if item.link_source_ref not in live_refs:
                problems.append(f"disproof[{n}]：link_source_ref {item.link_source_ref} 沒有在盯的 watch——沒人盯就新登，不要連結")
        else:
            existing_ref = live_by_condition.get(normalize(item.condition))
            if existing_ref:
                problems.append(f"disproof[{n}]：這條已在盯（{existing_ref}）——只填 link_source_ref，不重登")

    # ②b confirm（加碼條件，Phase 7 Step 7.0d）：與反證對稱的寫入當下檢查；同一個條件不得既是反證又是加碼條件
    disproof_keys = {normalize(d.condition): n for n, d in enumerate(parsed.disproof, 1)}
    first_confirm: dict[str, int] = {}
    for n, item in enumerate(parsed.confirm, 1):
        key = normalize(item.condition)
        if key in first_confirm:
            problems.append(f"confirm[{n}]：與 confirm[{first_confirm[key]}] 是同一個條件（正規化後相同）")
        else:
            first_confirm[key] = n
        if key in disproof_keys:
            problems.append(f"confirm[{n}]：與 disproof[{disproof_keys[key]}] 是同一個條件——一件事發生不會既確認又推翻結構")
        if item.expires <= ctx.today:
            problems.append(f"confirm[{n}]：expires {item.expires} 必須晚於今天")
        written = ew.condition_dates(item.condition)
        if written and item.expires < max(written):
            problems.append(f"confirm[{n}]：expires {item.expires} 早於條件自己寫的日期 {max(written)}")
        unknown = [e for e in item.entities if str(e).startswith("co:") and not _registry(ctx).has_company(e)]
        if unknown:
            problems.append(f"confirm[{n}]：entities 有 registry 解析不到的 co:*（INV-1）：{unknown}")
        if item.source.startswith("sr_") and item.source not in ctx.readings_by_id:
            problems.append(f"confirm[{n}]：source {item.source} 不是任何讀圖 id")

    # ③ answers：unmeasurable 只在對應稽核行全是缺席時允許；yes／no 時組的兩行有值就要一併引用
    tq = ctx.three_questions
    rows = {r["key"]: r for q in ("priced_in", "in_numbers") for r in (tq or {}).get(q) or ()}
    slots = {s.key: s.text for s in parsed.slots}
    for answer_key, lines in (("priced_in", _PRICED_IN_LINES), ("in_numbers", _IN_NUMBERS_LINES)):
        value = getattr(parsed.answers, answer_key) if parsed.answers else None
        valued = [k for k in lines if (rows.get(k) or {}).get("absence_kind") is None and k in rows]
        if value == "unmeasurable":
            if tq is None:
                problems.append(f"answers.{answer_key}=unmeasurable：這次讀不到三題稽核區，無法確認它真的量不到（fail closed）")
            elif valued:
                problems.append(f"answers.{answer_key}=unmeasurable，但稽核區 {valued} 有值——量得到就要答 yes／no")
    if parsed.answers and parsed.answers.priced_in in ("yes", "no"):
        text = slots.get("priced_in", "")
        if (rows.get("cohort_median") or {}).get("absence_kind") is None and "cohort_median" in rows \
                and "{cohort_median}" not in text:
            problems.append("priced_in：主題等權組中位數有值，這一格必須一併引用 {cohort_median}")

    # ④ candidate_state：缺 X／等回落 → 本公司 wake_brief、active、kind 合法
    cs = parsed.candidate_state
    if cs is not None and cs.state in ("missing", "priced_wait"):
        w = next((w for w in watches if w.get("watch_id") == cs.watch_id), None)
        if w is None:
            problems.append(f"candidate_state：watch {cs.watch_id} 不存在")
        elif w.get("status") != "active" or ew.past_expiry(w, today=ctx.today):
            problems.append(f"candidate_state：watch {cs.watch_id} 不是 active（{w.get('status')}"
                            f"{'、已過 expires ' + str(w.get('expires')) if ew.past_expiry(w, today=ctx.today) else ''}）"
                            "——指向一筆活的等待")
        elif w.get("wake_brief") != company:
            problems.append(f"candidate_state：watch {cs.watch_id} 必須是 wake_brief={company} 的 watch"
                            "（thesis／讀圖的語意 watch、別家的、或前一版 brief: 的都不行）")
        elif w.get("kind") not in ew.WAKE_BRIEF_KINDS:
            problems.append(f"candidate_state：watch {cs.watch_id} 的 kind {w.get('kind')} 不在 {sorted(ew.WAKE_BRIEF_KINDS)}")

    # ⑤ 該重寫的 watch 逐條處置（不論是否帶 supersedes_id、不論前一筆是否撤回）
    pending = {str(w.get("watch_id")) for w in pending_rewrite(company, watches=watches, brief_ids=brief_ids)}
    acked = {a.watch_id for a in parsed.acknowledged_touched}
    if pending - acked:
        problems.append(f"acknowledged_touched 沒處置本公司名下該重寫的 watch：{sorted(pending - acked)}（不列就拒收）")
    if acked - pending:
        problems.append(f"acknowledged_touched 處置了不在「該重寫」狀態的 watch：{sorted(acked - pending)}")

    # ⑥ 可開的三個前提（lifecycle 讀不到由 `blocking_for_open` fail closed，R2-a C3）
    if cs is not None and cs.state == "open":
        for ride in parsed.rides:
            row = status_by_ride.get((ride.node, ride.unit)) or {}
            if row.get("kind") not in OPEN_READING_KINDS:
                problems.append(f"open：押的 {ride.reading_id} 判讀是 {row.get('kind')}——可開要護城河或量")
        blocking = blocking_for_open(company, ticker, watches=watches, lifecycle=ctx.lifecycle, brief_ids=brief_ids,
                                     current_brief=parsed, acknowledged=acked)
        if blocking:
            problems.append("open：還有待處置的反證 watch——" + "；".join(blocking))

    # ⑦ 重押讀圖時格層引用跟著換（Phase 6 待決 #16，L18；Phase 7 Step 7.0c）：rides[] 押的是某節點、某單位的現行讀圖，
    #   任何一格的 evidence_refs 就不得指向**同一節點同一單位**已被取代的讀圖——讀的人點進去會看到舊讀圖。
    #   只拒收、列出是哪幾格與該換成哪一個 id；**不自動改寫 session 的文字或引用**。既有紀錄不動（append-only）。
    current_by_ride = {(ride.node, ride.unit): ride.reading_id for ride in parsed.rides}
    for slot in parsed.slots:
        for ref in slot.evidence_refs:
            old = ctx.readings_by_id.get(ref) if str(ref).startswith("sr_") else None
            node, unit = getattr(old, "node", None), getattr(old, "unit", None)
            current = current_by_ride.get((node, unit)) if node else None
            if current and ref != current:
                problems.append(f"{slot.key}：evidence_refs 的 {ref} 是 {node}（{unit}）已被取代的讀圖——"
                                f"這版押的是 {current}，請換成它（不自動改寫）")
    return problems


def write_brief(record: Mapping[str, Any], *, ctx: WriteContext, directory: Path | None = None,
                watches_path: Path | None = None) -> dict[str, Any]:
    """v2 的正式寫入入口：寫入當下檢查 → append → 登記／收舊／處置 watch → 存 registry。v1 只收撤回。"""
    import copy

    from engine_b import event_watch as ew
    from engine_b.narrative_watches import register_brief_watches, settle_due

    from ..narrative.contracts import RECORD_VERSION_V2

    parsed = parse_brief_record(record)
    existing, _ = read_brief_records(parsed.ticker, directory=directory)
    if parsed.record_version != RECORD_VERSION_V2 and not parsed.retracted:
        raise ContractViolation("新寫的短評一律 v2（v1 照讀、只收撤回；Phase 3 Step 3.4）")
    brief_ids = [r.brief_id for r in existing] + [parsed.brief_id]
    # R2-a C4：先做 daily 會做的時間轉換（已過到期→expired、date 已到→fired），再判——否則換版會吞掉「到期未判」。
    settle_due(ctx.watches, parsed.company_id, brief_ids=brief_ids, today=ctx.today)
    if parsed.history_not_comparable is not None and ctx.three_questions_reload is not None:
        ctx.three_questions = ctx.three_questions_reload(parsed.history_not_comparable.as_dict())
    if parsed.record_version == RECORD_VERSION_V2 and not parsed.retracted:
        problems = v2_write_problems(parsed, ctx=ctx, existing=existing)
        if problems:
            raise ContractViolation("短評 v2 寫入拒收：\n- " + "\n- ".join(problems))
    # R2-a C1：hook 的任何失敗（例：語意 watch 的條件不到 20 字）都必須發生在 append **之前**——
    # 否則 ledger 已有一行、registry 沒存，同一份重跑又被「已在 ledger 中」擋掉。先在副本上預演一次。
    try:
        register_brief_watches(parsed, data=copy.deepcopy(ctx.watches), company_brief_ids=brief_ids)
    except ew.EventWatchError as exc:
        raise ContractViolation(f"短評寫入拒收（watch 登記預演失敗，ledger 未動）：{exc}") from None
    path = append_brief_record(record, directory=directory)
    summary = register_brief_watches(parsed, data=ctx.watches, company_brief_ids=brief_ids)
    ew.save_watches(ctx.watches, watches_path)
    return {"path": str(path), "brief_id": parsed.brief_id, **summary}


__all__ = ["BRIEF_DIR", "CURRENT_READING_STATUSES", "OPEN_READING_KINDS", "WriteContext", "append_brief_record",
           "ledger_path", "read_brief_records", "v2_write_problems", "write_brief"]
