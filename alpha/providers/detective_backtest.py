"""偵探回溯（起漲點前看）的 I/O：價格（Engine C 唯讀）、主題等權組、Q3W 名單、封存檔、回溯日當時的鄰居、補抓、評分。

plan `docs/plans/2026-11-18-001-dev-detective-backtest-plan.md`；純規則在 `alpha/detective_backtest.py`。
⚠ **印出來的只准是代號、日期、組別**：價格、比值、誰是贏家只住封存檔 `cases_sealed.json`（§3.2）；
`score` 開封之後才印超額，印了就要照 §3.9 揭露。主 session 不讀封存檔。
不寫任何 authority（封存檔與補抓檔都在 `library/private/research_notes/detective/backtest/`，不進 `library/raw`）。
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..detective_backtest import (
    GROUPS, MaskEntry, UniverseMember, clean_bars, find_cases, lean_tally, next_case, pair_wins,
    separation_verdict, still_needed,
)

ROOT = Path(__file__).resolve().parents[2]
BACKTEST_DIR = ROOT / "library" / "private" / "research_notes" / "detective" / "backtest"
SEALED = BACKTEST_DIR / "cases_sealed.json"
BACKFILL_DIR = BACKTEST_DIR / "raw"
Q3W_PATH = ROOT / "docs" / "reports" / "phase7" / "cases.md"
#: 補抓的申報種類（EDGAR）：定期報告與重大公告；8-K／6-K 另抓 EX-99 附件（新聞稿與財報常在那裡，failure log #105）。
EDGAR_FORMS = frozenset({"10-K", "10-Q", "8-K", "20-F", "6-K", "40-F"})
BACKFILL_MONTHS = 12
BACKFILL_PER_COMPANY = 12
#: 評分窗（§3.8）：回溯日起 3／6／12 個月。
SCORE_WINDOWS = (("3 個月", 91), ("6 個月", 182), ("12 個月", 365))
MARKET_BENCHMARKS = ("QQQ", "SOXX", "IWM", "0050.TW")


# ---- 宇宙與價格 --------------------------------------------------------------------------------------
_Q3W_HEAD = re.compile(r"^## Q3W\b", re.M)
_Q3W_ROW = re.compile(r"^\|\s*\d+\s*\|\s*([^|\s]+)\s*\|", re.M)


def q3w_tickers(path: Path = Q3W_PATH) -> list[str]:
    """Q3W 名單（cases.md 的 Q3W 段、表格第二欄）。段落找不到就 raise——名單外是使用者的條件，不能默默變成「全收」。"""
    text = path.read_text(encoding="utf-8")
    m = _Q3W_HEAD.search(text)
    if not m:
        raise SystemExit(f"✗ {path} 找不到 Q3W 段——不能判名單外（plan §3.2）")
    rest = text[m.end():]
    end = re.search(r"^## ", rest, re.M)
    section = rest[:end.start()] if end else rest
    tickers = _Q3W_ROW.findall(section)
    if not tickers:
        raise SystemExit("✗ Q3W 段解析不到任何代號")
    return tickers


def universe() -> tuple[list[UniverseMember], dict[str, Any], list[str]]:
    """主題等權組現行成員（每檔帶它屬於哪幾組）＋ cohort_id → 組物件＋壞行。"""
    from .theme_cohorts import current_cohorts

    cohorts, errors = current_cohorts()
    by_ticker: dict[str, tuple[str, set[str]]] = {}
    for c in cohorts:
        for m in c.members:
            entry = by_ticker.setdefault(m.ticker, (m.company_id, set()))
            entry[1].add(c.cohort_id)
    members = [UniverseMember(t, cid, frozenset(ids)) for t, (cid, ids) in sorted(by_ticker.items())]
    return members, {c.cohort_id: c for c in cohorts}, list(errors)


def load_bars(tickers: Iterable[str], *, today: date | None = None) -> dict[str, list[tuple[date, float]]]:
    """Engine C 還原收盤（唯讀）。沒有還原收盤的根不收（不拿 raw 頂替：分割會變成假的 2 倍）。"""
    from engine_c.history import price_series

    from .three_questions import _conn_for

    conn = _conn_for("ro")
    out: dict[str, list[tuple[date, float]]] = {}
    for t in tickers:
        bars = price_series(conn, t, as_of=today or date.today())
        out[t] = clean_bars((date.fromisoformat(str(b["bar_date"])[:10]), b["close_adjusted"]) for b in bars)
    return out


# ---- 封存檔 ------------------------------------------------------------------------------------------
def read_sealed(path: Path = SEALED) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_sealed(data: Mapping[str, Any], path: Path = SEALED) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def build_sealed(*, today: date | None = None, rebuild: bool = False, path: Path = SEALED) -> dict[str, Any]:
    """找起漲點與對照、寫封存檔；已經有封存檔就不重找（除非 `rebuild`——那會丟掉已組包的狀態）。回只含計數的摘要。"""
    existing = read_sealed(path)
    if existing is not None and not rebuild:
        return {"reused": True, "counts": existing.get("counts", {}), "generated_at": existing.get("generated_at")}
    members, _cohorts, errors = universe()
    excluded = q3w_tickers()
    bars = load_bars([m.ticker for m in members], today=today)
    cases, counts = find_cases(members, bars, excluded=excluded)
    counts["cohort_errors"] = len(errors)
    counts["q3w_list"] = len(excluded)
    data = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "plan": "docs/plans/2026-11-18-001-dev-detective-backtest-plan.md",
            "price_through": max((b[-1][0] for b in bars.values() if b), default=None).isoformat() if bars else None,
            "counts": counts, "cases": cases}
    write_sealed(data, path)
    return {"reused": False, "counts": counts, "generated_at": data["generated_at"]}


def public_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """可以印的欄位：編號、代號、company_id、回溯日、組別、狀態。"""
    return {k: case.get(k) for k in ("case_id", "ticker", "company_id", "as_of", "group", "status")}


def next_for(group: str, *, path: Path = SEALED) -> tuple[dict[str, Any] | None, int]:
    data = read_sealed(path)
    if data is None:
        raise SystemExit("✗ 還沒有封存檔：先跑 `python -m alpha detective rallies`")
    case = next_case(data["cases"], group)
    return (public_case(case) if case else None), still_needed(data["cases"], group)


def mark(case_id: str, *, passed: bool, reason: str, path: Path = SEALED) -> dict[str, Any]:
    data = read_sealed(path)
    if data is None:
        raise SystemExit("✗ 還沒有封存檔")
    for case in data["cases"]:
        if case["case_id"] == case_id:
            case["status"] = "accepted" if passed else "skipped"
            case["status_reason"] = reason
            case["status_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            write_sealed(data, path)
            return public_case(case)
    raise SystemExit(f"✗ 封存檔沒有 {case_id}")


def case_dir(case_id: str) -> Path:
    """案例資料夾＝`backtest/<case_id>/`——**不含代號**：路徑會出現在提示裡，遮名包的路徑不能洩漏名字。"""
    return BACKTEST_DIR / case_id


# ---- 回溯日當時的鄰居 --------------------------------------------------------------------------------
def fetch_doc_dates(doc_ids: Iterable[str]) -> dict[str, date | None]:
    """SourceDoc 的 `published_at`（沒有的是 None——不拿 retrieved_at 冒充，INV-6）。"""
    import os

    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    ids = sorted({str(i) for i in doc_ids if i})
    if not ids:
        return {}
    load_dotenv(ROOT / ".env")
    driver = GraphDatabase.driver(os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                                  auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]))
    out: dict[str, date | None] = {i: None for i in ids}
    try:
        with driver.session() as session:
            for row in session.run("MATCH (s:SourceDoc) WHERE s.id IN $ids RETURN s.id AS id, s.published_at AS p", ids=ids):
                raw = str(row["p"] or "")[:10]
                try:
                    out[row["id"]] = date.fromisoformat(raw) if raw else None
                except ValueError:
                    out[row["id"]] = None
    finally:
        driver.close()
    return out


# ---- 補抓（§3.7）------------------------------------------------------------------------------------
def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()


def _write_doc(out_dir: Path, name: str, text: str, meta: Mapping[str, Any]) -> bool:
    path = out_dir / name
    if path.is_file():
        return False
    path.write_text(text, encoding="utf-8")
    path.with_suffix(".meta.json").write_text(json.dumps(dict(meta), ensure_ascii=False, indent=1), encoding="utf-8")
    return True


def _edgar_window(cik: str, start: date, end: date) -> list[dict[str, Any]]:
    """[start, end] 內的 EDGAR 申報（新到舊）：`recent` 不夠早時往舊的分頁補（`recent` 只保證約一年）。"""
    import requests

    from fetchers.edgar import EDGAR_SUBMISSIONS, _build_headers, fetch_submissions, recent_filings
    from fetchers.utils import rate_sleep

    data = fetch_submissions(cik)
    filings = recent_filings(data, cik)
    earliest = min((f["filed_date"] for f in filings), default="9999")
    if earliest > start.isoformat():
        for page in data.get("filings", {}).get("files", []) or []:
            if str(page.get("filingTo") or "") < start.isoformat() or str(page.get("filingFrom") or "") > end.isoformat():
                continue
            rate_sleep()
            resp = requests.get(f"{EDGAR_SUBMISSIONS}/{page['name']}", headers=_build_headers(), timeout=30)
            resp.raise_for_status()
            filings += recent_filings({"filings": {"recent": resp.json()}, "name": data.get("name", "")}, cik)
    picked = [f for f in filings if f["form_type"].upper() in EDGAR_FORMS and start.isoformat() <= f["filed_date"] <= end.isoformat()]
    return sorted(picked, key=lambda f: f["filed_date"], reverse=True)


def _backfill_edgar(ticker: str, start: date, end: date, out_dir: Path, per_company: int) -> dict[str, int]:
    from fetchers.edgar import fetch_filing_exhibits, fetch_filing_text, get_cik

    stats = {"listed": 0, "written": 0, "failed": 0}
    cik = get_cik(ticker)
    if not cik:
        return {**stats, "no_cik": 1}
    filings = _edgar_window(cik, start, end)
    stats["listed"] = len(filings)
    for f in filings[:per_company]:
        name = f"bf_{_safe(ticker)}_{_safe(f['form_type'])}_{f['filed_date']}_{f['accession'][-8:]}.txt"
        if (out_dir / name).is_file():
            continue
        text = fetch_filing_text(cik, f["accession"], f["primary_doc"]) or ""
        if f["form_type"].upper() in {"8-K", "6-K"}:
            try:
                for kind, doc, body in fetch_filing_exhibits(cik, f["accession"]):
                    text += f"\n\n===== {kind} {doc} =====\n{body}"
            except Exception:                       # noqa: BLE001 — 索引頁抓不到：只有主文件，記失敗
                stats["failed"] += 1
        if not text.strip():
            stats["failed"] += 1
            continue
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{f['accession']}/{f['primary_doc']}"
        stats["written"] += _write_doc(out_dir, name, text, {"filed_date": f["filed_date"], "form": f["form_type"],
                                                              "source_url": url, "ticker": ticker,
                                                              "retrieved_at": date.today().isoformat()})
    return stats


def _backfill_mops(ticker: str, start: date, end: date, out_dir: Path, per_company: int) -> dict[str, int]:
    from fetchers.mops import fetch_document, list_documents, pdf_to_text, roc_upload_time_to_iso_date

    stats = {"listed": 0, "written": 0, "failed": 0}
    co_id = ticker.split(".")[0]
    docs: list[dict[str, str]] = []
    for year in sorted({start.year - 1911, end.year - 1911}):
        try:
            docs += list_documents(co_id, str(year), mtype="A")
        except Exception:                           # noqa: BLE001
            stats["failed"] += 1
    picked = []
    for d in docs:
        filed = roc_upload_time_to_iso_date(d.get("uploaded_at", ""))
        if filed and start.isoformat() <= filed <= end.isoformat() and "英文版" not in d.get("detail", ""):
            picked.append((filed, d))
    picked.sort(key=lambda x: x[0], reverse=True)
    stats["listed"] = len(picked)
    for filed, d in picked[:per_company]:
        name = f"bf_{_safe(ticker)}_mops_{filed}_{_safe(d['filename'])[:40]}.txt"
        if (out_dir / name).is_file():
            continue
        try:
            text, _pages = pdf_to_text(fetch_document(co_id, d["filename"], mtype="A"))
        except Exception:                           # noqa: BLE001
            stats["failed"] += 1
            continue
        stats["written"] += _write_doc(out_dir, name, text, {"filed_date": filed, "form": d.get("detail", ""),
                                                              "source_url": "https://doc.twse.com.tw", "ticker": ticker,
                                                              "retrieved_at": date.today().isoformat()})
    return stats


def market_of(ticker: str) -> str:
    t = ticker.upper()
    if "." not in t and ":" not in t:
        return "us"
    if t.endswith((".TW", ".TWO")):
        return "tw"
    return "other"


def backfill(ticker: str, as_of: date, out_dir: Path, *, months: int = BACKFILL_MONTHS,
             per_company: int = BACKFILL_PER_COMPANY, rows: list[dict[str, Any]] | None = None,
             doc_dates: Mapping[str, date | None] | None = None) -> dict[str, Any]:
    """目標＋回溯日當時的直接鄰居，[as_of − months, as_of] 的定期報告與重大公告（照規則、不手挑）。
    美股走 EDGAR、台股走 MOPS 財報區；其他市場沒有日期區間列表的路線，**不補、數出來**（INV-3）。"""
    from identity.registry import get_registry

    from ..detective import neighbors_from_rows
    from ..detective_backtest import known_rows
    from .detective import fetch_neighbor_rows

    registry = get_registry()
    company_id = registry.company_id_for_ticker(ticker)
    if not company_id:
        raise SystemExit(f"✗ 名冊沒有 {ticker}（INV-1）")
    rows = rows if rows is not None else fetch_neighbor_rows(company_id)
    dates = doc_dates if doc_dates is not None else fetch_doc_dates(i for r in rows for ids in (r.get("edge_docs") or []) for i in (ids or []))
    kept, _dropped = known_rows(rows, dates, as_of)
    direct = [nb for nb in neighbors_from_rows(company_id, kept) if nb.roles - {"rival_customer"}]
    start = as_of - timedelta(days=round(months * 30.44))
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"companies": 0, "by_market": {}, "no_route": [], "no_ticker": [], "written": 0, "failed": 0}
    for cid in [company_id, *(nb.company_id for nb in direct)]:
        obj = registry.company(cid)
        t = getattr(obj, "research_ticker", None) if obj else None
        if not t:
            report["no_ticker"].append(cid)            # 私有公司、未上市：沒有申報可補
            continue
        report["companies"] += 1
        market = market_of(t)
        if market == "us":
            stats = _backfill_edgar(t, start, as_of, out_dir, per_company)
        elif market == "tw":
            stats = _backfill_mops(t, start, as_of, out_dir, per_company)
        else:
            report["no_route"].append(t)
            continue
        report["by_market"].setdefault(market, []).append({"ticker": t, **stats})
        report["written"] += stats.get("written", 0)
        report["failed"] += stats.get("failed", 0)
    report["window"] = [start.isoformat(), as_of.isoformat()]
    report["out_dir"] = out_dir.as_posix()
    return report


# ---- 遮名的名冊寫法 ----------------------------------------------------------------------------------
def mask_entries(target_id: str, neighbors: Sequence[Any]) -> list[MaskEntry]:
    """目標＝A、鄰居照清單順序 B、C…；名字只來自 `company_name_forms`（L16）＋圖上的名字，代號來自名冊。"""
    from identity.registry import get_registry
    from query.bottleneck import company_name_forms

    from ..detective_backtest import derive_stems, mask_letter

    registry = get_registry()
    entries: list[MaskEntry] = []
    for i, (cid, graph_name) in enumerate([(target_id, None), *((nb.company_id, nb.name) for nb in neighbors)]):
        obj = registry.company(cid)
        names = set(company_name_forms(obj)) if obj else set()
        if graph_name:
            names.add(str(graph_name))
        ascii_stems, cjk_stems = derive_stems(names)
        tickers = set()
        if obj:
            tickers |= {t for t in (obj.research_ticker, obj.execution_symbol, *obj.aliases) if t}
        entries.append(MaskEntry(company_id=cid, code=mask_letter(i), names=tuple(sorted(names | set(ascii_stems))),
                                 tickers=tuple(sorted(tickers)), stems=cjk_stems))
    return entries


def leak_check(texts: Mapping[str, str], entries: Sequence[MaskEntry]) -> dict[str, dict[str, int]]:
    """檔名 → 還找得到的寫法 → 次數。兩把尺：同一套寫法（`residual_forms`）＋名字比對的唯一 owner `quote_names_company`
    （嚴格：共用寫法也算）。應該全空；不空就不寫 PROMPT。"""
    from identity.registry import get_registry
    from query.bottleneck import quote_names_company

    from ..detective_backtest import residual_forms

    registry = get_registry()
    out: dict[str, dict[str, int]] = {}
    for name, text in texts.items():
        hits = residual_forms(text, entries)
        for e in entries:
            obj = registry.company(e.company_id)
            if obj is not None and quote_names_company(text, obj, shared=frozenset()):
                hits[f"quote_names_company:{e.company_id}"] = hits.get(f"quote_names_company:{e.company_id}", 0) + 1
        if hits:
            out[name] = hits
    return out


# ---- 評分（§3.8；開封之後）---------------------------------------------------------------------------
def _bench_series(symbols: Sequence[str], since: date) -> tuple[dict[str, dict[date, float]], list[str]]:
    """大盤收盤（與首頁同一支 `fetch_close_series`）。抓不到的列出來——yfinance 限流是靜默缺值（記憶），讀 `_ERRORS` 分清楚。"""
    from .close_series import fetch_close_series

    sessions = max(30, int((date.today() - since).days * 0.75) + 20)
    raw = fetch_close_series(symbols, sessions=sessions)
    out = {s: {date.fromisoformat(r["session_date"]): float(r["close"]) for r in rows} for s, rows in raw.items()}
    missing = [s for s in symbols if not out.get(s)]
    if missing:
        try:
            import yfinance

            errors = getattr(yfinance.shared, "_ERRORS", {}) or {}
            missing = [f"{s}（{errors[s]}）" if s in errors else s for s in missing]
        except Exception:                            # noqa: BLE001
            pass
    return out, missing


def evidence_report(case: Mapping[str, Any]) -> Path:
    """證據那一次的回報：清淨組照名、遮名組遮名（§3.4）。"""
    sub = "name" if case["group"] == "clean" else "mask"
    return case_dir(str(case["case_id"])) / sub / "REPORT.md"


def score_group(group: str, *, path: Path = SEALED) -> dict[str, Any]:
    """開封一組：每個已收案例的標籤、偏多強度（高／中）、相對主題等權組與大盤的超額（3／6／12 個月）、配對分辨。
    ⚠ 印出來就是看過價格：照 §3.9 揭露。"""
    from ..theme_cohort import cohort_return, series_return

    data = read_sealed(path)
    if data is None:
        raise SystemExit("✗ 還沒有封存檔")
    cases = [c for c in data["cases"] if c["group"] == group and c.get("status") == "accepted"]
    _members, cohorts, _errors = universe()
    tickers = sorted({m.ticker for c in cohorts.values() for m in c.members} | {c["ticker"] for c in cases})
    bars = {t: dict(b) for t, b in load_bars(tickers).items()}
    earliest = min((date.fromisoformat(c["as_of"]) for c in cases), default=date.today())
    bench, bench_missing = _bench_series(MARKET_BENCHMARKS, earliest)
    last_bar = max((max(b) for b in bars.values() if b), default=date.today())
    rows = []
    for c in cases:
        as_of = date.fromisoformat(c["as_of"])
        report = evidence_report(c)
        lean = lean_tally(report.read_text(encoding="utf-8")) if report.is_file() else None
        windows = []
        for label, days in SCORE_WINDOWS:
            end = as_of + timedelta(days=days)
            if end > last_bar:
                windows.append({"window": label, "status": "還沒到"})
                continue
            own = series_return(bars.get(c["ticker"]), as_of, end)
            cohort_rets = []
            for cid in c.get("cohorts") or []:
                cohort = cohorts.get(cid)
                if cohort is not None:
                    r = cohort_return(cohort, start=as_of, end=end, series=bars, exclude_company=c["company_id"],
                                      exclude_ticker=c["ticker"])
                    if r["return"] is not None:
                        cohort_rets.append(r["return"])
            cohort_ret = sum(cohort_rets) / len(cohort_rets) if cohort_rets else None
            market = {s: series_return(bench.get(s), as_of, end) for s in MARKET_BENCHMARKS}
            windows.append({"window": label, "own": own,
                            "vs_cohort": (own - cohort_ret) if own is not None and cohort_ret is not None else None,
                            "vs_market": {s: (own - r) if own is not None and r is not None else None for s, r in market.items()}})
        rows.append({**public_case(c), "label": c["label"], "lean": lean, "windows": windows,
                     "report": report.as_posix() if report.is_file() else None})
    by_label = {lab: [r["lean"]["lean_high"] for r in rows if r["label"] == lab and r["lean"] and r["lean"]["lean_high"] is not None]
                for lab in ("winner", "control")}
    wins, total = pair_wins(by_label["winner"], by_label["control"])
    return {"group": group, "rows": rows, "pair_wins": wins, "pairs": total, "verdict": separation_verdict(wins, total),
            "bench_missing": bench_missing, "price_through": last_bar.isoformat()}


__all__ = ["BACKFILL_DIR", "BACKTEST_DIR", "SEALED", "backfill", "build_sealed", "case_dir", "evidence_report",
           "fetch_doc_dates", "leak_check", "load_bars", "mark", "mask_entries", "market_of", "next_for", "public_case",
           "q3w_tickers", "read_sealed", "score_group", "universe", "write_sealed"]
