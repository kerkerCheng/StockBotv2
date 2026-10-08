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

from .diagrams import diagrams_for_nodes, load_diagrams
from .structure_readings import build_structure_readings_artifact
from .contracts import (
    ARTIFACT_SCHEMA_VERSION, STATE_SCHEMA_VERSIONS, ArtifactUnavailable, canonical_digest, freshness_identity,
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


def _candidate_overview(panel: Mapping[str, Any]) -> dict[str, Any]:
    """首頁分組（2026-10-07 使用者指示）：這檔落在候選板的哪一格——**照抄**候選面板那一格（與候選板同一個
    `derive_row`），鍵與中文都由產生端給，這裡不判、不造字。沒有那一格時，「沒寫敘事」與「這次沒讀到」分兩組
    （L12）：看面板自己宣告的缺席種類。"""
    from alpha.candidates import LIST_GROUPS

    datum = _line_map(panel).get("candidate:state") or {}
    row = datum.get("value")
    if isinstance(row, Mapping):
        if row.get("derived") in LIST_GROUPS:
            return {"list_group": str(row["derived"]), "label": row.get("derived_label"), "absence_kind": None}
        # 有候選列、值卻不在首頁分組字彙裡＝字彙漏了一格（不是「沒讀到」）：照實寫出那個值
        return {"list_group": "unavailable", "label": None, "absence_kind": "upstream_unavailable",
                "reason": f"候選狀態的值 {row.get('derived')!r} 不在首頁分組字彙裡（alpha.candidates.LIST_GROUPS）"}
    kind = datum.get("absence_kind") or panel.get("absence_kind")
    return {"list_group": "no_narrative" if kind == "not_yet_recorded" else "unavailable", "label": None,
            "absence_kind": kind or "upstream_unavailable", "reason": datum.get("reason") or panel.get("reason")}


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
        # 2026-10-07（使用者指示）：首頁照候選狀態分組。照抄候選面板（與候選板同一個推導）。
        "candidate": _candidate_overview(view.get("candidate") or {}),
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
        # ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`opinion_stance`（我們有沒有形成自己的觀點）退役——
        # 它是 FY+1 模型對估值假設 `derivation` 的聚合。「有沒有自己的觀點」改由讀圖與敘事回答（Phase 2）。
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
                     price_series: Sequence[Mapping[str, Any]] | None = None,
                     page_extra: Mapping[str, Any] | None = None,
                     diagrams: Sequence[Mapping[str, Any]] | None = None,
                     node_names: Mapping[str, str] | None = None,
                     demand_anchor: Mapping[str, Any] | None = None,
                     capture: Mapping[str, Any] | None = None,
                     what_it_does: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """`AnalystView.to_dict()` → artifact payload（含遮蔽、overview、兩個 digest）。純函式。

    `price_series` 是**脈絡不是判讀**：一條這檔自己的已收盤收盤價序列，讓使用者看得懂
    「現在這個價位在哪」。它不參與任何計算——`freshness_identity` 不含它（價格動了不算認知變了）。
    `page_extra`：個股頁 schema 填得滿表的頁外輸入（`layer_notes`＝引用這一頁的層說明節點）；沒給＝這一輪沒讀到，
    那一格印 `upstream_unavailable`（不是「沒有」）。
    `diagrams`：涵蓋這一頁坐的層的技術示意圖（`webapp.diagrams`；已檢查過、編成 data URI）——呈現用，不進新鮮度身分。
    `node_names`：坐的層的節點名——同上，呈現用（`content_digest` 照常涵蓋整份 artifact）。
    """
    from briefing.analyst_view.page_schema import PAGE_SCHEMA_VERSION, fill_summary, fill_table

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
        # 個股頁 schema 的填得滿表（2026-10-08，個股頁 S2）：每個元素有值或具名缺席，每次 materialize 重算、印在稽核區。
        # 合約（塊、元素、缺席宣告、證據等級對照）在 `.meta.json` 的 `page_schema`，這裡只放這一檔的逐格結果。
        "page_fill": _page_fill(view, page_extra, fill_table, fill_summary, PAGE_SCHEMA_VERSION),
        # 技術示意圖（2026-10-08，個股頁 S5b）：標「示意」、附出處；研究 session 畫，APP 用 <img> 顯示。
        "diagrams": [dict(d) for d in (diagrams or ())],
        # 坐的層的節點名（2026-10-08）：「技術鏈」的展開印名字、不印 `tech:…` ID——呈現用，不進新鮮度身分。
        "node_names": dict(node_names or {}),
        # 需求錨序列（個股頁 S3a，2026-10-08）：這家公司走到的錨對到的 A2 序列（季值、年增、可知日、缺哪一家），
        # 或缺席與原因。照抄 `alpha.demand_anchor`；APP 畫 B2「錨的變化」。
        "demand_anchor": dict(demand_anchor) if demand_anchor is not None else None,
        # 吃到多少（個股頁 S3b）：公司同一曆季營收（換美元）÷ 錨；照抄 `alpha.capture`（季、匯率、可知日、缺哪個）。
        "capture": dict(capture) if capture is not None else None,
        # 頁首「做什麼」（2026-10-08）：押的層或插槽（敘事）或圖上它供貨開發的節點（圖），與在示意圖的哪一格——`what_it_does` 組好照印。
        "what_it_does": dict(what_it_does) if what_it_does is not None else None,
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


def _page_fill(view: Mapping[str, Any], extra: Mapping[str, Any] | None, fill_table: Any, fill_summary: Any,
               version: str) -> dict[str, Any]:
    rows = fill_table(view, extra=extra)
    return {"schema": version, "rows": rows, "summary": fill_summary(rows)}


#: 「做什麼」沒有押的格、改列圖上的節點時最多列幾個（其餘寫「等共 N 個」）。列序是節點 id 的字母序（`seats_from_edges`），不是名次。
WHAT_IT_DOES_SHOWN = 3


def what_it_does(view: Mapping[str, Any], seats: Sequence[str] | None, names: Mapping[str, str],
                 diagrams: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    """頁首「做什麼」（個股頁 B0；2026-10-08 使用者：「這個公司在做甚麼東西是我們關注的…像 COHR 就寫個 CW DFB 雷射，
    一目了然」）。純函式。

    兩個來源分開寫（L12）：敘事宣告的 `rides`（押的層或插槽——研究判斷）優先，寫「押在：…」；沒宣告時才列圖上它供貨或
    開發的節點（`seats_from_edges`——圖的事實），寫「圖上它供貨或開發：…」並說敘事還沒宣告押哪一格；兩個都沒有＝具名缺席。
    `seats` 是 None＝圖這一輪讀不到（不是「圖上沒有」，INV-3）。
    `where_line`：這幾個節點在示意圖的哪一格（畫圖器的位置表）；沒有一格畫到就不印（技術鏈那一塊照樣有圖與說明）。
    只照抄、不排序、不打分。"""
    rides_line = next((line for line in ((view.get("bet") or {}).get("lines") or ())
                       if str(line.get("key") or "") == "rides"), None)
    rides = [r for r in ((rides_line or {}).get("datum") or {}).get("value") or () if isinstance(r, Mapping)]
    seat_list = [str(n) for n in seats or ()]
    if not rides and seats is None:
        return {"source": None, "line": None, "focus": [], "where": [], "where_line": None,
                "absence": {"kind": "upstream_unavailable",
                            "reason": "圖這一輪讀不到，說不出它供貨或開發哪些節點（敘事也還沒宣告押哪一格）"}}
    if rides:
        source, focus = "rides", [str(r.get("node")) for r in rides]
        line = "押在：" + "、".join(f"{r.get('node_name') or r.get('node')}（{r.get('unit_label') or r.get('unit')}）"
                                  for r in rides)
    elif seat_list:
        source, focus = "seats", seat_list
        shown = "、".join(names.get(n) or n for n in seat_list[:WHAT_IT_DOES_SHOWN])
        more = f" 等共 {len(seat_list)} 個" if len(seat_list) > WHAT_IT_DOES_SHOWN else ""
        line = f"圖上它供貨或開發：{shown}{more}（敘事還沒宣告押哪一格）"
    else:
        return {"source": None, "line": None, "focus": [], "where": [], "where_line": None,
                "absence": {"kind": "not_yet_recorded",
                            "reason": "敘事還沒宣告押哪一格，圖上也還沒有它供貨或開發的節點"}}
    want = set(focus)
    where = []
    for d in diagrams or ():
        hit = [str(b.get("title")) for b in d.get("boxes") or () if want & {str(n) for n in b.get("nodes") or ()}]
        if hit:
            where.append({"diagram": str(d.get("id")), "title": str(d.get("title") or ""), "boxes": hit})
    boxes = [title for w in where for title in w["boxes"]]
    where_line = ("示意圖上在" + "、".join(f"「{t}」" for t in boxes) + "（往下「技術鏈」有圖）") if boxes else None
    return {"source": source, "line": line, "focus": focus, "where": where, "where_line": where_line, "absence": None}


def page_extra_for(ticker: str, layer_notes: Mapping[str, Any] | None,
                  diagrams: Sequence[Mapping[str, Any]] | None = None,
                  demand_anchor: Mapping[str, Any] | None = None,
                  capture: Mapping[str, Any] | None = None,
                  what: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """個股頁填得滿表的頁外輸入：引用這一頁的層說明節點（`layer_notes` state artifact 的 `cited_by.pages`）、
    涵蓋這一頁坐的層的示意圖 id（`diagrams`；None＝這一輪沒讀到示意圖目錄）、需求錨序列（`demand_anchor`：有值的序列 key；
    讀不到或回看的那天不推＝不給這個鍵）、「做什麼」講的節點（`what`）。artifact 讀不到 → 那一個鍵不給
    （那一格印這一輪沒讀到，不是「沒有」）。"""
    extra: dict[str, Any] = {}
    if what is not None and ((what.get("absence") or {}).get("kind")) != "upstream_unavailable":
        extra["what_it_does"] = list(what.get("focus") or ())
    if diagrams is not None:
        extra["diagrams"] = [str(d.get("id")) for d in diagrams]
    absence_kind = ((demand_anchor or {}).get("absence") or {}).get("kind")
    if demand_anchor is not None and absence_kind not in ("upstream_unavailable", "point_in_time_unavailable"):
        extra["demand_anchor"] = [str(s.get("key")) for s in demand_anchor.get("series") or () if s.get("points")]
    capture_kind = ((capture or {}).get("absence") or {}).get("kind")
    if capture is not None and capture_kind not in ("upstream_unavailable", "point_in_time_unavailable"):
        extra["capture_ratio"] = [str(capture.get("anchor_key"))] if capture.get("points") else []
    if layer_notes is None:
        return extra or None
    want = str(ticker).upper()
    nodes = [str(row.get("node")) for row in layer_notes.get("rows") or ()
             if any(str(page.get("ticker") or "").upper() == want
                    for page in ((row.get("cited_by") or {}).get("pages") or ()))]
    return {**extra, "layer_notes": nodes}


def _diagrams_loaded() -> dict[str, Any] | None:
    """技術示意圖目錄（載入＋檢查一次）；讀不到目錄以外的錯 → None（B4 那一格印這一輪沒讀到）。"""
    try:
        return load_diagrams()
    except Exception:  # noqa: BLE001 — 示意圖是呈現，讀不到不該讓判讀讀不到
        return None


def _layer_notes_state(state_store: Any = None) -> dict[str, Any] | None:
    try:
        payload, _fresh = (state_store or StateArtifactStore()).read("layer_notes")
        return payload
    except Exception:  # noqa: BLE001 — 讀不到只讓 B4 那一格說沒讀到
        return None


def readings_context(*, today: date | None = None, as_of: date | None = None) -> dict[str, Any]:
    """讀圖面板與 argument 鏈段的輸入（Phase 2 Step 2.7；3.7 起兩者共用）：**一次**載入圖的邊與讀圖 ledger。

    組法住 `alpha.providers.structure_readings.seat_readings_context`（3.7 搬過去：briefing 的 CLI 也要用，
    而 briefing 不得 import webapp）。讀不到就整份回 `upstream_unavailable`，不回空集合（INV-3）。"""
    from alpha.providers.structure_readings import seat_readings_context

    return seat_readings_context(today=today, as_of=as_of)


def readings_input_for(context: Mapping[str, Any], company_id: str | None,
                       ticker: str | None = None) -> dict[str, Any]:
    """一檔的讀圖面板輸入（切片規則住 `alpha.providers.structure_readings.seat_readings_for`；L16）。

    `ticker`：給了就讀它現行的 `readings/demand_side` abstention（2026-09-30），交給切片規則決定採不採用。"""
    from alpha.providers.structure_readings import demand_side_abstention, seat_readings_for

    declared = demand_side_abstention(ticker) if ticker else None
    return seat_readings_for(context, company_id, demand_side=declared)


def bet_structure(state_store: Any = None) -> dict[str, Any]:
    """首屏「是不是新賭注」的需求錨來源（Phase 7 Step 7.0e）：`structure_table` state artifact 的逐列錨——
    `query.bottleneck.structure_table` 的輸出照抄，**唯一來源**；daily 的 materialize 同一輪先寫它（`--structure-table`
    排在個股頁與候選板之前），所以這裡讀到的是同一輪的那一份，不再連一次圖重算。只帶這一步讀的欄位。
    讀不到＝需求錨這半邊 `upstream_unavailable`（層照比），不是「沒有共用」。"""
    store = state_store or StateArtifactStore()
    try:
        payload, _freshness = store.read("structure_table")
    except ArtifactUnavailable as exc:
        return {"absence": {"kind": "upstream_unavailable",
                            "reason": f"結構表讀不到（{getattr(exc, 'reason', None) or exc}）"}}
    keep = ("company_id", "bottleneck", "bottleneck_name", "demand_anchor", "demand_anchor_name", "anchor_basis")
    return {"rows": [{k: r.get(k) for k in keep} for r in payload.get("rows") or ()],
            "generated_at": payload.get("generated_at")}


def _attach_bet_names(context: Mapping[str, Any]) -> None:
    """「是不是新賭注」會印到的層／插槽補上節點名（只補持有那幾家坐的、結構表沒帶到名字的，例如 `develops` 的插槽）。
    **fail-soft**：圖讀不到就不補——畫面照印 ID；名字只是顯示，不是認知狀態（與 `_attach_ride_node_names` 同一個理由）。"""
    bets = context.get("bets") if isinstance(context, Mapping) else None
    held = (context.get("held") or {}) if isinstance(context, Mapping) else {}
    if not bets or held.get("status") != "ok":
        return
    names = bets.setdefault("names", {})
    layers = bets.get("layers") or {}
    wanted = sorted({n for cid in (held.get("by_company") or {}) for n in layers.get(str(cid), ())} - set(names))
    try:
        found = _graph_node_names(wanted)
    except Exception:  # noqa: BLE001 — 名字補不上不擋 materialize
        return
    for node, name in found.items():
        names.setdefault(node, name)


def candidate_context(tickers: Sequence[str], *, as_of: date | None = None, board: bool = False,
                      state_store: Any = None) -> dict[str, Any]:
    """個股頁候選狀態＋downside 的共用輸入（Phase 3 Step 3.7；接回偏差 21）：**一次**載入 watch registry、thesis
    lifecycle、讀圖對圖、Sheet（readonly）、邊緣判定——與候選板同一個載入函式（`alpha.providers.candidates`）。

    as-of 視角不推：watch registry、Sheet、讀圖對圖都只有「現在」（INV-6：答不出 T 時刻的就明確拒絕）。
    讀不到＝`upstream_unavailable`，不是「不上板」（INV-3）。
    `board=True`：同一輪也要組候選板時載**候選板的超集**，一份同時交給個股頁與 `materialize_candidates`——
    否則同一輪兩次讀 Sheet／FX，兩份快照（3.7 R1 實測：SIVE.ST 的市值兩邊差一次 FX）。
    `state_store`：「是不是新賭注」讀哪一份結構表（Phase 7 Step 7.0e；`bet_structure`）——與這一輪寫 state 的是同一個目錄。"""
    if as_of is not None:
        return {"absence": {"kind": "point_in_time_unavailable",
                            "reason": "as-of 視角不推候選狀態與反證 watch——watch registry、Sheet、讀圖對圖都只有現在（INV-6）"}}
    try:
        from alpha.providers.candidates import candidate_context as load

        context = load(list(tickers), board=board, structure=bet_structure(state_store))
        _attach_bet_names(context)
        return context
    except Exception as exc:  # noqa: BLE001 — 讀不到只讓兩個選配面板說讀不到，其餘照走
        return {"absence": {"kind": "upstream_unavailable",
                            "reason": f"候選狀態的輸入沒讀到（{type(exc).__name__}: {str(exc)[:120]}）——不是「不上板」"}}


def candidate_input_for(context: Mapping[str, Any], view: Any) -> dict[str, Any]:
    """一檔的首屏候選狀態＋downside 輸入：把 read model 已算好的三題與舊判讀反證交給 `page_input`（候選板同一個推導）。"""
    if context.get("absence"):
        return {"absence": dict(context["absence"])}
    tq = getattr(view, "three_questions", None)
    if tq is None or (tq.meta.status == "missing" and tq.meta.absence_kind == "upstream_unavailable"):
        three, note = None, (tq.meta.reason if tq is not None else "read model 沒有接三題")
    else:
        three, note = {"will_it_die": list(tq.will_it_die), "priced_in": list(tq.priced_in),
                       "in_numbers": list(tq.in_numbers)}, None
    try:
        from alpha.providers.candidates import page_input

        return page_input(context, str(view.identity.ticker), view.identity.company_id, three_questions=three,
                          three_questions_note=note)
    except Exception as exc:  # noqa: BLE001 — 一檔推不出只讓這一檔的兩個選配面板說讀不到
        return {"absence": {"kind": "upstream_unavailable",
                            "reason": f"這一檔的候選狀態推不出來（{type(exc).__name__}: {str(exc)[:120]}）"}}


def materialize(ticker: str, *, as_of: date | None = None, scenario: str | None = None,
                store: ArtifactStore | None = None,
                generated_at: datetime | None = None,
                readings: Mapping[str, Any] | None = None,
                candidates: Mapping[str, Any] | None = None,
                layer_notes: Mapping[str, Any] | None = None,
                diagrams: Mapping[str, Any] | None = None,
                node_names: Mapping[str, str] | None = None,
                anchors: Mapping[str, Any] | None = None) -> tuple[Path, dict[str, Any]]:
    """跑一次完整鏈並寫下 artifact。**只有這裡會連 Neo4j／Engine C／private ledger。**

    `readings`：`readings_context()` 的結果（多檔時由 `materialize_many` 載入一次傳進來）；沒給就自己載一次。
    3.7 起它同時餵讀圖面板與 argument 鏈段的需求端（同一份，不各載一次）。
    `candidates`：`candidate_context()` 的結果（同上，多檔載一次）；沒給就為這一檔載一次。
    `node_names`：坐的層的節點名（`_seat_node_names`；多檔時載一次）；沒給就只查這一檔坐的那幾個。
    `anchors`：需求錨序列（`_anchor_context`；多檔時載一次）；沒給就為這一檔載一次。
    """
    from briefing.alpha_view.sources import fetch_alpha_investment_view
    from briefing.analyst_view import build_analyst_view

    context = readings if readings is not None else readings_context(as_of=as_of)
    view = fetch_alpha_investment_view(ticker, as_of=as_of, include_causal=False, scenario=scenario,
                                       seat_readings=context)
    candidate_ctx = candidates if candidates is not None else candidate_context([ticker], as_of=as_of)
    analyst = build_analyst_view(view, readings=readings_input_for(context, view.identity.company_id,
                                                                        str(view.identity.ticker)),
                                 candidate=candidate_input_for(candidate_ctx, view))
    notes_state = layer_notes if layer_notes is not None else _layer_notes_state()
    loaded = diagrams if diagrams is not None else _diagrams_loaded()
    seats = ((context or {}).get("seats") or {}).get(view.identity.company_id) or ()
    page_diagrams = None if loaded is None else diagrams_for_nodes(loaded, seats)
    names = node_names if node_names is not None else _seat_node_names({"seats": {"_": list(seats)}})
    anchor_ctx = anchors if anchors is not None else _anchor_context(as_of)
    demand = _page_demand_anchor(anchor_ctx, candidate_ctx, view.identity.company_id)
    capture = _page_capture(str(view.identity.ticker or ticker), demand, as_of)
    analyst_dict = analyst.to_dict()
    graph_read = isinstance((context or {}).get("seats"), Mapping)        # 讀圖 context 讀不到＝說不出坐哪幾格（不是「沒有」）
    what = what_it_does(analyst_dict, seats if graph_read else None, names, page_diagrams)
    payload = materialize_view(analyst_dict, generated_at=generated_at,
                               price_series=_close_series(ticker),
                               page_extra=page_extra_for(ticker, notes_state, page_diagrams, demand, capture, what),
                               diagrams=page_diagrams,
                               node_names={str(n): names[str(n)] for n in seats if str(n) in names},
                               demand_anchor=demand, capture=capture, what_it_does=what)
    target = store or ArtifactStore()
    return target.write(payload), payload


def _anchor_context(as_of: date | None) -> dict[str, Any]:
    """需求錨序列（個股頁 S3a；取數 `alpha.providers.demand_anchor`、組法 `alpha.demand_anchor`）：一輪載入一次
    （as-of T 只用 `filed ≤ T` 的申報）。讀不到 Engine C 或設定 → `{"absence": …}`——B2「錨的變化」印這一輪沒讀到，不是「沒有成長」。"""
    from alpha.providers.demand_anchor import anchor_context
    from engine_c.db import get_conn

    try:
        conn = get_conn()
    except Exception as exc:  # noqa: BLE001 — 錨是 B2 的一格，讀不到不擋整份判讀
        return {"absence": {"kind": "upstream_unavailable", "reason": f"Engine C 讀不到（{type(exc).__name__}: {str(exc)[:120]}）"}}
    try:
        return anchor_context(conn, as_of=as_of or date.today())
    finally:
        conn.close()


def _page_demand_anchor(anchor_ctx: Mapping[str, Any] | None, candidate_ctx: Mapping[str, Any] | None,
                        company_id: str | None) -> dict[str, Any]:
    """一頁的「錨的變化」：這家公司在結構表走到的需求錨（候選輸入 `bets.anchors`，與「是不是新賭注」同一份）→ 對到的序列。
    結構表的錨讀不到（或回看的那天不推）＝讀不到，不是「走不到錨」（L12）。"""
    from alpha.demand_anchor import page_anchor

    ctx = candidate_ctx if isinstance(candidate_ctx, Mapping) else {}
    bets = ctx.get("bets") if isinstance(ctx.get("bets"), Mapping) else None
    if ctx.get("absence") or bets is None or bets.get("anchors_absence"):
        source = ctx.get("absence") or (bets or {}).get("anchors_absence") or {}
        kind = source.get("kind") if source.get("kind") == "point_in_time_unavailable" else "upstream_unavailable"
        return {"anchors": [], "series": [], "absence": {
            "kind": kind, "reason": f"結構表的需求錨這一輪讀不到（{source.get('reason') or '候選輸入沒有需求錨'}）"}}
    return page_anchor(anchor_ctx, (bets.get("anchors") or {}).get(str(company_id)), bets.get("names"))


def _page_capture(ticker: str, demand: Mapping[str, Any] | None, as_of: date | None) -> dict[str, Any]:
    """一頁的「吃到多少」（個股頁 S3b；`alpha.providers.capture`）：公司同一曆季的營收（換美元）÷ 錨。
    讀不到 Engine C → 這一格印這一輪沒讀到（不是「吃到 0」）。"""
    from alpha.providers.capture import page_capture
    from engine_c.db import get_conn

    try:
        conn = get_conn()
    except Exception as exc:  # noqa: BLE001 — 吃到多少是 B2 的一格，讀不到不擋整份判讀
        return {"points": [], "gaps": [], "absence": {"kind": "upstream_unavailable",
                                                      "reason": f"Engine C 讀不到（{type(exc).__name__}）"}}
    try:
        return page_capture(conn, ticker, demand, as_of=as_of or date.today())
    except Exception as exc:  # noqa: BLE001
        return {"points": [], "gaps": [], "absence": {"kind": "upstream_unavailable",
                                                      "reason": f"吃到多少算不出來（{type(exc).__name__}: {str(exc)[:120]}）"}}
    finally:
        conn.close()


def _seat_node_names(context: Mapping[str, Any] | None) -> dict[str, str]:
    """讀圖 context 裡每一個坐的節點在圖上的名字（個股頁「技術鏈」的展開印名字、不印 `tech:…` ID；2026-10-08）。
    **fail-soft**：圖讀不到就回空——畫面照印 ID；名字只是顯示，不是認知狀態（與 `_attach_ride_node_names` 同一個理由）。"""
    nodes = sorted({str(n) for seats in ((context or {}).get("seats") or {}).values() for n in seats or ()})
    try:
        return _graph_node_names(nodes)
    except Exception:  # noqa: BLE001 — 名字補不上不擋 materialize
        return {}


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
                     store: ArtifactStore | None = None,
                     candidates: Mapping[str, Any] | None = None,
                     state_store: StateArtifactStore | None = None) -> list[tuple[str, Path | None, str | None]]:
    """一次 materialize 多檔。**一檔失敗不影響其他檔**——失敗以理由現形，不靜默跳過（INV-3）。
    `state_store`：沒給 `candidates` 時，候選輸入讀哪一份結構表（「是不是新賭注」；Phase 7 Step 7.0e）。"""
    target = store or ArtifactStore()
    results: list[tuple[str, Path | None, str | None]] = []
    # 讀圖面板的輸入只載一次（節點數會長，查詢次數不該跟著檔數長）；候選狀態的輸入同理（Sheet、watch、讀圖對圖）。
    readings = readings_context(as_of=as_of) if tickers else None
    if candidates is None and tickers:
        candidates = candidate_context(tickers, as_of=as_of, state_store=state_store)
    notes_state = _layer_notes_state(state_store) if tickers else None
    loaded = _diagrams_loaded() if tickers else None
    names = _seat_node_names(readings) if tickers else None
    anchors = _anchor_context(as_of) if tickers else None
    for ticker in tickers:
        try:
            path, _ = materialize(ticker, as_of=as_of, store=target, readings=readings, candidates=candidates,
                                  layer_notes=notes_state, diagrams=loaded, node_names=names, anchors=anchors)
        except Exception as exc:  # noqa: BLE001 — 逐檔隔離；理由原樣回報
            results.append((ticker, None, f"{type(exc).__name__}: {str(exc)[:200]}"))
        else:
            results.append((ticker, path, None))
    return results


# ---------------------------------------------------------------------------
# state artifact：`structure_table`（跨標的；照抄 `structure_table()` 的輸出）
# ⚠ 2026-09-23（Phase 0 Step 0b.3）：這裡原本是 `ranking` kind——首選、可行動／純結構兩份序、
# 產業別分組、落差註記、門檻濾掉的列。跨檔排序退役（G1／L19），artifact 只剩逐邊的結構事實、
# 母體定義的 INV-3 報告與 anchor gap 診斷。
# ---------------------------------------------------------------------------

STRUCTURE_TABLE_MATERIALIZER_VERSION = "webapp-materialize-structure-table/1"

#: 這份表**不是什麼**。隨 artifact 出門，讓畫面永遠印得出來（AGENTS「圖是中心」：不得輸出跨檔全序或首選；
#: 系統不給部位尺寸）。
STRUCTURE_TABLE_THIS_IS_NOT = (
    "不是排序、不是首選、不是回測——它是圖中「公司→向下邊」的逐邊結構事實；跨檔排序已於 2026-09-23 退役（G1）。",
    "不給部位尺寸：買多少、什麼時候買由使用者自行判斷並手動下單。",
    "不是「發現新標的」——只列已研究過的公司；圖裡沒有的公司不會出現。",
    "不含 lead time、不含瓶頸業務占該公司營收多少、不含市值／分析師覆蓋——那些在 Engine C，不在本表內。",
    "每檔的 disproof 與催化劑不在本表：點進單檔判讀（Analyst View）的「研究現況」才有。",
    "本 APP 不重算、不重排、不加權：順序與每一格都是 materialize 當下 structure_table() 的輸出照抄；列序是索引不是名次。",
)

_STRUCTURE_TABLE_AUTHORITY = {
    "function": "query.bottleneck.structure_table",
    "command": "python -m query.bottleneck",
    "note": "結構事實只有這一份（不排序、不設門檻）。本 artifact 照抄它的輸出：不重算、不重排、不加權，"
            "也不自建第二套結構評分。",
}


def _company_label(registry: Any, company_id: str) -> str | None:
    """面向人的公司名：registry 的 `display_name`，退而求其次用 `name`；**都沒有就 None，
    不從 ID 猜名字**（`co:iqe` → 「Iqe」是編出來的，不是公司的名字）。"""
    lookup = getattr(registry, "company", None)
    company = lookup(company_id) if callable(lookup) else None
    if company is None:
        return None
    return getattr(company, "display_name", None) or getattr(company, "name", None) or None


def _project_table_row(row: Mapping[str, Any], *, registry: Any,
                       evidence_label: Mapping[str, str],
                       node_names: Mapping[str, str] | None = None,
                       anchor_basis_label: Mapping[str, str] | None = None) -> dict[str, Any]:
    """一列的投影：**每一格照抄**，只加上公司名、節點名與證據標籤——沒有任何算術，也沒有名次。

    節點名（2026-09-30 使用者回饋：結構表滿是 `tech:cpo_full_stack_test` 這種內部代號）取自圖裡節點的 `name`；
    圖裡沒有名字就是 None，**不從 ID 猜**（畫面照印 ID）。公司名先用 registry，registry 沒有才用圖裡的名字。"""
    names = node_names or {}
    out = dict(row)
    out["company_label"] = _company_label(registry, str(row["company_id"])) or names.get(str(row["company_id"]))
    out["bottleneck_name"] = names.get(str(row.get("bottleneck")))
    out["demand_anchor_name"] = names.get(str(row["demand_anchor"])) if row.get("demand_anchor") else None
    out["chain_names"] = [names.get(str(n)) for n in (row.get("chain") or ())]
    out["evidence_label"] = evidence_label.get(str(row.get("evidence")), str(row.get("evidence")))
    # 錨的來處（Phase 6 Step 6.7a）：字彙照抄 `query.bottleneck.ANCHOR_BASIS`；整列沒有錨＝None。
    basis = row.get("anchor_basis")
    out["anchor_basis_label"] = (anchor_basis_label or {}).get(str(basis)) if basis else None
    return out


def _layer_options(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """結構表的瓶頸節點（＝畫面上的「層」篩選選項）：`{id, name, edges}`，依名字字母（沒名字用 ID）。"""
    seen: dict[str, dict[str, Any]] = {}
    for r in rows:
        node = str(r.get("bottleneck"))
        item = seen.setdefault(node, {"id": node, "name": r.get("bottleneck_name"), "edges": 0})
        item["edges"] += 1
    return sorted(seen.values(), key=lambda item: (str(item["name"] or item["id"]).casefold(), item["id"]))


def _table_node_ids(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """結構表各列提到的節點 ID（公司、瓶頸、需求錨、鏈上每一節）——取名字用。"""
    ids: set[str] = set()
    for r in rows:
        ids.update(str(x) for x in (r.get("company_id"), r.get("bottleneck"), r.get("demand_anchor")) if x)
        ids.update(str(x) for x in (r.get("chain") or ()) if x)
    return sorted(ids)


def build_structure_table_artifact(result: Mapping[str, Any], *, registry: Any,
                                   as_of: date | None = None, projection: Any = None,
                                   generated_at: datetime | None = None,
                                   node_names: Mapping[str, str] | None = None) -> dict[str, Any]:
    """`structure_table()` 的結果 → `structure_table` state artifact。**純函式**：不連 DB、不重排。

    所有固定文字（已知限制、表的註記、順序說明、無需求錨的讀法）都從 `query.bottleneck` 取——
    那裡是唯一一份（L16）。
    """
    from query.bottleneck import (
        ANCHOR_BASIS, ANCHOR_COLUMN_NOTE, EVIDENCE_LABEL, NO_ANCHOR_CHAIN_NOTE, NO_ANCHOR_READING, ORDER_NOTE,
        STRUCTURE_TABLE_NOTE, STRUCTURE_TABLE_TITLE, known_limitations,
    )

    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    rows = [_project_table_row(r, registry=registry, evidence_label=EVIDENCE_LABEL, node_names=node_names,
                               anchor_basis_label=ANCHOR_BASIS)
            for r in (result.get("rows") or ())]
    coverage = dict(result["coverage"])
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["structure_table"],
        "kind": "structure_table",
        "title": STRUCTURE_TABLE_TITLE,
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
        "authority": dict(_STRUCTURE_TABLE_AUTHORITY),
        "coverage": coverage,
        "limitations": known_limitations(coverage),
        "rows": rows,
        # 畫面「只看某一層」的選項（2026-09-30）：每個瓶頸節點一項＋幾條邊，**依名字字母**（沒名字用 ID）——
        # 這是選單的排列，不是名次；表的列序不動。前端不排序（`.sort(` 是 app.js 的禁字），所以在這裡排好。
        "layers": _layer_options(rows),
        # INV-3：母體定義是一個 filter，所以 input／accepted／excluded／reasons 跟著 artifact 走。
        # ⚠ 沒有門檻：2026-09-23 之前這裡是 `filter`／`filtered_rows`（substitutability ≥ 4 濾掉了誰）。
        "population": dict(result.get("population") or {}),
        # sub 引文核對的總數（Phase 4 Step 4.4b；每列另有 `assertions_without_sub_language`）。None＝沒核對。
        "sub_language": dict(result["sub_language"]) if result.get("sub_language") else None,
        # ⚠ 診斷，不是列上的欄位：`rows` 一字未動。
        "anchor_gaps": dict(result.get("anchor_gaps") or {}),
        "notes": {
            "order": ORDER_NOTE,
            "table": STRUCTURE_TABLE_NOTE,
            "no_anchor_chain": NO_ANCHOR_CHAIN_NOTE,
            "no_anchor_reading": NO_ANCHOR_READING if any(not r.get("demand_anchor") for r in rows) else None,
            # 「需求錨」那一欄的讀法（Phase 6 Step 6.7a：逐列、退回公司的標「公司層」）。
            "anchor_column": ANCHOR_COLUMN_NOTE,
        },
        "vocab": {
            "evidence_labels": dict(EVIDENCE_LABEL),
            # 列上 `anchor_basis` 的封閉字彙（row／company；整列沒有錨時是 null）。
            "anchor_basis": dict(ANCHOR_BASIS),
            "sole_source_states": {
                "true": "有文件說這條邊是唯一來源（強弱看 evidence：供應商自稱只算弱印證）",
                "false": "有文件說有第二來源",
                "null": "圖上沒有任何文件對這條邊的 sole_source 發言過——**未填不是否**",
            },
        },
        "this_is_not": list(STRUCTURE_TABLE_THIS_IS_NOT),
        "materializer": {
            "version": STRUCTURE_TABLE_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload = redact_private_paths(payload)
    payload["freshness_identity"] = state_freshness_identity(
        kind="structure_table", as_of=payload["as_of"],
        # 認知狀態＝每列的結構／證據欄位；`documents`（多讀一份文件）與 `confidence`
        # 不算——那是注意力指標，變了不代表我們對結構的判斷變了（L12 兩個 digest 分開的理由）。
        # 錨的來處（`anchor_basis`）跟錨一起算：同一個錨從「公司層」變成「這個節點自己接得到」也是認知變了。
        identity={"rows": [[r["company_id"], r["relation"], r["bottleneck"], r["substitutability"],
                            r["sole_source"], r["evidence"], r["qualification_status"],
                            r["demand_anchor"], r.get("anchor_basis")] for r in rows],
                  "canonical_edges": coverage.get("canonical_edges")})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def materialize_structure_table(*, as_of: date | None = None, store: StateArtifactStore | None = None,
                                generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """跑一次 `structure_table()` 並寫下 `structure_table` artifact。**只有這裡會連 Neo4j。**

    與 `python -m query.bottleneck` 走同一條路：同一個 driver 設定、同一個 `fetch_assertions`、
    同一個 registry。差別只在最後一步是寫 artifact 而不是印 markdown。
    """
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    from identity.registry import get_registry
    from query.bottleneck import fetch_assertions, project_assertions_as_of, structure_table
    from query.sub_language import fetch_all_quotes, get_language, sub_language_flags

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
            # 邊與逐字同一個唯讀 transaction，按 assertion id 對（不塞進 fetch_assertions）：sub 引文核對（Phase 4
            # Step 4.4b）與證據等級的逐來源具名核對（Phase 6 Step 6.4）讀同一份逐字。
            raw_rows, quotes = session.execute_read(lambda tx: (fetch_assertions(tx), fetch_all_quotes(tx)))
            projection = None
            rows: Sequence[Mapping[str, Any]] = raw_rows
            if as_of is not None:
                projection = project_assertions_as_of(raw_rows, as_of)
                rows = list(projection.rows)
            registry = get_registry()
            language = get_language()
            flags = sub_language_flags(rows, quotes, language=language)
            result = structure_table(rows, registry, quotes_by_assertion=quotes, sub_language_flags=flags,
                                     sub_language_label=language.label)
            # 節點的人話名字（同一個 session；與 `get_narrative_context` 同一條查詢）——畫面不再只印內部代號。
            node_names = {str(r["id"]): str(r["name"]) for r in session.run(
                "MATCH (n) WHERE n.id IN $ids AND n.name IS NOT NULL RETURN n.id AS id, n.name AS name",
                ids=_table_node_ids(result.get("rows") or ()))}
    finally:
        driver.close()
    payload = build_structure_table_artifact(result, registry=registry, as_of=as_of,
                                             projection=projection, generated_at=generated_at,
                                             node_names=node_names)
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
# state artifact：`graph_walk`（走圖九型問句；照抄 `query.graph_walk.collect()`）
# ---------------------------------------------------------------------------
# ⚠ 2026-09-26（Phase 2 Step 2.6）：取代 `coverage` kind。coverage 的「沒人供應」「建模待補」與重複節點
# 候選成為走圖第 7、8、9 型（沿用 `query/coverage_gaps.py`、`query/duplicate_nodes.py`，不搬不重算）；
# 磁碟上既有的 `coverage.json` 留著當孤兒（同 Phase 0 的 basket.json），從今天起沒有人讀它。

GRAPH_WALK_MATERIALIZER_VERSION = "webapp-materialize-graph-walk/1"

_GRAPH_WALK_AUTHORITY = {
    "function": "query.graph_walk.collect",
    "command": "python -m query.graph_walk",
    "note": "唯一走圖權威。本 artifact 照抄九型的命中／母體與每一筆問句：不重新分類、不排序、不合成跨型別數字。",
    "inputs": {
        "graph": "Neo4j（collapse_assertions ＋ classify_evidence；coverage_gaps.scan；duplicate_nodes.scan）",
        "readings": "alpha.providers.structure_readings.reading_status_rows（與 structure_readings kind 同一份算法）",
        "leads": "engine_b.leads.load（triaged_go／researching）",
    },
}


def _duplicate_side(view: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """重複節點候選的一端。**逐字照抄**，因為那是這一型存在的全部理由（L18）。"""
    if not view:
        return None
    return {"node": view.get("node"), "name": view.get("name"),
            "abstraction_level": view.get("abstraction_level"),
            "degree": view.get("degree"), "quote_count": view.get("quote_count"),
            "quotes": [dict(q) for q in view.get("quotes") or ()]}


def build_graph_walk_artifact(result: Mapping[str, Any], *,
                              generated_at: datetime | None = None) -> dict[str, Any]:
    """`query.graph_walk.collect()` 的結果 → `graph_walk` state artifact。**純函式**：不連 DB、不重新分類。"""
    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    questions = []
    for q in result["questions"]:
        row = dict(q)
        if q["key"] == "duplicate_node":
            row["hits"] = [dict(h, left=_duplicate_side(h.get("left")), right=_duplicate_side(h.get("right")))
                           for h in q["hits"]]
        else:
            row["hits"] = [dict(h) for h in q["hits"]]
        questions.append(row)
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["graph_walk"],
        "kind": "graph_walk",
        "title": result["title"],
        "generated_at": stamp.isoformat(),
        "as_of": None,
        "point_in_time": {"mode": "current", "as_of": None, "excluded": None},
        "authority": dict(_GRAPH_WALK_AUTHORITY),
        # 每型各自一格——**沒有加總**（加起來就是跨型別合成的數字，plan §0 第 7 條）。
        "counts": {q["key"]: {"hit_n": q["hit_n"], "scope_n": q["scope_n"]} for q in questions},
        "questions": questions,
        # 圖上全部節點 id：decompose 選題的「這個錨是不是已經在圖裡」讀它（原本讀 coverage 快照）。
        "graph_nodes": list(result["graph_nodes"]),
        # 層計數器（Phase 4 Step 4.4c；`query.layer_stats`）：ROADMAP Phase 4 ①②③ 與附屬，只印不判。
        # 心跳段 3 與結構表頁首讀這一段（`summary` 是同一行字，不在消費端重組）。沒有＝這份 artifact 沒算。
        "layer_stats": (dict(result["layer_stats"]) if result.get("layer_stats") is not None else None),
        "rules": dict(result["rules"]),
        "this_is_not": list(result["this_is_not"]),
        "materializer": {
            "version": GRAPH_WALK_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload = redact_private_paths(payload)
    layer = payload.get("layer_stats") or {}
    payload["freshness_identity"] = state_freshness_identity(
        kind="graph_walk", as_of=None,
        # 認知狀態＝每一型命中了誰（與母體多大）＋層計數器的主要數字。問句文字改字不算認知變了。
        identity={**{q["key"]: {"hits": sorted(str(h.get("subject")) for h in q["hits"]),
                                "scope_n": q["scope_n"]} for q in questions},
                  "layer_stats": (None if not layer.get("supply") else {
                      "sole_self_reported": layer["supply"]["sole_self_reported_nodes"],
                      "named_by_non_supplier": layer["enumeration"]["named_by_non_supplier_layers"],
                      "stock_unsupported": layer["sub_language"]["stock_unsupported"],
                      "new_unsupported": layer["sub_language"]["new_unsupported"],
                      # ③b 的「重寫」（Phase 5 Step 5.1，#29）：更正走廊沿用原 id 重寫，也算認知變了。
                      "superseded_unsupported": layer["sub_language"].get("superseded_unsupported"),
                      "language": layer.get("language"),
                      # 證據判準（Phase 6 Step 6.4）：哪幾條邊因為哪個理由沒升、違反、對 6.0 基準的升降——標籤變了就是認知變了。
                      "corroboration_withheld": {reason: sorted(f"{i['edge']}｜{i['origin']}" for i in items)
                                                 for reason, items in (layer.get("corroboration_withheld")
                                                                       or {}).items()},
                      "ec_without_naming_quote": layer.get("ec_without_naming_quote"),
                      "evidence_changes": (None if layer.get("evidence_vs_baseline") is None else sorted(
                          f"{c['edge']}｜{c.get('from')}→{c.get('to')}"
                          for part in ("up", "down", "same_rank", "new", "gone")
                          for c in layer["evidence_vs_baseline"][part])),
                      "relay_language": layer.get("relay_language")})})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def materialize_graph_walk(*, store: StateArtifactStore | None = None, as_of: date | None = None,
                           generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """跑一次 `query.graph_walk.collect()` 並寫下 artifact。**只有這裡（與 CLI）會為走圖連 Neo4j。**"""
    from query.graph_walk import collect

    result = collect(today=as_of or date.today(), as_of=as_of)
    payload = build_graph_walk_artifact(result, generated_at=generated_at)
    target = store or StateArtifactStore()
    return target.write(payload), payload


# ---------------------------------------------------------------------------
# state artifact：`watches`（在等什麼；照抄 Event Watch registry ＋ 追源 backlog）
# ---------------------------------------------------------------------------

WATCHES_MATERIALIZER_VERSION = "webapp-materialize-watches/1"

WATCHES_THIS_IS_NOT = (
    "不是提醒系統：這一頁不會通知你，它只讓「還有什麼在等」現形（L14：防呆要自己出現）。",
    "**停滯（stalled）不等於死亡**：具名標的都觸發過一輪、被動層短期不會再醒，但到期日仍會兜底。",
    "「等事件」不代表不用動作：`unwatched`／停滯需要人當場處置（補觸發條件／改主動輪詢／改 terminal）；"
    "`expired` 的追源型由 daily 自動轉終局並計數，需要人決定的（假設型）才進 pq2。",
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
    "expired": "等待已到期——追源型由 daily 轉終局並計數；thesis／讀圖的反證併進複查與重讀、層說明的主張併進換版；只有假設型等才進 pq2 watch_decision",
    "unwatched": "**沒有任何機制在等它**——唯一真正的黑洞，必須當場處置",
}


def _watch_row(watch: Mapping[str, Any]) -> dict[str, Any]:
    from engine_b.event_watch import SEMANTIC_KIND, flag_for_current, is_stalled, watch_detail, wake_target

    row = {
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
    if watch.get("kind") == SEMANTIC_KIND:
        # 語意條件（Phase 1 Step 1.4）：原文逐字、指回來源、預篩標旗（提示，不是判定）與判定——APP 先讀得到。
        row.update({
            "condition": watch.get("condition"), "source_ref": watch.get("source_ref"),
            "check_frequency": watch.get("check_frequency"), "action_48h": watch.get("action_48h"),
            "woken_by": watch.get("woken_by"), "semantic_flag": flag_for_current(watch),
            "judgment": watch.get("judgment"),
        })
    return row


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
        # 反證與確認條件（語意 watch）：在盯的與醒來待檢的——判定只在互動 session（`event_watch judge`）
        "semantic": [row for row in (by_status.get("active") or []) + (by_status.get("fired") or [])
                     if row["kind"] == "semantic_condition"],
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
            "semantic": "反證與確認條件由 thesis／讀圖登記、原文逐字；一手文件提到它的實體就醒來待檢。"
                        "預篩標旗只是提示，**判定只在互動 session**："
                        "`python -m engine_b.event_watch semantic-queue` → `judge`。",
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

POSITIONS_MATERIALIZER_VERSION = "webapp-materialize-positions/3"

POSITIONS_THIS_IS_NOT = (
    "**不是績效報告。** 「shadow 報酬」的錨點是**入圖日**——那天的語意是「這家公司的 claim 進圖了」，"
    "不是「那天該買」。它不含任何進場時點判斷，**不構成選股能力的證據**。",
    # Phase 5 Step 5.2（plan §3）：三條 lane 的錨點語意各不相同，壓成一個數字就是 L12。
    "paper lane 的錨點是**我們寫下判斷那天**，量的是判斷不是進場；live lane 才是買得準不準。三條 lane 分母分開，不得合併讀。",
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
                             generated_at: datetime | None = None,
                             nav_exposure: Mapping[str, Any] | None = None,
                             lanes: Mapping[str, Any] | None = None,
                             theme_cohort: Mapping[str, Any] | None = None,
                             price_budget: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """outcome 腳本的結果 ＋ Decision Store 計數器 → `positions` state artifact。**純函式**。

    v2（Phase 5 Step 5.2）：多 `lanes`（live／paper／history 各自的摘要；live 與 paper 帶逐列）、`theme_cohort`、
    `price_budget`。`rows` 仍是 history lane 的列——舊讀者不壞；history 的列不在 `lanes` 裡複製第二份。
    `lanes=None`＝這次沒算（舊呼叫端），不是「三條 lane 都是空的」。"""
    primary, reference = benchmarks
    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    rows = [_position_row(r, benchmark=primary, reference=reference) for r in results]
    rows.sort(key=lambda r: -(r["absolute_return"] if r["absolute_return"] is not None else -9))
    live = [{**dict(row), "executed_at": _iso(row.get("executed_at"))} for row in live_rows]
    measured_live = sum(1 for row in live if row.get("live_return") is not None)
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["positions"],
        "kind": "positions",
        "title": "追蹤表：判斷寫下之後、真的買了之後怎麼樣",
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
        # NAV 摘要（Phase 1 Step 1.8）：bucket 分布、最大單筆占 NAV——**只呈現**，心跳段 4 讀它。
        # `None` ＝ 這次沒算（舊呼叫端），不是「沒有持股」；讀不到持股時 `status` 照實帶出來。
        "nav_exposure": None if nav_exposure is None else dict(nav_exposure),
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
        # 三條 lane（Phase 5 Step 5.2）：outcome 腳本 `lanes_payload` 的摘要照抄＋live／paper 的逐列。
        "lanes": None if lanes is None else _jsonable_lanes(lanes),
        "theme_cohort": None if theme_cohort is None else _jsonable_lanes(theme_cohort),
        "price_budget": None if price_budget is None else dict(price_budget),
        "notes": {
            "two_anchors": "「live 報酬」以**實際成交價**為錨點，「shadow 報酬」以**入圖日**為錨點。"
                           "兩者語意不同：後者不含任何進場時點判斷，不構成選股能力的證據。",
            "aggregate": "等權重聚合是研究 cohort 等權的量測基準：每檔等權，回答整體有沒有跑贏。"
                         "各檔錨點日不同，這是跨持有期的粗聚合，**不是回測**（跨檔排序已退役，它不再是「排序品質」）。",
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
            # APP 只印 live／paper（2026-10-07 使用者：舊店拿掉）；history 仍在 `lanes` 裡給心跳與 outcome 腳本讀。
            "lanes": "兩條線各算各的分母（Phase 5）：**live**＝trade_log 的 alpha 成交（錨＝成交價，量買得準不準）；"
                     "**paper**＝每檔第一份 v2 敘事寫下那天（錨＝那天收盤，量判斷準不準；列上帶當時與現行的候選狀態、"
                     "首次點名它的 lead）。對主題等權組的超額每列排除本檔，"
                     "缺價的成員列出、不進平均——只印不比、不排序、不設門檻。",
            "legacy_live": "上面 `live` 那一段是**舊店**的 live fill（凍結唯讀）；`lanes.live` 讀的是 trade_log——"
                           "部位真相是 Google Sheet、收據跟著成交事件走（2026-09-16／09-22 定案）。",
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
                               ("eligible_cohorts", "total_cohorts", "live_choices", "live_fills")},
                  # 三條 lane 的成員與量測起始日（價格變動不算認知變化，plan §3）。
                  "lanes": None if lanes is None else {
                      lane: {"tickers": sorted(str(r.get("ticker")) for r in (entry.get("rows") or ())),
                             "n": entry.get("n"), "measurement_start": entry.get("measurement_start")}
                      for lane, entry in payload["lanes"].items()},
                  # 有哪些組（多主題等權組 S1）：多一組或換一組＝認知變化；組員的價格變動不是。
                  "theme_cohort": [entry.get("cohort_id") for entry in (theme_cohort or {}).get("cohorts") or []]})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def _jsonable_lanes(value: Any) -> Any:
    """lane 摘要與逐列裡的 `date` → ISO 字串；只轉型別、不改結構（同 outcome 腳本的 `_jsonable`）。"""
    if isinstance(value, Mapping):
        return {str(k): _jsonable_lanes(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable_lanes(v) for v in value]
    return _iso(value)


def nav_exposure_summary(exposure: Mapping[str, Any]) -> dict[str, Any]:
    """`portfolio.exposure.build_nav_exposure` 的回傳 → 心跳用的摘要（Phase 1 Step 1.8）。**純函式、只呈現**。

    bucket 分布照抄；最大單筆取非現金部位的 `nav_pct` 最大者。讀不到持股時 `status` 與 `blockers` 原樣帶出——
    「持股讀不到」與「什麼都沒持有」是相反的結論（build_nav_exposure 的同一條紀律）。"""
    positions = [p for p in exposure.get("positions") or [] if isinstance(p, Mapping)]
    top = max(positions, key=lambda p: float(p.get("nav_pct") or 0), default=None)
    return {
        "status": str(exposure.get("status") or "unknown"),
        "buckets": {str(k): float(v) for k, v in (exposure.get("buckets") or {}).items()},
        "cash_pct": exposure.get("cash_pct"),
        "positions": len(positions),
        "largest": None if top is None else {"ticker": top.get("ticker"), "nav_pct": top.get("nav_pct"),
                                             "bucket": top.get("bucket")},
        "blockers": list(exposure.get("blockers") or []),
        "failure": exposure.get("failure"),
    }


def _nav_exposure() -> dict[str, Any]:
    """讀持股（Google Sheet，readonly）→ NAV 摘要。讀不到就照實回 status（不丟例外、不猜 0）。"""
    from portfolio.exposure import build_nav_exposure

    try:
        from fetchers.gsheets import fetch_portfolio

        exposure = build_nav_exposure(list(fetch_portfolio(strict_operational=True)))
    except Exception as exc:  # noqa: BLE001 — 持股讀不到不得拖垮整份 positions artifact
        exposure = build_nav_exposure(None, upstream={"status": "unavailable", "failure": type(exc).__name__})
    return nav_exposure_summary(exposure)


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

    collected = outcome.collect()
    results = collected["lanes"]["history"]["rows"]
    unavailable = collected["lanes"]["history"]["unavailable"]
    benchmarks = collected["benchmarks"]
    from decision_lab.bootstrap import open_readonly_store

    store_handle = open_readonly_store()
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
        generated_at=generated_at, nav_exposure=_nav_exposure(),
        lanes=positions_lanes(outcome, collected), theme_cohort=collected["theme_cohort"],
        price_budget=collected["price_budget"])
    target = store or StateArtifactStore()
    return target.write(payload), payload


def positions_lanes(outcome: Any, collected: Mapping[str, Any]) -> dict[str, Any]:
    """三條 lane → artifact 的 `lanes`：摘要照抄 outcome 腳本的 `lanes_payload`（不另算一份）；live／paper 附逐列，
    history 的列就是 artifact 的 `rows`（不複製第二份）。"""
    summaries = outcome.lanes_payload(collected)
    out: dict[str, Any] = {}
    for lane in outcome.LANE_KEYS:
        entry = dict(summaries[lane])
        entry["empty_text"] = outcome.LANE_EMPTY[lane]
        if lane == "history":
            entry["rows_in"] = "rows"
        else:
            entry["rows"] = [dict(row) for row in collected["lanes"][lane]["rows"]]
        if lane == "live":
            live = collected["lanes"]["live"]
            entry.update(beta_events=live.get("beta_events", 0), unmatched_sells=list(live.get("unmatched_sells") or ()),
                         problems=list(live.get("problems") or ()), skipped=list(live.get("skipped") or ()))
        if lane == "paper":
            entry["filter"] = dict(collected["lanes"]["paper"].get("filter") or {})
        out[lane] = entry
    return out


# ⚠ 2026-09-23（Phase 0 Step 0b.3）：`materialize_basket`（V3 籃子頁：ranking × overview × positions 的 join，
# 首選＝filter）隨籃子 filter 退役；kind 已於 0a.2 從封閉字彙移除，這裡是最後一段程式。


# ---------------------------------------------------------------------------
# state artifact：`candidates`（候選狀態板；Phase 3 Step 3.6）
# ---------------------------------------------------------------------------

CANDIDATES_MATERIALIZER_VERSION = "webapp-materialize-candidates/1"

_CANDIDATES_AUTHORITY = {
    "function": "alpha.providers.candidates.load_board",
    "command": "python -m webapp materialize --candidates",
    "note": "宣告來自敘事 ledger（append-only）；已持有來自 Google Sheet（readonly）；前提每天對讀圖、watch registry、"
            "三題稽核區重驗。本 artifact 照抄推導結果：不排序、不加權、不給尺寸。",
}


def build_candidates_artifact(board: Mapping[str, Any], *, generated_at: datetime | None = None) -> dict[str, Any]:
    """`load_board()` 的結果 → `candidates` state artifact。**純函式**。

    字彙取自零 I/O 的 `alpha.candidates`（不經 `alpha.providers`：那會把 Neo4j／Engine C／yfinance 載進來，
    請求路徑測試的「不得載入模型／IO」哨兵在 fixture 階段就被預載瞎掉——2026-09-29 3.6 審查）。"""
    from alpha.candidates import CANDIDATES_THIS_IS_NOT, GROUP_LABELS, SIDE_LABELS

    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["candidates"],
        "kind": "candidates",
        "title": "候選狀態板（可開／缺 X／已定價等回落／不要／已持有）",
        "generated_at": stamp.isoformat(),
        "as_of": None,
        "point_in_time": {"mode": "current", "as_of": None, "excluded": None},
        "authority": dict(_CANDIDATES_AUTHORITY),
        "today": board.get("today"),
        "group_labels": dict(GROUP_LABELS),
        "side_labels": dict(SIDE_LABELS),
        "groups": {k: list(v) for k, v in (board.get("groups") or {}).items()},
        "side_groups": {k: list(v) for k, v in (board.get("side_groups") or {}).items()},
        "counts": dict(board.get("counts") or {}),
        "oldest_stall_days": dict(board.get("oldest_stall_days") or {}),
        "holdings": dict(board.get("holdings") or {}),
        "narrative_rewrite": list(board.get("narrative_rewrite") or ()),
        # 不上板的那幾檔（沒有敘事、也沒有持有）：計數在 counts.no_narrative，這裡列出是誰（2026-09-30）。
        "no_narrative": list(board.get("no_narrative") or ()),
        "ledger": dict(board.get("ledger") or {}),
        "readings": dict(board.get("readings") or {}),
        "rollup": dict(board.get("rollup") or {}),
        "universe": list(board.get("universe") or ()),
        # Phase 7 Step 7.0g-1：資料檢查的取數（closure-gate 讀它印）。**不進 freshness_identity**——資料品質不是認知，
        # 而且匯率每天在動；放進去會讓 Daily 天天以為「認知變了」。
        "data_checks": dict(board.get("data_checks") or {}),
        "this_is_not": list(CANDIDATES_THIS_IS_NOT),
        "materializer": {
            "version": CANDIDATES_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload = redact_private_paths(payload)

    def ids(rows: Sequence[Mapping[str, Any]]) -> list[str]:
        # 每一列的認知狀態：敘事版本、推導結果、前提失效與該重寫的理由、首屏三個字（燈變色就是認知變了）。
        return sorted(json.dumps([r.get("ticker"), r.get("brief_id"), r.get("derived"), list(r.get("preconditions") or ()),
                                  list(r.get("rewrite") or ()), r.get("three_words")], ensure_ascii=False, sort_keys=True)
                      for r in rows)

    roll = payload["rollup"]
    payload["freshness_identity"] = state_freshness_identity(
        kind="candidates", as_of=None,
        # 認知狀態＝每一組有誰（連同上面那幾格）、持股讀得到嗎與誰解析不到、哪些敘事該重寫、ledger 讀得到嗎、
        # 三題與燈的計數。滯留天數每天自己加一，那不算認知變了（對稱面：會變的都要在，不會變的都不在）。
        identity={"groups": {k: ids(v) for k, v in payload["groups"].items()},
                  "side_groups": {k: ids(v) for k, v in payload["side_groups"].items()},
                  "holdings": [payload["holdings"].get("status"), sorted(payload["holdings"].get("unresolved") or ())],
                  "rewrite": sorted(json.dumps(b, ensure_ascii=False, sort_keys=True) for b in payload["narrative_rewrite"]),
                  "no_narrative": ids(payload["no_narrative"]),
                  "ledger": [payload["ledger"].get("present"), payload["ledger"].get("parse_errors")],
                  "rollup": {k: roll.get(k) for k in ("lines", "wipeout", "not_read", "edge")}})
    payload["content_digest"] = canonical_digest(payload)
    return payload


def materialize_candidates(*, tickers: Sequence[str] | None = None, store: StateArtifactStore | None = None,
                           generated_at: datetime | None = None,
                           context: Mapping[str, Any] | None = None) -> tuple[Path, dict[str, Any]]:
    """推導整板並寫下 artifact。**不寫任何 authority**：讀敘事 ledger、讀圖對圖、watch registry、Engine C（三題 ?mode=ro；
    四盞燈與邊緣判定走一般連線）、Sheet（readonly）、邊緣判定的 FX（yfinance，與 `--beta` 同一個 get_fx_snapshot）。
    `tickers`：宇宙；沒給就用 APP 已 materialize 的那幾檔（`ArtifactStore().tickers()`）。"""
    from alpha.providers.candidates import load_board

    # `tickers=None`＝沒指定 → 預設 store 的目錄；**空 list 是「指定了、而且是空的」**，不得悄悄換成預設目錄
    # （`--dir` 指到別的目錄時會讀到真實機器上的清單；3.6 審查）。
    universe = list(tickers) if tickers is not None else ArtifactStore().tickers()
    # `context`：同一輪個股頁用的那一份（`candidate_context(..., board=True)`）；載入失敗的缺席 context 不能拿來組板，
    # 就照舊自己載一次（失敗會原樣拋出，由呼叫端印理由）。
    shared = context if context is not None and not context.get("absence") else None
    # 自己載的那一次也讀同一個 state 目錄的結構表（「是不是新賭注」；Phase 7 Step 7.0e）
    board = load_board(universe, context=shared, structure=None if shared is not None else bet_structure(store))
    _attach_ride_node_names(board)
    # Phase 7 Step 7.0g-1：資料檢查（營收量級）——母體＝本輪全部個股頁，不跟閉環母體走；要換匯，所以只在這裡算
    # （closure-gate 每輪都跑，只讀結果）。失敗只記理由、候選板照寫——它不是候選狀態的前提。
    try:
        from alpha.closure import REVENUE_MAGNITUDE_BAND
        from alpha.providers.data_checks import revenue_magnitude_pairs

        board["data_checks"] = {"revenue_magnitude": {
            "band": list(REVENUE_MAGNITUDE_BAND), "pairs": revenue_magnitude_pairs(sorted({str(t) for t in universe}))}}
    except Exception as exc:  # noqa: BLE001
        board["data_checks"] = {"revenue_magnitude": {"absence": f"{type(exc).__name__}: {str(exc)[:160]}"}}
    payload = build_candidates_artifact(board, generated_at=generated_at)
    target = store or StateArtifactStore()
    written = target.write(payload)
    # Phase 5 Step 5.6：artifact 寫完才記序列（artifact 寫失敗＝這一輪沒有板，不記）。序列寫失敗只印警告——
    # 候選板照樣有（plan §7）；序列漏一天會在「行數＝天數」的驗收上現形，不會安靜地消失。
    try:
        append_candidate_series(payload, path=candidate_series_path(target))
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ 候選狀態序列沒寫進去（{type(exc).__name__}: {str(exc)[:160]}）——候選板 artifact 照寫",
              file=sys.stderr)
    return written, payload


#: 候選狀態每日序列（Phase 5 Step 5.6；plan §7）。預設 state 目錄時寫 `library/private/measurement/`；給了別的
#: state 目錄（測試、`--dir`、`STOCKBOT_APP_STATE_DIR`）就寫在**那個目錄裡**的 `measurement/`——試跑碰不到真實序列。
CANDIDATE_SERIES_NAME = "candidate_state_series.jsonl"
DEFAULT_MEASUREMENT_DIR = Path(__file__).resolve().parents[1] / "library" / "private" / "measurement"


def candidate_series_path(store: StateArtifactStore) -> Path:
    from .store import DEFAULT_STATE_DIR

    directory = Path(store.directory)
    if directory.resolve() == DEFAULT_STATE_DIR.resolve():
        return DEFAULT_MEASUREMENT_DIR / CANDIDATE_SERIES_NAME
    return directory / "measurement" / CANDIDATE_SERIES_NAME


def candidate_series_row(payload: Mapping[str, Any]) -> dict[str, Any]:
    """候選板 artifact → 序列的一行：五組與四個附組的檔數、無敘事數、最老滯留天數。**照抄 artifact 的 `counts`**，
    不另算一份（`held` 在持股讀不到時是 `None`——照抄成 `null`，不是 0）。"""
    from alpha.candidates import GROUPS, SIDE_GROUPS

    counts = payload.get("counts") or {}
    return {
        "date": str(payload.get("today") or date.today().isoformat()),
        "counts": {group: counts.get(group) for group in GROUPS},
        "side": {side: counts.get(side) for side in SIDE_GROUPS},
        "no_narrative": counts.get("no_narrative"),
        "oldest_stall_days": dict(payload.get("oldest_stall_days") or {}),
        "generated_at": payload.get("generated_at"),
    }


def append_candidate_series(payload: Mapping[str, Any], *, path: Path) -> dict[str, Any]:
    """append 一行；同一天重跑只留最後一筆（以 `date` 去重，照 `_persist_aggregate`）。**只寫不讀**——心跳與 APP 不吃它。

    ⚠ 與 `_persist_aggregate` 不同的一點：**壞行原樣保留**、不丟。這份序列今天重抓拿不回昨天的值（L10：拿不回來的只能
    append），壞掉的那一行也是一筆紀錄的殘骸，留著才看得到它壞了。整檔以暫存檔＋`os.replace` 原子改寫。"""
    row = candidate_series_row(payload)
    kept: list[str] = []
    replaced = 0
    bad = 0
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                old = json.loads(line)
            except ValueError:
                bad += 1
                kept.append(line)
                continue
            if isinstance(old, Mapping) and str(old.get("date")) == row["date"]:
                replaced += 1
                continue
            kept.append(line)
    kept.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text("".join(line + "\n" for line in kept), encoding="utf-8")
    os.replace(temp, path)
    return {"path": str(path), "lines": len(kept), "replaced_same_day": replaced, "bad_lines_kept": bad}


def _graph_node_names(ids: Sequence[str]) -> dict[str, str]:
    """圖裡節點的 `name`（與結構表、`get_narrative_context` 同一條查詢）。只在 materialize 用；請求路徑不碰。"""
    if not ids:
        return {}
    from query.structure import _graph_driver

    driver = _graph_driver()
    try:
        with driver.session() as session:
            return {str(r["id"]): str(r["name"]) for r in session.run(
                "MATCH (n) WHERE n.id IN $ids AND n.name IS NOT NULL RETURN n.id AS id, n.name AS name", ids=list(ids))}
    finally:
        driver.close()


def _attach_ride_node_names(board: Mapping[str, Any]) -> None:
    """候選板每一列「押在哪一格」補上節點名（2026-09-30：原本只印 `mat:inp_substrate`）。**fail-soft**：
    圖讀不到就不補——畫面照印 ID；名字只是顯示，不是認知狀態（不進 freshness identity）。"""
    rides = [ride for rows in (*(board.get("groups") or {}).values(), *(board.get("side_groups") or {}).values())
             for row in rows for ride in (row.get("rides") or ())]
    try:
        names = _graph_node_names(sorted({str(ride.get("node")) for ride in rides if ride.get("node")}))
    except Exception:  # noqa: BLE001 — 名字補不上不擋組板
        return
    for ride in rides:
        if names.get(str(ride.get("node"))):
            ride["node_name"] = names[str(ride.get("node"))]


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
    from alpha.providers.structure_readings import known_nodes, reading_status_rows
    from engine_b.event_watch import load_watches
    from query.structure import _load_edges

    target = store or StateArtifactStore()
    # watch 那一側的重讀理由（Phase 1 Step 1.5）：需求側客戶出了新一手文件、讀圖的反證被判觸及——唯讀
    try:
        watches = list(load_watches().get("watches") or ())
    except Exception:  # noqa: BLE001 — registry 讀不到只少了這一側的理由，圖那一側照算
        watches = []
    today = as_of or date.today()
    edges = _load_edges() if known_nodes() else []
    # 算法住 provider（Step 2.6 搬出）：走圖第 4 型用同一份，不各算一次（L16）。
    rows, parse_errors = reading_status_rows(edges, today=today, as_of=as_of, watches=watches)
    payload = build_structure_readings_artifact(rows=rows, parse_errors=parse_errors,
                                                generated_at=generated_at, as_of=as_of,
                                                predictions=_prediction_table(today=today, as_of=as_of,
                                                                              watches=watches))
    return target.write(payload), payload


def materialize_layer_notes(*, pages: Sequence[str], store: StateArtifactStore | None = None,
                            generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """層說明的純文字閱讀頁（個股頁 plan S4b）。**唯讀**：讀 ledger、watch registry、raw 檔頭與抽取檔、圖的邊。

    `pages`：已 materialize 的個股頁（「哪幾頁連過來」只列真的有頁的）。**必填、沒有預設**——給空集合會把每一家都印成
    「還沒有個股頁」，那是一句假話（R1）。圖讀不到只讓「哪幾頁連過來」說讀不到；全文、出處、主張照印——那一半不靠圖。"""
    from alpha.layer_note import EVIDENCE_LABELS, SECTION_LABELS
    from alpha.providers.layer_notes import (
        CLAIM_STATES, DECLARATION_ABSENCES, layer_note_reread_rows, ledger_snapshot, note_citation_refs, note_page_row,
        source_declarations,
    )
    from engine_b import event_watch as ew
    from identity import get_registry

    from .layer_notes import build_layer_notes_artifact, cited_by

    snapshot = ledger_snapshot()
    notes = snapshot["notes"]
    watches = list(ew.load_watches().get("watches") or ())
    reread = {row["node"]: row["reasons"] for row in layer_note_reread_rows(notes, watches, today=ew._today())}
    declarations = source_declarations(ref for note in notes.values() for ref in note_citation_refs(note))
    try:
        from alpha.providers.structure_readings import seats_from_edges
        from query.structure import _load_edges

        edges = _load_edges() if notes else []
        seats: dict[str, list[str]] | None = seats_from_edges(edges)
        graph_nodes: frozenset[str] | None = frozenset({e.src for e in edges} | {e.dst for e in edges})
        graph_absence = None
    except Exception as exc:  # noqa: BLE001 — 圖讀不到只讓「哪幾頁連過來」說讀不到
        seats, graph_nodes = None, None
        graph_absence = {"kind": "upstream_unavailable",
                         "reason": f"這次沒讀到圖（{type(exc).__name__}）——「哪幾頁連過來」整欄未算，不是 0"}
    registry = get_registry()
    wanted = {co for co, nodes in (seats or {}).items() if set(nodes) & set(notes)}
    wanted |= {e for note in notes.values() for claim in note.claims for e in claim.entities}
    companies = {co: {"known": registry.company(co) is not None, "ticker": registry.research_ticker(co),
                      "label": _company_label(registry, co)} for co in sorted(wanted)}
    page_set = frozenset(str(t).upper() for t in pages)
    rows = []
    loaded_diagrams = _diagrams_loaded()   # 技術示意圖（個股頁 S5b）：同層的閱讀頁也看得到
    for node in sorted(notes):
        row = note_page_row(notes[node], watches=watches, declarations=declarations["by_ref"],
                            reread=reread.get(node, ()), versions=snapshot["versions"].get(node, 1))
        row["cited_by"] = cited_by(node, row["unit"], seats=seats, graph_nodes=graph_nodes, companies=companies,
                                   pages=page_set)
        row["diagrams"] = diagrams_for_nodes(loaded_diagrams, [node])
        rows.append(row)
    payload = build_layer_notes_artifact(
        rows=redact_private_paths(rows), parse_errors=redact_private_paths(snapshot["errors"]),
        withdrawn=snapshot["withdrawn"], declaration_problems=redact_private_paths(declarations["unreadable"]),
        graph_absence=graph_absence,
        company_labels={co: info["label"] for co, info in companies.items() if info["label"]},
        diagram_rejections=(loaded_diagrams or {}).get("rejected") or (),
        labels={"sections": SECTION_LABELS, "evidence": EVIDENCE_LABELS, "claim_states": CLAIM_STATES,
                "declaration_absences": DECLARATION_ABSENCES},
        generated_at=generated_at)
    target = store or StateArtifactStore()
    return target.write(payload), payload


def materialize_daily(*, store: StateArtifactStore | None = None, day: date | None = None,
                      heartbeat_dir: Path | None = None,
                      generated_at: datetime | None = None) -> tuple[Path, dict[str, Any]]:
    """「每日」頁（2026-10-07 使用者指示）：照抄 daily ⑱ 寫下的短版、當天的每日摘要與雷達收據的計數。**唯讀**。
    完整心跳五段不進這一頁（同日使用者：「不需要給我看的…拿掉」；細節照樣在 heartbeat 目錄給互動 session 查）。"""
    from engine_b.digest import load_digest

    from .daily import build_daily_artifact

    folder = heartbeat_dir or (Path(__file__).resolve().parents[1] / "library" / "private" / "heartbeat")
    day = day or datetime.now().astimezone().date()

    def text(name: str) -> str | None:
        path = folder / name
        try:
            return path.read_text(encoding="utf-8") if path.is_file() else None
        except OSError:
            return None

    receipt_text = text(f"radar_{day.isoformat()}.json")
    try:
        radar_summary = (json.loads(receipt_text) or {}).get("summary") if receipt_text else None
    except ValueError:
        radar_summary = None
    # private 路徑在組 artifact **之前**遮（digest 算的是遮過的內容；遮在後面會讓讀取端的 digest 對不上）
    brief_md = text(f"brief_{day.isoformat()}.md")
    payload = build_daily_artifact(day=day, brief_md=redact_private_paths(brief_md) if brief_md else None,
                                   digest=load_digest(day, out_dir=folder), radar_summary=radar_summary,
                                   generated_at=generated_at)
    target = store or StateArtifactStore()
    return target.write(payload), payload


def _prediction_table(*, today: date, as_of: date | None, watches: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """圖預測對錯表（Phase 5 Step 5.4）：讀圖 ledger 全部紀錄＋語意 watch＋兩張日期對照表 → `prediction_rows`。

    - as-of 視角：明確拒絕（`point_in_time_unavailable`）——ledger 與 watch 都是「現在」的，拿現在冒充 T 會是前視（INV-6）。
    - 某個節點的 ledger 有壞行：那個節點**整個不進表**、列進 `unreadable_nodes`——壞的那行可能正是後繼，照算會把錯印成現行。
    - SourceDoc 日期：同一次 materialize 以唯讀 Cypher 取全部 `published_at`；讀不到＝`None`，錯的種類整段
      `upstream_unavailable`、終局照算。lead registry 讀不到同理（判觸及那一種）。"""
    from alpha.providers.structure_readings import known_nodes, read_reading_records
    from alpha.structure_reading.predictions import prediction_rows

    if as_of is not None:
        return {"absence": {"kind": "point_in_time_unavailable",
                            "reason": "預測表只有現在的視角：ledger 與 watch 判定都是現在的狀態，as-of 會是前視"}}
    records: dict[str, list[Any]] = {}
    unreadable: list[dict[str, Any]] = []
    for node in known_nodes():
        recs, errors = read_reading_records(node)
        if errors:
            unreadable.append({"node": node, "bad_lines": len(errors)})
        else:
            records[node] = list(recs)
    try:
        source_published: dict[str, Any] | None = _source_doc_published()
    except Exception:  # noqa: BLE001 — 讀不到圖：錯的種類缺席，終局照算
        source_published = None
    try:
        from engine_b import leads as leads_mod

        lead_published: dict[str, Any] | None = {
            str(lid): (lead or {}).get("published_at") for lid, lead in (leads_mod.load().get("leads") or {}).items()}
    except Exception:  # noqa: BLE001
        lead_published = None
    table = prediction_rows(records, today=today, watches=watches, source_published=source_published,
                            lead_published=lead_published)
    table["unreadable_nodes"] = unreadable
    table["source_dates"] = "available" if source_published is not None else "upstream_unavailable"
    table["lead_dates"] = "available" if lead_published is not None else "upstream_unavailable"
    return table


def _source_doc_published() -> dict[str, Any]:
    """SourceDoc id → `published_at`（唯讀；空就是空，不拿 retrieved_at 冒充——INV-6）。"""
    from neo4j import READ_ACCESS

    from query.structure import _graph_driver

    driver = _graph_driver()
    try:
        with driver.session(default_access_mode=READ_ACCESS) as session:
            return {str(r["id"]): r["published_at"] for r in session.run(
                "MATCH (d:SourceDoc) WHERE d.id IS NOT NULL RETURN d.id AS id, d.published_at AS published_at")}
    finally:
        driver.close()


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
    from alpha.candidates import LIST_GROUP_LABELS, LIST_GROUPS
    from briefing.analyst_view.contracts import (
        ACCOUNTING_BASIS_DISPLAY, CORE_PANELS, OPTIONAL_PANELS, PLAIN_ABSENCE_SHORT,
        PLAIN_BET_UNITS, PLAIN_LINE_LABELS, PLAIN_PANEL_TITLES, PLAIN_PRICED_IN, PLAIN_READINESS, PLAIN_WIPEOUT,
        PRICE_SERIES_NOTE, QUESTIONS,
        WEAK_INPUT_RULES,
    )
    from briefing.analyst_view.page_schema import schema_payload as page_schema_payload

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
        "plain_bet_units": dict(PLAIN_BET_UNITS),
        # 「已定價嗎」的白話（Phase 7 Step 7.0c）：首屏三個字底下與稽核區那一題的標題旁各印一次，APP 不留第二份
        "plain_priced_in": PLAIN_PRICED_IN,
        # 「會不會死」四盞燈的白話（2026-10-08）：APP 印在四盞燈上面，不留第二份
        "plain_wipeout": PLAIN_WIPEOUT,
        # ⚠ 2026-10-08（個股頁 S5）：首屏五題退役——首屏的段與每塊讀法來源住 `page_schema.first_screen`（下面），只有一份
        "plain_readiness": {k: dict(v) for k, v in PLAIN_READINESS.items()},
        # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：plain_stance／plain_driver_labels／plain_multiple_derivation
        # 三份白話層隨估值鏈退役。
        "price_series_note": PRICE_SERIES_NOTE,
        "questions": dict(QUESTIONS),
        "weak_input_rules": dict(WEAK_INPUT_RULES),
        "core_panels": list(CORE_PANELS),
        "optional_panels": list(OPTIONAL_PANELS),
        # 首頁分組（2026-10-07 使用者指示）：順序與中文只有 `alpha.candidates` 那一份，API 照這個順序分段（L16）
        "list_groups": [{"key": key, "label": LIST_GROUP_LABELS[key]} for key in LIST_GROUPS],
        "readiness_states": {
            "ready": "核心各段都有內容，且沒有被標記需要動作",
            "ready_with_flags": "有內容，但至少一段 stale／review_required／not_applicable",
            "blocked": "至少一段核心缺內容——看 blocker_details 的 absence_kind 才知道該不該去補",
        },
        # 個股頁 schema v1.0 的合約（2026-10-08，個股頁 S2）：十三塊、元素、缺席宣告、證據等級對照——只有
        # `briefing.analyst_view.page_schema` 那一份，稽核區的填得滿表照這裡的塊與元素排（L16）
        "page_schema": page_schema_payload(),
    }
    path = target.directory / ".meta.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


__all__ = ["BETA_MATERIALIZER_VERSION", "BETA_THIS_IS_NOT", "GRAPH_WALK_MATERIALIZER_VERSION",
           "MATERIALIZER_VERSION", "STRUCTURE_TABLE_MATERIALIZER_VERSION",
           "STRUCTURE_TABLE_THIS_IS_NOT", "WATCHES_MATERIALIZER_VERSION", "WATCHES_THIS_IS_NOT",
           "WAKE_STATE_LABELS", "build_beta_artifact", "build_graph_walk_artifact", "build_overview",
           "build_structure_table_artifact", "build_watches_artifact", "materialize", "materialize_beta",
           "materialize_graph_walk", "materialize_many", "materialize_structure_table", "materialize_view",
           "materialize_watches", "POSITIONS_MATERIALIZER_VERSION", "POSITIONS_THIS_IS_NOT",
           "build_positions_artifact", "materialize_positions",
           "build_candidates_artifact", "materialize_candidates",
           "CANDIDATE_SERIES_NAME", "DEFAULT_MEASUREMENT_DIR", "append_candidate_series", "candidate_series_path",
           "candidate_series_row",
           "redact_private_paths", "write_vocabularies",
           "materialize_account_scorecard", "materialize_daily", "materialize_layer_notes"]
