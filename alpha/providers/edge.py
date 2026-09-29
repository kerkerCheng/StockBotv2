"""邊緣判定的取數（Phase 3 Step 3.3）：讀 `config/alpha_screen.json` 的兩個數＋正規化市值與覆蓋家數。

判定本身住 `alpha/edge.py`（純函式）；市值正規化住 `alpha/providers/market_normalization.py`（Phase 0 註明
「Phase 3 候選板接手時仍從這裡取」）。**一輪只打一次外部**（同一個 FX 快取），所以只在 materialize 呼叫——
request path 與資本路徑一律讀 artifact（plan §4.3）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..edge import edge_state

_ROOT = Path(__file__).resolve().parents[2]
ALPHA_SCREEN_PATH = _ROOT / "config" / "alpha_screen.json"


def load_edge_thresholds(path: Path | None = None) -> dict[str, Any]:
    """兩個數（AND）。讀不到或不合法就 raise——**不猜一個預設值**（缺門檻時的「邊緣」是假的）。"""
    payload = json.loads(Path(path or ALPHA_SCREEN_PATH).read_text(encoding="utf-8"))
    cap = payload.get("market_cap_max_usd")
    cov = payload.get("analyst_count_max")
    if not isinstance(cap, (int, float)) or isinstance(cap, bool) or not isinstance(cov, int) or isinstance(cov, bool):
        raise ValueError("config/alpha_screen.json 缺 market_cap_max_usd／analyst_count_max 或型別不對")
    return {"market_cap_max_usd": float(cap), "analyst_count_max": int(cov),
            "effective_from": payload.get("effective_from"), "version": payload.get("version")}


def edge_states(tickers: Sequence[str], *, db_path: Path | None = None,
                thresholds: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """一批標的的邊緣判定（每檔都回值；取不到的輸入落 `unmeasurable`，不丟檔）。"""
    from .market_normalization import screen_inputs

    limits = dict(thresholds or load_edge_thresholds())
    inputs = screen_inputs(list(tickers), db_path=db_path)
    out: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        row = inputs.get(ticker) or {}
        out[ticker] = edge_state(market_cap_usd=row.get("market_cap_usd"), analyst_count=row.get("analyst_count"),
                                 thresholds=limits, market_cap_absence=row.get("market_cap_absence"))
        out[ticker]["threshold_version"] = {"effective_from": limits.get("effective_from"),
                                            "version": limits.get("version")}
    return out


__all__ = ["ALPHA_SCREEN_PATH", "edge_states", "load_edge_thresholds"]
