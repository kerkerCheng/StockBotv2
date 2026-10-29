"""候選狀態板的契約與純函式（Phase 3 Step 3.6）——**零 I/O**。

推導本身（要讀 watch registry、讀圖對圖、Engine C、Sheet）住 `alpha/providers/candidates.py`；這裡只放：
封閉字彙、首屏三個字、滯留天數、Sheet 持有的索引、整板組裝、rollup。

⚠ 為什麼拆成兩個模組（2026-09-29 3.6 審查）：字彙原本住 providers，於是心跳與 APP 的 fake payload 一 import 字彙，
就經 `alpha/providers/__init__` 把 Neo4j provider、Engine C、yfinance、requests 全載進來——心跳 import 期多了一整串會失敗的
相依，而且請求路徑測試的「request path 不得載入模型／IO 模組」哨兵在 fixture 階段就被預載瞎掉（通過與失效同形，L13）。

封閉字彙：五組 `GROUPS`（可開／缺 X／已定價等回落／不要／已持有）＋四個附組 `SIDE_GROUPS`
（非倍率候選／邊緣無法量／舊版／前提失效）。**組內按 ticker 字母**；沒有分數、沒有名次（AGENTS 消費契約）。
可開為零就零——讓它非空的路是研究，不是放寬任何一條前提（硬約束 7）。
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, NamedTuple, Sequence

from .narrative.contracts import RECORD_VERSION_V2, InvestorBrief
from .three_questions import rollup as line_rollup

GROUPS: tuple[str, ...] = ("open", "missing", "priced_wait", "pass", "held")
GROUP_LABELS: Mapping[str, str] = {"open": "可開", "missing": "缺 X", "priced_wait": "已定價等回落",
                                   "pass": "不要", "held": "已持有"}
SIDE_GROUPS: tuple[str, ...] = ("not_multiple", "edge_unmeasurable", "legacy", "precondition_failed")
SIDE_LABELS: Mapping[str, str] = {"not_multiple": "非倍率候選", "edge_unmeasurable": "邊緣無法量",
                                  "legacy": "舊版（缺候選狀態）", "precondition_failed": "前提失效"}
#: 首頁（單檔判讀清單）的分組（2026-10-07 使用者指示）：候選板同一組字＋兩個出口——沒寫敘事、這次沒讀到（L12：兩件事）。
#: **順序是閱讀順序，不是名次**：研究時間花最多的在上（已持有、可開、缺 X、等回落——Phase 7 A4「深度」壓在這裡），
#: 敘事要重寫的其次，判斷過「不要」的在最後；組內一律 ticker 字母序（AGENTS：不得輸出跨檔全序）。
#: 沒有敘事分兩組（2026-10-28 使用者：「還沒寫敘事」讓 104 檔非邊緣看起來像待做）：`no_narrative`＝邊緣或量不到、
#: 該寫還沒寫（研究待做）；`not_edge_no_narrative`＝非邊緣、規定不寫（不是待做，放在「不要」之後）。
LIST_GROUPS: tuple[str, ...] = ("held", "open", "missing", "priced_wait", "precondition_failed", "legacy",
                                "edge_unmeasurable", "no_narrative", "not_multiple", "pass", "not_edge_no_narrative",
                                "unavailable")
LIST_GROUP_LABELS: Mapping[str, str] = {**GROUP_LABELS, **SIDE_LABELS, "no_narrative": "還沒寫敘事（邊緣，該寫）",
                                        "not_edge_no_narrative": "不寫敘事（非邊緣）",
                                        "unavailable": "候選狀態這次沒讀到"}
#: 成績單 paper 線「現在」的狀態除了 GROUPS，還有兩個出口（`scripts/outcome_if_settled_today.py` 寫這兩個鍵）。
#: 標籤住這裡、經 `.meta.json` 跟著資料走到畫面（L16）——2026-10-28 之前追蹤表直接印英文鍵（`pass → retracted`）。
PAPER_STATE_EXITS: Mapping[str, str] = {"retracted": "敘事已撤回", "legacy_v1": "現行是舊版敘事（沒有候選狀態）"}
#: 敘事宣告的兩題 → 首屏三個字（§8 第 1 點）；v1 或沒有敘事一律「未答」。
ANSWER_WORDS: Mapping[str, str] = {"yes": "是", "no": "否", "unmeasurable": "無法量"}
UNANSWERED = "未答"
#: 會死嗎：四盞燈的最差色與灰燈數（燈不是數字）。顏色字彙＝`alpha.wipeout` 的輸出。
LIGHT_ORDER: tuple[str, ...] = ("red", "amber", "green")
LIGHT_WORDS: Mapping[str, str] = {"red": "紅", "amber": "黃", "green": "綠"}
#: 「該重寫」的三種狀態（`engine_b.queue_segments.narrative_rewrite_state` 的值）→ 人讀。
REWRITE_STATE_WORDS: Mapping[str, str] = {"fired": "醒來", "touched": "觸及", "expired": "到期未判"}
#: 敘事落後於讀圖與圖的兩種原因（ROADMAP「敘事 stale 計數器」①③，2026-10-29）——`rewrite[]` 那一條的開頭。
#: 寫的一方（`alpha.providers.candidates.derive_row`）與分類的一方（`REWRITE_WHY`）共用這兩個字串（L16）。
RIDES_SUPERSEDED_PREFIX = "騎的讀圖已換版"
NEW_EDGES_PREFIX = "圖上有新邊、敘事沒讀過"
#: 候選列 `rewrite[]` 每一條 → 首頁卡片與個股頁那一行的幾個字（2026-10-29 使用者：「該重寫為啥沒寫…可以五字一目瞭然嗎」）。
#: 依序比對、先中先贏；原句（含 watch 編號）照舊留在 `rewrite[]`，這裡只分類、不改判斷；認不得的歸「其他」，不丟（INV-3）。
REWRITE_WHY: tuple[tuple[str, str], ...] = (
    (RIDES_SUPERSEDED_PREFIX, "騎舊讀圖"), (NEW_EDGES_PREFIX, "新邊沒讀"),
    ("連結 ", "連結斷了"), ("觸及", "條件觸及"), ("醒來", "條件醒了"), ("到期", "到期了"), ("已到", "重看日到了"),
    ("不存在", "等待不見了"), ("在等的 watch 已", "等待結束了"),
)


def rewrite_words(rewrite: Iterable[str] | None) -> list[str]:
    """`rewrite[]` 的原句 → 幾個字（同一種原因多條寫「× N」）。順序照第一次出現（不是名次）。"""
    counts: dict[str, int] = {}
    for text in rewrite or ():
        text = str(text)
        word = next((w for key, w in REWRITE_WHY
                     if (text.startswith(key) if key == "連結 " else key in text)), "其他")
        counts[word] = counts.get(word, 0) + 1
    return [f"{word} × {n}" if n > 1 else word for word, n in counts.items()]
PRICED_IN_LINES: tuple[str, ...] = ("own_history_pctile", "cohort_median", "rel_return_30d", "rel_return_90d")
#: 營收序列與占比序列（2026-10-14 拆成兩行，L12）：任一行有值，「出現在數字裡了嗎」就量得到。
IN_NUMBERS_LINES: tuple[str, ...] = ("in_numbers_series", "in_numbers_mix_series")
WIPEOUT_LINES: tuple[str, ...] = ("wipeout_cash_runway", "wipeout_debt", "wipeout_dilution", "wipeout_going_concern")

#: 這份板**不是什麼**——隨 artifact 出門，畫面永遠印得出來。
CANDIDATES_THIS_IS_NOT: tuple[str, ...] = (
    "不是排序、沒有名次：組內按 ticker 字母；可開是每檔各自過的前提，不是分數，可同時多檔，也可以是 0。",
    "不給部位尺寸：買多少、什麼時候買由使用者自行判斷並手動下單。",
    "宣告來自敘事（研究 session 寫的 append-only ledger）；「已持有」來自 Sheet；本板每天重算，不寫任何 authority。",
    "本檔標的高度集中於當前題材：N 檔不等於 N 個獨立機會。",
)


def cap_label(value: Any) -> str | None:
    """市值顯示字串（前端不做任何算術，連 ÷1e9 都不做；`tests/test_webapp_api.py` 守著）。"""
    try:
        return f"{float(value) / 1e9:.1f}B USD" if value is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 已持有（Sheet）
# ---------------------------------------------------------------------------

def held_index(resolution: Mapping[str, Any] | None, *, is_beta: Callable[[str], bool],
               failure: str | None = None, ignored: Mapping[str, Mapping[str, Any]] | None = None,
               ignored_problem: str | None = None) -> dict[str, Any]:
    """`portfolio.holdings.resolve_holdings()` 的結果 → 候選板用的「已持有」：**alpha、股數 > 0、解析得到**。

    - `resolution=None`＝Sheet 讀不到；**`rows` 是空的也一樣**（Sheet 分頁清空時 `fetch_portfolio` 回 [] 不丟例外；
      真實帳戶至少有現金列，空表只可能是讀取失敗——硬擋對同一份 [] 回 unmeasurable，這裡不得反過來判「持有 0」）。
      整板暫停已持有判定（`upstream_unavailable`），不得把「沒讀到」當成「沒持有」。
    - beta 由 `risk/hard_caps.py` 的公開判別排除（alpha／beta 同一條線）；beta 列、現金列、股數 0 的列解析不到
      都不算進「解析不到」——它們不是要人決定的 identity 問題。
    - `ignored`：`portfolio.holdings.load_ignored()` 的名單（使用者明確決定不研究，Phase 4 Step 4.7b）——解析不到的列
      若在名單上，改列 `ignored[]`（附 reason／decided_at），也不算「解析不到」；`ignored_problem`（名單讀不到）照帶出去。"""
    names = dict(ignored or {})
    rows = list((resolution or {}).get("rows") or ())
    if resolution is None or not rows:
        why = failure or ("Sheet 沒有任何可解析的持股列（連現金列都沒有）——視同讀不到" if resolution is not None
                          else "讀取失敗")
        return {"status": "upstream_unavailable",
                "reason": f"持股未讀到，已持有判定暫停（{why}）——其餘列的宣告照印，但標「持股未驗」",
                "by_company": {}, "unresolved": [], "ignored": [], "ignored_problem": ignored_problem,
                "beta_excluded": 0, "zero_shares": 0}
    by_company: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []
    skipped: dict[str, dict[str, Any]] = {}
    beta_excluded = zero_shares = 0
    for row in rows:
        if row.get("cash"):
            continue
        if is_beta(str(row.get("ticker") or "")):
            beta_excluded += 1
            continue
        if not (row.get("shares") or 0) > 0:
            zero_shares += 1
            continue
        if not row.get("company_id"):
            ticker = str(row.get("ticker"))
            if ticker.upper() in names:
                skipped[ticker.upper()] = dict(names[ticker.upper()])
            else:
                unresolved.append(ticker)
            continue
        by_company[str(row["company_id"])] = {"sheet_ticker": row.get("ticker"), "source": row.get("source")}
    return {"status": "ok", "reason": None, "by_company": by_company, "unresolved": sorted(set(unresolved)),
            "ignored": [skipped[t] for t in sorted(skipped)], "ignored_problem": ignored_problem,
            "beta_excluded": beta_excluded, "zero_shares": zero_shares}


# ---------------------------------------------------------------------------
# 三個字、滯留
# ---------------------------------------------------------------------------

def three_words(three_questions: Mapping[str, Any] | None, brief: InvestorBrief | None,
                *, not_read: str = "未讀到") -> dict[str, str]:
    """首屏三個字：會死嗎＝四盞燈的最差色（＋灰燈數）；已定價嗎／出現在數字裡＝敘事的宣告。"""
    if three_questions is None:
        will = not_read
    else:
        values = [r.get("value") for r in three_questions.get("will_it_die") or ()]
        grey = sum(1 for v in values if v not in LIGHT_ORDER)
        worst = next((c for c in LIGHT_ORDER if c in values), None)
        will = (LIGHT_WORDS[worst] + (f"（灰 {grey}）" if grey else "")) if worst else f"灰 {grey}"
    answers = brief.answers if brief is not None and brief.record_version == RECORD_VERSION_V2 else None
    return {"will_it_die": will,
            "priced_in": ANSWER_WORDS[answers.priced_in] if answers else UNANSWERED,
            "in_numbers": ANSWER_WORDS[answers.in_numbers] if answers else UNANSWERED}


def _walk_back(records: Sequence[InvestorBrief], brief: InvestorBrief,
               same: Callable[[InvestorBrief], bool]) -> InvestorBrief:
    """沿 `supersedes` 鏈往回，回傳 `same` 連續成立的最早那一版（滯留與已定價判斷日共用這一條路，L16）。
    **撤回打斷連續**：撤回用**時間**判，不看鏈上有沒有經過撤回紀錄——新版可以直接 supersede 被撤的那一筆（撤回紀錄
    本身不在鏈上），所以只要兩筆之間有任何一筆撤回紀錄落在 (prev, cur] 之間，那段時間就沒有生效的宣告。"""
    by_id = {r.brief_id: r for r in records}
    retractions = [r.created_at for r in records if r.retracted]
    cur, seen = brief, {brief.brief_id}
    while cur.supersedes_id and cur.supersedes_id in by_id and cur.supersedes_id not in seen:
        prev = by_id[cur.supersedes_id]
        seen.add(prev.brief_id)
        if prev.retracted or prev.record_version != RECORD_VERSION_V2 or not same(prev) \
                or any(prev.created_at < t <= cur.created_at for t in retractions):
            break
        cur = prev
    return cur


def stall_version(records: Sequence[InvestorBrief], brief: InvestorBrief) -> InvestorBrief:
    """**連續宣告同一 state** 的最早那一版（缺 X／等回落另要求同一 watch）——同 state 重寫不歸零；撤回打斷連續。"""
    state = brief.candidate_state.state if brief.candidate_state else None
    watch = brief.candidate_state.watch_id if brief.candidate_state else None

    def same(prev: InvestorBrief) -> bool:
        cs = prev.candidate_state
        return cs is not None and cs.state == state and (state not in ("missing", "priced_wait") or cs.watch_id == watch)

    return _walk_back(records, brief, same)


def stall_since(records: Sequence[InvestorBrief], brief: InvestorBrief) -> datetime:
    """沿 `supersedes` 鏈往回，取**連續宣告同一 state** 的最早一筆 `created_at`——撤回之後到重寫之前那段「沒有宣告」，
    不算進滯留。"""
    return stall_version(records, brief).created_at


# ---------------------------------------------------------------------------
# 已定價變動（ROADMAP 已定價變動常駐計數器；failure log #94）：只印不判——不設門檻、不亮燈、不改候選狀態
# ---------------------------------------------------------------------------

def priced_judgment_key(brief: InvestorBrief) -> tuple[Any, ...]:
    """「已定價判斷」的鍵：priced_in 那一格的文字、答案、候選狀態、歷史不可比宣告（換一把尺）；**理由與在等的 watch
    只在等回落時算進來**（等回落的價格理由寫在 reason 裡）。換騎、只換引用都不改這個鍵，所以不算改判。
    2026-10-21 使用者照推薦：缺 X／不要的理由多半是客戶、量級這類證據，改字就讓判斷日歸零會把「判斷日以來」縮短
    （R2 回放：9 列受影響，例 3363 判斷日以來 −2.6%，只看已定價那一格是 10-06 起 −22.1%）。"""
    slot = brief.slot("priced_in")
    cs = brief.candidate_state
    state = (cs.as_dict() if cs.state == "priced_wait" else {"state": cs.state}) if cs is not None else None
    return (slot.text if slot else None, brief.answers.priced_in if brief.answers else None, state,
            brief.history_not_comparable.as_dict() if brief.history_not_comparable else None)


def judgment_version(records: Sequence[InvestorBrief], brief: InvestorBrief) -> InvestorBrief:
    """最後一次真的改判的那一版（判斷鍵連續相同的最早一版）——換騎包裝成新日期的版本不算判斷日（2026-10-21：
    現行 73 份裡 23 份的現行版日期 ≠ 判斷日）。"""
    key = priced_judgment_key(brief)
    return _walk_back(records, brief, lambda prev: priced_judgment_key(prev) == key)


# ---------------------------------------------------------------------------
# 敘事落後於圖（ROADMAP「敘事 stale 計數器」③；2026-10-29 使用者 go）：公司在正文寫完之後有新邊，敘事沒讀過那份文件
# ---------------------------------------------------------------------------

def body_key(brief: InvestorBrief) -> tuple[Any, ...]:
    """敘事「正文」的鍵：七格原文＋候選狀態與理由。換騎、只改引用、改 answers 都不改它——換騎包裝成的新版不算重寫過正文。"""
    cs = brief.candidate_state
    return (tuple((s.key, s.text) for s in brief.slots), (cs.state, cs.reason) if cs is not None else None)


def body_version(records: Sequence[InvestorBrief], brief: InvestorBrief) -> InvestorBrief:
    """正文最後一次改動的那一版（正文鍵連續相同的最早一版；與滯留、判斷日走同一條鏈，L16）。"""
    key = body_key(brief)
    return _walk_back(records, brief, lambda prev: body_key(prev) == key)


def normalize_url(url: Any) -> str | None:
    """同一份文件的網址比對用：去掉 scheme、`www.`、錨點與結尾斜線，主機名小寫；不是 http(s) 網址回 None。"""
    match = re.match(r"(?i)^https?://(.+)$", str(url or "").strip().rstrip(".,;:。，；："))
    if not match:
        return None
    host, sep, path = match.group(1).split("#")[0].rstrip("/").partition("/")
    host = host.lower().removeprefix("www.")
    return host + (sep + path if path else "")


_QUOTE_MARKS = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


def squash(text: Any) -> str:
    """逐字比對用：拿掉所有空白（PDF 抽字的換行與字間空格）、彎引號換直的、小寫。"""
    return re.sub(r"\s+", "", str(text or "")).translate(_QUOTE_MARKS).lower()


class Cited(NamedTuple):
    """敘事七格引用過的東西。`raw_refs` 只是路徑——讀檔是 provider 的事（本模組零 I/O）。"""

    docs: frozenset[str]
    urls: frozenset[str]
    edges: frozenset[tuple[str, str, str]]
    raw_refs: tuple[str, ...]


def cited_identities(brief: InvestorBrief) -> Cited:
    """`graph://source/<doc_id>` → doc id；`graph://edge/<src>/<relation>/<dst>` → 那條邊；直接寫網址 → 網址；
    `library/raw/<檔>` → 檔名（去副檔名）當 doc id，路徑另外收進 `raw_refs`（比逐字用，見 `unread_new_edges`）。"""
    docs: set[str] = set()
    urls: set[str] = set()
    edges: set[tuple[str, str, str]] = set()
    raw: list[str] = []
    for slot in brief.slots:
        for ref in slot.evidence_refs:
            ref = str(ref).strip().split("#")[0]
            if ref.startswith("graph://source/"):
                docs.add(ref.removeprefix("graph://source/"))
            elif ref.startswith("graph://edge/"):
                parts = ref.removeprefix("graph://edge/").split("/")
                if len(parts) == 3:
                    edges.add((parts[0], parts[1], parts[2]))
            elif ref.startswith("library/raw/"):
                docs.add(ref.rsplit("/", 1)[-1].rsplit(".", 1)[0])
                if ref not in raw:
                    raw.append(ref)
            elif (url := normalize_url(ref)) is not None:
                urls.add(url)
    return Cited(frozenset(docs), frozenset(urls), frozenset(edges), tuple(raw))


def _written_at(value: Any) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return stamp if stamp.tzinfo is not None else stamp.replace(tzinfo=timezone.utc)


def _read(row: Mapping[str, Any], cited: Cited, cited_text: str) -> bool:
    """這一筆 assertion 敘事讀過嗎：文件 id 引過、網址直接引過，或**它的逐字至少一段在敘事引過的 raw 檔裡**。"""
    if str(row.get("doc_id")) in cited.docs or (normalize_url(row.get("url")) or "") in cited.urls:
        return True
    return any(q and q in cited_text for q in (squash(x) for x in row.get("quotes") or ()))


def unread_new_edges(assertions: Iterable[Mapping[str, Any]], *, since: datetime, cited: Cited,
                     cited_text: str = "") -> list[dict[str, Any]]:
    """公司在正文寫完（`since`）之後有寫入、而且敘事沒讀過的邊——一條邊一筆。

    「讀過」以**邊**為單位：那條邊任何一筆 assertion（不論何時寫入）讀過（`_read`），或敘事直接引用了那條邊——同一輪研究
    先寫敘事、隨後入圖，邊的來源敘事都引過（2026-10-29 量測 4 份），不是落後。`cited_text`：敘事引過的 raw 檔全文
    （`squash` 過）。**比逐字、不比網址**：raw 是節錄，同一個網址常有好幾份——9856.HK 引了招股書的一段節錄，10-20 入圖的
    是同一份招股書的另一段（LPO、LRO 在那裡，敘事沒寫）；3110.T、KSHINTL.NS 檔名不同、邊的逐字就在敘事引的檔裡（讀過）。
    `docs` 只列 `since` 之後寫入的那幾份（要去讀的）。寫入時間讀不懂的當作新的（往看得見那邊倒，INV-3）。
    順序：最早寫入時間、再依邊——不是名次。"""
    since = since if since.tzinfo is not None else since.replace(tzinfo=timezone.utc)
    by_edge: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for a in assertions:
        by_edge.setdefault((str(a.get("src")), str(a.get("relation")), str(a.get("dst"))), []).append(a)
    out: list[dict[str, Any]] = []
    for key, rows in by_edge.items():
        new = [(r, _written_at(r.get("updated_at"))) for r in rows]
        new = [(r, t) for r, t in new if t is None or t > since]
        if not new or key in cited.edges:
            continue
        if any(_read(r, cited, cited_text) for r in rows):
            continue
        stamps = [t for _, t in new if t is not None]
        out.append({"src": key[0], "relation": key[1], "dst": key[2],
                    "at": min(stamps).isoformat() if stamps else None,
                    "docs": sorted({str(r.get("doc_id")) for r, _ in new if r.get("doc_id")})})
    return sorted(out, key=lambda e: (e["at"] or "", e["src"], e["relation"], e["dst"]))


def new_edge_reason(edge: Mapping[str, Any]) -> str:
    """`rewrite[]` 那一條：哪條邊、哪天寫入、要讀哪幾份文件（L18：標籤指得回原始證據）。"""
    day = str(edge.get("at") or "")[:10] or "時間不明"
    docs = "、".join(edge.get("docs") or ()) or "不明"
    return f"{NEW_EDGES_PREFIX}：{edge.get('src')} -{edge.get('relation')}-> {edge.get('dst')}（{day} 寫入；文件 {docs}）"


def rides_reason(ride: Mapping[str, Any]) -> str:
    """`rewrite[]` 那一條：騎的那份讀圖、它在哪一格、現行是哪一份。"""
    return (f"{RIDES_SUPERSEDED_PREFIX}：{ride.get('reading_id')}（{ride.get('node')}；"
            f"現行 {ride.get('current_reading_id') or '不明'}）")


def _signed_pct(value: float) -> str:
    return f"{value * 100:+.1f}%".replace("-", "−")


def _point(row: Mapping[str, Any] | None) -> str:
    if not row or row.get("value") is None:
        return f"量不到（{(row or {}).get('absence_kind') or '未讀到'}）"
    return f"第 {float(row['value']):.1f}"


def _then_point(row: Mapping[str, Any] | None, source: str | None) -> str:
    """當時的值＋它是哪一根收盤、怎麼來的（回算或寫入時記下）——兩個數字並列時才分得出哪個是當時看到的（R2）。"""
    if not row or row.get("value") is None:
        return _point(row)
    how = "回算" if source == "recomputed" else "寫入時記下"
    return f"{_point(row)}（{str(row.get('as_of') or '')[5:10]} 收盤，{how}）"


def priced_since(ticker: str, brief: InvestorBrief, judged: InvestorBrief, *, judgment_day: Any,
                 then: Mapping[str, Any] | None, then_source: str, now: Mapping[str, Any] | None,
                 return_since: float | None, wait: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """一檔「判斷日 vs 今天」的列與一句話（候選板、心跳、短版共用這句——前端與心跳不組字，L16）。

    `then`／`now`：自家三年百分位那一行（`{value|absence_kind, basis, as_of}`）；`then_source`＝`recorded`（寫入端記下的）
    或 `recomputed`（舊版本：判斷日前一天收盤點時回算，與寫入當時看到的可能不同）。`wait`：等回落起點與判斷日不同時
    `{day, then, return}`。只在答 yes／no、宣告等回落、或答量不到而今天有值時回列；其餘回 None。"""
    answer = brief.answers.priced_in if brief.answers else None
    state = brief.candidate_state.state if brief.candidate_state else None
    now_valued = bool(now) and now.get("value") is not None
    if answer not in ("yes", "no") and state != "priced_wait" and not (answer == "unmeasurable" and now_valued):
        return None
    day = str(judgment_day)[5:10]
    label = ("等回落" if state == "priced_wait" else {"yes": "已定價答是", "no": "已定價答否"}.get(str(answer), "答量不到"))
    then_basis, now_basis = (then or {}).get("basis"), (now or {}).get("basis")
    then_text = _then_point(then, then_source)
    now_text = _point(now) + (f"（{str((now or {}).get('as_of') or '')[5:10]} 收盤）" if now_valued else "")
    if then_basis and now_basis and then_basis != now_basis:
        basis = f"判斷時 {then_basis}、今天 {now_basis}——兩把尺"
    else:
        basis = "自家三年" + (f" {now_basis or then_basis}" if (now_basis or then_basis) else "")   # 兩邊都沒口徑不印 None
    line = f"{label} {ticker}｜判斷日 {day}：{basis} {then_text} → 今天 {now_text}"
    if return_since is not None:
        line += f"｜判斷日以來 {_signed_pct(return_since)}（調整後收盤）"
    if wait:
        line += (f"｜等回落自 {str(wait.get('day'))[5:10]}（同一筆等待）：{_then_point(wait.get('then'), wait.get('then_source'))}"
                 + (f"、{_signed_pct(wait['return'])}" if wait.get("return") is not None else ""))
    return {"answer": answer, "state": state, "judgment_brief_id": judged.brief_id, "judgment_day": str(judgment_day),
            "then": dict(then or {}), "then_source": then_source, "now": dict(now or {}),
            "return_since": return_since, "wait_since": dict(wait) if wait else None, "line": line}


# ---------------------------------------------------------------------------
# 整板與 rollup
# ---------------------------------------------------------------------------

def _any_line_counts(read: Sequence[Mapping[str, Any]], question: str, keys: Sequence[str]) -> dict[str, int]:
    """一題有幾行可以回答它（例：營收序列或占比序列）：任一行有值算有值；都缺席時記第一行（主行）的缺席 kind。"""
    bucket: dict[str, int] = {}
    for tq in read:
        rows = [r for r in tq.get(question) or () if r.get("key") in keys]
        if any(r.get("absence_kind") is None for r in rows):
            kind = "value"
        else:
            kind = next((str(r.get("absence_kind")) for r in rows if r.get("key") == keys[0]), "no_line")
        bucket[kind] = bucket.get(kind, 0) + 1
    return bucket


def _absence_counts(bucket: Mapping[str, int] | None, not_read: int) -> dict[str, Any]:
    bucket = dict(bucket or {})
    valued = int(bucket.pop("value", 0))
    absent = {k: int(v) for k, v in bucket.items()}
    if not_read:
        absent["not_read"] = absent.get("not_read", 0) + not_read
    return {"valued": valued, "absent": dict(sorted(absent.items())), "absent_total": sum(absent.values())}


def rollup(three_questions_by_ticker: Mapping[str, Mapping[str, Any] | None],
           edges: Mapping[str, Mapping[str, Any]], *,
           not_read_reasons: Mapping[str, str] | None = None) -> dict[str, Any]:
    """宇宙每一檔的三題與四盞燈 rollup——**只數有值與依 kind 的缺席，不是結論**。

    逐行計數沿用 `alpha.three_questions.rollup`（Step 3.3 的那一份，不另算；L16）。四盞燈另外給
    **盞數**（紅／黃／綠／**灰＝沒量到**，灰依 kind 分）與「有紅燈的檔」——「一檔亮四盞」與「四檔各亮一盞」
    是兩件事（ARCHITECTURE §4.1 段 4）；⚠ 灰不是綠。讀不到三題的檔記 `not_read` 並帶理由（INV-3）。"""
    tqs = dict(three_questions_by_ticker)
    read = [tq for tq in tqs.values() if tq is not None]
    not_read = [t for t, tq in tqs.items() if tq is None]
    lines = line_rollup(read)
    lamps: dict[str, int] = {"red": 0, "amber": 0, "green": 0, "unlit": 0}
    unlit_by_kind: dict[str, int] = {}
    red_tickers: list[str] = []
    all_four = 0
    for ticker, tq in tqs.items():
        if tq is None:
            continue
        rows = list(tq.get("will_it_die") or ())
        for r in rows:
            v = r.get("value")
            if v in LIGHT_ORDER:
                lamps[v] += 1
            else:
                lamps["unlit"] += 1
                k = str(r.get("absence_kind") or "unlit")
                unlit_by_kind[k] = unlit_by_kind.get(k, 0) + 1
        if any(r.get("value") == "red" for r in rows):
            red_tickers.append(ticker)
        if rows and all(r.get("value") in LIGHT_ORDER for r in rows):
            all_four += 1
    edge_counts: dict[str, int] = {}
    for e in edges.values():
        k = str((e or {}).get("state") or "unmeasurable")
        edge_counts[k] = edge_counts.get(k, 0) + 1
    reasons = dict(not_read_reasons or {})
    return {
        "universe": len(tqs),
        "lines": {k: dict(v) for k, v in sorted(lines.items())},
        "priced_in_own": _absence_counts(lines.get("own_history_pctile"), len(not_read)),
        "in_numbers": _absence_counts(_any_line_counts(read, "in_numbers", IN_NUMBERS_LINES), len(not_read)),
        "wipeout": {"companies": len(read), "lamps": lamps, "unlit_by_kind": dict(sorted(unlit_by_kind.items())),
                    "red_tickers": sorted(red_tickers), "all_four_non_grey": all_four},
        "not_read": {"n": len(not_read), "tickers": sorted(not_read),
                     "reasons": {t: reasons.get(t, "（沒有留下理由）") for t in sorted(not_read)}},
        "edge": dict(sorted(edge_counts.items())),
    }


def assemble_board(rows: Sequence[Mapping[str, Any] | None], *, universe: Sequence[str], held: Mapping[str, Any],
                   narrative_rewrite: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """逐檔的列 → 五組＋附組＋計數（含 0）＋各組最老滯留。**組內按 ticker 字母**。

    `narrative_rewrite`：整板「敘事該重寫」的清單（連結斷了＋敘事來源 watch 醒來／觸及／到期未判），每筆帶 `kind`。"""
    groups: dict[str, list[dict[str, Any]]] = {g: [] for g in GROUPS}
    sides: dict[str, list[dict[str, Any]]] = {s: [] for s in SIDE_GROUPS}
    no_narrative = 0
    for row in rows:
        if row is None:
            no_narrative += 1
            continue
        if row.get("group"):
            groups[row["group"]].append(dict(row))
        elif row.get("side"):
            sides[row["side"]].append(dict(row))
    for bucket in (*groups.values(), *sides.values()):
        bucket.sort(key=lambda r: str(r.get("ticker")))
    held_ok = held.get("status") == "ok"
    counts = {**{g: (len(groups[g]) if (g != "held" or held_ok) else None) for g in GROUPS},
              **{s: len(sides[s]) for s in SIDE_GROUPS}, "no_narrative": no_narrative}
    oldest = {g: max((r["stall_days"] for r in groups[g] if isinstance(r.get("stall_days"), int)), default=None)
              for g in ("open", "missing", "priced_wait")}
    return {"groups": groups, "side_groups": sides, "counts": counts, "oldest_stall_days": oldest,
            "universe": sorted(universe),
            "holdings": {"status": held.get("status"), "reason": held.get("reason"),
                         "unresolved": list(held.get("unresolved") or ()),
                         "ignored": [dict(i) for i in held.get("ignored") or ()],
                         "ignored_problem": held.get("ignored_problem"),
                         "beta_excluded": held.get("beta_excluded"), "zero_shares": held.get("zero_shares")},
            "narrative_rewrite": [dict(b) for b in narrative_rewrite]}


__all__ = ["ANSWER_WORDS", "CANDIDATES_THIS_IS_NOT", "GROUPS", "GROUP_LABELS", "IN_NUMBERS_LINES", "LIGHT_ORDER",
           "LIGHT_WORDS", "LIST_GROUPS", "LIST_GROUP_LABELS", "NEW_EDGES_PREFIX", "PRICED_IN_LINES",
           "REWRITE_STATE_WORDS", "REWRITE_WHY", "RIDES_SUPERSEDED_PREFIX", "SIDE_GROUPS", "SIDE_LABELS", "UNANSWERED",
           "WIPEOUT_LINES", "Cited", "assemble_board", "body_key", "body_version", "cap_label", "cited_identities",
           "held_index", "judgment_version", "new_edge_reason", "normalize_url", "priced_judgment_key", "priced_since",
           "rewrite_words", "rides_reason", "rollup", "squash", "stall_since", "stall_version", "three_words",
           "unread_new_edges"]
