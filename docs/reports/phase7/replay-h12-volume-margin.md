# Phase 7 回放 — H12 量的拐點＋毛利率同時往上（台股全市場，事件月 2015–2022）

> **性質：回放報告（評估檔）。** 假說、量法與殺死條件預先登記在 [`registration.md`](registration.md)「2026-10-06｜新假說 H12」（commit 45e9453a，早於本報告的任何計算）。
> 起因：H11 削弱但兩邊尾巴更肥（[`replay-h11-volume-inflection.md`](replay-h11-volume-inflection.md)）；使用者 2026-10-06「H11 登記」。只讀公開資料，不改任何 ledger、不寫 Engine C。
> 執行：2026-10-06（台北）。月營收＝MOPS 歷史頁（上市＋上櫃、國內＋國外）；毛利率＝MOPS 綜合損益表彙總（`ajax_t163sb04`，合併、一般業版型、累計數相減成單季、可知日＝法定期限）；價格＝yfinance 月線（還原權息）。

## 一句話

**削弱**：事件當時毛利率同時往上（≥ +3 個百分點）的那組，12 個月內曾達 2 倍 9.0%，不高於其餘事件的 9.2%；6 個月內先跌 30% 以上 12.0%，反而高於 8.8%。前後兩段方向一樣。「量的拐點＋毛利率同時往上」分不開翻倍與先崩，不進 lead triage 的問句。

## 結果

| 組 | n | 12 個月內曾達 2 倍 | 6 個月內先跌 30% 以上 | 超額中位數 | 超額平均 |
|---|---|---|---|---|---|
| A：量＋毛利率 ≥ +3pp | 709 | 9.0% | 12.0% | -8.7% | +1.5% |
| B：量、毛利率 < +3pp | 1,071 | 9.2% | 8.8% | -3.3% | +10.2% |
| A 2015–2018 | 207 | 7.2% | 13.5% | -8.8% | +0.2% |
| B 2015–2018 | 409 | 7.3% | 12.5% | -2.2% | +7.4% |
| A 2019–2022 | 502 | 9.8% | 11.3% | -8.7% | +2.0% |
| B 2019–2022 | 662 | 10.3% | 6.5% | -3.9% | +12.0% |
| A（門檻 0） | 1,059 | 9.9% | 10.6% | -6.0% | +5.0% |
| B（門檻 0） | 721 | 7.9% | 9.3% | -3.6% | +9.2% |
| A（門檻 +5pp） | 538 | 8.2% | 12.6% | -11.2% | +0.1% |
| B（門檻 +5pp） | 1,242 | 9.5% | 8.9% | -3.7% | +9.6% |
| H11 定義的事件（新期間） | 2,079 | 10.2% | 9.9% | -4.4% | +10.2% |
| H11 定義的對照（新期間） | 145,744 | 8.1% | 7.2% | +0.0% | +11.1% |

判讀線（預先登記）：① A、B 各 ≥ 30 ✓ ② 曾達 2 倍 A > B ✗ ③ 先跌 30% A ≤ B ✗ ④ 前後兩段 ② 方向一致 ✗ → **削弱**。

## 描述（不進判讀）

- **毛利率往上越多，先崩越多**：門檻 +5pp 時 A 先跌 30% 12.6% 對 B 8.9%、超額中位數 -11.2% 對 -3.7%。只有門檻 0（毛利率「有往上」就算）時 A 的曾達 2 倍較高（9.9% 對 7.9%），但先崩也較高（10.6% 對 9.3%）。
- **H11 在新期間重現**：事件 n＝2,079，超額中位數 -4.4% 對對照 +0.0%；曾達 2 倍 10.2% 對 8.1%、先跌 30% 9.9% 對 7.2%——2023–2025 看到的「中位數不贏、兩邊尾巴都更肥」在 2015–2022 也成立。
- 和個股頁的發現一致（`docs/brainstorms/2026-10-05-stock-page-schema.md` F36）：毛利率大升常是週期高點，不是「一層薄」的定價權——聯亞 2021Q1 54% → 2021Q4 24%（三季），2023Q3 更到 −20%；AXT 2022Q3 42.0% → 2023Q3 10.7%（四季）。
- 要從量的拐點裡挑出右尾，**財務數字的條件到這裡為止**：量（H11）與量＋毛利（H12）兩個都在全市場測過、都分不開。剩下的候選是圖的條件（一層薄、需求錨），只能前向測——圖是 2026 年才建的，拿它回頭測等於先知道答案。
- 計數：{"codes": 1870, "rows": 147823, "events": 2079, "control": 145744, "dropped_no_price": {"event": 50, "control": 1603}, "gm_status": {"有": 1780, "毛利率基期太小": 23, "沒有毛利率": 276}, "base_too_small_months": 7862}

## 偏差標註

1. 價格：月線第一輪被 yfinance **限流**，600 個代號兩個後綴都沒價——若照用會把近三分之一的公司當成「沒有價格」剔除。補抓（`h12_fill_px.py`，分清楚「限流」與「Yahoo 沒有」）找回 592 個代號×後綴、仍缺 8 個代號（Yahoo 沒有資料，非限流）。剔除的列：事件 50、對照 1,603。已下市的公司 yfinance 大多仍有歷史月線，存活者偏差比預期小，但不是零。
2. KY（外國）公司的季報期限照一般業算，可能提早幾天看到。3. 回補拿到的是 MOPS **現在**的版本——重編或逾期申報的季仍照原期限當可知。
4. 「事件當時已知的最近一季」常早於量的拐點（例：3 月成立的事件，已知的是前一年第四季）——這是「當時看得到什麼」的代價。
5. 毛利率是合併報表全公司，不分押的那一塊。6. 月底收盤算「曾達 2 倍／先跌 30%」，不看盤中。7. 2015–2022 含 2020–2021 多頭與 2022 空頭，結論只適用這段環境。
8. 可知日抽查（`h12_pit_check.py`）：2,079 個事件裡，用到的那一季法定期限不早於進場月月底的 0 個；一筆手算與腳本一致。

## 腳本（逐字）

### h12_fetch.py

```python
"""H12 資料抓取（registration.md 2026-10-06 追加，登記 commit 45e9453a 早於本腳本）。只抓、不算任何結果。
1. MOPS 歷史月營收 2014-10..2022-12（上市＋上櫃、國內＋國外）→ h12_cache/rev_*.json
2. MOPS 綜合損益表彙總 ajax_t163sb04 2013Q1..2022Q4（上市＋上櫃）→ h12_cache/is_*.json（一般業版型：代號 → 累計營收、累計營業毛利）
3. yfinance 月線（還原權息）2014-12..2024-02，每個代號 .TW 與 .TWO 都抓 → h12_cache/px_TW.json、px_TWO.json
不寫任何 repo 檔、不寫 Engine C。"""
import json
import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
sys.path.insert(0, r"C:\Users\Cheng\code\StockBotv2")
from fetchers.mops_open_data import fetch_monthly_revenue_month  # noqa: E402
from fetchers.utils import build_headers  # noqa: E402

CACHE = HERE / "h12_cache"
CACHE.mkdir(exist_ok=True)
REV_MONTHS = [(y, m) for y in range(2014, 2023) for m in range(1, 13) if (2014, 10) <= (y, m) <= (2022, 12)]
IS_QUARTERS = [(y, q) for y in range(2013, 2023) for q in (1, 2, 3, 4)]
IS_URL = "https://mopsov.twse.com.tw/mops/web/ajax_t163sb04"
SEG = {"twse": "sii", "tpex": "otc"}
TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.I | re.S)
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
TAG = re.compile(r"<[^>]+>")
CODE = re.compile(r"^\d{4,6}$")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def txt(s):
    return TAG.sub("", s).replace("&nbsp;", " ").strip()


def num(s):
    s = (s or "").replace(",", "").strip()
    if s in ("", "--", "-", "N/A"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


# ---------- 1. 月營收 ----------
fails = []
for market in ("twse", "tpex"):
    for y, m in REV_MONTHS:
        f = CACHE / f"rev_{market}_{y}-{m:02d}.json"
        if f.exists():
            continue
        for attempt in range(4):
            try:
                rows = fetch_monthly_revenue_month(market, y, m)
                f.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 3:
                    fails.append(f"rev {market} {y}-{m:02d}: {exc}")
                time.sleep(5 * (attempt + 1))
        time.sleep(1.0)
    log("月營收", market, "完成；失敗", len(fails))

# ---------- 2. 損益表彙總 ----------
for market in ("twse", "tpex"):
    for y, q in IS_QUARTERS:
        f = CACHE / f"is_{market}_{y}Q{q}.json"
        if f.exists():
            continue
        data = {"encodeURIComponent": "1", "step": "1", "firstin": "1", "off": "1", "isQuery": "Y",
                "TYPEK": SEG[market], "year": str(y - 1911), "season": f"{q:02d}"}
        body = None
        for attempt in range(4):
            try:
                r = requests.post(IS_URL, data=data, headers=build_headers(), timeout=90)
                if r.status_code == 200 and len(r.content) > 5000:
                    body = r.content.decode("utf-8", errors="replace")
                    break
                raise RuntimeError(f"status {r.status_code} bytes {len(r.content)}")
            except Exception as exc:  # noqa: BLE001
                if attempt == 3:
                    fails.append(f"is {market} {y}Q{q}: {exc}")
                time.sleep(8 * (attempt + 1))
        if body is None:
            continue
        general, rejected, headers = {}, {}, []
        for t in TABLE.findall(body):
            trs = ROW.findall(t)
            if not trs:
                continue
            head = [txt(c) for c in CELL.findall(trs[0])]
            idx = {h: i for i, h in enumerate(head)}
            codes = [txt((CELL.findall(tr) or [""])[0]) for tr in trs[1:]]
            n_codes = sum(1 for c in codes if CODE.match(c))
            if not n_codes:
                continue
            if "公司代號" in idx and "營業收入" in idx and "營業毛利（毛損）" in idx:
                headers.append(len(head))
                for tr in trs[1:]:
                    cells = [txt(c) for c in CELL.findall(tr)]
                    if not cells or not CODE.match(cells[0]) or len(cells) != len(head):
                        continue
                    general[cells[0]] = [num(cells[idx["營業收入"]]), num(cells[idx["營業毛利（毛損）"]])]
            else:
                rejected[f"{len(head)}欄:{'｜'.join(head[2:4])}"] = n_codes
        f.write_text(json.dumps({"general": general, "rejected": rejected, "general_header_cols": headers},
                                ensure_ascii=False), encoding="utf-8")
        log("損益表", market, f"{y}Q{q}", "一般業", len(general), "其他版型", rejected)
        time.sleep(2.0)

# ---------- 3. 月線 ----------
codes = set()
for f in CACHE.glob("rev_*.json"):
    for r in json.loads(f.read_text(encoding="utf-8")):
        c = r.get("company_code")
        if c and CODE.match(c):
            codes.add(c)
codes = sorted(codes)
log("代號數", len(codes))
import yfinance as yf  # noqa: E402

for suffix in (".TW", ".TWO"):
    out_f = CACHE / f"px_{suffix.strip('.')}.json"
    if out_f.exists():
        continue
    px = {}
    tickers = [c + suffix for c in codes]
    for i in range(0, len(tickers), 120):
        chunk = tickers[i:i + 120]
        df = None
        for attempt in range(3):
            try:
                df = yf.download(chunk, start="2014-12-01", end="2024-03-01", interval="1mo", auto_adjust=True,
                                 group_by="ticker", threads=True, progress=False)
                break
            except Exception as exc:  # noqa: BLE001
                log("yfinance 重試", suffix, i, exc)
                time.sleep(15)
        if df is None:
            fails.append(f"px {suffix} chunk {i}")
            continue
        for t in chunk:
            try:
                s = df[t]["Close"].dropna() if len(chunk) > 1 else df["Close"].dropna()
            except Exception:  # noqa: BLE001
                continue
            if len(s):
                px[t[: -len(suffix)]] = {d.strftime("%Y-%m"): float(v) for d, v in s.items()}
        log("月線", suffix, min(i + 120, len(tickers)), "/", len(tickers), "有價", len(px))
        time.sleep(2)
    out_f.write_text(json.dumps(px), encoding="utf-8")

(CACHE / "fetch_failures.json").write_text(json.dumps(fails, ensure_ascii=False, indent=1), encoding="utf-8")
log("全部完成；失敗", len(fails), fails[:10])
```

### h12_fill_px.py

```python
"""H12 月線補抓：第一輪被 yfinance 限流的代號不能當成「沒有價格」（INV-3：兩種沒有不同形）。
只重抓兩個後綴都沒有價的代號；小批次、限流就退避重試；每個代號最後記成「有價／Yahoo 沒有（非限流的錯誤）／仍被限流」。"""
import json
import time
from pathlib import Path

import yfinance as yf
import yfinance.shared as yf_shared

HERE = Path(__file__).parent
CACHE = HERE / "h12_cache"
time.sleep(20)  # 第一輪限流已過約 6 分鐘


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


codes = set()
for f in CACHE.glob("rev_*.json"):
    codes.update(r["company_code"] for r in json.loads(f.read_text(encoding="utf-8")) if r.get("company_code"))
px = {sfx: json.loads((CACHE / f"px_{sfx}.json").read_text(encoding="utf-8")) for sfx in ("TW", "TWO")}
missing = sorted(codes - set(px["TW"]) - set(px["TWO"]))
log("兩個後綴都沒價的代號", len(missing))
status: dict[str, str] = {}
pending = [(c, sfx) for c in missing for sfx in ("TW", "TWO")]
attempt = 0
while pending and attempt < 6:
    attempt += 1
    still = []
    for i in range(0, len(pending), 30):
        chunk = pending[i:i + 30]
        tickers = [f"{c}.{sfx}" for c, sfx in chunk]
        try:
            df = yf.download(tickers, start="2014-12-01", end="2024-03-01", interval="1mo", auto_adjust=True,
                             group_by="ticker", threads=False, progress=False)
        except Exception as exc:  # noqa: BLE001
            log("下載例外", exc)
            still.extend(chunk)
            time.sleep(30)
            continue
        errors = dict(getattr(yf_shared, "_ERRORS", {}) or {})
        for (c, sfx), t in zip(chunk, tickers):
            err = str(errors.get(t, ""))
            try:
                s = df[t]["Close"].dropna() if len(tickers) > 1 else df["Close"].dropna()
            except Exception:  # noqa: BLE001
                s = None
            if s is not None and len(s):
                px[sfx][c] = {d.strftime("%Y-%m"): float(v) for d, v in s.items()}
                status[f"{c}.{sfx}"] = "有價"
            elif "Rate limit" in err or "Too Many Requests" in err:
                still.append((c, sfx))
                status[f"{c}.{sfx}"] = "仍被限流"
            else:
                status[f"{c}.{sfx}"] = "Yahoo 沒有：" + (err[:60] or "空回應")
        time.sleep(6)
    log(f"第 {attempt} 輪：重抓 {len(pending)}、仍被限流 {len(still)}")
    pending = still
    if pending:
        time.sleep(60 * attempt)
for sfx in ("TW", "TWO"):
    (CACHE / f"px_{sfx}.json").write_text(json.dumps(px[sfx]), encoding="utf-8")
(CACHE / "px_fill_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=0), encoding="utf-8")
final_missing = sorted(codes - set(px["TW"]) - set(px["TWO"]))
limited = sorted({k.split(".")[0] for k, v in status.items() if v == "仍被限流"})
log("補完：兩邊都沒價", len(final_missing), "其中仍被限流", len(limited))
```

### h12_compute.py

```python
"""H12 計算（docs/reports/phase7/registration.md 2026-10-06 追加，登記 commit 45e9453a 早於本腳本與任何結果）。
唯讀：只讀 h12_cache/（h12_fetch.py、h12_fill_px.py 抓的），結果寫 h12_result.json。不寫任何 repo 檔、不寫 Engine C。
事件、進出場、超額照 H11 腳本（r2_base_rate.py）逐字；新增的只有毛利率分組。"""
import json
import sys
from datetime import date
from pathlib import Path
from statistics import mean, median

HERE = Path(__file__).parent
CACHE = HERE / "h12_cache"
sys.path.insert(0, r"C:\Users\Cheng\code\StockBotv2")
from engine_c.tw_share_capital import statutory_deadline  # noqa: E402

MIN_BASE = 10_000          # 去年同月營收 < 1,000 萬元（千元）不判——同 H11
MIN_Q_REV = 30_000         # 單季營收 < 3,000 萬元（千元）＝毛利率基期太小
GM_THR = 3.0               # 百分點（登記的主門檻）
EVENT_MONTHS = [(y, m) for y in range(2015, 2023) for m in range(1, 13)]

# ---------- 月營收（以公司代號串，轉板前後接起來）----------
panel: dict[str, dict[str, tuple]] = {}
for f in sorted(CACHE.glob("rev_*.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        c = r.get("company_code")
        if not c:
            continue
        cur, ya, yoy = r.get("revenue_current"), r.get("revenue_year_ago"), r.get("change_yoy_pct")
        if yoy is None and cur is not None and ya:
            yoy = (cur / ya - 1) * 100
        rec = (None if yoy is None else yoy / 100, ya)
        prev = panel.setdefault(c, {}).get(r["data_month"])
        if prev is None or prev[0] is None:
            panel[c][r["data_month"]] = rec


def mkey(y, m):
    while m > 12:
        y, m = y + 1, m - 12
    while m < 1:
        y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"


def cond(c, y, m, thr):
    vals = []
    for k in (-2, -1, 0):
        rec = panel[c].get(mkey(y, m + k))
        if rec is None or rec[0] is None or rec[1] is None or rec[1] < MIN_BASE:
            return None
        vals.append(rec[0])
    return all(v > thr for v in vals)


# ---------- 價格：先上市、缺進場或出場月再上櫃 ----------
px = {sfx: json.loads((CACHE / f"px_{sfx}.json").read_text(encoding="utf-8")) for sfx in ("TW", "TWO")}


def series_for(c, e_k, x_k):
    for sfx in ("TW", "TWO"):
        p = px[sfx].get(c)
        if p and e_k in p and x_k in p:
            return p
    return None


# ---------- 損益表：累計 → 單季 ----------
cum: dict[tuple, dict[str, list]] = {}
for f in sorted(CACHE.glob("is_*.json")):
    _, _, yq = f.stem.split("_")
    y, q = int(yq[:4]), int(yq[5])
    for code, vals in json.loads(f.read_text(encoding="utf-8"))["general"].items():
        cum.setdefault((y, q), {})[code] = vals


def single_q(code, y, q):
    now = cum.get((y, q), {}).get(code)
    if not now or now[0] is None or now[1] is None:
        return None
    if q == 1:
        return now
    before = cum.get((y, q - 1), {}).get(code)
    if not before or before[0] is None or before[1] is None:
        return None
    return [now[0] - before[0], now[1] - before[1]]


QUARTERS = sorted({k for k in cum})
DEADLINE = {(y, q): date.fromisoformat(statutory_deadline(y, q)) for y, q in QUARTERS}


def month_end(key):
    y, m = int(key[:4]), int(key[5:])
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return date.fromordinal(nxt.toordinal() - 1)


def gm_change(code, entry_key):
    """(Δ百分點 或 None, 狀態, 用的那一季)。最近一季＝法定期限嚴格早於進場月月底的最新一季；那一季缺就是缺，不往前找。"""
    entry_day = month_end(entry_key)
    known = [k for k in QUARTERS if DEADLINE[k] < entry_day]
    if not known:
        return None, "沒有毛利率（期間外）", None
    y, q = max(known)
    this, last = single_q(code, y, q), single_q(code, y - 1, q)
    if this is None or last is None:
        return None, "沒有毛利率", f"{y}Q{q}"
    if this[0] < MIN_Q_REV or last[0] < MIN_Q_REV:
        return None, "毛利率基期太小", f"{y}Q{q}"
    return (this[1] / this[0] - last[1] / last[0]) * 100, "有", f"{y}Q{q}"


# ---------- 事件與對照（同 H11）----------
def build(thr=0.40):
    rows, no_price = [], {"event": 0, "control": 0}
    for c in panel:
        for y, m in EVENT_MONTHS:
            cc = cond(c, y, m, thr)
            if cc is None:
                continue
            prev = cond(c, y, m - 1, thr)
            is_event = cc and prev is not True
            if cc and not is_event:
                continue
            e_k, x_k = mkey(y, m + 1), mkey(y, m + 13)
            p = series_for(c, e_k, x_k)
            if p is None:
                no_price["event" if is_event else "control"] += 1
                continue
            entry = p[e_k]
            path = [p.get(mkey(y, m + k)) for k in range(2, 14)]
            path = [v for v in path if v is not None]
            rows.append({"c": c, "m": mkey(y, m), "entry_m": e_k, "event": is_event, "ret": p[x_k] / entry - 1,
                         "hit2x": any(v >= 2 * entry for v in path), "fall30": any(v <= 0.7 * entry for v in path[:6])})
    by_month: dict[str, list] = {}
    for r in rows:
        by_month.setdefault(r["entry_m"], []).append(r["ret"])
    med = {k: median(v) for k, v in by_month.items()}
    for r in rows:
        r["ex"] = r["ret"] - med[r["entry_m"]]
    for r in rows:
        if r["event"]:
            r["dgm"], r["gm_status"], r["gm_q"] = gm_change(r["c"], r["entry_m"])
    return rows, no_price


def stats(sel):
    if not sel:
        return {"n": 0}
    return {"n": len(sel), "hit2x": round(sum(r["hit2x"] for r in sel) / len(sel), 4),
            "fall30": round(sum(r["fall30"] for r in sel) / len(sel), 4),
            "ex_median": round(median(r["ex"] for r in sel), 4), "ex_mean": round(mean(r["ex"] for r in sel), 4)}


rows, no_price = build()
events = [r for r in rows if r["event"]]
control = [r for r in rows if not r["event"]]


def split(thr, sel):
    a = [r for r in sel if r.get("dgm") is not None and r["dgm"] >= thr]
    b = [r for r in sel if r.get("dgm") is not None and r["dgm"] < thr]
    return a, b


A, B = split(GM_THR, events)
first = [r for r in events if r["m"] < "2019-01"]
second = [r for r in events if r["m"] >= "2019-01"]
A1, B1 = split(GM_THR, first)
A2, B2 = split(GM_THR, second)
sA, sB = stats(A), stats(B)
c1 = sA["n"] >= 30 and sB["n"] >= 30
c2 = c1 and sA["hit2x"] > sB["hit2x"]
c3 = c1 and sA["fall30"] <= sB["fall30"]


def half_ok(a, b):
    if len(a) < 15 or len(b) < 15:
        return False
    return stats(a)["hit2x"] > stats(b)["hit2x"]


c4 = half_ok(A1, B1) and half_ok(A2, B2)
if not c1:
    verdict = "不足（A 或 B 不到 30）"
elif not (c2 and c3):
    verdict = "削弱（" + ("曾達 2 倍 A ≤ B" if not c2 else "") + ("、" if not c2 and not c3 else "") + ("先跌 30% A > B" if not c3 else "") + "）"
elif not c4:
    verdict = "不足（全期成立，但前後兩段方向不一致或某段 n < 15）"
else:
    verdict = "支持（四條全部成立）"

status_counts: dict[str, int] = {}
for r in events:
    status_counts[r["gm_status"]] = status_counts.get(r["gm_status"], 0) + 1
result = {
    "registered_commit": "45e9453a", "verdict": verdict,
    "conditions": {"①A、B 各 ≥ 30": c1, "②曾達 2 倍 A > B": c2, "③先跌 30% A ≤ B": c3, "④前後兩段 ② 方向一致": c4},
    "A_gm_up": sA, "B_not_up": sB,
    "halves": {"2015-2018": {"A": stats(A1), "B": stats(B1)}, "2019-2022": {"A": stats(A2), "B": stats(B2)}},
    "sensitivity": {f"{t:+.0f}pp": {"A": stats(split(t, events)[0]), "B": stats(split(t, events)[1])} for t in (0.0, 5.0)},
    "h11_replication": {"event": stats(events), "control": stats(control)},
    "by_year_n": {str(yy): {"events": sum(1 for r in events if r["m"].startswith(str(yy))),
                            "A": sum(1 for r in A if r["m"].startswith(str(yy))),
                            "B": sum(1 for r in B if r["m"].startswith(str(yy)))} for yy in range(2015, 2023)},
    "counts": {"codes": len(panel), "rows": len(rows), "events": len(events), "control": len(control),
               "dropped_no_price": no_price, "gm_status": status_counts,
               "base_too_small_months": sum(1 for c in panel for (yoy, ya) in panel[c].values() if ya is not None and ya < MIN_BASE)},
}
(HERE / "h12_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=1))
```
