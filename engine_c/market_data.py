"""
market_data.py — 取當日市場快照（股價、估值倍數、分析師共識）。

主要用途：為 Lane Memo 的 Variant Perception 段落提供數字錨點。
數據來源：yfinance（延遲 1 天；私人公司/未知 ticker 回傳 None）。

用法:
    from engine_c.market_data import get_snapshot, format_snapshot
    snap = get_snapshot("COHR")
"""
from __future__ import annotations

import sys


def get_snapshot(ticker: str) -> dict:
    """
    回傳市場快照 dict。若 yfinance 不可用或資料缺失，各欄位為 None。

    結構:
    {
      "ticker": "COHR",
      "price": 42.15,
      "pe_trailing": 25.3,
      "pe_forward": 18.3,
      "ev_revenue": 3.2,
      "analyst_target_mean": 55.0,
      "analyst_target_count": 12,
      "gross_margin": 0.452,
      "available": True/False,
      "note": "...",    # 說明（如「私人公司，無市場數據」）
    }
    """
    base = {
        "ticker": ticker,
        "price": None,
        "pe_trailing": None,
        "pe_forward": None,
        "ev_revenue": None,
        "analyst_target_mean": None,
        "analyst_target_count": None,
        "gross_margin": None,
        "available": False,
        "note": "",
    }

    try:
        import yfinance as yf
    except ImportError:
        base["note"] = "yfinance 未安裝（pip install yfinance）"
        return base

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        base["note"] = f"yfinance 取得失敗：{e}"
        return base

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if not price:
        base["note"] = f"{ticker} 無價格資料（可能未上市或 ticker 錯誤）"
        return base

    def _f(key) -> float | None:
        try:
            v = info.get(key)
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    def _i(key) -> int | None:
        try:
            v = info.get(key)
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    base.update({
        "price":                _f("currentPrice") or _f("regularMarketPrice"),
        "pe_trailing":          _f("trailingPE"),
        "pe_forward":           _f("forwardPE"),
        "ev_revenue":           _f("enterpriseToRevenue"),
        "analyst_target_mean":  _f("targetMeanPrice"),
        "analyst_target_count": _i("numberOfAnalystOpinions"),
        "gross_margin":         _f("grossMargins"),
        "available": True,
        "note": "",
    })
    return base


def format_snapshot(snap: dict) -> str:
    """格式化成 Lane Memo system prompt 的注入片段（Markdown）。"""
    ticker = snap.get("ticker", "?")
    if not snap.get("available"):
        note = snap.get("note", "市場數據不可用")
        return (
            f"## 市場定價數據（Variant Perception 錨點）\n"
            f"⚠ {ticker}: {note}\n"
            f"[請手動填寫 Variant Perception — 市場信 X，本 thesis 信 Y，催化劑 Z]\n"
        )

    lines = [f"## 市場定價數據：{ticker}（Variant Perception 錨點）"]

    if snap.get("price"):
        lines.append(f"- 當前股價：${snap['price']:.2f}")
    if snap.get("pe_trailing"):
        lines.append(f"- Trailing P/E：{snap['pe_trailing']:.1f}x")
    if snap.get("pe_forward"):
        lines.append(f"- Forward P/E：{snap['pe_forward']:.1f}x")
    if snap.get("ev_revenue"):
        lines.append(f"- EV/Revenue：{snap['ev_revenue']:.2f}x")
    if snap.get("analyst_target_mean") and snap.get("analyst_target_count"):
        lines.append(
            f"- 分析師目標價均值：${snap['analyst_target_mean']:.2f}"
            f"  (N={snap['analyst_target_count']})"
        )
    if snap.get("gross_margin"):
        lines.append(f"- 毛利率（最新）：{snap['gross_margin']:.1%}")

    if snap.get("ev_revenue") and snap.get("gross_margin"):
        ev = snap["ev_revenue"]
        gm = snap["gross_margin"]
        lines.append(
            f"\n**隱含假設提示：** EV/Rev={ev:.1f}x + 毛利率={gm:.0%} → "
            f"市場可能定價的收入增長率約為 {ev * gm * 100:.0f}%-{ev * (gm + 0.1) * 100:.0f}%/年（粗估）。"
            f"\n[請在 Variant Perception 填寫：市場假設 X，本 thesis 認為 Y，催化劑 Z]"
        )
    else:
        lines.append(
            "\n[請在 Variant Perception 填寫：市場假設 X，本 thesis 認為 Y，催化劑 Z]"
        )

    return "\n".join(lines)


def main() -> int:
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "COHR"
    snap = get_snapshot(ticker)
    print(format_snapshot(snap))
    return 0 if snap["available"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
