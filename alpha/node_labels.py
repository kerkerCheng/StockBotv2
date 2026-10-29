"""圖節點的中文名（呈現用字彙，`config/node_labels_zh.json`）——唯一的讀取點。

2026-10-29 起候選列（「是不是新賭注」那幾句）也要用中文名，原本只有 `webapp.materialize` 讀這份檔；
兩邊各讀一份會在第一次改格式時開始偏離（L16），所以讀取搬到這裡、兩邊都從這裡拿。
讀不到＝空表——畫面照印圖上的英文名，不擋任何流程。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

NODE_LABELS_ZH_PATH = Path(__file__).resolve().parents[1] / "config" / "node_labels_zh.json"


def node_labels_zh(path: Path | None = None) -> dict[str, str]:
    """節點 id → 中文名。讀不到或格式不對＝空表（呈現字彙，不是 authority）。"""
    try:
        raw = json.loads((path or NODE_LABELS_ZH_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    labels = raw.get("labels") if isinstance(raw, Mapping) else None
    return {str(k): str(v) for k, v in (labels or {}).items() if isinstance(v, str) and v.strip()}


__all__ = ["NODE_LABELS_ZH_PATH", "node_labels_zh"]
