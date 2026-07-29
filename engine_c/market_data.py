"""
market_data.py — 取當日市場快照（股價、估值倍數、分析師共識）。

主要用途：為 Lane Memo 的 Variant Perception 段落提供數字錨點。
數據來源：yfinance（延遲 1 天；私人公司/未知 ticker 回傳 None）。

用法:
    from engine_c.market_data import get_snapshot, format_snapshot
    snap = get_snapshot("COHR")
"""
from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from access_failures import classify_access_failure
from identity.execution import yfinance_symbol


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def build_tradeability_snapshot(
    *,
    ticker: str,
    currency: str,
    rows: Iterable[Mapping[str, Any]],
    fetched_at: str,
    source: str,
) -> dict[str, Any]:
    """由具實際 session timestamp 的 history rows 建立 execution 快照。"""

    blockers: list[str] = []
    sessions: dict[str, tuple[datetime, float, float]] = {}
    if not isinstance(ticker, str) or not ticker.strip():
        blockers.append("market_ticker_invalid")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isupper():
        blockers.append("market_currency_invalid")
    if _timestamp(fetched_at) is None:
        blockers.append("market_fetched_at_invalid")
    if not isinstance(source, str) or not source.strip():
        blockers.append("market_source_missing")
    for row in rows:
        as_of = _timestamp(row.get("as_of"))
        close = _finite_number(row.get("close"))
        volume = _finite_number(row.get("volume"))
        if as_of is None or close is None or close <= 0 or volume is None or volume < 0:
            blockers.append("market_history_row_invalid")
            continue
        sessions[as_of.date().isoformat()] = (as_of, close, volume)
    parsed_rows = list(sessions.values())
    if not parsed_rows:
        blockers.append("market_history_missing")
    elif len(parsed_rows) < 20:
        blockers.append("market_history_insufficient_sessions")
    if blockers:
        return {"status": "quarantined", "blockers": sorted(set(blockers))}

    parsed_rows.sort(key=lambda row: row[0])
    latest_time, latest_close, _ = parsed_rows[-1]
    trailing = parsed_rows[-20:]
    adv20 = sum(row[2] for row in trailing) / len(trailing)
    # yfinance 日線把當日 forming bar 標成交易所午夜；換算 UTC 在清晨時段可能略
    # 超前抓取時刻。觀測不可能晚於我們抓到它的時間——夾到 fetched_at，避免下游
    # 誤判 market_timestamp_future。
    fetched_time = _timestamp(fetched_at)
    if fetched_time is not None and latest_time > fetched_time:
        latest_time = fetched_time
    return {
        "status": "observed",
        "ticker": ticker.strip().upper(),
        "price": latest_close,
        "currency": currency,
        "adv20": adv20,
        "as_of": latest_time.isoformat(),
        "fetched_at": fetched_at,
        "unit_status": "ok",
        "source": source,
        "blockers": [],
    }


def get_tradeability_snapshot(ticker: str, currency: str) -> dict[str, Any]:
    """用 yfinance history 取可追溯的 20-session price/ADV 快照。"""

    try:
        import yfinance as yf
    except ImportError:
        return {"status": "unavailable", "blockers": ["yfinance_unavailable"]}
    fetched_at = datetime.now(timezone.utc).isoformat()
    provider_symbol = yfinance_symbol(ticker)
    try:
        history = yf.Ticker(provider_symbol).history(period="2mo", auto_adjust=False)
        rows = [
            {
                "as_of": index.to_pydatetime().isoformat(),
                "close": row.get("Close"),
                "volume": row.get("Volume"),
            }
            for index, row in history.iterrows()
        ]
    except Exception as exc:
        return {
            "status": "unavailable",
            "blockers": ["market_history_unavailable"],
            "failure_class": classify_access_failure(exc),
        }
    return build_tradeability_snapshot(
        ticker=ticker,
        currency=currency,
        rows=rows,
        fetched_at=fetched_at,
        source=f"yfinance://history/{provider_symbol}",
    )


def build_fx_snapshot(
    *,
    pair: str,
    rows: Iterable[Mapping[str, Any]],
    fetched_at: str,
    source: str,
) -> dict[str, Any]:
    """由 exact base/quote history 建立可追溯 FX observation。"""

    parts = pair.split("/")
    if (
        len(parts) != 2
        or any(len(part) != 3 or not part.isupper() for part in parts)
        or _timestamp(fetched_at) is None
        or not isinstance(source, str)
        or not source.strip()
    ):
        return {"status": "malformed", "blockers": ["fx_metadata_invalid"]}
    observations: list[tuple[datetime, float]] = []
    for row in rows:
        as_of = _timestamp(row.get("as_of"))
        rate = _finite_number(row.get("rate"))
        if as_of is not None and rate is not None and rate > 0:
            observations.append((as_of, rate))
    if not observations:
        return {"status": "missing", "pair": pair, "blockers": ["fx_history_missing"]}
    observations.sort(key=lambda item: item[0])
    as_of, rate = observations[-1]
    # 同 tradeability：夾 as_of 到不超過 fetched_at，避免 forming-bar 午夜時戳
    # 在清晨時段被誤判 future。
    fetched_time = _timestamp(fetched_at)
    if fetched_time is not None and as_of > fetched_time:
        as_of = fetched_time
    return {
        "status": "observed",
        "pair": pair,
        "rate": rate,
        "as_of": as_of.isoformat(),
        "fetched_at": fetched_at,
        "source": source,
        "blockers": [],
    }


def get_fx_snapshot(pair: str, evaluation_at: str) -> dict[str, Any]:
    """用 yfinance exact pair ticker 取得 FX；不倒數或猜測方向。"""

    del evaluation_at
    parts = pair.split("/")
    if len(parts) != 2 or any(len(part) != 3 or not part.isupper() for part in parts):
        return {"status": "malformed", "blockers": ["fx_pair_invalid"]}
    try:
        import yfinance as yf
    except ImportError:
        return {"status": "unavailable", "pair": pair, "blockers": ["yfinance_unavailable"]}
    symbol = f"{parts[0]}{parts[1]}=X"
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        history = yf.Ticker(symbol).history(period="5d", auto_adjust=False)
        rows = [
            {"as_of": index.to_pydatetime().isoformat(), "rate": row.get("Close")}
            for index, row in history.iterrows()
        ]
    except Exception as exc:
        return {
            "status": "unavailable",
            "pair": pair,
            "blockers": ["fx_history_unavailable"],
            "failure_class": classify_access_failure(exc),
        }
    return build_fx_snapshot(
        pair=pair,
        rows=rows,
        fetched_at=fetched_at,
        source=f"yfinance://fx/{symbol}",
    )


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
