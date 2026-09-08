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


__all__ = ["MATERIALIZER_VERSION", "RANKING_MATERIALIZER_VERSION", "RANKING_THIS_IS_NOT",
           "build_overview", "build_ranking_artifact", "materialize", "materialize_many",
           "materialize_ranking", "materialize_view", "redact_private_paths", "write_vocabularies"]
