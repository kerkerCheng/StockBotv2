"""
new_listing_history.py — 新登記台股的 Engine C 歷史回補（Phase 7 批次二 E1；failure log #81；使用者 2026-10-21 Q1 A）。

**事發：** 10-18 隨包登記的環宇、光環、台玻、金居、富喬，第一份敘事時月營收 0 個月、季報股數 0 季——三題的「出現在數字裡」與
「已定價①」都量不到；回補 40 個月後自家歷史窗只有 857 天，要 54 個月才夠三年（#39 10-07 波若威等四檔是第一次）。
根因：名冊寫入的流程沒有一步補新條目的歷史，daily 的月營收與股數只 `--sync` 當期——之後登記的檔永遠缺歷史，要人記得補（L14）。

**做什麼：** 名冊寫入的兩條互動路徑完成時呼叫 `backfill_new_listings`：

- `todo complete-registry-batch`：本批新登記的台股（spec 裡寫得出是哪幾家）；
- `todo complete-ra`：入圖包的名冊條目是隨包手寫的，完成時 payload 已壓縮、讀不出新增了哪幾家——所以**從資料判**：
  名冊上的台股裡月營收或季報股數一筆都沒有、而且嘗試紀錄裡沒有的（試過還是沒有的不重打 MOPS，心跳那一行照樣點名）。

回補失敗**不擋名冊寫入**（名冊是 identity authority，歷史是可重建投影，L10）；每次嘗試 append 一行到 `ATTEMPT_LOG`，
收據逐檔寫補到幾個月、幾季、三年窗滿了沒（INV-3）。呼叫端是互動 session（持 session writer lock），不進 daily——月營收與
季報股數照 OPERATIONS 的判準是互動式入口。日韓（.T／.KS）不在這裡：EDINET／OpenDART 是另外兩個入口。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parent.parent
ATTEMPT_LOG = ROOT / "library" / "private" / "engine_c" / "new_listing_backfill.jsonl"
#: 回補長度：10-18 實測 40 個月不夠三年窗（857 天），54 個月才夠（TTM 要先湊 12 個月、可用日是次月 10 日）。
MONTHS = 54
QUARTERS = 20
#: 三年窗與容許短缺——與 `alpha.three_questions` 的自家歷史窗同一個口徑（窗 3 年、短缺 30 天內不算不滿）。
WINDOW_DAYS = 365 * 3
WINDOW_TOLERANCE_DAYS = 30
TAIWAN_SUFFIXES = (".TW", ".TWO")


def taiwan_tickers(tickers: Iterable[Any]) -> list[str]:
    return sorted({str(t).strip().upper() for t in tickers if t and str(t).strip().upper().endswith(TAIWAN_SUFFIXES)})


def _add_months(month: str, n: int) -> str:
    year, mon = int(month[:4]), int(month[5:7])
    total = year * 12 + (mon - 1) + n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def history_window(conn: Any, ticker: str, *, today: date) -> dict[str, Any]:
    """一檔台股在 Engine C 的歷史夠不夠三年窗：月營收（第一個 TTM 的可用日）與季報股數（最早一季核對過的可用日）。"""
    from engine_c.monthly_revenue import disclosure_deadline
    from engine_c.tw_share_capital import ensure_share_capital_schema

    ensure_share_capital_schema(conn)
    first_month, months = conn.execute(
        "SELECT MIN(data_month), COUNT(DISTINCT data_month) FROM monthly_revenue_observations WHERE ticker = ?",
        (ticker,)).fetchone()
    first_shares, quarters = conn.execute(
        "SELECT MIN(available_on), COUNT(DISTINCT period_end) FROM tw_share_capital_observations "
        "WHERE ticker = ? AND cross_check_status = 'ok'", (ticker,)).fetchone()
    need = (today - timedelta(days=WINDOW_DAYS - WINDOW_TOLERANCE_DAYS)).isoformat()
    first_ttm = disclosure_deadline(_add_months(str(first_month), 11)) if first_month else None
    return {"months": int(months or 0), "quarters": int(quarters or 0),
            "monthly_full": bool(first_ttm and first_ttm <= need),
            "shares_full": bool(first_shares and str(first_shares)[:10] <= need)}


def attempted(log_path: Path = ATTEMPT_LOG) -> set[str]:
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    out: set[str] = set()
    for line in lines:
        try:
            out.update(json.loads(line).get("tickers") or ())
        except ValueError:
            continue
    return out


def candidates_without_history(conn: Any, *, today: date, registered: Iterable[str] | None = None,
                               log_path: Path = ATTEMPT_LOG) -> list[str]:
    """名冊上的台股裡，月營收或季報股數一筆都沒有、而且沒試過的。"""
    if registered is None:
        from engine_c.monthly_revenue import registry_taiwan_tickers

        registered = registry_taiwan_tickers()
    tried = attempted(log_path)
    out = []
    for ticker in taiwan_tickers(registered):
        if ticker in tried:
            continue
        window = history_window(conn, ticker, today=today)
        if window["months"] == 0 or window["quarters"] == 0:
            out.append(ticker)
    return out


def backfill_new_listings(tickers: Iterable[Any] | None, *, reason: str, conn: Any = None,
                          monthly: Callable[..., dict[str, Any]] | None = None,
                          shares: Callable[..., dict[str, Any]] | None = None, today: date | None = None,
                          log_path: Path = ATTEMPT_LOG) -> dict[str, Any]:
    """對 `tickers`（None＝`candidates_without_history`）回補月營收 54 個月、季報股數 20 季。**任何失敗都只寫進收據，不 raise。**"""
    today = today or date.today()
    own_conn = conn is None
    if own_conn:
        from engine_c.db import get_conn

        conn = get_conn()
    try:
        chosen = (candidates_without_history(conn, today=today, log_path=log_path) if tickers is None
                  else taiwan_tickers(tickers))
        if not chosen:
            return {"outcome": "nothing_to_do", "reason": reason, "tickers": []}
        if monthly is None:
            from engine_c.monthly_revenue import backfill as monthly
        if shares is None:
            from engine_c.tw_share_capital import backfill as shares
        errors: list[str] = []
        failed: dict[str, int] = {}
        for label, fn, n in (("monthly_revenue", monthly, MONTHS), ("tw_share_capital", shares, QUARTERS)):
            try:
                report = fn(conn, n, tickers=chosen, today=today)
                failed[label] = len(report.get("failed") or ())
            except Exception as exc:  # noqa: BLE001 — 名冊已寫，歷史補不到只記下來（INV-3），不擋
                errors.append(f"{label}：{type(exc).__name__}: {exc}"[:300])
        per = {t: history_window(conn, t, today=today) for t in chosen}
    finally:
        if own_conn:
            conn.close()
    receipt = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "reason": reason, "tickers": chosen,
               "months_requested": MONTHS, "quarters_requested": QUARTERS, "fetch_failures": failed, "errors": errors,
               "per_ticker": per,
               "short_of_window": sorted(t for t, w in per.items() if not (w["monthly_full"] and w["shares_full"]))}
    receipt["outcome"] = "error" if errors else "backfilled"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    return receipt


def window_shortfall(conn: Any, tickers: Iterable[str], *, today: date) -> dict[str, list[str]]:
    """心跳用：三年窗不滿的台股（月營收、季報股數各一張）。剛上市的公司也會在這裡——那是事實，不是缺漏，照樣點名。"""
    monthly, shares = [], []
    for ticker in taiwan_tickers(tickers):
        window = history_window(conn, ticker, today=today)
        if window["months"] and not window["monthly_full"]:
            monthly.append(ticker)
        if window["quarters"] and not window["shares_full"]:
            shares.append(ticker)
    return {"monthly": monthly, "shares": shares}


__all__ = ["ATTEMPT_LOG", "MONTHS", "QUARTERS", "backfill_new_listings", "candidates_without_history",
           "history_window", "taiwan_tickers", "window_shortfall"]
