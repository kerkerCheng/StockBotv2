"""
dart_history.py — 韓國 OpenDART 定期報告 → Engine C `fundamental_history`（日韓財報來源 S3，2026-10-21）。

**它回答的只有一件事：T 時刻市場已經從法定申報知道這家韓國公司的季營收、營業利益、現金與普通股股數是多少。**

## 要抓哪幾期由報告清單決定（不從日曆猜）

`list.json`（定期報告，含原件與更正版）的 `report_nm`＝「사업보고서 (2025.12)」「반기보고서 (2026.06)」「분기보고서 (2025.09)」——
清單上有的期才去抓；사업보고서的月份不是 12 → 這一檔的結局是 `non_december_fiscal_year`（報告代碼對不上會計年度，不猜）。

## 每一期的數（2026-10-21 實測 6/6 科目代碼一致）

- 營收 `ifrs-full_Revenue`、營業利益 `dart_OperatingIncomeLoss`：損益表（IS 或 CIS，兩處都有就要一致，否則拒寫）。
  1／2／3 分期取 `thstrm_amount`（**單季**；반기報告的 thstrm 是第二季單季、`thstrm_add_amount` 才是 6 個月累計）；
  第 1 分期的兩欄必須相等（語意核對）。第四季＝사업보고서 `thstrm_amount` − 3 分期 `thstrm_add_amount`（9 個月累計），標 derived，
  filed 取兩者較晚。
- 現金 `ifrs-full_CashAndCashEquivalents`；總借款只收整行 `ifrs-full_Borrowings`（計畫 Q3 A；今天 0/6 用到——淨負債缺席，已定價①用 P/S）。
- 股數（計畫 Q2 A）：股式總數現況 `se=보통주` 的 `distb_stock_co`（流通＝發行−自己株式），並核對它等於 `istc_totqy − tesstk_co`；
  優先股不加（三星優先股 802,371,203 不算）。

## 可知日（INV-6）：最新更正版的接收日

`fnlttSinglAcntAll` 只回**最新更正版**的 rcept_no——filed 取 `list.json` 裡那個 rcept_no 的 `rcept_dt`，並核對 rcept_no 前 8 碼；
對不到就拒寫（不猜）。代價：原件比更正版早知道的那段時間這一期缺席（SK hynix FY2020 晚 8 天），計數進 `late_known` 印出來。

## 為什麼是可重建的投影（L10）

DART 2015 起都查得到、今天重抓拿得回來；`--replace` 可整檔重建（只刪 `source=opendart://` 的列）。不進 daily（理由同 EDINET）。

用法::

    python -m engine_c.dart_history --backfill                     # 名冊全部 .KS／.KQ（約 300 次呼叫）
    python -m engine_c.dart_history --backfill --ticker 000660.KS --dry-run
    python -m engine_c.dart_history --sync                         # 清單重抓；期末在 400 天內的報告重抓（更正版會換 rcept_no）
    python -m engine_c.dart_history --ticker 000660.KS             # 印已存序列（不連網）
"""
from __future__ import annotations

import argparse
import calendar
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine_c.history_backfill import (  # noqa: E402
    DART_FORM_PREFIX, FUNDAMENTAL_LOOKBACK_YEARS, SOURCE_DART, SOURCE_DART_SHARES, insert_fundamentals)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "library" / "private" / "engine_c" / "dart"
KST = timezone(timedelta(hours=9))
CORPCODE_MAX_AGE_DAYS = 7
#: `--sync` 重抓期末在這幾天內的報告：更正版會換 rcept_no（可知日跟著變）；更早的更正版只有 `--backfill --refresh` 抓得到。
SYNC_REFRESH_DAYS = 400
LIST_MARGIN_DAYS = 120
FLOW_IDS: Mapping[str, tuple[str, ...]] = {"revenue": ("ifrs-full_Revenue",),
                                           "operating_income": ("dart_OperatingIncomeLoss",)}
INSTANT_IDS: Mapping[str, tuple[str, ...]] = {"cash": ("ifrs-full_CashAndCashEquivalents",),
                                              "total_debt": ("ifrs-full_Borrowings",)}
FLOW_STATEMENTS = ("IS", "CIS")
COMMON_SHARE = "보통주"
KEPT_ACCOUNTS = frozenset(i for ids in (*FLOW_IDS.values(), *INSTANT_IDS.values()) for i in ids)
#: 報告名稱 → 期別（분기 由月份分 1／3 分期）；12 月決算以外的公司報告代碼對不上，整檔不收。
_REPORT_NAME = re.compile(r"^(?:\[[^\]]*\]\s*)*(사업보고서|반기보고서|분기보고서)\s*\((\d{4})\.(\d{2})\)")
_KIND_BY_MONTH = {("사업보고서", 12): "FY", ("반기보고서", 6): "H1", ("분기보고서", 3): "Q1", ("분기보고서", 9): "Q3"}
REPORT_CODES = {"Q1": "11013", "H1": "11012", "Q3": "11014", "FY": "11011"}


class DartHistoryError(RuntimeError):
    """輸入不合法（不是「抓不到」——抓不到記進報告，不 raise）。"""


# ---------------------------------------------------------------------------
# 純函式
# ---------------------------------------------------------------------------

def parse_report_name(name: str) -> tuple[str, int, int] | None:
    """「[기재정정]사업보고서 (2020.12)」→ `("사업보고서", 2020, 12)`；不是定期報告的名稱 → None。"""
    m = _REPORT_NAME.match(str(name or "").strip())
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else None


def month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def period_of(kind: str, year: int) -> tuple[date, date]:
    """12 月決算：期別 → (期初, 期末)。季是單季（3 個月），FY 是整年。"""
    if kind == "FY":
        return date(year, 1, 1), date(year, 12, 31)
    end_month = {"Q1": 3, "H1": 6, "Q3": 9}[kind]
    return date(year, end_month - 2, 1), month_end(year, end_month)


def _amount(text: Any) -> Decimal | None:
    s = str(text if text is not None else "").replace(",", "").strip()
    if s in ("", "-"):
        return None
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


@dataclass
class ReportResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    internal: list[dict[str, Any]] = field(default_factory=list)   # FY 全年、Q3 九個月累計：只給第四季推算用
    rejected: list[dict[str, Any]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def build_report_rows(fs: Mapping[str, Any], shares: Mapping[str, Any] | None, *, ticker: str, kind: str, year: int,
                      filed_of: Mapping[str, str], fetched_at: str) -> ReportResult:
    """一期（`fnlttSinglAcntAll`＋`stockTotqySttus`）→ 列。**純函式**。`filed_of`＝list.json 的 {rcept_no: rcept_dt}。"""
    result = ReportResult()
    code = REPORT_CODES[kind]
    start, end = period_of(kind, year)
    label = f"{year} {kind}"

    def reject(metric: str, reason: str) -> None:
        result.rejected.append({"report": label, "metric": metric, "reason": reason})

    def filed_for(rcept_no: str, metric: str) -> str | None:
        dt = str(filed_of.get(rcept_no) or "")
        if not dt:
            reject(metric, f"rcept_no {rcept_no} 不在定期報告清單裡——可知日對不到，不猜")
            return None
        if not rcept_no.startswith(dt):
            reject(metric, f"rcept_no {rcept_no} 前 8 碼與接收日 {dt} 對不上")
            return None
        return f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}"

    rows = [r for r in fs.get("list") or () if r.get("account_id") in KEPT_ACCOUNTS]
    receipts = sorted({str(r.get("rcept_no") or "") for r in fs.get("list") or ()})
    filed = None
    if rows:
        if len(receipts) != 1:
            reject("*", f"同一期回了多個 rcept_no {receipts}——不挑一個")
            rows = []
        else:
            filed = filed_for(receipts[0], "*")
            if filed is None:
                rows = []
    base = {"ticker": ticker, "filed": filed, "accession": receipts[0] if receipts else None,
            "form": f"{DART_FORM_PREFIX}{code}", "unit_scale": 1, "source": SOURCE_DART, "fetched_at": fetched_at}

    def pick(metric: str, ids: Sequence[str], statements: Sequence[str], column: str) -> tuple[Decimal, str, str] | None:
        found: dict[Decimal, set[str]] = {}
        currencies: set[str] = set()
        hit_id = None
        for r in rows:
            if r.get("account_id") not in ids or r.get("sj_div") not in statements:
                continue
            value = _amount(r.get(column))
            if value is None:
                continue
            found.setdefault(value, set()).add(str(r.get("sj_div")))
            currencies.add(str(r.get("currency") or ""))
            hit_id = r["account_id"]
        if not found:
            if rows:
                result.missing.append(metric)
            return None
        if len(found) > 1:
            reject(metric, "同一科目在不同報表給出不同的數——不挑一個（"
                   + "；".join(f"{'／'.join(sorted(v))}＝{k}" for k, v in sorted(found.items())) + "）")
            return None
        currency = next(iter(currencies)) if len(currencies) == 1 else ""
        if len(currency) != 3 or not currency.isalpha() or not currency.isupper():
            reject(metric, f"幣別不是單一 ISO 代碼：{sorted(currencies)}")
            return None
        return next(iter(found)), currency, str(hit_id)

    for concept, ids in FLOW_IDS.items():
        got = pick(concept, ids, FLOW_STATEMENTS, "thstrm_amount")
        if got is None:
            continue
        value, currency, tag = got
        if kind == "Q1":
            add = pick(concept + "_cumulative", ids, FLOW_STATEMENTS, "thstrm_add_amount")
            if add is not None and add[0] != value:
                reject(concept, f"1 分期的 thstrm（{value}）≠ 累計（{add[0]}）——欄位語意對不上，不寫")
                continue
        if kind == "FY":
            result.internal.append({**base, "metric": f"{concept}_annual", "period_start": start.isoformat(),
                                    "period_end": end.isoformat(), "value": float(value), "currency": currency,
                                    "derived": None, "tag": tag})
            continue
        result.rows.append({**base, "metric": f"{concept}_quarter", "period_start": start.isoformat(),
                            "period_end": end.isoformat(), "value": float(value), "currency": currency,
                            "derived": None, "tag": tag})
        if kind == "Q3":
            nine = pick(concept + "_nine_month", ids, FLOW_STATEMENTS, "thstrm_add_amount")
            if nine is not None:
                result.internal.append({**base, "metric": f"{concept}_nine_month",
                                        "period_start": date(year, 1, 1).isoformat(), "period_end": end.isoformat(),
                                        "value": float(nine[0]), "currency": nine[1], "derived": None, "tag": nine[2]})
    for metric, ids in INSTANT_IDS.items():
        got = pick(metric, ids, ("BS",), "thstrm_amount")
        if got is None:
            continue
        value, currency, tag = got
        result.rows.append({**base, "metric": metric, "period_start": None, "period_end": end.isoformat(),
                            "value": float(value), "currency": currency, "derived": None, "tag": tag})
    if "total_debt" in result.missing:
        result.missing.remove("total_debt")          # 整行總額今天 0/6 有：不是異常，不計數
    shares_row = _shares(shares, ticker=ticker, kind=kind, end=end, filed_for=filed_for, fetched_at=fetched_at,
                         reject=reject, missing=result.missing)
    if shares_row is not None:
        result.rows.append(shares_row)
    return result


def is_common_share(se: Any) -> bool:
    """股式總數現況的 `se`（股類）是不是普通股。2026-10-21 實測同一個欄位有四種寫法：「보통주」（三星）、「보통주식」
    （HD 현대일렉트릭）、「의결권이 있는\\n주식(보통주)」與去掉換行的版本（삼성전기）——去空白後認這三種，其餘（우선주、
    종류주식、합계、비고）都不是。"""
    text = re.sub(r"\s+", "", str(se or ""))
    return text in (COMMON_SHARE, COMMON_SHARE + "식") or text.endswith(f"({COMMON_SHARE})")


def _shares(shares: Mapping[str, Any] | None, *, ticker: str, kind: str, end: date, filed_for: Any, fetched_at: str,
            reject: Any, missing: list[str]) -> dict[str, Any] | None:
    common = [r for r in (shares or {}).get("list") or () if is_common_share(r.get("se"))]
    if not common:
        missing.append("shares_outstanding_cover")
        return None
    if len(common) != 1:
        reject("shares_outstanding_cover", f"普通股有 {len(common)} 列——不挑一個")
        return None
    row = common[0]
    distb, issued = _amount(row.get("distb_stock_co")), _amount(row.get("istc_totqy"))
    treasury = _amount(row.get("tesstk_co")) or Decimal(0)
    if distb is None or issued is None:
        reject("shares_outstanding_cover", f"流通股數或發行股數是空的（distb={row.get('distb_stock_co')!r}）——不補")
        return None
    if issued - treasury != distb:
        reject("shares_outstanding_cover", f"distb_stock_co {distb} ≠ istc_totqy {issued} − tesstk_co {treasury}")
        return None
    if str(row.get("stlm_dt") or "")[:10] != end.isoformat():
        reject("shares_outstanding_cover", f"結算日 {row.get('stlm_dt')} 不是這一期的期末 {end}")
        return None
    rcept_no = str(row.get("rcept_no") or "")
    filed = filed_for(rcept_no, "shares_outstanding_cover")
    if filed is None:
        return None
    return {"ticker": ticker, "metric": "shares_outstanding_cover", "period_start": None, "period_end": end.isoformat(),
            "filed": filed, "accession": rcept_no, "form": f"{DART_FORM_PREFIX}{REPORT_CODES[kind]}",
            "value": float(distb), "currency": "shares", "unit_scale": 1,
            "derived": "발행−자기주식（보통주 distb_stock_co；우선주不加）", "tag": "stockTotqySttus:distb_stock_co（보통주）",
            "source": SOURCE_DART_SHARES, "fetched_at": fetched_at}


def derive_fourth_quarter(internal: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """第四季＝年度 − 同一年度的 9 個月累計（標 derived；filed＝兩者較晚）。缺 9 個月累計 → 計數，不估。**純函式**。"""
    out: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for concept in FLOW_IDS:
        nines = {(r["period_start"], r["currency"]): r for r in internal if r["metric"] == f"{concept}_nine_month"}
        for fy in (r for r in internal if r["metric"] == f"{concept}_annual"):
            nine = nines.get((fy["period_start"], fy["currency"]))
            if nine is None or nine["period_end"] >= fy["period_end"]:
                missing.append({"metric": concept, "fiscal_year": fy["period_start"][:4],
                                "reason": "沒有同一年度的 3 分期 9 個月累計——第四季推不出來（不估）"})
                continue
            q3_end = date.fromisoformat(nine["period_end"])
            out.append({**{k: fy[k] for k in ("ticker", "accession", "form", "unit_scale", "source", "fetched_at")},
                        "metric": f"{concept}_quarter", "period_start": (q3_end + timedelta(days=1)).isoformat(),
                        "period_end": fy["period_end"], "filed": max(fy["filed"], nine["filed"]),
                        "value": fy["value"] - nine["value"], "currency": fy["currency"], "tag": fy["tag"],
                        "derived": f"FY−9M：{fy['accession']}（{fy['tag']}）−{nine['accession']}（{nine['tag']}）"})
    return out, missing


# ---------------------------------------------------------------------------
# 快取（library/private；只留白名單科目）
# ---------------------------------------------------------------------------

def _report_path(cache_dir: Path, corp: str, year: int, code: str, what: str) -> Path:
    return cache_dir / "reports" / corp / f"{year}_{code}_{what}.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, ValueError):
        return None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load_corp_codes(client: Any, cache_dir: Path, *, today: date) -> tuple[list[dict[str, str]], str]:
    from fetchers.opendart import DartUnavailable, corp_code_rows

    path = cache_dir / "CORPCODE.zip"
    fresh = path.exists() and (today - datetime.fromtimestamp(path.stat().st_mtime).date()).days <= CORPCODE_MAX_AGE_DAYS
    note = "cache"
    if not fresh:
        try:
            data = client.corp_codes()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            note = "fetched"
        except DartUnavailable as exc:
            if exc.aborts_run or not path.exists():
                raise
            note = f"stale_cache（{exc}）"
    return corp_code_rows(path.read_bytes()), note


# ---------------------------------------------------------------------------
# 編排
# ---------------------------------------------------------------------------

def kr_universe() -> list[str]:
    from identity.registry import TICKER_MAP

    return sorted({t for t in TICKER_MAP.values() if t and t.endswith((".KS", ".KQ"))})


def _cached_call(path: Path, fetch: Any, *, refresh: bool, fetched_at: str) -> tuple[dict[str, Any], bool]:
    cached = _read_json(path)
    # 013（這一期沒資料）不當定案：清單上有這一期卻回 013，多半是財務資料還沒處理完——下一輪再問（10-21 實測 0 期，成本低）
    if cached is not None and not refresh and str(cached.get("status")) != "013":
        return cached, True
    body = fetch()
    keep = {"status": body.get("status"), "fetched_at": fetched_at,
            "list": [r for r in body.get("list") or () if "account_id" not in r or r.get("account_id") in KEPT_ACCOUNTS]}
    # 只留白名單科目，但保留「這一期回了哪幾個 rcept_no」（多版本要拒寫，不能被白名單篩掉而看不到）
    keep["rcept_nos"] = sorted({str(r.get("rcept_no") or "") for r in body.get("list") or ()})
    _write_json(path, keep)
    return keep, False


def _with_receipts(body: Mapping[str, Any]) -> dict[str, Any]:
    """快取只留白名單科目；把其他科目的 rcept_no 補回成空列，讓「多個 rcept_no」的檢查看得到。"""
    rows = list(body.get("list") or ())
    seen = {str(r.get("rcept_no") or "") for r in rows}
    rows += [{"rcept_no": r} for r in body.get("rcept_nos") or () if r not in seen]
    return {**body, "list": rows}


def collect(client: Any, *, tickers: Sequence[str], today: date, mode: str = "backfill", cache_dir: Path = CACHE_DIR,
            corp_rows: Sequence[Mapping[str, str]] | None = None, fetched_at: str | None = None,
            refresh_all: bool = False) -> dict[str, Any]:
    from fetchers.opendart import DartUnavailable, corp_code_for

    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    run: dict[str, Any] = {"aborted": None, "reports_fetched": 0, "reports_cached": 0, "reports_unfetched": 0,
                           "failed": []}
    per: dict[str, dict[str, Any]] = {}
    horizon = today - timedelta(days=365 * FUNDAMENTAL_LOOKBACK_YEARS)
    try:
        if corp_rows is None:
            corp_rows, run["corp_codes"] = load_corp_codes(client, cache_dir, today=today)
    except DartUnavailable as exc:
        run["aborted"] = str(exc)
        corp_rows = []
    for ticker in tickers:
        report: dict[str, Any] = {"reports_listed": 0, "reports_used": 0, "skipped": {}, "rejected": [], "missing": {},
                                  "late_known": []}
        per[ticker] = {"rows": [], "report": report}
        if run["aborted"]:
            report.update(outcome="aborted", absence=run["aborted"])
            continue
        try:
            corp = corp_code_for(ticker.split(".")[0], list(corp_rows))
            report["corp_code"] = corp
        except LookupError as exc:
            report.update(outcome="corp_code_unresolved", absence=str(exc))
            continue
        try:
            listed = client.periodic_reports(corp, (horizon - timedelta(days=LIST_MARGIN_DAYS)).strftime("%Y%m%d"),
                                             today.strftime("%Y%m%d"))
        except DartUnavailable as exc:
            if exc.aborts_run:
                run["aborted"] = str(exc)
                report.update(outcome="aborted", absence=str(exc))
            else:
                report.update(outcome="list_unavailable", absence=str(exc))
            continue
        filed_of = {str(r.get("rcept_no") or ""): str(r.get("rcept_dt") or "") for r in listed}
        periods: dict[tuple[str, int], list[dict[str, Any]]] = {}
        unsupported = None
        for r in listed:
            parsed = parse_report_name(str(r.get("report_nm") or ""))
            if parsed is None:
                continue
            name, year, month = parsed
            kind = _KIND_BY_MONTH.get((name, month))
            if kind is None:
                unsupported = f"{r.get('report_nm')}：報告月份對不上 12 月決算——報告代碼對不上會計年度，不猜"
                break
            periods.setdefault((kind, year), []).append(r)
        report["reports_listed"] = len(periods)
        if unsupported:
            report.update(outcome="non_december_fiscal_year", absence=unsupported)
            continue
        internal: list[dict[str, Any]] = []
        for (kind, year), versions in sorted(periods.items(), key=lambda kv: period_of(kv[0][0], kv[0][1])[1]):
            start, end = period_of(kind, year)
            if end < horizon - timedelta(days=366):
                continue
            code = REPORT_CODES[kind]
            refresh = refresh_all or (mode == "sync" and end >= today - timedelta(days=SYNC_REFRESH_DAYS))
            if run["aborted"]:
                run["reports_unfetched"] += 1
                continue
            try:
                fs, fs_cached = _cached_call(_report_path(cache_dir, corp, year, code, "fs"),
                                             lambda: client.single_account_all(corp, year, code),
                                             refresh=refresh, fetched_at=fetched_at)
                shares, sh_cached = _cached_call(_report_path(cache_dir, corp, year, code, "shares"),
                                                 lambda: client.share_totals(corp, year, code),
                                                 refresh=refresh, fetched_at=fetched_at)
            except DartUnavailable as exc:
                if exc.aborts_run:
                    run["aborted"] = str(exc)
                    run["reports_unfetched"] += 1
                else:
                    run["failed"].append({"ticker": ticker, "report": f"{year} {kind}", "reason": str(exc)})
                continue
            run["reports_cached" if fs_cached and sh_cached else "reports_fetched"] += 1
            if str(fs.get("status")) == "013" or not fs.get("list"):
                report["skipped"]["no_data"] = report["skipped"].get("no_data", 0) + 1
                continue
            result = build_report_rows(_with_receipts(fs), shares, ticker=ticker, kind=kind, year=year,
                                       filed_of=filed_of, fetched_at=fetched_at)
            report["reports_used"] += 1
            report["rejected"] += result.rejected
            for metric in result.missing:
                report["missing"][metric] = report["missing"].get(metric, 0) + 1
            per[ticker]["rows"] += result.rows
            internal += result.internal
            used = {r["accession"] for r in (*result.rows, *result.internal)}
            earlier = sorted(str(v.get("rcept_dt")) for v in versions if str(v.get("rcept_no")) not in used)
            used_dt = sorted(filed_of.get(a, "") for a in used)
            if earlier and used_dt and earlier[0] < used_dt[0]:
                report["late_known"].append({"report": f"{year} {kind}", "original_rcept_dt": earlier[0],
                                             "used_rcept_dt": used_dt[0]})
        q4, q4_missing = derive_fourth_quarter(internal)
        rows = [r for r in (*per[ticker]["rows"], *q4) if date.fromisoformat(r["period_end"]) >= horizon]
        per[ticker]["rows"] = rows
        report.update(q4_derived=len(q4), q4_missing=q4_missing, rows_built=len(rows),
                      metrics=dict(Counter(r["metric"] for r in rows)),
                      latest_period_end=max((r["period_end"] for r in rows), default=None),
                      latest_filed=max((r["filed"] for r in rows), default=None))
    run["calls"] = getattr(client, "calls", None)
    return {"run": run, "tickers": per}


def write(conn: Any, collected: Mapping[str, Any], *, replace: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"outcome": "written", "rows_new": {}, "rows_replaced": {}}
    for ticker, body in collected["tickers"].items():
        if "outcome" in body["report"]:
            continue
        if replace:
            cur = conn.execute("DELETE FROM fundamental_history WHERE ticker = ? AND source IN (?, ?)",
                               (ticker, SOURCE_DART, SOURCE_DART_SHARES))
            out["rows_replaced"][ticker] = cur.rowcount
        new = insert_fundamentals(conn, body["rows"])
        body["report"]["rows_new"] = new
        out["rows_new"][ticker] = new
    conn.commit()
    return out


def run(*, tickers: Sequence[str] | None, mode: str, dry_run: bool, replace: bool = False, refresh_all: bool = False,
        db: str | None = None, client: Any = None, today: date | None = None, cache_dir: Path = CACHE_DIR) -> dict[str, Any]:
    today = today or datetime.now(KST).date()
    universe = kr_universe()
    chosen = sorted({t.upper() for t in tickers}) if tickers else universe
    unknown = [t for t in chosen if t not in universe]
    if unknown:
        raise DartHistoryError(f"不是名冊裡的 .KS／.KQ：{unknown}")
    if client is None:
        from fetchers.opendart import Client, api_key

        client = Client(api_key())
    collected = collect(client, tickers=chosen, today=today, mode=mode, cache_dir=cache_dir, refresh_all=refresh_all)
    report = {"mode": mode, "dry_run": dry_run, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              **collected["run"],
              "tickers": {t: b["report"] for t, b in collected["tickers"].items()}}
    if dry_run:
        report["write"] = {"outcome": "dry_run"}
        report["rows_preview"] = {t: b["rows"] for t, b in collected["tickers"].items()}
        return report
    from engine_b.writer_lock import INTERACTIVE_OWNER, hold
    from engine_c.history_backfill import _open

    conn = _open(db)
    try:
        with hold(INTERACTIVE_OWNER, ttl_minutes=15, purpose="OpenDART 回填寫入 fundamental_history"):
            report["write"] = write(conn, collected, replace=replace)
    finally:
        conn.close()
    return report


def filing_freshness(conn: Any, tickers: Sequence[str], *, today: date) -> dict[str, Any]:
    """心跳段 1 的「韓國」那半行（零網路）。法定期限：分기／반기報告＝季後 45 日、사업보고서＝年度後 90 日。
    「落後」（下一期過了期限、表上還沒有——`--sync` 修得了）與「營收不能用」（抓到的最新一期沒有季營收）分開。"""
    out: dict[str, Any] = {"have": [], "empty": [], "lagging": [], "unusable": [], "latest": None}
    for ticker in tickers:
        rows = conn.execute("SELECT metric, period_end FROM fundamental_history WHERE ticker = ? AND source IN (?, ?) "
                            "AND filed <= ?", (ticker, SOURCE_DART, SOURCE_DART_SHARES, today.isoformat())).fetchall()
        if not rows:
            out["empty"].append(ticker)
            continue
        end = max(str(r[1]) for r in rows)
        revenue = max((str(r[1]) for r in rows if r[0] == "revenue_quarter"), default=None)
        if revenue is None:
            out["unusable"].append(f"{ticker}（沒有任何季營收）")
            continue
        out["have"].append(ticker)
        if revenue < end:
            out["unusable"].append(f"{ticker}（{end} 那一期營收沒收）")
        latest = date.fromisoformat(end)
        total = latest.year * 12 + latest.month + 2
        nxt = month_end(total // 12, total % 12 + 1)
        due = nxt + timedelta(days=90 if nxt.month == 12 else 45)
        if today > due:
            out["lagging"].append(f"{ticker}（{nxt} 那一期，期限 {due}）")
        out["latest"] = max(out["latest"] or end, end)
    return out


def last_run_summary(cache_dir: Path = CACHE_DIR) -> dict[str, Any] | None:
    """最近一輪正式寫入的報告摘要（乾跑不算）。讀不到回 None。"""
    try:
        report = json.loads((cache_dir / "last_write_report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {"generated_at": report.get("generated_at"), "aborted": report.get("aborted"),
            "rejected": sum(len(t.get("rejected") or ()) for t in (report.get("tickers") or {}).values()),
            "late_known": sum(len(t.get("late_known") or ()) for t in (report.get("tickers") or {}).values())}


def stored_series(conn: Any, ticker: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        """SELECT metric, period_start, period_end, filed, accession, form, value, currency, derived, tag
           FROM fundamental_history WHERE ticker = ? AND source IN (?, ?) ORDER BY metric, period_end, filed, accession""",
        (ticker, SOURCE_DART, SOURCE_DART_SHARES))
    keys = ("metric", "period_start", "period_end", "filed", "accession", "form", "value", "currency", "derived", "tag")
    return [dict(zip(keys, r)) for r in cur.fetchall()]


def _summary_lines(report: Mapping[str, Any]) -> list[str]:
    lines = [f"OpenDART {report['mode']}{'（乾跑）' if report.get('dry_run') else ''}｜報告 新抓 {report['reports_fetched']}、"
             f"快取 {report['reports_cached']}、沒抓 {report['reports_unfetched']}、失敗 {len(report['failed'])}｜呼叫 {report['calls']}"]
    if report.get("aborted"):
        lines.append(f"  ⛔ 中止：{report['aborted']}")
    for item in report["failed"][:5]:
        lines.append(f"  ✗ {item['ticker']} {item['report']}：{item['reason']}")
    for ticker, r in sorted(report["tickers"].items()):
        if r.get("outcome"):
            lines.append(f"  ✗ {ticker} {r['outcome']}：{r.get('absence')}")
            continue
        new = r.get("rows_new")
        lines.append(f"  {ticker} {r.get('corp_code')}｜清單 {r['reports_listed']} 期、用 {r['reports_used']}、跳過 {r['skipped']}"
                     f"｜列 {r['rows_built']}" + (f"（新 {new}）" if new is not None else "")
                     + f" {dict(sorted(r['metrics'].items()))}｜第四季推 {r['q4_derived']}、缺 {len(r['q4_missing'])}"
                     f"｜拒寫 {len(r['rejected'])}｜晚知道 {len(r['late_known'])} 期｜最新期末 {r['latest_period_end']}"
                     f"（filed {r['latest_filed']}）")
        for item in r["rejected"][:5]:
            lines.append(f"     ⚠ {item['report']} {item['metric']}：{item['reason']}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="韓國 OpenDART 定期報告 → fundamental_history（可重建投影）")
    parser.add_argument("--backfill", action="store_true", help="5 年定期報告（快取優先）並寫入")
    parser.add_argument("--sync", action="store_true", help="清單重抓、期末 400 天內的報告重抓並寫入")
    parser.add_argument("--refresh", action="store_true", help="所有報告都重抓（不用快取）")
    parser.add_argument("--ticker", nargs="*", help="只跑／只印這幾檔（.KS／.KQ）")
    parser.add_argument("--dry-run", action="store_true", help="不寫庫，印會寫的列")
    parser.add_argument("--replace", action="store_true", help="寫入前先刪這幾檔 source=opendart:// 的列（整檔重建）")
    parser.add_argument("--db", help="SQLite 路徑（省略＝正式庫）")
    parser.add_argument("--report", help="完整報告寫到這個 JSON 檔")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if not (args.backfill or args.sync):
        if not args.ticker:
            parser.error("沒有 --backfill／--sync 時要給 --ticker（印已存序列）")
        from engine_c.history_backfill import _open

        conn = _open(args.db)
        try:
            for ticker in args.ticker:
                rows = stored_series(conn, ticker.upper())
                print(f"{ticker.upper()}：{len(rows)} 列（source=opendart://）")
                for r in rows:
                    print(f"  {r['metric']:<24} {r['period_start'] or '':<10} → {r['period_end']}  filed {r['filed']}  "
                          f"{r['value']:>22,.0f} {r['currency']}  {r['accession']} {r['form']}"
                          + (f"  ⟨{r['derived']}⟩" if r["derived"] else ""))
        finally:
            conn.close()
        return 0
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    report = run(tickers=args.ticker, mode="sync" if args.sync else "backfill", dry_run=args.dry_run,
                 replace=args.replace, refresh_all=args.refresh, db=args.db)
    out = Path(args.report) if args.report else CACHE_DIR / "last_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if not args.dry_run:      # 心跳讀的是最近一輪**正式寫入**的那份（乾跑不算數）
        (CACHE_DIR / "last_write_report.json").write_text(json.dumps(report, ensure_ascii=False, default=str),
                                                          encoding="utf-8")
    print("\n".join(_summary_lines(report)))
    print(f"完整報告：{out}")
    return 1 if report.get("aborted") or (report.get("write") or {}).get("outcome") not in ("written", "dry_run") else 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FLOW_IDS", "INSTANT_IDS", "REPORT_CODES", "build_report_rows", "collect", "derive_fourth_quarter",
    "parse_report_name", "period_of", "run", "stored_series", "write",
]
