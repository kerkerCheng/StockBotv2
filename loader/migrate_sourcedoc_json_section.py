"""一次性：SourceDoc 的 `section`／`title` 寫回抽取 JSON（Phase 4 Step 4.2e；plan §0.4 A4）。

## 為什麼

抽取 JSON 是圖的可重建輸入（L10）。2026-10-01 實測：10 份 SourceDoc 的 `section` 只存在圖上（當初用遷移工具直接
改圖，JSON 沒跟上）、1 份兩個抽取檔的 section 互異；21 個多檔 doc_id 裡 19 個的 addendum 檔 `title` 與母文件不同，
誰最後載入誰的 title 就蓋上圖。修法是**讓輸入對齊**，不是在 loader 加 coalesce（coalesce 只救增量重載，全量重建時
只存在圖上的值仍會消失）。判讀一致性的唯一算法是 `loader/sourcedoc_sync.py`。

## 四個模式

    python loader/migrate_sourcedoc_json_section.py                 # dry-run：只印計畫（圖 READ、讀 extractions）
    python loader/migrate_sourcedoc_json_section.py --apply-json    # 寫回抽取 JSON
    python loader/migrate_sourcedoc_json_section.py --apply-graph --pq2 N   # 圖落後 JSON 的值對齊 JSON
    python loader/migrate_sourcedoc_json_section.py --corrections <manifest> [--apply --pq2 N]   # 逐份宣告的更正（JSON 與圖同一次）

同步欄位只有一份：`loader.sourcedoc_sync.FIELDS`（2026-10-03 Phase 6 Step 6.3d 加 `origin_entity`——它決定證據等級）。
- `origin_entity` 的對齊規則：同一個 doc_id 的多份 JSON 互異時對齊**圖上現值**（只在圖上的值正好是其中一份的寫法時；否則不猜）。
- `--corrections`：manifest（`kind: sourcedoc_corrections`、`pq2_ref`、每筆 doc_id／field／before／after／why）宣告「這份文件的這一欄
  其實是什麼」；dry-run 印計畫與**證據等級會變的邊**；`--apply --pq2 N`（編號的 ref_id 要逐字等於 `pq2_ref`）先核對每份抽取檔與
  圖上現值都等於 `before`，再改 JSON（綁收據的先歸檔）、圖上 compare-and-set，最後重跑一致性核對。

- `--apply-json`：只動 `source_doc.section`／`source_doc.title` 兩欄；**文字層級只換那一個值或插一行**（各檔排版
  不同，整份重寫會產生無關 diff），改完解析驗證「結果＝原內容只改這兩欄」。綁了 graph completion 收據的
  `extractions/<doc_id>.json` 先把改動前的版本歸檔成 `extractions/superseded/<doc_id>.<舊指紋8碼>.json`
  ——更正走廊的規矩（`intake/provenance.py`）：日後更正這份文件時，收據指的舊版必須找得到。**不改寫收據**
  （它如實記著當初載入的是哪一版）。manifest 寫進 `loader/manifests/`（before／after、指紋）。
- `--apply-graph`：**寫 Neo4j**，只在使用者對 pq2 [N] 明確 go 之後跑（plan 不可越線 1：本 Phase 的圖寫入要經人工
  核准）；只動「圖落後 JSON」的那幾筆的 section／title，「重建會遺失」的那一類一筆都不碰；先寫 manifest、取
  writer lock。

title 的母文件判準：檔名＝doc_id 的那份；沒有的話，唯一一個沒有 addendum 字樣的標題；判不出來就跳過並列出（不猜）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loader.sourcedoc_sync import FIELDS as SYNC_FIELDS  # noqa: E402  欄位清單只有一份

ADDENDUM =re.compile(r"addendum|——.*(第 \d+ 輪|授權研究)", re.IGNORECASE)
_STRING = r'"(?:[^"\\]|\\.)*"'


# ---------------------------------------------------------------------------
# 計畫（純函式）
# ---------------------------------------------------------------------------

def base_title(doc_id: str, files: list[Mapping[str, Any]]) -> str | None:
    named = [f["title"] for f in files if str(f["file"]).casefold() == f"{doc_id}.json".casefold()]
    if named:
        return named[0]
    clean = sorted({f["title"] for f in files if f.get("title") and not ADDENDUM.search(str(f["file"]))
                    and not ADDENDUM.search(str(f["title"]))})
    return clean[0] if len(clean) == 1 else None


def plan_json_edits(graph_rows: list[Mapping[str, Any]], json_docs: Mapping[str, list[Mapping[str, Any]]]) -> dict:
    """`{edits: [{file, doc_id, field, before, after}], skipped: [...]}`——讓 JSON 對齊（section 以圖為準、title 以母文件為準）。"""
    graph = {str(r["id"]): r for r in graph_rows}
    edits: list[dict] = []
    skipped: list[str] = []
    for doc_id, files in sorted(json_docs.items()):
        if doc_id.startswith("__"):
            continue
        row = graph.get(doc_id) or {}
        graph_section = (str(row.get("section")).strip() or None) if row.get("section") is not None else None
        sections = {f["section"] for f in files}
        if graph_section and sections != {graph_section}:
            edits += [{"file": f["file"], "doc_id": doc_id, "field": "section", "before": f["section"],
                       "after": graph_section} for f in files if f["section"] != graph_section]
        elif not graph_section and len(sections) > 1:
            skipped.append(f"{doc_id}：圖上沒有 section、抽取檔之間互異 {sorted(map(str, sections))}——不猜")
        titles = {f["title"] for f in files}
        if len(titles) > 1:
            target = base_title(doc_id, files)
            if target is None:
                skipped.append(f"{doc_id}：判不出母文件標題（{len(titles)} 個不同標題）——不猜")
            else:
                edits += [{"file": f["file"], "doc_id": doc_id, "field": "title", "before": f["title"],
                           "after": target} for f in files if f["title"] != target]
        # origin_entity（Phase 6 Step 6.3d）：同一個 doc_id 的多份 JSON 互異時，對齊**圖上現值**（它是現在決定證據等級的那個）
        # ——只有圖上的值正好是其中一份 JSON 的寫法才對齊；否則不猜。JSON 一致、圖落後的那種是 --apply-graph 的事。
        origins = {f.get("origin_entity") for f in files}
        if len(origins) > 1:
            graph_origin = (str(row.get("origin_entity")).strip() or None) if row.get("origin_entity") is not None else None
            if graph_origin in origins:
                edits += [{"file": f["file"], "doc_id": doc_id, "field": "origin_entity", "before": f.get("origin_entity"),
                           "after": graph_origin} for f in files if f.get("origin_entity") != graph_origin]
            else:
                skipped.append(f"{doc_id}：抽取檔之間 origin_entity 互異、圖上的值不是其中任何一個——不猜")
    return {"edits": edits, "skipped": skipped}


def _span(raw: str, key: str) -> tuple[int, int]:
    """`"key": {...}` 物件在原文裡的 [起, 迄)（含大括號）；字串裡的大括號不算。"""
    match = re.search(r'"' + re.escape(key) + r'"\s*:\s*\{', raw)
    if not match:
        raise ValueError(f"找不到 {key} 物件")
    start = match.end() - 1
    depth, i, in_string = 0, start, False
    while i < len(raw):
        ch = raw[i]
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    raise ValueError(f"{key} 物件沒有閉合")


def edit_source_doc_text(raw: str, changes: Mapping[str, str]) -> str:
    """只改 `source_doc` 物件裡的那幾個值（文字層級），其餘一個位元組都不動。"""
    start, end = _span(raw, "source_doc")
    block = raw[start:end]
    ascii_style = "\\u" in block
    for field, value in changes.items():
        literal = json.dumps(value, ensure_ascii=ascii_style)
        pattern = re.compile(r'("' + field + r'"\s*:\s*)(null|' + _STRING + r')')
        if pattern.search(block):
            block = pattern.sub(lambda m: m.group(1) + literal, block, count=1)
            continue
        # 沒有這個鍵：照該物件的排版插一行（鍵若排序就插在排序位置，否則插在 doc_id 之後）
        lines = re.findall(r'^([ \t]*)"([^"]+)"\s*:', block, re.MULTILINE)
        keys = [k for _, k in lines]
        doc_id_line = re.search(r'^([ \t]*)"doc_id"(\s*:\s*)' + _STRING + r",?[ \t]*\r?\n", block, re.MULTILINE)
        if not lines or not doc_id_line:
            raise ValueError("source_doc 不是一行一鍵的排版，無法安全插入")
        indent, sep = doc_id_line.group(1), doc_id_line.group(2)
        newline = "\r\n" if "\r\n" in block else "\n"
        new_line = f'{indent}"{field}"{sep}{literal},{newline}'
        if keys == sorted(keys):
            after = next((k for k in keys if k > field), None)
            anchor = re.search(r'^[ \t]*"' + re.escape(after) + r'"\s*:', block, re.MULTILINE) if after else None
            if anchor is None:
                raise ValueError("排序的 source_doc 找不到插入點")
            block = block[:anchor.start()] + new_line + block[anchor.start():]
        else:
            block = block[:doc_id_line.end()] + new_line + block[doc_id_line.end():]
    return raw[:start] + block + raw[end:]


# ---------------------------------------------------------------------------
# 執行
# ---------------------------------------------------------------------------

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apply_json(plan: Mapping[str, Any], *, root: Path = ROOT, receipts_dir: Path | None = None,
               now: datetime | None = None, manifest_name: str | None = None,
               plan_label: str = "docs/plans/2026-10-01-001 Step 4.2e") -> dict:
    """`manifest_name`：收據檔名（不給＝`sourcedoc-json-sync-<日期>.json`）——同一天跑兩次不同的對齊時要分開，免得後者蓋掉前者。"""
    from intake.provenance import canonical_extraction_hash

    receipts = {p.stem for p in (receipts_dir or root / "library" / "private" / "intake_state").glob("*.json")}
    by_file: dict[str, dict[str, Any]] = {}
    for edit in plan["edits"]:
        by_file.setdefault(edit["file"], {"doc_id": edit["doc_id"], "changes": {}})["changes"][edit["field"]] = edit["after"]
    results = []
    for name, item in sorted(by_file.items()):
        path = root / "extractions" / name
        raw = path.read_text(encoding="utf-8")
        before = json.loads(raw)
        new_raw = edit_source_doc_text(raw, item["changes"])
        after = json.loads(new_raw)
        expected = json.loads(raw)
        expected["source_doc"].update(item["changes"])
        if after != expected:
            raise RuntimeError(f"{name}：文字編輯的結果不等於「只改 {sorted(item['changes'])}」——中止，沒有寫入")
        old_hash = canonical_extraction_hash(before)
        archive = None
        if name.casefold() == f"{item['doc_id']}.json".casefold() and item["doc_id"] in receipts:
            archive_path = root / "extractions" / "superseded" / f"{item['doc_id']}.{old_hash[:8]}.json"
            if not archive_path.exists():
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                archive_path.write_text(raw, encoding="utf-8", newline="")
            archive = archive_path.relative_to(root).as_posix()
        path.write_text(new_raw, encoding="utf-8", newline="")
        results.append({"file": f"extractions/{name}", "doc_id": item["doc_id"],
                        "changes": {k: {"before": before["source_doc"].get(k), "after": v}
                                    for k, v in item["changes"].items()},
                        "file_sha256": {"before": _sha(raw), "after": _sha(new_raw)},
                        "extraction_sha256": {"before": old_hash, "after": canonical_extraction_hash(after)},
                        "superseded_archive": archive})
    stamp = (now or datetime.now(timezone.utc))
    manifest = {"kind": "sourcedoc_json_sync", "at": stamp.isoformat(), "plan": plan_label,
                "files": results, "skipped": list(plan["skipped"])}
    manifest_path = root / "loader" / "manifests" / (manifest_name or f"sourcedoc-json-sync-{stamp:%Y%m%d}.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"files": len(results), "manifest": manifest_path.relative_to(root).as_posix(),
            "archived": [r["superseded_archive"] for r in results if r["superseded_archive"]]}


#: 只准動 `loader.sourcedoc_sync.FIELDS` 那幾欄，各一條明確的 Cypher（欄位名不從資料來）；寫前比對圖上現值＝計畫時看到的值。
GRAPH_WRITES = {
    field: (f"MATCH (sd:SourceDoc {{id: $doc_id}}) "
            f"WHERE coalesce(sd.{field}, '') = coalesce($expected_before, '') "
            f"SET sd.{field} = $value RETURN sd.{field} AS value")
    for field in SYNC_FIELDS
}


def apply_graph(stale: list[Mapping[str, Any]], *, session, pq2: int, root: Path = ROOT,
                now: datetime | None = None, manifest_name: str | None = None) -> dict:
    """只對齊「圖落後 JSON」那幾筆；寫前比對圖上現值等於計畫時看到的值（被別人改過就跳過、不覆蓋）。"""
    stamp = now or datetime.now(timezone.utc)
    manifest = {"kind": "sourcedoc_graph_sync", "at": stamp.isoformat(), "pq2": int(pq2), "writes": []}
    manifest_path = root / "loader" / "manifests" / (manifest_name or f"sourcedoc-graph-sync-{stamp:%Y%m%d}.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({**manifest, "planned": list(stale)}, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    for item in stale:
        if item["field"] not in GRAPH_WRITES:
            raise ValueError(f"只准動 {'／'.join(SYNC_FIELDS)}：{item['field']}")
        rows = list(session.run(GRAPH_WRITES[item["field"]], doc_id=item["doc_id"],
                                expected_before=item["graph"], value=item["json"]))
        manifest["writes"].append({**dict(item), "written": bool(rows)})
    manifest_path.write_text(json.dumps({**manifest, "planned": list(stale)}, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return {"written": sum(1 for w in manifest["writes"] if w["written"]), "planned": len(stale),
            "manifest": manifest_path.relative_to(root).as_posix()}


#: 本工具掛的 pq2 `manual` 項 ref_id 前綴（2026-10-01 掛的是 `sourcedoc-title-sync:2026-10-01`，[663]）。
GRAPH_SYNC_REF_PREFIX = "sourcedoc-title-sync:"


def check_graph_approval(n: int, *, pool_path: Path | None = None, ref_id: str | None = None) -> dict:
    """寫圖之前的編號核對（R2-a N6）：[n] 存在且未結案、型別 `manual`、ref_id 是本工具掛的那種。

    `ref_id` 給了就要**逐字相等**（`--corrections` 模式：等於 manifest 的 `pq2_ref`）；不給就照舊要求
    `sourcedoc-title-sync:` 前綴（`--apply-graph` 模式）。
    授權載體仍是使用者在對話中的明確 go；這一道只擋「打錯號照樣寫圖、manifest 記錯編號」。不過就 raise ValueError（沒有任何寫入）。
    """
    from engine_b import todo

    pool = todo.load(pool_path or todo.DEFAULT_POOL_PATH)
    try:
        item = todo.get(pool, n)
    except todo.TodoError as exc:
        raise ValueError(f"[{n}] 不存在或已結案——只接受本工具掛的、尚未結案的 pq2 編號") from exc
    actual = str(item.get("ref_id") or "")
    matches = actual == ref_id if ref_id is not None else actual.startswith(GRAPH_SYNC_REF_PREFIX)
    if item.get("type") != "manual" or not matches:
        want = f"＝{ref_id}" if ref_id is not None else f"以 {GRAPH_SYNC_REF_PREFIX} 開頭"
        raise ValueError(f"[{n}] 不是本工具掛的項（type={item.get('type')}、ref_id={actual}；要 manual 且 ref_id {want}）"
                         "——沒有任何寫入")
    return item


# ---------------------------------------------------------------------------
# `--corrections`：逐份宣告的 SourceDoc 欄位更正（Phase 6 Step 6.3d；JSON 與圖同一次改，要 pq2 go）
# ---------------------------------------------------------------------------

def load_corrections(path: Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("kind") != "sourcedoc_corrections" or not str(manifest.get("pq2_ref") or "").strip():
        raise ValueError(f"{path}：kind 必須是 sourcedoc_corrections、要有 pq2_ref")
    for index, item in enumerate(manifest.get("corrections") or (), 1):
        if item.get("field") not in SYNC_FIELDS or not item.get("doc_id") or "before" not in item or "after" not in item:
            raise ValueError(f"{path}：第 {index} 筆缺 doc_id／field（{SYNC_FIELDS}）／before／after")
        if not str(item.get("why") or "").strip():
            raise ValueError(f"{path}：第 {index} 筆沒有寫理由")
    if not manifest.get("corrections"):
        raise ValueError(f"{path}：corrections 是空的")
    return manifest


def plan_corrections(manifest: Mapping[str, Any], json_docs: Mapping[str, list[Mapping[str, Any]]],
                     graph_rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    """每筆更正 → 那個 doc_id 的**每一份**抽取檔都要改（base＋addendum 同一個值，否則 SourceDocSync 紅），圖上那一筆也要改。

    前置（不過就 raise，沒有任何寫入）：每份抽取檔現值＝`before`、圖上現值＝`before`——宣告的就是要取代的那一版。"""
    graph = {str(r.get("id")): r for r in graph_rows}
    edits: list[dict[str, Any]] = []
    graph_items: list[dict[str, Any]] = []
    for item in manifest["corrections"]:
        doc_id, field = str(item["doc_id"]), str(item["field"])
        files = list(json_docs.get(doc_id) or [])
        if not files:
            raise ValueError(f"{doc_id}：沒有任何抽取檔")
        for f in files:
            if f.get(field) != (str(item["before"]).strip() or None):
                raise ValueError(f"{doc_id}：extractions/{f['file']} 的 {field} 是 {f.get(field)!r}，不是宣告的 before {item['before']!r}")
            edits.append({"file": f["file"], "doc_id": doc_id, "field": field, "before": f.get(field), "after": item["after"]})
        row = graph.get(doc_id)
        if row is None:
            raise ValueError(f"{doc_id}：圖上沒有這份 SourceDoc")
        graph_value = (str(row.get(field)).strip() or None) if row.get(field) is not None else None
        if graph_value != (str(item["before"]).strip() or None):
            raise ValueError(f"{doc_id}：圖上的 {field} 是 {graph_value!r}，不是宣告的 before {item['before']!r}")
        graph_items.append({"doc_id": doc_id, "field": field, "kind": "declared_correction",
                            "graph": graph_value, "json": item["after"]})
    return {"edits": edits, "skipped": [], "graph": graph_items}


PUBLISHERS_PATH = ROOT / "config" / "publishers.json"


def plan_publishers_add(manifest: Mapping[str, Any], *, publishers_path: Path | None = None) -> list[dict[str, Any]]:
    """manifest 的 `publishers_add`：要**跟著這次更正一起**登記的發布者。

    為什麼不先登記：發布者登記必須對得上它 `seen_in` 那份文件的 origin（`tests/test_origin_resolution.py::
    test_every_registration_spells_the_origin_of_the_document_it_came_from`，L18）——那份文件的 origin 要等這次更正才變，
    先登記就是一筆指不回原文的登記（2026-10-03 Step 6.3e 先登記、全測試紅了才撤回）。所以核對的是「更正**之後**」的 origin。"""
    from query.bottleneck import _strip_annotation
    from query.origin_resolution import PUBLISHER_KINDS, load_publishers

    entries = [dict(e) for e in manifest.get("publishers_add") or ()]
    existing = load_publishers(publishers_path or PUBLISHERS_PATH)
    after = {str(c["doc_id"]): str(c["after"]) for c in manifest["corrections"] if c["field"] == "origin_entity"}
    for e in entries:
        origin, kind = str(e.get("origin") or "").strip(), e.get("kind")
        if not origin or kind not in PUBLISHER_KINDS or e.get("corroborates") is not PUBLISHER_KINDS[kind]:
            raise ValueError(f"publishers_add：{e} 的 origin／kind／corroborates 不合規（類別決定算不算印證）")
        if existing.get(origin) is not None:
            raise ValueError(f"publishers_add：{origin} 已登記")
        seen_in = str(e.get("seen_in") or "")
        if seen_in not in after or _strip_annotation(after[seen_in]).casefold() != origin.casefold():
            raise ValueError(f"publishers_add：{origin} 的 seen_in={seen_in!r} 不是這次更正後 origin 去註解等於它的那份文件")
    return entries


def insert_publishers(raw: str, entries: list[Mapping[str, Any]]) -> str:
    """publishers.json 一筆一行的排版：每筆插在**同類別的最後一行之後**，其餘逐位不動；插完解析驗證。"""
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split(newline)
    for entry in entries:
        rows = [i for i, line in enumerate(lines) if f'"kind": "{entry["kind"]}"' in line and '"origin":' in line]
        if not rows:
            raise ValueError(f"publishers.json 沒有 {entry['kind']} 類別的列可以對齊排版")
        anchor = rows[-1]
        if not lines[anchor].rstrip().endswith(","):
            lines[anchor] = lines[anchor].rstrip() + ","
            new = "    " + json.dumps(entry, ensure_ascii=False)
        else:
            new = "    " + json.dumps(entry, ensure_ascii=False) + ","
        lines.insert(anchor + 1, new)
    out = newline.join(lines)
    data = json.loads(out)
    added = {e["origin"] for e in entries}
    if not added <= {p["origin"] for p in data["publishers"]}:
        raise ValueError("插入之後解析不到新條目——中止，沒有寫入")
    return out


def publishers_with(entries: list[Mapping[str, Any]], *, publishers_path: Path | None = None):
    """記憶體裡的 publishers（現在的設定＋這次要登記的），走 `load_publishers` 同一套驗證。"""
    import tempfile

    from query.origin_resolution import load_publishers

    raw = (publishers_path or PUBLISHERS_PATH).read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "publishers.json"
        path.write_text(insert_publishers(raw, list(entries)) if entries else raw, encoding="utf-8")
        return load_publishers(path)


def correction_evidence_changes(rows: list[Mapping[str, Any]], manifest: Mapping[str, Any], *,
                                publishers_after: Any = None) -> list[dict[str, Any]]:
    """更正 origin_entity（與跟著登記的發布者）之後，哪些邊的證據等級會變——現在的名冊、現在的規則，前後各算一次。
    `publishers_after`：更正之後的 publishers（含 `publishers_add`）；不給＝與現在相同。"""
    from identity.registry import get_registry
    from query.bottleneck import classify_evidence, collapse_assertions
    from query.origin_resolution import get_publishers

    new_origin = {str(c["doc_id"]): c["after"] for c in manifest["corrections"] if c["field"] == "origin_entity"}
    after_rows = [dict(r, origin=new_origin[str(r.get("source_doc_id"))]) if str(r.get("source_doc_id")) in new_origin
                  else dict(r) for r in rows]
    registry = get_registry()

    def classes(source_rows, pubs):
        return {k: classify_evidence(e.src, e.origins, registry, filing_origins=e.filing_origins,
                                     origin_linkages=e.origin_linkages, publishers=pubs)
                for k, e in collapse_assertions(source_rows).items()}

    before = classes(rows, get_publishers())
    after = classes(after_rows, publishers_after if publishers_after is not None else get_publishers())
    return [{"edge": list(k), "before": before.get(k), "after": after.get(k)}
            for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)]


def _driver():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(ROOT / ".env")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise SystemExit("請設 NEO4J_PASSWORD")
    return GraphDatabase.driver(os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                                auth=(os.environ.get("NEO4J_USER", "neo4j"), password))


def _run_corrections(args, driver) -> int:
    """`--corrections PATH`：dry-run 印計畫與證據等級變動；`--apply --pq2 N` 才寫（JSON 與圖同一次）。"""
    from neo4j import READ_ACCESS, WRITE_ACCESS

    from loader.sourcedoc_sync import GRAPH_CYPHER, drift, json_source_docs, summary_line
    from query.bottleneck import fetch_assertions

    manifest = load_corrections(Path(args.corrections))
    if args.apply:
        check_graph_approval(args.pq2, ref_id=manifest["pq2_ref"])
    with driver.session(default_access_mode=READ_ACCESS) as session:
        rows = [dict(r) for r in session.run(GRAPH_CYPHER)]
        assertions = session.execute_read(lambda tx: fetch_assertions(tx))
    json_docs = json_source_docs(ROOT / "extractions")
    planned = plan_corrections(manifest, json_docs, rows)
    new_publishers = plan_publishers_add(manifest)
    changes = correction_evidence_changes(assertions, manifest, publishers_after=publishers_with(new_publishers))
    for edit in planned["edits"]:
        print(f"- extractions/{edit['file']}｜{edit['doc_id']}.{edit['field']}：{edit['before']!r} → {edit['after']!r}")
    for item in planned["graph"]:
        print(f"- 圖 SourceDoc {item['doc_id']}.{item['field']}：{item['graph']!r} → {item['json']!r}")
    for entry in new_publishers:
        print(f"- config/publishers.json 登記 {entry['origin']}（{entry['kind']}；seen_in={entry['seen_in']}）")
    print(f"- 證據等級會變的邊 {len(changes)} 條：")
    for change in changes:
        print(f"  - {' '.join(change['edge'])}：{change['before']} → {change['after']}")
    if not args.apply:
        print(f"（dry-run：{len(planned['edits'])} 個抽取檔、{len(planned['graph'])} 份 SourceDoc；加 --apply --pq2 N 才寫）")
        return 0
    from engine_b.writer_lock import INTERACTIVE_OWNER, acquire, release

    stamp = datetime.now(timezone.utc)
    acquire(INTERACTIVE_OWNER, ttl_minutes=15, purpose=f"SourceDoc 欄位更正（pq2 [{args.pq2}]）")
    try:
        json_result = apply_json(planned, manifest_name=f"sourcedoc-corrections-{stamp:%Y%m%d}.json-sync.json",
                                 plan_label=str(manifest.get("plan") or ""))
        with driver.session(default_access_mode=WRITE_ACCESS) as session:
            graph_result = apply_graph(planned["graph"], session=session, pq2=args.pq2,
                                       manifest_name=f"sourcedoc-corrections-{stamp:%Y%m%d}.graph-sync.json")
        if new_publishers:      # 同一步登記：origin 更正落地之後，登記才指得回原文
            raw = PUBLISHERS_PATH.read_bytes().decode("utf-8")
            PUBLISHERS_PATH.write_bytes(insert_publishers(raw, new_publishers).encode("utf-8"))
    finally:
        release(INTERACTIVE_OWNER)
    with driver.session(default_access_mode=READ_ACCESS) as session:
        state = drift([dict(r) for r in session.run(GRAPH_CYPHER)], json_source_docs(ROOT / "extractions"))
    print(summary_line(state))
    print(json.dumps({"json": json_result, "graph": graph_result, "evidence_changes": changes},
                     ensure_ascii=False, indent=2))
    left = [s for s in state["stale"] + state["danger"] if s["doc_id"] in {c["doc_id"] for c in manifest["corrections"]}]
    if graph_result["written"] != len(planned["graph"]) or left:
        print(f"✗ 更正沒有全部對齊：寫了 {graph_result['written']}／{len(planned['graph'])}；仍不一致 {left}", file=sys.stderr)
        return 3
    return 0


def main(argv: list[str] | None = None) -> int:
    from loader.sourcedoc_sync import GRAPH_CYPHER, drift, json_source_docs, summary_line

    parser = argparse.ArgumentParser(description="SourceDoc 的 section／title／origin_entity 寫回抽取 JSON；圖落後的部分經 pq2 核准後對齊")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply-json", action="store_true", help="寫回抽取 JSON（只動 source_doc 的同步欄位）")
    mode.add_argument("--apply-graph", action="store_true", help="寫 Neo4j：圖落後 JSON 的值對齊 JSON（要 --pq2）")
    mode.add_argument("--corrections", default=None,
                      help="逐份宣告的欄位更正 manifest（dry-run；加 --apply --pq2 N 才寫 JSON 與圖）")
    parser.add_argument("--apply", action="store_true", help="配 --corrections：寫（要 --pq2）")
    parser.add_argument("--pq2", type=int, default=None, help="--apply-graph／--corrections --apply 必填：使用者明確 go 的 pq2 編號")
    args = parser.parse_args(argv)
    if (args.apply_graph or args.apply) and args.pq2 is None:
        parser.error("寫圖必須帶 --pq2（圖寫入要經使用者核准）")
    if args.apply and not args.corrections:
        parser.error("--apply 只配 --corrections")
    if args.apply_graph:
        try:
            check_graph_approval(args.pq2)
        except ValueError as exc:
            print(f"✗ 拒絕：{exc}", file=sys.stderr)
            return 2

    from neo4j import READ_ACCESS, WRITE_ACCESS

    driver = _driver()
    try:
        if args.corrections:
            try:
                return _run_corrections(args, driver)
            except ValueError as exc:
                print(f"✗ 拒絕：{exc}", file=sys.stderr)
                return 2
        with driver.session(default_access_mode=READ_ACCESS) as session:
            rows = [dict(r) for r in session.run(GRAPH_CYPHER)]
        json_docs = json_source_docs(ROOT / "extractions")
        state = drift(rows, json_docs)
        print(summary_line(state))
        if args.apply_graph:
            if state["danger"]:
                print("✗ 還有「重建會遺失或不確定」的不一致——先 --apply-json，不碰圖", file=sys.stderr)
                return 2
            from engine_b.writer_lock import INTERACTIVE_OWNER, acquire, release  # 只有寫圖才需要

            acquire(INTERACTIVE_OWNER, ttl_minutes=15, purpose=f"SourceDoc section／title 對齊 JSON（pq2 [{args.pq2}]）")
            try:
                with driver.session(default_access_mode=WRITE_ACCESS) as session:
                    result = apply_graph(state["stale"], session=session, pq2=args.pq2)
            finally:
                release(INTERACTIVE_OWNER)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        plan = plan_json_edits(rows, json_docs)
        for edit in plan["edits"]:
            print(f"- extractions/{edit['file']}｜{edit['doc_id']}.{edit['field']}：{edit['before']!r} → {edit['after']!r}")
        for line in plan["skipped"]:
            print(f"- 跳過：{line}")
        if args.apply_json:
            print(json.dumps(apply_json(plan), ensure_ascii=False, indent=2))
        else:
            print(f"（dry-run：{len(plan['edits'])} 處、{len({e['file'] for e in plan['edits']})} 個檔；加 --apply-json 才寫）")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
