"""語意預篩（Phase 1 Step 1.4；C7）：daily 的 ⑩a／⑩c——程式抓全文、程式驗證 LLM 的標旗提議。

**預篩只標旗、不判定**（G7）：`semantic_flag` 是給互動 session 讀的提示，不改 watch 狀態、不減少「未檢 N」，
判定只在互動（`event_watch judge`）。LLM（⑩b，`claude -p` 零工具）只看得到程式塞進 prompt 的條件原文與全文。

- ⑩a `prepare`：選 `fired`、語意型、且對「這一次叫醒它的 lead」還沒有標旗的 watch，照醒來時間排。
  **先排除觸發 lead 的來源沒有 fetcher 的**（計數 `no_fetcher`，**不佔名額**——否則它們每天被重選、永遠抓不到，
  可能吃光名額；第 4 輪 N4-10）。其餘逐筆抓全文，**抓到的才進批次、才算名額**；名額＝
  `semantic_screen_daily_limit` 扣掉**當日**已寫的標旗數（手動重跑不得超過 G7 的每日硬上限）。
  抓不到計數 `no_text`、不進批次、**不拿標題充數**；全文存 `library/private/semantic_text/<lead_id>.txt`，
  已存在就重用、不重抓。
- 全文來源只有兩種主機：EDGAR 主文件（`www.sec.gov`，URL 就是主文件）與 MFN 公告頁（`mfn.se`，
  **只取公告頁文字、不抓 `mb.cision.com` 的附件、不寫 `out_dir`**——`fetchers/mfn.py:fetch_release` 會做那些事，
  所以不用它；第 4 輪 N4-8）。MOPS 重訊本來就有 `raw_text`，直接用。
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


def strip_xbrl_header(text: str | None) -> str | None:
    """從封面（`UNITED STATES SECURITIES AND EXCHANGE COMMISSION`）起算；找不到就原樣回傳（不猜）。
    只切掉前面的機器表頭，不動正文——引文比對仍對存檔的這一份做。"""
    if not text:
        return text
    start = text.find(_COVER_START)
    return text[start:] if start > 0 else text


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


def fetcher_for(lead: Mapping[str, Any]) -> Callable[[], str | None] | None:
    """這則 lead 有沒有取全文的方法。None＝沒有 fetcher（計 `no_fetcher`、不佔名額）。"""
    source = str(lead.get("source") or "")
    url = str(lead.get("url") or "")
    if source.startswith("mops:") and str(lead.get("raw_text") or "").strip():
        return lambda: str(lead.get("raw_text"))
    if urlsplit(url).netloc == "www.sec.gov":
        parsed = parse_edgar_url(url)
        if parsed is None:
            return None

        def edgar() -> str | None:
            from fetchers.edgar import fetch_filing_text

            return strip_xbrl_header(fetch_filing_text(*parsed))

        return edgar
    if urlsplit(url).netloc == "mfn.se":
        return lambda: fetch_mfn_text(url)
    return None


def _text_path(lead_id: str, text_dir: Path) -> Path:
    return text_dir / f"{lead_id}.txt"


def load_or_fetch_text(lead_id: str, lead: Mapping[str, Any], *, text_dir: Path = TEXT_DIR,
                       fetch: Callable[[], str | None]) -> tuple[str | None, bool]:
    """(全文, 是否重用存檔)。已存檔就重用、不重抓；抓到空字串或失敗回 None。"""
    path = _text_path(lead_id, text_dir)
    if path.is_file():
        return path.read_text(encoding="utf-8"), True
    try:
        text = fetch()
    except Exception as exc:  # noqa: BLE001 — 抓不到就是抓不到（計數），不得拿標題充數
        print(f"[prescreen] {lead_id} 抓全文失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
        return None, False
    if not text or not str(text).strip():
        return None, False
    text_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text), encoding="utf-8")
    meta = {"lead_id": lead_id, "source_url": lead.get("url"),
            "sha256": hashlib.sha256(str(text).encode("utf-8")).hexdigest(),
            "chars": len(str(text)), "fetched_at": datetime.now(timezone.utc).isoformat()}
    path.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    return str(text), False


def _local_date(stamp: str | None) -> str:
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def flags_written_today(data: Mapping[str, Any], *, today: str | None = None) -> int:
    day = today or datetime.now().astimezone().strftime("%Y-%m-%d")
    return sum(1 for w in data.get("watches") or []
               if isinstance(w.get("semantic_flag"), dict) and _local_date(w["semantic_flag"].get("at")) == day)


def prepare(data: Mapping[str, Any], leads: Mapping[str, Any], *, run_id: str, text_dir: Path = TEXT_DIR,
            today: str | None = None, fetcher: Callable[[Mapping[str, Any]], Any] = fetcher_for) -> dict[str, Any]:
    cfg = ew.load_config()
    limit = int(cfg["semantic_screen_daily_limit"])
    max_chars = int(cfg["prescreen_text_max_chars"])
    already = flags_written_today(data, today=today)
    remaining = max(0, limit - already)
    candidates = [w for w in data.get("watches") or []
                  if w.get("kind") == ew.SEMANTIC_KIND and w.get("status") == "fired"
                  and ew.flag_for_current(w) is None]
    candidates.sort(key=lambda w: str((w.get("woken_by") or {}).get("at") or ""))
    counts = {"candidates": len(candidates), "no_fetcher": 0, "no_text": 0, "not_in_batch": 0,
              "reused_text": 0, "truncated": 0, "limit": limit, "flags_today": already}
    items: list[dict[str, Any]] = []
    for watch in candidates:
        lead_id = str((watch.get("woken_by") or {}).get("lead_id") or "")
        lead = leads.get(lead_id) or {}
        fetch = fetcher(lead) if lead else None
        if fetch is None:
            counts["no_fetcher"] += 1
            continue
        if len(items) >= remaining:
            counts["not_in_batch"] += 1
            continue
        text, reused = load_or_fetch_text(lead_id, lead, text_dir=text_dir, fetch=fetch)
        if text is None:
            counts["no_text"] += 1
            continue
        counts["reused_text"] += int(reused)
        truncated = len(text) > max_chars
        counts["truncated"] += int(truncated)
        items.append({"watch_id": watch["watch_id"], "lead_id": lead_id, "condition": watch.get("condition"),
                      "source_ref": watch.get("source_ref"), "text_path": str(_text_path(lead_id, text_dir)),
                      "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "truncated": truncated})
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
    print(f"預篩批次 {len(batch['items'])}｜無 fetcher {c['no_fetcher']}｜無全文 {c['no_text']}"
          f"｜截斷 {c['truncated']}｜還有 {c['not_in_batch']} 筆沒進本批（每日上限 {c['limit']}、"
          f"今天已標 {c['flags_today']}）", file=sys.stderr)
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
                    session_id=proposal.get("session_id"))
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
