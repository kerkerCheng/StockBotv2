"""SourceDoc 的 `section`／`title`／`origin_entity` 跟抽取 JSON 一不一致——常駐計數器的唯一算法（Phase 4 Step 4.2e；
`origin_entity` 2026-10-03 Phase 6 Step 6.3d 加入）。

## 為什麼需要它

抽取 JSON 是圖的可重建輸入（L10）：圖上任何一個值若不在 JSON 裡，下一次重載或全量重建就會靜默改變它。
2026-10-01 實測兩種：① `section` 只存在圖上（10 份——當初用遷移工具直接改圖，JSON 沒跟上），重建時合法拆段的
條件消失、`check_duplicate_url` 會擋下重載；② addendum 檔的 `source_doc.title` 與母文件不同，誰最後載入誰的
title 就蓋上圖（19 個 doc_id 的 JSON 標題互異、11 份圖上掛的是 addendum 標題）。

## 兩個方向分開報（L12：一個「不一致」承載兩種語意，下游二選一而兩邊都錯）

- **danger**（紅）：重建會**遺失或不確定**的——圖上有值、JSON 沒有；或同一個 doc_id 的多份 JSON 彼此互異
  （載入順序決定結果）。
- **stale**（黃）：圖**落後** JSON——JSON 是對的、圖還沒重載；重載就會對齊。

純函式＋讀本機 `extractions/*.json`；不連圖（圖上的值由呼叫端給）。`query/health_audit.py` 與 `audit/checks.py` 共用。
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parent.parent
#: 要求圖與抽取 JSON 一致的 SourceDoc 欄位。`origin_entity`（Phase 6 Step 6.3d）：它決定證據等級（`classify_evidence`
#: 讀的就是它），同一個 doc_id 的兩份抽取檔若寫法互異，重建時誰最後載入誰贏——2026-10-03 實測 1 份
#: （`iqe_tower_inp_epiwafer_agreement_2026_06_15`）。
FIELDS: tuple[str, ...] = ("section", "title", "origin_entity")
#: 圖那一側的唯一一條查詢（audit、健康審查、遷移工具共用——欄位跟著 FIELDS 走，不各寫一份；L16）。
GRAPH_CYPHER = "MATCH (sd:SourceDoc) RETURN sd.id AS id, " + ", ".join(f"sd.{f} AS {f}" for f in FIELDS)


def _norm(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def json_source_docs(extraction_dir: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """`doc_id → [{file, <FIELDS>…}]`（同一個 doc_id 可能有 base＋addendum 多份檔案）。讀不了的檔案跳過並記錄。"""
    directory = Path(extraction_dir) if extraction_dir else ROOT / "extractions"
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(directory.glob("*.json")):
        try:
            source_doc = json.loads(path.read_text(encoding="utf-8")).get("source_doc") or {}
        except (OSError, json.JSONDecodeError):
            out["__unreadable__"].append({"file": path.name, **{f: None for f in FIELDS}})
            continue
        doc_id = source_doc.get("doc_id")
        if doc_id:
            out[str(doc_id)].append({"file": path.name, **{f: _norm(source_doc.get(f)) for f in FIELDS}})
    return dict(out)


def drift(graph_rows: Iterable[Mapping[str, Any]], json_docs: Mapping[str, list[Mapping[str, Any]]]) -> dict[str, Any]:
    """逐份比對。回 `{danger: [...], stale: [...], graph_without_json: [...], counts: {...}}`，每筆帶 doc_id、欄位、兩邊的值。"""
    danger: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    without_json: list[str] = []
    for row in sorted(graph_rows, key=lambda r: str(r.get("id"))):
        doc_id = str(row.get("id"))
        files = list(json_docs.get(doc_id) or [])
        if not files:
            without_json.append(doc_id)
            continue
        for field in FIELDS:
            values = {f[field] for f in files}
            graph_value = _norm(row.get(field))
            if len(values) > 1:
                danger.append({"doc_id": doc_id, "field": field, "kind": "json_files_disagree",
                               "graph": graph_value, "json": {f["file"]: f[field] for f in files}})
                continue
            json_value = next(iter(values))
            if graph_value == json_value:
                continue
            if graph_value is not None and json_value is None:
                danger.append({"doc_id": doc_id, "field": field, "kind": "graph_only",
                               "graph": graph_value, "json": None})
            else:
                stale.append({"doc_id": doc_id, "field": field, "kind": "graph_behind_json",
                              "graph": graph_value, "json": json_value})
    # 讀不了的抽取檔（`json_source_docs` 收在 `__unreadable__`）：重載時它整份載不進去——也是重建會遺失，必須計數（R2-a N7、INV-3）。
    unreadable = sorted(str(f.get("file")) for f in json_docs.get("__unreadable__") or [])
    counts = {"danger": len(danger), "stale": len(stale), "graph_without_json": len(without_json),
              "unreadable_json": len(unreadable)}
    for name, items in (("danger", danger), ("stale", stale)):
        for field in FIELDS:
            counts[f"{name}_{field}"] = sum(1 for item in items if item["field"] == field)
    return {"danger": danger, "stale": stale, "graph_without_json": sorted(without_json),
            "unreadable_json": unreadable, "counts": counts}


def is_red(result: Mapping[str, Any]) -> bool:
    """紅燈（健康審查 🔴、audit FAIL）的唯一判準：重建會遺失或不確定。

    三種都算（R2-a N7；L10「重新取一次拿不回來」）：欄位只在圖上或多份 JSON 互異（`danger`）、圖上有但**沒有任何**
    抽取檔（最徹底的遺失：整份文件重建不回來）、抽取檔讀不了（重載時整份載不進去）。圖落後 JSON 不算（重載即對齊）。
    """
    return bool(result.get("danger") or result.get("graph_without_json") or result.get("unreadable_json"))


def summary_line(result: Mapping[str, Any]) -> str:
    c = result["counts"]

    def split(kind: str) -> str:
        return "／".join(f"{_LABELS.get(f, f)} {c.get(f'{kind}_{f}', 0)}" for f in FIELDS)

    return (f"SourceDoc 與抽取 JSON：重建會遺失或不確定 {c['danger']}（{split('danger')}）｜圖落後 JSON {c['stale']}"
            f"（{split('stale')}）｜圖上有、沒有任何抽取檔 {c['graph_without_json']}｜讀不了的抽取檔 {c.get('unreadable_json', 0)}")


_LABELS = {"section": "section", "title": "title", "origin_entity": "origin"}

__all__ = ["FIELDS", "GRAPH_CYPHER", "drift", "is_red", "json_source_docs", "summary_line"]
