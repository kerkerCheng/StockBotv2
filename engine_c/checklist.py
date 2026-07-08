"""
checklist.py — 5 項財務核驗清單查詢（Watchlist Gate 用）。

get_checklist(ticker) -> dict
  回傳 5 項各自的狀態（ok / manual_required / missing）與數值，
  供 thesis/generate_lane_memo.py 的 Watchlist Gate 使用。

連線方式與 etl_yfinance.py 相同（POSTGRES_DSN 或分項 env vars）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def _get_conn():
    try:
        import psycopg2
    except ImportError:
        return None
    dsn = os.environ.get("POSTGRES_DSN")
    try:
        if dsn:
            return psycopg2.connect(dsn)
        return psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", 5432)),
            dbname=os.environ.get("POSTGRES_DB", "stockbot"),
            user=os.environ.get("POSTGRES_USER", "stockbot"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
        )
    except Exception:
        return None


def _snap_status(value, label: str) -> dict:
    """把一個數值包成清單項目格式。"""
    if value is None:
        return {"status": "missing", "value": None, "label": label}
    return {"status": "ok", "value": value, "label": label}


def _manual_status(value: str | None, label: str) -> dict:
    if value:
        return {"status": "manual_reviewed", "value": value, "label": label}
    return {"status": "manual_required", "value": None, "label": label}


def get_checklist(ticker: str) -> dict:
    """
    5 項財務核驗清單。

    回傳結構：
    {
      "ticker": "COHR",
      "engine_c_available": True/False,
      "items": {
        "gross_margin_trend": {"status": "ok"|"missing", "value": [...], "label": "..."},
        "customer_concentration": {"status": "manual_required", "value": None, "label": "..."},
        "backlog": {"status": "manual_required", "value": None, "label": "..."},
        "dilution": {"status": "ok", "value": {...}, "label": "..."},
        "valuation_pressure": {"status": "ok", "value": {...}, "label": "..."},
      },
      "gate_pass": True/False   # True = 全部 ok 或 manual_reviewed（無 missing）
    }
    """
    conn = _get_conn()
    if conn is None:
        return {
            "ticker": ticker,
            "engine_c_available": False,
            "items": {},
            "gate_pass": False,
            "note": "Postgres 不可用（Engine C 未啟動）",
        }

    try:
        with conn.cursor() as cur:
            # 最近 4 季毛利率
            cur.execute("""
                SELECT snapshot_date, gross_margin, shares_outstanding,
                       pe_forward, ev_revenue, price,
                       analyst_target_mean, analyst_target_count
                FROM financial_snapshots
                WHERE ticker = %s
                ORDER BY snapshot_date DESC
                LIMIT 4
            """, (ticker,))
            snaps = cur.fetchall()

            # 人工填入項目
            cur.execute("""
                SELECT field_name, value FROM manual_fields
                WHERE ticker = %s
            """, (ticker,))
            manual = {row[0]: row[1] for row in cur.fetchall()}
    finally:
        conn.close()

    if not snaps:
        return {
            "ticker": ticker,
            "engine_c_available": True,
            "items": {
                k: {"status": "missing", "value": None, "label": l}
                for k, l in [
                    ("gross_margin_trend", "毛利率趨勢"),
                    ("customer_concentration", "客戶集中度"),
                    ("backlog", "Backlog/訂單能見度"),
                    ("dilution", "稀釋分析"),
                    ("valuation_pressure", "估值壓力"),
                ]
            },
            "gate_pass": False,
            "note": f"Postgres 有資料但 {ticker} 無快照，請先執行 ETL",
        }

    # 1. 毛利率趨勢（最近 4 季）
    gm_vals = [(str(r[0]), r[1]) for r in snaps if r[1] is not None]
    gm_item = _snap_status(gm_vals or None, "毛利率趨勢（近 4 季）")
    if gm_item["status"] == "ok":
        latest = gm_vals[0][1]
        oldest = gm_vals[-1][1]
        trend = "上升" if latest > oldest else ("下滑" if latest < oldest else "持平")
        gm_item["trend"] = trend
        gm_item["latest"] = f"{latest:.1%}"

    # 2. 客戶集中度（人工）
    cc_item = _manual_status(manual.get("customer_concentration"), "客戶集中度（前三大客戶 % 收入）")

    # 3. Backlog（人工）
    bl_item = _manual_status(manual.get("backlog"), "Backlog/訂單能見度")

    # 4. 稀釋分析（shares_outstanding 趨勢）
    shares = [(str(r[0]), r[2]) for r in snaps if r[2] is not None]
    dil_item = _snap_status(shares or None, "稀釋分析（股數趨勢）")
    if dil_item["status"] == "ok" and len(shares) >= 2:
        delta = (shares[0][1] - shares[-1][1]) / shares[-1][1]
        dil_item["shares_change"] = f"{delta:+.1%}"

    # 5. 估值壓力
    latest_snap = snaps[0]
    val_data = {
        "price": latest_snap[5],
        "pe_forward": latest_snap[3],
        "ev_revenue": latest_snap[4],
        "analyst_target_mean": latest_snap[6],
        "analyst_target_count": latest_snap[7],
    }
    has_val = any(v is not None for v in val_data.values())
    val_item = _snap_status(val_data if has_val else None, "估值壓力（P/E, EV/Rev, 分析師目標價）")

    items = {
        "gross_margin_trend":     gm_item,
        "customer_concentration": cc_item,
        "backlog":                bl_item,
        "dilution":               dil_item,
        "valuation_pressure":     val_item,
    }

    gate_pass = all(
        v["status"] in ("ok", "manual_reviewed")
        for v in items.values()
    )

    return {
        "ticker": ticker,
        "engine_c_available": True,
        "items": items,
        "gate_pass": gate_pass,
    }


def format_checklist(result: dict) -> str:
    """把 get_checklist() 的結果格式化成人類可讀字串（用於 Lane Memo context）。"""
    lines = [f"## 5 項財務核驗清單：{result['ticker']}"]

    if not result.get("engine_c_available"):
        lines.append(f"⚠ {result.get('note', 'Engine C 未啟動')}")
        return "\n".join(lines)

    note = result.get("note")
    if note:
        lines.append(f"⚠ {note}")

    status_icon = {"ok": "✓", "manual_reviewed": "✓(人工)", "manual_required": "⚠(人工待填)", "missing": "✗"}
    for key, item in result.get("items", {}).items():
        icon = status_icon.get(item["status"], "?")
        val = item.get("value", "")
        extra = ""
        if key == "gross_margin_trend" and item.get("trend"):
            extra = f"  趨勢：{item['trend']}，最新：{item.get('latest', 'N/A')}"
        elif key == "dilution" and item.get("shares_change"):
            extra = f"  股數變化：{item['shares_change']}"
        elif key == "valuation_pressure" and isinstance(val, dict):
            parts = []
            if val.get("price"):
                parts.append(f"價格=${val['price']:.2f}")
            if val.get("pe_forward"):
                parts.append(f"FwdPE={val['pe_forward']:.1f}x")
            if val.get("ev_revenue"):
                parts.append(f"EV/Rev={val['ev_revenue']:.1f}x")
            if val.get("analyst_target_mean"):
                parts.append(f"分析師目標=${val['analyst_target_mean']:.2f}(N={val.get('analyst_target_count', '?')})")
            extra = "  " + ", ".join(parts) if parts else ""
        lines.append(f"{icon} {item['label']}{extra}")

    gate = "✓ Gate 通過 → 可升格 Watchlist" if result.get("gate_pass") else "✗ Gate 未通過 → 輸出 [Research Note]"
    lines.append(f"\n**{gate}**")
    return "\n".join(lines)


def main() -> int:
    import json
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "COHR"
    result = get_checklist(ticker)
    print(format_checklist(result))
    print()
    print("--- raw ---")
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("gate_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
