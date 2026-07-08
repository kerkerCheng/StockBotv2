"""
checklist.py — 5 項財務核驗清單查詢（Watchlist Gate 用）。

get_checklist(ticker) -> dict
  回傳 5 項各自的狀態（ok / manual_required / missing）與數值，
  供 thesis/generate_lane_memo.py 的 Watchlist Gate 使用。

後端：SQLite（預設）或 Postgres（設 POSTGRES_HOST/DSN）。
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


def _get_conn():
    try:
        from engine_c.db import get_conn
        return get_conn()
    except Exception:
        return None


def _snap_status(value, label: str) -> dict:
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
        "gross_margin_trend":     {"status": "ok"|"missing", "value": [...], "label": "..."},
        "customer_concentration": {"status": "manual_required", ...},
        "backlog":                {"status": "manual_required", ...},
        "dilution":               {"status": "ok", ...},
        "valuation_pressure":     {"status": "ok", ...},
      },
      "gate_pass": True/False
    }
    """
    conn = _get_conn()
    if conn is None:
        return {
            "ticker": ticker,
            "engine_c_available": False,
            "items": {},
            "gate_pass": False,
            "note": "Engine C 資料庫不可用（db.py 匯入失敗）",
        }

    try:
        from engine_c.db import _use_postgres
        is_pg = _use_postgres()

        if is_pg:
            cur = conn.cursor()
            cur.execute("""
                SELECT snapshot_date, gross_margin, shares_outstanding,
                       pe_forward, ev_revenue, price,
                       analyst_target_mean, analyst_target_count
                FROM financial_snapshots
                WHERE ticker = %s ORDER BY snapshot_date DESC LIMIT 4
            """, (ticker,))
            snaps = cur.fetchall()
            cur.execute(
                "SELECT field_name, value FROM manual_fields WHERE ticker = %s",
                (ticker,)
            )
            manual = {row[0]: row[1] for row in cur.fetchall()}
            conn.close()
        else:
            import sqlite3
            cur = conn.execute("""
                SELECT snapshot_date, gross_margin, shares_outstanding,
                       pe_forward, ev_revenue, price,
                       analyst_target_mean, analyst_target_count
                FROM financial_snapshots
                WHERE ticker = ? ORDER BY snapshot_date DESC LIMIT 4
            """, (ticker,))
            snaps = [tuple(r) for r in cur.fetchall()]
            cur2 = conn.execute(
                "SELECT field_name, value FROM manual_fields WHERE ticker = ?",
                (ticker,)
            )
            manual = {row[0]: row[1] for row in cur2.fetchall()}
            conn.close()

    except Exception as e:
        return {
            "ticker": ticker,
            "engine_c_available": False,
            "items": {},
            "gate_pass": False,
            "note": f"資料庫查詢失敗：{e}",
        }

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
            "note": f"{ticker} 無快照，請先執行 python engine_c/etl_yfinance.py {ticker}",
        }

    # 1. 毛利率趨勢（最近 4 季）
    gm_vals = [(str(r[0]), r[1]) for r in snaps if r[1] is not None]
    gm_item = _snap_status(gm_vals or None, "毛利率趨勢（近 4 季）")
    if gm_item["status"] == "ok":
        latest = gm_vals[0][1]
        oldest = gm_vals[-1][1]
        gm_item["trend"] = "上升" if latest > oldest else ("下滑" if latest < oldest else "持平")
        gm_item["latest"] = f"{latest:.1%}"

    # 2. 客戶集中度（人工填入）
    cc_item = _manual_status(manual.get("customer_concentration"), "客戶集中度（前三大客戶 % 收入）")

    # 3. Backlog（人工填入）
    bl_item = _manual_status(manual.get("backlog"), "Backlog/訂單能見度")

    # 4. 稀釋（shares_outstanding 趨勢）
    shares = [(str(r[0]), r[2]) for r in snaps if r[2] is not None]
    dil_item = _snap_status(shares or None, "稀釋分析（股數趨勢）")
    if dil_item["status"] == "ok" and len(shares) >= 2:
        delta = (shares[0][1] - shares[-1][1]) / shares[-1][1]
        dil_item["shares_change"] = f"{delta:+.1%}"

    # 5. 估值壓力
    r0 = snaps[0]
    val_data = {
        "price": r0[5], "pe_forward": r0[3], "ev_revenue": r0[4],
        "analyst_target_mean": r0[6], "analyst_target_count": r0[7],
    }
    val_item = _snap_status(
        val_data if any(v is not None for v in val_data.values()) else None,
        "估值壓力（P/E, EV/Rev, 分析師目標價）"
    )

    items = {
        "gross_margin_trend":     gm_item,
        "customer_concentration": cc_item,
        "backlog":                bl_item,
        "dilution":               dil_item,
        "valuation_pressure":     val_item,
    }
    gate_pass = all(v["status"] in ("ok", "manual_reviewed") for v in items.values())

    return {
        "ticker": ticker,
        "engine_c_available": True,
        "items": items,
        "gate_pass": gate_pass,
    }


def format_checklist(result: dict) -> str:
    lines = [f"## 5 項財務核驗清單：{result['ticker']}"]

    if not result.get("engine_c_available"):
        lines.append(f"⚠ {result.get('note', 'Engine C 未啟動')}")
        return "\n".join(lines)

    if result.get("note"):
        lines.append(f"⚠ {result['note']}")

    icon_map = {"ok": "✓", "manual_reviewed": "✓(人工)", "manual_required": "⚠(人工待填)", "missing": "✗"}
    for key, item in result.get("items", {}).items():
        icon = icon_map.get(item["status"], "?")
        extra = ""
        if key == "gross_margin_trend" and item.get("trend"):
            extra = f"  趨勢：{item['trend']}，最新：{item.get('latest', 'N/A')}"
        elif key == "dilution" and item.get("shares_change"):
            extra = f"  股數變化：{item['shares_change']}"
        elif key == "valuation_pressure" and isinstance(item.get("value"), dict):
            v = item["value"]
            parts = []
            if v.get("price"):       parts.append(f"${v['price']:.2f}")
            if v.get("pe_forward"):  parts.append(f"FwdPE={v['pe_forward']:.1f}x")
            if v.get("ev_revenue"):  parts.append(f"EV/Rev={v['ev_revenue']:.1f}x")
            if v.get("analyst_target_mean"):
                parts.append(f"分析師=${v['analyst_target_mean']:.2f}(N={v.get('analyst_target_count','?')})")
            extra = "  " + ", ".join(parts) if parts else ""
        lines.append(f"{icon} {item['label']}{extra}")

    gate = "✓ Gate 通過 → 可升格 Watchlist" if result.get("gate_pass") else "✗ Gate 未通過 → [Research Note]"
    lines.append(f"\n**{gate}**")
    return "\n".join(lines)


def main() -> int:
    import json
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "COHR"
    result = get_checklist(ticker)
    print(format_checklist(result))
    print("\n--- raw ---")
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("gate_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
