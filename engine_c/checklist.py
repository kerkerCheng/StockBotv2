"""
checklist.py — 5 項財務核驗清單查詢（Watchlist Gate 用）。

get_checklist(ticker) -> dict
  回傳 5 項各自的狀態（ok / manual_required / missing）與數值，
  供 thesis/generate_lane_memo.py 的 Watchlist Gate 使用。

後端：SQLite（預設）或 Postgres（設 POSTGRES_HOST/DSN）。
"""
from __future__ import annotations

import json
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


def _manual_status(value: str | None, label: str, source_note: str | None = None) -> dict:
    if value and source_note:
        return {
            "status": "manual_reviewed",
            "value": value,
            "source": source_note,
            "label": label,
        }
    return {"status": "manual_required", "value": None, "label": label}


def _prefer_manual(auto_item: dict, manual: dict, field_name: str, label: str) -> dict:
    """已逐字核對的人工觀測優先於 financial_snapshots 的衍生值。

    自動值只看得到當期快照，會在真實世界變動時給出錯誤答案：shares_outstanding
    每天相同，稀釋因此永遠算成 +0.0%，與財報加權平均股數的實際變化矛盾（AXT
    Q2 2026 為 +45.2%）。有登記的人工觀測代表有人核過一手文件，讓它勝出；
    自動值整包留在 auto_item，不散落成會被誤讀的裸鍵。
    """
    value, source_note = manual.get(field_name, (None, None))
    if not value or not source_note:
        return auto_item
    return {
        "status": "manual_reviewed",
        "value": value,
        "source": source_note,
        "label": label,
        "auto_item": auto_item,
    }


def _extended_observations(manual: dict) -> dict:
    """把非 gate 的已登記人工觀測整理成開放讀取表面。

    每筆自帶 `authorities`，讓 Engine D 的 reference index 不必反查 Engine C registry
    （decision_lab 不得反向依賴 current-state authority）。未登記或無 provenance 的
    欄位一律略過——寧可不出現，也不要讓沒有來源的值被 Confidence 軸引用。
    """
    from engine_c.observation_fields import get_observation_field_registry

    registry = get_observation_field_registry()
    result: dict[str, dict] = {}
    for field_name, (value, source_note) in sorted(manual.items()):
        spec = registry.get(field_name)
        if spec is None or spec.gate_member:
            continue
        if not value or not source_note:
            continue
        result[field_name] = {
            "status": "manual_reviewed",
            "value": value,
            "source": source_note,
            "label": spec.label,
            "category": spec.category,
            "authorities": list(spec.authorities),
        }
    return result


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
            "observations": {},
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
                "SELECT field_name, value, source_note FROM manual_fields WHERE ticker = %s",
                (ticker,)
            )
            manual = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
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
                "SELECT field_name, value, source_note FROM manual_fields WHERE ticker = ?",
                (ticker,)
            )
            manual = {row[0]: (row[1], row[2]) for row in cur2.fetchall()}
            conn.close()

    except Exception as e:
        return {
            "ticker": ticker,
            "engine_c_available": False,
            "items": {},
            "observations": {},
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
            "observations": _extended_observations(manual),
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
    gm_item = _prefer_manual(gm_item, manual, "gross_margin_trend", "毛利率趨勢（近 4 季）")

    # 2. 客戶集中度（人工填入）
    cc_value, cc_source = manual.get("customer_concentration", (None, None))
    cc_item = _manual_status(
        cc_value,
        "客戶集中度（前三大客戶 % 收入）",
        cc_source,
    )

    # 3. Backlog（人工填入）
    bl_value, bl_source = manual.get("backlog", (None, None))
    bl_item = _manual_status(bl_value, "Backlog/訂單能見度", bl_source)

    # 4. 稀釋（shares_outstanding 趨勢）
    shares = [(str(r[0]), r[2]) for r in snaps if r[2] is not None]
    dil_item = _snap_status(shares or None, "稀釋分析（股數趨勢）")
    if dil_item["status"] == "ok" and len(shares) >= 2:
        delta = (shares[0][1] - shares[-1][1]) / shares[-1][1]
        dil_item["shares_change"] = f"{delta:+.1%}"
    dil_item = _prefer_manual(dil_item, manual, "dilution", "稀釋分析（股數趨勢）")

    # 5. 估值壓力
    r0 = snaps[0]
    val_data = {
        "price": r0[5], "pe_forward": r0[3], "ev_revenue": r0[4],
        "analyst_target_mean": r0[6], "analyst_target_count": r0[7],
    }
    val_label = "估值壓力（P/E, EV/Rev, 分析師目標價）"
    val_item = _snap_status(
        val_data if any(v is not None for v in val_data.values()) else None,
        val_label,
    )
    val_item = _prefer_manual(val_item, manual, "valuation_pressure", val_label)

    items = {
        "gross_margin_trend":     gm_item,
        "customer_concentration": cc_item,
        "backlog":                bl_item,
        "dilution":               dil_item,
        "valuation_pressure":     val_item,
    }
    # gate_pass 只掃 items（凍結的五項 L9 gate）。擴充欄位刻意不參與，否則新增一個
    # 欄位就會讓所有既有標的的 Watchlist 升格 gate 退化。
    gate_pass = all(v["status"] in ("ok", "manual_reviewed") for v in items.values())

    return {
        "ticker": ticker,
        "engine_c_available": True,
        "items": items,
        "observations": _extended_observations(manual),
        "gate_pass": gate_pass,
    }


_RUNWAY_INPUT_KEYS = ("cash_and_equivalents", "total_debt", "free_cash_flow_ttm")


def _parse_runway_inputs(value, source_note, as_of) -> dict | None:
    """把 runway_inputs 人工觀測轉成 decision_lab.derive_runway 能吃的 payload。

    三個數值缺一即視為未提供：runway 是除法，部分推導只會給出看起來精確的
    錯誤答案。provenance 沿用該筆觀測自己的 source 與 as_of，讓 decision_lab
    既有的 timestamp future／stale 檢查照常生效。
    """
    if not value or not source_note or not as_of:
        return None
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    numbers = {}
    for key in _RUNWAY_INPUT_KEYS:
        raw = payload.get(key)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None
        numbers[key] = float(raw)
    return numbers | {"source": str(source_note), "as_of": str(as_of)}


def _fetch_runway_inputs(connection, ticker: str, *, is_pg: bool) -> dict | None:
    sql = (
        "SELECT value, source_note, updated_at FROM manual_fields "
        "WHERE ticker = {ph} AND field_name = 'runway_inputs'"
    ).format(ph="%s" if is_pg else "?")
    try:
        if is_pg:
            with connection.cursor() as cursor:
                cursor.execute(sql, (ticker,))
                row = cursor.fetchone()
        else:
            row = connection.execute(sql, (ticker,)).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    return _parse_runway_inputs(row[0], row[1], row[2])


def get_probe_financial_baseline(ticker: str, *, conn=None) -> dict:
    """回傳 runway 所需的 point-in-time raw scalars，不在 Engine C 算部位。"""

    owned_connection = conn is None
    connection = conn or _get_conn()
    if connection is None:
        return {"ticker": ticker, "status": "unavailable"}
    try:
        from engine_c.db import _use_postgres

        if _use_postgres():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT snapshot_date, cash_and_equivalents, total_debt,
                           free_cash_flow_ttm, fetched_at
                    FROM financial_snapshots
                    WHERE ticker = %s
                    ORDER BY snapshot_date DESC, fetched_at DESC
                    LIMIT 1
                    """,
                    (ticker,),
                )
                row = cursor.fetchone()
        else:
            row = connection.execute(
                """
                SELECT snapshot_date, cash_and_equivalents, total_debt,
                       free_cash_flow_ttm, fetched_at
                FROM financial_snapshots
                WHERE ticker = ?
                ORDER BY snapshot_date DESC, fetched_at DESC
                LIMIT 1
                """,
                (ticker,),
            ).fetchone()
        if row is None:
            return {"ticker": ticker, "status": "missing"}
        values = tuple(row)
        result = {
            "ticker": ticker,
            "as_of": str(values[0]),
            "cash_and_equivalents": values[1],
            "total_debt": values[2],
            "free_cash_flow_ttm": values[3],
            "fetched_at": str(values[4]),
            "source": "yfinance.info",
        }
        result["status"] = (
            "observed"
            if all(result[key] is not None for key in _RUNWAY_INPUT_KEYS)
            else "manual_required"
        )
        if result["status"] == "manual_required":
            manual_runway = _fetch_runway_inputs(
                connection, ticker, is_pg=_use_postgres()
            )
            if manual_runway is not None:
                result["manual_runway"] = manual_runway
        return result
    except Exception:
        return {"ticker": ticker, "status": "unavailable"}
    finally:
        if owned_connection and connection is not None:
            connection.close()


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
