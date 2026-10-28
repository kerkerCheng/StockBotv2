"""Discord 那一則（2026-10-07 使用者指示）。

使用者原話：「每日心跳，太雜了，而且我想看到你每天 websearch 的結果跟你做了什麼，比較有實感……Lead 抓了哪些 TL;DR、
Websearch 大事件 TL;DR、幾件事待我決定、健康度等等」。

五塊、固定順序、**每塊一定出現**（沒東西也說沒東西——INV-3）：

① lead 抓了什麼：⑪c LLM 寫的 TL;DR（每句都指得回今天的 lead）；沒產生時退回程式組的來源計數與分流 go 的標題。
   上面是**我們做了哪些處理**（同日使用者：「我們做了哪些處理的數字也要印」）：分類幾則（go／no-go、LLM／互動）、
   還沒分類（其中無內文）、研究到終局幾條（入圖包／已入圖／停放；lead 的轉移紀錄 10-07 起才有）、待深挖。
② 市場大事：雷達收據收下的每一則（事實首句 → 現在的處置）；收據不在才退回 LLM 摘要。
③ 待你決定：pq2 要你決定的每一條，一條一塊（主詞、go 是什麼、不含什麼、圖會變什麼、建議）。
③b 等你提供的文件：向你要文件的每一條，**獨立一區、批次 go 不收**——提供文件才算 go（同日使用者：「隔離一區讓我知道
   也不要讓我直接 go 提供文件才算 go」；名單只有 `todo.document_requests()` 一份）。
④ 狀態與健康度：**每天都印**的基本狀態（daily 步數與出錯的步驟、候選五格檔數與最老滯留、等回落逐檔、watch 今日醒／
   到期／標旗、反證在盯與未盯、無到期的等待——2026-10-07 使用者：「daily 心跳基本重要的 status 還是要印」）。
⑤ 下一次研究要做的：常駐計數器（`engine_b.todo_ledger`）——非 0 的逐格，0 的格名字印在小字裡（L14：每格都出現）。
最後一則：③ 的建議批次指令，**單獨一則、inline code**——手機上一點就複製（2026-10-28 使用者：「最後給我一次複製的
指令可以用回以前的格式 那樣我一次點就可以複製」）。

排版（2026-10-28 使用者核可的 Discord 測試版）：每段 `### ` 標題（Discord 一段一則，`notifications/publisher.py` 依
`### ` 與單獨一行的 inline code 切訊息）、說明用 `-# ` 小字、一事一項、不用表格。開頭是心跳摘要行換排版
（`## 10-28 Daily｜球在你 5｜⚠ 2`＝討論串標題＋紅旗小字），旗一個不增不減。

完整五段心跳照樣每天寫進 `library/private/heartbeat/heartbeat_<日期>.md`（互動 session 讀它查細節）；APP「每日」頁
顯示的是這一則。這裡的數字全部來自心跳同一份快照、同一批函式與執行紀錄，不另算一份（L16）；LLM 寫的句子標明是提議，
判定只在互動 session。
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
HEARTBEAT_DIR = ROOT / "library" / "private" / "heartbeat"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engine_b.todo_ledger import LEDGER as _TODO_LEDGER  # noqa: E402

#: lead 來源前綴 → 人話（沒列到的照原字）。只用來分組計數，不判斷任何事。
SOURCE_LABELS: Mapping[str, str] = {
    "x": "X 帳號", "edgar": "SEC 申報", "mops": "台股公告", "mfn": "北歐公告", "yahoo": "Yahoo 新聞",
    "sivers": "Sivers 新聞", "official": "公司官網", "web_radar": "外部雷達", "decompose": "拆層研究題",
    "directed": "指定研究題", "event_watch": "等待醒來", "theme_scan": "題材掃描", "graph_walk": "走圖",
    "user_shared": "你給的",
}
RADAR_SCOPE_WORDS: Mapping[str, str] = {"market": "市場", "theme": "主題", "watch": "在盯"}
TITLE_CHARS = 70


def _short(text: Any, limit: int = TITLE_CHARS) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= limit else flat[:limit] + "…"


#: `_clip` 的斷點：標點之後（或左括號之前）優先，其次空白；都找不到才硬切（2026-10-28：雷達那則被切成「原下限為 1,300…」、
#: 建議理由被切成「tech:ai_context_m…」）。
_CLIP_AFTER = "，；。、）)"
_CLIP_BEFORE = "（("


def _clip(text: Any, limit: int) -> str:
    """縮成 `limit` 字以內：優先斷在標點（不切在詞或數字中間），其次空白，找不到合適的才硬切；有縮就補「…」。"""
    flat = " ".join(str(text or "").split())
    if len(flat) <= limit:
        return flat
    head = flat[:limit]
    marks = [i + 1 for i, ch in enumerate(head) if ch in _CLIP_AFTER] + [i for i, ch in enumerate(head) if ch in _CLIP_BEFORE]
    spaces = [i for i, ch in enumerate(head) if ch == " "]
    cut = max((m for m in marks if m >= limit * 0.5), default=None)
    if cut is None:
        cut = max((s for s in spaces if s >= limit * 0.6), default=limit)
    return head[:cut].rstrip("，；。、 ") + "…"


def _source_family(source: Any) -> str:
    prefix = str(source or "").split(":", 1)[0]
    return SOURCE_LABELS.get(prefix, prefix or "（沒有來源）")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 公司短名（名冊是唯一來源；不從 ID 或代號猜名字——INV-1）
# ---------------------------------------------------------------------------

_REGISTRY: Any = None
_CORP_SUFFIX_RE = re.compile(r",?\s+(?:Inc\.?|Incorporated|Corporation|Corp\.?|Co\.?,?\s*Ltd\.?|Ltd\.?|Limited|plc|PLC"
                             r"|AB|ASA|AG|SE|S\.A\.|N\.V\.|Holdings?)$")
_CJK_RE = re.compile(r"[一-鿿]")


def _registry() -> Any:
    global _REGISTRY
    if _REGISTRY is None:
        try:
            from identity.registry import get_registry

            _REGISTRY = get_registry()
        except Exception:  # noqa: BLE001 — 名冊讀不到就只印代號，不帶走整塊
            _REGISTRY = False
    return _REGISTRY or None


def company_label(*, company_id: str | None = None, ticker: str | None = None) -> str:
    """面向人的「短名 代號」（「聯亞 3081」「AXT AXTI」）：有中文別名用最短的中文別名，否則用名冊的 `display_name`
    去掉公司型態尾綴。名冊裡沒有就只印代號——不從 ID 猜名字（`co:iqe` →「Iqe」是編出來的）。"""
    reg = _registry()
    cid = company_id
    if cid is None and ticker and reg is not None:
        cid = reg.company_id_for_ticker(str(ticker))
    company = reg.company(cid) if (reg is not None and cid) else None
    if not ticker and company is not None:
        ticker = company.research_ticker
    code = re.sub(r"\.(TW|TWO)$", "", str(ticker or ""))
    name = None
    if company is not None:
        cjk = sorted((a for a in company.name_aliases if _CJK_RE.search(a) and len(a) >= 2), key=len)
        name = cjk[0] if cjk else None
        if name is None and company.display_name:
            name = str(company.display_name)
            while (stripped := _CORP_SUFFIX_RE.sub("", name)) != name:
                name = stripped
    if name and code and name.replace(" ", "").upper() != code.upper():
        return f"{name} {code}"
    return name or code or str(cid or "?")


# ---------------------------------------------------------------------------
# 開頭（＝討論串標題）
# ---------------------------------------------------------------------------

def brief_header(summary: str) -> list[str]:
    """短版開頭：心跳摘要行（`Daily 2026-10-28｜球在你 5｜…｜⚠ 旗…`）換排版成 `## 10-28 Daily｜球在你 5｜⚠ 2`
    ＋一行紅旗小字。**旗一個不增不減**——只換排版（摘要行由 `heartbeat.summary_line` 組，L16）。
    Discord 討論串標題取這一行（`notifications.publisher._forum_thread_name`）。"""
    parts = [p.strip() for p in str(summary or "").strip().split("｜") if p.strip()]
    if not parts:
        return ["## Daily"]
    first = parts[0]
    dated = re.fullmatch(r"Daily (\d{4})-(\d{2}-\d{2})", first)
    if dated:
        first = f"{dated.group(2)} Daily"
    head = [first, *(p for p in parts[1:] if not p.startswith("⚠"))]
    flags = [p.removeprefix("⚠").strip() for p in parts[1:] if p.startswith("⚠")]
    lines = ["## " + "｜".join(head) + (f"｜⚠ {len(flags)}" if flags else "")]
    if flags:
        lines.append("-# ⚠ " + "｜".join(flags))
    return lines


# ---------------------------------------------------------------------------
# ① lead
# ---------------------------------------------------------------------------

#: 研究到終局＝轉到這三個狀態（入圖包／已入圖／停放）。
RESEARCH_TERMINAL_STATES: tuple[str, ...] = ("action_prepared", "applied", "parked")


def _stamp(raw: Any) -> datetime | None:
    try:
        moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def processing_lines(store: Mapping[str, Any], *, now: datetime, hours: int | None = None,
                     since: datetime | None = None, held: int | None = None) -> list[str]:
    """① 的處理數字，一事一行（2026-10-07 使用者：「Lead 抓了什麼 我們做了哪些處理的數字也要印」）。

    同一個時間窗（`engine_b.digest.WINDOW_HOURS`）：分類（`triage.decided_at` 在窗內；go／no-go、LLM／互動分開）、
    研究到終局（`transitions` 在窗內轉到入圖包／已入圖／停放——10-07 起才有轉移紀錄）、還沒分類（其中無內文——
    failure log #105：daily 不送分類、要互動 session 讀全文；10-28 使用者在短版找不到這個數）與待深挖的總數。
    `held` 不給就就地盤點（`engine_b.lead_text.held_pending`，不連網）。"""
    from engine_b.digest import WINDOW_HOURS

    cutoff = since if since is not None else now - timedelta(hours=hours or WINDOW_HOURS)
    lead_map = {str(k): v for k, v in (store.get("leads") or {}).items() if isinstance(v, Mapping)}
    leads = list(lead_map.values())
    go = no_go = by_llm = by_hand = by_rule = 0
    finished = {state: 0 for state in RESEARCH_TERMINAL_STATES}
    for lead in leads:
        triage = lead.get("triage") or {}
        decided = _stamp(triage.get("decided_at"))
        if decided is not None and decided >= cutoff:
            go += triage.get("decision") == "go"
            no_go += triage.get("decision") == "no_go"
            # 誰判的：`decided_by` 是唯一記錄（claude-p:<session>＝分類層 LLM；harvest:…＝機械篩選）；
            # 互動判的看 `classified_by`（interactive:…）。三格分開——機械篩選不算進 LLM（L12）。
            decided_by = str(triage.get("decided_by") or "")
            classified_by = str((triage.get("classification") or {}).get("classified_by") or "")
            if decided_by.startswith("claude-p"):
                by_llm += 1
            elif classified_by.startswith("interactive"):
                by_hand += 1
            else:
                by_rule += 1
        for move in lead.get("transitions") or ():
            moment = _stamp((move or {}).get("at"))
            if moment is not None and moment >= cutoff and move.get("to") in finished:
                finished[move["to"]] += 1
    pending = sum(1 for lead in leads if lead.get("status") == "pending")
    queued = sum(1 for lead in leads if lead.get("status") == "triaged_go")
    held_text = None
    if held is None and pending:
        try:
            from engine_b.lead_text import held_pending

            held = len(held_pending(lead_map))
        except Exception as exc:  # noqa: BLE001 — 盤點不了就說，不印 0（INV-3）
            held_text = f"（其中無內文：盤點失敗 {type(exc).__name__}）"
    if held_text is None:
        held_text = (f"（其中**無內文 {held}**：daily 不送分類，互動 session 讀全文後分類）" if held
                     else "（其中無內文 0）")
    return [f"- 分類 {go + no_go}：go {go}｜no-go {no_go}（LLM {by_llm}／互動 {by_hand}／機械或舊資料 {by_rule}）",
            f"- 還沒分類 {pending}{held_text}",
            f"- 研究到終局 {sum(finished.values())}：入圖包 {finished['action_prepared']}｜已入圖 {finished['applied']}"
            f"｜停放 {finished['parked']}",
            f"- 待深挖 {queued}"]


def impact_total_line(impact: Mapping[str, Any] | None, digest: Mapping[str, Any] | None) -> str:
    """影響對照的一行總數（雷達精進 C2）：今天外部 lead 碰到我們幾則（確定性對照）＋ LLM 的「可能怎麼影響」收了幾句、丟幾句。
    完整表在 `impact_<日期>.json`；**只印在完整心跳**（2026-10-28 起短版不印這一行）。沒有對照檔與對照算壞要說出來，不印 0（INV-3）。"""
    if impact is None:
        return "- 對照：今天沒有對照檔（⑪b 沒跑或讀不到）"
    if impact.get("error"):
        return f"- 對照：沒算出來（{_short(impact.get('error'), 60)}）——摘要照跑、沒有「可能怎麼影響」"
    c = impact.get("counts") or {}
    line = (f"- 對照：外部 {c.get('leads', 0)} 則裡碰到敘事 {c.get('narratives', 0)}、讀圖 {c.get('readings', 0)}、"
            f"在盯條件 {c.get('watches', 0)} 則；只經樞紐 {c.get('hub_only', 0)}、沒碰到 {c.get('untouched', 0)}")
    if c.get("language_gap"):
        line += f"、中文比不到節點名 {c['language_gap']}"
    s = ((digest or {}).get("summary") or {}).get("impact")
    if s:
        dropped = sum(int(s.get(k) or 0) for k in ("invalid", "unknown_pair", "quote_not_verbatim", "too_long"))
        line += (f"｜LLM 提議 {s.get('kept', 0)} 句（候選 {s.get('candidates', 0)} 對"
                 + (f"、超過上限截掉 {s['truncated']}" if s.get("truncated") else "")
                 + (f"、丟 {dropped}" if dropped else "") + "）")
    elif digest is None:
        line += "｜LLM 提議：摘要今天沒產生"
    return line


def leads_block(*, digest: Mapping[str, Any] | None, todays: Sequence[Mapping[str, Any]], since: datetime,
                digest_problem: str | None, processing: Sequence[str] | None = None) -> list[str]:
    """① lead 抓了什麼。小字那一行永遠是程式數的（外面新進幾則、哪些來源；前幾天進來、這輪才分類的另計；
    我們自己登記的研究題另計、不摘要）；「今天的重點」是 LLM 的 TL;DR，沒有就退回分流 go 的標題。

    `todays` 是 `select_leads` 的窗（窗內首見 ∪ 窗內剛分類）；`since` 是窗的起點。2026-10-16：10-13 標題寫「新進 125」，
    其中 82 則是 10-10～10-12 積下來、那天才分類的——一個數字裝兩種意思（L12），所以首見在窗前的拆出來印。"""
    from engine_b.digest import is_external

    external = [lead for lead in todays if is_external(lead)]
    internal = len(todays) - len(external)
    fresh = [lead for lead in external if (seen := _stamp(lead.get("first_seen"))) is not None and seen >= since]
    backlog = len(external) - len(fresh)
    families = Counter(_source_family(lead.get("source")) for lead in fresh)
    sub = (f"-# 外面新進 {len(fresh)}"
           + (f"（{'、'.join(f'{name} {n}' for name, n in families.most_common())}）" if fresh else "")
           + (f"＋前幾天進來、這輪才分類 {backlog}" if backlog else "")
           + (f"＋我們自己登記的研究題 {internal}（不摘要）" if internal else ""))
    lines = ["### ① Lead 抓了什麼", sub, *(processing or ()), "", "**今天的重點**"]
    bullets = list((digest or {}).get("leads") or ())
    if bullets:
        lines.extend(f"- {b['text']}" for b in bullets)
        lines.append("-# 重點是 LLM 寫的摘要，每句指得回當天的 lead；判定只在互動 session")
        return lines
    went = [lead for lead in external if lead.get("status") == "triaged_go"]
    reason = digest_problem or "LLM 摘要今天沒產生"
    if not external:
        lines.append("- 這一輪外面沒有新進的 lead")
    elif went:
        lines.extend(f"- {_short(lead.get('title'))}" for lead in went[:3])
        lines.append(f"-# {reason}——改列分流判 go 的 {len(went)} 則" + ("（前 3 則）" if len(went) > 3 else ""))
    else:
        lines.append(f"- （{reason}；分流判 go 的 0 則）")
    return lines


# ---------------------------------------------------------------------------
# ② 市場大事
# ---------------------------------------------------------------------------

#: 雷達沒收的理由（`engine_b.radar` 收據的 reason 代碼 → 人話；認不得的照印原字）。
RADAR_REJECT_WORDS: Mapping[str, str] = {
    "duplicate": "lead 裡已經有這個網址", "over_cap": "超過每日上限", "url_not_in_search": "網址不在這一輪的搜尋結果裡",
    "invalid": "欄位不合法", "published_unparsed": "發布日讀不出來", "theme_unknown": "題材對不上",
    "relates_to_unknown": "在盯的條件對不上", "scope_unknown": "層別讀不懂",
}
#: 「可能是同一件事」：今天收下的標題與前幾天收下的標題，詞（英文）／兩字組（中日韓）重疊到這個比例就標出來——
#: 只標「可能」，不判定、不擋（同一件事換了網址會再被收一次：2026-10-08 LG 冷水機合約 10-07 收 PR Newswire、10-08 收 LG 官網）。
REPEAT_LOOKBACK_DAYS = 3
REPEAT_TITLE_OVERLAP = 0.5
_TITLE_STOPWORDS = frozenset({"a", "an", "and", "the", "to", "of", "in", "for", "on", "with", "by", "at", "as", "its", "is"})
#: ② 小字印「過去兩週每天收幾則」的回看天數（2026-10-28：雷達一天只收 1 則，使用者「這個我有點不太相信」——只拿今天的數
#: 看不出是不是異常）。只印不判：低於區間時多一個 ⚠，不擋任何東西。
RADAR_BASELINE_DAYS = 14


def _title_tokens(title: Any) -> set[str]:
    text = str(title or "").lower()
    words = {w for w in re.findall(r"[a-z0-9]+", text) if w not in _TITLE_STOPWORDS}
    cjk = re.sub(r"[^぀-ヿ一-鿿]", "", text)
    return words | {cjk[i:i + 2] for i in range(len(cjk) - 1)}


def _possible_repeat(item: Mapping[str, Any], recent: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    mine = _title_tokens(item.get("title"))
    best, best_ratio = None, 0.0
    for old in recent:
        theirs = _title_tokens(old.get("title"))
        if not mine or not theirs:
            continue
        ratio = len(mine & theirs) / len(mine | theirs)
        if ratio >= REPEAT_TITLE_OVERLAP and ratio > best_ratio:
            best, best_ratio = old, ratio
    return best


def recent_radar_accepted(heartbeat_dir: Path, today: date, *, days: int = REPEAT_LOOKBACK_DAYS) -> list[dict[str, Any]]:
    """前幾天雷達收據收下的那幾則（帶收據日期）；讀不到的那天就跳過（只拿來標「可能是同一件事」）。"""
    out: list[dict[str, Any]] = []
    for back in range(1, days + 1):
        day = today - timedelta(days=back)
        receipt = _read_json(heartbeat_dir / f"radar_{day.isoformat()}.json") or {}
        out.extend({**item, "_date": day.isoformat()} for item in receipt.get("accepted") or () if isinstance(item, Mapping))
    return out


def radar_baseline(heartbeat_dir: Path, today: date, *, days: int = RADAR_BASELINE_DAYS) -> tuple[int, int] | None:
    """前 `days` 天雷達收據每天收下幾則的 (最少, 最多)；一份都讀不到回 None（不編區間）。"""
    counts = []
    for back in range(1, days + 1):
        summary = (_read_json(heartbeat_dir / f"radar_{(today - timedelta(days=back)).isoformat()}.json") or {}).get("summary")
        if isinstance(summary, Mapping) and isinstance(summary.get("new"), int):
            counts.append(int(summary["new"]))
    return (min(counts), max(counts)) if counts else None


#: lead 現在的狀態 → 處置（固定幾個詞；2026-10-22）。完整心跳段 3 也用這一份。
LEAD_STATE_WORDS: Mapping[str, str] = {
    "triaged_go": "go", "triaged_no_go": "篩掉", "pending": "還沒分類", "researching": "研究中", "parked": "停放",
    "action_prepared": "入圖包等核准", "applied": "已入圖",
}
#: 短版改用 ⑤ 的格名（「go」在手機上讀不出下一步是什麼；10-28 使用者核可的排版寫「→ 待深挖」）。
SHORT_STATE_WORDS: Mapping[str, str] = {**LEAD_STATE_WORDS, "triaged_go": "待深挖"}


def _target_label(target: Any) -> str:
    """LLM 提議指的格（`代號#格` 或 watch id）→ 人看得懂的主詞（AGENTS：不得假設使用者能從內部 ID 還原主詞）。"""
    raw = str(target or "?").split("#", 1)[0]
    if raw.startswith("ew_"):
        return f"在盯條件 {raw}"
    return company_label(ticker=raw)


def radar_item_tail(row: Mapping[str, Any] | None, proposals: Sequence[Mapping[str, Any]], *,
                    impact_ran: bool = True) -> tuple[str, Counter]:
    """一則雷達新聞「LLM 看過的結果」（無關也算，不藏——2026-10-22：只印「碰到」看不到後來，就是使用者怕的
    「撈進來沒事」）。回（那一段字, 判定計數）。"""
    verdicts: Counter = Counter(str(p.get("verdict")) for p in proposals)
    kind = (row or {}).get("absence_kind")
    if proposals:
        may = [_target_label(p.get("target")) for p in proposals if p.get("verdict") == "may_touch"]
        bits = []
        if may:
            bits.append("可能碰到 " + "、".join(dict.fromkeys(may)))
        if verdicts.get("unclear"):
            bits.append(f"看不出 {verdicts['unclear']} 格")
        if verdicts.get("unrelated"):
            bits.append(f"無關 {verdicts['unrelated']} 格")
        return "LLM 提議：" + "；".join(bits) + ("；判定在研究時做" if may else ""), verdicts
    if kind == "hub_only":
        hubs = "／".join(str(h).removeprefix("co:") for h in (row or {}).get("hub_entities") or ())[:40]
        return f"只經 {hubs or '大樞紐'}（大樞紐，沒逐格對）", verdicts
    if not impact_ran:
        return "影響對照今天沒跑（不是沒碰到）", verdicts
    if kind == "untouched" or not row:
        return "沒碰到我們", verdicts
    return "碰到了，但 LLM 今天沒看（超過上限或摘要失敗）", verdicts


def events_block(*, digest: Mapping[str, Any] | None, receipt: Mapping[str, Any] | None,
                 digest_problem: str | None, radar_problem: str | None,
                 recent_accepted: Sequence[Mapping[str, Any]] = (),
                 lead_titles: Mapping[str, str] | None = None,
                 impact: Mapping[str, Any] | None = None,
                 lead_states: Mapping[str, str] | None = None,
                 baseline: tuple[int, int] | None = None) -> list[str]:
    """② 市場大事：**今天雷達收下的每一則都列**（事實首句 → 現在的處置，下一行小字是 LLM 看過的結果），沒收的附理由，
    跟前幾天收過的標題很像的標「可能是同一件事」。

    2026-10-08 使用者：「tldr 只有三則，但你說收四則……還是 tldr 就把收的都包含上去？如果沒收但想讓我知道的就再註明」。
    原本這裡印 LLM 摘要的「市場大事」——最多 3 句、取材是過去 26 小時的所有 lead，所以會漏掉今天收的、又夾進昨天收的。
    收據不在（雷達沒跑）才退回 LLM 摘要。2026-10-22 使用者：「可不可以短一點 讓我知道你有在做事就好 我怕的是撈進來然後
    什麼也沒發生」——「碰到」的逐項、LLM 原句、篩掉理由在完整心跳段 3。"""
    head = "### ② 市場大事"
    if receipt is None:
        lines = [head, f"-# ⚠ 外部雷達今天沒有收據：{radar_problem or '沒跑'}"]
        bullets = list((digest or {}).get("events") or ())
        if bullets:
            lines.extend(f"- {b['text']}" for b in bullets)
            lines.append("-# 改列 LLM 摘要的市場大事——取材是過去 26 小時的 lead，可能含前一天收的")
        else:
            lines.append("- 今天沒有收下任何一則")
        return lines
    summary = receipt.get("summary") or {}
    rejected = [r for r in receipt.get("rejected") or () if isinstance(r, Mapping)]
    accepted = [a for a in receipt.get("accepted") or () if isinstance(a, Mapping)]
    new = summary.get("new", 0)
    sub = (f"-# 雷達搜 {summary.get('searches', '?')} 次、收 {new} 則（市場 {summary.get('new_market', 0)}、"
           f"主題 {summary.get('new_theme', 0)}、在盯 {summary.get('new_watch', 0)}"
           + (f"；沒收 {len(rejected)}" if rejected else "") + "）")
    if baseline is not None:
        low, high = baseline
        span = f"{low}–{high}" if low != high else f"{low}"
        sub += ("｜⚠ " if isinstance(new, int) and new < low else "｜") + f"過去兩週每天收 {span} 則"
    lines = [head, sub]
    # 影響對照（雷達精進 C2）：確定性的「碰到」與 LLM 那一句都用 lead_id 對回這一則
    rows = {str(r.get("lead_id")): r for r in (impact or {}).get("rows") or () if isinstance(r, Mapping)}
    proposals: dict[str, list[Mapping[str, Any]]] = {}
    for p in (digest or {}).get("impacts") or ():
        if isinstance(p, Mapping):
            proposals.setdefault(str(p.get("lead_id")), []).append(p)
    impact_ran = impact is not None and not (impact or {}).get("error")
    for item in accepted:
        lead_id = str(item.get("lead_id") or "")
        status = (lead_states or {}).get(lead_id)
        tail, _verdicts = radar_item_tail(rows.get(lead_id), proposals.get(lead_id, ()), impact_ran=impact_ran)
        # 半形逗號夾在兩個數字之間是千分位，不是斷句（2026-10-28：「收窄為 1,350 億」被切成「收窄為 1」）
        first = re.split(r"[，。；;]|(?<!\d),|,(?!\d)",
                         str(item.get("fact") or item.get("title") or item.get("url") or ""), maxsplit=1)[0]
        line = f"- {_clip(first, 60)} → {SHORT_STATE_WORDS.get(str(status), str(status or 'lead 不在'))}"
        repeat = _possible_repeat(item, recent_accepted)
        if repeat is not None:
            line += f"（⚠ 可能跟 {str(repeat.get('_date', ''))[5:]} 收過的是同一件事）"
        lines.extend([line, f"-# {tail}"])
    if not accepted:
        lines.append("- 今天沒有收下任何一則")
    for item in rejected[:5]:
        why = RADAR_REJECT_WORDS.get(str(item.get("reason")), str(item.get("reason") or "?"))
        # 「已經有這個網址」那種：印那則既有 lead 的標題（收據只帶網址與 lead id）；讀不到就退回網址
        known = (lead_titles or {}).get(str(item.get("lead_id") or "")) or ""
        lines.append(f"-# 沒收：{_short(known or item.get('title') or item.get('url'), 80)}——{why}")
    return lines


# ---------------------------------------------------------------------------
# ③ 待你決定、③b 等你提供的文件
# ---------------------------------------------------------------------------

def _split_title(title: Any) -> tuple[str, str | None]:
    """編號標題 → (粗體主詞, 一行細節)：在第一個「：」切；主詞太長或沒有「：」就整句當主詞（縮到 60 字）。"""
    flat = " ".join(str(title or "").split())
    head, sep, rest = flat.partition("：")
    if sep and 0 < len(head) <= 50 and rest.strip():
        return head, rest.strip()
    return _clip(flat, 60), None


_IMPACT_ASIDE_RE = re.compile(r"（另[^）]*）")
_IMPACT_SOURCE_RE = re.compile(r"([^、]+?)（tier (\d+)）")


def _impact_text(graph_impact: Any) -> str | None:
    """`graph_impact`（`新增 1 節點、2 邊、2 claims（另 2 筆已在圖上或逐字保留）｜來源：NVIDIA（tier 1）、…`）→ 短版一行：
    去掉「另…」那個括號、同一個 tier 的來源併成一個括號。數字一個不改；格式認不得就照抄。"""
    text = " ".join(str(graph_impact or "").split())
    if not text:
        return None
    delta, sep, sources = text.partition("｜來源：")
    delta = _IMPACT_ASIDE_RE.sub("", delta).strip()
    if not sep:
        return delta
    found = _IMPACT_SOURCE_RE.findall(sources)
    tiers = {tier for _name, tier in found}
    if found and len(tiers) == 1 and "、".join(f"{n}（tier {t}）" for n, t in found) == sources:
        return f"{delta}｜來源 {'、'.join(n.strip() for n, _t in found)}（tier {tiers.pop()}）"
    return f"{delta}｜來源：{sources}"


def decisions_block(*, actionable: Sequence[Mapping[str, Any]] | None, problem: str | None,
                    todo_mod: Any) -> tuple[list[str], str | None]:
    """③ 待你決定：一條一塊——**[編號] 主詞**、細節一行、go＝、不含、圖會變、建議（2026-10-28 使用者核可的排版）。
    清單與批次指令跟心跳段 3 同一份（`todo.actionable_items`、`heartbeat.recommended_batch`）；go／不含的白話取自
    `todo.GO_PLAIN`（與 `GO_AUTHORIZATION` 同鍵，L16）。回（這一塊的行, 建議的批次指令或 None）——批次指令由
    `compose_brief` 單獨放最後一則。2026-10-07 起不含向你要文件（③b）。"""
    from crons.heartbeat import PQ2_LIST_LIMIT, recommended_batch

    if actionable is None:
        return [f"### ③ 待你決定（讀不到：{problem}）"], None
    lines = [f"### ③ 待你決定（{len(actionable)}）"]
    if not actionable:
        lines.append("- 沒有")
        return lines, None
    items = sorted(actionable, key=lambda i: int(i["n"]))
    shown = items[:PQ2_LIST_LIMIT]
    for index, item in enumerate(shown):
        head, detail = _split_title(item.get("title"))
        plain = todo_mod.go_plain(str(item.get("type")))
        if index:
            lines.append("")
        lines.append(f"**[{item['n']}] {head}**")
        if detail:
            lines.append(f"- {_clip(detail, 70)}")
        lines.extend([f"- go＝{plain['go']}", f"- 不含：{plain['excludes']}"])
        impact = _impact_text(item.get("graph_impact"))
        if impact:
            lines.append(f"- 圖會變：{impact}")
        rec = item.get("recommendation") or {}
        if rec.get("verb") in ("go", "drop", "pending"):
            lines.append(f"- 建議 {rec.get('verb')}：{_clip(rec.get('reason'), 90)}")
    if len(items) > PQ2_LIST_LIMIT:
        lines.append(f"-# 其餘 {len(items) - PQ2_LIST_LIMIT} 筆在完整心跳段 3")
    decisions = [int(i["n"]) for i in shown if i.get("type") == "watch_decision"]
    if decisions:
        # 批次語法帶不了日期，watch_decision 的 bare go／bare pending 一定被拒（Step 1.7，第 2 輪 N-h）
        lines.append(f"-# {'、'.join(f'[{n}]' for n in decisions)} 是到期的等待：批次裡只能 drop；續等或要研究在互動 session 說")
    batch, missing = recommended_batch(shown)
    if batch is None:
        lines.append("-# 都沒寫建議——自己判斷後回 `<編號…> go <編號…> drop <編號…> pending`")
        return lines, None
    if missing:
        lines.append(f"-# 沒寫建議：{'、'.join(f'[{n}]' for n in missing)}——要你自己判斷，不在最後那一則裡")
    lines.append("-# 建議是鑄號時寫的；最後一則是可直接複製的批次指令")
    return lines, batch


def documents_block(*, asking: Sequence[Mapping[str, Any]] | None, problem: str | None, todo_mod: Any) -> list[str]:
    """③b 等你提供的文件（2026-10-07 使用者：「隔離一區讓我知道 也不要讓我直接 go 提供文件才算 go」）。
    與心跳段 3 同一份名單（`todo.document_requests`）；0 也印一行。跟 ③ 同一則訊息（沒有自己的 `###`）。"""
    from crons.heartbeat import PQ2_LIST_LIMIT

    if asking is None:
        return [f"**③b 等你提供的文件：讀不到（{problem}）**"]
    if not asking:
        return ["**③b 等你提供的文件：沒有**", "-# 提供文件才算 go，批次 go 不收這一區"]
    ordered = sorted(asking, key=lambda i: int(i["n"]))
    lines = [f"**③b 等你提供的文件（{len(asking)}）**"]
    for item in ordered[:PQ2_LIST_LIMIT]:
        title = " ".join(str(item.get("title") or "").split()).removeprefix("向你要文件：")
        lines.append(f"- [{item['n']}] {_clip(title, 80)}")
    if len(ordered) > PQ2_LIST_LIMIT:
        lines.append(f"-# 其餘 {len(ordered) - PQ2_LIST_LIMIT} 筆在完整心跳段 3")
    excludes = todo_mod.go_plain("source_trace_review")["excludes"]
    lines.append("-# 提供文件才算 go，批次 go 不收這一區：有文件就直接給我（放 library/private/inbox/ 或貼路徑），"
                 f"拿不到回 `<編號> drop`｜不含：{excludes}")
    return lines


# ---------------------------------------------------------------------------
# ④ 狀態與健康度
# ---------------------------------------------------------------------------

#: LLM 步驟的短名（只給 Discord 那一則用；完整標籤在執行紀錄）。
LLM_STEP_WORDS: Mapping[str, str] = {"01c_radar_propose": "外部雷達", "07a_triage_propose": "分類",
                                     "10b_prescreen_propose": "預篩", "10e_poll_propose": "T2 輪詢",
                                     "11c_digest_propose": "每日摘要"}


def _last_line(text: Any) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _n(value: Any) -> str:
    return "未讀到" if value is None else str(value)


def disproof_line(snapshot: Mapping[str, Any]) -> str:
    """反證一行——數字是心跳快照同一份（`collect_snapshot` 用 `disproof_counts` 算的；L16 不另算）。在盯、觸及待處置、
    未盯每天都印（AGENTS 狀態塊）；到期待複查與加碼條件觸及只在不是 0 時印（讀不到也印——INV-3）。"""
    s = snapshot
    touched = s.get("disproof.touched_pending")
    line = (f"反證：在盯 {_n(s.get('disproof.watching'))}"
            + (f"｜**觸及待處置 {_n(touched)}**" if touched != 0 else "｜觸及待處置 0")
            + f"｜未盯 {_n(s.get('disproof.unwatched'))}")
    for key, label in (("disproof.expired_pending", "到期待複查"), ("confirm.touched_pending", "加碼條件觸及")):
        if s.get(key) != 0:
            line += f"｜**{label} {_n(s.get(key))}**"
    return line


def health_block(*, record: Mapping[str, Any] | None, record_problem: str | None,
                 quota: Sequence[Mapping[str, Any]], snapshot: Mapping[str, Any],
                 model_drift: str | None = None, invariant_fails: Sequence[str] = (),
                 red_sections: Sequence[str] = ()) -> list[str]:
    """④ 第一行「daily 幾步」＋底下逐條出錯的事；沒問題就同一行寫「健康度正常」。

    同一個原因只印一次：被額度擋下的 LLM 步驟併成一行；invariant 那一步失敗與快照的「invariants FAIL N」是同一件事，
    併成一行並寫出是哪幾條（2026-10-28：短版把同一個 SourceDocSync 誤報印成兩行「失敗」）。健康紅燈寫出是哪一節。"""
    problems: list[str] = []
    # 只有真的被擋（rejected）的步驟併進額度那一行。接近上限（allowed_warning）時步驟照跑，它們自己的失敗要照列——
    # 2026-10-08：T2 輪詢一次呼叫逾時，被併進「額度接近上限……這一輪沒跑」那行，使用者以為是額度出錯，而那些步驟其實都跑了。
    folded = {key for entry in quota if entry.get("status") == "rejected" for key in entry.get("steps") or ()}
    for entry in quota:
        names = "、".join(LLM_STEP_WORDS.get(k, k) for k in entry.get("steps") or ())
        head = (f"LLM 額度{entry.get('status_words')}：Claude{entry.get('window_words')}額度{entry.get('used_text')}，"
                f"{entry.get('reset_text')} 重置")
        problems.append(head + (f"——這一輪沒跑：{names}" if entry.get("status") == "rejected"
                                else f"——這一輪照跑（{names}）；用完時這些步驟會暫停"))
    fails = snapshot.get("invariants.fail")
    fail_text = f"invariant FAIL {fails}" + (f"：{'、'.join(invariant_fails)}" if invariant_fails else "")
    invariants_said = False
    if record is None:
        # `_load_run_record` 的理由本身就是完整的一句（「今天沒有 daily 執行紀錄（daily 沒跑…）」／「讀不到」／「格式不對」）
        problems.append(record_problem or "今天沒有 daily 執行紀錄")
        head_line = "- daily：沒有執行紀錄"
    else:
        steps = [r for r in record.get("steps") or [] if isinstance(r, Mapping)]
        done = sum(1 for r in steps if r.get("status") == "ok")
        skipped_n = sum(1 for r in steps if r.get("status") == "skipped")
        head_line = f"- daily {done}/{len(steps)} 步" + (f"（跳過 {skipped_n}）" if skipped_n else "")
        for row in steps:
            if row.get("status") in ("ok", "skipped", "running", None) or row.get("key") in folded:
                continue
            if str(row.get("key") or "").endswith("_invariants") and fails:
                problems.append(fail_text)
                invariants_said = True
                continue
            why = _last_line(row.get("error") or row.get("reason") or row.get("stderr_tail"))
            exit_text = f"exit {row.get('exit')}" if row.get("exit") not in (None, "", 0, "0") else ""
            # 多次呼叫的 LLM 步驟：寫出幾次、各幾次怎樣——任一次失敗整步不寫結果，成功的那幾次也沒套用（daily_task 的跑法）
            calls = [c for c in row.get("calls") or () if isinstance(c, Mapping)]
            calls_text = ""
            if len(calls) > 1:
                tally = Counter(str(c.get("status")) for c in calls)
                calls_text = (f"{len(calls)} 次呼叫：" + "、".join(f"{k} {v}" for k, v in tally.items())
                              + "；任一次沒過整步不寫結果")
            detail = "；".join(x for x in (exit_text, _short(why, 90), calls_text) if x)
            skipped = [r.get("label") or r.get("key") for r in steps
                       if r.get("status") == "skipped" and str(row.get("key")) in str(r.get("reason") or "")]
            problems.append(f"{row.get('label') or row.get('key')}：{row.get('status')}" + (f"（{detail}）" if detail else "")
                            + (f"——連帶跳過：{'、'.join(map(str, skipped))}" if skipped else ""))
    if fails and not invariants_said:
        problems.append(fail_text)
    if snapshot.get("health.red"):
        problems.append(f"健康紅燈 {snapshot['health.red']}" + (f"：{'、'.join(red_sections)}" if red_sections else ""))
    if model_drift:
        problems.append(f"LLM 實際 model 變了：{model_drift}——雷達與分類的產量可能跟著變")
    if not problems:
        return [head_line + "｜健康度正常（invariants、健康審查無紅）"]
    return [head_line, *(f"  - ⚠ {p}" for p in problems)]


def captured_problems(*, now: datetime, capture_dir: Path | None) -> tuple[list[str], list[str]]:
    """(FAIL 的 invariant 名, 紅燈的健康審查節名)——讀 daily 當天的 capture 檔（與快照的計數同一份來源）。
    讀不到回空：只少名字，計數照印。"""
    from crons import heartbeat as hb

    fails: list[str] = []
    reds: list[str] = []
    try:
        checks, problem = hb._capture("invariants", now=now, capture_dir=capture_dir)
        if problem is None:
            fails = [str(c.get("check")) for c in checks or () if isinstance(c, Mapping) and c.get("status") == "FAIL"]
    except Exception:  # noqa: BLE001
        pass
    try:
        health, problem = hb._capture("health", now=now, capture_dir=capture_dir)
        if problem is None:
            reds = [str(s.get("title") or "").split("（", 1)[0] for s in (health or {}).get("sections") or ()
                    if isinstance(s, Mapping) and s.get("level") == "red"]
    except Exception:  # noqa: BLE001
        pass
    return fails, reds


def candidate_short_lines(state_dir: Path | None) -> list[str]:
    """④ 的候選兩行：五個狀態（封閉字彙，0 也印、有檔印最老滯留）＋覆蓋（邊緣無法量、邊緣卻沒敘事每天印；舊版、
    前提失效、量不到卻沒敘事不是 0 才印）。數字與心跳段 2 同一個函式（`heartbeat.candidate_counts`）。"""
    from crons import heartbeat as hb

    board, absence = hb._load_state(state_dir, "candidates")
    if absence is not None:
        return [f"- 候選：{absence.reason}（{absence.kind}）"]
    c = hb.candidate_counts(board)
    cover = f"- 覆蓋：邊緣無法量 {c['edge_unmeasurable']}｜邊緣卻沒敘事 {c['edge_gap']}"
    for key, label in (("unmeasured", "量不到卻沒敘事"), ("legacy", "舊版"), ("precondition_failed", "前提失效")):
        if c.get(key):
            cover += f"｜{label} {c[key]}"
    lines = [f"- 候選：{hb.candidate_states_text(c)}", cover]
    holdings = board.get("holdings") or {}
    if holdings.get("status") == "ok" and holdings.get("unresolved"):
        lines.append(f"- 持股解析不到 {len(holdings['unresolved'])}：{'、'.join(map(str, holdings['unresolved'][:5]))}")
    return lines


def watch_short_line(*, now: datetime) -> str:
    from crons import heartbeat as hb

    c = hb.watch_today_counts(now=now)
    line = f"watch：今日醒 {c['woken']}｜到期 {c['expired']}｜語意標旗 {c['semantic_flagged']}"
    # 2026-10-28：APP「在等什麼」頁併進首頁——停滯與追源需處置改在這裡現形（短版只在不是 0 時印；完整心跳每天都印）
    if c.get("stalled"):
        line += f"｜停滯 {c['stalled']}"
    if c.get("trace_needs_attention"):
        line += f"｜追源需處置 {c['trace_needs_attention']}"
    return line


# ---------------------------------------------------------------------------
# ⑤ 下一次研究、最後一則
# ---------------------------------------------------------------------------

#: ⑤ 的格（2026-10-22 起由 `engine_b.todo_ledger.LEDGER` 導出——「歸零就不漏球」的唯一清單；涵蓋登記表與測試在那裡）。
#: 「等你提供的文件」是使用者的動作，只住 ③b，不再算進「下一次研究要做的」。
TODO_COUNTERS: tuple[tuple[str, str], ...] = tuple((row.key, row.label) for row in _TODO_LEDGER)


def todo_block(snapshot: Mapping[str, Any], ledger: Sequence[Any] | None = None,
               next_line: str | None = None) -> list[str]:
    """⑤：非 0 的格一格一行（工作量、最老天數）；0 的格名字印在小字（L14：每格都出現；AGENTS「未 triage N」
    「未檢 N」必印——0 也在這一行點名）；未讀到的另列警告（不是 0）。組不出 ledger 退回快照計數。最後一行小字是下一步。"""
    from engine_b.todo_ledger import LEDGER_BY_KEY

    lines = ["### ⑤ 下一次研究"]
    if ledger is not None:
        live, zero, unread = [], [], []
        for row in ledger:
            if row.count is None:
                unread.append(row.label)
            elif row.count == 0:
                zero.append(row.label)
            else:
                unit = LEDGER_BY_KEY[row.key].unit
                bits = [b for b in (row.work, f"最老 {row.oldest_days} 天" if row.oldest_days else None, row.note) if b]
                live.append(f"- {row.label} {row.count} {unit}" + (f"（{'；'.join(bits)}）" if bits else ""))
        lines.extend(live or ["- 每一格都是 0"])
        if unread:
            lines.append("- ⚠ 未讀到（不是 0）：" + "、".join(unread))
        if zero:
            lines.append(f"-# 0 的格：{'、'.join(zero)}")
    else:
        cells = [f"{label} {'未讀到' if snapshot.get(key) is None else snapshot.get(key)}" for key, label in TODO_COUNTERS]
        lines.append("- " + "｜".join(cells))
        lines.append("-# 清單組不出來，只有計數")
    if next_line:
        lines.append(f"-# 下一步貼：{next_line}")
    return lines


def next_step_line(*, snapshot: Mapping[str, Any], ledger: Sequence[Any] | None, now: datetime) -> str:
    """⑤ 的「下一步貼」：研究計數、Phase 下一步、題材到期——全部機械導出（`todo_ledger.next_prompt`）。
    ③ 的批次指令不在這裡（它是最後一則）；要清的格上面已逐行列出，這裡只留命令本身。"""
    from crons import heartbeat as hb
    from crons import phase_status_hint
    from engine_b.todo_ledger import next_prompt

    try:
        phase_step = phase_status_hint.active_step_text()
    except Exception:  # noqa: BLE001
        phase_step = None
    try:
        _line, theme_due = hb.theme_scan_line(now=now)
    except Exception:  # noqa: BLE001
        theme_due = False
    counts = ledger if ledger is not None else {key: snapshot.get(key) for key, _ in TODO_COUNTERS}
    text = next_prompt(counts, decision_batch=None, phase_step=phase_step, theme_due=bool(theme_due))
    return text.split("——", 1)[0] if text.startswith("`/research-drain`") else text


def copy_line(batch: str | None) -> list[str]:
    """最後一則：③ 的建議批次指令，單獨一行 inline code（Discord 手機上一點就複製）。沒有建議就沒有這一則。"""
    return [f"`{batch}`"] if batch else []


# ---------------------------------------------------------------------------
# 組裝
# ---------------------------------------------------------------------------

def compose_brief(*, now: datetime, summary: str, snapshot: Mapping[str, Any], run_record_path: Path | None,
                  leads_path: Path | None = None, heartbeat_dir: Path = HEARTBEAT_DIR,
                  diff_lines: Sequence[str] = (), state_dir: Path | None = None,
                  ledger: Sequence[Any] | None = None) -> str:
    """組 Discord 那一則（markdown）。每一塊各自降級：組不出來就印一行理由，不讓整則消失（L13）；
    ④ 的每一行也各自降級（候選板 artifact 讀不到不帶走 watch 那一行）。`diff_lines`（較昨變動）只在完整心跳印。"""
    from crons import heartbeat as hb
    from engine_b import digest as digest_mod

    del diff_lines  # 2026-10-28 起短版不印較昨變動（一行塞 47 項、手機上讀不完）；完整心跳段 2 照印
    today: date = now.astimezone().date()
    blocks: list[list[str]] = [brief_header(summary)]
    digest = digest_mod.load_digest(today, out_dir=heartbeat_dir)
    impact = digest_mod.load_impact(today, out_dir=heartbeat_dir)
    record, record_problem = hb._load_run_record(run_record_path, now=now)
    rows = {str(r.get("key")): r for r in (record or {}).get("steps") or [] if isinstance(r, Mapping)}
    digest_step = rows.get("11e_digest_apply") or rows.get("11c_digest_propose") or {}
    digest_problem = None if digest else (
        f"LLM 摘要今天沒產生（{digest_step.get('key') or '摘要步驟'} {digest_step.get('status') or '沒跑'}"
        + (f"：{_short(digest_step.get('error') or digest_step.get('reason'), 60)}" if
           (digest_step.get('error') or digest_step.get('reason')) else "") + "）")
    receipt = _read_json(heartbeat_dir / f"radar_{today.isoformat()}.json")
    radar_step = next((rows[k] for k in ("01e_radar_apply", "01c_radar_propose") if k in rows
                       and rows[k].get("status") != "ok"), None)
    radar_problem = None if radar_step is None else (
        f"{radar_step.get('key')} {radar_step.get('status')}：{_short(radar_step.get('error') or radar_step.get('reason'), 60)}")

    def guarded(title: str, build: Any) -> list[str]:
        try:
            return build()
        except Exception as exc:  # noqa: BLE001 — 一塊組不出來不帶走整則
            return [f"### {title}", f"- 這一塊組不出來：{type(exc).__name__}: {_short(exc, 80)}"]

    def load_store() -> Mapping[str, Any]:
        from engine_b import leads as leads_mod

        return leads_mod.load(leads_path) if leads_path else leads_mod.load()

    def leads_part() -> list[str]:
        store = load_store()
        # 窗從上一次心跳起算（2026-10-22：固定 26 小時每天重算前一輪）——①、處理數字、TL;DR 材料同一個起點
        since = digest_mod.window_start(now, snapshot_dir=heartbeat_dir / "snapshots")
        try:
            processing = processing_lines(store, now=now, since=since)
        except Exception as exc:  # noqa: BLE001 — 這幾行算不出來就說，不帶走整塊
            processing = [f"- 處理：算不出來（{type(exc).__name__}）"]
        return leads_block(digest=digest, todays=digest_mod.select_leads(store, now=now, since=since),
                           digest_problem=digest_problem, since=since, processing=processing)

    def lead_field(ids: set[str], field: str) -> dict[str, str]:
        try:
            leads = load_store().get("leads") or {}
            return {lid: str((leads.get(lid) or {}).get(field) or "") for lid in ids}
        except Exception:  # noqa: BLE001 — 讀不到就印網址／「lead 不在」，不帶走整塊
            return {}

    def events_part() -> list[str]:
        accepted = {str(a.get("lead_id")) for a in (receipt or {}).get("accepted") or () if isinstance(a, Mapping)}
        rejected = {str(r.get("lead_id")) for r in (receipt or {}).get("rejected") or () if isinstance(r, Mapping)}
        return events_block(digest=digest, receipt=receipt, digest_problem=digest_problem, radar_problem=radar_problem,
                            recent_accepted=recent_radar_accepted(heartbeat_dir, today),
                            lead_titles=lead_field(rejected, "title"), impact=impact,
                            lead_states=lead_field(accepted, "status"), baseline=radar_baseline(heartbeat_dir, today))

    batch: list[str | None] = [None]

    def decisions_part() -> list[str]:
        from engine_b import todo as todo_mod

        try:
            pool = todo_mod.load()
            actionable, asking = todo_mod.actionable_items(pool), todo_mod.document_requests(pool)
            problem = None
        except Exception as exc:  # noqa: BLE001
            actionable = asking = None
            problem = type(exc).__name__
        lines, batch[0] = decisions_block(actionable=actionable, problem=problem, todo_mod=todo_mod)
        return [*lines, "", *documents_block(asking=asking, problem=problem, todo_mod=todo_mod)]

    def line(build: Any, label: str) -> list[str]:
        try:
            out = build()
        except Exception as exc:  # noqa: BLE001 — 一行讀不到就說讀不到（INV-3），不帶走其他行
            return [f"- {label}：讀不到（{type(exc).__name__}）"]
        return [out] if isinstance(out, str) else list(out)

    def waits_line() -> str:
        from engine_b import leads as leads_mod

        holes = leads_mod.parked_without_expiry(load_store())
        return f"- **無到期的等待 {len(holes)}**（每個等待都要有到期）" if holes else "- 無到期的等待 0"

    def status_part() -> list[str]:
        capture_dir = run_record_path.parent if run_record_path else None
        try:
            drift = hb.llm_model_drift(record, now=now, record_dir=capture_dir)
        except Exception:  # noqa: BLE001 — 比不了就不印這一條，不帶走健康度
            drift = None
        fails, reds = captured_problems(now=now, capture_dir=capture_dir)
        health = health_block(record=record, record_problem=record_problem, quota=hb.quota_entries(rows, now=now),
                              snapshot=snapshot, model_drift=drift, invariant_fails=fails, red_sections=reds)
        # 2026-10-21 使用者問「價格一直跌，等回落能及時反應嗎」：只印不判，壞了只壞自己這一塊
        wait = line(lambda: hb.priced_wait_short_lines(state_dir, today=today,
                                                       label=lambda r: company_label(company_id=r.get("company_id"),
                                                                                     ticker=r.get("ticker"))), "等回落")
        return ["### ④ 狀態與健康度", *health, *line(lambda: candidate_short_lines(state_dir), "候選"),
                *(["", *wait, ""] if wait else []),
                *line(lambda: "- " + watch_short_line(now=now), "watch"),
                *line(lambda: "- " + disproof_line(snapshot), "反證"),
                *line(waits_line, "無到期的等待")]

    def todo_part() -> list[str]:
        try:
            nxt = next_step_line(snapshot=snapshot, ledger=ledger, now=now)
        except Exception as exc:  # noqa: BLE001 — 下一步組不出來不帶走 ⑤
            nxt = f"組不出來（{type(exc).__name__}）——看上面哪一格不是 0"
        return todo_block(snapshot, ledger, nxt)

    blocks.append(guarded("① Lead 抓了什麼", leads_part))
    blocks.append(guarded("② 市場大事", events_part))
    blocks.append(guarded("③ 待你決定", decisions_part))
    blocks.append(guarded("④ 狀態與健康度", status_part))
    blocks.append(guarded("⑤ 下一次研究", todo_part))
    blocks.append(copy_line(batch[0]))
    return "\n\n".join("\n".join(block) for block in blocks if block).rstrip() + "\n"


__all__ = ["RADAR_SCOPE_WORDS", "RESEARCH_TERMINAL_STATES", "SOURCE_LABELS", "TODO_COUNTERS", "brief_header",
           "candidate_short_lines", "company_label", "compose_brief", "copy_line", "decisions_block", "disproof_line",
           "documents_block", "events_block", "health_block", "impact_total_line", "leads_block", "processing_lines",
           "radar_baseline", "todo_block"]
