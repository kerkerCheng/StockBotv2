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

from .structure_readings import build_structure_readings_artifact
from .contracts import (
    ArtifactUnavailable,
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


from alpha.closure import row_from_artifact


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


def _brief_overview(brief_panel: Mapping[str, Any]) -> dict[str, Any]:
    lines = _line_map(brief_panel)
    bet_line = lines.get("brief:our_bet") or {}
    light = (lines.get("brief_status_light") or {}).get("value") or {}
    return {
        "status": brief_panel.get("status"),
        "absence_kind": brief_panel.get("absence_kind"),
        "our_bet": _cell(bet_line),
        "status_light": light,
    }


def _wipeout_overview(panel: Mapping[str, Any]) -> dict[str, Any]:
    """歸零旗標的清單投影：四盞燈的顏色與一句話，外加紅黃綠灰計數。**純選取。**

    ⚠ 顏色照抄 `alpha.wipeout` 經 read model 帶來的值；APP 端**不得**自己從 inputs 重判一次色
    ——重造品會立刻開始偏離（L16）。算出顏色的數字刻意**不進**這個投影：清單卡片是消費層，
    數字住稽核層（D2「紅黃綠不給數字」）。
    """
    lines = _line_map(panel)
    lanes = []
    for key, datum in lines.items():
        if not str(key).startswith("wipeout_"):
            continue
        value = datum.get("value") if isinstance(datum.get("value"), Mapping) else {}
        lanes.append({
            "lane": str(key).removeprefix("wipeout_"),
            "label": datum.get("display_label") or datum.get("label"),
            "colour": (value or {}).get("colour"),
            "reason": (value or {}).get("reason") or datum.get("reason"),
            "absence_kind": datum.get("absence_kind"),
        })
    return {"status": panel.get("status"), "absence_kind": panel.get("absence_kind"),
            "tally": (panel.get("context") or {}).get("tally"), "lanes": lanes}


def build_overview(view: Mapping[str, Any], *, price_context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """清單卡片的投影。**純選取**——這裡沒有任何算術。"""
    headline = view["headline"]
    lines = _line_map(headline)
    fundamental_lines = _line_map(view.get("fundamental") or {})
    price = lines.get("current_price") or {}
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
        # ⚠ **2026-09-23（Phase 0 Step 0b.1）：五個鍵退役**——`future_target`、`implied_return`、
        # `payoff`、`sell_side_target`、`target_reached`。它們就是 ROADMAP 首屏那一列要拿掉的
        # 「那把尺」（現價／沒賭對／賭對／判斷錯了）與它的兩端。**不是搬家，是退役**：
        # 「已定價嗎」改由財務三題回答（Phase 3），主參照是自己的歷史、不設門檻。
        # 現價（`price`）留著——它是 A2 觀測，不是模型輸出。
        # 2026-09-15 投資人短評：清單卡片要的第一句（賭什麼）與狀態燈。純選取。
        "brief": _brief_overview(view.get("brief") or {}),
        # V2：市場承認了嗎（照抄）。⚠ `target_reached` 已於 2026-09-23 隨目標價退役。
        "gap_closure": _cell(fundamental_lines.get("gap_closure")),
        # D2（2026-09-18）歸零旗標：四盞燈（顏色＋一句話）與紅黃綠灰計數。照抄 panel。
        "wipeout": _wipeout_overview(view.get("wipeout") or {}),
        # V1：熟成度計數（照抄 research panel 的 catalyst_quantitative_link）
        "ripeness": _cell(_line_map(view.get("research") or {}).get("catalyst_quantitative_link")),
        # 催化劑那一格的形狀（七缺陷之 1）：`ripeness` 在沒有 linked 催化劑時整格無值，
        # 於是四種不同的「沒有」變成同一句話。這一格永遠有值，由 producer 宣告。
        "catalyst_shape": _cell(_line_map(view.get("research") or {}).get("catalyst_shape")),
        "price_context": dict(price_context) if price_context else None,
        "readiness": {"state": readiness["state"],
                      "blocker_count": len(readiness.get("blockers") or []),
                      "flag_count": len(readiness.get("flags") or []),
                      "optional_unavailable": list(readiness.get("optional_unavailable") or [])},
        "primary_attention": primary,
        "accounting_basis": (headline.get("context") or {}).get("accounting_basis"),
        "period": (headline.get("context") or {}).get("period"),
        # 目標期末（2026-09-19）。`period` 那個標籤（"FY2026"）**承載不了它**：
        # 6594.T 與 6268.T 同樣是 FY2026，會計年度結束日卻差三個月——而「財報空窗」
        # 判的正是那一天。先前 `closure_terminal` 因此結構上回不出第三種終局。
        "period_end": (headline.get("context") or {}).get("period_end"),
        "refresh_overall": view["refresh"]["overall"],
        # 我們有沒有形成自己的觀點。**照抄 fundamental panel 的宣告**，這裡不重算、不推論。
        # 它與 readiness 正交：一份 ready 的判讀完全可以是 `consensus_inverted`（每一格都有
        # 數字，而每個數字都是共識反解出來的）——列表頁必須分得出這兩件事。
        "opinion_stance": _cell(_line_map(view.get("fundamental") or {}).get("opinion_stance")),
        # 這一檔到終局了沒（ready／settled／**awaiting_report**／None）。
        # **照抄 `alpha.closure` 的判定**——它已經是這個分類的 SSOT（drain 選題與
        # `webapp status` 都消費它），在 APP 端再寫一份「什麼叫做完」的規則就是 L16 記過的重造品。
        # ⚠ **`today` 必須傳**：不傳就回不出第三種終局，而「等財報（會自己解開）」會被
        # 下游歸進「還沒做」——兩者的下一步完全相反。PIT 模式下用 artifact 自己的 as_of，
        # 不用牆上的今天（INV-6）。
        "closure_terminal": row_from_artifact(
            str(view["ticker"]), view,
            today=(_as_date(view.get("as_of")) or date.today())).terminal,
    }


def _as_date(value: Any) -> date | None:
    """artifact 的 `as_of` 是 ISO 字串或 None（PIT 模式才有值）。解析不了就回 None。"""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _price_context(series: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    rows = [r for r in series if isinstance(r.get("close"), (int, float)) and r.get("session_date")]
    if not rows:
        return None
    low = min(rows, key=lambda r: r["close"])
    high = max(rows, key=lambda r: r["close"])
    return {"sessions": len(rows), "first_date": rows[0]["session_date"], "last_date": rows[-1]["session_date"],
            "low": low["close"], "low_date": low["session_date"], "high": high["close"], "high_date": high["session_date"],
            "note": "最近的已收盤交易日區間；脈絡不是訊號——不用它排序、不用它決定買多少"}


def materialize_view(analyst_view_dict: Mapping[str, Any], *,
                     generated_at: datetime | None = None,
                     price_series: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """`AnalystView.to_dict()` → artifact payload（含遮蔽、overview、兩個 digest）。純函式。

    `price_series` 是**脈絡不是判讀**：一條這檔自己的已收盤收盤價序列，讓使用者看得懂
    「現在這個價位在哪」。它不參與任何計算——`freshness_identity` 不含它（價格動了不算認知變了）。
    """
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
        "overview": build_overview(view, price_context=_price_context(price_series or ())),
        "view": view,
        "price_series": [dict(row) for row in (price_series or ())],
        # 尺的脈絡（2026-09-15）：最近 N 個已收盤交易日的高低點與日期。**脈絡不是訊號**：不排序、不決定尺寸；
        # 只是讓「現價在哪」有個參照。純選取（min／max 是挑點，不是模型）。
        "price_context": _price_context(price_series or ()),
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
    payload = materialize_view(analyst.to_dict(), generated_at=generated_at,
                               price_series=_close_series(ticker))
    target = store or ArtifactStore()
    return target.write(payload), payload


def _close_series(ticker: str, *, sessions: int = 180) -> list[dict[str, Any]]:
    """這檔自己的已收盤收盤價序列。抓失敗只是沒有折線，**不讓整份 artifact 失敗**。

    ⚠ 只取已收盤的交易日（provider 會回一根未結算的當日 bar，那會讓「單日報酬」時而是
    昨收到現價、時而是昨收到今收——一個欄位兩種語意，L12）。
    """
    from alpha.providers.close_series import fetch_close_series

    try:
        return list(fetch_close_series([ticker], sessions=sessions).get(ticker) or ())
    except Exception:  # noqa: BLE001 — 價格是脈絡，缺了不該讓判讀讀不到
        return []


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
        # Q1（2026-09-17 使用者核准 A）：被門檻擋下的那些也要進 artifact，否則籃子層
        # （純函式，只吃 artifact）讀不到第二個宇宙。**排序與門檻一字未動**——`rows` 逐位相同，
        # 這裡只是把 rank_bottlenecks 已經算出來的 filtered_rows 照抄下來（INV-3 的可見面）。
        # ⚠ 兩種理由不得混為一談：`substitutability_below_threshold`＝已研究、答案是否定的；
        # `substitutability_unfilled`＝還沒有人研究過。下一步完全相反（前者問「還值得看嗎」，
        # 後者去補研究），所以 reason 跟著每一列走。
        "filtered_rows": [dict(r) for r in (result.get("filtered_rows") or ())],
        "filter": dict(result.get("filter") or {}),
        # ⚠ 與 `filter` 是**不同的問題**，所以是不同的鍵：`filter` 說「這條邊為什麼沒進排序」，
        # 本欄說「這個**瓶頸節點**接不接得到有人花錢的地方」。三種成因刻意分開帶下來——
        # 壓成一句「走不到錨」的實測代價是 pq2 [606] 點名的 6 個節點裡有 3 個根本不是研究缺口
        # （ROADMAP Phase 4 ②③④）。⚠ 它**不參與排序**，`rows` 一字未動。
        "anchor_gaps": dict(result.get("anchor_gaps") or {}),
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
        # 看股網站式的「價格」：最新完整交易日的收盤，不是即時價。報價單位目前沒有 SSOT 可帶
        # （Engine C／policy 都沒有每檔的 quote unit 欄位）——寫 None，畫面標「未登記」，不猜。
        item["latest_close"] = None if not series else {
            "session_date": series[-1]["session_date"], "close": series[-1]["close"],
            "quote_unit": None,
            "note": "最新完整交易日收盤（provider 報價單位原值；單位未登記、未換算），不是即時價"}
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
            "goal": "約 30 年後 `retirement_net_terminal_wealth` 最大化。本頁不判斷「今天該不該投」、不給金額或時間表——beta 只回答兩件事：各 sleeve 距目標多遠、每檔現在在什麼水位。",
            "heartbeat": "逐檔心跳的最小要求：每列明示商品自身的**最新完整交易日**與 1 日漲跌，相對水位列 52 週區間位置（主要）、距 52 週高點、距 SMA200，全部取自商品**自身**價格序列（TQQQ 不冒用 QQQ、00631L 不冒用 0050）。這條在 Daily 收斂後由本頁承擔：**逐檔表永遠看得到**，不因今天沒有配置缺口而消失。",
            "water_level": "相對水位**只呈現、不參與排序、不換算金額**，且**不得用 RSI／MACD 等動能指標表達水位**；長期上漲的標的多數時間落在高位是正確資訊，不是該等回檔的訊號。**beta 不回答「今天該不該投」**——只回答各 sleeve 距目標多遠、每檔在什麼水位。",
            "band": "**band 是容忍區間不是 gate**：落在區間內即視為到位、沒有偏好。再平衡只用新投入的錢往低於目標的格子補，不賣出；本表只給差距，不給金額、不排名、不產生部位尺寸。目標比例的 SSOT 是 `config/target_allocation.json`，分母是已投入的非現金部位。**貸款 tranche 不適用配置建議**，仍走 Capital Authority 的逐次人工核准。",
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


# ---------------------------------------------------------------------------
# state artifact：`coverage`（圖的供給側覆蓋掃描；照抄 `query.coverage_gaps.scan()`）
# ---------------------------------------------------------------------------

COVERAGE_MATERIALIZER_VERSION = "webapp-materialize-coverage/2"

COVERAGE_THIS_IS_NOT = (
    "不是「世界上還缺哪些瓶頸」——它只能從**圖裡既有的節點**往回看；圖裡沒有的瓶頸不會出現在這裡。",
    "🔴 的數字不是研究待辦數：`prod:` 前綴是抽取副產品（文件掉出來的產品型號），只計數、不是題目。",
    "🟡 不是「還沒研究」——那個領域已經研究過，缺的是把邊接到 chokepoint 節點上（走入圖核准）。",
    "不排序、不評分：這一頁沒有名次，補哪一個由使用者決定。",
    "`層` 與 `邊` 不是分類也不是分數：它們是節點自己的屬性與邊數，只用來讓「下一步做什麼」看得出差別。",
    "本 APP 不重算：每一格都是 materialize 當下 `python -m query.coverage_gaps` 的輸出照抄。",
    "重複節點候選**不是缺口的一種**：它問的是「這個節點是不是旁邊那個」，"
    "放在同一頁是因為重複節點正是 🔴 的誤報來源——一個已經有供應商的東西被攤成兩個節點之後，"
    "其中孤立的那個看起來像空白。",
)

_COVERAGE_AUTHORITY = {
    "function": "query.coverage_gaps.scan",
    "command": "python -m query.coverage_gaps",
    "note": "唯一覆蓋掃描權威。本 artifact 照抄它的分桶結果：不重新分類、不補節點、不排序。",
    # 同一頁的第二題有自己的 authority——混成一個會讓「誰算的」答不出來。
    "duplicates": {
        "function": "query.duplicate_nodes.pair_candidates",
        "command": "python -m query.duplicate_nodes",
        "note": "只提名不合併；合併走 pq2 ra_admission ＋ config/entity_aliases.json。",
    },
}


def _coverage_row(row: Mapping[str, Any], *, with_question: bool = False) -> dict[str, Any]:
    out = {"node": row["node"], "name": row.get("name"),
           "direct": list(row.get("direct") or ()), "indirect": list(row.get("indirect") or ()),
           # 脈絡欄位（非分類）：節點自己的邊數與 stack 層別，照抄不重算。
           "degree": row.get("degree"), "abstraction_level": row.get("abstraction_level")}
    if with_question:
        from query.coverage_gaps import ISOLATED_DEGREE, RESEARCH_QUESTION_TEMPLATE

        # 孤立節點的下一步不是「誰供應它」——它連 stack 都還沒接上。
        out["question"] = (
            "先確認它該掛在 stack 哪一層"
            if row.get("degree") == ISOLATED_DEGREE
            else RESEARCH_QUESTION_TEMPLATE.format(node=row["node"])
        )
        out["isolated"] = row.get("degree") == ISOLATED_DEGREE
    return out


def _duplicate_pair_row(pair: Mapping[str, Any]) -> dict[str, Any]:
    """一對候選 → artifact 列。**逐字照抄**，因為那是這一區塊存在的全部理由（L18）。"""

    def _side(view: Mapping[str, Any]) -> dict[str, Any]:
        return {"node": view["node"], "name": view.get("name"),
                "abstraction_level": view.get("abstraction_level"),
                "degree": view.get("degree"), "quote_count": view.get("quote_count"),
                "quotes": [dict(q) for q in view.get("quotes") or ()]}

    return {
        "pair": list(pair["pair"]),
        "rules": list(pair["rules"]),
        "same_abstraction_level": pair["same_abstraction_level"],
        "left": _side(pair["left"]), "right": _side(pair["right"]),
        "registry_mentions": [dict(m) for m in pair.get("registry_mentions") or ()],
    }


def build_coverage_artifact(rows: Sequence[Mapping[str, Any]], *,
                            duplicate_buckets: Mapping[str, Sequence[Mapping[str, Any]]],
                            duplicate_node_total: int,
                            generated_at: datetime | None = None) -> dict[str, Any]:
    """`coverage_gaps.scan()` 的結果 → `coverage` state artifact。**純函式**：不連 DB、不重新分類。

    ⚠ `duplicate_buckets` 與 `duplicate_node_total` 是**必要參數而非預設 `None`**：預設值會讓
    「呼叫端忘了傳」與「這次真的沒算」同形（D15 的 `power_law` 踩過同一個坑）。
    """
    from query.coverage_gaps import (
        BUCKET_LABELS, BUCKET_NEXT_STEP, BUCKET_NOTE, COVERAGE_SCOPE_NOTE, COVERAGE_TITLE,
        ISOLATED_NOTE, LEVEL_NOTE, PRODUCT_NOISE_PREFIX, RESEARCH_GAP_SPLIT_NOTE,
        bucketize, split_research_gaps,
    )
    # 固定文字跟著判準走，不在 APP 抄第二份（L16）。
    from query.duplicate_nodes import (
        RULE_LABELS as DUPLICATE_RULE_LABELS,
        THIS_IS_NOT as DUPLICATE_THIS_IS_NOT,
        TITLE as DUPLICATE_TITLE,
    )

    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    buckets = bucketize(rows)
    real_gaps, product_noise = split_research_gaps(buckets["research_gap"])
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["coverage"],
        "kind": "coverage",
        "title": COVERAGE_TITLE,
        "generated_at": stamp.isoformat(),
        "as_of": None,
        "point_in_time": {"mode": "current", "as_of": None, "excluded": None},
        "authority": dict(_COVERAGE_AUTHORITY),
        "counts": {"nodes": len(rows), **{k: len(v) for k, v in buckets.items()},
                   "research_gap_real": len(real_gaps), "research_gap_product_noise": len(product_noise),
                   # 重複節點候選：`unmentioned` 才是待辦（registry 提過的那些已經有人寫過話了）。
                   "duplicate_unmentioned": len(duplicate_buckets["unmentioned"]),
                   "duplicate_mentioned": len(duplicate_buckets["mentioned"])},
        "labels": dict(BUCKET_LABELS),
        "next_steps": dict(BUCKET_NEXT_STEP),
        "notes": {"buckets": BUCKET_NOTE, "research_gap_split": RESEARCH_GAP_SPLIT_NOTE,
                  "scope": COVERAGE_SCOPE_NOTE,
                  "question_template": "研究題目是固定模板不是新判斷：同一個節點永遠得到同一句。",
                  "product_noise_rule": f"前綴 `{PRODUCT_NOISE_PREFIX}` ＝抽取副產品（機械比對，可重導）",
                  "isolated": ISOLATED_NOTE, "abstraction_level": LEVEL_NOTE},
        "research_gaps": [_coverage_row(r, with_question=True) for r in real_gaps],
        "product_noise": [_coverage_row(r) for r in product_noise],
        "modelling_gaps": [_coverage_row(r) for r in buckets["modelling_gap"]],
        "covered": [_coverage_row(r) for r in buckets["covered"]],
        "concept": [_coverage_row(r) for r in buckets["concept"]],
        "duplicates": {
            "title": DUPLICATE_TITLE,
            "node_total": duplicate_node_total,
            "rule_labels": dict(DUPLICATE_RULE_LABELS),
            "this_is_not": list(DUPLICATE_THIS_IS_NOT),
            "unmentioned": [_duplicate_pair_row(p) for p in duplicate_buckets["unmentioned"]],
            "mentioned": [_duplicate_pair_row(p) for p in duplicate_buckets["mentioned"]],
        },
        "this_is_not": list(COVERAGE_THIS_IS_NOT),
        "materializer": {
            "version": COVERAGE_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload = redact_private_paths(payload)
    payload["freshness_identity"] = state_freshness_identity(
        kind="coverage", as_of=None,
        # 認知狀態＝哪些節點還空白、哪些已覆蓋。節點名稱改字不算認知變了。
        identity={"research_gap": sorted(r["node"] for r in real_gaps),
                  "product_noise": sorted(r["node"] for r in product_noise),
                  "modelling_gap": sorted(r["node"] for r in buckets["modelling_gap"]),
                  "covered": sorted(r["node"] for r in buckets["covered"]),
                  # 哪幾對還沒人看過＝認知狀態；逐字改字不算認知變了（與上面四桶同一條原則）。
                  "duplicate_unmentioned": sorted(
                      "|".join(p["pair"]) for p in duplicate_buckets["unmentioned"])})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def materialize_coverage(*, store: StateArtifactStore | None = None,
                         generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """跑一次 `coverage_gaps.scan()` 並寫下 artifact。**只有這裡會連 Neo4j。**"""
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    from identity import entities
    from query.coverage_gaps import scan
    from query.duplicate_nodes import bucketize, pair_candidates
    from query.duplicate_nodes import scan as scan_duplicates

    load_dotenv()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("請設 NEO4J_PASSWORD（與 python -m query.coverage_gaps 相同的前置）")
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
    try:
        with driver.session() as session:
            rows = scan(session)
            # 同一個 session 掃兩題：兩個 authority、兩份 Cypher，但只連一次圖。
            duplicate_rows = scan_duplicates(session)
    finally:
        driver.close()
    duplicate_buckets = bucketize(pair_candidates(duplicate_rows), entities.load())
    payload = build_coverage_artifact(
        rows, duplicate_buckets=duplicate_buckets,
        duplicate_node_total=len(duplicate_rows), generated_at=generated_at)
    target = store or StateArtifactStore()
    return target.write(payload), payload


# ---------------------------------------------------------------------------
# state artifact：`watches`（在等什麼；照抄 Event Watch registry ＋ 追源 backlog）
# ---------------------------------------------------------------------------

WATCHES_MATERIALIZER_VERSION = "webapp-materialize-watches/1"

WATCHES_THIS_IS_NOT = (
    "不是提醒系統：這一頁不會通知你，它只讓「還有什麼在等」現形（L14：防呆要自己出現）。",
    "**停滯（stalled）不等於死亡**：具名標的都觸發過一輪、被動層短期不會再醒，但到期日仍會兜底。",
    "「等事件」不代表不用動作：`unwatched`／`expired`／停滯三種都需要人當場處置（延長／改主動輪詢／改 terminal）。",
    "本 APP 不寫任何東西：不喚醒 watch、不消化 fired、不改 lead 狀態——那些只能在對話裡做。",
    "本 APP 不重算：每一格都是 materialize 當下 registry 的原值照抄。",
)

_WATCHES_AUTHORITY = {
    "function": "engine_b.event_watch（registry）＋ engine_b.leads.trace_backlog",
    "command": "python -m engine_b.event_watch counters｜list；python -m engine_b.cli trace-backlog --needs-attention",
    "note": "等待狀態的單一 authority 是 Event Watch registry；本 artifact 照抄，不自己推導誰該醒。",
}

#: 「還會不會醒」的四種狀態——與 `trace_backlog` 的 `wake_state` 同一組字彙（L16）。
WAKE_STATE_LABELS = {
    "watching": "有機制在等（具名標的還沒全部觸發過）",
    "stalled": "停滯——具名標的都觸發過一輪，只剩到期日或主動輪詢能救它",
    "expired": "等待已到期——要決定續等、改主動輪詢，還是放棄",
    "unwatched": "**沒有任何機制在等它**——唯一真正的黑洞，必須當場處置",
}


def _watch_row(watch: Mapping[str, Any]) -> dict[str, Any]:
    from engine_b.event_watch import is_stalled, watch_detail, wake_target

    return {
        "watch_id": watch["watch_id"], "kind": watch["kind"], "status": watch.get("status"),
        "detail": watch_detail(watch), "target": wake_target(watch),
        "entities": list(watch.get("entities") or ()),
        "consumed_entities": list(watch.get("consumed_entities") or ()),
        "poll_eligible": bool((watch.get("poll") or {}).get("eligible")),
        "poll_last_checked": (watch.get("poll") or {}).get("last_checked"),
        "query_hint": watch.get("query_hint"),
        "created_at": watch.get("created_at"), "expires": watch.get("expires"),
        "stalled": is_stalled(watch),
    }


def build_watches_artifact(watch_data: Mapping[str, Any], *, config: Mapping[str, Any],
                           backlog: Sequence[Mapping[str, Any]], due: Sequence[Mapping[str, Any]],
                           generated_at: datetime | None = None) -> dict[str, Any]:
    """Event Watch registry ＋ 追源 backlog → `watches` state artifact。**純函式**。"""
    from engine_b.event_watch import counters

    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    watches = list(watch_data.get("watches") or ())
    by_status: dict[str, list[dict[str, Any]]] = {}
    for watch in watches:
        by_status.setdefault(str(watch.get("status")), []).append(_watch_row(watch))
    active = by_status.get("active") or []
    needs_attention = [dict(row) for row in backlog
                       if str(row.get("wake_state")) in {"stalled", "expired", "unwatched"}]
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["watches"],
        "kind": "watches",
        "title": "在等什麼（事件監看與追源 backlog）",
        "generated_at": stamp.isoformat(),
        "as_of": None,
        "point_in_time": {"mode": "current", "as_of": None, "excluded": None},
        "authority": dict(_WATCHES_AUTHORITY),
        "counters": dict(counters(watch_data)),
        "config": dict(config),
        "active": active,
        "stalled": [row for row in active if row["stalled"]],
        "pollable": [row for row in active if row["poll_eligible"]],
        "due_this_round": [_watch_row(w) for w in due],
        "fired_unconsumed": by_status.get("fired") or [],
        "expired": by_status.get("expired") or [],
        "trace_backlog": {
            "needs_attention": needs_attention,
            "total": len(backlog),
            "wake_state_labels": dict(WAKE_STATE_LABELS),
        },
        "notes": {
            "stalled": "停滯不等於死亡：到期日仍會兜底，主動輪詢也能撈回。持續攀升代表被動喚醒涵蓋率不足。",
            "budget": "每輪主動輪詢的上限由 `config/event_watch.json` 的 `sweep_budget_per_run` 決定；"
                      "budget=0 或 enabled=false 時系統退回純被動。",
            "fired": "fired 未消化＝事件已觸發但還沒有人去處理；它不會自己消失。",
        },
        "this_is_not": list(WATCHES_THIS_IS_NOT),
        "materializer": {
            "version": WATCHES_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload = redact_private_paths(payload)
    payload["freshness_identity"] = state_freshness_identity(
        kind="watches", as_of=None,
        # 認知狀態＝有哪些 watch、各自什麼狀態、哪些停滯、哪幾筆 backlog 需要人。
        # `poll.last_checked` 動了不算認知變了（那只是「我今天查過了」）。
        identity={"active": sorted(row["watch_id"] for row in active),
                  "stalled": sorted(row["watch_id"] for row in active if row["stalled"]),
                  "fired": sorted(row["watch_id"] for row in payload["fired_unconsumed"]),
                  "expired": sorted(row["watch_id"] for row in payload["expired"]),
                  "needs_attention": sorted(str(row.get("lead_id")) for row in needs_attention)})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def materialize_watches(*, store: StateArtifactStore | None = None,
                        generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """讀 Event Watch registry 與追源 backlog 並寫下 artifact。**唯讀**：不喚醒、不標記、不寫 lead。"""
    from engine_b import event_watch as ew
    from engine_b import leads as leads_mod

    watch_data = ew.load_watches()
    payload = build_watches_artifact(
        watch_data, config=ew.load_config(), backlog=leads_mod.trace_backlog(leads_mod.load()),
        due=ew.sweep_due(watch_data), generated_at=generated_at)
    target = store or StateArtifactStore()
    return target.write(payload), payload


# ---------------------------------------------------------------------------
# state artifact：`positions`（部位與問責；照抄 outcome 腳本與 Decision Store 計數器）
# ---------------------------------------------------------------------------

POSITIONS_MATERIALIZER_VERSION = "webapp-materialize-positions/1"

POSITIONS_THIS_IS_NOT = (
    "**不是績效報告。** 「shadow 報酬」的錨點是**入圖日**——那天的語意是「這家公司的 claim 進圖了」，"
    "不是「那天該買」。它不含任何進場時點判斷，**不構成選股能力的證據**。",
    "「live 報酬」才以實際成交價為錨點；兩者語意不同，不得混為同一個數字。",
    "不是回測：各檔錨點日不同，等權重聚合是跨持有期的粗聚合。",
    "樣本效度先於數字：錨點跨度短就不得視為 N 個獨立樣本——同一段行情被相關標的複製多次時，有效 n 接近 1。",
    "本 APP 不寫任何東西：不 close、不記錄選擇、不改 thesis；live choice／fill 永遠是本機人工動作。",
    "本 APP 不重算：每一格都是 materialize 當下 `scripts/outcome_if_settled_today.py` 與 Decision Store 的輸出照抄。",
)

_POSITIONS_AUTHORITY = {
    "function": "scripts.outcome_if_settled_today.collect ＋ DecisionStore.capital_expression_counters",
    "command": "python scripts/outcome_if_settled_today.py",
    "note": "與 daily 印的那份**同一個函式**——APP 不另算一份（第二份會立刻開始偏離）。"
            "materialize 只呼叫 collect()，不呼叫 render，所以不 append 排序快照、不寫聚合檔：唯讀。",
}


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _position_row(row: Mapping[str, Any], *, benchmark: str, reference: str) -> dict[str, Any]:
    """一列的投影：每一格照抄，只把日期序列化。"""
    return {
        "ticker": row.get("ticker"), "company_id": row.get("company_id"),
        "anchor_date": _iso(row.get("anchor_date")), "current_date": _iso(row.get("current_date")),
        "anchor_price": row.get("anchor_raw"), "anchor_currency": row.get("anchor_ccy"),
        "anchor_source": row.get("anchor_source"), "current_price": row.get("current_raw"),
        "pre_anchor_return": row.get("pre_anchor_return"),
        "absolute_return": row.get("absolute_return"),
        "benchmark_return": row.get(f"bench_{benchmark}"),
        "excess_return": row.get(f"excess_{benchmark}"),
        "reference_return": row.get(f"bench_{reference}"),
        "notes": list(row.get("note") or ()),
    }


def build_positions_artifact(results: Sequence[Mapping[str, Any]],
                             unavailable: Sequence[Mapping[str, Any]], *,
                             has_benchmark: bool, aggregate: Mapping[str, Any],
                             power_law: Mapping[str, Any] | None,
                             bet_convergence: Mapping[str, Any] | None,
                             health: Mapping[str, Any] | None, live_rows: Sequence[Mapping[str, Any]],
                             paper_only: Sequence[str], counters: Mapping[str, Any],
                             benchmarks: tuple[str, str],
                             generated_at: datetime | None = None) -> dict[str, Any]:
    """outcome 腳本的結果 ＋ Decision Store 計數器 → `positions` state artifact。**純函式**。"""
    primary, reference = benchmarks
    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    rows = [_position_row(r, benchmark=primary, reference=reference) for r in results]
    rows.sort(key=lambda r: -(r["absolute_return"] if r["absolute_return"] is not None else -9))
    live = [{**dict(row), "executed_at": _iso(row.get("executed_at"))} for row in live_rows]
    measured_live = sum(1 for row in live if row.get("live_return") is not None)
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["positions"],
        "kind": "positions",
        "title": "部位與問責：已投的怎麼樣、系統準不準",
        "generated_at": stamp.isoformat(),
        "as_of": None,
        "point_in_time": {"mode": "current", "as_of": None, "excluded": None},
        "authority": dict(_POSITIONS_AUTHORITY),
        "counters": {
            "eligible_cohorts": counters.get("eligible_cohorts"),
            "legacy_eligible_cohorts": counters.get("legacy_eligible_cohorts"),
            "total_cohorts": counters.get("total_cohorts"),
            "shadow_measurable_cohorts": counters.get("shadow_measurable_cohorts"),
            "shadow_anchored_cohorts": counters.get("shadow_anchored_cohorts"),
            "outcomes": counters.get("outcomes"),
            "measured_outcomes": counters.get("measured_outcomes"),
            "live_choices": counters.get("live_choices"),
            "live_fills": counters.get("live_fills"),
            "duplicate_cohort_companies": counters.get("duplicate_cohort_companies"),
            "orphan_cohorts": counters.get("orphan_cohorts"),
        },
        "benchmarks": {"primary": primary, "reference": reference, "available": bool(has_benchmark)},
        "aggregate": dict(aggregate),
        # D15 三量（2026-09-18）。**與 `aggregate` 並列不是取代**：等權絕對報酬回答
        # 「排序整體準不準」，這三個回答「有沒有抓到那一檔」——power-law 的賭注是
        # 小賠多檔一檔補回，平均值天生看不到它。`None` ＝ 這次沒算（舊呼叫端），
        # 不是「算了但都是 0」（L12）。
        "power_law": None if power_law is None else dict(power_law),
        # V4 賭注收斂（2026-09-19）。**第三個維度，不取代前兩個**：等權絕對問「排序整體準不準」、
        # power-law 問「有沒有抓到那一檔」，這一個問「**共識朝我們移動了嗎**」——而它不需要
        # 賣出就能驗證，也不受同漲同跌的 beta 污染（AGENTS「N 檔不等於 N 個獨立機會」）。
        # `None` ＝ 這次沒算，不是「算了但都是 0」（同 `power_law` 的取捨）。
        "bet_convergence": None if bet_convergence is None else dict(bet_convergence),
        # 時序（2026-09-11）。**照抄 `outcome_if_settled_today` 落的檔案，不重算**——
        # 沒有歷史就做不了樣本外驗證（ROADMAP §F：保存當時的 PIT view，事後對 actual 算誤差）。
        "aggregate_series": _outcome_series(),
        "anchor_health": None if health is None else {
            **{k: v for k, v in health.items() if k not in {"first", "last"}},
            "first": _iso(health["first"]), "last": _iso(health["last"]),
        },
        "rows": rows,
        "unavailable": [{"ticker": u.get("ticker") or u.get("research_ticker"),
                         "cohort_id": u.get("cohort_id"), "status": u.get("status")}
                        for u in unavailable],
        "live": {"rows": live, "measured": measured_live,
                 "tickers": sorted({row["ticker"] for row in live}),
                 "paper_only": sorted(paper_only)},
        "notes": {
            "two_anchors": "「live 報酬」以**實際成交價**為錨點，「shadow 報酬」以**入圖日**為錨點。"
                           "兩者語意不同：後者不含任何進場時點判斷，不構成選股能力的證據。",
            "aggregate": "等權重聚合是**推薦籃子**的量測基準：每檔等權，回答排序整體有沒有跑贏。"
                         "各檔錨點日不同，這是跨持有期的粗聚合，**不是回測**。",
            "power_law": "D15 三量問的是**另一個問題**：有沒有抓到那一檔。"
                         "`top_contributor` 與 `rest_contribution` 是恆等式的兩端"
                         "（籃子總報酬 ＝ 最大單檔 ＋ 其餘），刻意不做除法——"
                         "籃子總報酬接近 0 時比例會爆成幾萬 %。"
                         "`maturity` 的分母是**已滿 12／24 個月的檔數**，分母 0 時 `share` 是 "
                         "`null` 不是 0.0：「還沒有一檔滿一年」與「滿了但沒翻倍」是相反的結論。"
                         "`reached_2x_ever` 用期間高點、`reached_2x_now` 用現價——"
                         "D3 定案出場只認反證，所以抱著回吐是預期內的，兩個都要看得到。",
            "bet_convergence": "V4 問的是**不依賴賣出的驗證**：自我們寫下賭注那天起，共識朝我們移動了嗎。"
                               "起算日是**賭注寫下日**不是判斷日（賭注多半晚於判斷好幾天，用判斷日會把"
                               "賭注還不存在那段期間的共識變動算成朝我們移動）。"
                               "`unchanged`（市場看過沒改）與 `not_yet_observable`（還沒輪到市場說話）"
                               "是相反的結論，不得合併；`window_days` 短時「沒動」幾乎是必然。"
                               "⚠ 同向不等於同因——共識可能因為我們沒想到的理由朝同一個方向動。",
            "sample_validity": "**樣本效度先於數字**：錨點跨度短就不得視為 N 個獨立樣本——"
                               "反過來讀的話，一份有效 n 接近 1 的觀測會看起來像 N 個獨立驗證。",
            "judgment_anchor": "要讓這張表變成選股能力的證據，需要的不是等更久，"
                               "是讓錨點帶有進場判斷（`record-choice --user-sized` 的 `decided_at`）。",
            "monitoring": "alpha live 部位目前**不在** `event_search_requests` 的自動監控範圍"
                          "（那條只走 beta instruments）——有 live 部位時沒有人在自動看跌幅。",
        },
        "this_is_not": list(POSITIONS_THIS_IS_NOT),
        "materializer": {
            "version": POSITIONS_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload = redact_private_paths(payload)
    payload["freshness_identity"] = state_freshness_identity(
        kind="positions", as_of=None,
        # 認知狀態＝有哪些 cohort 被量測、有哪些真實成交、計數器的分子分母。
        # 價格與報酬每天都在動，那是內容變了不是判斷變了（L12）。
        identity={"tickers": sorted(str(r["ticker"]) for r in rows),
                  "measured": sorted(str(r["ticker"]) for r in rows if r["absolute_return"] is not None),
                  "live": sorted({str(row["ticker"]) for row in live}),
                  "counters": {k: payload["counters"][k] for k in
                               ("eligible_cohorts", "total_cohorts", "live_choices", "live_fills")}})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def materialize_positions(*, store: StateArtifactStore | None = None,
                          generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """跑一次 outcome 的 `collect()` 並寫下 artifact。

    ⚠ **只呼叫 `collect()`，不呼叫 render**——所以不 append 排序快照、不寫聚合檔：
    materialize 端維持唯讀（那兩個寫入是 daily 那支腳本的責任，不該被 APP 重複觸發）。
    """
    import importlib.util

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "outcome_if_settled_today", root / "scripts" / "outcome_if_settled_today.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("找不到 scripts/outcome_if_settled_today.py")
    outcome = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(outcome)

    results, unavailable, benchmarks = outcome.collect()
    from decision_lab.bootstrap import open_default_store

    store_handle = open_default_store()
    try:
        counters = dict(store_handle.capital_expression_counters())
    finally:
        store_handle.close()
    live_rows, paper_only = outcome.live_lane_rows(results, outcome._live_fills())
    payload = build_positions_artifact(
        results, unavailable, has_benchmark=bool(benchmarks),
        aggregate=outcome.equal_weight_aggregate(results),
        power_law=outcome.power_law_aggregate(results),
        bet_convergence=outcome._jsonable(outcome.collect_bet_convergence()),
        health=outcome.anchor_health(results),
        live_rows=live_rows, paper_only=paper_only, counters=counters,
        benchmarks=(outcome.PRIMARY_BENCHMARK, outcome.REFERENCE_BENCHMARK),
        generated_at=generated_at)
    target = store or StateArtifactStore()
    return target.write(payload), payload


def materialize_basket(*, store: StateArtifactStore | None = None, analyst_store: ArtifactStore | None = None,
                       generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """V3：籃子頁。**只讀三份已 materialize 的 artifact**（ranking／positions／每檔 overview），不連 DB、不跑模型。
    ⚠ 要在 ranking／positions／單檔之後跑，否則 join 的是舊的。"""
    from .basket import build_basket_artifact

    target = store or StateArtifactStore()
    ranking, _f = target.read("ranking")
    try:
        positions, _f2 = target.read("positions")
    except ArtifactUnavailable:
        positions = None
    overviews: dict[str, Mapping[str, Any]] = {}
    for ticker, payload, _fresh, _reason in (analyst_store or ArtifactStore()).read_all():
        if payload is not None:
            overviews[str(ticker)] = payload.get("overview") or {}
    # Phase 4a（2026-09-19）：D11 兩條機械條件的取數在這裡做，**不在純函式裡**。
    # ⚠ 正規化要打 FX——materialize 一輪只跑一次，而且它**不是 request path**
    # （APP 呈現契約禁的是 request path 抓外部）。取數失敗時 `screen` 留空，
    # 那兩條就**完全不套**（不是當成通過）。
    screen: dict[str, Any] = {}
    thresholds: dict[str, Any] | None = None
    try:
        from alpha.providers.market_normalization import screen_inputs

        config_path = Path(__file__).resolve().parents[1] / "config" / "alpha_screen.json"
        thresholds = json.loads(config_path.read_text(encoding="utf-8"))
        screen = dict(screen_inputs([str(r.get("ticker")) for r in (ranking.get("rows") or ())
                                     if r.get("ticker")]))
    except Exception as exc:  # noqa: BLE001 — 取數失敗只讓那兩條不套，不讓 basket 失敗
        screen, thresholds = {}, None
        print(f"  ⚠ D11 兩條未套用：{type(exc).__name__}: {str(exc)[:120]}")
    payload = build_basket_artifact(ranking=ranking, overviews=overviews, positions=positions,
                                    generated_at=generated_at, screen=screen,
                                    screen_thresholds=thresholds)
    return target.write(payload), payload


def materialize_account_scorecard(*, store: StateArtifactStore | None = None,
                                  allow_network: bool = True,
                                  generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """D5 帳號計分表（ROADMAP Phase 3）。

    ⚠ **這是唯一會抓價格的 materializer**，所以它只能在 materialize 跑，不能在 request path
    （APP 呈現契約：request path 不得抓外部資料）。心跳同理——心跳零網路，它只**讀**這份
    artifact，算是在這裡算的。`allow_network=False` 時五欄裡與價格有關的會誠實回報沒有值。
    """
    from engine_b.account_scorecard import build_scorecard

    loader = None if allow_network else (lambda *_: {})
    payload = build_scorecard(price_loader=loader)
    if generated_at is not None:
        payload["generated_at"] = generated_at.isoformat()
    target = store or StateArtifactStore()
    return target.write(payload), payload


# ⚠ **2026-09-23（Phase 0 Step 0b.1b）：`materialize_multi_year` 已移除。**
# 它是「要幾倍，哪一格得為真」的 state artifact producer，讀 `briefing.multi_year`（多年反向橋）。
# 多年橋整條在 Phase 0 退役（ROADMAP Phase 0／D 組）；state kind 已於 Step 0a.2 從封閉字彙移除，
# 這裡是它最後一個活的 import。


def materialize_structure_readings(*, store: StateArtifactStore | None = None,
                                   as_of: date | None = None,
                                   generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """每一份讀圖紀錄跟現在的圖還一不一致。**唯讀**：讀 ledger ＋ 查圖 ＋ 確定性比對。

    ⚠ 一次把圖的邊載進來（`_load_edges`），對每個節點各建一次 `StructureView`——
    不是每個節點各查一次圖。節點數會長，查詢次數不該跟著長。
    """
    from alpha.providers.structure_readings import known_nodes, read_reading_records
    from alpha.structure_reading import needs_reread, reading_status, select_reading
    from query.structure import _load_edges, build_structure

    target = store or StateArtifactStore()
    today = as_of or date.today()
    nodes = known_nodes()
    rows: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    edges = _load_edges() if nodes else []
    for node in nodes:
        records, errors = read_reading_records(node)
        parse_errors.extend(errors)
        reading = select_reading(records, as_of=as_of, today=today)
        if reading is None:
            # 有檔案但沒有現行紀錄（全部被撤回）——**不是「沒有這個節點」**，照實列出（INV-3）。
            rows.append({"node": node, "status": None, "reading_id": None,
                         "reason": "ledger 有紀錄但目前沒有現行的那一筆（已全部撤回）"})
            continue
        view = build_structure(node, edges)
        status = reading_status(reading, view.as_dict(), today=today)
        rows.append({
            "node": node,
            "reading_id": reading.reading_id,
            "kind": reading.kind,
            "reading": reading.reading,
            "tickers": list(reading.tickers),
            "read_on": reading.created_on.isoformat(),
            "expires": reading.expires.isoformat(),
            **status,
            "needs_reread": needs_reread(status),
        })
    payload = build_structure_readings_artifact(rows=rows, parse_errors=parse_errors,
                                                generated_at=generated_at, as_of=as_of)
    return target.write(payload), payload


def _outcome_series(limit: int = 180) -> dict[str, Any]:
    """等權聚合的時序。唯讀既有檔案；壞掉的行跳過但**不靜默丟掉整串**（INV-3）。"""
    path = (Path(__file__).resolve().parents[1] / "library" / "private" / "decision_lab"
            / "outcome_aggregate.jsonl")
    if not path.is_file():
        return {"rows": [], "skipped": 0,
                "reason": "尚無時序——2026-09-11 起才累積；在那之前是覆寫制，"
                          "只有當天一個快照（所以歷史拿不回來，不是讀不到）"}
    rows: list[dict[str, Any]] = []
    skipped = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            rows.append(json.loads(text))
        except ValueError:
            skipped += 1
    rows.sort(key=lambda r: str(r.get("date") or ""))
    return {"rows": rows[-limit:], "skipped": skipped,
            "reason": None if rows else "檔案存在但沒有可解析的列"}


def write_vocabularies(store: ArtifactStore | None = None) -> Path:
    """把封閉字彙寫成 `.meta.json`，讓 serve 端讀得到而**不必 import `alpha`／`briefing`**。

    這是 L16 的直接應用：分類已經有 SSOT，要做的是**讓它跟著資料走到需要它的地方**，
    而不是在 APP 端再寫一份「absence_kind 是什麼意思」的對照表。
    """
    from alpha.absence import ABSENCE_KINDS, SETTLED_ABSENCE_KINDS
    from briefing.analyst_view.contracts import (
        ACCOUNTING_BASIS_DISPLAY, CORE_PANELS, OPTIONAL_PANELS, PLAIN_ABSENCE_SHORT,
        PLAIN_DRIVER_LABELS, PLAIN_MULTIPLE_DERIVATION,
        PLAIN_LINE_LABELS, PLAIN_PANEL_TITLES, PLAIN_READINESS, PLAIN_STANCE,
        PRICE_SERIES_NOTE, QUESTIONS,
        WEAK_INPUT_RULES,
    )

    target = store or ArtifactStore()
    target.directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "absence_kinds": dict(ABSENCE_KINDS),
        "settled_absence_kinds": sorted(SETTLED_ABSENCE_KINDS),
        "accounting_basis_display": {k: dict(v) for k, v in ACCOUNTING_BASIS_DISPLAY.items()},
        # 面向使用者的白話別名（2026-09-08）。**字彙一個字沒改**——這是同一個東西的第二種說法，
        # 而且只有一份：前端不得再自己維護一張對照表（先前 app.js 的 ABSENCE_SHORT 就是重造品，L16）。
        "plain_panel_titles": {k: dict(v) for k, v in PLAIN_PANEL_TITLES.items()},
        "plain_line_labels": dict(PLAIN_LINE_LABELS),
        "plain_absence_short": dict(PLAIN_ABSENCE_SHORT),
        "plain_readiness": {k: dict(v) for k, v in PLAIN_READINESS.items()},
        # opinion stance 的白話層（2026-09-10）：前端不得再寫第二份（L16）。
        "plain_stance": {k: dict(v) for k, v in PLAIN_STANCE.items()},
        "plain_driver_labels": dict(PLAIN_DRIVER_LABELS),
        "plain_multiple_derivation": {k: dict(v) for k, v in PLAIN_MULTIPLE_DERIVATION.items()},
        "price_series_note": PRICE_SERIES_NOTE,
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


__all__ = ["BETA_MATERIALIZER_VERSION", "BETA_THIS_IS_NOT", "COVERAGE_MATERIALIZER_VERSION",
           "COVERAGE_THIS_IS_NOT", "MATERIALIZER_VERSION", "RANKING_MATERIALIZER_VERSION",
           "RANKING_THIS_IS_NOT", "WATCHES_MATERIALIZER_VERSION", "WATCHES_THIS_IS_NOT",
           "WAKE_STATE_LABELS", "build_beta_artifact", "build_coverage_artifact", "build_overview",
           "build_ranking_artifact", "build_watches_artifact", "materialize", "materialize_beta",
           "materialize_coverage", "materialize_many", "materialize_ranking", "materialize_view",
           "materialize_watches", "POSITIONS_MATERIALIZER_VERSION", "POSITIONS_THIS_IS_NOT",
           "build_positions_artifact", "materialize_positions",
           "redact_private_paths", "write_vocabularies", "materialize_basket",
           "materialize_account_scorecard"]
