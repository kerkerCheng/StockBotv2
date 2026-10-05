# Phase 7 回放 — H11 月營收「量的拐點」全市場基準率

> **性質：回放報告（評估檔）。** 假說、量法與殺死條件預先登記在 [`registration.md`](registration.md) 檔尾「2026-10-05｜新假說 H11」（commit 2e18b832，早於本報告的任何計算）。
> 起因：個股頁 schema 的獨立審查（`docs/brainstorms/2026-10-05-stock-page-schema.md` §12，F22）——規律 2 在庫內無法否證。只讀公開資料，不改任何 ledger、不寫 Engine C。
> 執行：2026-10-05（台北）；月營收＝MOPS 歷史頁（上市＋上櫃、國內＋國外），價格＝yfinance 月線（還原權息）。

## 一句話

**削弱**：事件組（n＝537）12 個月超額中位數 -1.2%，不高於對照組（n＝36,127，+0.0%）。「連三個月營收年增 > 40%」單獨當 lead 的找法作廢。

## 結果

| 組 | n | 超額中位數 | 超額平均 | 12 個月內曾達 2 倍 | 6 個月內先跌 30% 以上 |
|---|---|---|---|---|---|
| 事件（門檻 40%） | 537 | -1.2% | +26.0% | 15.1% | 14.0% |
| 對照（門檻 40%） | 36,127 | +0.0% | +16.7% | 9.3% | 7.2% |
| 事件 2024 | 307 | -1.8% | +12.2% | 9.4% | 17.3% |
| 對照 2024 | 20,451 | +0.0% | +8.0% | 5.1% | 8.4% |
| 事件 2025 | 230 | -1.1% | +44.5% | 22.6% | 9.6% |
| 對照 2025 | 15,676 | +0.0% | +28.1% | 14.8% | 5.5% |
| 事件（門檻 30%） | 740 | -0.5% | +26.0% | 13.7% | 12.8% |
| 對照（門檻 30%） | 35,302 | +0.0% | +16.5% | 9.2% | 7.1% |
| 事件（門檻 50%） | 395 | -4.4% | +26.5% | 15.2% | 16.2% |
| 對照（門檻 50%） | 36,661 | +0.0% | +17.0% | 9.4% | 7.2% |

## 描述（不進判讀）

- 中位數不贏、兩邊尾巴都更肥：曾達 2 倍與先跌 30% 的比例，事件組都是對照組的約 1.6–2 倍。量的拐點挑出的是「波動大」的股票，不是「中位數會贏」的股票。
- 「右尾比較肥」是看到結果之後才出現的說法，**不能用同一份資料改判**；要測得另外預先登記、用新的期間。
- 三檔錨點的事件月（月、12 個月報酬、超額）：{"3081.TWO": [["2024-09", 0.321, 0.421], ["2025-04", 7.892, 7.853]], "8996.TW": [["2025-04", 3.607, 3.568]], "4979.TWO": [["2025-03", 3.014, 2.979]]}——都在右尾，這正是「只看贏家」會得到的印象。
- 計數：{"tickers": 1980, "with_price": 1980, "rows_40": 36664, "base_too_small_rows": 4485, "revenue_fetch_failures": []}

## 偏差標註

1. discovery lookahead：無（純機械規則、全市場）。2. 選樣：用各月歷史頁當時上市櫃的公司；yfinance 抓不到價格的剔除（本次 0 檔）。
3. 價格是 yfinance 還原價，不是 Engine C 的取價層。4. 期間是 AI 多頭（2024–2026），結論只適用這個環境。5. 只測「量」那一半；「報告後」沒有全市場覆蓋資料，未量。

## 腳本（逐字）

```python
"""H11 基準率回放（docs/reports/phase7/registration.md 檔尾 2026-10-05 追加，先於本腳本 commit 2e18b832）。
唯讀：抓 MOPS 全市場歷史月營收與 yfinance 月線，算「連三月年增 > 40%」事件組 vs 對照組的 12 個月超額。不寫任何 repo 檔、不寫 Engine C。
快取在 scratchpad/r2_cache/；結果寫 r2_result.json。"""
import json
import sys
import time
from datetime import date
from pathlib import Path
from statistics import mean, median

HERE = Path(__file__).parent
sys.path.insert(0, r"C:\Users\Cheng\code\StockBotv2")
from fetchers.mops_open_data import fetch_monthly_revenue_month  # noqa: E402

CACHE = HERE / "r2_cache"
CACHE.mkdir(exist_ok=True)
MONTHS = [(y, m) for y in range(2023, 2027) for m in range(1, 13) if (y, m) <= (2026, 8)]
MIN_BASE = 10_000  # 去年同月營收 < 1,000 萬元（千元單位）不判


def log(*a):
    print(*a, flush=True)


# ---------- 1. 月營收 ----------
fails = []
for market in ("twse", "tpex"):
    for y, m in MONTHS:
        f = CACHE / f"rev_{market}_{y}-{m:02d}.json"
        if f.exists():
            continue
        for attempt in range(3):
            try:
                rows = fetch_monthly_revenue_month(market, y, m)
                f.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    fails.append(f"{market} {y}-{m:02d}: {exc}")
                time.sleep(3 * (attempt + 1))
        time.sleep(1.0)
log("月營收抓取失敗：", fails)

panel = {}  # ticker -> {YYYY-MM: (yoy, base)}
for f in sorted(CACHE.glob("rev_*.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        t = r.get("ticker")
        if not t:
            continue
        cur, ya, yoy = r.get("revenue_current"), r.get("revenue_year_ago"), r.get("change_yoy_pct")
        if yoy is None and cur is not None and ya:
            yoy = (cur / ya - 1) * 100
        panel.setdefault(t, {})[r["data_month"]] = (None if yoy is None else yoy / 100, ya)
log("代號數", len(panel))


def mkey(y, m):
    while m > 12:
        y, m = y + 1, m - 12
    while m < 1:
        y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"


def cond(t, y, m, thr):
    """None＝不判（缺資料或基期太小）；True／False＝成立與否。"""
    vals = []
    for k in (-2, -1, 0):
        rec = panel[t].get(mkey(y, m + k))
        if rec is None or rec[0] is None or rec[1] is None or rec[1] < MIN_BASE:
            return None
        vals.append(rec[0])
    return all(v > thr for v in vals)


# ---------- 2. 月線 ----------
px_file = CACHE / "px_monthly.json"
if px_file.exists():
    px = json.loads(px_file.read_text(encoding="utf-8"))
else:
    import yfinance as yf
    tickers = sorted(panel)
    px = {}
    for i in range(0, len(tickers), 120):
        chunk = tickers[i:i + 120]
        for attempt in range(3):
            try:
                df = yf.download(chunk, start="2023-12-01", end="2026-10-04", interval="1mo", auto_adjust=True,
                                 group_by="ticker", threads=True, progress=False)
                break
            except Exception as exc:  # noqa: BLE001
                log("yfinance 失敗重試", i, exc)
                time.sleep(10)
        for t in chunk:
            try:
                s = df[t]["Close"].dropna() if len(chunk) > 1 else df["Close"].dropna()
            except Exception:  # noqa: BLE001
                continue
            if len(s):
                px[t] = {d.strftime("%Y-%m"): float(v) for d, v in s.items()}
        log("月線進度", min(i + 120, len(tickers)), "/", len(tickers), "有價", len(px))
        time.sleep(2)
    px_file.write_text(json.dumps(px), encoding="utf-8")


# ---------- 3. 事件與對照 ----------
def run(thr):
    rows = []
    for t in panel:
        p = px.get(t)
        if not p:
            continue
        for y, m in [(yy, mm) for yy in (2024, 2025) for mm in range(1, 13) if (yy, mm) <= (2025, 9)]:
            c = cond(t, y, m, thr)
            if c is None:
                continue
            prev = cond(t, y, m - 1, thr)
            is_event = c and prev is not True
            if c and not is_event:
                continue  # 同一段連續成立的後續月份：不進事件、也不進對照
            e_k, x_k = mkey(y, m + 1), mkey(y, m + 13)
            if e_k not in p or x_k not in p:
                continue
            entry = p[e_k]
            path = [p.get(mkey(y, m + k)) for k in range(2, 14)]
            path = [v for v in path if v is not None]
            rows.append({"t": t, "m": mkey(y, m), "entry_m": e_k, "event": is_event, "ret": p[x_k] / entry - 1,
                         "hit2x": any(v >= 2 * entry for v in path),
                         "fall30": any(v <= 0.7 * entry for v in path[:6])})
    by_month = {}
    for r in rows:
        by_month.setdefault(r["entry_m"], []).append(r["ret"])
    med = {k: median(v) for k, v in by_month.items()}
    for r in rows:
        r["ex"] = r["ret"] - med[r["entry_m"]]

    def stats(sel):
        if not sel:
            return {"n": 0}
        return {"n": len(sel), "ex_median": round(median(r["ex"] for r in sel), 4), "ex_mean": round(mean(r["ex"] for r in sel), 4),
                "hit2x": round(sum(r["hit2x"] for r in sel) / len(sel), 4), "fall30": round(sum(r["fall30"] for r in sel) / len(sel), 4)}

    ev = [r for r in rows if r["event"]]
    ct = [r for r in rows if not r["event"]]
    out = {"thr": thr, "event": stats(ev), "control": stats(ct),
           "by_year": {yr: {"event": stats([r for r in ev if r["m"].startswith(yr)]), "control": stats([r for r in ct if r["m"].startswith(yr)])}
                       for yr in ("2024", "2025")},
           "anchors": {a: [(r["m"], round(r["ret"], 3), round(r["ex"], 3)) for r in ev if r["t"] == a] for a in ("3081.TWO", "8996.TW", "4979.TWO")}}
    return out, rows


main, rows40 = run(0.40)
sens = {thr: run(thr)[0] for thr in (0.30, 0.50)}
ev = main["event"]
ct = main["control"]
if ev["n"] < 30:
    verdict = "不足（事件組 n < 30）"
elif ev["ex_median"] <= ct["ex_median"]:
    verdict = "削弱（事件組超額中位數 ≤ 對照組）"
elif ev["hit2x"] > ct["hit2x"]:
    verdict = "支持（超額中位數與曾達 2 倍比例都高於對照組）"
else:
    verdict = "不足（超額中位數較高，但曾達 2 倍比例沒有較高）"
skipped_base = sum(1 for t in panel for (yoy, ya) in panel[t].values() if ya is not None and ya < MIN_BASE)
result = {"registered_commit": "2e18b832", "verdict": verdict, "main": main, "sensitivity": sens,
          "counts": {"tickers": len(panel), "with_price": len(px), "rows_40": len(rows40), "base_too_small_rows": skipped_base,
                     "revenue_fetch_failures": fails}}
(HERE / "r2_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
log(json.dumps({"verdict": verdict, "event": ev, "control": ct, "by_year": main["by_year"], "anchors": main["anchors"],
                "sens30": {k: sens[0.30][k] for k in ("event", "control")}, "sens50": {k: sens[0.50][k] for k in ("event", "control")},
                "counts": result["counts"]}, ensure_ascii=False, indent=1))
```
