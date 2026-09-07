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

from .contracts import ARTIFACT_SCHEMA_VERSION, canonical_digest, freshness_identity
from .store import ArtifactStore

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


__all__ = ["MATERIALIZER_VERSION", "build_overview", "materialize", "materialize_many",
           "materialize_view", "redact_private_paths", "write_vocabularies"]
