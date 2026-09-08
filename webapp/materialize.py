"""Materialize：`AlphaInvestmentView → AnalystView → MaterializedArtifact`。

**這是整個 APP 裡唯一會跑模型、連 DB、讀 private ledger 的地方。** serve 端不 import 本檔
（`tests/test_webapp_request_path.py` 逐條守著）。

## overview 是選取不是計算

`overview` 是清單卡片要用的那幾格。它**全部**取自已經算好的 `AnalystView`，
沒有任何算術：沒有百分比換算、沒有幣別換算、沒有 gap 重算。想在這裡「順手算一下」
就是在 canonical read model 之外生出第二份數字，而那是 Step 3.5 用型別層擋掉的事。

## private path 不出門

read model 裡有些理由句會寫出 authority 的檔案路徑（例如「找不到 session 判斷檔
（library/private/alpha/judgments/<TICKER>.json）」）。那對開發者有用，但它是 **private
filesystem 結構**，不該經由 HTTP 出去。`_redact_private_paths` 在寫檔前把它換成邏輯記號——
**在 materialize 端做一次**，而不是讓每個消費端各自記得要遮蔽（L16）。
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import (
    ARTIFACT_SCHEMA_VERSION, STATE_SCHEMA_VERSIONS, canonical_digest, freshness_identity,
    state_freshness_identity,
)
from .store import ArtifactStore, StateArtifactStore

MATERIALIZER_VERSION = "webapp-materialize/1"

#: 會被遮蔽的 private 路徑樣式。逐字保留其餘文字——遮蔽的目的是不洩漏 filesystem 結構，
#: 不是把理由變得看不懂。
_PRIVATE_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/])?(?:[\w.\-]+[\\/])*library[\\/]private[\\/][^\s（）()，,;；、\"']*")
_WINDOWS_ABS = re.compile(r"[A-Za-z]:\\[^\s（）()，,;；、\"']+")
_REDACTED = "«private-authority»"


def _redact_text(text: str) -> str:
    text = _PRIVATE_PATH.sub(_REDACTED, text)
    return _WINDOWS_ABS.sub(_REDACTED, text)


def redact_private_paths(value: Any) -> Any:
    """遞迴遮蔽 private filesystem 路徑。**只動字串內容，不動結構、不刪欄位。**"""
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, Mapping):
        return {k: redact_private_paths(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_private_paths(v) for v in value]
    return value


def _line_map(panel: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {line["key"]: line["datum"] for line in panel.get("lines", [])}


def _cell(datum: Mapping[str, Any] | None) -> dict[str, Any]:
    """一格的最小投影：值 ＋ 它的四種語意（狀態／為什麼沒有／單位／理由）。**照抄，不加工。**"""
    if datum is None:
        return {"value": None, "status": "missing", "absence_kind": "not_yet_recorded",
                "unit": None, "as_of": None, "reason": "read model 沒有這一格"}
    return {"value": datum.get("value"), "status": datum.get("status"),
            "absence_kind": datum.get("absence_kind"), "unit": datum.get("unit"),
            "as_of": datum.get("as_of"), "reason": datum.get("reason")}


def build_overview(view: Mapping[str, Any]) -> dict[str, Any]:
    """清單卡片的投影。**純選取**——這裡沒有任何算術。"""
    headline = view["headline"]
    lines = _line_map(headline)
    price = lines.get("current_price") or {}
    fair_value = lines.get("fair_value") or {}
    readiness = view["readiness"]
    blockers = list(readiness.get("blocker_details") or [])
    flags = list(readiness.get("flag_details") or [])
    # 「最重要的那一條」＝ blocker 優先於 flag，且維持 readiness 自己的順序（核心 panel 宣告序）。
    # 這是**挑選規則**不是嚴重度判斷——嚴重度序住在 `_WORST_FIRST`，這裡不重排。
    primary = (blockers or flags or [None])[0]
    return {
        "ticker": view["ticker"],
        "company_id": view.get("company_id"),
        "company_label": view.get("company_label"),
        "as_of": view.get("as_of"),
        "point_in_time_mode": view.get("point_in_time_mode"),
        "generated_on": view.get("generated_on"),
        "price": {**_cell(price),
                  "quote_unit": (price.get("dependencies") or {}).get("quote_unit")},
        "future_target": {**_cell(fair_value),
                          "currency": (fair_value.get("dependencies") or {}).get("currency"),
                          "value_date": _cell(lines.get("value_date"))},
        "implied_return": {"simple": _cell(lines.get("price_return")),
                           "annualized": _cell(lines.get("annualized_price_return"))},
        "readiness": {"state": readiness["state"],
                      "blocker_count": len(readiness.get("blockers") or []),
                      "flag_count": len(readiness.get("flags") or []),
                      "optional_unavailable": list(readiness.get("optional_unavailable") or [])},
        "primary_attention": primary,
        "accounting_basis": (headline.get("context") or {}).get("accounting_basis"),
        "period": (headline.get("context") or {}).get("period"),
        "refresh_overall": view["refresh"]["overall"],
    }


def materialize_view(analyst_view_dict: Mapping[str, Any], *,
                     generated_at: datetime | None = None) -> dict[str, Any]:
    """`AnalystView.to_dict()` → artifact payload（含遮蔽、overview、兩個 digest）。純函式。"""
    view = redact_private_paths(dict(analyst_view_dict))
    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    payload: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "analyst_view_schema_version": view["schema_version"],
        "source_schema_version": view["source_schema_version"],
        "ticker": view["ticker"],
        "company_id": view.get("company_id"),
        "company_label": view.get("company_label"),
        "generated_at": stamp.isoformat(),
        "as_of": view.get("as_of"),
        "point_in_time_mode": view.get("point_in_time_mode"),
        "research_context_digest": view.get("research_context_digest"),
        "readiness": view["readiness"],
        "refresh": view["refresh"],
        "overview": build_overview(view),
        "view": view,
        "materializer": {
            "version": MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload["freshness_identity"] = freshness_identity(
        ticker=payload["ticker"], as_of=payload["as_of"],
        point_in_time_mode=str(payload["point_in_time_mode"]),
        research_context_digest=payload["research_context_digest"],
        source_schema_version=str(payload["source_schema_version"]),
        readiness_state=str(payload["readiness"]["state"]),
        refresh_overall=str(payload["refresh"]["overall"]),
    )
    payload["content_digest"] = canonical_digest(payload)
    return payload


def materialize(ticker: str, *, as_of: date | None = None, scenario: str | None = None,
                store: ArtifactStore | None = None,
                generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """跑一次完整鏈並寫下 artifact。**只有這裡會連 Neo4j／Engine C／private ledger。**"""
    from briefing.alpha_view.sources import fetch_alpha_investment_view
    from briefing.analyst_view import build_analyst_view

    view = fetch_alpha_investment_view(ticker, as_of=as_of, include_causal=False, scenario=scenario)
    analyst = build_analyst_view(view)
    payload = materialize_view(analyst.to_dict(), generated_at=generated_at)
    target = store or ArtifactStore()
    return target.write(payload), payload


def materialize_many(tickers: Sequence[str], *, as_of: date | None = None,
                     store: ArtifactStore | None = None) -> list[tuple[str, Path | None, str | None]]:
    """一次 materialize 多檔。**一檔失敗不影響其他檔**——失敗以理由現形，不靜默跳過（INV-3）。"""
    target = store or ArtifactStore()
    results: list[tuple[str, Path | None, str | None]] = []
    for ticker in tickers:
        try:
            path, _ = materialize(ticker, as_of=as_of, store=target)
        except Exception as exc:  # noqa: BLE001 — 逐檔隔離；理由原樣回報
            results.append((ticker, None, f"{type(exc).__name__}: {str(exc)[:200]}"))
        else:
            results.append((ticker, path, None))
    return results


# ---------------------------------------------------------------------------
# state artifact：`ranking`（跨標的；照抄 `rank_bottlenecks()` 的輸出）
# ---------------------------------------------------------------------------

RANKING_MATERIALIZER_VERSION = "webapp-materialize-ranking/1"

#: 這份排序**不是什麼**。隨 artifact 出門，讓畫面永遠印得出來（AGENTS Alpha 呈現契約：
#: 排序是研究判斷，必須明標它不是回測或統計勝率；系統不給部位尺寸）。
RANKING_THIS_IS_NOT = (
    "不是回測、不是統計勝率——它是對圖中結構邊的研究判斷（AGENTS「哪些標的值得看」的交付要求）。",
    "不給部位尺寸：買多少、什麼時候買由使用者自行判斷並手動下單。",
    "不是「發現新標的」——只在已研究過的公司中排序；圖裡沒有的公司不會出現。",
    "不含 lead time、不含瓶頸業務占該公司營收多少、不含市值／分析師覆蓋——那些在 Engine C，不在本排序內。",
    "每檔的 disproof 與催化劑不在本表：點進單檔判讀（Analyst View）的「研究現況」才有。",
    "本 APP 不重算、不重排、不加權：順序與每一格都是 materialize 當下 rank_bottlenecks() 的輸出照抄。",
)

_RANKING_AUTHORITY = {
    "function": "query.bottleneck.rank_bottlenecks",
    "command": "python -m query.bottleneck",
    "note": "唯一排序權威（AGENTS）。本 artifact 照抄它的輸出：不重算結構分、不重排、不加權，"
            "也不自建第二套結構評分。",
}

_TOP_PICK_NOTE = (
    "首選＝可行動排序第 1 名——這是 authority 的順序，不是本 APP 的判斷。"
    "它是研究判斷，不是回測或統計勝率；每檔的 disproof 在單檔判讀的「研究現況」。"
)


def _row_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (str(row["company_id"]), str(row["relation"]), str(row["bottleneck"]))


def _company_label(registry: Any, company_id: str) -> str | None:
    """面向人的公司名：registry 的 `display_name`，退而求其次用 `name`；**都沒有就 None，
    不從 ID 猜名字**（`co:iqe` → 「Iqe」是編出來的，不是公司的名字）。"""
    lookup = getattr(registry, "company", None)
    company = lookup(company_id) if callable(lookup) else None
    if company is None:
        return None
    return getattr(company, "display_name", None) or getattr(company, "name", None) or None


def _project_ranking_row(row: Mapping[str, Any], *, rank: int, registry: Any,
                         evidence_label: Mapping[str, str]) -> dict[str, Any]:
    """一列的投影：**每一格照抄**，只加上名次、公司名與證據標籤——沒有任何算術。"""
    out = dict(row)
    out["rank"] = rank
    out["company_label"] = _company_label(registry, str(row["company_id"]))
    out["evidence_label"] = evidence_label.get(str(row.get("evidence")), str(row.get("evidence")))
    return out


def build_ranking_artifact(result: Mapping[str, Any], *, registry: Any,
                           sector_map: Mapping[str, Any] | None = None,
                           as_of: date | None = None, projection: Any = None,
                           generated_at: datetime | None = None) -> dict[str, Any]:
    """`rank_bottlenecks()` 的結果 → `ranking` state artifact。**純函式**：不連 DB、不重排。

    所有固定文字（已知限制、兩份排序的說明、無需求錨的讀法）與落差判準都從
    `query.bottleneck` 取——那裡是唯一一份（L16）。
    """
    from query.bottleneck import (
        EVIDENCE_LABEL, EVIDENCE_RANK, MIN_SUBSTITUTABILITY, NO_ANCHOR_CHAIN_NOTE,
        NO_ANCHOR_READING, QUALIFICATION_RANK, RANKING_TITLE, SORT_KEY_DESCRIPTIONS,
        STRUCTURAL_TABLE_NOTE, TWO_RANKINGS_NOTE, empty_sectors, group_rows_by_sector,
        known_limitations, load_sector_map, structural_gap_notes,
    )

    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    rows = [_project_ranking_row(r, rank=i, registry=registry, evidence_label=EVIDENCE_LABEL)
            for i, r in enumerate(result.get("rows") or (), 1)]
    rank_by_key = {_row_key(r): r["rank"] for r in rows}

    structural: list[dict[str, Any]] = []
    all_structural = result.get("structural_rows") or []
    for i, (r, actionable_rank, gap) in enumerate(
            structural_gap_notes(result, top_n=len(all_structural)), 1):
        row = _project_ranking_row(r, rank=i, registry=registry, evidence_label=EVIDENCE_LABEL)
        row["actionable_rank"] = actionable_rank
        row["gap_note"] = gap or None
        structural.append(row)

    sector_map = dict(sector_map) if sector_map is not None else load_sector_map()
    grouped = group_rows_by_sector(result, sector_map)
    sectors: list[dict[str, Any]] = []
    for name, buckets in sorted(grouped["sectors"].items(), key=lambda kv: -len(kv[1]["rows"])):
        first = buckets["structural_rows"][0] if buckets["structural_rows"] else None
        sectors.append({
            "sector": name,
            "actionable_count": len(buckets["rows"]),
            # 只放**名次**不放副本：一列的家只有 `rows`，分組是索引不是第二份資料。
            "actionable_ranks": [rank_by_key[_row_key(r)] for r in buckets["rows"]],
            "structural_first": None if first is None else {
                "company_id": first["company_id"], "ticker": first.get("ticker"),
                "company_label": _company_label(registry, str(first["company_id"])),
                "relation": first["relation"], "bottleneck": first["bottleneck"]},
        })

    coverage = dict(result["coverage"])
    top = rows[0] if rows else None
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["ranking"],
        "kind": "ranking",
        "title": RANKING_TITLE,
        "generated_at": stamp.isoformat(),
        "as_of": as_of.isoformat() if as_of else None,
        "point_in_time": {
            "mode": "as_of" if as_of else "current",
            "as_of": as_of.isoformat() if as_of else None,
            # as-of 視角下被排除的 assertion 計數：沒有它，「as-of 之後證據變少」與
            # 「本來就沒有證據」在畫面上同形（INV-3）。
            "excluded": projection.reasons() if projection is not None else None,
            "input_count": (projection.input_count if projection is not None
                            else coverage.get("assertions")),
        },
        "authority": dict(_RANKING_AUTHORITY),
        "coverage": coverage,
        "limitations": known_limitations(coverage),
        "top_pick": None if top is None else {
            "rank": 1, "company_id": top["company_id"], "ticker": top["ticker"],
            "company_label": top["company_label"], "relation": top["relation"],
            "bottleneck": top["bottleneck"], "note": _TOP_PICK_NOTE},
        "top_pick_absent_reason": None if top is not None else (
            f"無符合門檻的瓶頸邊（substitutability ≥ {MIN_SUBSTITUTABILITY} 且 src 為公司）——"
            "這是「排不出來」，不是「沒有標的值得看」；先看 coverage 與純結構表。"),
        "rows": rows,
        "structural_rows": structural,
        "notes": {
            "two_rankings": list(TWO_RANKINGS_NOTE),
            "structural_table": STRUCTURAL_TABLE_NOTE,
            "no_anchor_chain": NO_ANCHOR_CHAIN_NOTE,
            "no_anchor_reading": NO_ANCHOR_READING if "🔴 無需求錨" in grouped["sectors"] else None,
        },
        "sectors": sectors,
        "empty_sectors": empty_sectors(grouped, sector_map),
        "correlation_notes": list(grouped["correlation_notes"]),
        "vocab": {
            "evidence_labels": dict(EVIDENCE_LABEL),
            "evidence_rank": dict(EVIDENCE_RANK),
            "qualification_rank": dict(QUALIFICATION_RANK),
            "min_substitutability": MIN_SUBSTITUTABILITY,
            "sort_keys": {k: list(v) for k, v in SORT_KEY_DESCRIPTIONS.items()},
            "sole_source_states": {
                "true": "有文件說這條邊是唯一來源（強弱看 evidence：供應商自稱只算弱印證）",
                "false": "有文件說有第二來源",
                "null": "圖上沒有任何文件對這條邊的 sole_source 發言過——**未填不是否**",
            },
        },
        "this_is_not": list(RANKING_THIS_IS_NOT),
        "materializer": {
            "version": RANKING_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload = redact_private_paths(payload)
    payload["freshness_identity"] = state_freshness_identity(
        kind="ranking", as_of=payload["as_of"],
        # 認知狀態＝順序與每列的結構／證據欄位；`documents`（多讀一份文件）與 `confidence`
        # 不算——那是注意力指標，變了不代表我們對瓶頸的判斷變了（L12 兩個 digest 分開的理由）。
        identity={"rows": [[r["company_id"], r["relation"], r["bottleneck"], r["substitutability"],
                            r["sole_source"], r["evidence"], r["qualification_status"],
                            r["demand_anchor"]] for r in rows],
                  "canonical_edges": coverage.get("canonical_edges")})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def materialize_ranking(*, as_of: date | None = None, store: StateArtifactStore | None = None,
                        generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """跑一次 `rank_bottlenecks()` 並寫下 `ranking` artifact。**只有這裡會連 Neo4j。**

    與 `python -m query.bottleneck` 走同一條路：同一個 driver 設定、同一個 `fetch_assertions`、
    同一個 registry。差別只在最後一步是寫 artifact 而不是印 markdown。
    """
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    from identity.registry import get_registry
    from query.bottleneck import fetch_assertions, project_assertions_as_of, rank_bottlenecks

    load_dotenv()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("請設 NEO4J_PASSWORD（與 python -m query.bottleneck 相同的前置）")
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
    try:
        with driver.session() as session:
            raw_rows = fetch_assertions(session)
    finally:
        driver.close()
    projection = None
    rows: Sequence[Mapping[str, Any]] = raw_rows
    if as_of is not None:
        projection = project_assertions_as_of(raw_rows, as_of)
        rows = list(projection.rows)
    registry = get_registry()
    result = rank_bottlenecks(rows, registry)
    payload = build_ranking_artifact(result, registry=registry, as_of=as_of,
                                     projection=projection, generated_at=generated_at)
    target = store or StateArtifactStore()
    return target.write(payload), payload


# ---------------------------------------------------------------------------
# state artifact：`beta`（配置差距＋逐檔水位；照抄 daily_beta_snapshot／Engine D 的輸出）
# ---------------------------------------------------------------------------

BETA_MATERIALIZER_VERSION = "webapp-materialize-beta/1"

#: 這份畫面**不是什麼**。隨 artifact 出門（AGENTS Beta 呈現契約：只回答「距目標多遠」與「在什麼水位」）。
BETA_THIS_IS_NOT = (
    "不判斷今天要不要投入、不給金額、不給時間表——只回答各 sleeve 距目標多遠、每檔現在在什麼水位。",
    "相對水位是脈絡不是訊號：不參與排序、不換算金額。長期上漲的標的多數時間落在高位是正確資訊，不是該等回檔的訊號。",
    "容忍區間是「到位」的判準，不是 gate：落在區間內即視為到位、沒有偏好；再平衡只用新投入的錢往低於目標的格子補，不賣出。",
    "沒有任何動能或擇時指標：那一整組 2026-08-01 三次實測全部輸給無腦定投，已於 08-29 移除，不以任何名義回來。",
    "貸款 tranche 不適用配置建議：未動用額度不算自有現金，每次提款仍是逐次人工核准。",
    "發行人穿透（例：TSMC）只涵蓋 policy 已登記的部分：畫面上是「已知至少」，不是完整曝險。",
    "本 APP 不重算：每一格都是 materialize 當下 Engine D beta monitor 的輸出照抄；價格序列來自 Engine C 每日 ETL 已存的觀測，materialize 不重抓行情。",
)

_BETA_AUTHORITY = {
    "function": "portfolio.allocation.build_beta_monitor",
    "command": "python scripts/daily_beta_snapshot.py --format json --no-refresh --no-record-risk",
    "note": "Engine D 的 beta monitor 是唯一權威。本 artifact 照抄它的輸出：不重算差距、不重算水位、不補任何比例。"
            "`--no-refresh`＝不重抓行情（讀 daily ETL 已存的觀測）；`--no-record-risk`＝不 append 風險快照（那是 authority）。",
}

#: 逐檔價格序列只搬這兩格。`technical_observations` 表裡還留著 08-29 前的動能欄位——**永遠不搬進 artifact**，
#: 這條由 `tests/test_webapp_beta.py` 掃整份 JSON 守著。
_SERIES_FIELDS = ("session_date", "close_adjusted")


def _series_rows(rows: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    """Engine C 觀測 → `[{session_date, close}]`，由舊到新；只挑 `_SERIES_FIELDS`，其餘一格不碰。"""
    out: list[dict[str, Any]] = []
    for row in rows or ():
        close = row.get("close_adjusted")
        if close is None:
            continue
        out.append({"session_date": row.get("session_date"), "close": close})
    out.sort(key=lambda r: str(r["session_date"]))
    return out


def build_beta_artifact(report: Mapping[str, Any], *, series_by_key: Mapping[str, Sequence[Mapping[str, Any]]],
                        policy_risk: Mapping[str, Any], generated_at: datetime | None = None) -> dict[str, Any]:
    """`daily_beta_snapshot` 的 JSON report → `beta` state artifact。**純函式**：每格照抄，只加標籤與序列。

    標籤全部從 `portfolio.allocation` 的對照函式取（sleeve／差距狀態／行情狀態／降級原因／警告），
    那裡是 markdown 用的同一份（L16）——APP 不自己維護第二份對照表。
    """
    from portfolio.allocation import (
        _constraint_label, _gap_reason_label, _gap_state_label, _price_status_label, _sleeve_label,
        _warning_label,
    )

    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    gap = dict(report.get("allocation_gap") or {})
    sleeves: list[dict[str, Any]] = []
    for i, row in enumerate(gap.get("sleeves") or (), 1):
        item = dict(row)
        item["label"] = _sleeve_label(row.get("sleeve"))
        item["state_label"] = _gap_state_label(row.get("state"))
        item["unavailable_label"] = (_gap_reason_label(row["unavailable_reason"])
                                     if row.get("unavailable_reason") else None)
        # 固定色序：依 target_allocation 的 sleeve 順序給 slot，永遠不因排序或過濾重排（dataviz：色跟實體走）。
        item["slot"] = i
        sleeves.append(item)

    instruments: list[dict[str, Any]] = []
    for row in report.get("items") or ():
        item = dict(row)
        item["sleeve_label"] = _sleeve_label(row.get("sleeve"))
        item["status_label"] = _price_status_label(row)
        item["blocker_labels"] = [_constraint_label(b) for b in row.get("blockers") or ()]
        item["warning_labels"] = [_warning_label(w) for w in row.get("warnings") or ()]
        key = str(row.get("price_series_key") or "")
        series = _series_rows(series_by_key.get(key))
        item["series"] = series
        item["series_note"] = (
            f"Engine C 觀測序列自 {series[0]['session_date']} 起（{len(series)} 個已收盤交易日；"
            "只含 data_status=observed 的日子，會隨每日 ETL 變長）；數值是 provider 報價單位的原值，"
            "未換算幣別——不同檔的折線不可互比高低"
            if series else "Engine C 沒有這檔的已收盤觀測序列（尚未 ETL 或全部被隔離）——沒有折線不是價格為 0")
        instruments.append(item)

    capital_view = dict(report.get("capital_view") or {})
    portfolio = dict(report.get("portfolio") or {})
    credit = dict(report.get("contingent_credit_available") or {})
    risk_snapshot = dict(report.get("risk_snapshot") or {})
    issuer_exposures = dict(risk_snapshot.get("issuer_exposures") or {})
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["beta"],
        "kind": "beta",
        "title": "資產配置：距目標多遠、現在在什麼水位",
        "generated_at": stamp.isoformat(),
        "as_of": None,
        "point_in_time": {"mode": "current", "as_of": None, "excluded": None,
                          "report_as_of": report.get("as_of")},
        "authority": dict(_BETA_AUTHORITY),
        "report_status": report.get("status"),
        "refresh": {
            **dict(report.get("refresh") or {}),
            "note": "materialize 不重抓行情：逐檔的最新完整交易日是 daily ETL 最後一次寫入的 session_date。",
        },
        "twse_freshness": dict(report.get("twse_freshness") or {}),
        "blockers": list(report.get("blockers") or ()),
        "warnings": list(report.get("warnings") or ()),
        "warning_labels": [_warning_label(w) for w in report.get("warnings") or ()],
        "capital": {
            "base_currency": portfolio.get("base_currency") or capital_view.get("base_currency"),
            "status": capital_view.get("status"),
            "authority_as_of": capital_view.get("authority_as_of"),
            "blockers": list(capital_view.get("blockers") or ()),
            "nav_base": portfolio.get("nav_base"),
            "invested_non_cash_base": portfolio.get("invested_non_cash_base"),
            "portfolio_cash_base": portfolio.get("cash_base"),
            "cash_floor_base": portfolio.get("cash_floor_base"),
            "deployable_cash_base": portfolio.get("deployable_cash_base"),
            "self_funded_supported_range": list(report.get("self_funded_supported_range") or ()),
            "loan_funded_supported_range": report.get("loan_funded_supported_range"),
            "credit": {
                "status": credit.get("status"),
                "terms_status": credit.get("terms_status"),
                "currency": credit.get("currency"),
                "undrawn_amount_base": credit.get("undrawn_amount_base"),
                "drawn_amount_base": credit.get("drawn_amount_base"),
                "estimated_monthly_interest_base": credit.get("estimated_monthly_interest_base"),
                "estimated_annual_interest_base": credit.get("estimated_annual_interest_base"),
                "facilities": list(credit.get("facilities") or ()),
                "blockers": list(credit.get("blockers") or ()),
            },
            "fx": dict(capital_view.get("fx") or {}),
        },
        "allocation": {
            "status": gap.get("status"),
            "unavailable_reason": gap.get("unavailable_reason"),
            "basis": gap.get("basis"),
            "invested_non_cash_base": gap.get("invested_non_cash_base"),
            "rebalancing": dict(gap.get("rebalancing") or {}),
            "policy_version": gap.get("policy_version"),
            "sleeves": sleeves,
            "correlation_warnings": list(gap.get("correlation_warnings") or ()),
        },
        "instruments": instruments,
        "risk": {
            "snapshot": risk_snapshot,
            "thresholds": dict(policy_risk),
            "warning_labels": [_warning_label(w) for w in risk_snapshot.get("warnings") or ()],
            "hard_blocks": list(risk_snapshot.get("hard_blocks") or ()),
            "issuer_focus": {name: dict(value) for name, value in issuer_exposures.items()
                             if _finite_ratio(value.get("total_weight")) is not None
                             and value.get("total_weight") >= float(policy_risk.get("issuer_concentration_warning") or 0)},
        },
        "notes": {
            "water_level": "相對水位只呈現、不參與排序、不換算金額；長期上漲的標的多數時間落在高位是正確資訊，不是該等回檔的訊號。",
            "band": "容忍區間內＝到位、沒有偏好。再平衡只用新投入的錢往低於目標的格子補，不賣出；本表只給差距，不給金額。",
            "lookthrough": "發行人穿透覆蓋恆為 partial：顯示的是「已知至少」。",
            "loan": "未動用貸款額度不算自有現金；貸款 tranche 不適用配置建議，逐次人工核准。",
            "leverage_labels": "「槓桿 ETF 資金占比」＝投入槓桿 ETF 的資金占 NAV；「換算槓桿曝險」＝乘上 2x／3x 後的曝險。兩者不得混用。",
        },
        "vocab": {
            "sleeve_labels": {s["sleeve"]: s["label"] for s in sleeves},
            "gap_state_labels": {k: _gap_state_label(k) for k in ("below_band", "on_target", "above_band", "unknown")},
            "price_status_labels": {"observed": "行情正常", "insufficient_history": "歷史不足",
                                    "unavailable": "資料不足", "quarantined": "資料不足（TWSE 官方較新，暫時隔離）",
                                    "stale": "資料不足（行情過期）"},
        },
        "this_is_not": list(BETA_THIS_IS_NOT),
        "materializer": {
            "version": BETA_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload = redact_private_paths(payload)
    payload["freshness_identity"] = state_freshness_identity(
        kind="beta", as_of=None,
        # 認知狀態＝各 sleeve 到位／偏離的狀態、各檔行情資料狀態、風險警告與硬擋。
        # 價格動了（心跳、水位百分比）是內容變了，不是判斷該重看了（L12）。
        identity={"sleeves": [[s.get("sleeve"), s.get("state")] for s in sleeves],
                  "instruments": [[i.get("ticker"), i.get("price_status")] for i in instruments],
                  "warnings": sorted(risk_snapshot.get("warnings") or ()),
                  "hard_blocks": sorted(risk_snapshot.get("hard_blocks") or ()),
                  "allocation_status": gap.get("status"), "capital_status": capital_view.get("status")})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def _finite_ratio(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def materialize_beta(*, store: StateArtifactStore | None = None,
                     generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """跑一次 Engine D beta monitor（純讀）並寫下 `beta` artifact。

    與 daily 的 `scripts/daily_beta_snapshot.py` 同一支程式、同一個 `build_beta_monitor`；差別是
    `--no-refresh`（不重抓行情、不寫 Engine C）與 `--no-record-risk`（不 append 風險快照）。
    它仍會讀 Google Sheet 持股（readonly）與 FX——那是 authority 讀取，只准發生在 materialize。
    """
    import importlib.util
    import io

    from engine_c.db import get_conn
    from engine_c.technical import recent_technical_observations

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("daily_beta_snapshot", root / "scripts" / "daily_beta_snapshot.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("找不到 scripts/daily_beta_snapshot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    buffer = io.StringIO()
    code = module.run(["--format", "json", "--no-refresh", "--no-record-risk"], stdout=buffer)
    report = json.loads(buffer.getvalue() or "{}")
    if code != 0 or report.get("status") == "error":
        raise RuntimeError(f"daily_beta_snapshot 失敗（exit {code}，status={report.get('status')}）")
    policy = module.load_beta_policy()
    keys = {str(item.get("price_series_key")) for item in report.get("items") or () if item.get("price_series_key")}
    conn = get_conn()
    try:
        series_by_key = {key: recent_technical_observations(conn, key, limit=260) for key in sorted(keys)}
    finally:
        conn.close()
    payload = build_beta_artifact(report, series_by_key=series_by_key,
                                  policy_risk=dict(policy.get("risk") or {}), generated_at=generated_at)
    target = store or StateArtifactStore()
    return target.write(payload), payload


def write_vocabularies(store: ArtifactStore | None = None) -> Path:
    """把封閉字彙寫成 `.meta.json`，讓 serve 端讀得到而**不必 import `alpha`／`briefing`**。

    這是 L16 的直接應用：分類已經有 SSOT，要做的是**讓它跟著資料走到需要它的地方**，
    而不是在 APP 端再寫一份「absence_kind 是什麼意思」的對照表。
    """
    from alpha.absence import ABSENCE_KINDS, SETTLED_ABSENCE_KINDS
    from briefing.analyst_view.contracts import (
        ACCOUNTING_BASIS_DISPLAY, CORE_PANELS, OPTIONAL_PANELS, QUESTIONS, WEAK_INPUT_RULES,
    )

    target = store or ArtifactStore()
    target.directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "absence_kinds": dict(ABSENCE_KINDS),
        "settled_absence_kinds": sorted(SETTLED_ABSENCE_KINDS),
        "accounting_basis_display": {k: dict(v) for k, v in ACCOUNTING_BASIS_DISPLAY.items()},
        "questions": dict(QUESTIONS),
        "weak_input_rules": dict(WEAK_INPUT_RULES),
        "core_panels": list(CORE_PANELS),
        "optional_panels": list(OPTIONAL_PANELS),
        "readiness_states": {
            "ready": "核心四段都有內容，且沒有被標記需要動作",
            "ready_with_flags": "有內容，但至少一段 stale／review_required／not_applicable",
            "blocked": "至少一段核心缺內容——看 blocker_details 的 absence_kind 才知道該不該去補",
        },
    }
    path = target.directory / ".meta.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


__all__ = ["BETA_MATERIALIZER_VERSION", "BETA_THIS_IS_NOT", "MATERIALIZER_VERSION",
           "RANKING_MATERIALIZER_VERSION", "RANKING_THIS_IS_NOT", "build_beta_artifact",
           "build_overview", "build_ranking_artifact", "materialize", "materialize_beta",
           "materialize_many", "materialize_ranking", "materialize_view", "redact_private_paths",
           "write_vocabularies"]
