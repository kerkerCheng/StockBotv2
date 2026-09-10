"""`doc_id` → 抽取檔路徑。**一對多，且檔名不等於 doc_id。**

## 為什麼需要它

兩個實測事實，兩個都不能靠直覺：

1. **`doc_id` 不等於檔名。** `cpo_chip_package_paper.json` 的 doc_id 是
   `Electronic_Chip_Package_and_CPO_Technology_for_Modern_AI_Era`。
   全庫 206 個 doc_id 中有 **11 個**的 `extractions/<doc_id>.json` 不存在。
2. **一個 `doc_id` 可能有多份檔案。** 229 份檔案只有 206 個 doc_id——
   **21 組共用、涉及 44 份**，那是刻意的 addendum 慣例（同一份來源文件分多次抽取，
   共用 doc_id 讓 SourceDoc 不重複）。

⚠ **只有讀取端需要它。** `intake/provenance.py::_target_paths` 那條寫入路徑
（`<doc_id>.json`）是 intake 自己的約定，同一個 RA 流程內寫了再讀，一對一成立——
把它改成查索引反而會讓它找到歷史 addendum 檔。**分辨的問題是「這個路徑是我剛寫的，
還是別人歷史上寫的」**，不是「要不要一律查索引」。

## 誰在用

- `engine_b/todo.py` 的 graph receipt 稽核（改前對那 11 個 doc_id 會拋
  「無可稽核依據」，但依據存在、只是檔名不同——L15：gate 攔下的不是它想攔的東西）
- `loader/migrate_entity_alias_backfill.py` 的重載清單
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTIONS_DIR = ROOT / "extractions"


@lru_cache(maxsize=4)
def _index(directory: str) -> dict[str, tuple[Path, ...]]:
    index: dict[str, list[Path]] = {}
    for path in sorted(Path(directory).glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        doc_id = (doc.get("source_doc") or {}).get("doc_id")
        if doc_id:
            index.setdefault(str(doc_id), []).append(path)
    return {k: tuple(v) for k, v in index.items()}


def build_index(directory: Path | None = None) -> dict[str, tuple[Path, ...]]:
    """doc_id → 所有宣告該 doc_id 的抽取檔（依檔名排序）。"""

    return dict(_index(str(directory or EXTRACTIONS_DIR)))


def paths_for(doc_id: str, directory: Path | None = None) -> tuple[Path, ...]:
    """該 doc_id 的所有抽取檔；沒有就回空 tuple。"""

    return _index(str(directory or EXTRACTIONS_DIR)).get(str(doc_id), ())


def exists(doc_id: str, directory: Path | None = None) -> bool:
    """圖裡這個 doc_id 有沒有可稽核的抽取依據——**問的是內容，不是檔名**。"""

    return bool(paths_for(doc_id, directory))


def invalidate() -> None:
    """測試或剛寫入新檔之後呼叫。"""

    _index.cache_clear()
