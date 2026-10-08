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
到期分類（`expiry_class`）走 `reread`：不鑄號，重問＝換版。主張落哪一格只有一個判定（`claim_state`）——
「該重讀」與閱讀頁（S4b）都問它。

**閱讀頁（個股頁 plan S4b；`note_page_row`）：** 照印全文、出處與每條主張的 watch 狀態；每個出處旁另印**文件自宣告**
（`source_declarations`：文件自己帶的等級與開頭的說明，逐字）。層說明的證據等級看的是「誰說的」，文件自宣告看的是
「這份文件自己說它是什麼」——第三方轉錄的保真度住文件自己的 tier，不在層說明重編一次（L16），兩者並列、不合併。

⚠ 經 providers 呼叫 `engine_b`：`alpha/` 核心不得 import 它（`tests/test_layer_separation.py`）。
"""
from __future__ import annotations

import copy
import glob
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from alpha.errors import AlphaError, ContractViolation
from alpha.layer_note.contracts import (
    EVIDENCE_LABELS, SECTION_KEYS, SECTION_LABELS, Citation, LayerNote, parse_layer_note_record, select_current,
)

_ROOT = Path(__file__).resolve().parents[2]
LAYER_NOTE_DIR = _ROOT / "library" / "private" / "alpha" / "layer_notes"
RAW_DIR = _ROOT / "library" / "raw"
#: 抽取檔（`extract.py --out`）：`source_doc.evidence_tier` 是抽取時替這份文件記下的等級。
EXTRACTION_DIR = _ROOT / "extractions"
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
    if parsed.supersedes_id and not parsed.retracted and existing:
        # 2026-10-08（Phase 7 failure log #56，讀圖那一側的對稱面）：換版只取代最新那一筆（select_current 的規則），
        # 取代更舊的一版會讓取代鏈分岔。
        head = max(existing, key=lambda r: (r.created_at, r.note_id))
        if head.note_id != parsed.supersedes_id:
            raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不是 {parsed.node} 最新的一筆"
                                    f"（最新是 {head.note_id}）——換版只取代現行那一份，否則取代鏈會分岔")
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
    try:
        records, _errors = read_note_records(parsed.node, directory=directory)
        summary = _apply_note_watches(parsed, data, records, stamp=stamp)
        ew.save_watches(data, watches_path)
    except Exception as exc:  # noqa: BLE001 — 紀錄已 append：登記沒跟上要說清楚怎麼補，不得變成 traceback（INV-3；R2 複審）
        raise AlphaError(f"層說明 {parsed.note_id} 已寫入 {path.name}，但 watch 登記失敗（{type(exc).__name__}: {exc}）"
                         f"——修好後跑 `python -m alpha layer-note {parsed.node} --register-watches` 冪等補登") from exc
    return {"path": str(path), "note_id": parsed.note_id, **summary}


#: 一條層說明主張現在在哪一格（封閉字彙；S4b）。**判定只有 `claim_state` 一個**——閱讀頁的狀態與「該重讀」的三種
#: 主張理由（沒人盯／被判觸及／等滿一輪）都問它（L16），不各寫一套。
CLAIM_STATES: Mapping[str, str] = {
    "active": "在盯",
    "fired": "醒來待判（判定只在互動 session）",
    "touched": "被判觸及——該換版",
    "expired": "等滿一輪都沒發生——換版時換新一批",
    "settled": "已處置",
    "unwatched": "沒有 watch 在盯（`--register-watches` 補登）",
}


def claim_state(watch: Mapping[str, Any] | None) -> str:
    """`CLAIM_STATES` 的鍵。沒有 watch 或只剩已收掉的（consumed）＝沒人盯——不得印成「在盯」（INV-3）。"""
    if not watch or watch.get("status") == "consumed":
        return "unwatched"
    judgment = watch.get("judgment") or {}
    if judgment.get("touches") == "yes" and not judgment.get("handled"):
        return "touched"
    status = watch.get("status")
    if status == "expired":
        return "settled" if watch.get("expiry_resolution") else "expired"
    return str(status) if status in ("active", "fired") else "settled"


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
        state = claim_state(watch)
        rows.append({"n": index, "claim": claim.claim, "condition": claim.condition, "evidence": claim.evidence,
                     "watch_id": watch.get("watch_id"), "status": watch.get("status") or "未盯",
                     "expires": watch.get("expires"), "source_ref": ref,
                     "state": state, "state_label": CLAIM_STATES[state]})
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
            if row["state"] == "unwatched":
                reasons.append(f"主張 {row['n']} 沒有 watch 在盯（`--register-watches` 補登）：{label}")
            elif row["state"] == "touched":
                reasons.append(f"層說明主張被判觸及：{label}")
            elif row["state"] == "expired":
                reasons.append(f"層說明主張等滿一輪都沒發生：{label}（換版時換新一批）")
        if reasons:
            rows.append({"node": node, "note_id": note.note_id, "title": note.title, "reasons": reasons})
    return rows


# ---------------------------------------------------------------------------
# 閱讀頁（個股頁 plan S4b；2026-10-07）
# ---------------------------------------------------------------------------

def ledger_snapshot(*, directory: Path | None = None) -> dict[str, Any]:
    """閱讀頁要的整份 ledger 現況：每個節點的現行層說明、紀錄筆數、壞行、已撤回的節點。

    與 `current_notes` 的差別是**壞的不靜默丟**（INV-3）：壞行逐行回報；整個檔一行都讀不出 node 的（`all_nodes`
    找不到它）另列一筆——否則那份層說明會從閱讀頁安靜消失。"""
    root = directory or LAYER_NOTE_DIR
    notes: dict[str, LayerNote] = {}
    versions: dict[str, int] = {}
    errors: list[str] = []
    withdrawn: list[str] = []
    nodes = all_nodes(directory=directory)
    for node in nodes:
        records, errs = read_note_records(node, directory=directory)
        errors.extend(errs)
        versions[node] = len(records)
        current = select_current(records)
        if current is not None:
            notes[node] = current
        elif records:
            withdrawn.append(node)
    known = {ledger_path(node, directory=directory).name for node in nodes}
    for path in sorted(root.glob("*.jsonl")) if root.is_dir() else ():
        if path.name not in known:
            errors.append(f"{path.name}：一行都讀不出 node——整個檔不在閱讀頁")
    return {"notes": notes, "versions": versions, "errors": errors, "withdrawn": withdrawn}


#: 出處旁「文件自宣告」的缺席種類（封閉字彙；S4b）——缺席由產生它的這一端宣告（L16），前端照印。
DECLARATION_ABSENCES: Mapping[str, str] = {
    "not_declared": "文件沒宣告",
    "lead_ref": "文件沒宣告（出處是 lead：文件還沒入庫）",
    "raw_missing": "library/raw 對不到這個檔名（寫入時對得到——之後被搬走或改名）",
}
#: 只看文件開頭這幾行：宣告寫在檔頭（SOURCE／URL／…／NOTE），正文裡的字不算宣告；遇到 `---` 分隔線（檔頭與正文的界線，
#: 例：「--- 逐字 quote ---」）就停。檔頭之後另起一段的 `Note:`（例：改寫過的節錄自己聲明「paraphrased, not verbatim」）照收。
_DECLARATION_HEAD_LINES = 20
#: 檔頭欄位：`KEY:` 或 `KEY：`（可帶 `#`、`⚠` 前綴）。鍵名含 NOTE 或 TIER 的那一段算文件自宣告
#: （例：`NOTE:`、`NOTE ON SCOPE:`、`⚠ EVIDENCE TIER：`）；其他欄位（SOURCE、URL…）結束上一段。
_HEADER_KEY = re.compile(r"^[#⚠\s]*([A-Za-z][A-Za-z _]{0,30}?)\s*[:：]")
_TEXT_SUFFIXES = frozenset({".txt", ".md"})


def _header_declarations(path: Path) -> list[str]:
    """raw 文字檔開頭的宣告段，**逐字**（續行照原樣換行）——不判讀、不從句子裡抽 tier 數字（L16、L18）。"""
    try:
        head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:_DECLARATION_HEAD_LINES]
    except OSError:
        return []
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in head:
        if line.strip().startswith("---"):
            break
        if not line.strip():
            current = None
            continue
        match = _HEADER_KEY.match(line)
        if match:
            key = match.group(1).upper()
            current = [line.strip()] if ("NOTE" in key or "TIER" in key) else None
            if current is not None:
                blocks.append(current)
        elif current is not None:
            current.append(line.strip())
    return ["\n".join(block) for block in blocks]


def _meta_tier(path: Path) -> tuple[Any, str | None]:
    """`<檔名>.meta.json` 的 `evidence_tier`（抓取器寫的）。回 (等級或 None, 讀不懂的理由或 None)。"""
    if not path.is_file():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"{path.name} 讀不懂（{type(exc).__name__}）"
    return (payload.get("evidence_tier") if isinstance(payload, dict) else None), None


def _extraction_tiers(stems: set[str], directory: Path) -> tuple[dict[str, list[tuple[str, Any]]], list[str]]:
    """抽取檔裡 `source_doc.doc_id` **完全等於** raw 檔名的那幾份 → `[(抽取檔名, evidence_tier)]`。

    ⚠ 只認完全相同：同一份文件在圖上／抽取檔／raw 名字不一定一樣（failure log #37），對不上就不算——不猜。
    讀不懂的抽取檔逐檔回報（INV-3：它可能正是帶著等級的那一份）。"""
    found: dict[str, list[tuple[str, Any]]] = {}
    unreadable: list[str] = []
    if not stems or not directory.is_dir():
        return found, unreadable
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            unreadable.append(path.name)
            continue
        doc = payload.get("source_doc") if isinstance(payload, dict) else None
        doc_id = str(doc.get("doc_id") or "") if isinstance(doc, dict) else ""
        if doc_id in stems:
            found.setdefault(doc_id, []).append((path.name, doc.get("evidence_tier")))
    return found, unreadable


def source_declarations(refs: Iterable[str], *, raw_dir: Path | None = None,
                        extraction_dir: Path | None = None) -> dict[str, Any]:
    """每個出處的**文件自宣告**（閱讀頁 S4b）——照抄文件自己帶著的三種東西，一個都不判：

    ①`library/raw/<檔名>.meta.json` 的 `evidence_tier`（抓取器寫的）；②抽取檔 `source_doc.doc_id` 等於檔名的 `evidence_tier`；
    ③raw 文字檔開頭鍵名含 NOTE 或 TIER 的宣告段（逐字）。三種都沒有＝「文件沒宣告」；lead 出處＝文件還沒入庫。

    回 `{"by_ref": {ref: {tiers, lines, absence}}, "unreadable": [讀不懂的抽取檔或 meta]}`。"""
    raw_dir = raw_dir or RAW_DIR
    wanted = sorted({str(r) for r in refs if r})
    stems = {r.split(":", 1)[1] for r in wanted if r.startswith("raw:")}
    extraction, unreadable = _extraction_tiers(stems, extraction_dir or EXTRACTION_DIR)
    by_ref: dict[str, dict[str, Any]] = {}

    def absent(kind: str) -> dict[str, Any]:
        return {"tiers": [], "lines": [], "absence": {"kind": kind, "label": DECLARATION_ABSENCES[kind]}}

    for ref in wanted:
        kind, _, ident = ref.partition(":")
        if kind != "raw":
            by_ref[ref] = absent("lead_ref" if kind == "lead" else "not_declared")
            continue
        files = sorted(p for p in raw_dir.glob(f"{glob.escape(ident)}.*") if p.stem == ident)
        if not files:
            by_ref[ref] = absent("raw_missing")
            continue
        tiers: list[dict[str, Any]] = []
        meta = raw_dir / f"{ident}.meta.json"
        tier, problem = _meta_tier(meta)
        if problem:
            unreadable.append(problem)
        if tier is not None:
            tiers.append({"tier": tier, "from": f"raw 附檔 {meta.name}"})
        tiers.extend({"tier": t, "from": f"抽取檔 {name}"} for name, t in extraction.get(ident, ()) if t is not None)
        lines = [block for path in files if path.suffix.lower() in _TEXT_SUFFIXES for block in _header_declarations(path)]
        by_ref[ref] = {"tiers": tiers, "lines": lines, "absence": None} if (tiers or lines) else absent("not_declared")
    return {"by_ref": by_ref, "unreadable": unreadable}


def note_citation_refs(note: LayerNote) -> list[str]:
    """一份層說明的全部出處（三段＋每條主張；有 ref 的才算）。"""
    cites = [c for key in SECTION_KEYS if key in note.sections for c in note.sections[key].citations]
    cites += [c for claim in note.claims for c in claim.citations]
    return [str(c.ref) for c in cites if c.ref]


def note_page_row(note: LayerNote, *, watches: Sequence[Mapping[str, Any]], declarations: Mapping[str, Any],
                  reread: Sequence[str] = (), versions: int = 1) -> dict[str, Any]:
    """閱讀頁的一列（一個節點的現行層說明）：三段依 `SECTION_KEYS` 的 ①②③ 順序（不看存檔順序）、每個出處帶
    證據等級與文件自宣告、每條主張帶 watch 狀態（`claim_watch_rows`）。**純函式**；不含 `body_ref`（private 路徑不出門）。"""

    def cite(citation: Citation) -> dict[str, Any]:
        out: dict[str, Any] = {"evidence": citation.evidence, "evidence_label": EVIDENCE_LABELS[citation.evidence],
                               "ref": citation.ref, "quote": citation.quote}
        # 沒有出處（推一步／沒有）就沒有文件可問：`declared` 是 None，不是「文件沒宣告」（L12：兩件事）。
        # 有出處卻不在 `declarations` 裡＝呼叫端漏算——直接 KeyError，不退回「文件沒宣告」（那會是一句假話）。
        out["declared"] = declarations[citation.ref] if citation.ref else None
        return out

    watch_rows = {row["n"]: row for row in claim_watch_rows(note, watches)}
    claims = []
    for index, claim in enumerate(note.claims, 1):
        row = watch_rows[index]
        claims.append({
            "n": index, "claim": claim.claim, "condition": claim.condition, "entities": list(claim.entities),
            "check_frequency": claim.check_frequency, "action_48h": claim.action_48h,
            "evidence": claim.evidence, "evidence_label": EVIDENCE_LABELS[claim.evidence],
            "expires": claim.expires.isoformat() if claim.expires else None,
            "citations": [cite(c) for c in claim.citations],
            "source_ref": row["source_ref"], "watch_id": row["watch_id"],
            "watch_status": row["status"] if row["watch_id"] else None, "watch_expires": row["expires"],
            "state": row["state"], "state_label": row["state_label"],
        })
    return {
        "node": note.node, "note_id": note.note_id, "unit": note.unit, "title": note.title,
        "created_at": note.created_at.isoformat(), "author": note.author,
        "expires": note.expires.isoformat() if note.expires else None, "reread_reason": note.reread_reason,
        "supersedes_id": note.supersedes_id, "versions": versions,
        "sections": [{"key": key, "label": SECTION_LABELS[key], "text": note.sections[key].text,
                      "citations": [cite(c) for c in note.sections[key].citations]}
                     for key in SECTION_KEYS if key in note.sections],
        "claims": claims, "reread": list(reread),
    }


__all__ = [
    "CLAIM_STATES", "DECLARATION_ABSENCES", "EXTRACTION_DIR", "LAYER_NOTE_DIR", "SOURCE_PREFIX", "all_nodes",
    "append_note_record", "claim_state", "claim_watch_rows", "current_notes", "layer_note_reread_rows", "ledger_path",
    "ledger_snapshot", "note_citation_refs", "note_page_row", "read_note_records", "register_note_watches",
    "source_declarations", "verify_citation_refs", "write_note",
]
