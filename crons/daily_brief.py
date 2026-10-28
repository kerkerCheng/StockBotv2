"""Discord 那一則（2026-10-07 使用者指示）。

使用者原話：「每日心跳，太雜了，而且我想看到你每天 websearch 的結果跟你做了什麼，比較有實感……Lead 抓了哪些 TL;DR、
Websearch 大事件 TL;DR、幾件事待我決定、健康度等等」。

五塊、固定順序、**每塊一定出現**（沒東西也說沒東西——INV-3）：

① lead 抓了什麼：⑪c LLM 寫的 TL;DR（每句都指得回今天的 lead）；沒產生時退回程式組的來源計數與分流 go 的標題。
   第二行是**我們做了哪些處理**（同日使用者：「我們做了哪些處理的數字也要印」）：分類幾則（go／no-go、LLM／互動）、
   研究到終局幾條（入圖包／已入圖／停放；lead 的轉移紀錄 10-07 起才有）、還沒分類與待深挖的總數。
② 市場大事：同上；退回雷達收據收下的那幾則（層別｜標題｜一句事實）。
③ 待你決定：pq2 要你決定的每一條（程式組，與心跳段 3 同一個 `_pq2_item_lines`）。
③b 等你提供的文件：向你要文件的每一條，**獨立一區、批次 go 不收**——提供文件才算 go（同日使用者：「隔離一區讓我知道
   也不要讓我直接 go 提供文件才算 go」；名單只有 `todo.document_requests()` 一份）。
④ 狀態與健康度：**每天都印**的基本狀態（daily 步數、較昨變動、候選各格檔數與最老滯留、watch 今日醒／到期／標旗／未檢、
   反證與加碼條件、無到期的等待、今天第一次被點名的新名字——2026-10-07 使用者：「daily 心跳基本重要的 status 還是要印」），
   再接健康度：沒問題就一行；有問題才逐條（daily 失敗的步驟、LLM 額度、invariants FAIL、健康紅燈）。
⑤ 下一次研究要做的：常駐計數器（未 triage、未檢、待深挖、該重讀、等你提供的文件）——**0 也印**（L14）。

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


def _source_family(source: Any) -> str:
    prefix = str(source or "").split(":", 1)[0]
    return SOURCE_LABELS.get(prefix, prefix or "（沒有來源）")


def _read_json(path: Path) -> Any:
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


#: 研究到終局＝轉到這三個狀態（入圖包／已入圖／停放）。
RESEARCH_TERMINAL_STATES: tuple[str, ...] = ("action_prepared", "applied", "parked")


def _stamp(raw: Any) -> datetime | None:
    try:
        moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def processing_line(store: Mapping[str, Any], *, now: datetime, hours: int | None = None,
                    since: datetime | None = None) -> str:
    """① 的處理數字（2026-10-07 使用者：「Lead 抓了什麼 我們做了哪些處理的數字也要印」）。

    同一個時間窗（`engine_b.digest.WINDOW_HOURS`）：分類（`triage.decided_at` 在窗內；go／no-go、LLM／互動分開）、
    研究到終局（`transitions` 在窗內轉到入圖包／已入圖／停放——10-07 起才有轉移紀錄）、還沒分類與待深挖的總數。"""
    from datetime import timedelta

    from engine_b.digest import WINDOW_HOURS

    cutoff = since if since is not None else now - timedelta(hours=hours or WINDOW_HOURS)
    leads = [lead for lead in (store.get("leads") or {}).values() if isinstance(lead, Mapping)]
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
    return (f"- 處理：分類 {go + no_go}（go {go}／no-go {no_go}；LLM {by_llm}／互動 {by_hand}／機械或舊資料 {by_rule}）"
            f"｜研究到終局 {sum(finished.values())}（入圖包 {finished['action_prepared']}／已入圖 {finished['applied']}"
            f"／停放 {finished['parked']}）｜還沒分類 {pending}｜待深挖 {queued}")


def impact_total_line(impact: Mapping[str, Any] | None, digest: Mapping[str, Any] | None) -> str:
    """① 的一行總數（雷達精進 C2）：今天外部 lead 碰到我們幾則（確定性對照）＋ LLM 的「可能怎麼影響」收了幾句、丟幾句。
    完整表在 `impact_<日期>.json`（心跳落檔也印）。沒有對照檔與對照算壞要說出來，不印 0（INV-3）。"""
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


_LINK_WORDS = {"own": "本身"}
#: 短版每則雷達新聞下最多印幾句 LLM 提議（推播只送短版、短版不能太雜——2026-10-07 使用者）。
PROPOSALS_PER_ITEM = 2


def _narrative_label(ticker: str, links: Sequence[str]) -> str:
    first = links[0] if links else ""
    if first in _LINK_WORDS:
        word = _LINK_WORDS[first]
    elif first.startswith("slot:"):
        word = first[len("slot:"):].split("<", 1)[0] + " 格"
    else:
        word = "騎讀圖"
    return f"{ticker}〔{word}〕"


def impact_touch_lines(row: Mapping[str, Any] | None, proposals: Sequence[Mapping[str, Any]] = (), *,
                       limit: int = 3) -> list[str]:
    """② 每則雷達新聞下面：「↳ 碰到」一行（每類最多 `limit` 個、其餘「另 N」、樞紐只印數字）＋ LLM 那一句（標「提議」）。
    什麼都沒碰到就不印（那則本身已列在上面；總數在 ①）。"""
    if not row:
        return []
    parts: list[str] = []
    narr = list((row.get("narratives") or {}).items())
    if narr:
        parts.append("敘事 " + "、".join(_narrative_label(t, v) for t, v in narr[:limit])
                     + (f" 另 {len(narr) - limit} 份" if len(narr) > limit else ""))
    reads = list(row.get("readings") or {})
    if reads:
        parts.append("讀圖 " + "、".join(reads[:limit]) + (f" 另 {len(reads) - limit} 份" if len(reads) > limit else ""))
    ws = row.get("watches") or []
    if ws:
        parts.append(f"在盯 反證 {sum(w.get('role') == '反證' for w in ws)}／加碼 {sum(w.get('role') == '加碼條件' for w in ws)}")
    hub = row.get("hub_only_counts") or {}
    if row.get("hub_entities") and any(hub.values()):
        parts.append(f"另經 {'／'.join(str(h).removeprefix('co:') for h in row['hub_entities'][:2])} 碰到 "
                     f"敘事 {hub.get('narratives', 0)}、在盯 {hub.get('watches', 0)}（樞紐只計數）")
    lines = [f"  ↳ 碰到：{'；'.join(parts)}"] if parts else []
    shown = [p for p in proposals if p.get("verdict") != "unrelated"]
    for p in shown[:PROPOSALS_PER_ITEM]:
        tag = "提議" if p.get("verdict") == "may_touch" else "提議・不確定"
        lines.append(f"  ↳ {tag}（{p.get('target')}）：{_short(p.get('sentence'), 80)}")
    if len(shown) > PROPOSALS_PER_ITEM:
        lines.append(f"  ↳ 另 {len(shown) - PROPOSALS_PER_ITEM} 句提議見心跳落檔")
    return lines


def leads_block(*, digest: Mapping[str, Any] | None, todays: Sequence[Mapping[str, Any]], since: datetime,
                digest_problem: str | None, processing: str | None = None, impact_line: str | None = None) -> list[str]:
    """① lead 抓了什麼。標題行永遠是程式數的（外面新進幾則、哪些來源；前幾天進來、這輪才分類的另計；
    我們自己登記的研究題另計、不摘要）；內容是 LLM 的 TL;DR，沒有就退回分流 go 的標題。

    `todays` 是 `select_leads` 的窗（窗內首見 ∪ 窗內剛分類）；`since` 是窗的起點。2026-10-16：10-13 標題寫「新進 125」，
    其中 82 則是 10-10～10-12 積下來、那天才分類的——一個數字裝兩種意思（L12），所以首見在窗前的拆出來印。"""
    from collections import Counter

    from engine_b.digest import is_external

    external = [lead for lead in todays if is_external(lead)]
    internal = len(todays) - len(external)
    fresh = [lead for lead in external if (seen := _stamp(lead.get("first_seen"))) is not None and seen >= since]
    backlog = len(external) - len(fresh)
    families = Counter(_source_family(lead.get("source")) for lead in fresh)
    head = f"**① Lead 抓了什麼**（外面新進 {len(fresh)} 則" + (
        "：" + "、".join(f"{name} {n}" for name, n in families.most_common()) if fresh else "") + (
        f"；另有前幾天進來、這輪才分類的 {backlog} 則" if backlog else "") + (
        f"；另有我們自己登記的研究題 {internal} 則，不摘要" if internal else "") + "）"
    lines = [head]
    if processing:
        lines.append(processing)
    if impact_line:
        lines.append(impact_line)
    bullets = list((digest or {}).get("leads") or ())
    if bullets:
        lines.extend(f"- {b['text']}" for b in bullets)
        return lines
    went = [lead for lead in external if lead.get("status") == "triaged_go"]
    reason = digest_problem or "LLM 摘要今天沒產生"
    if not external:
        lines.append("- 這一輪外面沒有新進的 lead")
    elif went:
        lines.append(f"- （{reason}——改列分流判 go 的 {len(went)} 則）")
        lines.extend(f"- {_short(lead.get('title'))}" for lead in went[:3])
    else:
        lines.append(f"- （{reason}；分流判 go 的 0 則）")
    return lines


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


#: lead 現在的狀態 → ② 每則後面印的處置（固定幾個詞；2026-10-22）。
LEAD_STATE_WORDS: Mapping[str, str] = {
    "triaged_go": "go", "triaged_no_go": "篩掉", "pending": "還沒分類", "researching": "研究中", "parked": "停放",
    "action_prepared": "入圖包等核准", "applied": "已入圖",
}


def _target_ticker(target: Any) -> str:
    return str(target or "?").split("#", 1)[0]


def radar_item_outcome(row: Mapping[str, Any] | None, proposals: Sequence[Mapping[str, Any]],
                       status: str | None, *, impact_ran: bool = True) -> tuple[str, Counter]:
    """一則雷達新聞「後來怎麼了」：處置（lead 現在的狀態）＋ LLM 看過的結果（無關也算，不藏——2026-10-22：只印「碰到」
    看不到後來，就是使用者怕的「撈進來沒事」）。回（那一段字, 判定計數）。"""
    verdicts: Counter = Counter(str(p.get("verdict")) for p in proposals)
    head = LEAD_STATE_WORDS.get(str(status), str(status or "lead 不在"))
    kind = (row or {}).get("absence_kind")
    if proposals:
        may = [_target_ticker(p.get("target")) for p in proposals if p.get("verdict") == "may_touch"]
        bits = []
        if may:
            bits.append("可能有關 " + "、".join(dict.fromkeys(may)))
        if verdicts.get("unclear"):
            bits.append(f"看不出 {verdicts['unclear']} 格")
        if verdicts.get("unrelated"):
            bits.append(f"LLM 看過：無關 {verdicts['unrelated']} 格" if not may else f"無關 {verdicts['unrelated']} 格")
        tail = "；".join(bits)
    elif kind == "hub_only":
        hubs = "／".join(str(h).removeprefix("co:") for h in (row or {}).get("hub_entities") or ())[:40]
        tail = f"只經 {hubs or '大樞紐'}（大樞紐，沒逐格對）"
    elif not impact_ran:
        tail = "影響對照今天沒跑（不是沒碰到）"
    elif kind == "untouched" or not row:
        tail = "沒碰到我們"
    else:
        tail = "碰到了，但 LLM 今天沒看（超過上限或摘要失敗）"
    return f"→ {head}｜{tail}", verdicts


def events_block(*, digest: Mapping[str, Any] | None, receipt: Mapping[str, Any] | None,
                 digest_problem: str | None, radar_problem: str | None,
                 recent_accepted: Sequence[Mapping[str, Any]] = (),
                 lead_titles: Mapping[str, str] | None = None,
                 impact: Mapping[str, Any] | None = None,
                 lead_states: Mapping[str, str] | None = None) -> list[str]:
    """② 市場大事：**今天雷達收下的每一則都列**（層別＋雷達寫的一句事實），沒收的附理由，跟前幾天收過的標題很像的標「可能是同一件事」。

    2026-10-08 使用者：「tldr 只有三則，但你說收四則……還是 tldr 就把收的都包含上去？如果沒收但想讓我知道的就再註明」。
    原本這裡印 LLM 摘要的「市場大事」——最多 3 句、取材是過去 26 小時的所有 lead，所以會漏掉今天收的、又夾進昨天收的。
    收據不在（雷達沒跑）才退回 LLM 摘要。"""
    summary = (receipt or {}).get("summary") or {}
    rejected = [r for r in (receipt or {}).get("rejected") or () if isinstance(r, Mapping)]
    if receipt is None:
        lines = [f"**② 市場大事**（外部雷達今天沒有收據：{radar_problem or '沒跑'}）"]
        bullets = list((digest or {}).get("events") or ())
        if bullets:
            lines.append("- （改列 LLM 摘要的市場大事——取材是過去 26 小時的 lead，可能含前一天收的）")
            lines.extend(f"- {b['text']}" for b in bullets)
        else:
            lines.append("- 今天沒有收下任何一則")
        return lines
    accepted = [a for a in (receipt or {}).get("accepted") or () if isinstance(a, Mapping)]
    # 影響對照（雷達精進 C2）：確定性的「碰到」與 LLM 那一句都用 lead_id 對回這一則
    rows = {str(r.get("lead_id")): r for r in (impact or {}).get("rows") or () if isinstance(r, Mapping)}
    proposals: dict[str, list[Mapping[str, Any]]] = {}
    for p in (digest or {}).get("impacts") or ():
        if isinstance(p, Mapping):
            proposals.setdefault(str(p.get("lead_id")), []).append(p)
    # 2026-10-22 使用者：「可不可以短一點 讓我知道你有在做事就好 我怕的是撈進來然後什麼也沒發生」——每則一行
    # 「事實首句 → 處置｜LLM 看過的結果」；「碰到」的逐項、LLM 原句、篩掉理由在完整心跳段 3（雷達收下的每一則）。
    body: list[str] = []
    states: Counter = Counter()
    seen: Counter = Counter()
    for item in accepted:
        scope = RADAR_SCOPE_WORDS.get(str(item.get("scope")), "主題")
        lead_id = str(item.get("lead_id") or "")
        status = (lead_states or {}).get(lead_id)
        outcome, verdicts = radar_item_outcome(rows.get(lead_id), proposals.get(lead_id, ()), status,
                                               impact_ran=impact is not None and not (impact or {}).get("error"))
        states[LEAD_STATE_WORDS.get(str(status), "lead 不在")] += 1
        seen.update(verdicts)
        # 半形逗號夾在兩個數字之間是千分位，不是斷句（2026-10-28：「收窄為 1,350 億」被切成「收窄為 1」）
        first = re.split(r"[，。；;]|(?<!\d),|,(?!\d)",
                         str(item.get("fact") or item.get("title") or item.get("url") or ""), maxsplit=1)[0]
        line = f"- [{scope}] {_short(first, 60)} {outcome}"
        repeat = _possible_repeat(item, recent_accepted)
        if repeat is not None:
            line += f"（⚠ 可能跟 {str(repeat.get('_date', ''))[5:]} 收過的是同一件事）"
        body.append(line)
    after = "、".join(f"{word} {n}" for word, n in states.most_common())
    judged = sum(seen.values())
    looked = (f"；碰到我們的 {judged} 對 LLM 看過：可能有關 {seen.get('may_touch', 0)}、看不出 {seen.get('unclear', 0)}、"
              f"無關 {seen.get('unrelated', 0)}") if judged else ""
    lines = [f"**② 市場大事**（雷達搜 {summary.get('searches', '?')} 次、收 {summary.get('new', 0)} 則"
             f"——市場 {summary.get('new_market', 0)}、主題 {summary.get('new_theme', 0)}、在盯 {summary.get('new_watch', 0)}"
             + (f"；沒收 {len(rejected)} 則" if rejected else "") + (f"｜之後：{after}{looked}" if accepted else "") + "）"]
    lines.extend(body)
    if accepted:
        lines.append("- go 的已算進 ⑤「待深挖」；「可能有關」等研究那則 lead 時判定；原句、逐格對照與篩掉理由在完整心跳段 3")
    else:
        lines.append("- 今天沒有收下任何一則")
    for item in rejected[:5]:
        why = RADAR_REJECT_WORDS.get(str(item.get("reason")), str(item.get("reason") or "?"))
        # 「已經有這個網址」那種：印那則既有 lead 的標題（收據只帶網址與 lead id）；讀不到就退回網址
        known = (lead_titles or {}).get(str(item.get("lead_id") or "")) or ""
        lines.append(f"- 沒收：{_short(known or item.get('title') or item.get('url'), 80)}——{why}")
    return lines


def decisions_block(*, actionable: Sequence[Mapping[str, Any]] | None, problem: str | None,
                    todo_mod: Any) -> list[str]:
    """③ 待你決定：與心跳段 3 同一份清單與同一個格式（`_pq2_item_lines`）。2026-10-07 起不含向你要文件（另一區）。"""
    from crons.heartbeat import _pq2_item_lines

    if actionable is None:
        return [f"**③ 待你決定**（讀不到：{problem}）"]
    lines = [f"**③ 待你決定**（{len(actionable)}）"]
    if not actionable:
        lines.append("- 沒有")
        return lines
    lines.extend("- " + line.strip() for line in _pq2_item_lines(actionable, todo_mod=todo_mod))
    return lines


def documents_block(*, asking: Sequence[Mapping[str, Any]] | None, problem: str | None, todo_mod: Any) -> list[str]:
    """③b 等你提供的文件（2026-10-07 使用者：「隔離一區讓我知道 也不要讓我直接 go 提供文件才算 go」）。
    與心跳段 3 同一份名單（`todo.document_requests`）與同一個格式（`_document_request_lines`）；0 也印。"""
    from crons.heartbeat import _document_request_lines

    if asking is None:
        return [f"**③b 等你提供的文件**（讀不到：{problem}）"]
    lines = [f"**③b 等你提供的文件**（{len(asking)}；提供文件才算 go，批次 go 不收這一區）"]
    if not asking:
        lines.append("- 沒有")
        return lines
    lines.extend("- " + line.strip() for line in _document_request_lines(asking, todo_mod=todo_mod))
    return lines


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
    """反證與加碼條件一行——數字是心跳快照同一份（`collect_snapshot` 用 `disproof_counts` 算的；L16 不另算）。"""
    s = snapshot
    return (f"反證：在盯 {_n(s.get('disproof.watching'))}｜**觸及待處置 {_n(s.get('disproof.touched_pending'))}**"
            f"｜到期待複查 {_n(s.get('disproof.expired_pending'))}｜未盯 {_n(s.get('disproof.unwatched'))}"
            f"｜加碼條件 在盯 {_n(s.get('confirm.watching'))}／觸及 {_n(s.get('confirm.touched_pending'))}")


def status_lines(*, record: Mapping[str, Any] | None, diff_lines: Sequence[str], status: Sequence[str]) -> list[str]:
    """④ 的上半：**每天都印**的基本狀態（2026-10-07 使用者：「daily 心跳基本重要的 status 還是要印」；AGENTS 要求心跳必印的
    計數器——候選各格檔數與最老滯留、watch 今日醒／到期／標旗、反證在盯與未盯——Discord 只送短版之後就住這裡）。
    `status` 是心跳自己的函式組的那幾行（同一個函式，不另寫一份——L16）；這裡只加 daily 的步數與較昨變動。"""
    lines = []
    if record is not None:
        steps = [r for r in record.get("steps") or [] if isinstance(r, Mapping)]
        ok = sum(1 for r in steps if r.get("status") == "ok")
        skipped = sum(1 for r in steps if r.get("status") == "skipped")
        lines.append(f"- daily {ok}/{len(steps)} 步完成｜跳過 {skipped}｜沒完成 {len(steps) - ok - skipped}")
    lines.extend(f"- {line}" for line in diff_lines[:1])
    lines.extend(f"- {line}" for line in status if line)
    return lines


def health_block(*, record: Mapping[str, Any] | None, record_problem: str | None,
                 quota: Sequence[Mapping[str, Any]], snapshot: Mapping[str, Any],
                 model_drift: str | None = None) -> list[str]:
    """④ 的下半（健康度）：沒問題一行；有問題逐條。被額度擋下的 LLM 步驟併成一行（同一個原因不重複四次）；其他失敗印人話標籤
    與錯誤的最後一行；invariants FAIL、健康紅燈照快照。"""
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
    if record is None:
        # `_load_run_record` 的理由本身就是完整的一句（「今天沒有 daily 執行紀錄（daily 沒跑…）」／「讀不到」／「格式不對」）
        problems.append(record_problem or "今天沒有 daily 執行紀錄")
        done = total = None
    else:
        steps = [r for r in record.get("steps") or [] if isinstance(r, Mapping)]
        total = len(steps)
        done = sum(1 for r in steps if r.get("status") == "ok")
        for row in steps:
            if row.get("status") in ("ok", "skipped", "running", None) or row.get("key") in folded:
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
    for key, label in (("invariants.fail", "invariants FAIL"), ("health.red", "健康紅燈")):
        if snapshot.get(key):
            problems.append(f"{label} {snapshot[key]}")
    if model_drift:
        problems.append(f"LLM 實際 model 變了：{model_drift}——雷達與分類的產量可能跟著變")
    if not problems:
        return [f"- 健康度：正常（daily {done}/{total} 步 ok；invariants、健康審查無紅）"]
    return [f"- 健康度：{len(problems)} 個問題", *(f"  - ⚠ {p}" for p in problems)]


#: ⑤ 的常駐計數器（快照鍵 → 人話）。**0 也印**（L14：會自己出現的計數器）。
#: ⑤ 的格（2026-10-22 起由 `engine_b.todo_ledger.LEDGER` 導出——「歸零就不漏球」的唯一清單；涵蓋登記表與測試在那裡）。
#: 「等你提供的文件」是使用者的動作，只住 ③b，不再算進「下一次研究要做的」。
TODO_COUNTERS: tuple[tuple[str, str], ...] = tuple((row.key, row.label) for row in _TODO_LEDGER)


def todo_block(snapshot: Mapping[str, Any], ledger: Sequence[Any] | None = None,
               next_line: str | None = None) -> list[str]:
    """⑤：有 ledger 印逐格（工作量、最老天數、0 的格）；組不出來退回快照計數。最後一行「下一步貼」。"""
    from engine_b.todo_ledger import render_cells

    lines = ["**⑤ 下一次研究要做的**（歸零＝不漏球；每一種狀態落在哪一格見 engine_b/todo_ledger.py 的涵蓋登記表）"]
    if ledger is not None:
        lines.extend(render_cells(ledger))
    else:
        cells = [f"{label} {'未讀到' if snapshot.get(key) is None else snapshot.get(key)}" for key, label in TODO_COUNTERS]
        lines.append("- " + "｜".join(cells) + "（清單組不出來，只有計數）")
    if next_line:
        lines.append(f"- **下一步貼**：{next_line}")
    return lines


def next_step_line(*, snapshot: Mapping[str, Any], ledger: Sequence[Any] | None, now: datetime) -> str:
    """「下一步貼」：③ 有建議的批次行、研究計數、Phase 下一步、題材到期——全部機械導出（`todo_ledger.next_prompt`）。"""
    from crons import heartbeat as hb
    from crons import phase_status_hint
    from engine_b import todo as todo_mod
    from engine_b.todo_ledger import next_prompt

    batch = None
    try:
        batch, _missing = hb.recommended_batch(todo_mod.actionable_items(todo_mod.load()))
    except Exception:  # noqa: BLE001
        batch = None
    try:
        phase_step = phase_status_hint.active_step_text()
    except Exception:  # noqa: BLE001
        phase_step = None
    try:
        _line, theme_due = hb.theme_scan_line(now=now)
    except Exception:  # noqa: BLE001
        theme_due = False
    counts = ledger if ledger is not None else {key: snapshot.get(key) for key, _ in TODO_COUNTERS}
    return next_prompt(counts, decision_batch=batch, phase_step=phase_step, theme_due=bool(theme_due))


def compose_brief(*, now: datetime, summary: str, snapshot: Mapping[str, Any], run_record_path: Path | None,
                  leads_path: Path | None = None, heartbeat_dir: Path = HEARTBEAT_DIR,
                  diff_lines: Sequence[str] = (), state_dir: Path | None = None,
                  ledger: Sequence[Any] | None = None) -> str:
    """組 Discord 那一則（markdown）。每一塊各自降級：組不出來就印一行理由，不讓整則消失（L13）；
    ④ 的每一行也各自降級（候選板 artifact 讀不到不帶走 watch 那一行）。"""
    from crons import heartbeat as hb
    from engine_b import digest as digest_mod

    today: date = now.astimezone().date()
    blocks: list[list[str]] = [[summary]]
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
            return [f"**{title}**（這一塊組不出來：{type(exc).__name__}: {_short(exc, 80)}）"]

    def leads_part() -> list[str]:
        from engine_b import leads as leads_mod

        store = leads_mod.load(leads_path) if leads_path else leads_mod.load()
        # 窗從上一次心跳起算（2026-10-22：固定 26 小時每天重算前一輪）——①、處理數字、TL;DR 材料同一個起點
        since = digest_mod.window_start(now, snapshot_dir=heartbeat_dir / "snapshots")
        try:
            processing = processing_line(store, now=now, since=since)
        except Exception as exc:  # noqa: BLE001 — 這一行算不出來就說，不帶走整塊
            processing = f"- 處理：算不出來（{type(exc).__name__}）"
        try:
            impact_line = impact_total_line(impact, digest)
        except Exception as exc:  # noqa: BLE001
            impact_line = f"- 對照：算不出來（{type(exc).__name__}）"
        return leads_block(digest=digest, todays=digest_mod.select_leads(store, now=now, since=since),
                           digest_problem=digest_problem, since=since, processing=processing,
                           impact_line=impact_line)

    def decisions_part() -> list[str]:
        from engine_b import todo as todo_mod

        try:
            pool = todo_mod.load()
            actionable, asking = todo_mod.actionable_items(pool), todo_mod.document_requests(pool)
        except Exception as exc:  # noqa: BLE001
            problem = f"{type(exc).__name__}"
            return [*decisions_block(actionable=None, problem=problem, todo_mod=todo_mod), "",
                    *documents_block(asking=None, problem=problem, todo_mod=todo_mod)]
        return [*decisions_block(actionable=actionable, problem=None, todo_mod=todo_mod), "",
                *documents_block(asking=asking, problem=None, todo_mod=todo_mod)]

    def line(build: Any, label: str) -> str:
        try:
            return build()
        except Exception as exc:  # noqa: BLE001 — 一行讀不到就說讀不到（INV-3），不帶走其他行
            return f"{label}：讀不到（{type(exc).__name__}）"

    def waits_line() -> str:
        from engine_b import leads as leads_mod

        store = leads_mod.load(leads_path) if leads_path else leads_mod.load()
        holes = leads_mod.parked_without_expiry(store)
        return (f"**無到期的等待 {len(holes)}**（INV-2：每個等待都要有到期）" if holes else "無到期的等待 0")

    def status_part() -> list[str]:
        status = [line(lambda: hb._candidate_lines(state_dir)[0], "候選"),
                  # 2026-10-21 使用者問「價格一直跌，等回落能及時反應嗎」：只印不判，壞了只壞自己這一行
                  line(lambda: hb._priced_wait_short(state_dir), "等回落"),
                  line(lambda: hb._watch_today_line(now=now, hint=False), "watch"),
                  line(lambda: disproof_line(snapshot), "反證"),
                  line(waits_line, "無到期的等待"),
                  line(lambda: hb._new_names_line(now=now, leads_path=leads_path, hint=False), "新點名")]
        try:
            drift = hb.llm_model_drift(record, now=now,
                                       record_dir=run_record_path.parent if run_record_path else None)
        except Exception:  # noqa: BLE001 — 比不了就不印這一條，不帶走健康度
            drift = None
        health = health_block(record=record, record_problem=record_problem,
                              quota=hb.quota_entries(rows, now=now), snapshot=snapshot, model_drift=drift)
        return ["**④ 狀態與健康度**", *status_lines(record=record, diff_lines=diff_lines, status=status), *health]

    blocks.append(guarded("① Lead 抓了什麼", leads_part))
    def rejected_titles() -> dict[str, str]:
        try:
            from engine_b import leads as leads_mod

            store = leads_mod.load(leads_path) if leads_path else leads_mod.load()
            ids = {str(r.get("lead_id")) for r in (receipt or {}).get("rejected") or () if isinstance(r, Mapping)}
            return {lid: str(((store.get("leads") or {}).get(lid) or {}).get("title") or "") for lid in ids}
        except Exception:  # noqa: BLE001 — 標題讀不到就印網址，不帶走整塊
            return {}

    def radar_states() -> dict[str, str]:
        try:
            from engine_b import leads as leads_mod

            store = leads_mod.load(leads_path) if leads_path else leads_mod.load()
            ids = {str(a.get("lead_id")) for a in (receipt or {}).get("accepted") or () if isinstance(a, Mapping)}
            return {lid: str(((store.get("leads") or {}).get(lid) or {}).get("status") or "") for lid in ids}
        except Exception:  # noqa: BLE001 — 讀不到就印「lead 不在」，不帶走整塊
            return {}

    blocks.append(guarded("② 市場大事", lambda: events_block(
        digest=digest, receipt=receipt, digest_problem=digest_problem, radar_problem=radar_problem,
        recent_accepted=recent_radar_accepted(heartbeat_dir, today), lead_titles=rejected_titles(), impact=impact,
        lead_states=radar_states())))
    blocks.append(guarded("③ 待你決定", decisions_part))
    blocks.append(guarded("④ 狀態與健康度", status_part))
    def todo_part() -> list[str]:
        try:
            nxt = next_step_line(snapshot=snapshot, ledger=ledger, now=now)
        except Exception as exc:  # noqa: BLE001 — 下一步組不出來不帶走 ⑤
            nxt = f"組不出來（{type(exc).__name__}）——看上面哪一格不是 0"
        return todo_block(snapshot, ledger, nxt)

    blocks.append(guarded("⑤ 下一次研究要做的", todo_part))
    if digest:
        blocks.append(["_TL;DR 與「可能有關／無關」是 LLM 寫的提議、每句指得回當天的 lead；判定只在互動 session。_"])
    return "\n\n".join("\n".join(block) for block in blocks).rstrip() + "\n"


__all__ = ["RADAR_SCOPE_WORDS", "RESEARCH_TERMINAL_STATES", "SOURCE_LABELS", "TODO_COUNTERS", "compose_brief",
           "decisions_block", "disproof_line", "documents_block", "events_block", "health_block", "impact_total_line",
           "impact_touch_lines", "leads_block", "processing_line", "status_lines", "todo_block"]
