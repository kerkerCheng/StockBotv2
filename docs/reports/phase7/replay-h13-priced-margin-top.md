# Phase 7 回放 — H13 量的拐點裡「價在自家三年頂端＋毛利在自家前高」（台股全市場，事件月 2015–2022）

> **性質：回放報告（評估檔）。** 假說、量法與判讀線預先登記在 [`registration.md`](registration.md)「2026-10-07｜新假說 H13」（commit 8d8043df，早於本報告的任何計算）。
> 起因：個股頁 schema 負錨點時光機頁（`docs/brainstorms/2026-10-05-stock-page-schema.md` §15）；使用者 2026-10-07 go（pq2 [731]）。只讀公開資料，不改任何 ledger、不寫 Engine C。
> 執行：2026-10-07（台北）。事件、進出場、結果欄＝H12 抓取快取原檔＋H12 腳本逐字（[`replay-h12-volume-margin.md`](replay-h12-volume-margin.md)）；
> 價＝未還原權息月線（yfinance，分割還原）× EPS 推的股數 ÷ 月營收 TTM；錢＝綜合損益表彙總累計相減的單季毛利率對自家前高。

## 一句話

**削弱**：量的拐點裡，價在自家三年頂端、毛利在自家前高的那組（P，n＝123），6 個月內先跌 30% 以上 14.6%，確實高於其餘事件（R，n＝1,531）的 8.7%，前後兩段同向；但 12 個月內曾達 2 倍 16.3%，**也**高於 R 的 8.4%——照登記的第 ③ 條（P ≤ R）不成立。兩格同時在頂端挑出的是「兩邊尾巴都肥」的事件，不是「週期頂點」。照登記的後果：S4 的 rubric 不寫「週期頂點的形狀」這句，兩格照留在個股頁上當脈絡。

## 結果

| 組 | n | 12 個月內曾達 2 倍 | 6 個月內先跌 30% 以上 | 超額中位數 | 超額平均 |
|---|---|---|---|---|---|
| P：價 ≥ 95 且毛利 ≥ 前高九成 | 123 | 16.3% | 14.6% | -15.6% | +2.0% |
| R：其餘（兩格都有值） | 1,531 | 8.4% | 8.7% | -4.8% | +7.1% |
| P 2015-2018 | 26 | 15.4% | 19.2% | -18.6% | -3.6% |
| R 2015-2018 | 489 | 6.1% | 9.8% | -4.4% | +4.9% |
| P 2019-2022 | 97 | 16.5% | 13.4% | -14.8% | +3.5% |
| R 2019-2022 | 1,042 | 9.5% | 8.2% | -5.0% | +8.1% |

判讀線（預先登記）：①P、R 各 ≥ 30 ✓　②先跌 30% P > R ✓　③曾達 2 倍 P ≤ R ✗　④前後兩段 ② 方向一致 ✓ → **削弱（曾達 2 倍 P > R）**。

## 另印（不進判讀）

| 組 | n | 12 個月內曾達 2 倍 | 6 個月內先跌 30% 以上 | 超額中位數 | 超額平均 |
|---|---|---|---|---|---|
| ①只看價（≥95 對 <95；有價位的事件）——前者 | 282 | 13.8% | 18.1% | -11.9% | +0.1% |
| ①只看價（≥95 對 <95；有價位的事件）——後者 | 1,529 | 9.0% | 7.1% | -3.4% | +11.9% |
| ①只看錢（≥前高九成 對 未達；有前高的事件）——前者 | 458 | 10.9% | 12.0% | -11.3% | +3.0% |
| ①只看錢（≥前高九成 對 未達；有前高的事件）——後者 | 1,227 | 8.4% | 8.2% | -3.5% | +8.1% |
| ②增量：毛利在前高的事件裡，價 ≥95 對 <95——前者 | 123 | 16.3% | 14.6% | -15.6% | +2.0% |
| ②增量：毛利在前高的事件裡，價 ≥95 對 <95——後者 | 326 | 9.2% | 10.7% | -10.6% | +3.2% |
| ②增量：價 ≥95 的事件裡，毛利 ≥前高九成 對 未達——前者 | 123 | 16.3% | 14.6% | -15.6% | +2.0% |
| ②增量：價 ≥95 的事件裡，毛利 ≥前高九成 對 未達——後者 | 134 | 11.2% | 23.1% | -11.6% | -5.0% |

門檻敏感度：

| 組 | n | 12 個月內曾達 2 倍 | 6 個月內先跌 30% 以上 | 超額中位數 | 超額平均 |
|---|---|---|---|---|---|
| P（價 90） | 184 | 14.7% | 17.4% | -16.5% | -0.3% |
| R（價 90） | 1,470 | 8.3% | 8.1% | -4.2% | +7.6% |
| P（價 80） | 262 | 12.6% | 13.4% | -15.6% | -1.1% |
| R（價 80） | 1,392 | 8.3% | 8.3% | -3.9% | +8.2% |
| P（錢 80%） | 169 | 14.8% | 17.8% | -15.6% | -0.7% |
| R（錢 80%） | 1,485 | 8.3% | 8.2% | -4.4% | +7.5% |
| P（錢 100%） | 64 | 14.1% | 23.4% | -24.8% | -7.5% |
| R（錢 100%） | 1,590 | 8.8% | 8.6% | -4.8% | +7.3% |

其他對照：

| 組 | n | 12 個月內曾達 2 倍 | 6 個月內先跌 30% 以上 | 超額中位數 | 超額平均 |
|---|---|---|---|---|---|
| P（含兩檔負錨點） | 125 | 16.0% | 16.0% | -15.9% | +1.3% |
| R（含兩檔負錨點） | 1,531 | 8.4% | 8.7% | -4.8% | +7.1% |
| 非事件列：同一分組的 P | 5,801 | 9.5% | 7.0% | +0.9% | +11.8% |
| 非事件列：同一分組的 R | 112,926 | 8.1% | 6.0% | +0.1% | +11.1% |
| H12 重現：A（毛利年增 ≥ +3pp） | 709 | 9.0% | 12.0% | -8.7% | +1.5% |
| H12 重現：B | 1,071 | 9.2% | 8.8% | -3.3% | +10.2% |

- H12 的 A（毛利年增 ≥ +3pp）在兩組的占比：P 71.5%（n＝123）、R 38.0%（n＝1,531）。
- 各年的 n：2015：事件 155、P 2、R 61｜2016：事件 147、P 5、R 92｜2017：事件 225、P 14、R 156｜2018：事件 217、P 5、R 180｜2019：事件 141、P 5、R 116｜2020：事件 243、P 27、R 179｜2021：事件 637、P 61、R 496｜2022：事件 312、P 4、R 251。
- 兩檔負錨點在 H13 口徑下（從判讀線剔除；§15 的日線＋四季損益表口徑是價 99、100，毛利第 93、100 百分位）：
  - 6182 事件月 2021-10（進場 2021-11，TWO）：價——百分位 100.0（股價營收比 4.32，窗內 37 點，區間 1.79–4.32）；錢——2021Q3 單季毛利率 39.46%、前高 42.4%（2019Q1），比值 0.93；落在 P；之後 12 個月 -42%、先跌 30% 是、曾達 2 倍 否
  - 8016 事件月 2021-06（進場 2021-07，TW）：價——百分位 100.0（股價營收比 2.62，窗內 37 點，區間 0.96–2.62）；錢——2021Q1 單季毛利率 47.17%、前高 38.61%（2020Q4），比值 1.22；落在 P；之後 12 個月 -46%、先跌 30% 是、曾達 2 倍 否

## 描述（不進判讀）

- **兩邊尾巴都肥（和 H11 同形）**：P 的超額中位數 −15.6% 對 R −4.8%、平均 +2.0% 對 +7.1%——中位數更差、先崩更多，但翻倍也更多。門檻改成價 90／80、錢 80%／100%，方向都一樣：P 曾達 2 倍 12.6–14.8% 對 R 8.3–8.8%，先跌 30% 13.4–23.4% 對 8.1–8.6%。
- **「價」那一格本身最有分量**：只看價（≥ 95 對 < 95）先跌 18.1% 對 7.1%、曾達 2 倍 13.8% 對 9.0%；只看錢（≥ 前高九成對未達）先跌 12.0% 對 8.2%、曾達 2 倍 10.9% 對 8.4%。分層看——毛利在前高的事件裡，價 ≥ 95 對 < 95：先跌 14.6% 對 10.7%、曾達 2 倍 16.3% 對 9.2%——價在錢之外還有增量，而且增量也是兩邊一起加。
- **一個看完結果才有的說法（不能用同一份資料改判）**：價 ≥ 95 的事件裡，毛利**沒有**跟到前高九成的那組（n＝134）先跌 30% 是 23.1%、曾達 2 倍 11.2%；毛利在前高的那組（P）是 14.6%、16.3%。「價跑在錢前面」比「價和錢都在頂端」更像會崩的形狀——和 §15.3 第 2 點原本的讀法方向相反。要當真得另外預先登記、換一段期間測。
- **P 有七成是 H12 的 A 組**（毛利年增 ≥ +3pp；R 只有 38%）——P 先崩較多和 H12「量＋毛利大升那組先崩較多」是同一件事的延伸。
- **非事件月同一分組**：P（n＝5,801）先跌 30% 7.0% 對 R 6.0%、曾達 2 倍 9.5% 對 8.1%——同向但小得多；兩格同時在頂端的效果在量的拐點裡被放大。
- **P 集中在 2020–2021**（123 筆裡 88 筆，2021 年 61 筆）；2015–2018 只有 26 筆（④ 的門檻 15 過了）。
- **兩檔負錨點**在 H13 口徑下兩格都在頂端（價百分位都是 100；毛利對前高 0.93、1.22），落在 P——和 §15 的日線口徑（99、100）一致。它們從判讀線剔除；含它們時 P n＝125、先跌 16.0%、曾達 2 倍 16.0%，判讀不變。
- **後果（照登記）**：S4 把讀法寫進研究 skill rubric 時**不寫「週期頂點的形狀」**；兩格照留在頁上當脈絡；brainstorm §15.3 第 1、2、3 點已加註。量過的只有這一句描述：「量的拐點當下價在自家三年頂端的，之後兩邊尾巴都更肥（先崩與翻倍都更多）」——要不要寫進 rubric 是 S4 的事；不論寫不寫，它都不是門檻、不排序、不改候選狀態（G10）。

## 計數

```json
{
 "counts": {
  "events_judged": 2077,
  "anchors_removed": 2,
  "both_known": 1654,
  "price_status": {
   "有": 1811,
   "沒有三年價位（有值的點 < 24）": 196,
   "沒有三年價位（T 沒有值）": 70
  },
  "money_status": {
   "有": 1685,
   "沒有毛利率": 213,
   "沒有前高（之前合格的季 < 8）": 174,
   "毛利率基期太小": 4,
   "沒有前高（前高 ≤ 0）": 1
  },
  "codes_with_shares": 1920,
  "codes_with_raw_px": {
   "TW": 1015,
   "TWO": 832
  },
  "pit_violations": 0
 },
 "h12_reproduction": {
  "events": 2079,
  "control": 145744,
  "dropped_no_price": {
   "event": 50,
   "control": 1603
  }
 },
 "control_same_split": {
  "control_n": 145744,
  "control_both_known": 118727
 }
}
```

## 偏差標註

1. **不是沒看過的期間**：H12 已公布這段期間「毛利大升那組先崩較多」；兩檔負錨點（照結果挑的）已從判讀線剔除。P 七成落在 H12 的 A 組，先崩那一半不完全是新資訊（見描述）。
2. 股數是「歸屬母公司淨利 ÷ 基本每股盈餘」推的加權平均股數、不是期末股數；|EPS| < 0.3 的季沿用前一個可用季。
3. 原始價靠 Yahoo 記的分割還原；下載窗（2013-01..2023-02）之後的分割對整段窗是同一個常數，不影響百分位；Yahoo 配股比例記錯會讓序列跳一階（不查、計數不了）。H12 月線有、這次窗內 Yahoo 沒有的代號×後綴 15 個（非限流，抓取時記成「Yahoo 沒有」）。
4. 月營收 TTM、月底取樣與 §15 的四季損益表 TTM、每日取樣是不同口徑；兩檔負錨點兩種口徑都在頂端（100、100 對 99、100）。
5. 自家前高的歷史長度隨事件年份變（2015 年的事件約 8 季、2022 年約 36 季）；「沒有前高（之前合格的季 < 8）」174 筆的年分：2015 年 57、2016–2020 年共 67、2021 與 2022 年各 25——早期事件歷史不夠只解釋三分之一，其餘推一步多半是上市櫃不滿兩年的公司（沒逐筆查）；「沒有三年價位（點 < 24）」196 筆同形（2015 年 61，2021、2022 年 29、24）。兩種缺都偏向剔掉新掛牌的公司。
6. 不分組的事件：價 266（窗內有值的點 < 24：196；T 沒有值：70）、錢 392（沒有毛利率 213、沒有前高 175、基期太小 4）——判讀線只用兩格都有值的 1,654 筆（2,077 筆的 80%）。
7. H12 的 ①–⑦ 全部照舊（存活者、KY 期限、MOPS 現行版本、已知季可能早於拐點、全公司毛利、月底收盤、2015–2022 的環境）。
8. 可知日：腳本對每一個用到的股數季與毛利季檢查法定期限嚴格早於該點——違規 0；一筆手算（合晶 6182，T＝2021-11-30：2021Q3 推股數 510,442,963、TTM 月營收 96.585 億元、原始收盤 81.8 元）與腳本一致（4.3231，`h13_pit_check.py`）。
9. H12 重現：事件 2,079、A 709／B 1,071 的曾達 2 倍與先跌 30% 與 H12 報告逐位相同——事件集合與結果欄沒有因為重跑而漂移。

## 腳本（逐字）

### h13_fetch.py

```python
"""H13 資料抓取（registration.md 2026-10-07 追加，登記 commit 8d8043df 早於本腳本）。只抓、不算任何結果。
H12 的抓取快取（月營收 2014-10..2022-12、損益表營收與毛利、還原權息月線）原檔沿用、不重抓；本腳本只抓登記寫的三樣：
1. MOPS 歷史月營收 2012-04..2014-09（上市＋上櫃、國內＋國外）→ h13_cache/rev_*.json（三年價位窗最早的點要 TTM）
2. MOPS 綜合損益表彙總 ajax_t163sb04 2013Q1..2022Q4（上市＋上櫃）→ h13_cache/isx_*.json（代號 → 基本每股盈餘、兩個淨利欄；推股數用）
3. yfinance 月線未還原權息（auto_adjust=False、actions=True）2013-01..2023-02 → h13_cache/pxraw_TW.json、pxraw_TWO.json
   只抓 H12 月線裡有的（代號 × 後綴）——那些是 Yahoo 有的；抓不到的分清楚「限流」與「Yahoo 沒有」（yfinance.shared._ERRORS），限流就退避重抓。
不寫任何 repo 檔、不寫 Engine C。"""
import json
import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
sys.path.insert(0, r"C:\Users\Cheng\code\StockBotv2")
sys.stdout.reconfigure(encoding="utf-8")
from fetchers.mops_open_data import fetch_monthly_revenue_month  # noqa: E402
from fetchers.utils import build_headers  # noqa: E402

H12 = Path(r"C:\Users\Cheng\AppData\Local\Temp\claude\C--Users-Cheng-code-StockBotv2"
           r"\0127fd91-d75d-4bb9-9435-2b14d8f5ca61\scratchpad\h12_cache")
CACHE = HERE / "h13_cache"
CACHE.mkdir(exist_ok=True)
REV_MONTHS = [(y, m) for y in range(2012, 2015) for m in range(1, 13) if (2012, 4) <= (y, m) <= (2014, 9)]
IS_QUARTERS = [(y, q) for y in range(2013, 2023) for q in (1, 2, 3, 4)]
IS_URL = "https://mopsov.twse.com.tw/mops/web/ajax_t163sb04"
SEG = {"twse": "sii", "tpex": "otc"}
TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.I | re.S)
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
TAG = re.compile(r"<[^>]+>")
CODE = re.compile(r"^\d{4,6}$")
EPS_COL = "基本每股盈餘（元）"
NI_PARENT = "淨利（淨損）歸屬於母公司業主"
NI_ALL = "本期淨利（淨損）"


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


fails = []

# ---------- 1. 月營收 ----------
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
    log("月營收", market, "完成；累計失敗", len(fails))

# ---------- 2. 損益表彙總（每股盈餘與淨利）----------
for market in ("twse", "tpex"):
    for y, q in IS_QUARTERS:
        f = CACHE / f"isx_{market}_{y}Q{q}.json"
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
                    fails.append(f"isx {market} {y}Q{q}: {exc}")
                time.sleep(8 * (attempt + 1))
        if body is None:
            continue
        out, no_eps = {}, {}
        for t in TABLE.findall(body):
            trs = ROW.findall(t)
            if not trs:
                continue
            head = [txt(c) for c in CELL.findall(trs[0])]
            idx = {h: i for i, h in enumerate(head)}
            codes = [txt((CELL.findall(tr) or [""])[0]) for tr in trs[1:]]
            n_codes = sum(1 for c in codes if CODE.match(c))
            if not n_codes or "公司代號" not in idx:
                continue
            if EPS_COL not in idx:
                no_eps[f"{len(head)}欄"] = n_codes
                continue
            for tr in trs[1:]:
                cells = [txt(c) for c in CELL.findall(tr)]
                if not cells or not CODE.match(cells[0]) or len(cells) != len(head):
                    continue
                out[cells[0]] = {"eps": num(cells[idx[EPS_COL]]),
                                 "ni_parent": num(cells[idx[NI_PARENT]]) if NI_PARENT in idx else None,
                                 "ni": num(cells[idx[NI_ALL]]) if NI_ALL in idx else None}
        f.write_text(json.dumps({"rows": out, "tables_without_eps": no_eps}, ensure_ascii=False), encoding="utf-8")
        log("損益表", market, f"{y}Q{q}", "有每股盈餘", len(out), "沒有每股盈餘欄的表", no_eps)
        time.sleep(2.0)

# ---------- 3. 月線未還原權息 ----------
import yfinance as yf  # noqa: E402
import yfinance.shared as yf_shared  # noqa: E402

h12_px = {sfx: json.loads((H12 / f"px_{sfx}.json").read_text(encoding="utf-8")) for sfx in ("TW", "TWO")}
raw = {}
for sfx in ("TW", "TWO"):
    f = CACHE / f"pxraw_{sfx}.json"
    raw[sfx] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
pending = [(c, sfx) for sfx in ("TW", "TWO") for c in sorted(h12_px[sfx]) if c not in raw[sfx]]
log("月線要抓的（代號 × 後綴）", len(pending))
status: dict[str, str] = {}
attempt = 0
while pending and attempt < 7:
    attempt += 1
    still = []
    size = 100 if attempt == 1 else 30
    for i in range(0, len(pending), size):
        chunk = pending[i:i + size]
        tickers = [f"{c}.{sfx}" for c, sfx in chunk]
        try:
            df = yf.download(tickers, start="2013-01-01", end="2023-03-01", interval="1mo", auto_adjust=False,
                             actions=True, group_by="ticker", threads=(attempt == 1), progress=False)
        except Exception as exc:  # noqa: BLE001
            log("下載例外", exc)
            still.extend(chunk)
            time.sleep(30)
            continue
        errors = dict(getattr(yf_shared, "_ERRORS", {}) or {})
        for (c, sfx), t in zip(chunk, tickers):
            err = str(errors.get(t, ""))
            try:
                try:
                    sub = df[t]
                except Exception:  # noqa: BLE001
                    sub = df
                close = sub["Close"].dropna()
                spl = sub["Stock Splits"].fillna(0) if "Stock Splits" in sub else None
            except Exception:  # noqa: BLE001
                close, spl = None, None
            if close is not None and len(close):
                raw[sfx][c] = {"close": {d.strftime("%Y-%m"): float(v) for d, v in close.items()},
                               "splits": ({d.strftime("%Y-%m"): float(v) for d, v in spl.items() if v and float(v) != 0.0}
                                          if spl is not None else {}),
                               "splits_column": spl is not None}
                status[t] = "有價"
            elif "Rate limit" in err or "Too Many Requests" in err or "YFRateLimit" in err:
                still.append((c, sfx))
                status[t] = "仍被限流"
            else:
                status[t] = "Yahoo 沒有：" + (err[:80] or "空回應")
        log(f"第 {attempt} 輪", min(i + size, len(pending)), "/", len(pending), "有價累計",
            sum(len(v) for v in raw.values()), "本輪限流", len(still))
        time.sleep(3 if attempt == 1 else 6)
    for sfx in ("TW", "TWO"):
        (CACHE / f"pxraw_{sfx}.json").write_text(json.dumps(raw[sfx]), encoding="utf-8")
    pending = still
    if pending:
        log(f"第 {attempt} 輪結束：仍被限流 {len(pending)}，退避 {60 * attempt} 秒")
        time.sleep(60 * attempt)
(CACHE / "pxraw_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=0), encoding="utf-8")
if pending:
    fails.append(f"月線仍被限流 {len(pending)} 個（代號 × 後綴）")
nones = sum(1 for v in status.values() if v.startswith("Yahoo 沒有"))
log("月線：H12 有、這次 Yahoo 沒有（非限流）", nones)

(CACHE / "fetch_failures.json").write_text(json.dumps(fails, ensure_ascii=False, indent=1), encoding="utf-8")
log("全部完成；失敗", len(fails), fails[:10])
```
### h13_compute.py

```python
"""H13 計算（docs/reports/phase7/registration.md 2026-10-07 追加，登記 commit 8d8043df 早於本腳本與任何結果）。
唯讀：讀 H12 抓取快取原檔（月營收 2014-10..2022-12、損益表營收與毛利、還原權息月線）與 h13_cache（h13_fetch.py 抓的：
月營收 2012-04..2014-09、損益表每股盈餘與淨利、未還原權息月線），結果寫 h13_result.json。不寫任何 repo 檔、不寫 Engine C。
事件、進出場、結果欄、超額照 H12 腳本（h12_compute.py）逐字；新增的只有「價」「錢」兩格與分組。"""
import json
import sys
from datetime import date
from pathlib import Path
from statistics import mean, median

HERE = Path(__file__).parent
H12 = Path(r"C:\Users\Cheng\AppData\Local\Temp\claude\C--Users-Cheng-code-StockBotv2"
           r"\0127fd91-d75d-4bb9-9435-2b14d8f5ca61\scratchpad\h12_cache")
CACHE = H12                     # H12 腳本逐字的部分讀這個
H13 = HERE / "h13_cache"
sys.path.insert(0, r"C:\Users\Cheng\code\StockBotv2")
sys.stdout.reconfigure(encoding="utf-8")
from engine_c.tw_share_capital import statutory_deadline  # noqa: E402

MIN_BASE = 10_000          # 去年同月營收 < 1,000 萬元（千元）不判——同 H11
MIN_Q_REV = 30_000         # 單季營收 < 3,000 萬元（千元）＝毛利率基期太小
GM_THR = 3.0               # H12 的毛利年變化門檻（只用在另印 ⑤）
EVENT_MONTHS = [(y, m) for y in range(2015, 2023) for m in range(1, 13)]

# H13 登記的參數
PRICE_PCT = 95.0           # 自家三年股價營收比百分位 ≥ 95
MONEY_RATIO = 0.9          # 單季毛利率 ≥ 自家前高的九成
WINDOW_MONTHS = 36         # T 與 T 之前 36 個月底
MIN_POINTS = 24            # 有值的點 < 24 →「沒有三年價位」
MIN_HIST_Q = 8             # 之前合格的季 < 8 →「沒有前高」
EPS_MIN = 0.3              # |EPS| < 0.3 的季不用、沿用前一個可用季
ANCHORS = {("6182", "2021-10"), ("8016", "2021-06")}   # 兩檔負錨點（照結果挑的）——判讀線剔除

# ---------- 月營收（以公司代號串，轉板前後接起來）——H12 逐字 ----------
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


# ---------- 價格：先上市、缺進場或出場月再上櫃——H12 逐字 ----------
px = {sfx: json.loads((CACHE / f"px_{sfx}.json").read_text(encoding="utf-8")) for sfx in ("TW", "TWO")}


def series_for(c, e_k, x_k):
    for sfx in ("TW", "TWO"):
        p = px[sfx].get(c)
        if p and e_k in p and x_k in p:
            return p
    return None


# ---------- 損益表：累計 → 單季——H12 逐字 ----------
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


# ---------- 事件與對照（同 H11）——H12 逐字 ----------
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


# =====================================================================================
# H13 新增：價（自家三年股價營收比百分位）與錢（單季毛利率對自家前高）
# =====================================================================================

# ---------- 月營收金額（TTM 用）：h13_cache 2012-04..2014-09 ＋ H12 快取 2014-10..2022-12，以公司代號串 ----------
rev_amt: dict[str, dict[str, float]] = {}
for d in (H13, CACHE):
    for f in sorted(d.glob("rev_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            c, cur = r.get("company_code"), r.get("revenue_current")
            if not c or cur is None:
                continue
            rev_amt.setdefault(c, {}).setdefault(r["data_month"], float(cur))


def ttm_revenue(c, key):
    """月底 d（月 key）時已知的最近 12 個連續月營收合計：月 k 的可知日＝k+1 月 10 日，嚴格早於 d → 用 key−12..key−1。缺任一個月 → None。"""
    y, m = int(key[:4]), int(key[5:])
    vals = [rev_amt.get(c, {}).get(mkey(y, m - k)) for k in range(1, 13)]
    if any(v is None for v in vals):
        return None
    return sum(vals) * 1000.0      # 千元 → 元


# ---------- 股數：損益表彙總「淨利歸屬母公司 ÷ 基本每股盈餘」（年初至今累計 → 加權平均股數），|EPS| < 0.3 沿用前一個可用季 ----------
isx: dict[tuple, dict[str, dict]] = {}
for f in sorted(H13.glob("isx_*.json")):
    _, _, yq = f.stem.split("_")
    y, q = int(yq[:4]), int(yq[5])
    for code, row in json.loads(f.read_text(encoding="utf-8"))["rows"].items():
        slot = isx.setdefault((y, q), {})
        if code not in slot or slot[code].get("eps") is None:
            slot[code] = row
ISX_QUARTERS = sorted(isx)
ISX_DEADLINE = {(y, q): date.fromisoformat(statutory_deadline(y, q)) for y, q in ISX_QUARTERS}
shares_by_q: dict[str, dict[tuple, float]] = {}
for c in {code for v in isx.values() for code in v}:
    last = None
    for k in ISX_QUARTERS:
        row = isx[k].get(c)
        if row:
            ni = row.get("ni_parent") if row.get("ni_parent") is not None else row.get("ni")
            eps = row.get("eps")
            if ni is not None and eps is not None and abs(eps) >= EPS_MIN:
                s = ni * 1000.0 / eps
                if s > 0:
                    last = s
        if last is not None:
            shares_by_q.setdefault(c, {})[k] = last


def shares_at(c, d):
    """d 時已知（法定期限嚴格早於 d）的最新一季股數（含沿用）。"""
    s = shares_by_q.get(c)
    if not s:
        return None, None
    known = [k for k in ISX_QUARTERS if ISX_DEADLINE[k] < d and k in s]
    if not known:
        return None, None
    k = max(known)
    return s[k], k


# ---------- 原始收盤：未還原權息 Close × 該月之後（窗內）Yahoo 記的分割比例 ----------
pxraw = {sfx: json.loads((H13 / f"pxraw_{sfx}.json").read_text(encoding="utf-8")) for sfx in ("TW", "TWO")}


def raw_close(c, sfx, key):
    s = pxraw[sfx].get(c)
    if not s or key not in s["close"]:
        return None
    factor = 1.0
    for sk, ratio in s.get("splits", {}).items():
        if sk > key and ratio:
            factor *= ratio
    return s["close"][key] * factor


def suffix_for(c, e_k, x_k):
    """H12 series_for 選的那個後綴（同一個判準）。"""
    for sfx in ("TW", "TWO"):
        p = px[sfx].get(c)
        if p and e_k in p and x_k in p:
            return sfx
    return None


_ps_cache: dict[tuple, float | None] = {}
pit_violations = []


def ps_at(c, sfx, key):
    """月底 key 的股價營收比；價格先用 sfx、缺的月份用另一個後綴補。"""
    ck = (c, sfx, key)
    if ck in _ps_cache:
        return _ps_cache[ck]
    d = month_end(key)
    price = raw_close(c, sfx, key)
    if price is None:
        price = raw_close(c, "TWO" if sfx == "TW" else "TW", key)
    sh, sq = shares_at(c, d)
    ttm = ttm_revenue(c, key)
    val = None
    if price is not None and sh is not None and ttm and ttm > 0:
        val = price * sh / ttm
        if ISX_DEADLINE[sq] >= d:
            pit_violations.append(("shares", c, key, sq))
    _ps_cache[ck] = val
    return val


def price_position(c, sfx, e_k):
    """(百分位 或 None, 狀態, 細節)。窗＝T 與 T 之前 36 個月底；百分位＝窗內 ≤ T 的點數 ÷ 有值的點數 × 100（含 T）。"""
    y, m = int(e_k[:4]), int(e_k[5:])
    t_val = ps_at(c, sfx, e_k)
    if t_val is None:
        return None, "沒有三年價位（T 沒有值）", None
    vals = [ps_at(c, sfx, mkey(y, m - k)) for k in range(0, WINDOW_MONTHS + 1)]
    vals = [v for v in vals if v is not None]
    if len(vals) < MIN_POINTS:
        return None, "沒有三年價位（有值的點 < 24）", {"points": len(vals)}
    pct = sum(1 for v in vals if v <= t_val) / len(vals) * 100
    return pct, "有", {"ps": t_val, "points": len(vals), "min": min(vals), "max": max(vals)}


_gm_cache: dict[tuple, tuple] = {}


def money_position(c, e_k):
    """(那一季毛利率 ÷ 自家前高 或 None, 狀態, 細節)。最近一季同 H12 gm_change；前高＝之前所有合格季的最大單季毛利率。"""
    entry_day = month_end(e_k)
    known = [k for k in QUARTERS if DEADLINE[k] < entry_day]
    if not known:
        return None, "沒有毛利率（期間外）", None
    y, q = max(known)
    ck = (c, y, q)
    if ck in _gm_cache:
        return _gm_cache[ck]
    this = single_q(c, y, q)
    if this is None:
        out = (None, "沒有毛利率", {"q": f"{y}Q{q}"})
    elif this[0] < MIN_Q_REV:
        out = (None, "毛利率基期太小", {"q": f"{y}Q{q}"})
    else:
        gm = this[1] / this[0] * 100
        hist = []
        for k in QUARTERS:
            if k >= (y, q):
                break
            sq = single_q(c, *k)
            if sq is not None and sq[0] >= MIN_Q_REV:
                hist.append((k, sq[1] / sq[0] * 100))
        if len(hist) < MIN_HIST_Q:
            out = (None, "沒有前高（之前合格的季 < 8）", {"q": f"{y}Q{q}", "hist": len(hist)})
        else:
            peak_k, peak = max(hist, key=lambda h: h[1])
            if peak <= 0:
                out = (None, "沒有前高（前高 ≤ 0）", {"q": f"{y}Q{q}"})
            else:
                out = (gm / peak, "有", {"q": f"{y}Q{q}", "gm": round(gm, 2), "peak": round(peak, 2),
                                         "peak_q": f"{peak_k[0]}Q{peak_k[1]}", "hist": len(hist)})
        if DEADLINE[(y, q)] >= entry_day:
            pit_violations.append(("gm", c, e_k, (y, q)))
    _gm_cache[ck] = out
    return out


def annotate(r):
    sfx = suffix_for(r["c"], r["entry_m"], mkey(int(r["m"][:4]), int(r["m"][5:]) + 13))
    r["sfx"] = sfx
    r["pct"], r["price_status"], r["price_detail"] = price_position(r["c"], sfx, r["entry_m"])
    r["mr"], r["money_status"], r["money_detail"] = money_position(r["c"], r["entry_m"])


def groups(sel, pct_thr=PRICE_PCT, mr_thr=MONEY_RATIO):
    both = [r for r in sel if r["pct"] is not None and r["mr"] is not None]
    p = [r for r in both if r["pct"] >= pct_thr and r["mr"] >= mr_thr]
    rr = [r for r in both if not (r["pct"] >= pct_thr and r["mr"] >= mr_thr)]
    return p, rr


rows, no_price = build()
events_all = [r for r in rows if r["event"]]
control = [r for r in rows if not r["event"]]
for r in events_all:
    annotate(r)
events = [r for r in events_all if (r["c"], r["m"]) not in ANCHORS]      # 判讀線：剔除兩檔負錨點
anchors_found = [r for r in events_all if (r["c"], r["m"]) in ANCHORS]

P, R = groups(events)
sP, sR = stats(P), stats(R)
first = [r for r in events if r["m"] < "2019-01"]
second = [r for r in events if r["m"] >= "2019-01"]
P1, R1 = groups(first)
P2, R2 = groups(second)
c1 = sP["n"] >= 30 and sR["n"] >= 30
c2 = c1 and sP["fall30"] > sR["fall30"]
c3 = c1 and sP["hit2x"] <= sR["hit2x"]


def half_ok(a, b):
    if len(a) < 15 or len(b) < 15:
        return False
    return stats(a)["fall30"] > stats(b)["fall30"]


c4 = half_ok(P1, R1) and half_ok(P2, R2)
if not c1:
    verdict = "不足（P 或 R 不到 30）"
elif not (c2 and c3):
    verdict = "削弱（" + ("先跌 30% P ≤ R" if not c2 else "") + ("、" if not c2 and not c3 else "") + ("曾達 2 倍 P > R" if not c3 else "") + "）"
elif not c4:
    verdict = "不足（全期成立，但前後兩段方向不一致或某段 n < 15）"
else:
    verdict = "支持（四條全部成立）"

# ---------- 另印（不進判讀線）----------
price_known = [r for r in events if r["pct"] is not None]
money_known = [r for r in events if r["mr"] is not None]
both_known = [r for r in events if r["pct"] is not None and r["mr"] is not None]
side = {
    "①只看價（≥95 對 <95；有價位的事件）": {"hi": stats([r for r in price_known if r["pct"] >= PRICE_PCT]),
                                    "lo": stats([r for r in price_known if r["pct"] < PRICE_PCT])},
    "①只看錢（≥前高九成 對 未達；有前高的事件）": {"hi": stats([r for r in money_known if r["mr"] >= MONEY_RATIO]),
                                      "lo": stats([r for r in money_known if r["mr"] < MONEY_RATIO])},
    "②增量：毛利在前高的事件裡，價 ≥95 對 <95": {
        "hi": stats([r for r in both_known if r["mr"] >= MONEY_RATIO and r["pct"] >= PRICE_PCT]),
        "lo": stats([r for r in both_known if r["mr"] >= MONEY_RATIO and r["pct"] < PRICE_PCT])},
    "②增量：價 ≥95 的事件裡，毛利 ≥前高九成 對 未達": {
        "hi": stats([r for r in both_known if r["pct"] >= PRICE_PCT and r["mr"] >= MONEY_RATIO]),
        "lo": stats([r for r in both_known if r["pct"] >= PRICE_PCT and r["mr"] < MONEY_RATIO])},
}
sens = {}
for label, pt, mt in (("價 90", 90.0, MONEY_RATIO), ("價 80", 80.0, MONEY_RATIO),
                      ("錢 80%", PRICE_PCT, 0.8), ("錢 100%", PRICE_PCT, 1.0)):
    a, b = groups(events, pt, mt)
    sens[label] = {"P": stats(a), "R": stats(b)}


def a_share(sel):
    known = [r for r in sel if r.get("dgm") is not None]
    return {"n": len(sel), "dgm_known": len(known),
            "A_share": round(sum(1 for r in known if r["dgm"] >= GM_THR) / len(known), 4) if known else None}


Pa, Ra = groups(events_all)
for r in control:
    annotate(r)
Pc, Rc = groups(control)
status_counts = {"price": {}, "money": {}}
for r in events:
    status_counts["price"][r["price_status"]] = status_counts["price"].get(r["price_status"], 0) + 1
    status_counts["money"][r["money_status"]] = status_counts["money"].get(r["money_status"], 0) + 1
anchor_detail = [{"c": r["c"], "m": r["m"], "entry": r["entry_m"], "sfx": r["sfx"], "pct": r["pct"],
                  "price": r["price_detail"], "money_ratio": r["mr"], "money": r["money_detail"],
                  "in_P": r["pct"] is not None and r["mr"] is not None and r["pct"] >= PRICE_PCT and r["mr"] >= MONEY_RATIO,
                  "hit2x": r["hit2x"], "fall30": r["fall30"], "ret": round(r["ret"], 4)} for r in anchors_found]

A12 = [r for r in events_all if r.get("dgm") is not None and r["dgm"] >= GM_THR]
B12 = [r for r in events_all if r.get("dgm") is not None and r["dgm"] < GM_THR]
result = {
    "registered_commit": "8d8043df", "verdict": verdict,
    "conditions": {"①P、R 各 ≥ 30": c1, "②先跌 30% P > R": c2, "③曾達 2 倍 P ≤ R": c3, "④前後兩段 ② 方向一致": c4},
    "P_priced_and_margin_top": sP, "R_rest": sR,
    "halves": {"2015-2018": {"P": stats(P1), "R": stats(R1)}, "2019-2022": {"P": stats(P2), "R": stats(R2)}},
    "side_prints": side,
    "sensitivity": sens,
    "h12_A_share": {"P": a_share(P), "R": a_share(R)},
    "with_anchors": {"P": stats(Pa), "R": stats(Ra)},
    "anchors": anchor_detail,
    "control_same_split": {"P": stats(Pc), "R": stats(Rc), "control_n": len(control),
                           "control_both_known": len(Pc) + len(Rc)},
    "by_year_n": {str(yy): {"events": sum(1 for r in events if r["m"].startswith(str(yy))),
                            "P": sum(1 for r in P if r["m"].startswith(str(yy))),
                            "R": sum(1 for r in R if r["m"].startswith(str(yy)))} for yy in range(2015, 2023)},
    "h12_reproduction": {"events": len(events_all), "control": len(control), "A": stats(A12), "B": stats(B12),
                         "dropped_no_price": no_price},
    "counts": {"events_judged": len(events), "anchors_removed": len(anchors_found), "both_known": len(both_known),
               "price_status": status_counts["price"], "money_status": status_counts["money"],
               "codes_with_shares": len(shares_by_q), "codes_with_raw_px": {s: len(v) for s, v in pxraw.items()},
               "pit_violations": len(pit_violations)},
}
(HERE / "h13_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
```
### h13_pit_check.py

```python
"""H13 一筆手算（不呼叫 h13_compute 的任何函式）：合晶 6182，事件月 2021-10，T＝2021-11-30。
直接讀快取原檔：①T 時已知的最新一季（法定期限嚴格早於 T）推股數 ②2020-11..2021-10 月營收合計 ③2021-11 月底原始收盤。"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, r"C:\Users\Cheng\code\StockBotv2")
sys.stdout.reconfigure(encoding="utf-8")
from engine_c.tw_share_capital import statutory_deadline  # noqa: E402

HERE = Path(__file__).parent
H12 = Path(r"C:\Users\Cheng\AppData\Local\Temp\claude\C--Users-Cheng-code-StockBotv2"
           r"\0127fd91-d75d-4bb9-9435-2b14d8f5ca61\scratchpad\h12_cache")
T = date(2021, 11, 30)
code = "6182"

quarters = [(2021, 3), (2021, 2), (2021, 1), (2020, 4)]
known = [q for q in quarters if date.fromisoformat(statutory_deadline(*q)) < T]
q = known[0]
row = None
for mk in ("tpex", "twse"):
    f = HERE / "h13_cache" / f"isx_{mk}_{q[0]}Q{q[1]}.json"
    row = json.loads(f.read_text(encoding="utf-8"))["rows"].get(code) or row
ni = row["ni_parent"] if row["ni_parent"] is not None else row["ni"]
shares = ni * 1000 / row["eps"]
print("最新已知季", q, "期限", statutory_deadline(*q), "淨利（千元）", ni, "EPS", row["eps"], "→ 股數", round(shares))

months = [f"{y:04d}-{m:02d}" for y, m in [(2020, 11), (2020, 12)] + [(2021, k) for k in range(1, 11)]]
rev = {}
for f in sorted(H12.glob("rev_*.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        if r.get("company_code") == code and r["data_month"] in months and r.get("revenue_current") is not None:
            rev.setdefault(r["data_month"], r["revenue_current"])
assert len(rev) == 12, rev
ttm = sum(rev.values()) * 1000
print("TTM 月營收（2020-11..2021-10，元）", round(ttm))

pxraw = json.loads((HERE / "h13_cache" / "pxraw_TWO.json").read_text(encoding="utf-8"))[code]
close = pxraw["close"]["2021-11"]
factor = 1.0
for k, v in pxraw["splits"].items():
    if k > "2021-11":
        factor *= v
print("2021-11 月底收盤（未還原權息）", close, "之後分割", {k: v for k, v in pxraw["splits"].items() if k > "2021-11"}, "→ 原始", close * factor)
print("股價營收比", round(close * factor * shares / ttm, 4), "（腳本：4.3231）")
```
### check_nopeak_years.py

```python
"""查證報告偏差第 5 點：「沒有前高（之前合格的季 < 8）」的事件落在哪些年。重跑 h13_compute（輸出丟掉），只讀它的 events。"""
import contextlib
import io
import runpy
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
with contextlib.redirect_stdout(io.TextIOWrapper(io.BytesIO(), encoding="utf-8")):
    g = runpy.run_path(r"C:\Users\Cheng\AppData\Local\Temp\p7s\h13\h13_compute.py")
ev = g["events"]
c = Counter(r["m"][:4] for r in ev if r["money_status"].startswith("沒有前高（之前合格的季"))
print("沒有前高（< 8 季）by year:", dict(sorted(c.items())), "total", sum(c.values()))
c2 = Counter(r["m"][:4] for r in ev if r["price_status"].startswith("沒有三年價位（有值的點"))
print("沒有三年價位（點 < 24）by year:", dict(sorted(c2.items())), "total", sum(c2.values()))
```
