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
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from access_failures import classify_access_failure
from identity.currency import resolve_quote_unit, settlement_currency
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
    """由具實際 session timestamp 的 history rows 建立 execution 快照。

    ``currency`` 收的是**交易所報價單位**（Yahoo 對 .L 標的回傳 ``GBp``）。
    快照對外一律換算成 ISO 結算幣別，minor unit 的原始報價另存 ``quote_*``
    欄位留痕；未登記的報價單位 fail closed，不猜測換算倍率。
    """

    blockers: list[str] = []
    sessions: dict[str, tuple[datetime, float, float]] = {}
    if not isinstance(ticker, str) or not ticker.strip():
        blockers.append("market_ticker_invalid")
    unit = resolve_quote_unit(currency)
    if unit is None:
        blockers.append(
            "market_quote_unit_unregistered"
            if isinstance(currency, str) and currency.strip()
            else "market_currency_invalid"
        )
    if _timestamp(fetched_at) is None:
        blockers.append("market_fetched_at_invalid")
    if not isinstance(source, str) or not source.strip():
        blockers.append("market_source_missing")
    # 尚未結算的 trailing bar：provider 已開出當日 row，但 close 還沒發佈（NaN）。
    # 這在非美國交易所很常見（2026-08-05 實測 IQE.L／SIVE.ST／2DG.F 同時中招，
    # 美股沒有）。它不是資料錯誤，只是資料還太年輕；先蒐集起來，等知道最後一根
    # 有效 session 的時間之後再判斷。
    unsettled: list[datetime] = []
    for row in rows:
        as_of = _timestamp(row.get("as_of"))
        if as_of is None:
            # 無法定位的 row 永遠是硬錯誤：不知道它在序列的哪裡，就無法判斷它
            # 是「還沒結算」還是「中間破洞」。
            blockers.append("market_history_row_invalid")
            continue
        close = _finite_number(row.get("close"))
        volume = _finite_number(row.get("volume"))
        if close is None or volume is None:
            unsettled.append(as_of)
            continue
        if close <= 0 or volume < 0:
            # 值有寫出來但超出合理範圍＝資料損毀，不是未結算。維持 fail closed。
            blockers.append("market_history_row_invalid")
            continue
        sessions[as_of.date().isoformat()] = (as_of, close, volume)
    parsed_rows = list(sessions.values())
    latest_valid = max((row[0] for row in parsed_rows), default=None)
    unsettled_trailing = 0
    for as_of in unsettled:
        if as_of.date().isoformat() in sessions:
            continue  # 同一 session 另有完整 row，這筆被取代
        if latest_valid is not None and as_of > latest_valid:
            unsettled_trailing += 1  # 落在序列末端：丟棄，不 quarantine
        else:
            # 落在序列中間＝真的有破洞，整份仍 quarantine。
            blockers.append("market_history_row_invalid")
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
    assert unit is not None
    snapshot = {
        "status": "observed",
        "ticker": ticker.strip().upper(),
        # adv20 是股數，不隨報價單位換算；只有價格要換。
        "price": unit.to_settlement(latest_close),
        "currency": unit.currency,
        "adv20": adv20,
        "as_of": latest_time.isoformat(),
        "fetched_at": fetched_at,
        "unit_status": "ok",
        "source": source,
        "blockers": [],
    }
    if unit.is_minor_unit:
        snapshot["quote_currency"] = unit.quote_code
        snapshot["quote_price"] = latest_close
        snapshot["quote_factor"] = unit.factor
    if unsettled_trailing:
        # 留痕：解釋為什麼 as_of 不是 provider 回傳的最後一根 bar。丟幾根不設上限，
        # 因為丟太多會自動被 20-session 門檻與下游 market_stale 擋下。
        snapshot["unsettled_trailing_rows"] = unsettled_trailing
    return snapshot


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


def get_historical_tradeability_snapshot(
    ticker: str, currency: str, *, before: str
) -> dict[str, Any]:
    """重建 ``before`` 當下應該看到的快照；用於修復遺失的 Shadow 錨點。

    這條路存在的理由是「可重建的事實」與「只有當下才有的真相」必須分開處理：
    decision context 是後者，必須 point-in-time 凍結、永不回寫；Shadow 錨點是
    前者——它只是某個已知時刻的最後一個完整交易日收盤價，用歷史資料可以完整
    重建，不該因為當下一次抓取失敗就永久遺失。

    只採 **UTC 日期嚴格早於 ``before`` 當日** 的 bar：觀測當下該交易日可能尚未
    收盤，取同日 bar 會拿到觀測者當時看不到的價格（實測 co:axt 觀測於
    2026-07-29T00:59Z＝美東 07-28 晚間，同日 bar 會把錨點從 42.76 誤設為 36.97）。
    """

    try:
        import yfinance as yf
    except ImportError:
        return {"status": "unavailable", "blockers": ["yfinance_unavailable"]}
    moment = _timestamp(before)
    if moment is None:
        return {"status": "unavailable", "blockers": ["market_before_invalid"]}
    cutoff = moment.astimezone(timezone.utc).date()
    provider_symbol = yfinance_symbol(ticker)
    try:
        history = yf.Ticker(provider_symbol).history(
            # 往前多取一季，確保過濾後仍滿足 20-session 門檻。
            start=(cutoff - timedelta(days=180)).isoformat(),
            end=cutoff.isoformat(),
            auto_adjust=False,
        )
        rows = [
            {
                "as_of": index.to_pydatetime().isoformat(),
                "close": row.get("Close"),
                "volume": row.get("Volume"),
            }
            for index, row in history.iterrows()
            if index.to_pydatetime().date() < cutoff
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
        # 回填的 fetched_at 用觀測時刻，代表「這是當時該看到的值」，
        # 並讓 build_ 內的 latest_time 夾制自然生效。
        fetched_at=moment.isoformat(),
        source=f"backfill://yfinance/{provider_symbol}@{cutoff.isoformat()}",
    )


def _settlement_pair(pair: Any) -> str | None:
    """把 ``base/quote`` 正規化成結算幣別 pair；任一側無法確定即 None。

    minor unit 只影響價格的計價單位，不影響匯率本身——換算倍率已在行情層套用，
    這裡若再折一次就會重複計算。因此 ``GBp/USD`` 一律正規化成 ``GBP/USD``。
    """

    if not isinstance(pair, str):
        return None
    parts = pair.split("/")
    if len(parts) != 2:
        return None
    settled = [settlement_currency(part) for part in parts]
    if any(code is None for code in settled):
        return None
    return f"{settled[0]}/{settled[1]}"


def build_fx_snapshot(
    *,
    pair: str,
    rows: Iterable[Mapping[str, Any]],
    fetched_at: str,
    source: str,
) -> dict[str, Any]:
    """由 exact base/quote history 建立可追溯 FX observation。"""

    settled = _settlement_pair(pair)
    if (
        settled is None
        or _timestamp(fetched_at) is None
        or not isinstance(source, str)
        or not source.strip()
    ):
        return {"status": "malformed", "blockers": ["fx_metadata_invalid"]}
    pair = settled
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
    settled = _settlement_pair(pair)
    if settled is None:
        return {"status": "malformed", "blockers": ["fx_pair_invalid"]}
    pair = settled
    base, quote = pair.split("/")
    try:
        import yfinance as yf
    except ImportError:
        return {"status": "unavailable", "pair": pair, "blockers": ["yfinance_unavailable"]}
    symbol = f"{base}{quote}=X"
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
