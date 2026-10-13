"""層代表公司宣告——研究替一層宣告用誰的營收代表這一層的成長（個股頁 S3c）。

`contracts.py` 是純邏輯（紀錄形狀、id、現行選取）；檔案 I/O 與寫入端核對在 `alpha/providers/layer_reps.py`。
"""
from .contracts import (
    MIN_WHY_CHARS, RECORD_VERSION, REFUSED_PREFIXES, SCOPE_LABELS, SCOPES, LayerRepresentatives, Representative,
    layer_reps_record, new_rep_id, parse_layer_reps_record, select_current,
)

__all__ = ["MIN_WHY_CHARS", "RECORD_VERSION", "REFUSED_PREFIXES", "SCOPES", "SCOPE_LABELS", "LayerRepresentatives",
           "Representative", "layer_reps_record", "new_rep_id", "parse_layer_reps_record", "select_current"]
