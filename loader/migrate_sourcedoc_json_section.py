"""一次性：SourceDoc 的 `section`／`title` 寫回抽取 JSON（Phase 4 Step 4.2e；plan §0.4 A4）。

## 為什麼

抽取 JSON 是圖的可重建輸入（L10）。2026-10-01 實測：10 份 SourceDoc 的 `section` 只存在圖上（當初用遷移工具直接
改圖，JSON 沒跟上）、1 份兩個抽取檔的 section 互異；21 個多檔 doc_id 裡 19 個的 addendum 檔 `title` 與母文件不同，
誰最後載入誰的 title 就蓋上圖。修法是**讓輸入對齊**，不是在 loader 加 coalesce（coalesce 只救增量重載，全量重建時
只存在圖上的值仍會消失）。判讀一致性的唯一算法是 `loader/sourcedoc_sync.py`。

## 三個模式

    python loader/migrate_sourcedoc_json_section.py                 # dry-run：只印計畫（圖 READ、讀 extractions）
    python loader/migrate_sourcedoc_json_section.py --apply-json    # 寫回抽取 JSON
    python loader/migrate_sourcedoc_json_section.py --apply-graph --pq2 N   # 圖落後 JSON 的值對齊 JSON

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
               now: datetime | None = None) -> dict:
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
    manifest = {"kind": "sourcedoc_json_sync", "at": stamp.isoformat(), "plan": "docs/plans/2026-10-01-001 Step 4.2e",
                "files": results, "skipped": list(plan["skipped"])}
    manifest_path = root / "loader" / "manifests" / f"sourcedoc-json-sync-{stamp:%Y%m%d}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"files": len(results), "manifest": manifest_path.relative_to(root).as_posix(),
            "archived": [r["superseded_archive"] for r in results if r["superseded_archive"]]}


#: 只准動這兩欄，各一條明確的 Cypher（欄位名不從資料來）；寫前比對圖上現值＝計畫時看到的值。
GRAPH_WRITES = {
    field: (f"MATCH (sd:SourceDoc {{id: $doc_id}}) "
            f"WHERE coalesce(sd.{field}, '') = coalesce($expected_before, '') "
            f"SET sd.{field} = $value RETURN sd.{field} AS value")
    for field in ("section", "title")
}


def apply_graph(stale: list[Mapping[str, Any]], *, session, pq2: int, root: Path = ROOT,
                now: datetime | None = None) -> dict:
    """只對齊「圖落後 JSON」那幾筆；寫前比對圖上現值等於計畫時看到的值（被別人改過就跳過、不覆蓋）。"""
    stamp = now or datetime.now(timezone.utc)
    manifest = {"kind": "sourcedoc_graph_sync", "at": stamp.isoformat(), "pq2": int(pq2), "writes": []}
    manifest_path = root / "loader" / "manifests" / f"sourcedoc-graph-sync-{stamp:%Y%m%d}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({**manifest, "planned": list(stale)}, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    for item in stale:
        if item["field"] not in GRAPH_WRITES:
            raise ValueError(f"只准動 section／title：{item['field']}")
        rows = list(session.run(GRAPH_WRITES[item["field"]], doc_id=item["doc_id"],
                                expected_before=item["graph"], value=item["json"]))
        manifest["writes"].append({**dict(item), "written": bool(rows)})
    manifest_path.write_text(json.dumps({**manifest, "planned": list(stale)}, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return {"written": sum(1 for w in manifest["writes"] if w["written"]), "planned": len(stale),
            "manifest": manifest_path.relative_to(root).as_posix()}


def _driver():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(ROOT / ".env")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise SystemExit("請設 NEO4J_PASSWORD")
    return GraphDatabase.driver(os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                                auth=(os.environ.get("NEO4J_USER", "neo4j"), password))


def main(argv: list[str] | None = None) -> int:
    from loader.sourcedoc_sync import drift, json_source_docs, summary_line

    parser = argparse.ArgumentParser(description="SourceDoc 的 section／title 寫回抽取 JSON；圖落後的部分經 pq2 核准後對齊")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply-json", action="store_true", help="寫回抽取 JSON（只動 source_doc.section／title）")
    mode.add_argument("--apply-graph", action="store_true", help="寫 Neo4j：圖落後 JSON 的值對齊 JSON（要 --pq2）")
    parser.add_argument("--pq2", type=int, default=None, help="--apply-graph 必填：使用者明確 go 的 pq2 編號")
    args = parser.parse_args(argv)
    if args.apply_graph and args.pq2 is None:
        parser.error("--apply-graph 必須帶 --pq2（圖寫入要經使用者核准）")

    from neo4j import READ_ACCESS, WRITE_ACCESS

    driver = _driver()
    try:
        with driver.session(default_access_mode=READ_ACCESS) as session:
            rows = [dict(r) for r in session.run(
                "MATCH (sd:SourceDoc) RETURN sd.id AS id, sd.section AS section, sd.title AS title")]
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
