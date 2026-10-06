"""層說明 ledger 的 I/O、出處核對與 watch 登記（個股頁 plan S4a；2026-10-07）。

純邏輯在 `alpha/layer_note/contracts.py`；本檔照 `alpha/providers/structure_readings.py` 的分工與慣例：
一個節點一個 JSONL、只 append、壞行不靜默丟棄、寫入端核對（不過就整筆拒收並逐條說出原因）。

**寫入端核對（契約層驗不了、要碰檔案的那幾件）：**
- 出處 `raw:<id>` 要在 `library/raw/` 找得到同名檔、`lead:<id>` 要在 lead registry 找得到（L18：標籤要指得回原始證據）。
- `supersedes_id` 要在同節點 ledger 裡；同內容不得重複 append。
- 密鑰形狀的內容拒收（`shared.redaction`）。

**watch（`register_note_watches`，冪等）：** 每條主張一筆語意 watch，`source_ref=layer_note:<note_id>#<n>`、帶 `node`；
到期＝主張自己的 `expires`，沒寫就用整份的重讀日（INV-2）。換版或撤回時，舊那一份還在盯的條件收掉（consume）——
與讀圖同一條規則：同一個節點同時只有一份現行，舊條件不得掛著變孤兒。到期分類走「重讀」（`expiry_class` 的 `reread`）：
不鑄號，列進該節點的重讀理由，換版時收掉換新。

⚠ 經 providers 呼叫 `engine_b`：`alpha/` 核心不得 import 它（`tests/test_layer_separation.py`）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from alpha.errors import ContractViolation
from alpha.layer_note.contracts import LayerNote, parse_layer_note_record, select_current

_ROOT = Path(__file__).resolve().parents[2]
LAYER_NOTE_DIR = _ROOT / "library" / "private" / "alpha" / "layer_notes"
RAW_DIR = _ROOT / "library" / "raw"
SOURCE_PREFIX = "layer_note:"

#: node id 允許的字元；其餘一律換成 `_`（`tech:x` 直接當檔名在 Windows 會被當成 NTFS 資料流）。
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def _slug(node: str) -> str:
    text = _UNSAFE.sub("_", str(node).strip())
    if not text:
        raise ContractViolation("node 正規化後是空字串——檔名推不出來")
    return text


def ledger_path(node: str, *, directory: Path | None = None) -> Path:
    return (directory or LAYER_NOTE_DIR) / f"{_slug(node)}.jsonl"


def read_note_records(node: str, *, directory: Path | None = None) -> tuple[list[LayerNote], list[str]]:
    """讀一個節點的全部紀錄。壞掉的行**不靜默丟棄**——回在第二個 list 裡（INV-3）。"""
    path = ledger_path(node, directory=directory)
    if not path.is_file():
        return [], []
    records: list[LayerNote] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(parse_layer_note_record(json.loads(text)))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def all_nodes(*, directory: Path | None = None) -> list[str]:
    """ledger 裡有紀錄的節點（讀每個檔第一行的 node；檔名是正規化過的，不能反推）。"""
    out: set[str] = set()
    for path in sorted((directory or LAYER_NOTE_DIR).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.add(str(json.loads(line).get("node") or ""))
                except ValueError:
                    pass
                break
    return sorted(n for n in out if n)


def current_notes(*, directory: Path | None = None) -> dict[str, LayerNote]:
    """每個節點的現行層說明（沒有現行的節點不在裡面）。"""
    out: dict[str, LayerNote] = {}
    for node in all_nodes(directory=directory):
        records, _errors = read_note_records(node, directory=directory)
        note = select_current(records)
        if note is not None:
            out[node] = note
    return out


def _refs(record: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(在哪裡, ref) 的清單：三段＋每條主張的出處。"""
    out: list[tuple[str, str]] = []
    for key, section in (record.get("sections") or {}).items():
        for cite in (section or {}).get("citations") or ():
            if cite.get("ref"):
                out.append((str(key), str(cite["ref"])))
    for index, claim in enumerate(record.get("claims") or (), 1):
        for cite in claim.get("citations") or ():
            if cite.get("ref"):
                out.append((f"claims[{index}]", str(cite["ref"])))
    return out


def verify_citation_refs(record: Mapping[str, Any], *, raw_dir: Path | None = None,
                         lead_exists: Any = None) -> list[str]:
    """每個出處指不指得回去：`raw:<id>` 在 library/raw 有同名檔、`lead:<id>` 在 lead registry 裡。回問題清單（空＝全過）。"""
    raw_dir = raw_dir or RAW_DIR
    if lead_exists is None:
        def lead_exists(lead_id: str) -> bool:
            from engine_b import leads

            return lead_id in (leads.load().get("leads") or {})
    problems: list[str] = []
    for where, ref in _refs(record):
        kind, _, ident = ref.partition(":")
        if kind == "raw":
            if not any(p.stem == ident for p in raw_dir.glob(f"{ident}.*")):
                problems.append(f"{where}：{ref} 在 library/raw 找不到（出處要先入庫，L18）")
        elif kind == "lead":
            if not lead_exists(ident):
                problems.append(f"{where}：{ref} 不在 lead registry")
    return problems


def append_note_record(record: Mapping[str, Any], *, directory: Path | None = None,
                       raw_dir: Path | None = None, lead_exists: Any = None) -> Path:
    """append 一筆（已由 `layer_note_record()` 驗證過的）紀錄；只 append，永不改寫既有行。"""
    from shared.redaction import sensitive_payload_path

    parsed = parse_layer_note_record(record)
    sensitive = sensitive_payload_path(dict(record), "layer_note")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing layer note rejected at {sensitive}")
    existing, _errors = read_note_records(parsed.node, directory=directory)
    if any(r.note_id == parsed.note_id for r in existing):
        raise ContractViolation(f"layer note {parsed.note_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id and not any(r.note_id == parsed.supersedes_id for r in existing):
        raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在 {parsed.node} 的 ledger 中")
    if not parsed.retracted:
        problems = verify_citation_refs(record, raw_dir=raw_dir, lead_exists=lead_exists)
        if problems:
            raise ContractViolation("層說明拒收：\n  - " + "\n  - ".join(problems))
    path = ledger_path(parsed.node, directory=directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def register_note_watches(record: Mapping[str, Any], *, watches_path: Path | None = None,
                          directory: Path | None = None) -> dict[str, list[str]]:
    """層說明 append 成功後的等待登記（冪等，可重跑）。

    1. 同節點其他每一份（換版）或被撤回的那一份：還在盯的語意 watch → consume；到期待決的 → `source_superseded`。
    2. 這一份的 `claims[]` → 每條一筆語意 watch（`source_ref=layer_note:<id>#<n>`、`node`）。已登記的不重登。
    """
    from datetime import datetime, timezone

    from engine_b import event_watch as ew

    parsed = parse_layer_note_record(record)
    stamp = datetime.now(timezone.utc).isoformat()
    data = ew.load_watches(watches_path)
    summary: dict[str, list[str]] = {"registered": [], "consumed": []}
    records, _errors = read_note_records(parsed.node, directory=directory)
    if parsed.retracted:
        stale_ids = {str(parsed.supersedes_id)} if parsed.supersedes_id else set()
    else:
        stale_ids = ({r.note_id for r in records} | ({str(parsed.supersedes_id)} if parsed.supersedes_id else set())) \
            - {parsed.note_id}
    if stale_ids:
        note = "retracted" if parsed.retracted else f"superseded by {parsed.note_id}"
        for watch in data["watches"]:
            ref = str(watch.get("source_ref") or "")
            if (watch.get("kind") != ew.SEMANTIC_KIND or not ref.startswith(SOURCE_PREFIX)
                    or ref[len(SOURCE_PREFIX):].split("#", 1)[0] not in stale_ids):
                continue
            # 判定觸及、還沒處置的舊條件：換版本身就是處置（verb reread）——與讀圖換版同一條（對稱面，L17）
            judgment = watch.get("judgment") or {}
            if judgment.get("touches") == "yes" and not judgment.get("handled"):
                judgment["handled"] = {"verb": "reread", "note_id": parsed.note_id, "at": stamp}
            if watch.get("status") in ("active", "fired"):
                watch["status"] = "consumed"
                watch["closed"] = {"at": stamp, "note": note}
                summary["consumed"].append(watch["watch_id"])
            elif watch.get("status") == "expired" and not watch.get("expiry_resolution"):
                ew.resolve_expiry(data, watch["watch_id"], {"kind": "source_superseded", "note": note})
                summary["consumed"].append(watch["watch_id"])
    if not parsed.retracted:
        for index, claim in enumerate(parsed.claims, 1):
            ref = f"{SOURCE_PREFIX}{parsed.note_id}#{index}"
            if any(w.get("source_ref") == ref for w in data["watches"]):
                continue
            expires = claim.expires or parsed.expires
            watch = ew.add_watch(
                data, kind=ew.SEMANTIC_KIND, disproof_ref=ref, source_ref=ref,
                expires=expires.isoformat() if expires else None, entities=list(claim.entities),
                condition=claim.condition, check_frequency=claim.check_frequency, action_48h=claim.action_48h,
                node=parsed.node, quote_locator="layer note claims[]",
                note=f"層說明 {parsed.note_id}（{parsed.node}）的第 {index} 條主張：{claim.claim[:60]}",
            )
            summary["registered"].append(watch["watch_id"])
    ew.save_watches(data, watches_path)
    return summary


def claim_watch_rows(note: LayerNote, watches: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """每條主張配它的 watch 狀態（閱讀頁與個股頁入口用；沒登記的印「未盯」，不得安靜消失）。"""
    by_ref = {str(w.get("source_ref") or ""): w for w in watches}
    rows = []
    for index, claim in enumerate(note.claims, 1):
        ref = f"{SOURCE_PREFIX}{note.note_id}#{index}"
        watch = by_ref.get(ref) or {}
        rows.append({"n": index, "claim": claim.claim, "condition": claim.condition, "evidence": claim.evidence,
                     "watch_id": watch.get("watch_id"), "status": watch.get("status") or "未盯",
                     "expires": watch.get("expires")})
    return rows


__all__ = [
    "LAYER_NOTE_DIR", "SOURCE_PREFIX", "all_nodes", "append_note_record", "claim_watch_rows", "current_notes",
    "ledger_path", "read_note_records", "register_note_watches", "verify_citation_refs",
]
