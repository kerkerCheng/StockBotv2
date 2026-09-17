"""結構讀圖 ledger 的 I/O：`library/private/alpha/structure_readings/<node>.jsonl`。

與 `alpha/providers/abstentions.py`／`briefs.py` 同一個位置慣例與同一套規則：private、
append-only、content-addressed id 拒絕重複、secret 拒絕、`supersedes_id` 必須指到既有紀錄。
純邏輯（解析、選取、分級）在 `alpha/structure_reading/`；這裡只讀寫檔。

⚠ **主鍵是 node 不是 ticker**（`tech:cw_dfb_laser`、`mat:inp_substrate`）——結構讀圖問的是
「這個位置卡不卡」，一個節點會餵好幾檔股票的賭注。所以它另立一本，不塞進 `briefs/`：
那本的主鍵是 ticker、七格是封閉字彙，硬塞會讓兩邊的 contract 都變成「什麼都能放」（L16-3）。
node 會出現在檔名裡，所以 `:`／`/` 等路徑字元要正規化。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from shared.redaction import sensitive_payload_path

from ..errors import ContractViolation
from ..structure_reading.contracts import StructureReading, parse_structure_reading_record

_ROOT = Path(__file__).resolve().parents[2]
STRUCTURE_READING_DIR = _ROOT / "library" / "private" / "alpha" / "structure_readings"

#: node id 允許的字元；其餘一律換成 `_`。**不是為了美觀**——`tech:cw_dfb_laser` 直接當檔名
#: 在 Windows 上會被當成 NTFS 資料流（`檔名:資料流`）而靜默寫到別的地方。
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def _slug(node: str) -> str:
    text = _UNSAFE.sub("_", str(node).strip())
    if not text:
        raise ContractViolation("node 正規化後是空字串——檔名推不出來")
    return text


def ledger_path(node: str, *, directory: Path | None = None) -> Path:
    return (directory or STRUCTURE_READING_DIR) / f"{_slug(node)}.jsonl"


def read_reading_records(node: str, *, directory: Path | None = None,
                         ) -> tuple[list[StructureReading], list[str]]:
    """讀一個節點的全部紀錄。壞掉的行**不靜默丟棄**——回在第二個 list 裡，消費端計數（INV-3）。"""
    path = ledger_path(node, directory=directory)
    if not path.is_file():
        return [], []
    records: list[StructureReading] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(parse_structure_reading_record(json.loads(text)))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def append_reading_record(record: Mapping[str, Any], *, directory: Path | None = None) -> Path:
    """append 一筆（已由 `structure_reading_record()` 驗證過的）紀錄；只 append，永不改寫既有行。"""
    parsed = parse_structure_reading_record(record)
    sensitive = sensitive_payload_path(dict(record), "structure_reading")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing structure reading rejected at {sensitive}")
    existing, _errors = read_reading_records(parsed.node, directory=directory)
    if any(r.reading_id == parsed.reading_id for r in existing):
        raise ContractViolation(f"reading {parsed.reading_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id and not any(r.reading_id == parsed.supersedes_id for r in existing):
        raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在 ledger 中")
    path = ledger_path(parsed.node, directory=directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def fetch_structure_snapshot(node: str) -> dict[str, Any]:
    """現在的圖對這個節點回什麼（`query.structure` 的輸出照抄）。

    ⚠ **這一支住在 providers 是刻意的**：`alpha/` 的契約與模型層不得依賴外部世界，
    providers 是唯一例外（`tests/test_layer_separation.py` 在守）。2026-09-17 實測：
    先前把 `from query.structure import ...` 寫進 `alpha/cli.py`，那條測試立刻紅。

    ⚠ 快照**只能**由這裡產生，不接受呼叫端遞來——手組的快照偵測不了
    「多了一條我當初沒讀到的邊」，而那正是這本 ledger 存在的理由。
    """
    from query.structure import _load_edges, build_structure

    return build_structure(str(node), _load_edges()).as_dict()


def known_nodes(*, directory: Path | None = None) -> list[str]:
    """ledger 裡有紀錄的節點（由檔案內容回報真正的 node，不從檔名反推 slug）。"""
    root = directory or STRUCTURE_READING_DIR
    if not root.is_dir():
        return []
    nodes: list[str] = []
    for path in sorted(root.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                node = str(json.loads(text).get("node") or "")
            except ValueError:
                continue
            if node:
                nodes.append(node)
                break
    return nodes


__all__ = ["STRUCTURE_READING_DIR", "append_reading_record", "fetch_structure_snapshot", "known_nodes",
           "ledger_path", "read_reading_records"]
