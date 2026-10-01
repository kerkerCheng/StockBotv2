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
from ..structure_reading.contracts import READING_KINDS, READING_UNITS
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
            failed.append(f"押的讀圖 {ride.reading_id} 已不是現行（現行 {row.get('reading_id') if row else '沒有'}）")
        elif row.get("status") not in CURRENT_READING_STATUSES:
            failed.append(f"押的讀圖 {ride.reading_id} 狀態 {row.get('status')}（只有 current／stale_low 算現行）")
        elif row.get("kind") not in OPEN_READING_KINDS:
            failed.append(f"押的讀圖 {ride.reading_id} 判讀是 {row.get('kind')}（可開要護城河或量）")
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
            r = reading_rows.get((ride.node, ride.unit))
            same = r is not None and r.get("reading_id") == ride.reading_id
            # 三種不同的事分開寫（L12）：現行（照印狀態）、那一格現行的是另一份（superseded）、那一格這次沒有讀圖列
            # （讀圖 ledger 讀不到或壞行——不是「換版」）。
            kind = r.get("kind") if same else None
            # 中文標籤跟著列走（2026-09-30 使用者回饋：候選板印 `volume`／`layer` 看不懂）——字彙的 SSOT 是讀圖 contracts，
            # 取前半句（與個股頁讀圖面板同一個切法）；畫面照抄、不自己維護對照表（L16）。
            row["rides"].append({"node": ride.node, "unit": ride.unit, "reading_id": ride.reading_id,
                                 "unit_label": str(READING_UNITS.get(ride.unit, ride.unit)).split("讀圖")[0],
                                 "kind": kind,
                                 "kind_label": str(READING_KINDS.get(str(kind), kind)).split("——")[0] if kind else None,
                                 "status": r.get("status") if same else ("superseded" if r is not None else "not_found")})
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
            elif w.get("status") == "active" and w.get("kind") == "date" and _until_reached(w, today):
                # 對稱面（寫入端 settle_due 兩種轉換都做）：date 已到 until、daily 還沒把它轉成 fired
                row["rewrite"].append(f"{GROUP_LABELS[cs.state]}在等的日子 {w.get('until')} 已到"
                                      "（daily 尚未標記），該重寫")
            elif w.get("status") != "active":
                row["rewrite"].append(f"{GROUP_LABELS[cs.state]}在等的 watch 已 {w.get('status')}，該重寫")
    since = stall_since(records, brief)
    row["since"] = since.isoformat()
    # 「今天」是排程時區的今天；since 是 UTC 時戳——換到同一個時區再相減，否則台北 00:00–08:00 寫的會多算一天。
    row["stall_days"] = (today - since.astimezone(ew._local_timezone()).date()).days
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


def _until_reached(watch: Mapping[str, Any], today: date) -> bool:
    try:
        return date.fromisoformat(str(watch.get("until"))) <= today
    except (TypeError, ValueError):
        return False


def board_rewrite(rows: Sequence[Mapping[str, Any] | None], breaks: Sequence[Mapping[str, Any]], *,
                  watches: Sequence[Mapping[str, Any]] = (),
                  company_ticker: Mapping[str, str] | None = None,
                  brief_company: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    """整板「敘事該重寫」清單：連結斷了（全部現行 v2 敘事，`link_breaks`）＋各列的敘事來源 watch 待重寫
    ＋**沒有列帶著的**待重寫 watch（現行敘事已撤回、是 v1、或根本沒有敘事——那家公司不在板上或那一列不是 v2，
    watch 仍在 narrative_rewrite 段；3.6 覆核：只收現行 v2 列會讓它們在板上消失、audit 卻報「那一列沒帶著」）。"""
    from engine_b.queue_segments import narrative_rewrite_state

    out = [{"kind": "link", **dict(b)} for b in breaks]
    carried: set[str] = set()
    by_id = {str(w.get("watch_id")): w for w in watches}
    for row in rows:
        for wid in (row or {}).get("rewrite_watch_ids") or ():
            carried.add(str(wid))
            state = narrative_rewrite_state(by_id.get(str(wid)) or {})
            out.append({"kind": "watch", "ticker": row["ticker"], "company_id": row.get("company_id"),
                        "brief_id": row.get("brief_id"), "watch_id": wid,
                        "state": REWRITE_STATE_WORDS.get(str(state), state)})
    for w in watches:
        state = narrative_rewrite_state(w)
        wid = str(w.get("watch_id"))
        if state is None or wid in carried:
            continue
        company = str(w.get("wake_brief") or (brief_company or {}).get(str(w.get("source_ref") or "").split("#")[0])
                      or "")
        out.append({"kind": "watch", "ticker": (company_ticker or {}).get(company) or company or "（公司不明）",
                    "company_id": company or None, "brief_id": None, "watch_id": wid,
                    "state": REWRITE_STATE_WORDS.get(str(state), state),
                    "note": "那家公司的現行敘事已撤回、是舊版或沒有敘事——板上沒有帶著它的 v2 列"})
    return out


def _wipeout_and_three_questions(ticker: str, *, today: date, history_not_comparable: Mapping[str, Any] | None
                                 ) -> tuple[Mapping[str, Any] | None, str | None]:
    """四盞燈（唯一串接點 `alpha.providers.wipeout.wipeout_for`）＋三題。讀不到回 `(None, 理由)`——理由要帶出去（INV-3）。"""
    from .three_questions import three_questions_for
    from .wipeout import wipeout_for

    try:
        flags, reason = wipeout_for(ticker, today=today)
        return three_questions_for(ticker, today=today, wipeout=flags, wipeout_reason=reason,
                                   history_not_comparable=history_not_comparable), None
    except Exception as exc:  # noqa: BLE001 — 一檔讀不到記成「未讀到＋理由」，不帶走整板
        return None, f"{type(exc).__name__}: {str(exc)[:120]}"


def candidate_context(tickers: Sequence[str], *, today: date | None = None,
                      holdings_loader: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
                      board: bool = True) -> dict[str, Any]:
    """候選狀態推導的共用輸入——**一次載入**，候選板與個股頁 materialize 共用（Step 3.7 接回偏差 21）。

    唯讀：敘事 ledger 目錄、讀圖對圖、watch registry、thesis lifecycle、registry、Engine C（邊緣判定）、Sheet readonly。
    `board=True`（候選板）：宇宙併入敘事 ledger 裡有的與只在 Sheet 持有的——上板的依據是敘事與持有；
    `board=False`（個股頁）：只算傳進來那幾檔的邊緣判定（頁面不需要別檔）。Sheet 讀不到＝已持有判定暫停，不是「沒持有」。"""
    from engine_b import event_watch as ew
    from engine_b.disproof import load_lifecycle
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

    def research(ticker: str) -> str:
        # 呼叫端可能給 alias（SIVEF、SKHY、XFAB）；上板與個股頁都以 research ticker 為鍵（3.7 R1：alias 查不到邊緣判定）。
        cid = registry.company_id_for_ticker(str(ticker))
        return str((registry.research_ticker(cid) if cid else None) or ticker).upper()

    universe = sorted({research(t) for t in tickers} | ({t.upper() for t in ledger_tickers} if board else set()))
    watches = list(ew.load_watches().get("watches") or ())
    lifecycle = load_lifecycle()
    rows_raw, reading_errors = reading_status_rows(_load_edges(), today=today, watches=watches)
    reading_rows = {(r.get("node"), r.get("unit")): r for r in rows_raw if r.get("reading_id")}
    # 有紀錄但沒有現行的格子＝全部撤回（`reading_status_rows` 的兩種 reading_id=None 列；整個節點撤回時 unit 是 None）。
    retracted_cells = sorted({(str(r.get("node")), r.get("unit")) for r in rows_raw if not r.get("reading_id")},
                             key=str)
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
    extra: dict[str, str] = {}
    if board:
        for cid, _info in (held.get("by_company") or {}).items():
            research = str(registry.research_ticker(cid) or "").upper()
            if research and research not in universe:
                extra[research] = cid
    return {"today": today, "registry": registry, "universe": universe, "extra": extra, "watches": watches,
            "lifecycle": lifecycle, "reading_rows": reading_rows, "reading_errors": list(reading_errors),
            "retracted_cells": retracted_cells,
            "held": held, "edges": edge_states(sorted(set(universe) | set(extra))),
            "ledger_present": ledger_present, "ledger_tickers": ledger_tickers}


def page_input(context: Mapping[str, Any], ticker: str, company_id: str | None, *,
               three_questions: Mapping[str, Any] | None, three_questions_note: str | None = None,
               judgment_conditions: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """個股頁首屏的候選狀態＋三個字、downside 的反證對 watch（Step 3.7）。**與候選板同一個 `derive_row`**——
    個股頁不另推一份（L16）。`three_questions`：這一頁 read model 已算好的那一份（與候選板同一個函式、同一個
    `history_not_comparable`）；沒有敘事也沒有持有時 `row` 是 None，三個字照印（會死嗎看燈；兩題「未答」）。"""
    from engine_b.disproof import downside_rows

    from . import briefs as briefs_provider

    today = context["today"]
    records, errors = briefs_provider.read_brief_records(ticker)
    row = derive_row(ticker, company_id, records=records, today=today, reading_rows=context["reading_rows"],
                     watches=context["watches"], lifecycle=context["lifecycle"],
                     edge=(context.get("edges") or {}).get(str(ticker).upper()), three_questions=three_questions,
                     held=context["held"], three_questions_note=three_questions_note)
    brief = select_brief(records, as_of=None, today=today)
    v2 = brief if brief is not None and brief.record_version == RECORD_VERSION_V2 else None
    words = (row["three_words"] if row is not None else
             three_words(three_questions, brief, not_read=(f"未讀到（{three_questions_note}）"
                                                           if three_questions_note else "未讀到")))
    page_row = None
    sheet = context["held"]
    row_absence = None
    if row is not None:
        # 個股頁是分析畫面，不帶任何部位欄位（`tests/test_analyst_view.py` 的部位 token 掃描）：「已持有」只以狀態字出現，
        # Sheet 那一列的來源欄位留在候選板（它才是對帳 Sheet 的畫面）。
        page_row = {k: v for k, v in row.items() if k not in ("held_source", "holdings_verified")}
        page_row["sheet_verified"] = bool(row.get("holdings_verified"))
        derived = row.get("derived")
        # v1 敘事只落附組（derived 是 None）：標籤跟候選板同一個（舊版（缺候選狀態）），不印「—」。
        page_row["derived_label"] = (GROUP_LABELS.get(str(derived)) or SIDE_LABELS.get(str(derived))
                                     or SIDE_LABELS.get(str(row.get("side"))))
    elif sheet.get("status") == "ok":
        row_absence = {"kind": "not_yet_recorded", "reason": "沒有敘事、也沒有持有——不上候選板（寫敘事才有候選狀態）"}
    else:
        # Sheet 讀不到時「也沒有持有」是沒驗過的否定（3.7 R1；L12）——產生端宣告暫停，不是「還沒做」。
        row_absence = {"kind": "upstream_unavailable",
                       "reason": f"沒有敘事；持股未讀到，已持有判定暫停（{sheet.get('reason') or '讀取失敗'}）——推不出它上不上板"}
    return {"row": page_row, "row_absence": row_absence, "three_words": words, "today": today.isoformat(),
            "sheet": {"status": sheet.get("status"), "reason": sheet.get("reason")},
            "brief_parse_errors": len(errors),
            "downside": downside_rows(company_id, ticker, records=records, current_brief=v2,
                                      watches=context["watches"], lifecycle=context["lifecycle"],
                                      reading_rows=context["reading_rows"],
                                      judgment_conditions=judgment_conditions,
                                      retracted_cells=context.get("retracted_cells") or ())}


def load_board(tickers: Sequence[str], *, today: date | None = None,
               holdings_loader: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
               context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """讀真實資料組整板（materialize 用；**唯讀**：敘事 ledger、讀圖對圖、registry、Engine C、Sheet readonly）。

    ⚠ Engine C：三題走 `?mode=ro`；四盞燈走唯一串接點 `alpha.providers.wipeout.wipeout_for`（與單檔 materialize 同一條路，
    一般連線）；邊緣判定的市值正規化沿用 `alpha/providers/market_normalization.py`（FX 由 yfinance 取一次）。
    `tickers`：宇宙（APP 已 materialize 的那幾十檔）；敘事 ledger 裡有、宇宙沒有的也併進來——上板的依據是敘事。
    `context`：`candidate_context(tickers)` 的結果（沒給就自己載一次）。"""
    from engine_b.disproof import current_briefs
    from engine_b.narrative_watches import link_breaks

    from . import briefs as briefs_provider

    ctx = context if context is not None else candidate_context(tickers, today=today,
                                                                 holdings_loader=holdings_loader)
    today = ctx["today"]
    registry = ctx["registry"]
    universe, extra, edges, held = ctx["universe"], ctx["extra"], ctx["edges"], ctx["held"]
    if context is not None:
        # 共用 context 是在 materialize **之前**以（要跑的 ∪ store 已有的）載的超集；組板的宇宙仍以呼叫端給的 `tickers`
        # （materialize 之後的目錄）為準——materialize 失敗的那一檔不得上板（3.7 覆核）。敘事 ledger 裡有的照舊併進來。
        wanted = {str(t).upper() for t in tickers} | {t.upper() for t in ctx["ledger_tickers"]}
        universe = [t for t in universe if t in wanted]
    watches, lifecycle, reading_rows = ctx["watches"], ctx["lifecycle"], ctx["reading_rows"]
    reading_errors = ctx["reading_errors"]
    ledger_present, ledger_tickers = ctx["ledger_present"], ctx["ledger_tickers"]
    # 只在 Sheet 持有的公司也進彙總（3.6 覆核：列上算了三題與燈、rollup 卻不含它——已持有最需要看會死嗎）。
    board_universe = sorted(set(universe) | set(extra))

    tq_by_ticker: dict[str, Mapping[str, Any] | None] = {}
    tq_notes: dict[str, str] = {}
    parse_errors: list[str] = []
    rows: list[dict[str, Any] | None] = []
    # 不上板的那幾檔（沒有敘事、也沒有持有）：原本只有計數，使用者看不到是誰（2026-09-30 回饋「候選板是死的」）。
    # 每檔帶首屏三個字——會死嗎照燈，兩題「未答」；上板的依據仍是敘事，這份清單不是第六組。
    no_narrative: list[dict[str, Any]] = []
    company_ticker: dict[str, str] = {}
    brief_company: dict[str, str] = {}
    for ticker in [*universe, *sorted(extra)]:
        records, errors = briefs_provider.read_brief_records(ticker)
        parse_errors.extend(errors)
        for rec in records:
            brief_company[f"brief:{rec.brief_id}"] = rec.company_id
            company_ticker.setdefault(rec.company_id, ticker)
        brief = select_brief(records, as_of=None, today=today)
        hnc = (brief.history_not_comparable.as_dict()
               if brief is not None and brief.record_version == RECORD_VERSION_V2 and brief.history_not_comparable
               else None)
        tq, note = _wipeout_and_three_questions(ticker, today=today, history_not_comparable=hnc)
        tq_by_ticker[ticker] = tq
        if note:
            tq_notes[ticker] = note
        cid = extra.get(ticker) or registry.company_id_for_ticker(ticker)
        row = derive_row(ticker, cid, records=records, today=today, reading_rows=reading_rows,
                         watches=watches, lifecycle=lifecycle, edge=edges.get(ticker), three_questions=tq,
                         held=held, three_questions_note=note)
        rows.append(row)
        if row is None:
            no_narrative.append({"ticker": ticker, "company_id": cid,
                                 "three_words": three_words(tq, brief, not_read=(f"未讀到（{note}）" if note
                                                                                 else "未讀到"))})
    for cid, info in (held.get("by_company") or {}).items():                   # registry 沒有 research ticker 的持有
        if cid not in {r["company_id"] for r in rows if r} and cid not in extra.values():
            rows.append(derive_row(str(info.get("sheet_ticker")), cid, records=[], today=today,
                                   reading_rows=reading_rows, watches=watches, lifecycle=lifecycle, edge=None,
                                   three_questions=None, held=held,
                                   three_questions_note="registry 沒有這家公司的 research ticker"))
    board = assemble_board(rows, universe=board_universe, held=held,
                           narrative_rewrite=board_rewrite(rows, link_breaks(current_briefs(), watches=watches),
                                                           watches=watches, company_ticker=company_ticker,
                                                           brief_company=brief_company))
    board["no_narrative"] = no_narrative
    board["rollup"] = rollup({t: tq_by_ticker[t] for t in board_universe},
                             {t: edges.get(t) or {} for t in board_universe}, not_read_reasons=tq_notes)
    board["ledger"] = {"present": ledger_present, "tickers": len(ledger_tickers), "parse_errors": len(parse_errors),
                       "parse_error_examples": parse_errors[:3]}
    # 讀圖 ledger 的壞行也要現形（對稱面：敘事 ledger 那一側已做）——壞掉的那份讀圖不在讀圖列裡，騎它的列會印 not_found。
    board["readings"] = {"parse_errors": len(reading_errors), "parse_error_examples": list(reading_errors)[:3]}
    board["today"] = today.isoformat()
    board["generated_at"] = datetime.now(timezone.utc).isoformat()
    return board


__all__ = ["ANSWER_WORDS", "CANDIDATES_THIS_IS_NOT", "GROUPS", "GROUP_LABELS", "SIDE_GROUPS", "SIDE_LABELS",
           "UNANSWERED", "assemble_board", "board_rewrite", "candidate_context", "derive_row", "held_index",
           "load_board", "open_preconditions", "page_input", "rollup", "stall_since", "three_words"]
