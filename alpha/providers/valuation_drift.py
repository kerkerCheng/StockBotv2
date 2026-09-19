"""目標倍數 vs 今天的市場倍數：**誰在盯這兩者背離**（2026-09-19，七缺陷之 6）。

⚠ 住在 `providers/` 而不是 `valuation/`：它讀 ledger 檔與 Engine C sqlite，是 I/O。
`alpha/valuation/` 是純邏輯層，`tests/test_valuation_model.py` 會擋 `sqlite3` 這類 import。

## 為什麼需要這個模組

AGENTS.md（2026-09-09 定案）：**沒有 re-rating 證據時，目標倍數預設等於校準用的市場倍數**。
那是一條**不會腐壞的判準**。但它一旦落地成 ledger 裡的**一個固定數字**，判準就從此不再被
執行——而每一天的股價變動都在擴大背離。

事發（2026-09-19 [616] 紅隊審查）：LITE 的估值假設逐字宣告「目標倍數＝校準倍數，**零折溢價**」，
校準於 2026-09-08 的 978.535 ÷ 21.6426 ＝ 45.21x。11 天後股價 −8.7%、共識只動 +0.13%，
於是同一筆假設**同時宣告「零溢價」又印出 +9.6% 的倍數差異貢獻**——兩者不可能都對。
代價：base +19.3%／賭對 +20.7%／判斷錯 −1.3% 看起來是極不對稱的好賭注，重新校準後
變成 +8.8%／+10.1%／−10.0%，**幾乎完全對稱**。那個不對稱不是 LITE 的性質，是倍數陳舊的假象。

`implied_return` 其實早就印著那句警告，但它**不進 refresh、不進 readiness、不進籃子 filter、
不進心跳**——警告在，沒有人被叫醒（L13-1：產出要出現在下游消費者手上）。

## 三道 fail closed——**這個 gate 必須攔對東西**（L15-1）

2026-09-19 實測 49 筆生效假設，兩個「量級異常」都**不是腐壞**：

1. **SOI.PA 的 −96.5%（ROADMAP 原記）是把兩個不同的量相比。** 它的生效假設是
   `target_ev_to_sales=7.25`，根本沒有 `target_pe`；拿 7.25 去跟 `price/eps`＝204x 比，
   得出的 −96.5% 沒有任何意義。→ **parameter／method 不對就不判定。**
2. **HEXA-B.ST 的 −91.3% 是幣別不一致。** 報價是 SEK（registry `market_quote_unit`），
   共識 EPS 是 EUR（Hexagon 報表幣別）：95.56 ÷ 0.31346 ＝ 304.9 是**把 SEK 除以 EUR**。
   以 EUR 計的隱含匯率 11.4456 SEK/EUR 正是真實量級——**那筆 26.64x 是對的**。
   → **單位不可比就不判定**（缺陷 7 剛讓 `quote_unit` 跟著資料走，這裡就是第一個消費者）。
3. **刻意主張折溢價的不該被叫醒**（L11-6：最先壞掉的是哪一筆）。`derivation` 不是
   `calibrated_to_market` 的那些（實測 COHR −25.8%、LYC.AX −13.4%）背離是**有意的**。

⚠ 第 2 道不是新判準，是**把既有的判準帶到這一層**（L16）：`python -m webapp status` 對
6680.HK 早就印著 `headline=inputs_incompatible`——**headline 層已經 fail closed，估值假設層沒有**。
同一個問題在一層擋住、在另一層照算，正是 L12 的形狀。

三道都過不了時回 `not_applicable`／`cannot_compare` **並帶理由**，不靜默跳過（INV-3）。

## 為什麼是 5%

實測 47 筆 `calibrated_to_market`：背離 >3% 有 22 筆（47%）、**>5% 有 14 筆（30%）**、
>10% 有 5 筆（11%）、>15% 有 1 筆。L14-4 的三個免 outcome 測試：
**恆亮？** 30% 不是恆亮。**不會滅？** 會——append 一筆重新校準的假設就清掉。
**講得出因果機制？** 講得出：宣告零折溢價卻背離 5%，那 5% 就是**沒有證據的溢價**，
而它會原封不動變成隱含報酬兩欄拆解裡的「倍數差異貢獻」。
⚠ 10% 會漏掉事發那一筆（LITE 當時 9.6%），所以**不取 10%**。

⚠ **不要改成每天自動重新校準**：那會讓 fair value 永遠跟著股價走、隱含報酬只剩 EPS 一桿，
等於偷偷取消「倍數也是一個可以有主張的桿」。本模組**只標記，不改任何 ledger**。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

#: 背離多少算「該重新校準」。見模組 docstring 的分佈量測。
DRIFT_THRESHOLD = 0.05

#: 封閉字彙。**缺值自成一類**，不併進「沒背離」也不靜默放行（INV-3）。
STATUSES = {
    "drift_exceeds": "宣告零折溢價，但與今天的市場倍數背離超過門檻——該重新校準或寫出折溢價的證據",
    "within_band": "在門檻內",
    "not_applicable": "這條判準不適用於這筆假設（不是 target_pe，或刻意主張折溢價）",
    "cannot_compare": "比不了——缺價格／缺共識／單位不可比。**不是沒背離，是不知道**",
}

_ROOT = Path(__file__).resolve().parents[2]
VALUATION_DIR = _ROOT / "library" / "private" / "alpha" / "valuation"
ENGINE_C_DB = _ROOT / "library" / "private" / "engine_c" / "stockbot-engine-c-private-v1-458db5270ee2.db"


@dataclass(frozen=True)
class DriftRow:
    ticker: str
    status: str
    target: float | None = None
    market: float | None = None
    drift: float | None = None
    period_end: str | None = None
    reason: str | None = None
    assumption_id: str | None = None


def live_target_pe_records(directory: Path | None = None) -> list[dict[str, Any]]:
    """每一檔的**生效** `target_pe`：未 `retracted`、且未被任何一筆 `supersedes_id` 指到。

    ⚠ 刻意讀 raw jsonl 而不是走完整 selector：selector 要 target period、evidence_index
    與 scenario，而本模組問的是「ledger 裡現在躺著什麼」，不是「某個 as-of 下哪一筆生效」。
    """
    out: list[dict[str, Any]] = []
    for path in sorted((directory or VALUATION_DIR).glob("*.jsonl")):
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        superseded = {r["supersedes_id"] for r in records if r.get("supersedes_id")}
        out.extend(
            r for r in records
            if r.get("parameter") == "target_pe"
            and not r.get("retracted")
            and r.get("assumption_id") not in superseded
        )
    return out


def _quote_and_settlement(ticker: str) -> tuple[str | None, str | None]:
    from identity.registry import get_registry

    registry = get_registry()
    company_id = registry.company_id_for_ticker(ticker)
    company = registry.company(company_id) if company_id else None
    return (getattr(company, "market_quote_unit", None), getattr(company, "market_currency", None))


def assess(record: Mapping[str, Any], conn: sqlite3.Connection) -> DriftRow:
    """單筆假設 → 一列判定。**三道 fail closed 在前，比值在後**（先身分，再判準；L15-3）。"""
    ticker = str(record["ticker"])
    target = record.get("value")
    period_end = str(record.get("period_end") or "")
    base = dict(ticker=ticker, target=target, period_end=period_end,
                assumption_id=str(record.get("assumption_id") or ""))

    if record.get("method") != "forward_earnings_multiple":
        return DriftRow(status="not_applicable", reason=f"method={record.get('method')}，不是前瞻本益比", **base)
    if record.get("derivation") != "calibrated_to_market":
        return DriftRow(status="not_applicable",
                        reason=f"derivation={record.get('derivation')}——**刻意主張折溢價，背離是有意的**", **base)

    row = conn.execute(
        "SELECT price, bar_date FROM financial_snapshots WHERE ticker=? "
        "ORDER BY COALESCE(bar_date, snapshot_date) DESC LIMIT 1", (ticker,)).fetchone()
    if not row or row["price"] is None:
        return DriftRow(status="cannot_compare", reason="Engine C 無現價快照", **base)
    estimate = conn.execute(
        "SELECT estimate_avg, currency FROM consensus_estimates WHERE ticker=? AND metric='eps' "
        "AND fiscal_period_end=? ORDER BY snapshot_date DESC LIMIT 1", (ticker, period_end)).fetchone()
    if not estimate or not estimate["estimate_avg"]:
        return DriftRow(status="cannot_compare", reason=f"無 {period_end} 的共識 EPS", **base)

    quote_unit, settlement = _quote_and_settlement(ticker)
    consensus_currency = (estimate["currency"] or "").upper() or None
    if not quote_unit or not settlement:
        return DriftRow(status="cannot_compare",
                        reason="registry 沒有可解析的 market_currency——不知道 price 以什麼單位報價", **base)
    if consensus_currency and settlement.upper() != consensus_currency:
        return DriftRow(
            status="cannot_compare",
            reason=(f"單位不可比：報價 {quote_unit}（結算 {settlement}）vs 共識 EPS {consensus_currency}"
                    "——相除得到的不是本益比。**這不是背離，是換算沒做**"), **base)
    if quote_unit != settlement:
        return DriftRow(
            status="cannot_compare",
            reason=(f"報價單位 {quote_unit} 是 minor unit（結算 {settlement}），"
                    "與共識 EPS 差 100 倍——先換算再比"), **base)

    market = float(row["price"]) / float(estimate["estimate_avg"])
    drift = float(target) / market - 1 if market else None
    status = "drift_exceeds" if (drift is not None and abs(drift) > DRIFT_THRESHOLD) else "within_band"
    return DriftRow(status=status, market=market, drift=drift, **base)


def scan(*, directory: Path | None = None, db_path: Path | None = None,
         conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """全 ledger 掃描 → rows ＋ 每個 status 的計數（INV-3：input／accepted／filtered 都報）。"""
    owns = conn is None
    if conn is None:
        conn = sqlite3.connect(db_path or ENGINE_C_DB)
        conn.row_factory = sqlite3.Row
    try:
        rows = [assess(r, conn) for r in live_target_pe_records(directory)]
    finally:
        if owns:
            conn.close()
    counts = {key: sum(1 for r in rows if r.status == key) for key in STATUSES}
    return {
        "threshold": DRIFT_THRESHOLD,
        "input": len(rows),
        "counts": counts,
        "status_labels": STATUSES,
        "rows": sorted(rows, key=lambda r: (r.status != "drift_exceeds", -abs(r.drift or 0))),
    }


def heartbeat_line(result: Mapping[str, Any]) -> str:
    """心跳段 2 的一行。**不重算**——吃的是 `scan()` 的結果。"""
    counts = result["counts"]
    flagged: Iterable[DriftRow] = [r for r in result["rows"] if r.status == "drift_exceeds"]
    names = "、".join(f"{r.ticker} {r.drift:+.1%}" for r in list(flagged)[:5])
    line = (f"目標倍數背離：**{counts['drift_exceeds']} 檔超過 {result['threshold']:.0%}**"
            f"（在帶內 {counts['within_band']}｜不適用 {counts['not_applicable']}"
            f"｜比不了 {counts['cannot_compare']}）")
    if names:
        line += "：" + names + ("…" if counts["drift_exceeds"] > 5 else "")
        line += "——宣告零折溢價卻背離，**要嘛重新校準、要嘛寫出折溢價的證據**"
    return line


__all__ = ["DRIFT_THRESHOLD", "DriftRow", "STATUSES", "assess", "heartbeat_line",
           "live_target_pe_records", "scan"]
