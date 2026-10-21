"""
edinet_history.py — 日本 EDINET 半期・有價證券報告書 → Engine C `fundamental_history`（日韓財報來源 S2，2026-10-21）。

**它回答的只有一件事：T 時刻市場已經從法定申報知道這家日本公司的半年營收、營業利益、現金與股數是多少。**
已定價①（自家三年 P/S 百分位）與「出現在數字裡了嗎」要的就是這幾個數；日本 2024-04 起沒有 Q1／Q3 法定申報，
所以序列是**半年**：上半年取半期報告書（2024 以前取第 2 季四半期報告書的 6 個月累計）、下半年＝年度−上半年（標 derived）。

## 期間與 context 一律由 DEI 決定（2026-10-21 實測推翻計畫書原設計）

- 書類一覧的 `periodStart／End` 不能用（160 是整個會計年度、140 是單季、訂正書是 null）。期間＝DEI
  `CurrentFiscalYearStartDateDEI` → `CurrentPeriodEndDateDEI`。
- context 由 DEI `TypeOfCurrentPeriodDEI` 選（`CONTEXTS`），**docType 不參與**：6594 S100UOHJ 列在 160（半期報告書）、
  taxonomy 卻是 q2r、DEI 是 Q2、context 是 `CurrentYTDDuration`。
- 只收**不帶後綴**的 context：分部資料帶 member 後綴（3110 分部合計 67,761 百萬 ≠ 連結 57,412 百萬）。

## 白名單與拒寫（L15：放寬解析不等於放寬判準）

- 會計基準只收 Japan GAAP 與 IFRS（`STANDARDS`）；只收連結（`jppfs_cor` 的列還要「連結・個別」＝連結）。
- 同一期、同一份申報裡白名單元素給出不同的數 → 那個指標整筆拒寫、列進報告，不挑一個看起來對的。
- 總借款沒有白名單（計畫 Q3 A：13 檔都沒有整行總額，只有流動／非流動分列）——淨負債缺席，已定價①用 P/S。
- 股數＝期末發行（議決権の状況，不帶後綴）− **自己保有**株式（`OWN_TREASURY_SUFFIXES`）；**不扣**「自己株式等合計」
  （相互保有在 7/18 份出現，法律上仍是流通股；3110：1,144,700 ≠ 1,142,300）。自己保有是 `－` → 0（5016：明確為 0）；
  自己保有那一行不在 → 拒寫（不補 0）。期末發行與「事業年度末現在発行数」對不上、或出現普通股以外的股類 → 拒寫。
  除權日落在期末前 10 天內的那一期由讀取端整期不用（`engine_c.three_question_inputs.split_near_period_end`）。

## 可知日（INV-6）

`filed`＝書類一覧 `submitDateTime` 的日期（JST），只到日（同 EDGAR 的限制）。訂正報告書各存一列（accession＝自己的 docID），
as-of 讀取取 `filed ≤ T` 的最新版。下半年在**每個改變它的時點**各存一列：年度報告交件時、之後上半年或年度又被訂正時；
每一列的 filed＝觸發它的那份申報（`derive_second_half`）——不得拿 T 之後才交的上半年訂正去算 T 時的下半年。

## 為什麼是可重建的投影（L10）

EDINET 保存 10 年、今天重抓拿得回來：寫進 `fundamental_history`，`--replace` 可整檔重建（只刪 `source=edinet://` 的列）。
不進 daily：兩個海外來源都永久可查、漏抓補得回來，也不把 API key 放進無人值守路徑（`tests/test_codex_daily_permissions.py`）。

## INV-3：每一份看到的書類都落到一個具名結局

`docs_seen_by_type`、`skipped{…}`、`rejected[]`、`h2_missing_h1[]`、`rows_built`／`rows_new`；整輪
`dates_scanned／cached／failed／unscanned`、`calls`、`aborted`。中止（401、限流）時沒掃的日期與沒抓的書類照數印出。

用法::

    python -m engine_c.edinet_history --backfill                          # 名冊全部 .T（書類一覧逐日掃，可續跑）
    python -m engine_c.edinet_history --backfill --ticker 3110.T --dry-run --since 2025-11-01 --until 2025-11-20
    python -m engine_c.edinet_history --sync                              # 重掃最近 30 天＋沒掃過的日期
    python -m engine_c.edinet_history --ticker 3110.T                     # 印已存序列（不連網）
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine_c.history_backfill import (  # noqa: E402
    EDINET_FORM_PREFIX, FUNDAMENTAL_LOOKBACK_YEARS, SOURCE_EDINET, insert_fundamentals, late_metrics_supported)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "library" / "private" / "engine_c" / "edinet"
JST = timezone(timedelta(hours=9))          # 日本沒有日光節約時間
CODELIST_MAX_AGE_DAYS = 7
SYNC_RESCAN_DAYS = 30
#: 掃描起點＝今天 − 5 年 − 這幾天：最早那個年度的上半年（12 月決算的公司 8 月交）也要掃到，下半年才推得出來。
SCAN_MARGIN_DAYS = 120
HALF_METRICS = ("revenue_half", "operating_income_half")
NIL = "－"

#: DEI `TypeOfCurrentPeriodDEI` → (期間 context, 時點 context, 期間種類)。**docType 不參與**（S100UOHJ）。
CONTEXTS: Mapping[str, tuple[str, str, str]] = {
    "FY": ("CurrentYearDuration", "CurrentYearInstant", "annual"),
    "HY": ("InterimDuration", "InterimInstant", "half"),
    "Q2": ("CurrentYTDDuration", "CurrentQuarterInstant", "half"),
}
QUARTER_PERIOD_TYPES = ("Q1", "Q3")
SPAN_DAYS: Mapping[str, tuple[int, int]] = {"annual": (350, 380), "half": (160, 200)}
STANDARDS = ("Japan GAAP", "IFRS")
#: 期間型白名單。摘要元素（`…SummaryOfBusinessResults`）排最後：與報表元素並列當交叉核對，tag 取報表元素。
FLOW_TAGS: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "revenue": {
        "Japan GAAP": ("jppfs_cor:NetSales", "jpcrp_cor:NetSalesSummaryOfBusinessResults"),
        "IFRS": ("jpigp_cor:RevenueIFRS", "jpigp_cor:Revenue2IFRS", "jpigp_cor:NetSalesIFRS",
                 "jpcrp_cor:RevenueIFRSSummaryOfBusinessResults"),
    },
    "operating_income": {
        "Japan GAAP": ("jppfs_cor:OperatingIncome",),
        "IFRS": ("jpigp_cor:OperatingProfitLossIFRS",),
    },
}
INSTANT_TAGS: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "cash": {"Japan GAAP": ("jppfs_cor:CashAndCashEquivalents",),
             "IFRS": ("jpigp_cor:CashAndCashEquivalentsIFRS",)},
}
SHARES_ISSUED = "jpcrp_cor:NumberOfSharesIssuedSharesVotingRights"
#: 自己保有株式（完全議決権株式の自己株式等）：拆分版（14/18 份）與沒拆分版（6501 兩份、5802）。**不含相互保有。**
OWN_TREASURY_SUFFIXES = ("_OrdinarySharesTreasurySharesSharesWithFullVotingRightsTreasurySharesEtcMember",
                         "_OrdinarySharesSharesWithFullVotingRightsTreasurySharesEtcMember")
RESTRICTED_TREASURY_SUFFIX = "_SharesWithRestrictedVotingRightsTreasurySharesEtcMember"
ISSUED_CROSS_CHECK = "jpcrp_cor:NumberOfIssuedSharesAsOfFiscalYearEndIssuedSharesTotalNumberOfSharesEtc"
ORDINARY_SHARE_CONTEXTS = ("FilingDateInstant", "FilingDateInstant_OrdinaryShareMember")
SHARES_DERIVED = "發行（議決権の状況）−自己保有株式（相互保有與信託持有不扣）"
DEI_FIELDS = ("TypeOfCurrentPeriodDEI", "CurrentPeriodEndDateDEI", "CurrentFiscalYearStartDateDEI",
              "CurrentFiscalYearEndDateDEI", "AccountingStandardsDEI",
              "WhetherConsolidatedFinancialStatementsArePreparedDEI", "EDINETCodeDEI", "SecurityCodeDEI",
              "AmendmentFlagDEI", "NumberOfSubmissionDEI", "IdentificationOfDocumentSubjectToAmendmentDEI")
#: 文件快取只留這些元素的列（全部 context，讓規則改了也能從快取重建）。
KEPT_ELEMENTS = frozenset(
    [t for spec in (*FLOW_TAGS.values(), *INSTANT_TAGS.values()) for tags in spec.values() for t in tags]
    + [SHARES_ISSUED, ISSUED_CROSS_CHECK])


class EdinetHistoryError(RuntimeError):
    """輸入不合法（不是「抓不到」——抓不到記進報告，不 raise）。"""


# ---------------------------------------------------------------------------
# 純函式：一份書類 → 列
# ---------------------------------------------------------------------------

def extract(csv_rows: Iterable[Any]) -> dict[str, Any]:
    """`fetchers.edinet.parse_csv_zip` 的列 → `{dei, rows}`（文件快取的形狀；rows＝[元素, context, 連結・個別, 單位, 值]）。"""
    dei: dict[str, str] = {}
    rows: list[list[str]] = []
    for r in csv_rows:
        if r.element.startswith("jpdei_cor:"):
            name = r.element.split(":", 1)[1]
            if name in DEI_FIELDS:
                dei.setdefault(name, r.value)
        elif r.element in KEPT_ELEMENTS:
            rows.append([r.element, r.context, r.consolidation, r.unit, r.value])
    return {"dei": dei, "rows": rows}


def _iso(text: Any) -> date | None:
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def doc_outcome(dei: Mapping[str, Any]) -> str | None:
    """這份書類用不用得了（None＝用得了）。依序判，第一個不過的就是結局（INV-3：每份都有一個具名結局）。"""
    kind = str(dei.get("TypeOfCurrentPeriodDEI") or "")
    if kind in QUARTER_PERIOD_TYPES:
        return "quarter_not_used"
    if kind not in CONTEXTS:
        return "unknown_period_type"
    if str(dei.get("AccountingStandardsDEI") or "") not in STANDARDS:
        return "unsupported_standard"
    if str(dei.get("WhetherConsolidatedFinancialStatementsArePreparedDEI") or "").lower() != "true":
        return "non_consolidated"
    start, end = _iso(dei.get("CurrentFiscalYearStartDateDEI")), _iso(dei.get("CurrentPeriodEndDateDEI"))
    if start is None or end is None:
        return "period_unparseable"
    lo, hi = SPAN_DAYS[CONTEXTS[kind][2]]
    if not lo <= (end - start).days <= hi:
        return "irregular_fiscal_year" if CONTEXTS[kind][2] == "annual" else "irregular_half"
    return None


def _number(text: str) -> Decimal | None:
    try:
        value = Decimal(str(text).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return value if value.is_finite() else None


def _currency(units: set[str]) -> str | None:
    if len(units) != 1:
        return None
    unit = next(iter(units))
    return unit if len(unit) == 3 and unit.isalpha() and unit.isupper() else None


@dataclass
class DocResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    nil_values: int = 0


def build_doc_rows(doc: Mapping[str, Any], *, ticker: str, edinet_code: str, sec5: str, doc_id: str, doc_type: str,
                   filed: date, fetched_at: str) -> tuple[str | None, DocResult]:
    """一份書類（`extract` 的形狀）→ `(跳過理由或 None, DocResult)`。**純函式**：不連網、不寫檔。

    年度報告的營收／營業利益產出 `*_annual` 列——**只給 `derive_second_half` 用，不寫進表**（日本序列是半年；寫了年度列，
    三題的年度分支會把它標成 SEC companyfacts——L18）。
    """
    dei = doc.get("dei") or {}
    skip = doc_outcome(dei)
    result = DocResult()
    if skip is not None:
        return skip, result
    if str(dei.get("EDINETCodeDEI") or "") != edinet_code or str(dei.get("SecurityCodeDEI") or "") not in (sec5, NIL, ""):
        result.rejected.append({"doc_id": doc_id, "metric": "*", "reason": (
            f"DEI 身分對不上（EDINETCode={dei.get('EDINETCodeDEI')}、SecurityCode={dei.get('SecurityCodeDEI')}；"
            f"預期 {edinet_code}／{sec5}）——整份不用（INV-1）")})
        return None, result
    kind = str(dei["TypeOfCurrentPeriodDEI"])
    duration_ctx, instant_ctx, span = CONTEXTS[kind]
    standard = str(dei["AccountingStandardsDEI"])
    start, end = _iso(dei["CurrentFiscalYearStartDateDEI"]), _iso(dei["CurrentPeriodEndDateDEI"])
    rows = [list(r) for r in doc.get("rows") or ()]
    base = {"ticker": ticker, "filed": filed.isoformat(), "accession": doc_id, "form": f"{EDINET_FORM_PREFIX}{doc_type}",
            "unit_scale": 1, "source": SOURCE_EDINET, "fetched_at": fetched_at}

    def pick(concept: str, tags: Sequence[str], context: str) -> tuple[Decimal, str, str] | None:
        found: dict[Decimal, list[tuple[str, str]]] = {}
        for element, ctx, consolidation, unit, value in rows:
            if element not in tags or ctx != context:
                continue
            if element.startswith("jppfs_cor:") and consolidation != "連結":
                continue
            if value == NIL:
                result.nil_values += 1
                continue
            number = _number(value)
            if number is None:
                result.rejected.append({"doc_id": doc_id, "metric": concept, "reason": f"{element} 的值不是數字：{value!r}"})
                return None
            found.setdefault(number, []).append((element, unit))
        if not found:
            result.missing.append(concept)
            return None
        if len(found) > 1:
            result.rejected.append({"doc_id": doc_id, "metric": concept, "reason": (
                "白名單元素對同一期給出不同的數——不挑一個（"
                + "；".join(f"{'、'.join(sorted({e for e, _u in v}))}＝{k}" for k, v in sorted(found.items())) + "）")})
            return None
        number, hits = next(iter(found.items()))
        currency = _currency({u for _e, u in hits})
        if currency is None:
            result.rejected.append({"doc_id": doc_id, "metric": concept,
                                    "reason": f"單位不是單一 ISO 幣別：{sorted({u for _e, u in hits})}"})
            return None
        tag = next(t for t in tags if any(e == t for e, _u in hits))
        return number, currency, tag

    for concept, spec in FLOW_TAGS.items():
        got = pick(concept, spec[standard], duration_ctx)
        if got is not None:
            number, currency, tag = got
            result.rows.append({**base, "metric": f"{concept}_{span}", "period_start": start.isoformat(),
                                "period_end": end.isoformat(), "value": float(number), "currency": currency,
                                "derived": None, "tag": tag})
    for metric, spec in INSTANT_TAGS.items():
        got = pick(metric, spec[standard], instant_ctx)
        if got is not None:
            number, currency, tag = got
            result.rows.append({**base, "metric": metric, "period_start": None, "period_end": end.isoformat(),
                                "value": float(number), "currency": currency, "derived": None, "tag": tag})
    shares = _shares(rows, instant_ctx, doc_id=doc_id, result=result)
    if shares is not None:
        value, suffix = shares
        result.rows.append({**base, "metric": "shares_outstanding_cover", "period_start": None,
                            "period_end": end.isoformat(), "value": float(value), "currency": "shares",
                            "derived": SHARES_DERIVED, "tag": f"{SHARES_ISSUED}−{suffix.lstrip('_')}"})
    return None, result


def _shares(rows: Sequence[Sequence[str]], instant_ctx: str, *, doc_id: str, result: DocResult) -> tuple[int, str] | None:
    """期末發行 − 自己保有株式。任何一步對不上就拒寫（不補 0、不挑一個）。"""
    def reject(reason: str) -> None:
        result.rejected.append({"doc_id": doc_id, "metric": "shares_outstanding_cover", "reason": reason})

    def values(element: str, context: str) -> set[str]:
        return {v for e, c, _k, _u, v in rows if e == element and c == context}

    issued_raw = values(SHARES_ISSUED, instant_ctx)
    if not issued_raw:
        result.missing.append("shares_outstanding_cover")
        return None
    issued_nums = {_number(v) for v in issued_raw}
    if len(issued_raw) != 1 or None in issued_nums:
        reject(f"期末發行股數不是單一數字：{sorted(issued_raw)}")
        return None
    issued = int(next(iter(issued_nums)))
    restricted = values(SHARES_ISSUED, instant_ctx + RESTRICTED_TREASURY_SUFFIX)
    if restricted - {NIL}:
        reject(f"議決権制限株式（自己株式等）有值 {sorted(restricted)}——口徑不明，不扣也不加")
        return None
    own = {suffix: values(SHARES_ISSUED, instant_ctx + suffix) for suffix in OWN_TREASURY_SUFFIXES}
    present = [s for s, v in own.items() if v]
    if len(present) != 1:
        reject("自己保有株式那一行" + ("不在——不補 0" if not present else "兩種寫法都出現——不挑一個"))
        return None
    suffix = present[0]
    own_raw = own[suffix]
    if len(own_raw) != 1:
        reject(f"自己保有株式不是單一值：{sorted(own_raw)}")
        return None
    own_text = next(iter(own_raw))
    own_number = Decimal(0) if own_text == NIL else _number(own_text)
    if own_number is None:
        reject(f"自己保有株式不是數字：{own_text!r}")
        return None
    classes = {c for e, c, _k, _u, _v in rows if e == ISSUED_CROSS_CHECK}
    other = sorted(c for c in classes if c not in ORDINARY_SHARE_CONTEXTS)
    if other:
        reject(f"出現普通股以外的股類 {other}——多股類不加總")
        return None
    cross = {_number(v) for e, c, _k, _u, v in rows if e == ISSUED_CROSS_CHECK and c in ORDINARY_SHARE_CONTEXTS}
    if cross and cross != {Decimal(issued)}:
        reject(f"期末發行 {issued:,} 與「事業年度末現在発行数」{sorted(str(x) for x in cross)} 對不上")
        return None
    value = issued - int(own_number)
    if value <= 0:
        reject(f"發行 {issued:,} − 自己保有 {int(own_number):,} ≤ 0")
        return None
    return value, suffix


def derive_second_half(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """年度列 − 上半年列 → 下半年列（標 derived）。回 `(下半年列, 缺上半年的年度)`。**純函式**。

    每個會計年度在**每個改變下半年的時點**各產生一列：時點＝年度或上半年（含訂正）的 (filed, accession)，
    且不早於第一份年度報告；那一刻的下半年＝當時已知最新的年度 − 當時已知最新的上半年。值沒變就不另存一列。
    filed＝觸發它的那份申報的 filed（INV-6：T 之後才交的上半年訂正不得用來算 T 時的下半年）。
    """
    out: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for concept in FLOW_TAGS:
        annual = [r for r in rows if r["metric"] == f"{concept}_annual"]
        halves = [r for r in rows if r["metric"] == f"{concept}_half" and not r.get("derived")]
        groups: dict[tuple, list[Mapping[str, Any]]] = {}
        for r in annual:
            groups.setdefault((r["period_start"], r["period_end"], r["currency"]), []).append(r)
        for (start, end, currency), fys in sorted(groups.items()):
            h1s = [h for h in halves if h["period_start"] == start and h["period_end"] < end and h["currency"] == currency]
            if len({h["period_end"] for h in h1s}) > 1:
                missing.append({"metric": concept, "fiscal_year": f"{start}→{end}",
                                "reason": f"同一年度有多個上半年期末 {sorted({h['period_end'] for h in h1s})}——不挑一個"})
                continue
            key = lambda r: (str(r["filed"]), str(r["accession"]))  # noqa: E731
            fys = sorted(fys, key=key)
            h1s = sorted(h1s, key=key)
            first = key(fys[0])
            events = sorted({key(r): r for r in (*fys, *h1s) if key(r) >= first}.items())
            last_value = None
            for event, trigger in events:
                fy = [r for r in fys if key(r) <= event][-1]
                known = [h for h in h1s if key(h) <= event]
                if not known:
                    if last_value is None and not any(m.get("fiscal_year") == f"{start}→{end}" and m["metric"] == concept
                                                      for m in missing):
                        missing.append({"metric": concept, "fiscal_year": f"{start}→{end}", "annual_doc": fy["accession"],
                                        "reason": "年度報告交件時還沒有同一年度的上半年——下半年推不出來（不估）"})
                    continue
                h1 = known[-1]
                value = fy["value"] - h1["value"]
                if value == last_value:
                    continue
                last_value = value
                h1_end = date.fromisoformat(h1["period_end"])
                out.append({**{k: trigger[k] for k in ("ticker", "filed", "accession", "form", "unit_scale", "source",
                                                       "fetched_at")},
                            "metric": f"{concept}_half", "period_start": (h1_end + timedelta(days=1)).isoformat(),
                            "period_end": end, "value": value, "currency": currency, "tag": fy["tag"],
                            "derived": f"FY−H1：{fy['accession']}（{fy['tag']}）−{h1['accession']}（{h1['tag']}）"})
    return out, missing


def finalize_rows(rows: Sequence[Mapping[str, Any]], *, today: date) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """一檔全部書類的列 → 寫進表的列：推下半年、拿掉年度列（只給推算用）、套 5 年視窗。"""
    h2, missing = derive_second_half(rows)
    horizon = today - timedelta(days=365 * FUNDAMENTAL_LOOKBACK_YEARS)
    kept = [dict(r) for r in (*rows, *h2) if not r["metric"].endswith("_annual")
            and date.fromisoformat(r["period_end"]) >= horizon]
    dropped = sum(1 for r in (*rows, *h2) if not r["metric"].endswith("_annual")) - len(kept)
    return kept, {"h2_derived": len(h2), "h2_missing_h1": missing, "outside_window": dropped}


# ---------------------------------------------------------------------------
# 快取（library/private；原檔不留，只留白名單列）
# ---------------------------------------------------------------------------

def _list_path(cache_dir: Path, day: date) -> Path:
    return cache_dir / "lists" / f"{day.year}" / f"{day.isoformat()}.json.gz"


def _read_list(cache_dir: Path, day: date) -> dict[str, Any] | None:
    path = _list_path(cache_dir, day)
    if not path.exists():
        return None
    try:
        return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
    except (OSError, ValueError):
        return None


def _write_list(cache_dir: Path, day: date, body: Mapping[str, Any], *, fetched_at: str) -> None:
    path = _list_path(cache_dir, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"date": day.isoformat(), "fetched_at": fetched_at, **body}
    path.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8")))


def _list_settled(entry: Mapping[str, Any], day: date) -> bool:
    """那一天的書類一覧是在那天過完（JST）之後抓的才算定案；當天或隔天抓的下一輪重抓。"""
    try:
        fetched = datetime.fromisoformat(str(entry.get("fetched_at"))).astimezone(JST).date()
    except ValueError:
        return False
    return fetched > day + timedelta(days=1)


def _doc_path(cache_dir: Path, doc_id: str) -> Path:
    return cache_dir / "docs" / f"{doc_id}.json"


def _read_doc(cache_dir: Path, doc_id: str) -> dict[str, Any] | None:
    path = _doc_path(cache_dir, doc_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_doc(cache_dir: Path, doc_id: str, payload: Mapping[str, Any]) -> None:
    path = _doc_path(cache_dir, doc_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load_codelist(cache_dir: Path, *, today: date, fetch: Any = None) -> tuple[list[dict[str, str]], str]:
    """コードリスト（不需 key）：快取超過 7 天就重抓；抓不到用舊的並註明。"""
    from fetchers.edinet import EdinetUnavailable, codelist_rows, fetch_codelist

    path = cache_dir / "Edinetcode.zip"
    fresh = path.exists() and (today - datetime.fromtimestamp(path.stat().st_mtime).date()).days <= CODELIST_MAX_AGE_DAYS
    note = "cache"
    if not fresh:
        try:
            data = (fetch or fetch_codelist)()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            note = "fetched"
        except EdinetUnavailable as exc:
            if not path.exists():
                raise
            note = f"stale_cache（{exc}）"
    return codelist_rows(path.read_bytes()), note


# ---------------------------------------------------------------------------
# 編排
# ---------------------------------------------------------------------------

def jp_universe() -> list[str]:
    from identity.registry import TICKER_MAP

    return sorted({t for t in TICKER_MAP.values() if t and t.endswith(".T")})


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def scan_lists(client: Any, days: Sequence[date], *, cache_dir: Path, force: Iterable[date] = (),
               fetched_at: str) -> tuple[dict[date, list[dict[str, Any]]], dict[str, Any]]:
    """逐日書類一覧（快取優先）。中止（401、限流）後剩下的日期照用快取（若有）並計數為沒掃（INV-3）。"""
    from fetchers.edinet import EdinetAuthError, EdinetRateLimited, EdinetUnavailable

    force = set(force)
    entries: dict[date, list[dict[str, Any]]] = {}
    report: dict[str, Any] = {"dates_total": len(days), "dates_cached": 0, "dates_fetched": 0, "dates_failed": [],
                              "dates_unscanned": 0, "aborted": None}
    for day in days:
        cached = _read_list(cache_dir, day)
        if cached is not None and day not in force and _list_settled(cached, day):
            entries[day] = list(cached.get("results") or ())
            report["dates_cached"] += 1
            continue
        if report["aborted"]:
            report["dates_unscanned"] += 1
            if cached is not None:
                entries[day] = list(cached.get("results") or ())
            continue
        try:
            body = client.list_documents(day)
        except (EdinetAuthError, EdinetRateLimited) as exc:
            report["aborted"] = str(exc)
            report["dates_unscanned"] += 1
            if cached is not None:
                entries[day] = list(cached.get("results") or ())
            continue
        except EdinetUnavailable as exc:
            report["dates_failed"].append({"date": day.isoformat(), "reason": str(exc)})
            if cached is not None:
                entries[day] = list(cached.get("results") or ())
            continue
        _write_list(cache_dir, day, body, fetched_at=fetched_at)
        entries[day] = list(body["results"])
        report["dates_fetched"] += 1
    return entries, report


def _load_doc(client: Any, doc_id: str, *, cache_dir: Path, fetched_at: str) -> dict[str, Any]:
    """文件快取優先；抓到就只存白名單列。404 也快取（取下或沒有 CSV 是永久的）。"""
    from fetchers.edinet import EdinetDocMissing, EdinetUnavailable, parse_csv_zip

    cached = _read_doc(cache_dir, doc_id)
    if cached is not None:
        return {**cached, "_cached": True}
    try:
        data = client.fetch_csv_zip(doc_id)
    except EdinetDocMissing as exc:
        payload = {"doc_id": doc_id, "fetched_at": fetched_at, "error": "doc_missing", "detail": str(exc)}
        _write_doc(cache_dir, doc_id, payload)
        return payload
    try:
        parsed = extract(parse_csv_zip(data))
    except EdinetUnavailable as exc:
        payload = {"doc_id": doc_id, "fetched_at": fetched_at, "error": "csv_unparseable", "detail": str(exc)}
        _write_doc(cache_dir, doc_id, payload)
        return payload
    payload = {"doc_id": doc_id, "fetched_at": fetched_at, **parsed}
    _write_doc(cache_dir, doc_id, payload)
    return payload


def collect(client: Any, *, tickers: Sequence[str], days: Sequence[date], today: date, cache_dir: Path = CACHE_DIR,
            force: Iterable[date] = (), codelist: Sequence[Mapping[str, str]] | None = None,
            fetched_at: str | None = None) -> dict[str, Any]:
    """掃書類一覧 → 抓名冊各檔的定期報告 → 每檔的列（還沒寫）。回 `{run, tickers: {t: {rows, report}}}`。"""
    from fetchers.edinet import EdinetAuthError, EdinetRateLimited, EdinetUnavailable, edinet_code_for

    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    run: dict[str, Any] = {}
    if codelist is None:
        codelist, run["codelist"] = load_codelist(cache_dir, today=today)
    per: dict[str, dict[str, Any]] = {}
    code_of: dict[str, str] = {}
    for ticker in tickers:
        report: dict[str, Any] = {"docs_seen_by_type": {}, "docs_used": 0, "skipped": {}, "rejected": [],
                                  "missing": {}, "nil_values": 0}
        per[ticker] = {"rows": [], "report": report}
        try:
            code_of[ticker] = edinet_code_for(ticker.split(".")[0], list(codelist))
            report["edinet_code"] = code_of[ticker]
        except LookupError as exc:
            report.update(outcome="edinet_code_unresolved", absence=str(exc))
    entries, scan = scan_lists(client, days, cache_dir=cache_dir, force=force, fetched_at=fetched_at)
    run.update(scan)
    ticker_of = {code: t for t, code in code_of.items()}
    # 同一份書類會在之後某天的書類一覧重列（書類資訊修正、取下）——以 docID 去重，留**較晚那天**列表上的那一筆
    # （取下與修正狀態以最新的為準；submitDateTime 不變）。10-21 實測 6268 S100WHTQ 列在兩天、被處理兩次。
    latest: dict[str, dict[str, Any]] = {}
    relisted = 0
    for day in sorted(entries):
        for e in entries[day]:
            if e.get("edinetCode") not in ticker_of:
                continue
            doc_id = str(e.get("docID") or "")
            relisted += int(doc_id in latest)
            latest[doc_id] = e
    docs = sorted(latest.values(), key=lambda e: (str(e.get("submitDateTime")), str(e.get("docID"))))
    run.update(docs_fetched=0, docs_cached=0, docs_unfetched=0, docs_failed=[], docs_relisted=relisted)
    aborted = run.get("aborted")
    for entry in docs:
        ticker = ticker_of[entry["edinetCode"]]
        report = per[ticker]["report"]
        doc_id, doc_type = str(entry.get("docID") or ""), str(entry.get("docTypeCode") or "")
        seen = report["docs_seen_by_type"]
        seen[doc_type] = seen.get(doc_type, 0) + 1
        skipped = report["skipped"]
        if str(entry.get("withdrawalStatus") or "0") != "0":
            skipped["withdrawn"] = skipped.get("withdrawn", 0) + 1
            continue
        if str(entry.get("csvFlag") or "0") != "1":
            skipped["no_csv"] = skipped.get("no_csv", 0) + 1
            continue
        filed = _iso(entry.get("submitDateTime"))
        if filed is None:
            report["rejected"].append({"doc_id": doc_id, "metric": "*",
                                       "reason": f"submitDateTime 解析不了：{entry.get('submitDateTime')!r}——不猜可知日"})
            continue
        if aborted and _read_doc(cache_dir, doc_id) is None:
            run["docs_unfetched"] += 1
            continue
        try:
            doc = _load_doc(client, doc_id, cache_dir=cache_dir, fetched_at=fetched_at)
        except (EdinetAuthError, EdinetRateLimited) as exc:
            aborted = run["aborted"] = str(exc)
            run["docs_unfetched"] += 1
            continue
        except EdinetUnavailable as exc:
            run["docs_failed"].append({"doc_id": doc_id, "ticker": ticker, "reason": str(exc)})
            continue
        run["docs_cached" if doc.pop("_cached", False) else "docs_fetched"] += 1
        if doc.get("error"):
            skipped[doc["error"]] = skipped.get(doc["error"], 0) + 1
            continue
        skip, result = build_doc_rows(doc, ticker=ticker, edinet_code=code_of[ticker],
                                      sec5=f"{ticker.split('.')[0]}0", doc_id=doc_id, doc_type=doc_type,
                                      filed=filed, fetched_at=fetched_at)
        if skip is not None:
            skipped[skip] = skipped.get(skip, 0) + 1
            continue
        report["docs_used"] += 1
        report["rejected"] += result.rejected
        report["nil_values"] += result.nil_values
        for concept in result.missing:
            report["missing"][concept] = report["missing"].get(concept, 0) + 1
        per[ticker]["rows"] += result.rows
    for ticker, body in per.items():
        if "outcome" in body["report"]:
            continue
        rows, derivation = finalize_rows(body["rows"], today=today)
        body["rows"] = rows
        body["report"].update(derivation, rows_built=len(rows),
                              metrics=dict(Counter(r["metric"] for r in rows)),
                              latest_period_end=max((r["period_end"] for r in rows), default=None),
                              latest_filed=max((r["filed"] for r in rows), default=None))
    run["calls"] = getattr(client, "calls", None)
    run["aborted"] = aborted
    return {"run": run, "tickers": per}


def write(conn: Any, collected: Mapping[str, Any], *, replace: bool = False) -> dict[str, Any]:
    """寫入（呼叫端持 writer lock）。CHECK 還不認得半年字彙 → 整輪不寫、給具名結局（附遷移命令）。"""
    if not late_metrics_supported(conn, HALF_METRICS):
        return {"outcome": "check_not_migrated",
                "reason": "fundamental_history 的 CHECK 還不認得 revenue_half／operating_income_half——"
                          "先跑 python -m engine_c.migrate_fundamental_metrics --apply"}
    out: dict[str, Any] = {"outcome": "written", "rows_new": {}, "rows_replaced": {}}
    for ticker, body in collected["tickers"].items():
        if "outcome" in body["report"]:
            continue
        if replace:
            cur = conn.execute("DELETE FROM fundamental_history WHERE ticker = ? AND source = ?", (ticker, SOURCE_EDINET))
            out["rows_replaced"][ticker] = cur.rowcount
        new = insert_fundamentals(conn, body["rows"])
        body["report"]["rows_new"] = new
        out["rows_new"][ticker] = new
    conn.commit()
    return out


def run(*, tickers: Sequence[str] | None, mode: str, dry_run: bool, replace: bool = False, since: date | None = None,
        until: date | None = None, db: str | None = None, client: Any = None, today: date | None = None,
        cache_dir: Path = CACHE_DIR) -> dict[str, Any]:
    today = today or datetime.now(JST).date()
    start = since or (today - timedelta(days=365 * FUNDAMENTAL_LOOKBACK_YEARS + SCAN_MARGIN_DAYS))
    end = min(until or today, today)
    if start > end:
        raise EdinetHistoryError(f"掃描區間是空的：{start} → {end}")
    universe = jp_universe()
    chosen = sorted({t.upper() for t in tickers}) if tickers else universe
    unknown = [t for t in chosen if t not in universe]
    if unknown:
        raise EdinetHistoryError(f"不是名冊裡的 .T：{unknown}")
    if client is None:
        from fetchers.edinet import Client, api_key

        client = Client(api_key())
    force = [d for d in _days(start, end) if mode == "sync" and d >= today - timedelta(days=SYNC_RESCAN_DAYS)]
    collected = collect(client, tickers=chosen, days=_days(start, end), today=today, cache_dir=cache_dir, force=force)
    report = {"mode": mode, "dry_run": dry_run, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "window": [start.isoformat(), end.isoformat()], **collected["run"],
              "tickers": {t: b["report"] for t, b in collected["tickers"].items()}}
    if dry_run:
        report["write"] = {"outcome": "dry_run"}
        report["rows_preview"] = {t: b["rows"] for t, b in collected["tickers"].items()}
        return report
    from engine_b.writer_lock import INTERACTIVE_OWNER, hold
    from engine_c.history_backfill import _open

    conn = _open(db)
    try:
        with hold(INTERACTIVE_OWNER, ttl_minutes=15, purpose="EDINET 回填寫入 fundamental_history"):
            report["write"] = write(conn, collected, replace=replace)
    finally:
        conn.close()
    return report


#: 法定期限：有價證券報告書＝年度結束後 3 個月；半期報告書＝上半年結束後 45 日（2024-04 新制）。
ANNUAL_FORMS = (f"{EDINET_FORM_PREFIX}120", f"{EDINET_FORM_PREFIX}130")


def _add_months(day: date, months: int) -> date:
    import calendar

    total = day.year * 12 + day.month - 1 + months
    year, month = divmod(total, 12)
    return date(year, month + 1, calendar.monthrange(year, month + 1)[1])


def filing_freshness(conn: Any, tickers: Sequence[str], *, today: date) -> dict[str, Any]:
    """心跳段 1 的「日本」那半行（零網路，只讀本機）。「落後」與「抓到了但營收不能用」分開（L13-2：修法不同）：

    - 落後：已抓到的最新一期（不分指標）之後的下一期已過法定期限、表上還沒有——`--sync` 修得了；
    - 營收不能用：抓到的最新一期沒有半年營收（下半年推不出來、白名單拒寫）——`--sync` 修不了，看報告的拒寫與缺上半年。
    """
    out: dict[str, Any] = {"have": [], "empty": [], "lagging": [], "unusable": [], "latest": None}
    for ticker in tickers:
        rows = conn.execute("SELECT metric, period_end, form FROM fundamental_history WHERE ticker = ? AND source = ? "
                            "AND filed <= ?", (ticker, SOURCE_EDINET, today.isoformat())).fetchall()
        if not rows:
            out["empty"].append(ticker)
            continue
        end, form = max((str(r[1]), str(r[2])) for r in rows)
        latest = date.fromisoformat(end)
        revenue = max((str(r[1]) for r in rows if r[0] == "revenue_half"), default=None)
        if revenue is None:
            out["unusable"].append(f"{ticker}（沒有任何半年營收）")
            continue
        out["have"].append(ticker)
        if revenue < end:
            out["unusable"].append(f"{ticker}（{end} 那一期營收沒收）")
        nxt = _add_months(latest, 6)
        due = nxt + timedelta(days=45) if form in ANNUAL_FORMS else _add_months(nxt, 3)
        if today > due:
            out["lagging"].append(f"{ticker}（{nxt} 那一期，期限 {due}）")
        out["latest"] = max(out["latest"] or end, end)
    return out


def last_run_summary(cache_dir: Path = CACHE_DIR) -> dict[str, Any] | None:
    """最近一輪正式寫入的報告摘要（乾跑不算）：日期、拒寫筆數、是否中止。讀不到回 None。"""
    try:
        report = json.loads((cache_dir / "last_write_report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {"generated_at": report.get("generated_at"), "aborted": report.get("aborted"),
            "rejected": sum(len(t.get("rejected") or ()) for t in (report.get("tickers") or {}).values())}


def stored_series(conn: Any, ticker: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        """SELECT metric, period_start, period_end, filed, accession, form, value, currency, derived, tag
           FROM fundamental_history WHERE ticker = ? AND source = ? ORDER BY metric, period_end, filed, accession""",
        (ticker, SOURCE_EDINET))
    keys = ("metric", "period_start", "period_end", "filed", "accession", "form", "value", "currency", "derived", "tag")
    return [dict(zip(keys, r)) for r in cur.fetchall()]


def _summary_lines(report: Mapping[str, Any]) -> list[str]:
    lines = [f"EDINET {report['mode']}{'（乾跑）' if report.get('dry_run') else ''}｜區間 {report['window'][0]}→{report['window'][1]}"
             f"｜書類一覧 {report['dates_total']} 天：快取 {report['dates_cached']}、新抓 {report['dates_fetched']}、"
             f"失敗 {len(report['dates_failed'])}、沒掃 {report['dates_unscanned']}｜文件 新抓 {report['docs_fetched']}、"
             f"快取 {report['docs_cached']}、沒抓 {report['docs_unfetched']}、失敗 {len(report['docs_failed'])}、"
             f"重列去重 {report.get('docs_relisted', 0)}｜呼叫 {report['calls']}"]
    if report.get("aborted"):
        lines.append(f"  ⛔ 中止：{report['aborted']}")
    for ticker, r in sorted(report["tickers"].items()):
        if r.get("outcome"):
            lines.append(f"  ✗ {ticker} {r['outcome']}：{r.get('absence')}")
            continue
        new = r.get("rows_new")
        lines.append(f"  {ticker} {r.get('edinet_code')}｜看到 {dict(sorted(r['docs_seen_by_type'].items()))}、用 {r['docs_used']}、"
                     f"跳過 {dict(sorted(r['skipped'].items()))}｜列 {r['rows_built']}"
                     + (f"（新 {new}）" if new is not None else "")
                     + f" {dict(sorted(r['metrics'].items()))}｜下半年推 {r['h2_derived']}、缺上半年 {len(r['h2_missing_h1'])}"
                     f"｜拒寫 {len(r['rejected'])}｜最新期末 {r['latest_period_end']}（filed {r['latest_filed']}）")
        for item in r["rejected"][:5]:
            lines.append(f"     ⚠ {item['doc_id']} {item['metric']}：{item['reason']}")
    write_result = report.get("write") or {}
    if write_result.get("outcome") not in (None, "written", "dry_run"):
        lines.append(f"  ⛔ 沒寫：{write_result.get('outcome')}——{write_result.get('reason')}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="日本 EDINET 半期・有價證券報告書 → fundamental_history（可重建投影）")
    parser.add_argument("--backfill", action="store_true", help="掃 5 年書類一覧（快取優先、可續跑）並寫入")
    parser.add_argument("--sync", action="store_true", help="重掃最近 30 天＋沒掃過的日期並寫入")
    parser.add_argument("--ticker", nargs="*", help="只跑／只印這幾檔（.T）")
    parser.add_argument("--dry-run", action="store_true", help="不寫庫，印會寫的列")
    parser.add_argument("--replace", action="store_true", help="寫入前先刪這幾檔 source=edinet:// 的列（整檔重建）")
    parser.add_argument("--since", type=date.fromisoformat, help="掃描起日（預設 今天−5 年−120 天）")
    parser.add_argument("--until", type=date.fromisoformat, help="掃描迄日（預設 今天，JST）")
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
                print(f"{ticker.upper()}：{len(rows)} 列（source={SOURCE_EDINET}）")
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
                 replace=args.replace, since=args.since, until=args.until, db=args.db)
    out = Path(args.report) if args.report else CACHE_DIR / "last_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if not args.dry_run:      # 心跳讀的是最近一輪**正式寫入**的那份（乾跑不算數）
        (CACHE_DIR / "last_write_report.json").write_text(json.dumps(report, ensure_ascii=False, default=str),
                                                          encoding="utf-8")
    print("\n".join(_summary_lines(report)))
    print(f"完整報告：{out}")
    write_outcome = (report.get("write") or {}).get("outcome")
    return 1 if report.get("aborted") or write_outcome not in ("written", "dry_run") else 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONTEXTS", "FLOW_TAGS", "INSTANT_TAGS", "OWN_TREASURY_SUFFIXES", "SHARES_ISSUED", "build_doc_rows", "collect",
    "derive_second_half", "doc_outcome", "extract", "finalize_rows", "run", "scan_lists", "stored_series", "write",
]
