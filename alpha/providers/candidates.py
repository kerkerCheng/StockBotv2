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
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..candidates import (
    ANSWER_WORDS, CANDIDATES_THIS_IS_NOT, GROUP_LABELS, GROUPS, IN_NUMBERS_LINES, RETIRED_STATE_LABELS,
    PRICED_IN_LINES, REWRITE_STATE_WORDS, SIDE_GROUPS, SIDE_LABELS, UNANSWERED, assemble_board, body_version, cap_label,
    cited_identities, edge_note, held_index, judgment_version, new_edge_reason, not_edge_pending_note,
    on_threshold_entries, priced_since, rewrite_words, rides_reason, rollup,
    squash, stall_since, three_words, unread_new_edges, wipeout_worst,
    BODY_BEHIND_KINDS, body_behind_readings, body_behind_reasons,
)
from ..edge import not_edge_confirmed
from ..narrative.contracts import CANDIDATE_STATES_RETIRED, RECORD_VERSION_V2, InvestorBrief, select_brief
from ..narrative.depth_check import unchecked_items
from ..structure_reading.contracts import READING_KINDS, READING_UNITS
from .briefs import CURRENT_READING_STATUSES, OPEN_READING_KINDS, PRICED_IN_WRITE_LINES


def _valued(three_questions: Mapping[str, Any] | None, question: str, keys: Sequence[str]) -> bool:
    """這一題有沒有任何一行有值。**逐行看、不以 key 建 dict**——一檔屬於多個主題組時同一個 key 會有多行
    （一組有值、另一組缺席），dict 會讓後一行覆蓋前一行，造成假的「前提失效」（L17：key 真的唯一嗎）。"""
    return any(r.get("key") in keys and r.get("absence_kind") is None
               for r in (three_questions or {}).get(question) or ())


_RAW_DIR = Path(__file__).resolve().parents[2] / "library" / "raw"


@lru_cache(maxsize=1024)
def raw_text(ref: str) -> str:
    """`library/raw/<檔>` 全文，`squash` 過——敘事 stale ③ 比「邊的逐字在不在敘事引過的檔裡」用。
    檔不在、或路徑跑出 `library/raw/` 就回空字串（那一份只靠檔名比，比不到的邊照列——往看得見那邊倒）。"""
    path = (_RAW_DIR.parent.parent / ref).resolve()
    if _RAW_DIR.resolve() not in path.parents:
        return ""
    try:
        return squash(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""


def open_preconditions(brief: InvestorBrief, *, reading_rows: Mapping[tuple[str, str], Mapping[str, Any]],
                       three_questions: Mapping[str, Any] | None, blocking: Sequence[str],
                       breaks: Sequence[Mapping[str, Any]]) -> list[str]:
    """「可開」的起始門，每天重驗；回傳失效理由（空＝全部成立）。

    2026-11-03 起（盲點修法第 18＋16 條；AGENTS「讀到邊是加碼的門、不是起始的門」）起始門＝會死嗎不是紅、押的那一層讀過
    且判讀不是 neither、反證已寫下且有到期、已定價寫成一句脈絡（v2 契約本來就要七格與 answers）——加上本來就有的
    「宣告時的稽核行還在」「沒有待處置的反證」「連結來源仍在盯」。讀到邊與深挖清單是加碼條件，不在這裡。
    寫入端（`alpha.providers.briefs.v2_write_problems` ⑥）擋同一套，這裡是每天的對稱面（L17）。"""
    failed: list[str] = []
    if not brief.rides:                                                        # ① 押的那一層讀過、判讀不是 neither
        # 寫入端擋新寫的；舊紀錄（11-03 前的等回落讀成可開）可能沒押——驗不了押的層，不放行
        failed.append("沒有押任何讀圖（起始門要押的那一層讀過、判讀不是 neither）")
    for ride in brief.rides:
        row = reading_rows.get((ride.node, ride.unit))
        if row is None or row.get("reading_id") != ride.reading_id:
            failed.append(f"押的讀圖 {ride.reading_id} 已不是現行（現行 {row.get('reading_id') if row else '沒有'}）")
        elif row.get("status") not in CURRENT_READING_STATUSES:
            failed.append(f"押的讀圖 {ride.reading_id} 狀態 {row.get('status')}（只有 current／stale_low 算現行）")
        elif row.get("kind") not in OPEN_READING_KINDS:
            failed.append(f"押的讀圖 {ride.reading_id} 判讀是 {row.get('kind')}（起始門要押的那一層判讀不是 neither）")
    if not brief.disproof:                                                     # ② 反證已寫下且有到期
        failed.append("沒寫反證（起始門要反證已寫下且有到期——知道什麼時候認錯才開始）")
    if three_questions is None:                                                # ③ 會死嗎不是紅、answers 的稽核行還在
        failed.append("這次讀不到三題稽核區，會死嗎與 answers 都驗不了（fail closed）")
    else:
        worst, grey = wipeout_worst(three_questions)
        if worst == "red":
            failed.append("會死嗎是紅（四盞燈至少一盞紅）——起始門要會死嗎不是紅")
        elif worst is None:
            failed.append(f"會死嗎四盞燈都讀不到（灰 {grey}）——驗不了不是紅（fail closed）")
    answers = brief.answers
    if answers is not None and three_questions is not None:
        if answers.priced_in in ("yes", "no") and not _valued(three_questions, "priced_in", PRICED_IN_LINES):
            failed.append("已定價的稽核行已全部缺席（宣告時有值）")
        if answers.in_numbers in ("yes", "no") and not _valued(three_questions, "in_numbers", IN_NUMBERS_LINES):
            failed.append("出現在數字裡的稽核行已缺席（宣告時有值）")
        # 對稱面（ROADMAP 已定價變動計數器）：答量不到、今天量得到了——宣告時的前提也失效了。稽核行用**寫入端同一份**
        # （不含相對組漲幅：它有值並不強迫答 yes／no，用 PRICED_IN_LINES 會讓量不到的列大批誤判失效）。
        if answers.priced_in == "unmeasurable" and _valued(three_questions, "priced_in", PRICED_IN_WRITE_LINES):
            failed.append("已定價答量不到，今天稽核行有值（宣告時量不到）")
        if answers.in_numbers == "unmeasurable" and _valued(three_questions, "in_numbers", IN_NUMBERS_LINES):
            failed.append("出現在數字裡答量不到，今天稽核行有值（宣告時量不到）")
    failed.extend(f"待處置的反證 watch：{b}" for b in blocking)                # ④ 歸屬本檔的 watch 沒有待判
    failed.extend(f"連結 {b['link_source_ref']}：{b.get('label') or '已換版'}" for b in breaks)   # ⑤ 連結來源仍在盯
    return failed


# ---------------------------------------------------------------------------
# 是不是新賭注（Phase 7 Step 7.0e；使用者 2026-10-04 A3）
# ---------------------------------------------------------------------------

def bet_index(structure: Mapping[str, Any] | None, seats: Mapping[str, Sequence[str]], *,
              node_names: Mapping[str, str] | None = None) -> dict[str, Any]:
    """首屏「是不是新賭注」的比對輸入——**一次**建好，候選板與個股頁共用（同一個 `candidate_context`）。

    - 需求錨：結構表的逐列錨（`query.bottleneck.structure_table` 的 `demand_anchor`／`anchor_basis`，**唯一來源**；
      這裡收的是 materialize 同一輪寫下的 `structure_table` artifact 照抄的那幾格）。同一家公司同一個錨，任一列由節點
      自己走到（`row`）就記 `row`，全部是退回公司才走到的才記 `company`——錨的值與它的來處一起走（L12）。
    - 層與插槽：`structure_readings.seats_from_edges`（讀圖面板同一個函式）。
    `structure` 是 None 或 `{"absence": …}` → 需求錨這半邊 `upstream_unavailable`（層照比）——不是「沒有共用」。"""
    anchors: dict[str, dict[str, str]] = {}
    names: dict[str, str] = {}
    absence: dict[str, Any] | None = None
    if structure is None:
        absence = {"kind": "upstream_unavailable", "reason": "這次沒有載入結構表"}
    elif structure.get("absence"):
        absence = dict(structure["absence"])
    else:
        for r in structure.get("rows") or ():
            if r.get("bottleneck") and r.get("bottleneck_name"):
                names.setdefault(str(r["bottleneck"]), str(r["bottleneck_name"]))
            company, anchor = str(r.get("company_id") or ""), str(r.get("demand_anchor") or "")
            if not company or not anchor:
                continue
            mine = anchors.setdefault(company, {})
            if mine.get(anchor) != "row":
                mine[anchor] = str(r.get("anchor_basis") or "")
            if r.get("demand_anchor_name"):
                names.setdefault(anchor, str(r["demand_anchor_name"]))
    for node, name in (node_names or {}).items():
        if name:
            names.setdefault(str(node), str(name))
    # 有中文名的節點用中文（2026-10-29：「是不是新賭注」印英文的錨名，使用者看不懂）；沒有的照圖上的名字
    from alpha.node_labels import node_labels_zh

    names.update({node: zh for node, zh in node_labels_zh().items() if node in names})
    return {"anchors": anchors, "anchors_absence": absence,
            "anchors_as_of": None if absence else (structure or {}).get("generated_at"),
            "layers": {str(co): list(nodes) for co, nodes in seats.items()}, "names": names}


def shared_bet(company_id: str | None, ticker: str, *, held: Mapping[str, Any], bets: Mapping[str, Any] | None,
               registry: Any = None) -> dict[str, Any]:
    """首屏⑤：這一檔和每一檔**持有的 alpha 檔**（`held_index`：Sheet、alpha、股數 > 0）共用的需求錨與層／插槽。
    依 ticker 字母列（索引，不是名次）——**不打分、不排序、不加權**，也不進候選狀態的前提（plan §0 第 3 條）；沒有共用的持股不列。

    缺席由這裡宣告（L16）：Sheet 讀不到＝持有判定暫停（`upstream_unavailable`，不是「沒有共用」）；沒載入比對輸入同；
    結構表讀不到＝需求錨這半邊沒比（`anchors_absence`，層照比）；這檔走不到任何需求錨＝照實寫。
    每一句（`lines`）在這裡組好，候選板與個股頁照印（前端不組字）。欄位名不帶部位語彙（個股頁的 key 掃描）——
    「持有」只以 `state` 的值出現，與候選狀態同一個字彙。"""
    out: dict[str, Any] = {"rows": [], "absence": None, "anchors_absence": None, "anchors_as_of": None, "lines": []}
    if held.get("status") != "ok" or bets is None:
        reason = (str(held.get("reason") or "持股未讀到，已持有判定暫停") if held.get("status") != "ok"
                  else "這次沒有載入需求錨與層的比對輸入")
        out["absence"] = {"kind": "upstream_unavailable", "reason": reason}
        out["lines"] = [f"是不是新賭注：比不出來——{reason}"]
        return out
    names = bets.get("names") or {}
    anchors = bets.get("anchors") or {}
    layers = bets.get("layers") or {}
    out["anchors_absence"] = dict(bets["anchors_absence"]) if bets.get("anchors_absence") else None
    out["anchors_as_of"] = bets.get("anchors_as_of")
    me = str(company_id or "")
    my_anchors = anchors.get(me) or {}
    my_layers = set(layers.get(me) or ())
    rows: list[dict[str, Any]] = []
    for peer, info in (held.get("by_company") or {}).items():
        if str(peer) == me:
            continue
        theirs = anchors.get(str(peer)) or {}
        common_anchors = [{"node": a, "name": names.get(a), "basis": {"this": my_anchors[a], "other": theirs[a]}}
                          for a in sorted(set(my_anchors) & set(theirs))]
        common_layers = [{"node": n, "name": names.get(n)} for n in sorted(my_layers & set(layers.get(str(peer)) or ()))]
        if common_anchors or common_layers:
            label = (registry.research_ticker(peer) if registry is not None else None) or info.get("sheet_ticker")
            rows.append({"ticker": str(label or peer), "company_id": str(peer), "state": "held",
                         "shared_anchors": common_anchors, "shared_layers": common_layers})
    out["rows"] = sorted(rows, key=lambda r: (r["ticker"], r["company_id"]))
    out["lines"] = _shared_bet_lines(out, has_anchor=bool(my_anchors), has_layer=bool(my_layers))
    return out


def _shared_bet_lines(out: Mapping[str, Any], *, has_anchor: bool, has_layer: bool) -> list[str]:
    """`shared_bet` 要印的句子。錨是退回公司才走到的（任一邊）標「公司層」——與結構表那一格同一個標法。"""
    lines: list[str] = []
    for r in out["rows"]:
        bits = []
        if r["shared_anchors"]:
            bits.append("押同一個需求：" + "、".join(
                f"{a['name'] or a['node']}{'（公司層）' if 'company' in a['basis'].values() else ''}"
                for a in r["shared_anchors"]))
        if r["shared_layers"]:
            bits.append("坐同一層：" + "、".join(str(n["name"] or n["node"]) for n in r["shared_layers"]))
        lines.append(f"和你持有的 {r['ticker']} " + "；".join(bits))
    if not out["rows"]:
        lines.append("和目前持有的 alpha 檔沒有共用的層" if out["anchors_absence"]
                     else "和目前持有的 alpha 檔沒有共用的需求錨或層")
    if out["anchors_absence"]:
        lines.append(f"需求錨這半邊沒比：{out['anchors_absence'].get('reason') or '結構表讀不到'}")
    elif not has_anchor:
        lines.append("這檔在結構表走不到任何需求錨——需求錨無從比對，只比了層")
    if not has_layer:
        lines.append("這檔在圖上沒有坐任何層或插槽——同一層無從比對")
    # 2026-10-29：「需求錨取自 <日期> 的結構表逐列錨」那一句不再上畫面（使用者：「太多日期很沒必要」）；日期照舊在 `anchors_as_of`。
    return lines


def _reason_story(brief: InvestorBrief | None, stories: Mapping[str, Mapping[str, Any]] | None) -> dict[str, Any]:
    """候選理由的故事（`reason_story`）與缺 X 的短標（`missing_label`，只有宣告缺 X 才有）。故事 ledger 照抄，不改字；
    沒有這一版敘事的故事＝兩格 None（理由照印原文）。"""
    story = (stories or {}).get(brief.brief_id) if brief is not None else None
    candidate = (story or {}).get("candidate") if isinstance((story or {}).get("candidate"), Mapping) else {}
    state = brief.candidate_state.state if brief is not None and brief.candidate_state else None
    label = candidate.get("missing_label") if state == "missing" else None
    return {"reason_story": candidate.get("story") or None, "missing_label": label or None,
            "story_id": (story or {}).get("story_id")}


def derive_row(ticker: str, company_id: str | None, *, records: Sequence[InvestorBrief], today: date,
               reading_rows: Mapping[tuple[str, str], Mapping[str, Any]], watches: Sequence[Mapping[str, Any]],
               lifecycle: Mapping[str, Any] | None, edge: Mapping[str, Any] | None,
               three_questions: Mapping[str, Any] | None, held: Mapping[str, Any],
               three_questions_note: str | None = None, bets: Mapping[str, Any] | None = None,
               registry: Any = None, own_history_at: Callable[..., Mapping[str, Any]] | None = None,
               bars_at: Callable[[str, date], Sequence[tuple[date, float | None]]] | None = None,
               stories: Mapping[str, Mapping[str, Any]] | None = None,
               company_assertions: Sequence[Mapping[str, Any]] | None = None,
               raw_text: Callable[[str], str] | None = None,
               open_document_requests: Sequence[int] | None = None,
               readings_by_id: Mapping[str, Any] | None = None,
               ) -> dict[str, Any] | None:
    """一檔的候選狀態。沒有敘事、也沒有持有 → None（不上板，計數另印「無敘事」）。

    邊緣：非邊緣進「非倍率候選」；邊緣判定少一個輸入時**只擋宣告可開**（附組「可開但邊緣無法量」），
    缺 X／不要照敘事分組、列上帶 `edge_note`（2026-10-30）。

    宣告一律照讀法分組（`CandidateState.effective`）：11-03 前的「已定價等回落」讀成可開、走同一道起始門，
    `declared_retired` 照留當時寫的字（舊紀錄不回寫）。`addon_unchecked`：可開或已持有（敘事不是「不要」）的檔，深挖清單
    還沒查的項目（`alpha.narrative.depth_check.unchecked_items`）——⑤「加碼條件還沒查」數它；其餘列是空清單。

    `bets`／`registry`：首屏「是不是新賭注」的比對輸入（`bet_index`，Phase 7 Step 7.0e）——只呈現在 `shared_bet`，
    **不進任何狀態判斷**；沒給就由 `shared_bet` 宣告缺席。

    `rewrite[]`（**每一列都算，不論宣告哪一態、落哪一組**）：連結斷了（附為什麼斷）、敘事來源 watch 醒來／觸及／
    到期未判（plan §5 第 6 點：候選板印「敘事該重寫：<watch id> <狀態>」）、缺 X（與舊的等回落）在等的 watch 已失效、
    騎的讀圖已換版、圖上有新邊而敘事沒讀過那份文件（ROADMAP「敘事 stale 計數器」①③，2026-10-29——心跳 ⑤ 讀這兩種，
    不自己再算）。`company_assertions`：這家公司在圖上的 assertion 寫入紀錄（`query.company_assertions`）；
    None＝圖讀不到，`rewrite_new_edges` 也是 None（沒算，不是 0）。`raw_text`：敘事引的 raw 檔全文的讀法（比邊的逐字；
    沒給＝只比文件 id、網址與直接引的邊）。
    `readings_by_id`：全部讀圖紀錄（含已被取代的）——②④「正文寫的時候騎的那份讀圖」要查得到舊紀錄（2026-11-03）；
    None＝沒載入，`rewrite_reading_changes` 也是 None（沒算，不是 0）。"""
    from engine_b import event_watch as ew
    from engine_b.narrative_watches import blocking_for_open, link_breaks, pending_rewrite
    from engine_b.queue_segments import narrative_rewrite_state

    brief = select_brief(records, as_of=None, today=today)
    held_info = (held.get("by_company") or {}).get(str(company_id)) if held.get("status") == "ok" else None
    if brief is None and held_info is None:
        return None
    v2 = brief is not None and brief.record_version == RECORD_VERSION_V2
    cs = brief.candidate_state if v2 else None
    eff = cs.effective if cs else None
    row: dict[str, Any] = {
        "ticker": ticker, "company_id": company_id,
        "brief_id": brief.brief_id if brief else None,
        "record_version": brief.record_version if brief else None,
        "declared": eff,
        "declared_label": GROUP_LABELS.get(eff) if eff else None,
        # 當時寫的是退役的宣告值（11-03 前的等回落）才有——照讀成 `declared`，這一格只讓稽核分得出來
        "declared_retired": cs.state if cs and cs.state in CANDIDATE_STATES_RETIRED else None,
        # 它的中文（11-04 R2：個股頁與「問 Claude」原本把讀法 `declared_label` 標成「敘事宣告」——當時說的是等回落就印等回落，
        # INV-6）。加法欄、不升版：讀不到它的舊 artifact 由畫面退回印原字
        "declared_retired_label": (RETIRED_STATE_LABELS.get(cs.state, cs.state)
                                   if cs and cs.state in CANDIDATE_STATES_RETIRED else None),
        "derived": None, "group": None, "side": None,
        "reason": cs.reason if cs else None,
        # 故事層（2026-10-29）：理由的一句故事、缺 X 的短標——寫給這一版敘事的才算（敘事換版就退回印原理由）
        **_reason_story(brief if v2 else None, stories),
        "preconditions": [], "rewrite": [], "rewrite_watch_ids": [], "rewrite_words": [],
        "rewrite_rides": [], "rewrite_new_edges": [],
        # 敘事 stale ②④（2026-11-03）：正文版騎的讀圖 vs 這一格現行的讀圖，判讀或供給側家數變了（`body_behind_readings`）；
        # 沒比成的格數另計（讀圖紀錄找不到——不是 0）
        "rewrite_reading_changes": [], "reading_change_unchecked": 0,
        "edge": {**{k: (edge or {}).get(k) for k in ("state", "label", "reasons", "market_cap_usd", "analyst_count",
                                                     "on_threshold", "inputs_as_of", "prior", "prior_absence")},
                 "market_cap_label": cap_label((edge or {}).get("market_cap_usd"))},
        # 邊緣判定少一個輸入時的那一句（下面判邊緣時才填；已持有、非邊緣確認、舊版不填）——是標記，不是分組；
        # 2026-11-01 起「非邊緣待確認」（今天才翻成非邊緣）也寫在這一格
        "edge_note": None,
        # 遲滯（ROADMAP「邊緣門檻的遲滯與在門檻上計數器」，2026-11-01）：今天判非邊緣、前一次不是 → 這裡帶前一次是什麼；
        # None＝不適用（不是非邊緣、或連續兩次已確認進「非倍率候選」）
        "edge_pending": None,
        "held_source": dict(held_info) if held_info else None,
        "holdings_verified": held.get("status") == "ok",
        "rides": [], "watch": None, "since": None, "stall_days": None,
        # 缺 X 三分法（2026-10-30）：敘事宣告的 missing_kind（filing／layer／user_document；舊敘事沒寫＝None「未分」）
        "missing_kind": cs.missing_kind if cs else None,
        # 待辦池裡還開著、標了這家公司的「向你要文件」編號（load_board 讀池；None＝池沒讀到或單檔頁沒帶，不是 0）
        "document_requests": (sorted(int(n) for n in open_document_requests)
                              if open_document_requests is not None else None),
        # 加碼條件（Phase 7 Step 7.0d）：每條與它的 watch 狀態；觸及只提醒，不是買進訊號、不改候選狀態
        "confirm": [], "confirm_summary": None,
        # 加碼條件還沒查（2026-11-03，第 18＋16 條）：可開或已持有（敘事不是「不要」）才有加碼這件事——深挖清單還沒查的
        # 項目名；已持有沒有 v2 敘事＝十項都還沒查。等回落的價格叫醒、重開條件、只差已定價隨等回落退役，列上不再有那幾格
        "addon_unchecked": (unchecked_items(brief.depth_check_map if v2 else None)
                            if eff == "open" or (held_info is not None and eff != "pass") else []),
        # 逾期型反證條數（2026-11-03，第 10 條②）：這一版敘事標 `deadline` 的反證幾條；沒有 v2 敘事＝None（不是 0 條）。
        # 板上「逾期型反證 0 條的持有／可開敘事」數的是可開與已持有裡這一格是 0 的列（`alpha.candidates.no_deadline_rows`）
        "deadline_disproof": sum(1 for d in brief.disproof if d.deadline) if v2 else None,
        # 是不是新賭注（Phase 7 Step 7.0e）：和持有的 alpha 檔共用的需求錨與層——只呈現，不進任何狀態判斷
        "shared_bet": shared_bet(company_id, ticker, held=held, bets=bets, registry=registry),
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
    from engine_b.disproof import confirm_rows, confirm_summary

    row["confirm"] = confirm_rows(brief, watches)
    row["confirm_summary"] = confirm_summary(row["confirm"])      # 個股頁首屏只數在等的那幾條（2026-10-29）
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
        # 舊的等回落讀成可開，但那筆等待照舊有到期——結束了就叫重寫（重寫時寫不出等回落，舊紀錄就這樣自然換掉）
        who = GROUP_LABELS.get(cs.state) or RETIRED_STATE_LABELS.get(cs.state, cs.state)
        if cs.watch_id not in row["rewrite_watch_ids"]:                       # 醒來／到期已由上面那條列過
            if w is None:
                row["rewrite"].append(f"{who}在等的 watch {cs.watch_id} 不存在，該重寫")
            elif w.get("status") == "active" and ew.past_expiry(w, today=today):
                row["rewrite"].append(f"{who}在等的 watch 已過到期日 {w.get('expires')}（daily 尚未標記），該重寫")
            elif w.get("status") == "active" and w.get("kind") == "date" and _until_reached(w, today):
                # 對稱面（寫入端 settle_due 兩種轉換都做）：date 已到 until、daily 還沒把它轉成 fired
                row["rewrite"].append(f"{who}在等的日子 {w.get('until')} 已到（daily 尚未標記），該重寫")
            elif w.get("status") != "active":
                row["rewrite"].append(f"{who}在等的 watch 已 {w.get('status')}，該重寫")
    # 敘事落後於讀圖與圖（ROADMAP「敘事 stale 計數器」①③，2026-10-29）：①騎的讀圖那一格現行已是另一份；
    # ③正文最後一次改動之後，圖上這家公司多了敘事沒讀過的邊（以邊為單位；比文件 id、直接引的網址與邊的逐字）。
    row["rewrite_rides"] = [
        {"node": r["node"], "unit": r["unit"], "reading_id": r["reading_id"],
         "current_reading_id": (reading_rows.get((r["node"], r["unit"])) or {}).get("reading_id")}
        for r in row["rides"] if r.get("status") == "superseded"]
    row["rewrite"].extend(rides_reason(r) for r in row["rewrite_rides"])
    # ②④（2026-11-03）：正文最後一次改動時騎的讀圖，跟這一格現行的讀圖比判讀與供給側家數。騎舊讀圖（①）的格也比——
    # 只換騎就夠（①）還是正文要改（②④），要分得出來。
    if readings_by_id is None:
        row["rewrite_reading_changes"] = None
        row["reading_change_unchecked"] = None
    else:
        entries, unchecked = body_behind_readings(
            body_version(records, brief), brief, readings_by_id=readings_by_id,
            current_cells={cell: (r or {}).get("reading_id") for cell, r in reading_rows.items()})
        row["rewrite_reading_changes"] = entries
        row["reading_change_unchecked"] = unchecked
        row["rewrite"].extend(reason for entry in entries for reason in body_behind_reasons(entry))
    if company_assertions is None:
        row["rewrite_new_edges"] = None
    else:
        cited = cited_identities(brief)
        # 檔與檔之間放一個逐字裡不會有的字，免得兩份檔的頭尾接起來湊出一段假的逐字
        text = "\x00".join(raw_text(ref) for ref in cited.raw_refs) if raw_text is not None else ""
        row["rewrite_new_edges"] = unread_new_edges(company_assertions, since=body_version(records, brief).created_at,
                                                    cited=cited, cited_text=text)
        row["rewrite"].extend(new_edge_reason(e) for e in row["rewrite_new_edges"])
    since = stall_since(records, brief)
    row["since"] = since.isoformat()
    # 「今天」是排程時區的今天；since 是 UTC 時戳——換到同一個時區再相減，否則台北 00:00–08:00 寫的會多算一天。
    row["stall_days"] = (today - since.astimezone(ew._local_timezone()).date()).days
    # 已定價變動（只印不判；在 held 提早 return 之前——持有的也印）。loader 沒給（測試、個股頁單檔）就不算。
    row["priced_since"] = (_priced_since_row(ticker, records, brief, three_questions=three_questions, today=today,
                                             own_history_at=own_history_at, bars_at=bars_at)
                           if own_history_at is not None and bars_at is not None else None)
    # 2026-11-03：等回落的價格叫醒（#116）、重開條件（#124）、只差已定價（#123）隨等回落併回可開一起退役——已定價是可開那一列
    # 的脈絡（`priced_since` 照印），價格動了不再叫研究重寫；要不要等價格是使用者在短版 ③ 的選擇（看了沒買）。
    row["rewrite_words"] = rewrite_words(row["rewrite"])
    if row["group"] == "held":
        return row
    state = (edge or {}).get("state")
    if state == "not_edge":
        if not_edge_confirmed(edge):
            row.update(side="not_multiple", derived="not_multiple")
            return row
        # 遲滯（2026-11-01；failure log #110 第 4 次）：今天才翻成非邊緣（前一次判邊緣／無法量／沒有更早的／沒讀到）——
        # 不列撤回建議，照敘事分組、列上帶標記；宣告可開的照「缺輸入不放行」那條既有的路（同一個附組、同一句標記）
        prior = (edge or {}).get("prior") or {}
        row["edge_pending"] = {"prior_state": prior.get("state") if prior else None,
                               "prior_inputs_as_of": prior.get("inputs_as_of") if prior else None,
                               "prior_absence": (edge or {}).get("prior_absence")}
        row["edge_note"] = not_edge_pending_note(edge)
        if eff == "open":
            row.update(side="edge_unmeasurable", derived="edge_unmeasurable")
            return row
        row.update(group=eff, derived=eff)
        return row
    if state != "edge":
        # 缺輸入不放行（`alpha.edge`）——要擋的只有宣告可開的那一種；缺 X／不要照敘事分組、帶標記
        # （2026-10-30 使用者「好 改吧」：原本一律蓋掉宣告，敘事寫的 X 與「不要」的理由都被藏進這一組，L12）
        row["edge_note"] = edge_note(edge)
        if eff == "open":
            row.update(side="edge_unmeasurable", derived="edge_unmeasurable")
            return row
        row.update(group=eff, derived=eff)
        return row
    if eff == "open":
        blocking = blocking_for_open(str(company_id), ticker, watches=watches, lifecycle=lifecycle,
                                     brief_ids=brief_ids, current_brief=brief)
        row["preconditions"] = open_preconditions(brief, reading_rows=reading_rows, three_questions=three_questions,
                                                  blocking=blocking, breaks=breaks)
        if row["preconditions"]:
            row.update(side="precondition_failed", derived="precondition_failed")
            return row
    row.update(group=eff, derived=eff)
    return row


def _close_on_or_before(bars: Sequence[tuple[date, float | None]], day: date) -> tuple[date, float] | None:
    hits = [(d, float(c)) for d, c in bars if d <= day and c is not None]
    return hits[-1] if hits else None


def _return_between(bars: Sequence[tuple[date, float | None]], base_day: date, today: date) -> float | None:
    base, now = _close_on_or_before(bars, base_day), _close_on_or_before(bars, today)
    if base is None or now is None or base[1] == 0:
        return None
    return now[1] / base[1] - 1


def knowable_bar_day(created_at: datetime) -> date:
    """寫入當下系統手上**最後一根收盤**的日子（INV-6 的截點）：daily 每天 `schedule.daily_local_time`（排程時區）才抓前一天
    收盤——那之前寫的只有前前一天。R2 2026-10-21：原本寫死「判斷日前一天」，台北 00:00–05:30 寫的版本（美股甚至當天
    收盤還不存在）會往後多看一根；FORM 10-16 00:01 那版手打「寫入時第 87」，前一天截點回算 84.0、這個截點 87.2。"""
    from datetime import timedelta

    from engine_b import event_watch as ew
    from engine_b.routine_config import load_schedule

    hh, mm = (int(x) for x in str(load_schedule()["daily_local_time"]).split(":"))
    local = created_at.astimezone(ew._local_timezone())
    return (local - timedelta(hours=hh, minutes=mm)).date() - timedelta(days=1)


def _then_row(ticker: str, version: InvestorBrief, cutoff: date,
              own_history_at: Callable[..., Mapping[str, Any]]) -> tuple[dict[str, Any], str]:
    """某一版判斷當時的已定價①：寫入端記下的優先（`recorded`）；舊版本點時回算（`recomputed`，截點＝`knowable_bar_day`）。
    寫入當下偶發讀不到（記下的是 upstream_unavailable）也退回回算——不讓一次讀取失敗永久蓋掉可回算的值（R2）。
    回算失敗照實記缺席——**不得拿今天的值頂替**（INV-6）。"""
    snap = version.priced_at_write
    if snap is not None and snap.absence_kind != "upstream_unavailable":
        return snap.as_dict(), "recorded"
    hnc = version.history_not_comparable.as_dict() if version.history_not_comparable else None
    try:
        row = dict(own_history_at(ticker, cutoff, history_not_comparable=hnc))
    except Exception as exc:  # noqa: BLE001 — 回算壞了照實記缺席，不帶走整列
        row = {"absence_kind": "upstream_unavailable", "reason": f"判斷日回算失敗：{type(exc).__name__}"}
    return row, "recomputed"


def _priced_since_row(ticker: str, records: Sequence[InvestorBrief], brief: InvestorBrief, *,
                      three_questions: Mapping[str, Any] | None, today: date,
                      own_history_at: Callable[..., Mapping[str, Any]],
                      bars_at: Callable[[str, date], Sequence[tuple[date, float | None]]]) -> dict[str, Any] | None:
    """判斷日的自家三年百分位 → 今天，與判斷日以來報酬（調整後收盤）。
    判斷日印日曆日；回算的截點與報酬基準一律用 `knowable_bar_day`（同一個函式，三處共用）。"""
    from engine_b import event_watch as ew

    tz = ew._local_timezone()
    now = next((dict(r) for r in (three_questions or {}).get("priced_in") or () if r.get("key") == "own_history_pctile"),
               None)
    answer = brief.answers.priced_in if brief.answers else None
    if answer not in ("yes", "no") and not (answer == "unmeasurable" and (now or {}).get("value") is not None):
        return None                                    # 不會出列的不必回算（R2：40 份答量不到、147 次多餘取數）
    judged = judgment_version(records, brief)
    jday = judged.created_at.astimezone(tz).date()
    jcut = knowable_bar_day(judged.created_at)
    then, source = _then_row(ticker, judged, jcut, own_history_at)
    try:
        bars = list(bars_at(ticker, today))
    except Exception:  # noqa: BLE001 — 報酬算不出來就不印報酬，百分位照印
        bars = []
    base_day = (date.fromisoformat(str(then["as_of"])[:10]) if source == "recorded" and then.get("as_of") else jcut)
    return priced_since(ticker, brief, judged, judgment_day=jday.isoformat(), then=then, then_source=source, now=now,
                        return_since=_return_between(bars, base_day, today))


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
    watch 仍在 narrative_rewrite 段；3.6 覆核：只收現行 v2 列會讓它們在板上消失、audit 卻報「那一列沒帶著」）
    ＋騎舊讀圖（`kind=rides`，一份讀圖一筆）＋判讀變了／供給家數變了（`kind=reading_kind`／`supply_count`，一格一筆，2026-11-03）
    ＋新邊沒讀（`kind=new_edges`，一家公司一筆、帶邊與要讀的文件）——
    心跳 ⑤「敘事該重寫」讀這份清單，不自己再算（ROADMAP「敘事 stale 計數器」同源，2026-10-29）。
    已回落、重開條件達成、沒寫重開條件三種（`pulled_back`／`reopen_met`／`no_reopen`）2026-11-03 隨等回落退役。"""
    from engine_b.queue_segments import narrative_rewrite_state

    out = [{"kind": "link", **dict(b)} for b in breaks]
    carried: set[str] = set()
    by_id = {str(w.get("watch_id")): w for w in watches}
    for row in rows:
        who = {"ticker": (row or {}).get("ticker"), "company_id": (row or {}).get("company_id"),
               "brief_id": (row or {}).get("brief_id")}
        out.extend({"kind": "rides", **who, **dict(ride)} for ride in (row or {}).get("rewrite_rides") or ())
        # ②④（2026-11-03）：一格一個 change 一筆（kind＝reading_kind／supply_count，`BODY_BEHIND_KINDS`）——四種訊號各自計數
        for entry in (row or {}).get("rewrite_reading_changes") or ():
            out.extend({"kind": change, **who, **{k: v for k, v in dict(entry).items() if k != "changes"}}
                       for change in entry.get("changes") or () if change in BODY_BEHIND_KINDS)
        if (row or {}).get("rewrite_new_edges"):
            out.append({"kind": "new_edges", **who, "edges": [dict(e) for e in row["rewrite_new_edges"]]})
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
                      board: bool = True, structure: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """候選狀態推導的共用輸入——**一次載入**，候選板與個股頁 materialize 共用（Step 3.7 接回偏差 21）。

    唯讀：敘事 ledger 目錄、讀圖對圖、watch registry、thesis lifecycle、registry、Engine C（邊緣判定）、Sheet readonly。
    `board=True`（候選板）：宇宙併入敘事 ledger 裡有的與只在 Sheet 持有的——上板的依據是敘事與持有；
    `board=False`（個股頁）：只算傳進來那幾檔的邊緣判定（頁面不需要別檔）。Sheet 讀不到＝已持有判定暫停，不是「沒持有」。
    `structure`：結構表的逐列錨（`webapp.materialize.bet_structure` 讀同一輪的 `structure_table` artifact；Phase 7 Step 7.0e）
    ——與讀圖對圖同一份邊算出的坐的層，一起建成「是不是新賭注」的比對索引 `bets`（`bet_index`）。沒給＝需求錨這半邊缺席。"""
    from engine_b import event_watch as ew
    from engine_b.disproof import load_lifecycle
    from identity.registry import get_registry
    from portfolio.holdings import load_ignored, resolve_holdings
    from portfolio.policy import load_beta_policy
    from query.structure import _load_edges
    from risk.hard_caps import is_beta_symbol

    from . import briefs as briefs_provider
    from .edge import edge_states_with_prior
    from .structure_readings import reading_status_rows, seats_from_edges

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
    graph_edges = _load_edges()
    rows_raw, reading_errors = reading_status_rows(graph_edges, today=today, watches=watches)
    reading_rows = {(r.get("node"), r.get("unit")): r for r in rows_raw if r.get("reading_id")}
    # 敘事 stale ②④（2026-11-03）：全部讀圖紀錄（含已被取代的）——「正文寫的時候騎的那份」多半已不是現行。
    # 讀不到＝整板宣告「判讀／家數變了沒算」（不是 0，INV-3）
    try:
        from .structure_readings import known_nodes, read_reading_records

        readings_by_id = {rec.reading_id: rec for node in known_nodes() for rec in read_reading_records(node)[0]}
        readings_note = None
    except Exception as exc:  # noqa: BLE001 — 只讓 ②④ 宣告沒算
        readings_by_id, readings_note = None, f"{type(exc).__name__}: {str(exc)[:80]}"
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
    ignored, ignored_problem = load_ignored()      # 使用者決定不研究的持股（config/holdings_coverage.json）
    held = held_index(resolution, is_beta=lambda s: is_beta_symbol(s, beta_policy), failure=failure,
                      ignored=ignored, ignored_problem=ignored_problem)
    # 只在 Sheet 持有、宇宙沒有的公司也要上板（已持有、缺敘事），三題與燈一樣要算——不是「未讀到」。
    extra: dict[str, str] = {}
    if board:
        for cid, _info in (held.get("by_company") or {}).items():
            research = str(registry.research_ticker(cid) or "").upper()
            if research and research not in universe:
                extra[research] = cid
    from .stories import current_stories

    # 故事層（2026-10-29）：候選理由的一句故事與缺 X 的短標——只呈現，不進任何狀態判斷；讀不到就沒有（照印原理由）
    try:
        stories, _story_errors = current_stories()
    except Exception:  # noqa: BLE001 — 故事 ledger 讀不到只讓理由照印原文
        stories = {}
    # 敘事 stale ③（2026-10-29）：每家公司在圖上的 assertion 寫入紀錄。讀不到＝整板宣告「新邊沒讀沒算」（不是 0，INV-3）
    try:
        from query.company_assertions import load_company_assertions

        company_assertions, assertions_note = load_company_assertions(), None
    except (Exception, SystemExit) as exc:  # noqa: BLE001 — `_graph_driver` 缺密碼丟 SystemExit；只讓 ③ 宣告沒算
        company_assertions, assertions_note = None, f"{type(exc).__name__}: {str(exc)[:80]}"
    return {"today": today, "registry": registry, "universe": universe, "extra": extra, "watches": watches,
            "lifecycle": lifecycle, "reading_rows": reading_rows, "reading_errors": list(reading_errors),
            "retracted_cells": retracted_cells,
            # 今天的判定＋今天判非邊緣的檔的前一次判定（遲滯，2026-11-01）；兩趟共用一個 FX 快取
            "held": held, "edges": edge_states_with_prior(sorted(set(universe) | set(extra))),
            "ledger_present": ledger_present, "ledger_tickers": ledger_tickers,
            "bets": bet_index(structure, seats_from_edges(graph_edges)), "stories": stories,
            "company_assertions": company_assertions, "company_assertions_note": assertions_note,
            "readings_by_id": readings_by_id, "readings_by_id_note": readings_note}


def assertions_for(context: Mapping[str, Any], company_id: str | None) -> list[Mapping[str, Any]] | None:
    """一家公司的 assertion 寫入紀錄；context 沒讀到圖（或沒帶這個鍵）＝None——`derive_row` 就不算 ③，不是 0。"""
    index = context.get("company_assertions")
    if index is None:
        return None
    return list(index.get(str(company_id), ())) if company_id else []


_OVER_EDGE = {"cap_over_edge": "市值", "coverage_over_edge": "分析師家數"}


def no_narrative_reason(edge: Mapping[str, Any] | None, records: Sequence[Any], *, today: date) -> str:
    """沒有敘事也沒有持有的那一頁，候選狀態格寫「為什麼沒有敘事」（2026-10-28 使用者：「滑 app 滑了很久看不出來
    這些公司為何沒有敘事」——原本 104 頁都只印同一句「不上候選板」）。非邊緣＝規定不寫敘事（research-drain 段 5
    的母體外）：那一句照抄閉環同一個 `population_detail`（L16，不另造一份）；撤回過的另寫哪天撤回、理由開頭。"""
    from .closure import population_detail

    edge = dict(edge or {})
    if edge.get("state") == "not_edge":
        line, _due = population_detail("non_multiple", "", {"edge": edge}, board_day=today.isoformat(),
                                       last_brief=None, today=today)
        # 判定日不上畫面（2026-10-29 使用者：「太多日期很沒必要」）；閉環那一邊照舊帶日期
        line = line.split("（判定")[0]
        limits = edge.get("thresholds") or {}
        over = [_OVER_EDGE.get(str(r), str(r)) for r in edge.get("reasons") or ()]
        bound = ""
        if limits.get("market_cap_max_usd") and limits.get("analyst_count_max") is not None:
            bound = (f"（門檻：市值 ≤{limits['market_cap_max_usd'] / 1e9:g}B USD、分析師 ≤{limits['analyst_count_max']} 位"
                     + (f"；超過的是{'與'.join(over)}）" if over else "）"))
        reason = f"{line}{bound}——非邊緣不寫敘事，它的財報與文件當層的證據用"
    else:
        reason = "沒有敘事、也沒有持有——不上候選板（寫敘事才有候選狀態）"
        if edge.get("label"):
            reason += f"；邊緣判定：{edge['label']}"
    latest = records[-1] if records else None
    if latest is not None and getattr(latest, "retracted", False):
        day = str(getattr(latest, "created_at", "") or "")[:10]
        note = str(getattr(latest, "note", "") or "").strip()
        # 撤回說明只在短的時候附上（2026-10-29「理由太冗長看不完」：AMKR 那一筆是一整段查證命令）；全文照舊在 ledger
        reason += f"。原本的敘事 {day} 撤回" + (f"：{note}" if note and len(note) <= RETRACTION_NOTE_SHOWN else "")
    return reason


#: 沒有敘事那一頁的理由裡，撤回說明附上的上限（字）——超過就只寫撤回日（說明在 ledger）。
RETRACTION_NOTE_SHOWN = 24


def page_input(context: Mapping[str, Any], ticker: str, company_id: str | None, *,
               three_questions: Mapping[str, Any] | None, three_questions_note: str | None = None) -> dict[str, Any]:
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
                     held=context["held"], three_questions_note=three_questions_note,
                     bets=context.get("bets"), registry=context.get("registry"),
                     stories=context.get("stories"),
                     company_assertions=assertions_for(context, company_id), raw_text=raw_text,
                     readings_by_id=context.get("readings_by_id"))
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
        # 已定價變動（priced_since）也不上個股頁：首屏不放價格報酬（2026-09-30 使用者定案）——它住候選板與心跳。
        page_row = {k: v for k, v in row.items() if k not in ("held_source", "holdings_verified", "priced_since")}
        page_row["sheet_verified"] = bool(row.get("holdings_verified"))
        derived = row.get("derived")
        # v1 敘事只落附組（derived 是 None）：標籤跟候選板同一個（舊版（缺候選狀態）），不印「—」。
        page_row["derived_label"] = (GROUP_LABELS.get(str(derived)) or SIDE_LABELS.get(str(derived))
                                     or SIDE_LABELS.get(str(row.get("side"))))
    elif sheet.get("status") == "ok":
        edge = (context.get("edges") or {}).get(str(ticker).upper())
        # `edge_state` 跟著缺席走到首頁分組：非邊緣＝規定不寫（不是待做），與「邊緣、還沒寫」分兩組（L12）。
        row_absence = {"kind": "not_yet_recorded", "reason": no_narrative_reason(edge, records, today=today),
                       "edge_state": (edge or {}).get("state")}
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
                                      retracted_cells=context.get("retracted_cells") or ())}


def open_document_requests_by_company() -> tuple[dict[str, list[int]], dict[str, Any]]:
    """待辦池裡還開著的「向你要文件」（`engine_b.todo.document_requests`，唯一名單）→ `company_id → [n]`，與一格「讀了沒有」。
    池讀不到 → `({}, {"status": "unavailable", …})`：列上 `document_requests=None`、狀態塊印「未算」，不印成 0（INV-3）。
    沒標公司的請求（舊的、或 lead refs 沒寫 `trace_review_company`）併不到任何一列，列在 `unassigned` 讓它現形。只讀池。"""
    try:
        from engine_b import todo as todo_mod

        items = todo_mod.document_requests(todo_mod.load())
    except Exception as exc:  # noqa: BLE001 — 池壞了只讓這一格說讀不到，不帶走整板
        return {}, {"status": "unavailable", "reason": f"{type(exc).__name__}: {str(exc)[:120]}"}
    by_company: dict[str, list[int]] = {}
    unassigned: list[int] = []
    for item in items:
        if item.get("company_id"):
            by_company.setdefault(str(item["company_id"]), []).append(int(item["n"]))
        else:
            unassigned.append(int(item["n"]))
    return by_company, {"status": "ok", "open": len(items), "unassigned": sorted(unassigned)}


def load_board(tickers: Sequence[str], *, today: date | None = None,
               holdings_loader: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
               context: Mapping[str, Any] | None = None,
               structure: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """讀真實資料組整板（materialize 用；**唯讀**：敘事 ledger、讀圖對圖、registry、Engine C、Sheet readonly）。

    ⚠ Engine C：三題走 `?mode=ro`；四盞燈走唯一串接點 `alpha.providers.wipeout.wipeout_for`（與單檔 materialize 同一條路，
    一般連線）；邊緣判定的市值正規化沿用 `alpha/providers/market_normalization.py`（FX 由 yfinance 取一次）。
    `tickers`：宇宙（APP 已 materialize 的那幾十檔）；敘事 ledger 裡有、宇宙沒有的也併進來——上板的依據是敘事。
    `context`：`candidate_context(tickers)` 的結果（沒給就自己載一次，`structure` 照傳）。"""
    from engine_b.disproof import current_briefs
    from engine_b.narrative_watches import link_breaks

    from . import briefs as briefs_provider
    from .three_questions import adjusted_bars, own_history_at

    ctx = context if context is not None else candidate_context(tickers, today=today,
                                                                 holdings_loader=holdings_loader, structure=structure)
    today = ctx["today"]
    # 缺 X 三分法 ①（2026-10-30）：待辦池裡還開著的「向你要文件」對公司併到列上——池只讀；讀不到列上是 None、計數印「未算」
    doc_requests, doc_check = open_document_requests_by_company()
    registry = ctx["registry"]
    bets = ctx.get("bets")
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
                         held=held, three_questions_note=note, bets=bets, registry=registry,
                         own_history_at=own_history_at, bars_at=adjusted_bars, stories=ctx.get("stories"),
                         company_assertions=assertions_for(ctx, cid), raw_text=raw_text,
                         open_document_requests=(doc_requests.get(str(cid), []) if doc_check["status"] == "ok"
                                                 else None),
                         readings_by_id=ctx.get("readings_by_id"))
        rows.append(row)
        if row is None:
            no_narrative.append({"ticker": ticker, "company_id": cid,
                                 "three_words": three_words(tq, brief, not_read=(f"未讀到（{note}）" if note
                                                                                 else "未讀到")),
                                 # 7.0g-2：閉環母體要分「非倍率」與「邊緣」——邊緣判定本來就對整個宇宙算好了，
                                 # 這裡只是寫出來（不進 freshness_identity：市值每天在動，那不是認知變了）。
                                 "edge": edges.get(ticker)})
    for cid, info in (held.get("by_company") or {}).items():                   # registry 沒有 research ticker 的持有
        if cid not in {r["company_id"] for r in rows if r} and cid not in extra.values():
            rows.append(derive_row(str(info.get("sheet_ticker")), cid, records=[], today=today,
                                   reading_rows=reading_rows, watches=watches, lifecycle=lifecycle, edge=None,
                                   three_questions=None, held=held,
                                   three_questions_note="registry 沒有這家公司的 research ticker",
                                   bets=bets, registry=registry))
    board = assemble_board(rows, universe=board_universe, held=held,
                           narrative_rewrite=board_rewrite(rows, link_breaks(current_briefs(), watches=watches),
                                                           watches=watches, company_ticker=company_ticker,
                                                           brief_company=brief_company))
    board["no_narrative"] = no_narrative
    # 在門檻上（ROADMAP「邊緣門檻的遲滯與在門檻上計數器」，2026-11-01）：整個宇宙逐檔、ticker 字母序——只計數、不排序、不改門檻。
    # 帶寬的人話由產生端給（心跳、closure-gate 照抄，L16）；宇宙空就是空 list（不是沒算）、帶寬 None。
    from alpha.edge import band_label

    board["on_threshold"] = on_threshold_entries({t: edges.get(t) for t in board_universe},
                                                 {str(r.get("ticker")) for r in rows if r})
    board["on_threshold_band"] = band_label(next((e.get("thresholds") for e in edges.values() if e), None))
    board["counts"]["on_threshold"] = len(board["on_threshold"])
    board["document_requests_check"] = doc_check
    # ③ 算了沒有（INV-3）：圖讀不到時「新邊沒讀」是沒算，心跳 ⑤ 照這一格印「未算」，不印成 0
    board["new_edges_check"] = {"status": "ok" if ctx.get("company_assertions") is not None else "unavailable",
                                "reason": ctx.get("company_assertions_note")}
    # ②④ 算了沒有（2026-11-03）：讀圖紀錄讀不到＝沒算；讀到了但有幾格的舊讀圖找不到也要說（`unchecked`，不是 0）
    unchecked = sum(int(r.get("reading_change_unchecked") or 0) for r in rows if r)
    board["reading_change_check"] = ({"status": "ok", "reason": None, "unchecked": unchecked}
                                     if ctx.get("readings_by_id") is not None else
                                     {"status": "unavailable", "reason": ctx.get("readings_by_id_note"), "unchecked": None})
    board["rollup"] = rollup({t: tq_by_ticker[t] for t in board_universe},
                             {t: edges.get(t) or {} for t in board_universe}, not_read_reasons=tq_notes)
    board["ledger"] = {"present": ledger_present, "tickers": len(ledger_tickers), "parse_errors": len(parse_errors),
                       "parse_error_examples": parse_errors[:3]}
    # 讀圖 ledger 的壞行也要現形（對稱面：敘事 ledger 那一側已做）——壞掉的那份讀圖不在讀圖列裡，騎它的列會印 not_found。
    board["readings"] = {"parse_errors": len(reading_errors), "parse_error_examples": list(reading_errors)[:3]}
    board["today"] = today.isoformat()
    board["generated_at"] = datetime.now(timezone.utc).isoformat()
    return board


# ---------------------------------------------------------------------------
# 逾期型反證的寫入提醒（2026-11-03 盲點修法第 10 條②）
# ---------------------------------------------------------------------------

def deadline_reminder(record: Mapping[str, Any], *, held: bool | None) -> str | None:
    """`alpha brief --add` 寫完印的一行提醒：宣告可開、或候選板上是已持有的敘事，一條逾期型反證（`disproof[].deadline: true`）
    都沒有就提醒——**只印、不擋**（審查 strategy-4：事件型反證要等一份新文件才醒，輸家常常什麼都不發）。`held`＝候選板
    artifact 上是不是已持有（`held_on_board`；None＝讀不到——不猜，短版 ④「逾期型反證 0 條」每天會點名）。撤回與 v1 不提醒。"""
    if record.get("retracted") or record.get("record_version") != RECORD_VERSION_V2:
        return None
    if (record.get("candidate_state") or {}).get("state") != "open" and held is not True:
        return None
    if any(d.get("deadline") is True for d in record.get("disproof") or ()):
        return None
    return ("  ⚠ 這一版沒有逾期型反證（disproof[].deadline: true）——持有／可開的敘事至少一條寫成「X 未在 D 前發生」："
            "輸家常常什麼都不發，事件型反證等不到新文件就不會醒（只提醒、不擋；短版 ④ 每天點名）")


def held_on_board(ticker: str) -> bool | None:
    """候選板 artifact 上這一檔是不是已持有（寫入時的提醒用）。讀不到、或那一版板子持股沒讀到＝None——不讀 Sheet、零網路。"""
    try:
        from webapp.store import StateArtifactStore

        board, _freshness = StateArtifactStore().read("candidates")
    except Exception:  # noqa: BLE001
        return None
    if (board.get("holdings") or {}).get("status") != "ok":
        return None
    return any(str(r.get("ticker") or "").upper() == str(ticker).upper()
               for r in (board.get("groups") or {}).get("held") or ())


__all__ = ["ANSWER_WORDS", "CANDIDATES_THIS_IS_NOT", "GROUPS", "GROUP_LABELS", "SIDE_GROUPS", "SIDE_LABELS",
           "UNANSWERED", "assemble_board", "assertions_for", "bet_index", "board_rewrite", "candidate_context",
           "deadline_reminder", "derive_row", "held_index", "held_on_board", "raw_text",
           "knowable_bar_day", "load_board", "open_preconditions", "page_input", "rollup", "shared_bet", "stall_since",
           "three_words"]
