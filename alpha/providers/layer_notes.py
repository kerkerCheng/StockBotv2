"""層說明 ledger 的 I/O、出處核對與 watch 登記（個股頁 plan S4a；2026-10-07）。

純邏輯在 `alpha/layer_note/contracts.py`；本檔照 `alpha/providers/structure_readings.py` 的分工與慣例：
一個節點一個 JSONL、只 append、壞行不靜默丟棄、寫入端核對（不過就整筆拒收並逐條說出原因）。

**唯一的寫入入口是 `write_note`**（R2 C1，同敘事寫入端 R2-a C1）：①寫入端核對 ②在 registry **副本**上預演 watch 登記
（實體不在名冊、到期日已過、條件不到 20 字……任何一條在這裡就拒收）③append ④正式登記並存檔。
預演放在 append 之前：否則 ledger 已有一行、registry 一筆都沒有，同一份重跑又被「已在 ledger 中」擋掉。

**寫入端核對（契約層驗不了、要碰檔案的那幾件）：**
- 出處 `raw:<檔名>` 要在 `library/raw/` 找得到同名檔、`lead:<id>` 要在 lead registry 找得到（L18：標籤要指得回原始證據）。
- `supersedes_id` 要在同節點 ledger 裡；同內容不得重複 append；同一份裡兩條主張條件相同拒收（同一個條件會被叫醒兩次）。
- 密鑰形狀的內容拒收（`shared.redaction`）。

**watch：** 每條主張一筆語意 watch，`source_ref=layer_note:<note_id>#<n>`、帶 `node`；到期＝主張自己的 `expires`，
沒寫就用整份的重讀日（INV-2）。換版或撤回時，同節點其他每一份還在盯的條件收掉、觸及未處置的標 handled、
到期待決的記 `source_superseded`——與讀圖同一條規則（同一個節點同時只有一份現行，舊條件不得掛著變孤兒）。

**該重讀（`layer_note_reread_rows`，R2 C2）：** 逐節點、**不依賴結構讀圖**（轉換型節點永遠沒有讀圖）。理由四種：
整份重讀日到期、主張到期未處置、主張被判觸及未處置、主張沒有 watch 在盯。心跳與 audit 讀這一份。
到期分類（`expiry_class`）走 `reread`：不鑄號，重問＝換版。

⚠ 經 providers 呼叫 `engine_b`：`alpha/` 核心不得 import 它（`tests/test_layer_separation.py`）。
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date
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
            raw = json.loads(text)
            if not isinstance(raw, dict):
                raise ContractViolation("這一行不是 object")
            records.append(parse_layer_note_record(raw))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def all_nodes(*, directory: Path | None = None) -> list[str]:
    """ledger 裡有紀錄的節點（讀每個檔**第一個解析得到 node 的行**；檔名是正規化過的，不能反推）。

    ⚠ 壞行跳過、繼續讀下一行（R2 F4：原本第一行壞掉就整個檔案消失）。"""
    out: set[str] = set()
    for path in sorted((directory or LAYER_NOTE_DIR).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except ValueError:
                continue
            node = raw.get("node") if isinstance(raw, dict) else None
            if node:
                out.add(str(node))
                break
    return sorted(out)


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
    """每個出處指不指得回去：`raw:<檔名>` 在 library/raw 有同名檔、`lead:<id>` 在 lead registry 裡。回問題清單（空＝全過）。"""
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
                problems.append(f"{where}：{ref} 在 library/raw 找不到（出處要先入庫，L18；圖上 SourceDoc id 與檔名可能不同——引用檔名）")
        elif kind == "lead":
            if not lead_exists(ident):
                problems.append(f"{where}：{ref} 不在 lead registry")
    return problems


def _duplicate_conditions(parsed: LayerNote) -> list[str]:
    """同一份裡兩條主張的條件正規化後相同（判準同敘事 4.7d：`engine_b.disproof.normalize`）。"""
    from engine_b.disproof import normalize

    seen: dict[str, int] = {}
    problems = []
    for index, claim in enumerate(parsed.claims, 1):
        key = normalize(claim.condition)
        if key in seen:
            problems.append(f"claims[{index}] 的條件與 claims[{seen[key]}] 相同——同一個條件登記兩次會被叫醒兩次")
        else:
            seen[key] = index
    return problems


def append_note_record(record: Mapping[str, Any], *, directory: Path | None = None,
                       raw_dir: Path | None = None, lead_exists: Any = None) -> Path:
    """append 一筆（已由 `layer_note_record()` 驗證過的）紀錄；只 append，永不改寫既有行。

    ⚠ 只有寫入端核對、**沒有** watch 預演——正式寫入請走 `write_note`（它先預演再呼叫本函式）。"""
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
        problems = verify_citation_refs(record, raw_dir=raw_dir, lead_exists=lead_exists) + _duplicate_conditions(parsed)
        if problems:
            raise ContractViolation("層說明拒收：\n  - " + "\n  - ".join(problems))
    path = ledger_path(parsed.node, directory=directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _apply_note_watches(parsed: LayerNote, data: dict[str, Any], records: Sequence[LayerNote], *,
                        stamp: str) -> dict[str, list[str]]:
    """在 `data`（registry 的記憶體版本）上做登記／收舊；不存檔。預演與正式登記共用這一份（不寫兩套，L16）。"""
    from engine_b import event_watch as ew

    summary: dict[str, list[str]] = {"registered": [], "consumed": []}
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
            if any(w.get("source_ref") == ref and w.get("status") != "consumed" for w in data["watches"]):
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
    return summary


def register_note_watches(record: Mapping[str, Any], *, watches_path: Path | None = None,
                          directory: Path | None = None) -> dict[str, list[str]]:
    """層說明 append 成功後的等待登記（冪等，可重跑；`--register-watches` 用它）。"""
    from datetime import datetime, timezone

    from engine_b import event_watch as ew

    parsed = parse_layer_note_record(record)
    data = ew.load_watches(watches_path)
    records, _errors = read_note_records(parsed.node, directory=directory)
    summary = _apply_note_watches(parsed, data, records, stamp=datetime.now(timezone.utc).isoformat())
    ew.save_watches(data, watches_path)
    return summary


def write_note(record: Mapping[str, Any], *, watches_path: Path | None = None, directory: Path | None = None,
               raw_dir: Path | None = None, lead_exists: Any = None) -> dict[str, Any]:
    """**唯一的寫入入口**（R2 C1）：預演 → append → 正式登記 → 存 registry。預演失敗整筆拒收、ledger 不動。"""
    from datetime import datetime, timezone

    from engine_b import event_watch as ew

    parsed = parse_layer_note_record(record)
    data = ew.load_watches(watches_path)
    records, _errors = read_note_records(parsed.node, directory=directory)
    stamp = datetime.now(timezone.utc).isoformat()
    try:
        _apply_note_watches(parsed, copy.deepcopy(data), records, stamp=stamp)
    except ew.EventWatchError as exc:
        raise ContractViolation(f"層說明拒收（watch 登記預演失敗，ledger 未動）：{exc}") from None
    path = append_note_record(record, directory=directory, raw_dir=raw_dir, lead_exists=lead_exists)
    records, _errors = read_note_records(parsed.node, directory=directory)
    summary = _apply_note_watches(parsed, data, records, stamp=stamp)
    ew.save_watches(data, watches_path)
    return {"path": str(path), "note_id": parsed.note_id, **summary}


def claim_watch_rows(note: LayerNote, watches: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """每條主張配它的 watch 狀態（閱讀頁與個股頁入口用；沒登記的印「未盯」，不得安靜消失）。"""
    by_ref: dict[str, Mapping[str, Any]] = {}
    for w in watches:
        ref = str(w.get("source_ref") or "")
        if ref and (ref not in by_ref or by_ref[ref].get("status") == "consumed"):
            by_ref[ref] = w
    rows = []
    for index, claim in enumerate(note.claims, 1):
        ref = f"{SOURCE_PREFIX}{note.note_id}#{index}"
        watch = by_ref.get(ref) or {}
        rows.append({"n": index, "claim": claim.claim, "condition": claim.condition, "evidence": claim.evidence,
                     "watch_id": watch.get("watch_id"), "status": watch.get("status") or "未盯",
                     "expires": watch.get("expires")})
    return rows


def layer_note_reread_rows(notes: Mapping[str, LayerNote], watches: Sequence[Mapping[str, Any]], *,
                           today: date) -> list[dict[str, Any]]:
    """逐節點的「該重讀」（R2 C2：不依賴結構讀圖；R2 F6：整份重讀日也有消費端）。只回有理由的節點，依節點 id 排。"""
    from engine_b import event_watch as ew

    rows = []
    for node in sorted(notes):
        note = notes[node]
        reasons: list[str] = []
        if note.expires is not None and note.expires < today:
            reasons.append(f"整份重讀日 {note.expires.isoformat()} 已過：{note.reread_reason}")
        for row in claim_watch_rows(note, watches):
            label = ew.condition_label(row["condition"])
            watch = next((w for w in watches if w.get("watch_id") == row["watch_id"]), {}) if row["watch_id"] else {}
            judgment = watch.get("judgment") or {}
            if row["status"] == "未盯" or row["status"] == "consumed":
                reasons.append(f"主張 {row['n']} 沒有 watch 在盯（`--register-watches` 補登）：{label}")
            elif judgment.get("touches") == "yes" and not judgment.get("handled"):
                reasons.append(f"層說明主張被判觸及：{label}")
            elif watch.get("status") == "expired" and not watch.get("expiry_resolution"):
                reasons.append(f"層說明主張等滿一輪都沒發生：{label}（換版時換新一批）")
        if reasons:
            rows.append({"node": node, "note_id": note.note_id, "title": note.title, "reasons": reasons})
    return rows


__all__ = [
    "LAYER_NOTE_DIR", "SOURCE_PREFIX", "all_nodes", "append_note_record", "claim_watch_rows", "current_notes",
    "layer_note_reread_rows", "ledger_path", "read_note_records", "register_note_watches", "verify_citation_refs",
    "write_note",
]
