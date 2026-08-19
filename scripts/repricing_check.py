"""已被定價了嗎：把追蹤期間的股價變化拆成「估值倍數」與「獲利預估」兩部分（唯讀）。

## 為什麼需要這個

`AGENTS.md` 的 Lane Memo 規格把 **variant perception 列為必填**，操作定義是
「當前股價／估值隱含的假設是 X，本 thesis 認為真實情況會是 Y」。但系統**沒有任何欄位
或報表在回答它**——`blind-spot-audit` 的 A2 lens（反身性／已被定價）因此每次都只能靠
人臨場判斷。2026-08-18 使用者問「COHR 是不是已經被 price in」時，答案是「答不出來」。

## 這不是估值模型，是算術

三個都是 Engine C 既有欄位的確定性分解，**不預測任何東西**：

1. **股價變化** vs **forward P/E 變化**。兩者相除即隱含的獲利預估修正：
   `(1+價格變化) / (1+倍數變化) - 1`。價格漲而倍數降 → 獲利預估上修得比股價快
   （較不像已被定價）；價格漲且倍數也漲 → 多重擴張（較像已被定價）。
2. **現價 vs 分析師目標均值**。價格超過目標均值是「賣方共識已被走完」的直接訊號。
3. **毛利率**同期變化，作為基本面是否同步改善的對照。

## 明確的限制（隨輸出常駐）

- 分析師目標會**追著股價跑**，落後且有偏。它只說「賣方共識在哪」，不說「值多少」。
- forward P/E 來自 provider 的共識 EPS，同樣是共識而非真相。
- **這裡沒有任何一項能證明「便宜」或「貴」。** 它只能回答「市場在這段期間改變了什麼看法」，
  以及「你的 variant perception 是否還有空間」。要主張 variant perception，
  仍必須自己寫出 X 與 Y。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

POINTER = ROOT / "library" / "private" / "runtime_pointer.json"
DECISION_DB = ROOT / "library" / "private" / "decision_lab" / "decision_lab.db"


def _connect_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _anchors() -> dict[str, str]:
    """每檔的追蹤起點＝Shadow 錨點日（Decision Store authority）。"""
    try:
        with _connect_ro(DECISION_DB) as conn:
            rows = conn.execute(
                "SELECT ticker, min(substr(as_of,1,10)) AS d FROM shadow_observations "
                "WHERE status='observed' AND ticker IS NOT NULL GROUP BY ticker"
            ).fetchall()
        return {str(r["ticker"]): str(r["d"]) for r in rows}
    except sqlite3.Error:
        return {}


def _pct(new, old):
    if not isinstance(new, (int, float)) or not isinstance(old, (int, float)) or not old:
        return None
    return new / old - 1.0


def _provider_close(ticker: str) -> tuple[str, float, bool] | None:
    """最新一根**實際 K 線**的 (交易日, 收盤價, 是否尚未收盤)。

    現價取 provider K 線而非 Engine C `financial_snapshots.price`，理由是 **as-of 新鮮度**：
    快照是每日 ETL 執行時的一個點，盤中比對時最新 K 線更貼近當下；兩者在同一交易日收盤後
    應當一致。

    ⚠ **2026-08-19 更正：本 docstring 的初版宣稱 Engine C 那欄「取自 `previousClose`、
    對不上任何收盤，且 ETL 憑空蓋了 `bar_date=2026-08-17`（那天沒開市）」——三點全錯，
    不要再沿用那套說法：**

    - 2026-08-17 是**星期一**，正常交易日；初版寫的「週五 08-14 → 週二 08-18」漏掉了它。
    - `yf.Ticker("COHR").history()` 實測**有** 08-17 那根 K 線，收盤 `351.220001`，
      正是 Engine C 記下的值。
    - `etl_yfinance.fetch_snapshot` 讀的是 `currentPrice`／`regularMarketPrice`；
      `_bar_identity()` 只用 provider 明示的 `regularMarketTime`＋`exchangeTimezoneName`＋
      `marketState`，**不做推斷**，欄位缺就回 `None`。它沒有生成任何日期。

    當時的觸發現象（使用者 08-18 以 316.23 成交、系統顯示 351.22）是 **COHR 當天跌 12.7%**
    （351.22 → 306.43，盤中低 305.50），不是資料污染；「+17% → +33%」則是 as-of 由 08-17
    收盤換成 08-18 盤中的必然差異，不是修正了一個錯誤。

    留下的教訓不是「Engine C 的價格不可信」，而是 L11／L15：**在自己的診斷上要套用跟圖裡
    claim 同一套追源紀律**。當時只要多做一步（`history()` 印出來、或查 08-17 是星期幾），
    整條推論就會停住；沒做那一步，錯誤結論反而被寫進 commit message、ROADMAP 和本檔。
    """
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(period="1mo", auto_adjust=False)["Close"].dropna()
    except Exception:  # noqa: BLE001 — 抓不到就退回 Engine C 並標示
        return None
    if hist.empty:
        return None
    stamp = hist.index[-1]
    # 第三個回傳值＝「這根 bar 的日期是交易所當地的今天」。yfinance 的 index 帶交易所
    # 時區，所以直接跟同一時區的今天比，不必自己推時區。⚠ 它**不等於**「尚未收盤」——
    # 美東晚間跑時當日 bar 早已定案，仍會是 True。要真正判斷收盤與否得看交易時段表或
    # `marketState`，本函式不猜，只回報它查得到的事實。
    try:
        today_there = datetime.now(stamp.tzinfo).date() if stamp.tzinfo else date.today()
    except Exception:  # noqa: BLE001 — 取不到就當作已收盤，不謊報盤中
        today_there = None
    unsettled = today_there is not None and stamp.date() == today_there
    return stamp.date().isoformat(), float(hist.iloc[-1]), unsettled


def _positive_pe(value) -> float | None:
    """只有正的 forward P/E 才能做倍數分解。

    ⚠ 虧損公司的 forward P/E 是負數（實測 AEVA -14、IQE.L -229、SIVE.ST -205）。
    直接相除會得出「倍數變化 +30.6%、隱含獲利預估 -0.0%」這種**無意義卻長得像有意義**
    的數字——與需求鏈那次同一類錯誤（看起來結構化、實際沒有內容）。
    負值一律回 None，讓該列顯示「虧損中」而不是假裝算得出來。
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return float(value) if value > 0 else None


def _fmt(v, suffix="%"):
    return "—" if v is None else (f"{v * 100:+.1f}{suffix}" if suffix == "%" else f"{v:.1f}")


def main() -> int:
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    engine_c = ROOT / "library" / "private" / pointer["engine_c"]
    anchors = _anchors()
    if not anchors:
        print("沒有 Shadow 錨點可用", file=sys.stderr)
        return 1

    rows = []
    with _connect_ro(engine_c) as conn:
        for ticker, anchor in sorted(anchors.items()):
            snaps = conn.execute(
                "SELECT snapshot_date, price, pe_forward, ev_revenue, gross_margin, "
                "       analyst_target_mean "
                "  FROM financial_snapshots WHERE ticker=? AND price IS NOT NULL "
                " ORDER BY snapshot_date",
                (ticker,),
            ).fetchall()
            if len(snaps) < 2:
                continue
            # 錨點日當天或之後的第一筆；Engine C 的覆蓋期可能晚於 Shadow 錨點。
            start = next((s for s in snaps if str(s["snapshot_date"]) >= anchor), snaps[0])
            end = snaps[-1]
            # 現價用 provider 最新 K 線（as-of 較新）；Engine C 提供共識 EPS。
            bar = _provider_close(ticker)
            end_price = bar[1] if bar else end["price"]
            price_source = f"bar@{bar[0]}" if bar else "engine_c(⚠未取得 K 線)"
            price_unsettled = bool(bar and bar[2])

            pe_from, pe_to = _positive_pe(start["pe_forward"]), _positive_pe(end["pe_forward"])
            # forward P/E 與 price 同源（同一份快照）。可還原的是隱含的 forward EPS
            # （= price ÷ pe），再用現價重算倍數，讓兩者的 as-of 對齊。
            if pe_to and end["price"]:
                implied_eps = end["price"] / pe_to
                pe_to = end_price / implied_eps if implied_eps else pe_to
            price_chg = _pct(end_price, start["price"])
            pe_chg = _pct(pe_to, pe_from)
            implied = (
                (1 + price_chg) / (1 + pe_chg) - 1
                if price_chg is not None and pe_chg is not None
                else None
            )
            target = end["analyst_target_mean"]
            upside = _pct(target, end_price) if target else None
            rows.append(
                {
                    "ticker": ticker,
                    "from": str(start["snapshot_date"]),
                    "price_chg": price_chg,
                    "pe_from": pe_from,
                    "pe_to": pe_to,
                    "loss_making": pe_to is None,
                    "pe_chg": pe_chg,
                    "implied_eps": implied,
                    "gm_chg": _pct(end["gross_margin"], start["gross_margin"]),
                    "price": end_price,
                    "price_source": price_source,
                    "price_unsettled": price_unsettled,
                    "target": target,
                    "upside": upside,
                }
            )

    print(f"# 已被定價了嗎（{date.today().isoformat()}）— 唯讀，這是算術不是估值模型\n")
    print("| 標的 | 自 | 股價 | fwd P/E | 倍數變化 | 隱含獲利預估 | 現價 vs 分析師目標 |")
    print("|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: -(x["upside"] if x["upside"] is not None else 9)):
        pe_span = (
            f"{r['pe_from']:.1f}→{r['pe_to']:.1f}"
            if r["pe_from"] and r["pe_to"]
            else "虧損中"
        )
        flag = ""
        if r["upside"] is not None and r["upside"] < 0:
            flag = " 🔴"
        elif r["upside"] is not None and r["upside"] < 0.10:
            flag = " 🟠"
        print(
            f"| {r['ticker']} | {r['from']} | {_fmt(r['price_chg'])} | {pe_span} "
            f"| {_fmt(r['pe_chg'])} | {_fmt(r['implied_eps'])} "
            f"| {_fmt(r['upside'])}{flag} |"
        )

    print("\n**現價來源**（取 provider 最新 K 線，理由見 `_provider_close`）：")
    for r in sorted(rows, key=lambda x: x["ticker"]):
        # 只斷言查得到的事實：這根 bar 的日期就是交易所當地的今天。它是否已過收盤鐘
        # 需要交易時段表或 marketState 才知道，這裡不猜（L12：別讓一個標籤兼講兩件事）。
        note = "（交易所當地今日 bar，可能尚在盤中）" if r["price_unsettled"] else ""
        print(f"- {r['ticker']}：{r['price']:.2f}　{r['price_source']}{note}")

    print(
        "\n**怎麼讀：**\n"
        "- **倍數變化為負、隱含獲利預估為正** → 獲利預估上修得比股價快，"
        "市場還在追基本面，較不像已被定價完畢。\n"
        "- **倍數變化為正且幅度接近股價漲幅** → 這段漲的是多重擴張，不是獲利，"
        "較像敘事已被 price in。\n"
        "- 🔴 現價已高於分析師目標均值｜🟠 剩餘空間不到 10%。\n"
    )
    print(
        "⚠ **限制：** 分析師目標會追著股價跑，落後且有偏；forward P/E 來自共識 EPS，"
        "同樣是共識不是真相。**本表不能證明便宜或貴**——它只說市場這段期間改變了什麼看法。"
        "要主張 variant perception，仍必須自己寫出「股價隱含 X，我認為 Y，催化劑 Z」。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
