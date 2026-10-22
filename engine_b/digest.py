"""每日摘要（2026-10-07 使用者指示）——daily ⑪b 準備、⑪c LLM、⑪e 套用。

使用者原話：「我想看到你每天 websearch 的結果跟你做了什麼，比較有實感……Lead 抓了哪些 TL;DR、Websearch 大事件 TL;DR、
幾件事待我決定、健康度」「心跳沒有不能跑 LLM，必要就跑」。

分工（LLM 可以解析與提議，不可以授權——L15）：

- **prepare**（程式）：組 LLM 要的資料——今天這一輪新進或剛分流的 lead（harvest 與外部雷達；標題、來源、摘錄、分流結果）
  與雷達收據裡收下的那幾則（層別、標題、一句事實、為什麼）。**不讀 Sheet、持股、NAV、私人路徑**。
- **LLM**（⑪c，`claude -p` 零工具、只回 JSON）：寫兩段 TL;DR——lead 抓到什麼、市場大事；每一句都要列出它根據的 lead id。
- **apply**（程式）：每一句引用的 lead id 都要在這一輪的資料裡、段別與長度合法，不合的整句丟掉並照數（INV-3）；
  寫成 `library/private/heartbeat/digest_<日期>.json`。**不寫任何 authority**。

「待你決定」「健康度」「todo」**不經 LLM**——它們是 registry 與執行紀錄的計數，心跳用程式組（`crons/heartbeat.py`）。
LLM 失敗（例：額度用完）時沒有摘要檔，心跳印「今天沒產生」並退回程式組的標題清單，其餘照發。

**影響對照（雷達精進 C2，2026-10-21）**：prepare 用 `engine_b.impact` 對今天的外部 lead 算確定性對照（碰到哪份敘事哪一格、
哪份讀圖、哪條在盯條件），寫 `impact_<日期>.json`（LLM 失敗也有）；並把候選對（lead_id, target）連同那一格的敘事摘錄或條件原文
交給同一次 LLM 呼叫，請它對每一對寫一句「可能怎麼影響」——**只標旗、不判定**：apply 只收候選集內的對、quote 必須是那則 lead
原文的逐字片段（L18），每日上限 `IMPACT_CAP` 對、截掉的照數。使用者 2026-10-20 同意摘要 LLM 讀敘事各格摘錄（只限這一步）；
仍不讀持股、Sheet、NAV。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "library" / "private" / "heartbeat"
BATCH_SCHEMA = "digest-batch-v1"
DIGEST_SCHEMA = "daily-digest-v1"
#: 兩段的封閉字彙與每段最多幾句（多的照數、不收）。
IMPACT_CAP = 15
IMPACT_SENTENCE_CHARS = 80
IMPACT_EXCERPT_CHARS = 200
IMPACT_VERDICTS = frozenset({"may_touch", "unrelated", "unclear"})
IMPACT_DROP_REASONS: Mapping[str, str] = {
    "invalid": "欄位不合法、verdict 不在字彙裡、或同一對重複",
    "unknown_pair": "這一對不在程式給的候選裡（LLM 不得自己發明連結，L15）",
    "quote_not_verbatim": "quote 不是那則 lead 原文的逐字片段（L18）",
    "too_long": "說明超過字數上限",
}
SECTIONS: Mapping[str, str] = {"leads": "lead 抓到什麼", "events": "市場大事"}
SECTION_CAPS: Mapping[str, int] = {"leads": 4, "events": 3}
MAX_TEXT_CHARS = 160
#: 一輪最多給 LLM 幾則 lead、每則摘錄多長（daily 的 harvest 一天一百則上下；超過的照數、列在批次檔裡）。
MAX_LEADS = 150
EXCERPT_CHARS = 240
#: 「今天這一輪」的窗：**從上一次心跳起算**（`window_start`）；沒有上一份快照才退回往回 26 小時。
#: ⚠ 2026-10-22：固定 26 小時每天都把前一天 05:30 那一輪包進來（daily 06:24 組短版，往回 26 小時是前一天 04:24）——
#: 10-21 重算 48 則、10-22 重算 41 則，TL;DR 有一整條重講昨天的新聞。
WINDOW_HOURS = 26
#: 上一份快照比現在早超過這麼多小時（例：daily 停了幾天）就不信它，退回 26 小時——不讓窗無限張開。
WINDOW_MAX_HOURS = 72
SNAPSHOT_DIR = OUT_DIR / "snapshots"


def window_start(now: datetime, *, snapshot_dir: Path | None = None) -> datetime:
    """「新進」窗的起點：上一份心跳快照（日期早於今天）的 `generated_at`——上一輪組短版的那一刻。
    讀不到、或早於 `WINDOW_MAX_HOURS`，退回 `now − WINDOW_HOURS`。"""
    fallback = now - timedelta(hours=WINDOW_HOURS)
    directory = snapshot_dir or SNAPSHOT_DIR
    today = now.astimezone().date().isoformat()
    try:
        names = sorted(p.stem for p in directory.glob("*.json") if len(p.stem) == 10 and p.stem < today)
        if not names:
            return fallback
        stamp = json.loads((directory / f"{names[-1]}.json").read_text(encoding="utf-8")).get("generated_at")
        start = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (OSError, ValueError, TypeError):
        return fallback
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if start >= now or now - start > timedelta(hours=WINDOW_MAX_HOURS):
        return fallback
    return start
DROP_REASONS: Mapping[str, str] = {
    "invalid": "欄位不合法（段別、文字或引用是空的）",
    "unknown_ref": "引用的 lead id 不在這一輪的資料裡",
    "too_long": f"超過 {MAX_TEXT_CHARS} 字",
    "over_cap": "超過這一段的句數上限",
}


#: 只會出現在簡體的常用字（繁體不用這些字形）。用來**數**、不用來丟句子：AGENTS 工作語言是繁體，退化要自己出現（L14），
#: 但為了字形把一句有根據的話丟掉不划算。字表刻意只收繁簡不同形、繁體也不借用的字（例：不收「准」「台」「后」「里」）。
SIMPLIFIED_ONLY = frozenset("们这为说时会对发过还进经个么样关开动设计实现场电认识问题应该业务产资费长东车门马龙书买卖"
                            "观视记让论读贵贸运营条举报战组织总结构线级绩济专转换层质证据访标确试验紧价钟储测订单览处"
                            "侧扩厂兴图团国际币汇银钱谁难稳续")


def simplified_count(text: str) -> int:
    return sum(1 for ch in str(text or "") if ch in SIMPLIFIED_ONLY)


def _stamp(value: Any) -> datetime | None:
    try:
        moment = datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _one_line(text: Any, limit: int) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= limit else flat[:limit] + "…"


#: 外部抓進來的 lead 一定帶 `source_class`（harvest 與雷達寫 primary／secondary）；研究 session 自己登記的研究題（拆層、
#: 指定研究、走圖……）沒有——用這個結構化欄位分，不用來源前綴清單（清單會腐壞）。
EXTERNAL_CLASSES: frozenset[str] = frozenset({"primary", "secondary"})


def is_external(lead: Mapping[str, Any]) -> bool:
    """「lead 抓到的」＝外面來的（2026-10-07 第一輪試跑：①有兩句在講我們自己登記的研究題，那不是今天抓到的新東西）。"""
    return str(lead.get("source_class") or "") in EXTERNAL_CLASSES


def select_leads(store: Mapping[str, Any], *, now: datetime, hours: int = WINDOW_HOURS,
                 since: datetime | None = None) -> list[Mapping[str, Any]]:
    """這一輪的 lead：窗內**新進**的，加上窗內**剛分流**的（分流結果是今天做了什麼的一部分）。依首見時間新到舊。
    `since`：窗的起點（正式路徑給 `window_start(now)`）；沒給才用 `now − hours`。"""
    since = since if since is not None else now - timedelta(hours=hours)
    picked = []
    for lead in (store.get("leads") or {}).values():
        seen = _stamp(lead.get("first_seen"))
        decided = _stamp((lead.get("triage") or {}).get("decided_at"))
        if (seen and seen >= since) or (decided and decided >= since):
            picked.append(lead)
    picked.sort(key=lambda l: (str(l.get("first_seen") or ""), str(l.get("lead_id"))), reverse=True)
    return picked


def _lead_row(lead: Mapping[str, Any]) -> dict[str, Any]:
    triage = lead.get("triage") or {}
    refs = lead.get("refs") or {}
    row: dict[str, Any] = {
        "lead_id": str(lead.get("lead_id")),
        "source": str(lead.get("source") or ""),
        "status": str(lead.get("status") or ""),
        "title": _one_line(lead.get("title"), 160),
        "excerpt": _one_line(lead.get("raw_text"), EXCERPT_CHARS),
        "published_at": lead.get("published_at"),
    }
    if triage.get("decision"):
        row["triage"] = {"decision": triage.get("decision"), "reason": _one_line(triage.get("reason"), 140)}
    if refs.get("radar_fact"):
        row["radar"] = {"scope": refs.get("radar_scope"), "fact": refs.get("radar_fact"), "why": refs.get("radar_why")}
    return row


def _norm(text: Any) -> str:
    return " ".join(str(text or "").split())


def impact_bundle(leads_rows: Sequence[Mapping[str, Any]], radar_ids: set[str], ctx: Any, *,
                  eligible: set[str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """(對照列, 給 LLM 的候選對, 截掉的對數)。候選的次序是固定規則、不是分數：雷達收下的先；同一群裡每則輪流取
    （每則先給它的第一對、再第二對）；每則自己的次序是反證 → 加碼條件 → 公司本身 → 某一格具名 → 只靠騎的讀圖；
    同級照 lead 原本的次序。target：watch_id，或 `<ticker>#<格>`（附那一格摘錄）。
    對照列涵蓋全部外部 lead；候選只給 `eligible`（這一輪真的交給 LLM 的 lead——沒給原文就沒得逐字引用）。"""
    from engine_b import impact as im

    slot_text = {(b.ticker, s.key): _one_line(s.text, IMPACT_EXCERPT_CHARS) for b in ctx.briefs for s in b.slots or ()}
    first_slot = {b.ticker: (b.slots[0].key if b.slots else None) for b in ctx.briefs}
    rows: list[dict[str, Any]] = []
    pairs: list[tuple[tuple[int, int, int, int], dict[str, Any]]] = []
    for order, lead in enumerate(leads_rows):
        if not is_external(lead):
            continue
        row = im.impact(lead, ctx)
        rows.append(row)
        lead_id = str(lead.get("lead_id"))
        if eligible is not None and lead_id not in eligible:
            continue
        own: list[tuple[int, dict[str, Any]]] = []
        for w in row["watches"]:
            own.append((0 if w["role"] == "反證" else 1,
                        {"lead_id": lead_id, "target": w["watch_id"], "kind": f"在盯條件（{w['role']}）",
                         "text": _one_line(w["condition"], 300)}))
        for ticker, links in row["narratives"].items():
            slots = [x.split("<", 1)[0][len("slot:"):] for x in links if x.startswith("slot:")]
            rank = 2 if "own" in links else 3 if slots else 4
            key = slots[0] if slots else ("our_bet" if (ticker, "our_bet") in slot_text else first_slot.get(ticker))
            if key is None:
                continue
            own.append((rank, {"lead_id": lead_id, "target": f"{ticker}#{key}", "kind": "敘事的一格",
                               "text": slot_text.get((ticker, key), "")}))
        # 每則輪流取：先每則的第一對、再第二對（10-21 試跑：一則雷達新聞碰到 8 條反證，把 15 對吃掉一半）
        own.sort(key=lambda p: p[0])
        radar = 0 if lead_id in radar_ids else 1
        pairs.extend(((radar, turn, rank, order), pair) for turn, (rank, pair) in enumerate(own))
    pairs.sort(key=lambda p: p[0])
    candidates = [p[1] for p in pairs[:IMPACT_CAP]]
    return rows, candidates, max(len(pairs) - IMPACT_CAP, 0)


def build_request(leads_rows: Sequence[Mapping[str, Any]], radar_receipt: Mapping[str, Any] | None, *,
                  today: date, impact_candidates: Sequence[Mapping[str, Any]] = (),
                  impact_truncated: int = 0) -> dict[str, Any]:
    """LLM 要的那一份資料。**沒有任何持股、部位、私人路徑的欄位**——只有外部 lead 的公開內容與雷達收下的新聞；
    我們自己登記的研究題只計數、不給 LLM（它們不是今天抓到的）。"""
    external = [lead for lead in leads_rows if is_external(lead)]
    rows = [_lead_row(lead) for lead in external[:MAX_LEADS]]
    radar_rows = []
    for item in (radar_receipt or {}).get("accepted") or ():
        radar_rows.append({"lead_id": item.get("lead_id"), "scope": item.get("scope"), "title": item.get("title"),
                           "fact": item.get("fact"), "why": item.get("why"), "publisher": item.get("publisher")})
    return {"today": today.isoformat(), "sections": dict(SECTIONS), "section_caps": dict(SECTION_CAPS),
            "max_text_chars": MAX_TEXT_CHARS, "leads": rows, "radar": radar_rows,
            "leads_total": len(external), "leads_given": len(rows), "internal_total": len(leads_rows) - len(external),
            "impact_candidates": [dict(c) for c in impact_candidates], "impact_cap": IMPACT_CAP,
            "impact_truncated": int(impact_truncated), "impact_sentence_chars": IMPACT_SENTENCE_CHARS}


IMPACT_SCHEMA = "lead-impact-v1"


def impact_path(day: date, *, out_dir: Path = OUT_DIR) -> Path:
    return out_dir / f"impact_{day.isoformat()}.json"


def load_impact(day: date, *, out_dir: Path = OUT_DIR) -> dict[str, Any] | None:
    """短版與心跳讀它；沒有檔或讀不懂回 None（呼叫端要說「今天沒有對照」，不是印空白）。"""
    path = impact_path(day, out_dir=out_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) and payload.get("schema") == IMPACT_SCHEMA else None


def impact_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {"leads": len(rows), "narratives": sum(bool(r.get("narratives")) for r in rows),
            "readings": sum(bool(r.get("readings")) for r in rows), "watches": sum(bool(r.get("watches")) for r in rows),
            "hub_only": sum(r.get("absence_kind") == "hub_only" for r in rows),
            "untouched": sum(r.get("absence_kind") in ("untouched", "no_entities") for r in rows),
            "language_gap": sum(bool(r.get("language_gap")) for r in rows)}


def prepare(run_id: str, out: Path, *, now: datetime | None = None, store: Mapping[str, Any] | None = None,
            receipt_dir: Path = OUT_DIR, impact_context: Any = None) -> dict[str, Any]:
    """`impact_context`：載入對照 Context 的函式（預設 `engine_b.impact.load_context`；測試注入）。對照載不起來不阻斷摘要——
    批次照寫、候選為空，對照檔記下錯誤（失敗要說出來，L13）。"""
    from engine_b import leads

    now = now or datetime.now(timezone.utc)
    today = now.astimezone().date()
    store = store if store is not None else leads.load()
    picked = select_leads(store, now=now, since=window_start(now))
    receipt_path = receipt_dir / f"radar_{today.isoformat()}.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else None
    radar_ids = {str(a.get("lead_id")) for a in (receipt or {}).get("accepted") or () if a.get("lead_id")}
    given = [lead for lead in picked if is_external(lead)][:MAX_LEADS]
    eligible = {str(lead.get("lead_id")) for lead in given} | radar_ids
    rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    truncated, impact_error = 0, None
    try:
        if impact_context is None:
            from engine_b.impact import load_context as impact_context
        ctx = impact_context()
        rows, candidates, truncated = impact_bundle(picked, radar_ids, ctx, eligible=eligible)
    except Exception as exc:  # noqa: BLE001 — 對照壞了摘要照跑；錯誤寫進對照檔，心跳與短版會印
        impact_error = f"{type(exc).__name__}: {_one_line(exc, 160)}"
    request = build_request(picked, receipt, today=today, impact_candidates=candidates, impact_truncated=truncated)
    # 一則都沒有就給空批次——daily 的 LLM 步驟遇到空批次不呼叫模型，照樣寫空結果（沒事與壞了不同形，L13）
    envelope = {"schema": BATCH_SCHEMA, "run_id": run_id, "run_date": today.isoformat(),
                "requests": [request] if (request["leads"] or request["radar"]) else []}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = impact_counts(rows)
    impact_doc = {"schema": IMPACT_SCHEMA, "run_id": run_id, "date": today.isoformat(), "error": impact_error,
                  "counts": counts, "candidates": len(candidates), "truncated": truncated, "rows": rows,
                  "note": "確定性對照（名字對到哪裡），不是判定；判定只在互動 session。"}
    receipt_dir.mkdir(parents=True, exist_ok=True)
    impact_path(today, out_dir=receipt_dir).write_text(json.dumps(impact_doc, ensure_ascii=False, indent=1) + "\n",
                                                       encoding="utf-8")
    return {"leads_total": request["leads_total"], "leads_given": request["leads_given"],
            "internal_total": request["internal_total"], "radar_items": len(request["radar"]),
            "radar_receipt": receipt is not None, "impact_touched": counts["leads"] - counts["untouched"] - counts["hub_only"],
            "impact_candidates": len(candidates), "impact_truncated": truncated, "impact_error": impact_error}


def _given_text(request: Mapping[str, Any]) -> dict[str, str]:
    """lead_id → 這一輪交給 LLM 的原文（標題、摘錄、雷達的一句事實），空白正規化——quote 只能從這裡逐字取（L18）。"""
    out: dict[str, list[str]] = {}
    for r in request.get("leads") or ():
        out.setdefault(str(r.get("lead_id")), []).extend(
            [str(r.get("title") or ""), str(r.get("excerpt") or ""), str((r.get("radar") or {}).get("fact") or "")])
    for r in request.get("radar") or ():
        out.setdefault(str(r.get("lead_id")), []).extend([str(r.get("title") or ""), str(r.get("fact") or "")])
    return {lid: "\n".join(_norm(p) for p in parts if p) for lid, parts in out.items()}


def _apply_impacts(items: Sequence[Any], request: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """C2 的那一句：只收程式給的候選對、quote 逐字、說明不超長、verdict 在字彙裡；不合的照數（INV-3）。同一對只收第一句。"""
    candidates = {(str(c.get("lead_id")), str(c.get("target"))): c for c in request.get("impact_candidates") or ()}
    texts = _given_text(request)
    counts = {"candidates": len(candidates), "truncated": int(request.get("impact_truncated") or 0), "proposed": 0,
              "kept": 0, **{k: 0 for k in IMPACT_DROP_REASONS}}
    kept: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        counts["proposed"] += 1
        if not isinstance(item, Mapping):
            counts["invalid"] += 1
            continue
        pair = (str(item.get("lead_id") or ""), str(item.get("target") or ""))
        verdict, quote, sentence = str(item.get("verdict") or ""), _norm(item.get("quote")), _norm(item.get("sentence"))
        if verdict not in IMPACT_VERDICTS or not quote or not sentence or pair in seen:
            counts["invalid"] += 1
            continue
        if pair not in candidates:
            counts["unknown_pair"] += 1
            continue
        if quote not in texts.get(pair[0], ""):
            counts["quote_not_verbatim"] += 1
            continue
        if len(sentence) > IMPACT_SENTENCE_CHARS:
            counts["too_long"] += 1
            continue
        seen.add(pair)
        kept.append({"lead_id": pair[0], "target": pair[1], "kind": candidates[pair].get("kind"), "verdict": verdict,
                     "quote": quote, "sentence": sentence})
        counts["kept"] += 1
    return kept, counts


def apply(result_path: Path, batch_path: Path, run_id: str, *, out_dir: Path = OUT_DIR,
          today: date | None = None) -> dict[str, Any]:
    """驗證後寫 `digest_<日期>.json`，回傳 `{summary, rejected}`（daily 的套用步驟把最後一行 JSON 收進執行紀錄）。"""
    result = json.loads(result_path.read_text(encoding="utf-8"))
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    if result.get("run_id") != run_id or batch.get("run_id") != run_id:
        raise ValueError("結果檔或批次檔的 run_id 不是這一輪的——不套用舊檔")
    request = (batch.get("requests") or [{}])[0]
    known = {str(r.get("lead_id")) for r in request.get("leads") or ()}
    known |= {str(r.get("lead_id")) for r in request.get("radar") or () if r.get("lead_id")}
    kept: dict[str, list[dict[str, Any]]] = {key: [] for key in SECTIONS}
    rejected: list[dict[str, Any]] = []
    counts = {"proposed": 0, "kept": 0, "simplified_suspect": 0, **{k: 0 for k in DROP_REASONS}}
    for item in result.get("bullets") or ():
        counts["proposed"] += 1
        section = str(item.get("section") or "") if isinstance(item, Mapping) else ""
        text = " ".join(str(item.get("text") or "").split()) if isinstance(item, Mapping) else ""
        refs = [str(r) for r in (item.get("lead_ids") or ()) if str(r).strip()] if isinstance(item, Mapping) else []

        def drop(reason: str) -> None:
            counts[reason] += 1
            rejected.append({"section": section or None, "text": text[:80] or None, "reason": reason,
                             "detail": DROP_REASONS[reason]})

        if section not in SECTIONS or not text or not refs:
            drop("invalid")
            continue
        if any(r not in known for r in refs):
            drop("unknown_ref")
            continue
        if len(text) > MAX_TEXT_CHARS:
            drop("too_long")
            continue
        if len(kept[section]) >= SECTION_CAPS[section]:
            drop("over_cap")
            continue
        kept[section].append({"text": text, "lead_ids": refs})
        counts["kept"] += 1
        # 寫成簡體的照數（不丟——有根據的一句比字形重要；計數讓「又退回簡體」自己出現）
        counts["simplified_suspect"] = counts.get("simplified_suspect", 0) + int(simplified_count(text) >= 2)
    impacts, impact_counts_ = _apply_impacts(result.get("impacts") or (), request)
    today = today or datetime.now().astimezone().date()
    summary = {**counts, "rejected": len(rejected), "leads_total": request.get("leads_total", 0),
               "leads_given": request.get("leads_given", 0), "radar_items": len(request.get("radar") or ()),
               "no_material_change": bool(result.get("no_material_change")), "impact": impact_counts_}
    digest = {"schema": DIGEST_SCHEMA, "run_id": run_id, "date": today.isoformat(), "sections": dict(SECTIONS),
              **kept, "impacts": impacts, "summary": summary, "rejected": rejected,
              "sessions": list(result.get("sessions") or ()),
              "note": "兩段 TL;DR 與「可能怎麼影響」都是 LLM 寫的提議（每句都指得回當天的 lead），不是判定；判定只在互動 session。"}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"digest_{today.isoformat()}.json").write_text(
        json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"summary": summary, "rejected": rejected}


def load_digest(day: date, *, out_dir: Path = OUT_DIR) -> dict[str, Any] | None:
    """心跳讀它：沒有檔（LLM 沒跑或失敗）回 None——呼叫端要說「今天沒產生」，不是印空白。"""
    path = out_dir / f"digest_{day.isoformat()}.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) and payload.get("schema") == DIGEST_SCHEMA else None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m engine_b.digest")
    sub = parser.add_subparsers(dest="command", required=True)
    p_prep = sub.add_parser("prepare", help="組每日摘要的批次檔（今天的 lead 與雷達收下的新聞；不讀持股）")
    p_prep.add_argument("--run-id", required=True)
    p_prep.add_argument("--out", type=Path, required=True)
    p_apply = sub.add_parser("apply", help="驗證 LLM 寫的兩段 TL;DR 後寫 digest_<日期>.json")
    p_apply.add_argument("--file", type=Path, required=True)
    p_apply.add_argument("--batch", type=Path, required=True)
    p_apply.add_argument("--run-id", required=True)
    p_apply.add_argument("--out-dir", type=Path, default=OUT_DIR, help="試跑時指到暫存目錄")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        print(json.dumps({"summary": prepare(args.run_id, args.out)}, ensure_ascii=False))
        return 0
    print(json.dumps(apply(args.file, args.batch, args.run_id, out_dir=args.out_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["BATCH_SCHEMA", "DIGEST_SCHEMA", "DROP_REASONS", "EXTERNAL_CLASSES", "IMPACT_CAP", "IMPACT_DROP_REASONS", "IMPACT_SCHEMA",
           "IMPACT_VERDICTS", "SECTIONS", "SECTION_CAPS", "apply", "build_request", "impact_bundle", "impact_counts", "impact_path",
           "is_external", "load_digest", "load_impact", "main", "prepare", "select_leads"]
