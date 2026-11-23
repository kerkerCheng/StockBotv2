# 回測乙（硬訊號之後）乾跑：只有「澄清媒體報導」一類數得出樣本，而且要先有標旗器

> 2026-11-23｜Phase 8 第二個修正案「劇本時間線」第 2 步（設計稿檔尾第五則：「回測乙的乾跑：硬訊號之後——數得出樣本的事件有幾種、各幾筆，數完再決定登不登記」）。
> **只數、不判。** 沒有看任何一筆的價格或之後的結果；這裡沒有判讀線，登不登記由使用者決定。

## 一句話

回測甲量的是「已經漲一倍之後」；回測乙要量的是「同樣的硬訊號出現了、後來沒漲的有幾成」。台股手上的資料裡，**全市場、不只倖存者、量又夠的只有一種**：
公司被要求澄清的媒體報導裡寫到漲價、缺貨、滿載、在手訂單、交期——抽樣估一年約 200 則、八年約 1,600 則。
但那些句子混著法人預估、報社轉述與公司否認（比例沒有量），哪一則算「寫明白的硬訊號」要先標過一遍，**所以回測乙排在標旗器的考卷之後**。

## 資料源盤點

| 來源 | 全市場？ | 含後來下市的？ | 手上有嗎 | 補齊要多久 |
|---|---|---|---|---|
| 歷史重大訊息（公開資訊觀測站，依日期查；主旨＋說明全文） | 是 | 是（那一天的名單） | 抽樣 25 天 | 全期約 1,900 個交易日、估約 80 萬則、約 1.1 GB；照 6 秒節流約 3.2 小時 |
| 月營收 | 是 | 歷史頁只有倖存者（見記憶 reference_mops_history_survivor_only） | 有 | — |
| 資產負債表的合約負債、預收 | 要逐家逐季抓 | — | 只有 H16 事件公司的 712 份 | 約 1,800 家 × 32 季，沒有找到一次拿全市場的來源（未查完） |

月營收的「量的拐點」H11、H12、H13 已經量過三次（都削弱），不在這裡重做。

## 抽樣

2017–2024 每年 3、7、11 月的 15 日（遇假日順延到下一個交易日），另加 2018-05-15 一天探針，共 25 天。規則先寫、沒有挑日子。
四碼公司的重訊 **10,592 則**；每天 171–814 則，三月（年報與董事會季）最多。

## 數得出樣本的候選事件（抽樣日的計數；一年約＝計數 ÷ 25 × 245）

| 候選事件 | 對應的事件種類 | 抽樣日 | 一年約 | 判斷 |
|---|---|---|---|---|
| (a) 澄清媒體報導，說明裡寫到漲價、缺貨、滿載、在手訂單、交期 | `hard_signal`（多半是第三方轉述） | 21 則（澄清類共 223 則） | 200 | **唯一夠量的**。例：華新科 2018-03「今年 MLCC 景氣仍維持高檔，且會充分反映漲價效益」、益張 2021-07「Q3 產品再調漲 5~20%」、臺慶科 2021-07「擴產趕不上接單」。也混著法人預估與公司否認，要先標 |
| (b) 買方「取得機器設備」，交易相對人具名 | 對設備商是 `hard_signal`（訂單） | 12 則、具名 9 則 | 118 | 太薄：具名的多是外商（Lam、Teradyne、ULVAC、Accretech），配得到台股上市櫃的 0 則 |
| (c) 籌錢：現金增資 292、私募 159、可轉債發行 17、授信 23 | `supplier_raise` | 491 則 | 4,800 | 量很多但多是子公司與例行；這一種回測甲的「發股」已量過（不確定） |
| (d) 說明裡寫到預收、合約負債、長約、預付（排除財報類） | `buyer_commit` | 13 則 | — | **重訊裡沒有這一種**：13 則全是背書保證、速動比率、財報更正 |
| (e) 主旨直接寫漲價、缺貨、滿載 | `hard_signal` | 0 則 | 0 | 沒有 |

## 結論（只數不判）

- 定義得出、量又夠的只有 (a)。它要先過一遍「這一則是不是寫明白的硬訊號」——正是標旗器的工作，所以順序是：考卷 → 全抓重訊 → 標旗器標 (a) 類 → 人抽查 → 才有樣本。
- (b) 對台股設備商太薄；(d) 重訊裡沒有，要等全市場資產負債表的來源；(c) 已量過。
- 美股那邊（8-K、10-Q 的預付與長約）每日已經在收，但 19 檔騎的層裡美股形式的只有 6 檔，而且全市場的反例要另外建宇宙，這一輪沒有數。

## 要使用者決定的

登不登記回測乙＝「台股公司被要求澄清的媒體報導裡出現硬訊號之後，兩年內漲一倍的、回落四成的各占幾成；跟同月沒有這種報導的公司比」。
登記之前要先做兩件事（各自不需要決定）：全抓 2017–2024 的重訊（約 3 小時）、標旗器的考卷結果。

## 腳本

抓取 `probe_news.py`、拆解 `parse_news.py`、計數 `count_b.py`、`count_eq.py`（本機暫存，逐字附在下面）。對外請求只用一般瀏覽器 UA，不帶任何個人資訊；節流 6 秒。

## 腳本（逐字）

### probe_news.py（抓抽樣日的歷史重大訊息；sha256 前 16 碼 `a665c39975672c2f`）

```python
"""回測乙乾跑的資料探針：公開資訊觀測站「歷史重大訊息（依日期）」一天有幾則、主旨長什麼樣。
只存原始回應到這個資料夾；節流 6 秒；對外請求不帶任何個人資訊。用法：python probe_news.py 民國年 月 日 [民國年 月 日 …]"""
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
OUT = HERE / "news"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script",
      "Content-Type": "application/x-www-form-urlencoded"}
URL = "https://mopsov.twse.com.tw/mops/web/ajax_t05st02"
args = sys.argv[1:]
for k in range(0, len(args), 3):
    y, m, d = args[k:k + 3]
    dest = OUT / f"{y}_{m}_{d}.html"
    if dest.exists():
        print("已有", dest.name, dest.stat().st_size)
        continue
    body = f"encodeURIComponent=1&step=1&step00=0&firstin=1&off=1&TYPEK=all&year={y}&month={m}&day={d}"
    try:
        r = requests.post(URL, data=body, headers=UA, timeout=60)
        dest.write_bytes(r.content)
        print(y, m, d, r.status_code, len(r.content), flush=True)
    except Exception as exc:  # noqa: BLE001
        print(y, m, d, "失敗", type(exc).__name__, flush=True)
    time.sleep(6)
```

### parse_news.py（拆解與主旨分類；sha256 前 16 碼 `9034f1d54e71ddca`）

```python
"""回測乙乾跑：把抽樣日的歷史重大訊息拆成（日期、代號、名稱、主旨、說明）並照主旨分類計數。只數，不看任何價格。
用法：python parse_news.py"""
import collections
import html
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
FIELD = re.compile(r"name='h\d*?(\d)' value='(.*?)'>", re.S)   # 欄名＝h＋列號＋欄號（h10…h18 是第 1 列）

#: 主旨或說明命中就算；先寫下再數，沒有看過結果調。一則只歸第一個命中的類（順序就是優先序）。
CATS = [
    ("設備或廠房（取得）", ("取得機器設備", "取得設備", "取得廠房", "取得不動產", "取得使用權資產", "購置機器", "購置設備", "承攬", "擴建", "新建廠房")),
    ("籌錢（發股、發債、授信）", ("現金增資", "可轉換公司債", "私募", "聯合授信", "聯貸", "發行公司債", "無擔保公司債", "海外存託憑證")),
    ("重要合約或長約", ("重要合約", "長期合約", "長期供貨", "簽訂合約", "簽署合約", "供貨合約", "採購合約", "簽訂", "合作備忘錄", "策略聯盟")),
    ("漲價、缺貨、滿載（多在澄清）", ("漲價", "調漲", "缺貨", "滿載", "供不應求", "產能吃緊")),
    ("減損、跌價、下修", ("減損", "存貨跌價", "下修", "調降", "暫停生產", "停工", "裁員")),
    ("澄清媒體報導（其他）", ("澄清", "媒體報導", "報載", "新聞報導")),
    ("例行（法說、注意交易、董事會、股東會、股利、子公司）", ("法人說明會", "法說會", "投資論壇", "注意交易", "董事會", "股東會", "股利", "子公司",
                                                     "資金貸與", "背書保證", "代子公司", "除權", "除息", "庫藏股", "董事", "監察人", "經理人",
                                                     "會計師", "財務報告", "財務報表", "營收", "自結")),
]


def parse(path):
    t = path.read_bytes().decode("utf-8", errors="replace")
    rows = []
    for form in t.split("<form ")[1:]:
        f = dict(("h0" + k, html.unescape(v)) for k, v in FIELD.findall(form))
        if "h01" in f and "h04" in f:
            rows.append({"date": f.get("h02", ""), "code": f["h01"].strip(), "name": f.get("h00", "").strip(),
                         "subject": f["h04"].strip(), "detail": f.get("h08", "")})
    return rows


def cat_of(r):
    s = r["subject"]
    for name, words in CATS:
        if any(w in s for w in words):
            return name
    return "其他"


allrows, per_day = [], {}
for p in sorted((HERE / "news").glob("*.html")):
    rows = parse(p)
    rows = [r for r in rows if re.fullmatch(r"\d{4}", r["code"])]
    per_day[p.stem] = len(rows)
    for r in rows:
        r["day"] = p.stem
    allrows += rows
print("抽樣日", len(per_day), "｜四碼公司的重訊", len(allrows), "｜每天", sorted(per_day.items()))
cnt = collections.Counter(cat_of(r) for r in allrows)
for name, _w in CATS + [("其他", ())]:
    print("  %-34s %5d（每天 %.1f）" % (name, cnt[name], cnt[name] / len(per_day)))
# 取得設備的重訊：交易相對人是誰（說明欄）
eq = [r for r in allrows if cat_of(r) == "設備或廠房（取得）"]
cp = collections.Counter()
samples = []
for r in eq:
    m = re.search(r"交易相對人[^：:]*[：:]\s*([^\n]{1,80})", r["detail"])
    who = m.group(1).strip() if m else "（沒寫）"
    cp["寫了" if m else "沒寫"] += 1
    samples.append((r["day"], r["code"], r["name"], r["subject"][:40], who[:50]))
print("取得設備或廠房", len(eq), "｜說明欄有「交易相對人」", dict(cp))
for s in samples[:25]:
    print("   ", s)
for name in ("漲價、缺貨、滿載（多在澄清）", "重要合約或長約", "減損、跌價、下修"):
    print("==", name)
    for r in [r for r in allrows if cat_of(r) == name][:12]:
        print("   ", r["day"], r["code"], r["name"], r["subject"][:70])
(HERE / "news_rows.json").write_text(json.dumps(allrows, ensure_ascii=False), encoding="utf-8")
```

### count_b.py（候選事件計數；sha256 前 16 碼 `f9d8c0c024a6dc0a`）

```python
"""回測乙乾跑之二：在抽樣日的重訊裡，數三種「定義得出樣本」的候選事件各幾則；只數，不看價格。"""
import collections
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
rows = json.loads((HERE / "news_rows.json").read_text(encoding="utf-8"))
days = sorted({r["day"] for r in rows})
n_days = len(days)


def per_year(n):
    return n / n_days * 245   # 一年約 245 個交易日


# (a) 買方取得機器設備、交易相對人具名（設備商的訂單）
EQ = re.compile(r"機器設備|生產設備|購置設備|取得設備")
NOT_EQ = re.compile(r"使用權|不動產|土地|廠房|承攬|關係人|處分")
eq = [r for r in rows if EQ.search(r["subject"]) and not NOT_EQ.search(r["subject"])]
cp = []
for r in eq:
    m = re.search(r"交易相對人[^：:\n]*[：:]\s*([^\n，,;；]{1,80})", r["detail"])
    who = m.group(1).strip() if m else ""
    amt = re.search(r"交易總金額[^：:\n]*[：:]\s*([^\n]{1,60})", r["detail"])
    cp.append((r["day"], r["code"], r["name"], who, amt.group(1).strip() if amt else ""))
tw = [x for x in cp if "股份有限公司" in x[3] or re.search(r"\(股\)|（股）", x[3])]
print("(a) 取得機器設備（排除使用權、不動產、關係人）：%d 則（一年約 %.0f）｜交易相對人寫了 %d｜看起來是台灣公司 %d（一年約 %.0f）"
      % (len(eq), per_year(len(eq)), sum(1 for x in cp if x[3]), len(tw), per_year(len(tw))))
for x in cp[:40]:
    print("    ", x[0], x[1], x[2], "｜", x[3][:40], "｜", x[4][:40])
who_cnt = collections.Counter(x[3] for x in cp if x[3])
print("   最常出現的交易相對人：", who_cnt.most_common(12))

# (b) 澄清媒體報導、說明裡講到漲價／缺貨／滿載／訂單
CL = re.compile(r"澄清|媒體報導|報載|新聞報導|說明媒體")
HOT = re.compile(r"漲價|調漲|缺貨|滿載|供不應求|產能吃緊|訂單|接單|交期")
cl = [r for r in rows if CL.search(r["subject"])]
hot = [r for r in cl if HOT.search(r["detail"])]
print("\n(b) 澄清媒體報導 %d 則；說明裡講到漲價、缺貨、滿載、訂單、交期的 %d 則（一年約 %.0f）" % (len(cl), len(hot), per_year(len(hot))))
for r in hot[:15]:
    m = HOT.search(r["detail"])
    i = m.start()
    print("    ", r["day"], r["code"], r["name"], "｜", r["subject"][:30].replace("\r\n", ""), "｜…", r["detail"][max(0, i - 40):i + 50].replace("\n", " "), "…")

# (c) 籌錢：拆成現金增資、可轉債發行、私募、授信，與例行的轉換／付息／買回
RAISE = [("現金增資（發行新股）", r"現金增資"), ("可轉債（發行）", r"(發行|募集).{0,10}(轉換公司債|可轉債)"), ("私募", r"私募"),
         ("授信、聯貸", r"聯合授信|聯貸|授信"), ("轉換、付息、買回、到期（例行）", r"轉換.{0,6}(股份|普通股)|付息|還本|買回|到期|轉換價格|下櫃|終止櫃檯")]
print("\n(c) 籌錢")
for label, pat in RAISE:
    n = sum(1 for r in rows if re.search(pat, r["subject"]))
    print("    %-30s %4d（一年約 %.0f）" % (label, n, per_year(n)))

# (d) 說明裡有「預收」「合約負債」「長期合約」「預付」的（買家綁產能的線索）
BC = re.compile(r"預收貨款|合約負債|長期供貨|長期合約|長約|預付款")
bc = [r for r in rows if BC.search(r["detail"]) and not re.search(r"財務報告|財務報表|會計師", r["subject"])]
print("\n(d) 說明裡講到預收、合約負債、長約、預付的（排除財報類）%d 則（一年約 %.0f）" % (len(bc), per_year(len(bc))))
for r in bc[:10]:
    m = BC.search(r["detail"])
    print("    ", r["day"], r["code"], r["name"], "｜", r["subject"][:40].replace("\r\n", ""), "｜…", r["detail"][max(0, m.start() - 30):m.start() + 40].replace("\n", " "))
print("\n每天的重訊數：", {d: sum(1 for r in rows if r["day"] == d) for d in days})
```

### count_eq.py（取得設備的交易相對人；sha256 前 16 碼 `993c0ce62c2ec7ee`）

```python
"""回測乙乾跑之三：買方「取得機器設備」重訊裡具名的交易相對人，有幾個是台灣上市櫃公司（粗配：上市櫃簡稱出現在全名開頭）。只數。"""
import collections
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"<repo>\library\private\measurement\h17_cache")
import os
os.chdir(r"<repo>\library\private\measurement\h17_cache")
import h17lib as L

HERE = Path(__file__).parent
rows = json.loads((HERE / "news_rows.json").read_text(encoding="utf-8"))
n_days = len({r["day"] for r in rows})
ME = L.month_ends()
_raw, name, _mkt = L.load_quotes(ME)
short = {v: k for k, v in name.items() if v and len(v) >= 2}
EQ = re.compile(r"機器設備|生產設備|購置設備|取得設備")
NOT_EQ = re.compile(r"使用權|不動產|土地|廠房|承攬|處分")
CP = re.compile(r"得免揭露其姓名）[:：]?\s*\r?\n\s*([^\r\n]{1,120})")
eq = [r for r in rows if EQ.search(r["subject"]) and not NOT_EQ.search(r["subject"])]
out = []
for r in eq:
    m = CP.search(r["detail"])
    who = m.group(1).split("；")[0].split(";")[0].strip() if m else ""
    rel = "關係" in (m.group(1) if m else "") and "無" not in (m.group(1).split("關係")[-1][:4] if m else "")
    hit = next((c for s, c in short.items() if who.startswith(s) and c != r["code"]), None)
    out.append((r["day"], r["code"], r["name"], who[:40], "關係企業" if rel else "", hit or ""))
print("取得機器設備 %d 則（%d 個抽樣日；一年約 %.0f）" % (len(eq), n_days, len(eq) / n_days * 245))
print("  交易相對人具名 %d｜其中是關係企業 %d｜配得到上市櫃簡稱 %d（一年約 %.0f）"
      % (sum(1 for x in out if x[3] and "非關係人" not in x[3]), sum(1 for x in out if x[4]), sum(1 for x in out if x[5]),
         sum(1 for x in out if x[5]) / n_days * 245))
for x in out:
    print("   ", x)
print("  買方是誰：", collections.Counter(x[2] for x in out).most_common(10))
```
