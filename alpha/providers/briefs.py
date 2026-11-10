"""投資人短評 ledger 的 I/O：`library/private/alpha/briefs/<TICKER>.jsonl`。

與 `alpha/providers/abstentions.py` 同一個位置慣例與同一套規則：private、append-only、
content-addressed id 拒絕重複、secret 拒絕、`supersedes_id` 必須指到既有紀錄。
純邏輯（解析、選取、驗證）在 `alpha/narrative/contracts.py`；這裡只讀寫檔。
"""
from __future__ import annotations

import json
from datetime import date as date_type
from pathlib import Path
from typing import Any, Mapping, Sequence

from shared.redaction import sensitive_payload_path

from ..narrative.contracts import (CANDIDATE_STATES_RETIRED, LINKABLE_SOURCE_PREFIXES, RAW_EXCERPT_PREFIX,
                                   InvestorBrief, lamp_colour_claims, parse_brief_record, price_quote_claims,
                                   undated_position_claims, wrong_signal_items)
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


def current_brief_id(ticker: str) -> str | None:
    """現行那一份的 id（`select_brief`，排程時區的今天）；沒寫過或最新一筆是撤回回 None。"""
    from engine_b import event_watch as ew

    from ..narrative.contracts import select_brief

    current = select_brief(read_brief_records(ticker)[0], as_of=None, today=ew._today())
    return current.brief_id if current is not None else None


def raw_record(ticker: str, brief_id: str | None = None) -> dict[str, Any] | None:
    """ledger 裡的一行原樣（`alpha brief --show`，failure log #152）：沒給 id＝現行那一份；找不到回 None。
    遮價格由呼叫端做（`alpha.price_mask.mask_brief_record`）——讀全文不必再直接開 jsonl。"""
    wanted = brief_id or current_brief_id(ticker)
    path = ledger_path(ticker)
    if wanted is None or not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            raw = json.loads(line) if line.strip() else None
        except ValueError:
            continue                     # 壞行由 read_brief_records 計數（INV-3）；這裡只找指定的那一筆
        if isinstance(raw, dict) and raw.get("brief_id") == wanted:
            return raw
    return None


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

#: 讀圖判這一層押得下去的兩種判讀（護城河或量）——APP「圖」頁「押得下去的層」那一區（`webapp.materialize.reading_zones`）。
BETTABLE_READING_KINDS: frozenset[str] = frozenset({"moat", "volume"})
#: 「可開」的起始門要押的那一層讀過、而且判讀不是 `neither`（換得掉）——`undecided`（查了判不出）可以：讀到邊是加碼的門、
#: 不是起始的門（2026-11-03 盲點修法第 18＋16 條；決定紀錄 §10.1 條 2 作答 (a)）。之前只收護城河或量、與上面那一組同一份；
#: 11-03 起是兩句話（L12）：圖頁分區說的是**這一層**判了什麼，起始門說的是**這一檔**能不能開始——判不出的層照樣在「還判不出」那一區。
OPEN_READING_KINDS: frozenset[str] = BETTABLE_READING_KINDS | {"undecided"}
#: 讀圖「現行」＝這兩態：`stale_low` 只有低等級變動、不進重讀佇列——不算現行的話，可開會被一個修不回來的狀態打掉。
CURRENT_READING_STATUSES: frozenset[str] = frozenset({"current", "stale_low"})
#: 已定價那一格引用的稽核行。相對組漲幅（③）2026-09-30 起只在稽核區、不上首屏，所以不在這裡——它有值不強迫答 yes／no。
_PRICED_IN_LINES = ("own_history_pctile", "cohort_median")
#: 公開名（L16：候選板每天重驗對稱面時用**同一份**清單——不能用 `alpha.candidates.PRICED_IN_LINES`，那份含相對組漲幅，
#: 它有值並不強迫答 yes／no，用錯會讓「量不到」的列大批誤判前提失效）。
PRICED_IN_WRITE_LINES = _PRICED_IN_LINES
_IN_NUMBERS_LINES = ("in_numbers_series", "in_numbers_mix_series")
#: 「出現在數字裡了嗎」的兩個 placeholder → 各自填值的稽核行（2026-10-14 拆開：年增率與占比是兩種量，L12）。
IN_NUMBERS_PLACEHOLDER_LINES: Mapping[str, str] = {"in_numbers_latest": "in_numbers_series",
                                                   "in_numbers_mix_latest": "in_numbers_mix_series"}


class WriteContext:
    """寫入當下的世界（讀圖狀態、讀圖紀錄、三題、watch registry、thesis lifecycle）。正式入口由 `load()` 讀真實資料；
    測試直接注入。**這裡的每一樣都是 as-of 今天的**——所以這些檢查只放寫入端。"""

    def __init__(self, *, today: Any, reading_rows: Sequence[Mapping[str, Any]],
                 readings_by_id: Mapping[str, Any], three_questions: Mapping[str, Any] | None,
                 watches: dict[str, Any], lifecycle: Mapping[str, Any] | None, registry: Any = None,
                 three_questions_reload: Any = None, filings: Sequence[Mapping[str, Any]] | None = None,
                 calendar_checkpoints: Sequence[Mapping[str, Any]] | None = None) -> None:
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
        #: 何時格的裁決點（2026-11-10，failure log #150）：這家公司在 lead 池的 SEC 定期報告、名冊上這一檔的檢核點
        #: （`alpha.providers.checkpoints`）。None＝沒載入，那一半不核（只印的提示，不擋）。
        self.filings = filings
        self.calendar_checkpoints = calendar_checkpoints

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

        from identity.registry import get_registry

        from .checkpoints import calendar_checkpoints_by_ticker, sec_filings_by_company

        filings, filings_note = sec_filings_by_company()
        calendar, calendar_note = calendar_checkpoints_by_ticker()
        registry = get_registry()
        cid = registry.company_id_for_ticker(str(ticker))
        # 名冊以 research ticker 為鍵（與候選板同一個鍵；呼叫端可能給 alias）
        research = str((registry.research_ticker(cid) if cid else None) or ticker).upper()
        return cls(today=today, reading_rows=rows, readings_by_id=readings, three_questions=tq, watches=watches,
                   lifecycle=load_lifecycle(), three_questions_reload=reload,
                   filings=None if filings_note else list(filings.get(str(cid), ())),
                   calendar_checkpoints=None if calendar_note else list(calendar.get(research, ())))


def _registry(ctx: WriteContext) -> Any:
    if ctx.registry is None:
        from identity.registry import get_registry

        ctx.registry = get_registry()
    return ctx.registry


def _supply_side(reading: Any) -> set[str]:
    # 與敘事 stale ④ 的家數比對同一個（`alpha.candidates.supply_side_companies`，L16）
    from ..candidates import supply_side_companies

    return set(supply_side_companies(reading))


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
    # 出現在數字裡了嗎答 yes／no：引用的 placeholder 至少一個要有值（2026-10-14 兩個 placeholder 拆開後的補償控制——
    # 以前占比序列會填進 {in_numbers_latest}，現在不會；答 yes 卻印「（尚無）」是自相矛盾，L15）
    if tq is not None and parsed.answers and parsed.answers.in_numbers in ("yes", "no"):
        text = slots.get("position", "")
        cited = [p for p in IN_NUMBERS_PLACEHOLDER_LINES if "{" + p + "}" in text]
        valued_lines = {p: k for p, k in IN_NUMBERS_PLACEHOLDER_LINES.items()
                        if k in rows and (rows.get(k) or {}).get("absence_kind") is None}
        if cited and not any(p in valued_lines for p in cited):
            hint = "、".join("{" + p + "}" for p in valued_lines) or "沒有（那就答 unmeasurable）"
            problems.append(f"answers.in_numbers={parsed.answers.in_numbers}：position 引用的 "
                            f"{'、'.join('{' + p + '}' for p in cited)} 在稽核區沒有值，印出來是（尚無）——有值的是 {hint}")

    # ④⁰ 退役的宣告值（2026-11-03 盲點修法第 18＋16 條；AGENTS「候選狀態是封閉字彙：可開／缺 X／不要／已持有」）：
    #    舊紀錄照讀成可開，新寫的拒收——只改字面值的重述（restates）也一樣：它要沿用的判斷已經不在字彙裡
    cs = parsed.candidate_state
    if cs is not None and cs.state in CANDIDATE_STATES_RETIRED:
        problems.append(f"candidate_state：「已定價等回落」2026-11-03 已併回可開——已定價寫在 priced_in 那一格當脈絡"
                        f"（已定價時翻倍條件寫得更嚴），候選狀態照起始門宣告 {CANDIDATE_STATES_RETIRED[cs.state]}／missing／pass；"
                        "要不要等價格是使用者在 ③ 的選擇（看了沒買），不是候選狀態")
    # ④ candidate_state：缺 X → 本公司 wake_brief、active、kind 合法
    if cs is not None and cs.state == "missing":
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
    # ④b（等回落的重開條件，2026-11-01）隨等回落一起退役（2026-11-03）：新紀錄寫不出等回落，上面 ④⁰ 已擋

    # ⑤ 該重寫的 watch 逐條處置（不論是否帶 supersedes_id、不論前一筆是否撤回）
    pending = {str(w.get("watch_id")) for w in pending_rewrite(company, watches=watches, brief_ids=brief_ids)}
    acked = {a.watch_id for a in parsed.acknowledged_touched}
    if pending - acked:
        problems.append(f"acknowledged_touched 沒處置本公司名下該重寫的 watch：{sorted(pending - acked)}（不列就拒收）")
    if acked - pending:
        problems.append(f"acknowledged_touched 處置了不在「該重寫」狀態的 watch：{sorted(acked - pending)}")

    # ⑥ 可開的起始門（2026-11-03 盲點修法第 18＋16 條；AGENTS「候選狀態是封閉字彙」那一句）：押的那一層判讀不是 neither、
    #   反證已寫下且有到期（到期晚於今天由 ② 驗）、沒有待處置的反證 watch（lifecycle 讀不到由 `blocking_for_open` fail closed，
    #   R2-a C3）。「已定價寫成一句脈絡」是 v2 契約（priced_in 那一格與 answers 必寫）；「會死嗎不是紅」每天重算、寫入端不載燈，
    #   只在候選板驗（`alpha.providers.candidates.open_preconditions`）。讀到邊與深挖清單是加碼條件，不在這裡擋。
    if cs is not None and cs.state == "open":
        for ride in parsed.rides:
            row = status_by_ride.get((ride.node, ride.unit)) or {}
            if row.get("kind") not in OPEN_READING_KINDS:
                problems.append(f"open：押的 {ride.reading_id} 判讀是 {row.get('kind')}——起始門要押的那一層讀過、"
                                "而且判讀不是 neither（換得掉）")
        if not parsed.disproof:
            problems.append("open：起始門要反證已寫下且有到期（disproof[] 至少一條）——知道什麼時候認錯才開始")
        blocking = blocking_for_open(company, ticker, watches=watches, lifecycle=ctx.lifecycle, brief_ids=brief_ids,
                                     current_brief=parsed, acknowledged=acked)
        if blocking:
            problems.append("open：還有待處置的反證 watch——" + "；".join(blocking))
        # 候選板起始門 ③ 的對稱面（failure log #131）：已定價答 yes／no 時稽核行至少一行有值，清單用候選板**同一份**
        # （L16）——全部缺席還答 yes，寫得進去、當天物化就是「前提失效」（300757.SZ 11-05：A 股自家百分位沒接、不在任何組）。
        # 出現在數字裡那一題不必另擋：v2 的 position 必引用 placeholder，③ 已要求引用的那一行有值。
        from ..candidates import PRICED_IN_LINES
        value = parsed.answers.priced_in if parsed.answers else None
        if value in ("yes", "no") and tq is not None and not any(
                r.get("key") in PRICED_IN_LINES and r.get("absence_kind") is None for r in tq.get("priced_in") or ()):
            problems.append(f"open：answers.priced_in={value}，但已定價的稽核行 {list(PRICED_IN_LINES)} 全部缺席——"
                            "量不到就答 unmeasurable（候選板每天用同一條重驗）")

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

    # ⑧ 已定價的位置詞要帶日期（ROADMAP 已定價變動計數器；failure log #94）：「高檔」「偏貴」這種依賴百分位大小的結論，
    #   數字每天重填、這句不會——換騎照抄舊句就會把舊判斷包裝成新日期。只擋寫入；舊紀錄照讀（不放 parse 路徑）。
    for label, text, need_price in (("priced_in", slots.get("priced_in", ""), False),
                                    ("candidate_state.reason", (cs.reason or "") if cs is not None else "", True)):
        for words, sentence in undated_position_claims(text, require_price_word=need_price):
            problems.append(f"{label}：「{'、'.join(words)}」是依賴百分位大小的位置結論，數字每天重填、這句不會——"
                            f"拿掉，或寫明日期（「寫這句的 YYYY-MM-DD 當天…」）；判斷當時的百分位寫入端已自動記下："
                            f"{sentence[:40]}")

    # ⑨ 一手節錄要指得回（批次二 E12；failure log #50；L18）：`library/raw/<檔名>` 的檔要真的在、而且不得跳出 library/raw
    #   ——證據清單照這個路徑列，指不回的引用列出來只會是一個死連結。
    problems.extend(raw_excerpt_problems(parsed, root=_ROOT))

    # ⑩ 寫死的燈色（2026-10-31，failure log #120）：會死嗎的燈每天重算、首屏另有一行——敘事寫「現金跑道紅燈」，燈一變就錯
    #   （4971.TWO、AAON 10-29 改燈的規則後由紅變黃，首屏照印）。只擋寫入；舊紀錄照讀（不放 parse 路徑）。
    for label, text in [*((s.key, s.text) for s in parsed.slots),
                        ("candidate_state.reason", (cs.reason or "") if cs is not None else "")]:
        for sentence in lamp_colour_claims(text):
            problems.append(f"{label}：寫死了燈色——會死嗎的燈每天重算、首屏另有一行；改寫成燈背後的事實"
                            f"（本業在燒錢、欠的比手上的現金多…）：{sentence[:40]}")

    # ⑪ 只改字面值的換版宣告重述哪一版（2026-10-31 使用者「修吧」；failure log #121）
    if parsed.restates is not None:
        problems.extend(restates_problems(parsed, existing))

    # ⑫ 換騎不能跨過判讀或家數改變（ROADMAP「敘事 stale 計數器」②④；failure log #93：AEVA 10-19 換騎跨過
    #   undecided→neither、COHR／LITE／SIVE.ST 換騎跨過供給側 7→9 家，正文都一字不改）。正文（七格＋候選狀態與理由，`body_key`）
    #   沒改的這一版，騎的讀圖跟正文寫的時候騎的那份比：判讀或供給側家數不同就拒收——改寫受影響的句子再寫。
    #   比的是讀圖紀錄的結構，不看 note 寫什麼、不解析正文的「N 家」。正文改過（或第一版）就不比。
    problems.extend(body_behind_problems(parsed, existing=existing, readings_by_id=ctx.readings_by_id))

    # ⑬ 深挖清單的引用要指得回（2026-11-03 盲點修法第 18＋16 條；L18）：寫成引用的項目算「查過」，所以引用的一手節錄要在
    #   library/raw、讀圖 id 要真的存在——指不回的引用等於沒查卻算查過。其他寫法（網址、不適用、加碼條件、缺）不在這裡驗
    #   （形狀由契約擋）。
    problems.extend(depth_check_ref_problems(parsed, readings_by_id=ctx.readings_by_id, root=_ROOT))

    # ⑭ 錯的訊號標的反證編號要指得到（2026-11-10，failure log #140）：「（第 N 條）」的 N 是 disproof[] 的順序——指到不存在的
    #   那一條，等於宣稱有 watch 在盯、其實沒有。沒標編號的條目不擋、只印（`v2_write_notices`；從文字切條會誤切，L16）。
    problems.extend(wrong_signal_ref_problems(parsed))
    return problems


def wrong_signal_ref_problems(parsed: InvestorBrief) -> list[str]:
    """⑭：「錯的訊號」段每一條標的 disproof[] 編號都要在 1..len(disproof[]) 之內。回問題清單。"""
    slot = parsed.slot("what_must_be_true")
    count = len(parsed.disproof)
    return [f"what_must_be_true：錯的訊號「{item[:40]}」標的第 {n} 條不在 disproof[]（共 {count} 條）——"
            "編號照 disproof[] 的順序、從 1 起算"
            for item, refs, _ in wrong_signal_items(slot.text if slot is not None else "")
            for n in refs if not 1 <= n <= count]


def _cited_file(text: str, start: int, base: Path, root: Path) -> bool:
    """`text[start:]` 開頭是不是一個在 `base` 底下的檔：候選終點是每個副檔名之後與整串結尾，取第一個存在的
    （引用後面可以接註解；檔名本身可能含全形逗號，所以不以標點切）。"""
    import re

    ends = [start + m.end() for m in re.finditer(r"\.[A-Za-z0-9]{1,6}(?![A-Za-z0-9])", text[start:])] + [len(text)]
    for end in ends:
        path = (root / text[start:end].strip()).resolve()
        if base in path.parents and path.is_file():
            return True
    return False


def depth_check_ref_problems(parsed: InvestorBrief, *, readings_by_id: Mapping[str, Any], root: Path) -> list[str]:
    """⑬：`depth_check` 裡寫到的每一個 `library/raw/…`／`library/private/…` 都要是那個目錄底下的檔（私人節錄同一條，
    2026-11-04 R2 對稱面）、每一個 `sr_…` 都要是讀圖 id。回問題清單。

    引用後面可以接註解（`library/raw/x.txt（第三季新聞稿）`——skill 寫的是「開頭限」）；2026-11-04 drain 起改成值裡**每一個**
    路徑與讀圖 id 都驗（原本整串當一個路徑：接了註解就拒收，第二個以後的引用反而不驗）。"""
    import re

    problems: list[str] = []
    for key, value in parsed.depth_check:
        text = str(value).strip()
        for prefix, label in ((RAW_EXCERPT_PREFIX, "library/raw"), ("library/private/", "library/private")):
            base = (root / prefix).resolve()
            for match in re.finditer(re.escape(prefix), text):
                if not _cited_file(text, match.start(), base, root):
                    problems.append(f"depth_check.{key}：{text[match.start():match.start() + 80]} 在 {label} 找不到"
                                    f"（或跳出了 {label}）——節錄要先存成檔再引用")
        head = re.split(r"[\s（(＋+，,；;、]", text, maxsplit=1)[0]
        ids = set(re.findall(r"(?<![0-9A-Za-z_])sr_[0-9a-f]{16}(?![0-9a-f])", text)) | ({head} if head.startswith("sr_") else set())
        for reading_id in sorted(ids):
            if reading_id not in readings_by_id:
                problems.append(f"depth_check.{key}：{reading_id} 不是任何讀圖 id")
    return problems


def body_behind_problems(parsed: InvestorBrief, *, existing: Sequence[InvestorBrief],
                         readings_by_id: Mapping[str, Any]) -> list[str]:
    """⑫：這一版正文沒改、騎的讀圖判讀或供給側家數與正文版騎的那份不同 → 問題清單（`alpha.candidates` 同一個比對）。"""
    from ..candidates import body_behind_readings, body_behind_reasons, body_version

    if parsed.retracted:
        return []
    body = body_version([*existing, parsed], parsed)
    if body.brief_id == parsed.brief_id:
        return []
    entries, _unchecked = body_behind_readings(
        body, parsed, readings_by_id=readings_by_id,
        current_cells={(r.node, r.unit): r.reading_id for r in parsed.rides})
    return [f"rides：{reason}（這一版正文與 {body.brief_id}（{body.created_on}）一字不差；換騎跨過判讀或家數改變不收，"
            "改寫受影響的句子再寫）" for entry in entries for reason in body_behind_reasons(entry)]


def restates_problems(parsed: InvestorBrief, existing: Sequence[InvestorBrief]) -> list[str]:
    """⑪：`restates` 指的那一版必須是這一版 supersedes 鏈上的祖先，之後沒有撤回；它與它之後到這一版之間的每一版，
    候選狀態（state／watch／missing_kind／重開條件）、answers、歷史不可比宣告都與這一版相同——結構化的判斷一個都沒變才算
    只改字面值（文字是不是只改字面值，由寫的人負責；`note` 寫明改了什麼）。回問題清單。
    重開條件（2026-11-01）進判斷鍵：改它就是改判，不能包裝成只改字面值（L12）。"""
    def judged(b: InvestorBrief) -> tuple[Any, ...]:
        cs = b.candidate_state
        return ((cs.state, cs.watch_id, cs.missing_kind, cs.reopen.as_dict() if cs.reopen is not None else None)
                if cs is not None else None,
                b.answers.as_dict() if b.answers is not None else None,
                b.history_not_comparable.as_dict() if b.history_not_comparable is not None else None)

    by_id = {r.brief_id: r for r in existing}
    chain: list[InvestorBrief] = []
    cur_id, seen = parsed.supersedes_id, set()
    while cur_id and cur_id in by_id and cur_id not in seen:
        seen.add(cur_id)
        chain.append(by_id[cur_id])
        if cur_id == parsed.restates:
            break
        cur_id = by_id[cur_id].supersedes_id
    if not chain or chain[-1].brief_id != parsed.restates:
        return [f"restates：{parsed.restates} 不在這一版的 supersedes 鏈上——只能重述這條鏈上更早的一版"]
    target = chain[-1]
    problems: list[str] = []
    if any(r.retracted and r.created_at > target.created_at for r in existing):
        problems.append(f"restates：{target.brief_id} 之後有撤回紀錄——撤回打斷連續，不能跨過它重述")
    want = judged(parsed)
    for b in chain:
        if judged(b) != want:
            problems.append(f"restates：{b.brief_id}（{b.created_on}）的候選狀態／answers／歷史不可比宣告與這一版不同——"
                            "結構化的判斷變了就不是只改字面值，不寫 restates")
    return problems


def v2_write_notices(parsed: InvestorBrief) -> list[str]:
    """只印、不擋的提示（2026-10-31，failure log #120）：已定價那一格與候選理由寫了收盤價——9-30 使用者定案首屏不放價格報酬
    （相對組漲幅只在稽核區）。先看它印出什麼（L16：比對文字的檢查會誤報），要擋另議。"""
    priced = parsed.slot("priced_in")
    reason = parsed.candidate_state.reason if parsed.candidate_state is not None else None
    notices: list[str] = []
    for label, text in (("priced_in", priced.text if priced is not None else ""), ("candidate_state.reason", reason or "")):
        for sentence in price_quote_claims(text):
            notices.append(f"{label}：寫了收盤價——首屏不放價格報酬（9-30 使用者定案），改用文字描述方向：{sentence[:40]}")
    # 錯的訊號沒標對應的反證（2026-11-10，failure log #140）：只印——沒有反證就沒有 watch，到期那天不會有東西叫你回來看
    must = parsed.slot("what_must_be_true")
    bare = [item for item, refs, reading in wrong_signal_items(must.text if must is not None else "")
            if not refs and not reading]
    if bare:
        notices.append("what_must_be_true：這幾條錯的訊號沒標對應的反證——對到哪一條就寫「（第 N 條）」（N＝disproof[] 的順序；"
                       "讀圖的反證寫「讀圖第 N 條」或連進 disproof[]），對不到的補一條（有日期寫逾期型）或寫為什麼不補：「"
                       + "」「".join(item[:40] for item in bare) + "」")
    return notices


def checkpoint_notices(parsed: InvestorBrief, *, existing: Sequence[InvestorBrief], ctx: WriteContext) -> list[str]:
    """何時格的兩個提示（只印、不擋；2026-11-10，failure log #150）：①這一版照抄的何時格，寫的裁決點已過（PSIX、EFXT 那種
    重述版）；②把 `{next_checkpoint_date}` 寫成某件事的日子——佔位字每天換成名冊上的下一個日子，那件事一過句子就錯。
    新寫的何時格「寫下那天」是今天，①不會亮；候選板每天核同一件事（`derive_row`），這裡是寫入當下的對稱面（L17）。"""
    from engine_b import event_watch as ew

    from ..narrative.checkpoints import (PLACEHOLDER, checkpoint_passed, checkpoint_reason, placeholder_as_event,
                                         when_text_since)

    slot = parsed.slot("when")
    text = slot.text if slot is not None else ""
    notices: list[str] = []
    try:
        today = ctx.today if isinstance(ctx.today, date_type) else date_type.fromisoformat(str(ctx.today)[:10])
        written_on = when_text_since([*existing, parsed], parsed).astimezone(ew._local_timezone()).date()
        passed = checkpoint_passed(text, written_on=written_on, today=today, filings=ctx.filings or (),
                                   calendar_checkpoints=ctx.calendar_checkpoints or ())
    except Exception as exc:  # noqa: BLE001 — append 之後才算的提示：算不成照實說，不讓已寫入的那一版看起來失敗
        notices.append(f"when：何時格的裁決點這次沒核成（{type(exc).__name__}: {str(exc)[:80]}）——只是提示，寫入照常")
        passed = None
    if passed:
        notices.append(f"when：這一版照抄了舊的何時格——{checkpoint_reason(passed)}")
    if placeholder_as_event(text):
        notices.append(f"when：把 {PLACEHOLDER} 寫成某件事的日子——佔位字每天換成名冊上的下一個日子，那件事一過句子就指著"
                       "別的日子；寫那件事自己的日子，佔位字單獨寫（「…。{next_checkpoint_date}。」）")
    return notices


def raw_excerpt_problems(parsed: InvestorBrief, *, root: Path) -> list[str]:
    """每格 `library/raw/<檔名>` 引用：檔在、在 `library/raw` 底下。回問題清單（⑨，`v2_write_problems` 用）。"""
    raw_dir = (root / "library" / "raw").resolve()
    problems: list[str] = []
    for slot in parsed.slots:
        for ref in slot.evidence_refs:
            if not str(ref).startswith(RAW_EXCERPT_PREFIX):
                continue
            path = (root / str(ref)).resolve()
            if raw_dir not in path.parents or not path.is_file():
                problems.append(f"{slot.key}：evidence_refs 的 {ref} 在 library/raw 找不到（或跳出了 library/raw）——"
                                "一手節錄要先存成檔再引用（證據清單照這個路徑列）")
    return problems


def priced_snapshot(three_questions: Mapping[str, Any] | None, *, today: Any) -> dict[str, Any]:
    """寫入當下的已定價①（`priced_at_write`）：照抄三題稽核區自家歷史那一行，讀不到就照實記缺席（不得空著，INV-3）。"""
    from alpha.absence import check_absence_kind

    from ..narrative.contracts import PricedSnapshot

    day = today if isinstance(today, date_type) else date_type.fromisoformat(str(today)[:10])
    row = next((r for r in (three_questions or {}).get("priced_in") or () if r.get("key") == "own_history_pctile"), None)
    if three_questions is None:
        snap = PricedSnapshot(recorded_on=day, absence_kind="upstream_unavailable", reason="寫入當下讀不到三題稽核區")
    elif row is None:
        snap = PricedSnapshot(recorded_on=day, absence_kind="upstream_unavailable", reason="三題稽核區沒有自家歷史那一行")
    elif row.get("absence_kind") is not None:
        check_absence_kind(str(row["absence_kind"]))
        snap = PricedSnapshot(recorded_on=day, absence_kind=str(row["absence_kind"]),
                              reason=str(row.get("reason") or "（三題沒有寫理由）"), basis=row.get("basis"))
    else:
        snap = PricedSnapshot(recorded_on=day, value=float(row["value"]), basis=row.get("basis"),
                              as_of=row.get("as_of"), multiple=(row.get("detail") or {}).get("multiple_today"))
    return snap.as_dict()                                       # 正規形狀（有值與缺席同一組鍵），R2 2026-10-21


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
    # 判斷當時的已定價①由寫入端記下（不進 id；換騎也記——那一刻的值就是那一版寫入時看到的）。手寫的一律拒收（含撤回）：
    # 寫的人手打的數字不是「T 時刻系統知道什麼」（INV-6）。
    if record.get("priced_at_write") is not None:
        raise ContractViolation("priced_at_write 由寫入端從當下的三題記下，不收手寫")
    if parsed.record_version == RECORD_VERSION_V2 and not parsed.retracted:
        record = {**record, "priced_at_write": priced_snapshot(ctx.three_questions, today=ctx.today)}
        parsed = parse_brief_record(record)
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
    notices = ([*v2_write_notices(parsed), *checkpoint_notices(parsed, existing=existing, ctx=ctx)]
               if parsed.record_version == RECORD_VERSION_V2 and not parsed.retracted else [])
    return {"path": str(path), "brief_id": parsed.brief_id, **summary, "notices": notices}


__all__ = ["BETTABLE_READING_KINDS", "BRIEF_DIR", "CURRENT_READING_STATUSES", "OPEN_READING_KINDS", "PRICED_IN_WRITE_LINES", "WriteContext", "append_brief_record", "priced_snapshot",
           "body_behind_problems", "checkpoint_notices", "current_brief_id", "depth_check_ref_problems",
           "ledger_path", "raw_record", "read_brief_records", "restates_problems", "v2_write_notices", "v2_write_problems",
           "write_brief", "wrong_signal_ref_problems"]
