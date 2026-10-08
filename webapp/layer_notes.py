"""層說明的 state artifact（個股頁 plan S4b；2026-10-07）：**純文字閱讀頁**——照印 ledger 全文、出處與每條主張的 watch 狀態。

## 它回答什麼

- 每一份現行層說明的三段全文（依 ①②③ 的固定順序），每個出處帶兩種等級、**並列不合併**：層說明自己寫的
  證據等級（看「誰說的」：一手／學理／…）與**文件自宣告**（文件自己帶的等級與開頭的說明，逐字；沒有就印
  「文件沒宣告」）——第三方轉錄的保真度住文件自己的 tier，不在層說明重編一次（L16）；
- 每條主張盯它的 watch 與狀態（判定只有 `alpha.providers.layer_notes.claim_state` 一個，與「該重讀」同一套）；
- **哪幾頁連過來**：由圖推——公司對這個節點有 `supplies_to`／`develops` 邊，與個股頁「坐的層」同一個函式
  （`alpha.providers.structure_readings.seats_from_edges`）。由層說明點名推會是第二個 owner（L16），所以不用。

## 它不做的事

- 不寫 ledger（append-only authority，只有互動 session 的 `python -m alpha layer-note` 寫）；不重新推理。
- 不排序、不打分、不 gate 任何東西：列序是節點 id 的字母序；層說明是研究判斷（A3）。
- 不做版面與示意圖（個股頁 plan S5）。
"""
from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .contracts import STATE_SCHEMA_VERSIONS, canonical_digest, state_freshness_identity

LAYER_NOTES_MATERIALIZER_VERSION = "webapp-materialize-layer-notes/1"

LAYER_NOTES_THIS_IS_NOT: tuple[str, ...] = (
    "不是排序、不是名次：列序是節點 id 的字母序；一層一份、同層每一頁共用。",
    "不 gate 任何東西：層說明是研究判斷（A3）——不濾候選、不排序、不給尺寸；它也不改讀圖面板的狀態與 readiness。",
    "出處旁的「文件自宣告」照抄文件自己帶的等級與開頭的說明，不是本頁重新評等；層說明自己的證據等級看的是誰說的，"
    "兩者並列、不合併。",
    "「哪幾頁連過來」由圖推（公司對這個節點有供貨或開發邊），不由層說明的文字點名推——節點還沒入圖就沒有頁連過來。",
    "本頁不重算、不寫入：每一格都是 materialize 當下 ledger、watch registry 與圖的照抄；寫層說明只在互動 session。",
)

#: 「哪幾頁連過來」的缺席種類（封閉字彙；由產生缺席的這一端宣告，L16）。
CITED_BY_ABSENCES: Mapping[str, str] = {
    "transition": "轉換不是層：公司不坐在轉換上，個股頁不會連過來",
    "node_absent_from_graph": "圖上沒有任何邊碰到這個節點（還沒入圖，或節點 id 不同）——個股頁「坐的層」由圖推，入圖後才連得過來",
    "no_seated_company": "圖上有這個節點，但沒有公司對它有供貨或開發邊",
    "upstream_unavailable": "這次沒讀到圖——不是「沒有頁連過來」",
}

UNIT_LABELS: Mapping[str, str] = {"layer": "層", "transition": "轉換"}

_AUTHORITY = {
    "function": "alpha.providers.layer_notes（ledger 現況、claim_state、source_declarations）＋ engine_b.event_watch（registry）"
                "＋ alpha.providers.structure_readings.seats_from_edges（圖的供貨／開發邊）",
    "command": "python -m webapp materialize --layer-notes",
    "note": "ledger 是 append-only authority，本層唯讀照抄；寫層說明只在互動 session（python -m alpha layer-note）。",
}


def cited_by(node: str, unit: str, *, seats: Mapping[str, Sequence[str]] | None, graph_nodes: frozenset[str] | None,
             companies: Mapping[str, Mapping[str, Any]], pages: frozenset[str]) -> dict[str, Any]:
    """一份層說明被哪幾頁連過來。**純函式**。

    `seats`：`seats_from_edges` 的輸出（`co:*` → 坐的節點）；`None`＝這次沒讀到圖。`graph_nodes`：邊碰到的全部節點。
    `companies`：`co:*` → `{ticker, label, known}`（名冊）；`pages`：已 materialize 的個股頁（大寫 ticker）。
    坐在這一層、卻沒有個股頁的公司另列 `without_page` 並附理由——不得因為沒有頁就安靜消失（INV-3）。"""

    def absent(kind: str) -> dict[str, Any]:
        return {"pages": [], "without_page": [], "absence": {"kind": kind, "reason": CITED_BY_ABSENCES[kind]}}

    if unit == "transition":
        return absent("transition")
    if seats is None or graph_nodes is None:
        return absent("upstream_unavailable")
    if node not in graph_nodes:
        return absent("node_absent_from_graph")
    seated = sorted(co for co, nodes in seats.items() if node in nodes)
    if not seated:
        return absent("no_seated_company")
    linked: list[dict[str, Any]] = []
    without: list[dict[str, Any]] = []
    for company_id in seated:
        info = companies.get(company_id) or {}
        ticker = str(info.get("ticker") or "").upper() or None
        if ticker and ticker in pages:
            linked.append({"ticker": ticker, "company_id": company_id, "label": info.get("label")})
            continue
        if not info.get("known"):
            reason = "名冊解析不到這個 co id（INV-1：不猜）"
        elif ticker is None:
            # null 不只代表私人公司：子公司、合資、代號還沒登記都是 null——名冊不分，這裡不猜是哪一種（L11-5）
            reason = "名冊的研究代號是 null（私人、子公司，或代號還沒登記——這裡不猜是哪一種）"
        else:
            reason = f"有代號 {ticker}，但還沒有個股頁"
        without.append({"company_id": company_id, "label": info.get("label"), "reason": reason})
    return {"pages": sorted(linked, key=lambda r: r["ticker"]), "without_page": without, "absence": None}


def _citations(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    out = [c for section in row.get("sections") or () for c in section.get("citations") or ()]
    out += [c for claim in row.get("claims") or () for c in claim.get("citations") or ()]
    return out


def build_layer_notes_artifact(
    *, rows: Sequence[Mapping[str, Any]], labels: Mapping[str, Mapping[str, str]],
    parse_errors: Sequence[str] = (), withdrawn: Sequence[str] = (), declaration_problems: Sequence[str] = (),
    graph_absence: Mapping[str, Any] | None = None, company_labels: Mapping[str, str] | None = None,
    generated_at: datetime | None = None, diagram_rejections: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """逐節點的閱讀頁列 → state artifact。**純函式**：不讀 ledger、不查圖。

    `labels`：段、證據等級、主張狀態、文件自宣告缺席的中文（由 materialize 從各自的 SSOT 帶進來；本層不造字）。"""
    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    claims = [claim for row in rows for claim in row.get("claims") or ()]
    citations = [c for row in rows for c in _citations(row)]
    declared = [c for c in citations if c.get("declared") is not None]
    pages = sorted({p["ticker"] for row in rows for p in (row.get("cited_by") or {}).get("pages") or ()})
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["layer_notes"],
        "kind": "layer_notes",
        "title": "層說明：一層一份、同層每一頁共用",
        "generated_at": stamp.isoformat(),
        "as_of": None,
        "point_in_time": {"mode": "current", "as_of": None,
                          "note": "只有現在的視角：ledger 的現行那一份、watch 的現在狀態、現在的圖"},
        "authority": dict(_AUTHORITY),
        "counts": {
            "notes": len(rows),
            "units": dict(Counter(str(row.get("unit")) for row in rows)),
            "claims": len(claims),
            "claim_states": dict(Counter(str(c.get("state")) for c in claims)),
            "citations": len(citations),
            # 有出處的那幾個：文件有自宣告／沒有（含 lead、對不到檔）；推一步與「沒有」不在分母裡
            "citations_with_ref": len(declared),
            "citations_declared": sum(1 for c in declared if not (c.get("declared") or {}).get("absence")),
            "pages_linked": len(pages),
            "needs_reread": sum(1 for row in rows if row.get("reread")),
        },
        "pages_linked": pages,
        "rows": [dict(row) for row in rows],
        "withdrawn": list(withdrawn),
        "parse_errors": list(parse_errors),
        "declaration_problems": list(declaration_problems),
        # 技術示意圖檢查沒過的（2026-10-08，個股頁 S5b）：沒嵌進任何一頁，理由逐條列在這裡（INV-3）
        "diagram_rejections": [dict(r) for r in diagram_rejections],
        "graph": {"absence": dict(graph_absence)} if graph_absence else {"absence": None},
        "company_labels": dict(company_labels or {}),
        "labels": {**{k: dict(v) for k, v in labels.items()}, "cited_by_absences": dict(CITED_BY_ABSENCES),
                   "units": dict(UNIT_LABELS)},
        "this_is_not": list(LAYER_NOTES_THIS_IS_NOT),
        "materializer": {
            "version": LAYER_NOTES_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload["freshness_identity"] = state_freshness_identity(
        kind="layer_notes", as_of=None,
        # 認知狀態＝現行是哪幾份、每條主張在哪一格、哪幾頁連過來（或為什麼沒有）、該重讀幾條；
        # 生成時間與文件自宣告的字面不算（那是呈現，不是「我們的判斷該重看了」）。
        identity={"rows": [[row.get("node"), row.get("note_id"), [c.get("state") for c in row.get("claims") or ()],
                            [p["ticker"] for p in (row.get("cited_by") or {}).get("pages") or ()],
                            ((row.get("cited_by") or {}).get("absence") or {}).get("kind"), len(row.get("reread") or ())]
                           for row in rows],
                  "withdrawn": sorted(withdrawn), "parse_errors": len(parse_errors),
                  "graph": (graph_absence or {}).get("kind")})
    payload["content_digest"] = canonical_digest(payload)
    return payload


__all__ = ["CITED_BY_ABSENCES", "LAYER_NOTES_MATERIALIZER_VERSION", "LAYER_NOTES_THIS_IS_NOT", "UNIT_LABELS",
           "build_layer_notes_artifact", "cited_by"]
