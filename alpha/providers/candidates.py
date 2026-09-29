"""候選狀態推導（Phase 3 Step 3.6）——**候選板、心跳、個股頁、成交收據共用這一個函式**。

顯示端、每天重算、可重建的 derived cache（L10）：它不寫任何 authority，只把幾份 authority 對起來——
敘事 ledger（宣告）、Sheet（已持有）、讀圖對圖（現行與判讀）、watch registry（在等什麼、有沒有待判）、
三題稽核區（answers 對應的行還在不在）、邊緣判定（`config/alpha_screen.json`）。

每一列回傳 `{declared, derived, preconditions[], edge, held_source, rewrite[], …}`——**不只回最後一個值**：
「宣告可開、但前提失效」與「宣告缺 X」是兩件不同的事，壓成一個 group 字串下游就分不出來（L12）。

字彙與純函式（三個字、滯留、已持有索引、整板組裝、rollup）住零 I/O 的 `alpha/candidates.py`；這裡只放要讀
watch registry／讀圖／Engine C／Sheet 的那一半。舊名從這裡再匯出，呼叫端不必改。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from ..candidates import (
    ANSWER_WORDS, CANDIDATES_THIS_IS_NOT, GROUP_LABELS, GROUPS, IN_NUMBERS_LINES, PRICED_IN_LINES,
    REWRITE_STATE_WORDS, SIDE_GROUPS, SIDE_LABELS, UNANSWERED, assemble_board, cap_label, held_index, rollup,
    stall_since, three_words,
)
from ..narrative.contracts import RECORD_VERSION_V2, InvestorBrief, select_brief
from .briefs import CURRENT_READING_STATUSES, OPEN_READING_KINDS


def _valued(three_questions: Mapping[str, Any] | None, question: str, keys: Sequence[str]) -> bool:
    """這一題有沒有任何一行有值。**逐行看、不以 key 建 dict**——一檔屬於多個主題組時同一個 key 會有多行
    （一組有值、另一組缺席），dict 會讓後一行覆蓋前一行，造成假的「前提失效」（L17：key 真的唯一嗎）。"""
    return any(r.get("key") in keys and r.get("absence_kind") is None
               for r in (three_questions or {}).get(question) or ())


def open_preconditions(brief: InvestorBrief, *, reading_rows: Mapping[tuple[str, str], Mapping[str, Any]],
                       three_questions: Mapping[str, Any] | None, blocking: Sequence[str],
                       breaks: Sequence[Mapping[str, Any]]) -> list[str]:
    """「可開」每天重驗的四個前提；回傳失效理由（空＝全部成立）。"""
    failed: list[str] = []
    for ride in brief.rides:                                                   # ① 騎的讀圖仍現行、判讀仍是護城河或量
        row = reading_rows.get((ride.node, ride.unit))
        if row is None or row.get("reading_id") != ride.reading_id:
            failed.append(f"騎的讀圖 {ride.reading_id} 已不是現行（現行 {row.get('reading_id') if row else '沒有'}）")
        elif row.get("status") not in CURRENT_READING_STATUSES:
            failed.append(f"騎的讀圖 {ride.reading_id} 狀態 {row.get('status')}（只有 current／stale_low 算現行）")
        elif row.get("kind") not in OPEN_READING_KINDS:
            failed.append(f"騎的讀圖 {ride.reading_id} 判讀是 {row.get('kind')}（可開要護城河或量）")
    answers = brief.answers                                                    # ② answers 的稽核行沒有全變缺席
    if answers is not None:
        if three_questions is None:
            failed.append("這次讀不到三題稽核區，answers 驗不了（fail closed）")
        else:
            if answers.priced_in in ("yes", "no") and not _valued(three_questions, "priced_in", PRICED_IN_LINES):
                failed.append("已定價的稽核行已全部缺席（宣告時有值）")
            if answers.in_numbers in ("yes", "no") and not _valued(three_questions, "in_numbers", IN_NUMBERS_LINES):
                failed.append("出現在數字裡的稽核行已缺席（宣告時有值）")
    failed.extend(f"待處置的反證 watch：{b}" for b in blocking)                # ③ 歸屬本檔的 watch 沒有待判
    failed.extend(f"連結 {b['link_source_ref']}：{b.get('label') or '已換版'}" for b in breaks)   # ④ 連結來源仍在盯
    return failed


def derive_row(ticker: str, company_id: str | None, *, records: Sequence[InvestorBrief], today: date,
               reading_rows: Mapping[tuple[str, str], Mapping[str, Any]], watches: Sequence[Mapping[str, Any]],
               lifecycle: Mapping[str, Any] | None, edge: Mapping[str, Any] | None,
               three_questions: Mapping[str, Any] | None, held: Mapping[str, Any],
               three_questions_note: str | None = None) -> dict[str, Any] | None:
    """一檔的候選狀態。沒有敘事、也沒有持有 → None（不上板，計數另印「無敘事」）。

    `rewrite[]`（**每一列都算，不論宣告哪一態、落哪一組**）：連結斷了（附為什麼斷）、敘事來源 watch 醒來／觸及／
    到期未判（plan §5 第 6 點：候選板印「敘事該重寫：<watch id> <狀態>」）、缺 X／等回落在等的 watch 已失效。"""
    from engine_b import event_watch as ew
    from engine_b.narrative_watches import blocking_for_open, link_breaks, pending_rewrite
    from engine_b.queue_segments import narrative_rewrite_state

    brief = select_brief(records, as_of=None, today=today)
    held_info = (held.get("by_company") or {}).get(str(company_id)) if held.get("status") == "ok" else None
    if brief is None and held_info is None:
        return None
    v2 = brief is not None and brief.record_version == RECORD_VERSION_V2
    cs = brief.candidate_state if v2 else None
    row: dict[str, Any] = {
        "ticker": ticker, "company_id": company_id,
        "brief_id": brief.brief_id if brief else None,
        "record_version": brief.record_version if brief else None,
        "declared": cs.state if cs else None,
        "declared_label": GROUP_LABELS.get(cs.state) if cs else None,
        "derived": None, "group": None, "side": None,
        "reason": cs.reason if cs else None,
        "preconditions": [], "rewrite": [], "rewrite_watch_ids": [],
        "edge": {**{k: (edge or {}).get(k) for k in ("state", "label", "reasons", "market_cap_usd", "analyst_count")},
                 "market_cap_label": cap_label((edge or {}).get("market_cap_usd"))},
        "held_source": dict(held_info) if held_info else None,
        "holdings_verified": held.get("status") == "ok",
        "rides": [], "watch": None, "since": None, "stall_days": None,
        "three_words": three_words(three_questions, brief, not_read=f"未讀到（{three_questions_note}）"
                                   if three_questions_note else "未讀到"),
        "note": None,
    }
    if brief is not None:
        for ride in (brief.rides if v2 else ()):
            r = reading_rows.get((ride.node, ride.unit)) or {}
            row["rides"].append({"node": ride.node, "unit": ride.unit, "reading_id": ride.reading_id,
                                 "kind": r.get("kind") if r.get("reading_id") == ride.reading_id else None,
                                 "status": r.get("status") if r.get("reading_id") == ride.reading_id else "superseded"})
    if held_info is not None:                                                   # Sheet 持有 → 已持有，宣告照留
        row.update(derived="held", group="held")
        if brief is None:
            row["note"] = "已持有、缺敘事"
        elif not v2:
            row["note"] = "已持有、敘事是舊版（缺候選狀態）"
    if brief is None:
        return row
    if not v2:
        if row["group"] is None:
            row.update(side="legacy")
        return row
    brief_ids = [r.brief_id for r in records]
    breaks = link_breaks([brief], watches=watches)
    row["rewrite"].extend(f"連結 {b['link_source_ref']}：{b.get('label')}" for b in breaks)
    pending = pending_rewrite(str(company_id), watches=watches, brief_ids=brief_ids)
    for w in pending:
        state = narrative_rewrite_state(w)
        row["rewrite"].append(f"敘事該重寫：{w.get('watch_id')} {REWRITE_STATE_WORDS.get(str(state), state)}")
        row["rewrite_watch_ids"].append(str(w.get("watch_id")))
    if cs.watch_id:
        w = next((w for w in watches if w.get("watch_id") == cs.watch_id), None)
        row["watch"] = {"watch_id": cs.watch_id, "status": (w or {}).get("status", "不存在"),
                        "until": (w or {}).get("until"), "expires": (w or {}).get("expires")}
        if cs.watch_id not in row["rewrite_watch_ids"]:                       # 醒來／到期已由上面那條列過
            if w is None:
                row["rewrite"].append(f"{GROUP_LABELS[cs.state]}在等的 watch {cs.watch_id} 不存在，該重寫")
            elif w.get("status") == "active" and ew.past_expiry(w, today=today):
                row["rewrite"].append(f"{GROUP_LABELS[cs.state]}在等的 watch 已過到期日 {w.get('expires')}"
                                      "（daily 尚未標記），該重寫")
            elif w.get("status") != "active":
                row["rewrite"].append(f"{GROUP_LABELS[cs.state]}在等的 watch 已 {w.get('status')}，該重寫")
    since = stall_since(records, brief)
    row["since"] = since.isoformat()
    row["stall_days"] = (today - since.date()).days
    if row["group"] == "held":
        return row
    state = (edge or {}).get("state")
    if state == "not_edge":
        row.update(side="not_multiple", derived="not_multiple")
        return row
    if state != "edge":
        row.update(side="edge_unmeasurable", derived="edge_unmeasurable")
        return row
    if cs.state == "open":
        blocking = blocking_for_open(str(company_id), ticker, watches=watches, lifecycle=lifecycle,
                                     brief_ids=brief_ids, current_brief=brief)
        row["preconditions"] = open_preconditions(brief, reading_rows=reading_rows, three_questions=three_questions,
                                                  blocking=blocking, breaks=breaks)
        if row["preconditions"]:
            row.update(side="precondition_failed", derived="precondition_failed")
            return row
    row.update(group=cs.state, derived=cs.state)
    return row


def board_rewrite(rows: Sequence[Mapping[str, Any] | None],
                  breaks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """整板「敘事該重寫」清單：連結斷了（全部現行 v2 敘事，`link_breaks`）＋各列的敘事來源 watch 待重寫。"""
    out = [{"kind": "link", **dict(b)} for b in breaks]
    for row in rows:
        for wid in (row or {}).get("rewrite_watch_ids") or ():
            out.append({"kind": "watch", "ticker": row["ticker"], "company_id": row.get("company_id"),
                        "brief_id": row.get("brief_id"), "watch_id": wid})
    return out


def _wipeout_and_three_questions(ticker: str, *, today: date, history_not_comparable: Mapping[str, Any] | None
                                 ) -> tuple[Mapping[str, Any] | None, str | None]:
    """四盞燈（Engine C 取數＋`alpha.wipeout` 判色）＋三題。讀不到回 `(None, 理由)`——理由要帶出去（INV-3）。"""
    from alpha.wipeout import wipeout_flags
    from engine_c.checklist import get_wipeout_inputs

    from .three_questions import three_questions_for

    try:
        raw = get_wipeout_inputs(ticker)
        flags = (wipeout_flags(runway=raw.get("runway"), shares_series=raw.get("shares_series"),
                               going_concern=raw.get("going_concern"), today=today,
                               shares_source=raw.get("shares_source")) if raw.get("status") == "ok" else None)
        reason = None if flags is not None else str(raw.get("reason") or "Engine C 觀測不可用")
        return three_questions_for(ticker, today=today, wipeout=flags, wipeout_reason=reason,
                                   history_not_comparable=history_not_comparable), None
    except Exception as exc:  # noqa: BLE001 — 一檔讀不到記成「未讀到＋理由」，不帶走整板
        return None, f"{type(exc).__name__}: {str(exc)[:120]}"


def load_board(tickers: Sequence[str], *, today: date | None = None,
               holdings_loader: Callable[[], Sequence[Mapping[str, Any]]] | None = None) -> dict[str, Any]:
    """讀真實資料組整板（materialize 用；**唯讀**：敘事 ledger、讀圖對圖、registry、Engine C、Sheet readonly）。

    ⚠ Engine C：三題走 `?mode=ro`；四盞燈沿用 `engine_c.checklist.get_wipeout_inputs`（與單檔 materialize 同一條路，
    一般連線）；邊緣判定的市值正規化沿用 `alpha/providers/market_normalization.py`（FX 由 yfinance 取一次）。
    `tickers`：宇宙（APP 已 materialize 的那幾十檔）；敘事 ledger 裡有、宇宙沒有的也併進來——上板的依據是敘事。"""
    from engine_b import event_watch as ew
    from engine_b.disproof import current_briefs, load_lifecycle
    from engine_b.narrative_watches import link_breaks
    from identity.registry import get_registry
    from portfolio.holdings import resolve_holdings
    from portfolio.policy import load_beta_policy
    from query.structure import _load_edges
    from risk.hard_caps import is_beta_symbol

    from . import briefs as briefs_provider
    from .edge import edge_states
    from .structure_readings import reading_status_rows

    today = today or ew._today()
    registry = get_registry()
    brief_dir = briefs_provider.BRIEF_DIR
    ledger_present = brief_dir.is_dir()
    ledger_tickers = sorted(p.stem for p in brief_dir.glob("*.jsonl")) if ledger_present else []
    universe = sorted({str(t).upper() for t in tickers} | {t.upper() for t in ledger_tickers})
    watches = list(ew.load_watches().get("watches") or ())
    lifecycle = load_lifecycle()
    rows_raw, _errors = reading_status_rows(_load_edges(), today=today, watches=watches)
    reading_rows = {(r.get("node"), r.get("unit")): r for r in rows_raw if r.get("reading_id")}
    beta_policy = load_beta_policy()
    try:
        if holdings_loader is None:
            from fetchers.gsheets import fetch_portfolio

            def holdings_loader() -> Sequence[Mapping[str, Any]]:
                return fetch_portfolio(strict_operational=True)
        resolution, failure = resolve_holdings(list(holdings_loader()), registry=registry), None
    except Exception as exc:  # noqa: BLE001 — Sheet 讀不到＝已持有判定暫停，不是「沒持有」
        resolution, failure = None, type(exc).__name__
    held = held_index(resolution, is_beta=lambda s: is_beta_symbol(s, beta_policy), failure=failure)
    # 只在 Sheet 持有、宇宙沒有的公司也要上板（已持有、缺敘事），三題與燈一樣要算——不是「未讀到」。
    extra = {}
    for cid, info in (held.get("by_company") or {}).items():
        research = str(registry.research_ticker(cid) or "").upper()
        if research and research not in universe:
            extra[research] = cid
    edges = edge_states(sorted(set(universe) | set(extra)))

    tq_by_ticker: dict[str, Mapping[str, Any] | None] = {}
    tq_notes: dict[str, str] = {}
    parse_errors: list[str] = []
    rows: list[dict[str, Any] | None] = []
    for ticker in [*universe, *sorted(extra)]:
        records, errors = briefs_provider.read_brief_records(ticker)
        parse_errors.extend(errors)
        brief = select_brief(records, as_of=None, today=today)
        hnc = (brief.history_not_comparable.as_dict()
               if brief is not None and brief.record_version == RECORD_VERSION_V2 and brief.history_not_comparable
               else None)
        tq, note = _wipeout_and_three_questions(ticker, today=today, history_not_comparable=hnc)
        tq_by_ticker[ticker] = tq
        if note:
            tq_notes[ticker] = note
        cid = extra.get(ticker) or registry.company_id_for_ticker(ticker)
        rows.append(derive_row(ticker, cid, records=records, today=today, reading_rows=reading_rows,
                               watches=watches, lifecycle=lifecycle, edge=edges.get(ticker), three_questions=tq,
                               held=held, three_questions_note=note))
    for cid, info in (held.get("by_company") or {}).items():                   # registry 沒有 research ticker 的持有
        if cid not in {r["company_id"] for r in rows if r} and cid not in extra.values():
            rows.append(derive_row(str(info.get("sheet_ticker")), cid, records=[], today=today,
                                   reading_rows=reading_rows, watches=watches, lifecycle=lifecycle, edge=None,
                                   three_questions=None, held=held,
                                   three_questions_note="registry 沒有這家公司的 research ticker"))
    board = assemble_board(rows, universe=universe, held=held,
                           narrative_rewrite=board_rewrite(rows, link_breaks(current_briefs(), watches=watches)))
    board["rollup"] = rollup({t: tq_by_ticker[t] for t in universe}, {t: edges.get(t) or {} for t in universe},
                             not_read_reasons=tq_notes)
    board["ledger"] = {"present": ledger_present, "tickers": len(ledger_tickers), "parse_errors": len(parse_errors),
                       "parse_error_examples": parse_errors[:3]}
    board["today"] = today.isoformat()
    board["generated_at"] = datetime.now(timezone.utc).isoformat()
    return board


__all__ = ["ANSWER_WORDS", "CANDIDATES_THIS_IS_NOT", "GROUPS", "GROUP_LABELS", "SIDE_GROUPS", "SIDE_LABELS",
           "UNANSWERED", "assemble_board", "board_rewrite", "derive_row", "held_index", "load_board",
           "open_preconditions", "rollup", "stall_since", "three_words"]
