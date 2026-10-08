"""FRED（聖路易聯準銀行）的日序列 CSV——個股頁 S3b（2026-10-08）的歷史匯率來源。

匯率用聯準會 H.10 的紐約中午買入匯率（例：`DEXTAUS`＝一美元換幾元台幣）：官方、公開、不用金鑰、任何人重抓都得到同一個數
（L10：可重建投影）。H.10 每週一公布前一週的日資料（週一是聯邦假日就延到週二），讀取端用的公布上界是
`engine_c.history.FX_PUBLICATION_LAG_DAYS`（10 天，理由寫在那裡；INV-6）——本檔只抓，不判斷何時可知。

只抓、不判讀、不換算。抓不到就 raise——**不回空清單**（空清單會被下游讀成「沒有匯率」）；FRED 用 `.` 表示那天沒有報價
（美國假日），那一天就不是觀測（照實跳過、計數交給呼叫端）。
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request
from datetime import date

CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={start}"


class FredUnavailable(RuntimeError):
    """FRED 取不到或格式不是預期的——呼叫端記缺席，不印成「沒有匯率」。"""


def parse_csv(text: str, series_id: str) -> tuple[list[tuple[date, float]], int]:
    """FRED CSV → `([(日期, 值)], 沒有報價的天數)`。表頭不是 `observation_date,<series>`（或舊的 `DATE,<series>`）就 raise。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0].split(",")[-1].strip() != series_id or lines[0].split(",")[0] not in ("observation_date", "DATE"):
        raise FredUnavailable(f"FRED {series_id} 的表頭不是預期的（{lines[0][:60] if lines else '空的'}）")
    out: list[tuple[date, float]] = []
    blanks = 0
    for line in lines[1:]:
        day, _, value = line.partition(",")
        if value.strip() in ("", "."):
            blanks += 1
            continue
        try:
            out.append((date.fromisoformat(day.strip()), float(value)))
        except ValueError as exc:
            raise FredUnavailable(f"FRED {series_id} 有一列讀不懂：{line[:60]}") from exc
    return out, blanks


def fetch_series(series_id: str, *, start: date, timeout: float = 30.0, retries: int = 2) -> tuple[list[tuple[date, float]], int]:
    """抓一條日序列（`start` 起）。回 `parse_csv` 的結果；取不到就 raise。"""
    url = CSV_URL.format(series=series_id, start=start.isoformat())
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "StockBotv2 research (local, read-only)"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return parse_csv(resp.read().decode("utf-8"), series_id)
        except FredUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001
            last = exc
        if attempt < retries:
            time.sleep(1.0 + attempt)
    raise FredUnavailable(f"FRED {series_id} 取不到：{type(last).__name__}: {last}")


__all__ = ["CSV_URL", "FredUnavailable", "fetch_series", "parse_csv"]
