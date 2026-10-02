"""成交的研究收據（Phase 3 Step 3.8）——A5 記下「當時憑什麼決定」；**A3 不替 A5 做決定**。

`scripts/record_trade.py` 在每一筆 **alpha** 成交寫 trade_log 之前組這份收據，放進那一筆事件的
`research_receipt` key（不另開檔、不與 `hard_cap_check` 混）。beta 不需要收據（行為與 3.8 之前相同）。

收據分兩半（L12：宣告與推導是兩件事，壓成一份就分不出「寫的人說」與「系統當天算」）：

- `declared`：現行 v2 敘事的宣告——`brief_id`（內容雜湊）、`candidate_state`、`answers`、`rides[]` 的 `reading_id`
  與各讀圖**寫入當時**的 `result_digest`（讀圖 ledger）、歸屬本檔還在處理中的 watch（`attributed_watches`，§5 第 8 點）。
- `derived`：當天候選板 artifact 那一列（前提重驗、失效原因、邊緣判定、三個字）＋個股頁 artifact 的三題稽核行，
  以及成交前由 Sheet 推得的持有狀態（`--log-only` 時 Sheet 已是成交後，照實標）。
  **資本路徑不連 Neo4j、不即時打行情或 FX**——讀圖對圖與邊緣判定已在 materialize 算好；artifact 缺席或不是今天 →
  `derived.status = upstream_unavailable`＋原因，**不擋成交**（plan §0 第 13 條）。

`narrative`（封閉字彙）：`present`（有現行 v2）／`legacy_v1`（現行是 v1，沒有候選狀態）／`absent`（沒有敘事）／
`unresolved`（Sheet symbol 解析不到 `co:*`，INV-1 不猜）／`unreadable`（敘事 ledger 讀不到、有壞行，或 registry 沒有
research ticker 可對——確認不了現行是哪一版；L11-5「我找不到」≠「它不存在」）。**買進只有 `present` 放行**；其餘 fail closed，
`--no-narrative-override "<理由>"` 放行並把理由寫進收據。這個放行**不放行**硬擋，硬擋的 `--override` 也不放行它。

本模組只組資料，不讀檔、不連網——輸入由呼叫端（`scripts/record_trade.py::_research_inputs`）一次讀好帶進來。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping, Sequence

RECEIPT_VERSION = "research-receipt/v1"

#: 收據機制上線日（Phase 3 Step 3.8 交付，2026-09-30）。這天之前的成交**沒有、也不可能有**當時的收據——
#: `scripts/record_trade.py --backfill-before-receipts` 只收這些（Phase 5 Step 5.3）；這天或之後的成交一律走正常路徑。
#: 常數，不從 trade_log 推（trade_log 在 5.3 時沒有任何收據事件可推，plan §13）。
RECEIPT_EPOCH = date(2026, 9, 30)

#: 敘事狀態 → 人讀（收據與 CLI 輸出同一份字）。封閉字彙：加一個值就要多一段消費端語意（追蹤表 live lane 照抄它）。
NARRATIVE_STATES: Mapping[str, str] = {
    "present": "有現行 v2 敘事",
    "legacy_v1": "現行敘事是舊版 v1（沒有候選狀態）——視同缺 v2",
    "absent": "沒有敘事",
    "unresolved": "Sheet symbol 解析不到公司（INV-1：不猜）",
    "unreadable": "敘事 ledger 讀不到或有壞行（或 registry 沒有 research ticker 可對）——確認不了現行是哪一版，視同缺 v2",
    # Phase 5 Step 5.3：回填的舊成交——缺的是紀錄本身（那時候還沒有收據機制），不是「我們沒讀到」。
    "backfilled": "回填：成交早於收據機制上線（2026-09-30），當時沒有收據",
}


def current_brief(records: Sequence[Any], *, today: date) -> Any:
    """現行敘事（最新、未撤回；與候選板同一個 `select_brief`）。"""
    from alpha.narrative.contracts import select_brief

    return select_brief(list(records), as_of=None, today=today)


def narrative_state(company_id: str | None, brief: Any, *, readable: bool = True) -> str:
    """`readable=False`：ledger 讀不到／有壞行／沒有 research ticker 可對——**不得**壓成 `absent`（L12）。
    有壞行時 `select_brief` 可能退回較舊的一版而得到 present，所以只要有壞行就是 unreadable（fail closed）。"""
    from alpha.narrative.contracts import RECORD_VERSION_V2

    if not company_id:
        return "unresolved"
    if not readable:
        return "unreadable"
    if brief is None:
        return "absent"
    return "present" if brief.record_version == RECORD_VERSION_V2 else "legacy_v1"


def _live_watches(watches: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """還在處理中的 watch（在盯／醒來／觸及待處置／到期未判）；已收掉的不列。"""
    from engine_b.disproof import watch_category

    out = []
    for w in watches:
        if w.get("status") in ("active", "fired") or watch_category(w) is not None:
            out.append({"watch_id": w.get("watch_id"), "kind": w.get("kind"), "status": w.get("status"),
                        "source_ref": w.get("source_ref"), "expires": w.get("expires")})
    return out


def attributed(company_id: str | None, ticker: str | None, *, records: Sequence[Any], brief: Any,
               watches: Sequence[Mapping[str, Any]], lifecycle: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    """歸屬本檔的 watch——**§5 第 8 點的唯一歸屬函式**（以來源判，不以 entities）。"""
    from alpha.narrative.contracts import RECORD_VERSION_V2
    from engine_b.narrative_watches import attributed_watches

    if not company_id:
        return []
    v2 = brief if brief is not None and brief.record_version == RECORD_VERSION_V2 else None
    return attributed_watches(str(company_id), str(ticker or ""), watches=watches, lifecycle=lifecycle,
                              brief_ids=[str(r.brief_id) for r in records], current_brief=v2)


def declared_half(brief: Any, *, company_id: str | None, ticker: str | None, records: Sequence[Any],
                  watches: Sequence[Mapping[str, Any]], lifecycle: Mapping[str, Any] | None,
                  reading_digests: Mapping[str, str | None]) -> dict[str, Any] | None:
    """現行 v2 敘事的宣告；不是 v2 回 None（由 `narrative` 說是哪一種沒有）。"""
    from alpha.narrative.contracts import RECORD_VERSION_V2

    if brief is None or brief.record_version != RECORD_VERSION_V2:
        return None
    cs = brief.candidate_state
    mine = attributed(company_id, ticker, records=records, brief=brief, watches=watches, lifecycle=lifecycle)
    return {
        "brief_id": brief.brief_id,
        "brief_created_at": brief.created_at.isoformat(),
        "candidate_state": ({"state": cs.state, "watch_id": cs.watch_id, "reason": cs.reason} if cs else None),
        "answers": ({"priced_in": brief.answers.priced_in, "in_numbers": brief.answers.in_numbers}
                    if brief.answers else None),
        # 讀圖寫入當時的 result_digest（讀圖 ledger 裡那一筆）；讀不到記 None，不猜（INV-3：由 `reading_digest_missing` 現形）。
        "rides": [{"node": r.node, "unit": r.unit, "reading_id": r.reading_id,
                   "result_digest": reading_digests.get(r.reading_id)} for r in brief.rides],
        "reading_digest_missing": sorted(r.reading_id for r in brief.rides if not reading_digests.get(r.reading_id)),
        "watches": _live_watches(mine),
    }


def _local_date(stamp: Any) -> date | None:
    """排程時區的日期。排程時區讀不到時退回本機時區——與 `record_trade` 對 `_today()` 的退回一致，
    **不讓成交 crash**（3.8 R2-b：原本只接 TypeError／ValueError，設定檔讀不到的 OSError 會連賣出一起擋下）。"""
    try:
        moment = datetime.fromisoformat(str(stamp))
    except (TypeError, ValueError):
        return None
    try:
        from engine_b import event_watch as ew

        return moment.astimezone(ew._local_timezone()).date()
    except Exception:  # noqa: BLE001 — 設定檔讀不到／時區名不認得：退回本機時區
        return moment.astimezone().date()


def _candidate_row(artifact: Mapping[str, Any], ticker: str | None,
                   company_id: str | None = None) -> Mapping[str, Any] | None:
    """以公司對（INV-1）；公司沒解析到才退回 ticker。候選板對沒有 research ticker 的持有以 Sheet ticker 開列。"""
    rows = [row for bucket in ("groups", "side_groups") for group in (artifact.get(bucket) or {}).values()
            for row in group or ()]
    if company_id:
        hit = next((row for row in rows if row.get("company_id") == company_id), None)
        if hit is not None:
            return hit
    if ticker:
        return next((row for row in rows if str(row.get("ticker") or "").upper() == str(ticker).upper()), None)
    return None


def _three_question_rows(analyst: Mapping[str, Any]) -> list[dict[str, Any]]:
    """稽核行**照抄**：值／來源／as of／口徑／規則／支撐數字（detail）／狀態或缺席分型——收據是「當時憑什麼」唯一的
    A5 留存（個股頁 artifact 每天覆蓋），漏抄的日後補不回來（3.8 R1）。"""
    panel = ((analyst.get("view") or {}).get("three_questions") or {})
    out = []
    for line in panel.get("lines") or ():
        datum = line.get("datum") or {}
        deps = datum.get("dependencies") or {}
        out.append({"question": deps.get("question"), "key": deps.get("row_key"), "label": datum.get("label"),
                    "status": datum.get("status"), "value": datum.get("value"),
                    "absence_kind": datum.get("absence_kind"), "reason": datum.get("reason"),
                    "as_of": datum.get("as_of"), "source": deps.get("source"), "basis": deps.get("basis"),
                    "rule": datum.get("method") or deps.get("rule"), "detail": deps.get("detail")})
    return out


def derived_half(ticker: str | None, *, today: date, candidates: Mapping[str, Any] | None,
                 candidates_error: str | None, analyst: Mapping[str, Any] | None, analyst_error: str | None,
                 held_before: bool | None, log_only: bool, company_id: str | None = None,
                 sheet_symbol: str | None = None, held_company: bool | None = None,
                 declared_brief_id: str | None = None) -> dict[str, Any]:
    """當天的推導。**缺席、不是今天、或不是現在視角 → upstream_unavailable＋原因，不擋成交**（A3 不替 A5 做決定）。

    `held_before`：以 symbol＋broker 定位的那一列（成交會改的那一列）；`held_company`：同一家公司在 Sheet 任何一列有沒有
    持股（候選板「已持有」同一個層級）。兩者都記，免得「這一列沒有、別家券商有」被讀成沒持有（3.8 R1）。"""
    post = "post_trade（--log-only：Sheet 已由使用者手動更新成成交後）"
    sheet = {"held_before_this_row": held_before, "held_before_company": held_company,
             "sheet_state": post if log_only else "pre_trade"}
    problems: list[str] = []
    out: dict[str, Any] = {"sheet": sheet}
    if candidates is None:
        problems.append(f"候選板 artifact 讀不到（{candidates_error or '缺席'}）")
    elif str(candidates.get("today")) != today.isoformat():
        problems.append(f"候選板 artifact 是 {candidates.get('today')} 的，不是今天 {today.isoformat()}（先跑 materialize --candidates）")
    else:
        row = _candidate_row(candidates, ticker or sheet_symbol, company_id)
        out["candidate_as_of"] = candidates.get("today")
        out["candidate_generated_at"] = candidates.get("generated_at")
        out["candidate"] = dict(row) if row is not None else None
        if row is None:
            unresolved = [str(t).upper() for t in ((candidates.get("holdings") or {}).get("unresolved") or ())]
            out["candidate_note"] = (
                ("解析不到公司；候選板把它列在「持股解析不到」" if str(sheet_symbol or "").upper() in unresolved
                 else "解析不到公司，候選板也沒有它") if not company_id
                else "候選板上沒有這一檔（沒有敘事也沒有持有，或不在宇宙裡）")
        elif declared_brief_id and row.get("brief_id") != declared_brief_id:
            # 宣告與推導講的是不同版本（L12）：今天寫了新敘事、候選板還是舊快照。
            problems.append(f"候選板那一列的敘事版本（{row.get('brief_id') or '無'}）不是現行（{declared_brief_id}）"
                            "——候選板早於這次寫入，先重跑 materialize --candidates")
    if analyst is None:
        # 理由照抄產生端（讀不到、或解析不到公司而根本沒有個股頁可對——兩者下一步不同，不加「讀不到」前綴；L12）。
        problems.append(f"個股頁 artifact：{analyst_error or '讀不到（缺席）'}")
    elif _local_date(analyst.get("generated_at")) != today:
        problems.append(f"個股頁 artifact 產於 {analyst.get('generated_at')}，不是今天（三題稽核行沒記）")
    elif analyst.get("as_of") is not None or str(analyst.get("point_in_time_mode") or "current") != "current":
        # 同一路徑也可能被 `materialize <T> --as-of` 覆蓋：那是歷史視角，不是當天推導（INV-6；3.8 R1）。
        problems.append(f"個股頁 artifact 是 as-of {analyst.get('as_of')} 視角，不是現在（三題稽核行沒記）")
    else:
        panel = ((analyst.get("view") or {}).get("three_questions") or {})
        out["three_questions_as_of"] = analyst.get("generated_at")
        out["three_questions_panel"] = {"status": panel.get("status"), "absence_kind": panel.get("absence_kind"),
                                        "reason": panel.get("reason")}
        out["three_questions"] = _three_question_rows(analyst)
        if panel.get("status") in (None, "missing", "invalidated", "not_modeled", "insufficient_evidence"):
            # 整段缺席不得記成 available＋空陣列（3.8 R1 blocking：silent absence）。
            problems.append(f"個股頁三題整段缺席（{panel.get('absence_kind') or '分型未宣告'}："
                            f"{panel.get('reason') or '沒有理由句'}）")
    out["status"] = "upstream_unavailable" if problems else "available"
    if problems:
        out["reason"] = "；".join(problems)
    return out


def check_disproof_watch(watch_id: str, *, company_id: str | None, ticker: str | None, records: Sequence[Any],
                         brief: Any, watches: Sequence[Mapping[str, Any]],
                         lifecycle: Mapping[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    """賣出的 `--disproof-watch`：必須存在、且**以來源歸屬本檔**（entities 含本檔但來源不歸屬 → 拒；
    來源歸屬但 entities 不含本檔 → 收——歸屬以來源判，plan §5 第 8 點）。回 `(watch 摘要, 錯誤)`。"""
    found = next((w for w in watches if str(w.get("watch_id")) == str(watch_id)), None)
    if found is None:
        return None, f"watch {watch_id} 不存在（讀 registry）"
    if lifecycle is None and str(found.get("source_ref") or "").startswith("thesis:"):
        # 「確認不了」≠「不歸屬」（L12；與 `blocking_for_open` 對 None 的處理對稱，L17）。
        return None, (f"watch {watch_id} 的來源是 thesis memo，但 thesis lifecycle 讀不到——無法確認它歸不歸屬 {ticker}"
                      "（先修 thesis/lifecycle.json；或拿掉 --disproof-watch 照記賣出）")
    mine = attributed(company_id, ticker, records=records, brief=brief, watches=watches, lifecycle=lifecycle)
    if all(str(w.get("watch_id")) != str(watch_id) for w in mine):
        return None, (f"watch {watch_id}（來源 {found.get('source_ref') or found.get('wake_brief') or '—'}）不歸屬 {ticker}"
                      "——歸屬以來源判（本檔 thesis／騎的讀圖／敘事連結／敘事自己的反證），不以 entities")
    return {"watch_id": found.get("watch_id"), "kind": found.get("kind"), "status": found.get("status"),
            "source_ref": found.get("source_ref"), "condition": found.get("condition")}, None


def build_receipt(*, side: str, why: str, symbol: str, today: date, inputs: Mapping[str, Any],
                  held_before: bool | None, log_only: bool, narrative_override: str | None = None,
                  disproof_watch: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """組一份收據（alpha 買進與賣出共用）。`inputs`：`_research_inputs` 讀好的原料。"""
    records = list(inputs.get("records") or ())
    brief = current_brief(records, today=today)
    company_id, ticker = inputs.get("company_id"), inputs.get("research_ticker")
    state = narrative_state(company_id, brief, readable=bool(inputs.get("narrative_readable", True)))
    declared = declared_half(brief, company_id=company_id, ticker=ticker, records=records,
                             watches=inputs.get("watches") or (), lifecycle=inputs.get("lifecycle"),
                             reading_digests=inputs.get("reading_digests") or {}) if state == "present" else None
    receipt: dict[str, Any] = {
        "version": RECEIPT_VERSION, "side": side, "why": why, "sheet_symbol": symbol,
        "company_id": company_id, "research_ticker": ticker, "resolution": inputs.get("resolution_source"),
        "narrative": state, "narrative_label": NARRATIVE_STATES[state],
        "declared": declared,
        "derived": derived_half(ticker, today=today, candidates=inputs.get("candidates"),
                                candidates_error=inputs.get("candidates_error"), analyst=inputs.get("analyst"),
                                analyst_error=inputs.get("analyst_error"), held_before=held_before,
                                log_only=log_only, company_id=company_id, sheet_symbol=symbol,
                                held_company=(None if log_only else inputs.get("held_company")),
                                declared_brief_id=(declared or {}).get("brief_id")),
        "input_problems": list(inputs.get("problems") or ()),
    }
    if narrative_override:
        receipt["narrative_override_reason"] = narrative_override
    if disproof_watch is not None:
        receipt["disproof_watch"] = dict(disproof_watch)
    return receipt


def build_backfill_receipt(*, side: str, why: str, symbol: str, company_id: str | None,
                           research_ticker: str | None, resolution: str | None, reason: str) -> dict[str, Any]:
    """回填舊成交的收據（Phase 5 Step 5.3；plan §4）。

    **不讀敘事、不讀候選板、不讀個股頁**：拿今天的判斷填進一筆 2026-08 的成交，就是讓收據回答一個它當時答不出的問題
    （INV-6：答不出「T 時刻我知道什麼」就明確拒絕，不得靜默回傳當前值）。所以 `declared`／`derived` 一律 `None`，
    `narrative` 是 `backfilled`——追蹤表的 live lane 照抄它、印「回填、無當時收據」。公司身分照解析（INV-1），那是
    今天也拿得回來的事實，不是判斷。"""
    return {
        "version": RECEIPT_VERSION, "side": side, "why": why, "sheet_symbol": symbol,
        "company_id": company_id, "research_ticker": research_ticker, "resolution": resolution,
        "narrative": "backfilled", "narrative_label": NARRATIVE_STATES["backfilled"],
        "backfill_reason": reason, "declared": None, "derived": None,
    }


__all__ = ["NARRATIVE_STATES", "RECEIPT_EPOCH", "RECEIPT_VERSION", "attributed", "build_backfill_receipt",
           "build_receipt", "check_disproof_watch",
           "current_brief", "declared_half", "derived_half", "narrative_state"]
