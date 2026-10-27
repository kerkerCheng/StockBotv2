"""語意預篩（Phase 1 Step 1.4；C7）：daily 的 ⑩a／⑩c——程式抓全文、程式驗證 LLM 的標旗提議。

**預篩只標旗、不判定**（G7）：`semantic_flag` 是給互動 session 讀的提示，不改 watch 狀態、不減少「未檢 N」，
判定只在互動（`event_watch judge`）。LLM（⑩b，`claude -p` 零工具）只看得到程式塞進 prompt 的條件原文與全文。

2026-10-27（failure log #96）起也預篩**擋下的追源／讀圖叫醒**（`event_watch.wake_screen`）：條件由 `wake_condition`
組（追源讀停放時寫的觸發條件、讀圖讀節點）。標旗只決定放不放行——標「可能觸及」「看不出」交給原 consumer，
標「無關」仍擋著等互動 `wake-judge` 確認；狀態照樣不在這裡改。

- ⑩a `prepare`：選 `fired`、語意型、且對「這一次叫醒它的 lead」還沒有標旗的 watch，加上擋下還沒預篩的叫醒；
  照（醒來時間、觸發文件）排，同一份文件叫醒的排在一起。
  **先排除觸發 lead 的來源沒有 fetcher 的**（計數 `no_fetcher`，**不佔名額**——否則它們每天被重選、永遠抓不到，
  可能吃光名額；第 4 輪 N4-10）。其餘逐份抓全文，**抓到的才進批次、才算名額**；名額＝
  `semantic_screen_daily_limit` **份文件**扣掉**當日**已看過的份數（手動重跑不得超過 G7 的每日硬上限；
  #96 前是條數——一份 Sivers 股東會通知叫醒 35 條，花錢的是那一份全文，條數上限會讓它拖四天）。
  抓不到計數 `no_text`、不進批次、**不拿標題充數**；全文存 `library/private/semantic_text/<lead_id>.txt`，
  已存在就重用、不重抓。
- 全文來源：EDGAR 主文件（`www.sec.gov`，URL 就是主文件；6-K／8-K 另照索引頁 Type 欄抓 EX-99.x 附件、放在前面——
  2026-10-27 failure log #105：主文件只是封面）、MFN 公告頁（`mfn.se`，
  **只取公告頁文字、不抓 `mb.cision.com` 的附件、不寫 `out_dir`**——`fetchers/mfn.py:fetch_release` 會做那些事，
  所以不用它；第 4 輪 N4-8）、harvest 登記的一手 feed **同主機**的公司新聞頁（2026-10-27 #96；不新增對外主機、
  UA 不帶聯絡信箱）。MOPS 重訊與 X 貼文本來就有 `raw_text`，直接用。
- ⑩c `apply`：批次與結果的 `run_id` 相同且等於參數，否則一則都不寫；壞 JSON、沒有結果檔 → 一則都不寫、exit 非零；
  逐則驗 `(watch_id, lead_id)` 在本批、不重複、verdict 在封閉字彙內、`likely_touches` 必帶 quote 且
  quote 是存檔全文的**逐字子字串**（兩邊用同一個空白正規化；L18：標籤要指得回原文）——不合格的拒收並計數。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from engine_b import event_watch as ew

TEXT_DIR = Path("library/private/semantic_text")
#: 主文件常常只是封面、內容在附件 EX-99.x 的表單（failure log #105）；form_type 不明的也照抓附件。
EXHIBIT_FORMS = frozenset({"6-K", "8-K"})
_EDGAR_PATH = re.compile(r"^/Archives/edgar/data/(?P<cik>\d+)/(?P<acc>\d{10,20})/(?P<doc>[^/]+)$")


def normalize_whitespace(text: str | None) -> str:
    """引文比對的正規化——**只處理空白**（HTML 轉文字與 LLM 回的 quote 換行、空白數可能不同）。
    不做更寬的正規化：放寬解析 ≠ 放寬判準（L15）。"""
    return " ".join(str(text or "").split())


def parse_edgar_url(url: str) -> tuple[str, str, str] | None:
    """EDGAR lead URL（主文件）→ (cik, accession, primary_doc)。

    `xslF…` 路徑是持股申報的 XSL 呈現（Form 3／4／5），**明確缺席**：語意 watch 本來就排除持股申報，
    這裡再擋一次，不去抓一份 XML 樣式頁當全文。"""
    parts = urlsplit(str(url or ""))
    if parts.netloc != "www.sec.gov":
        return None
    path = parts.path
    if "/xslF" in path:
        return None
    match = _EDGAR_PATH.match(path)
    if not match:
        return None
    return match["cik"], match["acc"], match["doc"]


#: inline XBRL filing 轉文字後，前段是隱藏的 `ix:header`（taxonomy URL、context id）——2026-09-24 實測
#: 三份 10-Q 的封面分別在第 8.6k／23.9k／33.9k 字才開始，而預篩只取前 `prescreen_text_max_chars` 字。
_COVER_START = "UNITED STATES SECURITIES AND EXCHANGE COMMISSION"
#: 同一串字、字之間容許任何空白：2026-10-08 起 EDGAR 走共用文字化（區塊元素各自一行，failure log #5），封面常是
#: 「UNITED STATES」「SECURITIES AND EXCHANGE COMMISSION」兩個段落——不放寬就會找不到、整段表頭留在預篩的字數裡。
_COVER_START_RE = re.compile(r"\s+".join(map(re.escape, _COVER_START.split())))


def strip_xbrl_header(text: str | None) -> str | None:
    """從封面（`UNITED STATES SECURITIES AND EXCHANGE COMMISSION`，字間空白不拘）起算；找不到就原樣回傳（不猜）。
    只切掉前面的機器表頭，不動正文——引文比對仍對存檔的這一份做。"""
    if not text:
        return text
    match = _COVER_START_RE.search(text)
    return text[match.start():] if match and match.start() > 0 else text


def fetch_mfn_text(url: str, *, session: Any = None) -> str:
    """MFN 公告頁 → 正文文字。**只連 `mfn.se`**、不抓附件、不寫檔。"""
    from fetchers.mfn import _session, parse_release_page
    from fetchers.utils import rate_sleep

    if urlsplit(url).netloc != "mfn.se":
        raise ValueError(f"不是 mfn.se 的公告頁：{url}")
    http = session or _session()
    resp = http.get(url, timeout=30)
    resp.raise_for_status()
    rate_sleep()
    return str(parse_release_page(resp.text)["text"])


#: 公司自家新聞頁的 User-Agent——**不帶聯絡信箱**（harvest 的 `_UA` 帶，這條路不沿用）。
PAGE_UA = "StockBotv2 research (contact via repo owner)"
HARVEST_CONFIG = Path("crons/harvest_config.json")


def primary_feed_hosts(config_path: Path | None = None) -> dict[str, str]:
    """harvest 登記的一手 feed（MFN、EDGAR、MOPS 以外）→ 那個 feed 的主機。公司新聞頁只准連這些主機——
    harvest 本來就每天連，預篩不新增對外主機（#96：`sivers:press` 的股東會通知叫醒 20 則停放 lead，當時沒有 fetcher）。"""
    try:
        config = json.loads(Path(config_path or HARVEST_CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, str] = {}
    for feed in config.get("feeds") or ():
        source = str(feed.get("source") or "")
        if feed.get("source_class") == "primary" and not source.startswith(("mfn:", "edgar:", "mops:")):
            out[source] = urlsplit(str(feed.get("url") or "")).netloc
    return out


def fetch_page_text(url: str, *, opener: Callable[..., Any] | None = None) -> str:
    """公司新聞頁 → 文字（共用 `fetchers.utils.html_to_text`）。不抓附件、不寫 `out_dir`。"""
    from urllib.request import Request, urlopen

    from fetchers.utils import html_to_text, rate_sleep

    with (opener or urlopen)(Request(url, headers={"User-Agent": PAGE_UA}), timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    rate_sleep()
    return html_to_text(html)


def fetcher_for(lead: Mapping[str, Any]) -> Callable[[], str | None] | None:
    """這則 lead 有沒有取全文的方法。None＝沒有 fetcher（計 `no_fetcher`、不佔名額）。

    順序：MOPS 重訊自帶全文 → EDGAR 主文件 → MFN 公告頁 → harvest 一手 feed 同主機的公司新聞頁 →
    其他自帶 `raw_text` 的（X 貼文本身就是全文；只有 `related_entity_signal` 的追源叫醒會用到——語意 watch 只認一手）。"""
    source = str(lead.get("source") or "")
    url = str(lead.get("url") or "")
    if source.startswith("mops:") and str(lead.get("raw_text") or "").strip():
        return lambda: str(lead.get("raw_text"))
    if urlsplit(url).netloc == "www.sec.gov":
        parsed = parse_edgar_url(url)
        if parsed is None:
            return None
        exhibits = wants_exhibits(lead)

        def edgar() -> str | None:
            from fetchers.edgar import fetch_filing_exhibits, fetch_filing_text

            main = strip_xbrl_header(fetch_filing_text(*parsed))
            if not exhibits:
                return main
            # 附件放前面：分類只看前幾千字（failure log #105：6-K 主文件只是封面，新聞稿在 EX-99.1）
            parts = [f"【附件 {kind}｜{doc}】\n{text}" for kind, doc, text in fetch_filing_exhibits(parsed[0], parsed[1])]
            if main and main.strip():
                parts.append(f"【主文件｜{parsed[2]}】\n{main}")
            return "\n\n".join(parts) or None

        return edgar
    if urlsplit(url).netloc == "mfn.se":
        return lambda: fetch_mfn_text(url)
    host = primary_feed_hosts().get(source)
    if host and urlsplit(url).netloc == host and urlsplit(url).scheme == "https":
        return lambda: fetch_page_text(url)
    if str(lead.get("raw_text") or "").strip():
        return lambda: str(lead.get("raw_text"))
    return None


def _text_path(lead_id: str, text_dir: Path) -> Path:
    return Path(text_dir) / f"{lead_id}.txt"


def wants_exhibits(lead: Mapping[str, Any]) -> bool:
    """這則 lead 的全文要不要含 EX-99.x 附件：EDGAR 主文件、而且是 6-K／8-K 或 form_type 不明。"""
    if parse_edgar_url(str(lead.get("url") or "")) is None:
        return False
    form = str(lead.get("form_type") or "").upper().split("/")[0]
    return not form or form in EXHIBIT_FORMS


def cached_text(lead_id: str, lead: Mapping[str, Any], *, text_dir: Path = TEXT_DIR) -> str | None:
    """存檔的全文。沒存檔、或是 #105 之前只存了封面的 6-K／8-K（meta 沒有 `exhibits_checked`）回 None＝要重抓。

    2026-10-27 實測：GFS 10-14 6-K 的存檔 950 字，只有封面與「Exhibit 99.1 Press release」一行——預篩與分類讀到的都是它。
    重抓的新版仍逐字包含主文件（附件在前、主文件在後），已驗過的引文仍是子字串。"""
    path = _text_path(lead_id, text_dir)
    if not path.is_file():
        return None
    if wants_exhibits(lead):
        try:
            meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        if not meta.get("exhibits_checked"):
            return None
    return path.read_text(encoding="utf-8")


def load_or_fetch_text(lead_id: str, lead: Mapping[str, Any], *, text_dir: Path = TEXT_DIR,
                       fetch: Callable[[], str | None]) -> tuple[str | None, bool]:
    """(全文, 是否重用存檔)。已存檔（且不是只有封面的舊版，見 `cached_text`）就重用、不重抓；抓到空字串或失敗回 None。"""
    path = _text_path(lead_id, text_dir)
    cached = cached_text(lead_id, lead, text_dir=text_dir)
    if cached is not None:
        return cached, True
    try:
        text = fetch()
    except Exception as exc:  # noqa: BLE001 — 抓不到就是抓不到（計數），不得拿標題充數
        print(f"[prescreen] {lead_id} 抓全文失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
        return None, False
    if not text or not str(text).strip():
        return None, False
    Path(text_dir).mkdir(parents=True, exist_ok=True)
    path.write_text(str(text), encoding="utf-8")
    meta = {"lead_id": lead_id, "source_url": lead.get("url"),
            "sha256": hashlib.sha256(str(text).encode("utf-8")).hexdigest(),
            "chars": len(str(text)), "fetched_at": datetime.now(timezone.utc).isoformat(),
            "exhibits_checked": wants_exhibits(lead)}
    path.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    return str(text), False


def _local_date(stamp: str | None) -> str:
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def documents_screened_today(data: Mapping[str, Any], *, today: str | None = None) -> int:
    """當日已標過旗的**文件**份數（觸發 lead 去重）——每日上限的單位（#96：一份文件叫醒 35 條，花錢的是那份全文）。"""
    day = today or datetime.now().astimezone().strftime("%Y-%m-%d")
    return len({str(w["semantic_flag"].get("lead_id")) for w in data.get("watches") or []
                if isinstance(w.get("semantic_flag"), dict) and _local_date(w["semantic_flag"].get("at")) == day})


def wake_condition(watch: Mapping[str, Any], leads: Mapping[str, Any]) -> str:
    """擋下的追源／讀圖叫醒在等什麼（#96）——給預篩看的條件。追源線索讀停放時寫的觸發條件（`trace_next_trigger`，
    沒寫就用 T2 的 query hint）；讀圖叫醒等的是「需求側客戶寫到這一層」。末句點名例行申報不算（誤醒的那幾型）。"""
    if watch.get("wake_lead"):
        lead = leads.get(str(watch["wake_lead"])) or {}
        waits = " ".join(str((lead.get("refs") or {}).get("trace_next_trigger")
                             or (watch.get("poll") or {}).get("query_hint") or "").split())
        title = " ".join(str(lead.get("title") or "").split())[:200]
        return (f"（停放中的追源線索在等的事）{waits or '（停放時沒寫觸發條件，只能看線索原題）'}｜線索原題：{title}｜"
                "這份新文件有沒有回答它在等的事；只是同一家公司的例行申報（治理、股權、董事、融資合約、會議通知、持股）不算")
    node = str(watch.get("wake_reading") or "")
    label = node.split(":", 1)[-1].replace("_", " ")
    return (f"（結構讀圖在等需求側客戶的新文件）讀圖節點 {node}（{label}）｜這份文件有沒有寫到這一層或這個產品的具體內容"
            "（用量、採購、供應商、認證、產能、規格、價格、技術路線）；只寫財務、治理、股權、融資合約的不算")


def _screen_candidates(data: Mapping[str, Any], leads: Mapping[str, Any]) -> list[tuple[Mapping[str, Any], str]]:
    """(watch, 條件)：醒來還沒標旗的語意 watch，加上擋下還沒預篩的追源／讀圖叫醒（追源只收 lead 仍停放的——
    在路上的 consume-fired 已直接回 active）。照（醒來時間、觸發文件）排：同一份文件的排在一起，一次看完。"""
    out: list[tuple[Mapping[str, Any], str]] = []
    for watch in data.get("watches") or []:
        if watch.get("kind") == ew.SEMANTIC_KIND and watch.get("status") == "fired" and ew.flag_for_current(watch) is None:
            out.append((watch, str(watch.get("condition") or "")))
        elif ew.wake_screen(watch) == "held_unscreened":
            if watch.get("wake_lead") and (leads.get(str(watch["wake_lead"])) or {}).get("status") != "parked":
                continue
            out.append((watch, wake_condition(watch, leads)))
    def woken(watch: Mapping[str, Any]) -> tuple[str, str]:
        w = watch.get("woken_by") or {}
        return str(w.get("at") or ""), str(w.get("lead_id") or "")

    # 文件的先後＝它叫醒的第一條的時間；同一份文件不論各條幾點醒，都排在一起（分批照文件分，全文只付一次）
    first: dict[str, str] = {}
    for watch, _ in out:
        at, lead_id = woken(watch)
        first[lead_id] = min(first.get(lead_id, at), at)
    out.sort(key=lambda pair: (first[woken(pair[0])[1]], woken(pair[0])[1], woken(pair[0])[0]))
    return out


def prepare(data: Mapping[str, Any], leads: Mapping[str, Any], *, run_id: str, text_dir: Path = TEXT_DIR,
            today: str | None = None, fetcher: Callable[[Mapping[str, Any]], Any] = fetcher_for) -> dict[str, Any]:
    """名額＝`semantic_screen_daily_limit` 份**文件**扣掉當日已看過的份數；同一份文件叫醒的每一條都跟著進批次、不另佔名額。"""
    cfg = ew.load_config()
    limit = int(cfg["semantic_screen_daily_limit"])
    max_chars = int(cfg["prescreen_text_max_chars"])
    already = documents_screened_today(data, today=today)
    remaining = max(0, limit - already)
    candidates = _screen_candidates(data, leads)
    counts = {"candidates": len(candidates), "no_fetcher": 0, "no_text": 0, "not_in_batch": 0,
              "reused_text": 0, "truncated": 0, "limit": limit, "flags_today": already,
              "wakes": sum(1 for w, _ in candidates if w.get("kind") != ew.SEMANTIC_KIND), "documents": 0}
    items: list[dict[str, Any]] = []
    texts: dict[str, str | None] = {}
    for watch, condition in candidates:
        lead_id = str((watch.get("woken_by") or {}).get("lead_id") or "")
        lead = leads.get(lead_id) or {}
        fetch = fetcher(lead) if lead else None
        if fetch is None:
            counts["no_fetcher"] += 1
            continue
        if lead_id not in texts:
            # 抓到的才算名額（抓不到的計 no_text、不佔位；N4-10 同一條）
            if sum(1 for t in texts.values() if t is not None) >= remaining:
                counts["not_in_batch"] += 1
                continue
            text, reused = load_or_fetch_text(lead_id, lead, text_dir=text_dir, fetch=fetch)
            texts[lead_id] = text
            if text is not None:
                counts["reused_text"] += int(reused)
                counts["truncated"] += int(len(text) > max_chars)
        text = texts[lead_id]
        if text is None:
            counts["no_text"] += 1
            continue
        items.append({"watch_id": watch["watch_id"], "lead_id": lead_id, "condition": condition,
                      "source_ref": watch.get("source_ref"), "text_path": str(_text_path(lead_id, text_dir)),
                      "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "truncated": len(text) > max_chars})
    counts["documents"] = len({i["lead_id"] for i in items})
    return {"schema": "prescreen-batch-v1", "run_id": run_id,
            "run_date": datetime.now().astimezone().strftime("%Y-%m-%d"),
            "max_chars": max_chars, "items": items, "counts": counts}


def cmd_prepare(*, run_id: str, out: Path) -> int:
    from engine_b.leads import load as load_leads

    out.unlink(missing_ok=True)
    data = ew.load_watches()
    batch = prepare(data, load_leads()["leads"], run_id=run_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    c = batch["counts"]
    print(json.dumps({"status": "ok", "selected": len(batch["items"]), **c}, ensure_ascii=False))
    print(f"預篩批次 {len(batch['items'])} 條（{c['documents']} 份文件；其中追源／讀圖叫醒 {c['wakes']} 條候選）"
          f"｜無 fetcher {c['no_fetcher']}｜無全文 {c['no_text']}"
          f"｜截斷 {c['truncated']} 份｜還有 {c['not_in_batch']} 條沒進本批（每日上限 {c['limit']} 份、"
          f"今天已看 {c['flags_today']} 份）", file=sys.stderr)
    return 0


def apply(data: dict[str, Any], batch: Mapping[str, Any], result: Mapping[str, Any], *,
          run_id: str) -> dict[str, Any]:
    """驗證後只寫 `semantic_flag`。回傳摘要；`run_id` 不符 raise（一則都不寫）。"""
    if not (result.get("run_id") == batch.get("run_id") == run_id):
        raise ValueError(f"run_id 不符：結果 {result.get('run_id')!r}／批次 {batch.get('run_id')!r}／參數 {run_id!r}")
    items = batch.get("items")
    flags = result.get("flags")
    if not isinstance(items, list) or not isinstance(flags, list):
        raise ValueError("批次的 items 或結果的 flags 不是 list")
    in_batch = {(str(i.get("watch_id")), str(i.get("lead_id"))): i for i in items if isinstance(i, dict)}
    seen: dict[tuple[str, str], int] = {}
    for proposal in flags:
        if isinstance(proposal, dict):
            key = (str(proposal.get("watch_id")), str(proposal.get("lead_id")))
            seen[key] = seen.get(key, 0) + 1
    by_verdict = {v: 0 for v in ew.PRESCREEN_VERDICTS}
    rejected: list[dict[str, str]] = []
    quote_rejected = 0
    answered: set[tuple[str, str]] = set()
    for proposal in flags:
        if not isinstance(proposal, dict):
            rejected.append({"pair": "?", "reason": "不是 object"})
            continue
        key = (str(proposal.get("watch_id") or ""), str(proposal.get("lead_id") or ""))
        answered.add(key)
        verdict = proposal.get("verdict")
        if not key[0] or not key[1] or verdict is None:
            rejected.append({"pair": "／".join(key), "reason": "缺 watch_id／lead_id／verdict"})
            continue
        if verdict not in ew.PRESCREEN_VERDICTS:
            rejected.append({"pair": "／".join(key), "reason": f"verdict 不在字彙內：{verdict!r}"})
            continue
        if seen.get(key, 0) > 1:
            rejected.append({"pair": "／".join(key), "reason": "duplicate"})
            continue
        item = in_batch.get(key)
        if item is None:
            rejected.append({"pair": "／".join(key), "reason": "not_in_batch"})
            continue
        quote = proposal.get("quote")
        if verdict == "likely_touches" and not str(quote or "").strip():
            rejected.append({"pair": "／".join(key), "reason": "likely_touches 缺引文"})
            quote_rejected += 1
            continue
        if str(quote or "").strip():
            try:
                text = Path(str(item["text_path"])).read_text(encoding="utf-8")
            except OSError:
                text = ""
            if normalize_whitespace(quote) not in normalize_whitespace(text):
                rejected.append({"pair": "／".join(key), "reason": "引文不是原文逐字"})
                quote_rejected += 1
                continue
        try:
            ew.flag(data, key[0], lead_id=key[1], verdict=str(verdict), quote=quote or None,
                    session_id=proposal.get("session_id"), note=proposal.get("note"))
        except ew.EventWatchError as exc:
            rejected.append({"pair": "／".join(key), "reason": str(exc)})
            continue
        by_verdict[str(verdict)] += 1
    not_answered = sorted("／".join(k) for k in set(in_batch) - answered)
    return {"flagged": sum(by_verdict.values()), "by_verdict": by_verdict, "rejected": len(rejected),
            "quote_rejected": quote_rejected, "not_answered": len(not_answered),
            "rejections": rejected[:30], "unanswered": not_answered[:30]}


def cmd_apply(*, result_path: Path, batch_path: Path, run_id: str) -> int:
    def fail(message: str) -> int:
        print(json.dumps({"status": "error", "error": message}, ensure_ascii=False))
        print(f"prescreen-apply 一則都不寫：{message}", file=sys.stderr)
        return 1

    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fail(f"沒有結果檔：{result_path}")
    except (OSError, ValueError) as exc:
        return fail(f"結果檔讀不到或不是 JSON：{exc}")
    try:
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return fail(f"批次檔讀不到或不是 JSON：{exc}")
    if not isinstance(result, dict) or not isinstance(batch, dict):
        return fail("結果檔或批次檔不是 JSON object")
    data = ew.load_watches()
    try:
        summary = apply(data, batch, result, run_id=run_id)
    except ValueError as exc:
        return fail(str(exc))
    ew.save_watches(data)
    counts = batch.get("counts") or {}
    v = summary["by_verdict"]
    print(json.dumps({"status": "ok", "summary": {**summary, "batch": len(batch.get("items") or []),
                                                    "no_text": counts.get("no_text"),
                                                    "no_fetcher": counts.get("no_fetcher"),
                                                    "truncated": counts.get("truncated")}},
                     ensure_ascii=False))
    print(f"預篩 {len(batch.get('items') or [])}｜標旗 {summary['flagged']}（可能觸及 {v['likely_touches']}"
          f"／無關 {v['likely_unrelated']}／看不出 {v['cannot_tell']}）｜無全文 {counts.get('no_text')}"
          f"｜無 fetcher {counts.get('no_fetcher')}｜截斷 {counts.get('truncated')}｜拒收 {summary['rejected']}"
          f"｜未進本批 {counts.get('not_in_batch')}", file=sys.stderr)
    return 0
