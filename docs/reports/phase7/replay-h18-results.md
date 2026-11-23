# H18 結果（回測乙）：硬訊號之後，八成沒漲；判讀的兩條都「不確定」；在風口上那一格有公告的翻倍多一些（事後、只印）

> 日期 2026-11-24｜判讀線：[`registration.md`](registration.md)「新假說 H18」（commit `6019b125`）｜階段一：commit `e92e29fe`｜假結果自查與讀法：commit `a37a0b67`。三筆都早於任何結果的計算。
> **一次判讀，沒有重跑、沒有改門檻。** 只進假說帳，不改任何 filter、候選狀態、排序（G10）。
> 載體：Phase 8 第二個修正案「劇本時間線」（使用者 2026-11-23：「符合劇本但沒漲的 這個有回測過嗎？ 感覺這個反面是我們要去看一次的不然盲點很大？」）。

## 白話版（先讀這段）

**問的問題**：媒體寫了某家公司漲價、缺貨、滿載、接到訂單，公司出來澄清——這種「符合劇本」的時刻之後，有幾成真的漲？比沒有這種公告的股票多嗎？（台股 2017–2024，865 次、515 檔）

1. **大多數沒漲**：24 個月內漲到 2 倍的只有 20%，跟同期隨便一檔（20.5%）一樣；一年後一半跌破公告那個月的價格。**「符合劇本卻沒漲」是常態，不是例外。**
2. **一年內漲到 2 倍的稍微多一點**（10.4% 對 8.5%），但差不到事先定的 3 個百分點，判「不確定」。跟同月、前一年漲幅差不多的股票比，差更小（+1.8），也是「不確定」。
3. **只算「漲價、缺貨、滿載」這種最硬的**（193 次），差比較大（+6 個百分點），但這一條事先只登記成「只印」，而且差距全在 2017–2020 年（2021 年以後幾乎是 0）——不能當結論。
4. **你問的「浪潮中走得快的」**：前一年漲最多的那一群（已經在風口上）裡，有這種公告的，一年內漲到 2 倍 16% 對沒有的 10%，兩年 25% 對 21%——多出來的不是衝一下又掉回來。
   但典型的一檔兩邊一樣：一年後一半跌破起點。也就是多了**少數大贏家**，不是大家都比較好。這一格是看過結果才並排的，要當真得另外登記、換一段期間測。
5. 前一年漲得少的三群（五分位 0–2）裡，有這種公告的反而**比較差**（一年內漲到 2 倍 4–6% 對 7–9%）。同一句「漲價、缺貨、訂單」，出現在已經在漲的股票上和沒在漲的股票上，後面不一樣。

**它回答不了的**：只量了一種硬訊號（媒體報導＋公司出來澄清），不是劇本的整套、不是公司自己主動發的；只有台股、2017–2024，不是 AI 這一波、不是美股。

**怎麼用**：照登記的後果——「不確定」照實寫；劇本卡上硬訊號那一格可以寫「回測乙：澄清公告這一種，之後一年翻倍的機會只比隨便一檔多一點，沒過事先的線；八成兩年內沒翻倍」。不接任何門檻、不改任何候選狀態。

## 判讀

判讀的兩條（ALPHA＝0.05 ÷ 2＝0.025；支持要 Δ ≥ 3 個百分點）。Δ＝層內「事件比例 − 對照比例」的 Mantel–Haenszel 加權平均，主量＝12 個月內月收盤曾達 t 收盤 2 倍。

| 條 | 事件 | 事件／對照 12 個月內曾達 2 倍 | Δ | W | p | 95% 區間 | 前段／後段 Δ（事件數） | 拿掉 2017 年 | 24 個月版 Δ | 判讀 |
|---|---:|---|---:|---:|---:|---|---|---:|---:|---|
| 寬 × 同月全市場 | 864 | 10.4%／8.5% | +2.2 | 857.3 | 0.0134 | −0.0～+4.3 | +1.6（565）／+3.2（299） | +1.0 | +0.8 | **不確定** |
| 寬 × 同月同漲幅五分位 | 803 | 10.6%／8.4% | +1.8 | 793.2 | 0.0402 | −0.6～+4.2 | +1.3（522）／+2.6（281） | +0.8 | +1.5 | **不確定** |

- 兩條都沒到「支持」：Δ 不到 3 個百分點（第一條 p 過了 0.025，第二條沒過）；也沒到「削弱」：區間上界都在 3 個百分點以上（4.3、4.2）。
- 存活者的界限只在判成支持或削弱時才算（登記第 5 條）；兩條都是不確定，沒有算。
- 結果側資料旗標剔除 1 筆（寬）。

只印的兩條（窄定義；登記第 6 條「同樣算、只印」）：

| 條 | 事件 | 事件／對照 | Δ | p | 區間 | 前段／後段 Δ（事件數） | 拿掉 2021 年 | 24 個月版 Δ | 照判讀規則會是 |
|---|---:|---|---:|---:|---|---|---:|---:|---|
| 窄 × 同月全市場 | 193 | 14.5%／8.5% | +6.2 | 0.0034 | +1.4～+10.8 | +9.3（122）／+0.9（71） | +7.2 | +2.9 | 支持（只印） |
| 窄 × 同月同漲幅五分位 | 183 | 15.3%／8.4% | +6.1 | 0.0029 | +1.1～+11.0 | +9.8（114）／+0.1（69） | +7.4 | +4.6 | 支持（只印） |

**窄的這兩條不能升格成結論**：它們登記時就是只印；而且後段（2021 年以後）的 Δ 幾乎是 0、只有 69–71 個事件，整個差來自 2017–2020（2017 年被動元件那一段：38 個事件裡 10 個一年內翻倍）。要當真得另登一筆、用新的期間測。

## 讀這個結果要一起看的四件事

1. **「同月全市場」那一條本來就偏正**（假結果自查，commit `a37a0b67`）：事件集中在前一年漲最多的五分位（804 個裡 321 個），在「前一年漲越多越容易翻倍」的世界裡，這一條在公告完全沒作用時也會偏正。所以它的 +2.2 讀成「有這種公告的股票翻倍的比隨便一檔多一點」，**不讀成「公告本身有用」**；公告本身看第二條（+1.8，不確定）。
2. **五分位兩頭方向相反**：前一年漲幅五分位 0、1、2 的事件，一年內曾達 2 倍 5.8%、5.7%、4.4%，對照 8.9%、7.5%、7.4%——事件比較差；五分位 3、4 是 10.8% 對 8.2%、15.9% 對 10.3%——事件比較好。第二條的 +1.8 是兩頭抵銷之後的平均。
3. **年分**（寬，事件 12 個月內曾達 2 倍）：2017 22／165、2018 6／139、2019 7／142、2020 21／119、2021 11／128、2022 11／73、2023 9／56、2024 3／42。事件數逐年變少（原因沒有查）。
4. **「曾達 2 倍」不等於「抱一年賺一倍」**：一年後低於公告當月價格的，事件 49.7%、對照 42.3%；一年超額中位數事件 −12.6、對照 −9.3。翻倍的多一點，但典型的一檔沒有比較好。

## 另印（登記第 8 條；不進判讀）

寬（事件 864）與同期全部對照（147,655 列，每一列＝一檔一個月）：

| 群 | n | 12 個月內曾達 2 倍 | 24 個月內曾達 2 倍 | 24 個月都沒到 2 倍 | 12 個月後低於起點 | 12 個月超額 平均／中位數 |
|---|---:|---:|---:|---:|---:|---|
| 事件 | 864 | 10.4% | 20.3% | **79.7%** | 49.7% | +0.2／−12.6 |
| 對照（同期全部） | 147,655 | 8.5% | 20.5% | 79.5% | 42.3% | +0.6／−9.3 |
| 說明有否認字眼 | 128 | 10.9% | 23.4% | 76.6% | 47.7% | +4.7／−12.1 |
| 沒有否認字眼 | 736 | 10.3% | 19.7% | 80.3% | 50.0% | −0.6／−12.9 |
| 公告前 24 個月已漲一倍以上 | 177 | 9.6% | 19.8% | 80.2% | 66.1% | −10.0／−26.4 |
| 公告前 24 個月沒漲一倍 | 581 | 10.8% | 21.3% | 78.7% | 42.5% | +3.8／−8.5 |

依前一年漲幅五分位（事件；最後一欄是同一格對照的 12 個月內曾達 2 倍）：

| 五分位 | 事件 n | 12 個月內曾達 2 倍 | 24 個月內曾達 2 倍 | 12 個月後低於起點 | 12 個月超額 平均／中位數 | 對照 12 個月內曾達 2 倍 |
|---|---:|---:|---:|---:|---|---:|
| 0（最低） | 104 | 5.8% | 13.5% | 50.0% | −4.2／−12.3 | 8.9% |
| 1 | 106 | 5.7% | 19.8% | 45.3% | −1.0／−10.6 | 7.5% |
| 2 | 114 | 4.4% | 17.5% | 44.7% | −3.7／−7.5 | 7.4% |
| 3 | 158 | 10.8% | 20.3% | 44.3% | +0.7／−7.6 | 8.2% |
| **4（最高＝已經在風口上）** | 321 | **15.9%** | 25.2% | 52.0% | +3.9／−18.2 | **10.3%** |

窄（事件 193）：12 個月內曾達 2 倍 14.5%、24 個月 22.3%、24 個月都沒到 2 倍 77.7%、12 個月後低於起點 47.7%、超額平均 +4.4／中位數 −12.0；
最高五分位 94 個事件 20.2%（對照 10.3%）；其餘四格 13–36 個事件，太少，不列。依年（窄）：2017 10／38、2018 0／26、2019 4／30、2020 8／28、2021 5／48、2022 1／13、2023 0／6、2024 0／4。

## 事後（看過階段二的結果才加的；不進判讀、不改任何判讀）

另印的最高五分位只印了對照的 12 個月比例；為了回答「多出來的翻倍是不是衝一下又掉回來」，把那一格的事件與對照完整並排（腳本 `posthoc_top.py`）：

| 最高五分位 | n | 12 個月內曾達 2 倍（第 12 個月已回到 2 倍以下） | 24 個月內曾達 2 倍 | 12 個月後低於起點 | 12 個月超額 中位數／平均 | 24 個月超額 中位數／平均 |
|---|---:|---|---:|---:|---|---|
| 寬：事件 | 321 | 15.9%（4.4%） | 25.2% | 52.0% | −18.2／+3.9 | −31.4／−1.6 |
| 寬：對照 | 27,141 | 10.3%（4.0%） | 20.6% | 50.2% | −15.0／−2.9 | −29.0／−6.6 |
| 窄：事件 | 94 | 20.2%（5.3%） | 25.5% | 51.1% | −17.9／+10.4 | −22.7／−2.0 |

月內加權的 Δ：寬 12 個月 +5.3、24 個月 +5.5 個百分點；窄 +9.6、+6.8。
**讀法**：多出來的翻倍到 24 個月還在；但中位數兩邊差不多（都約一半一年後跌破起點）——多的是右尾，不是整群往上。
這是事後挑出來看的一格，而且「已經在風口上」的定義（前一年漲幅最高的五分之一）是我們定的；要當真得另登一筆前向假說、換一段期間（例：2010–2016，或 AI 這一波的美股）測。

## 後果（照登記第 9 條，一字不改地套）

兩條都是**不確定** → 照實寫。給使用者的一句：「媒體寫了漲價、缺貨、訂單，公司出來澄清——之後一年翻倍的機會只比隨便一檔多一點（+2 個百分點），沒過事先的線；跟同樣已經漲過的股票比更分不出來。八成兩年內沒翻倍。」
劇本卡上硬訊號那一格可以附這一句；**不改任何 filter、候選狀態、排序、門檻**。「沒漲的占幾成」照登記交付（上面另印的表）：它就是劇本卡缺的反例。

## 偏差標註（登記第 10 條＋這次看到的）

①只量了一種硬訊號（媒體報導＋公司澄清），不是劇本的整套，也不是公司自己主動發布的訊號；澄清多半在股價異動之後，起點偏晚（事件集中在最高五分位印證了這一點）
②關鍵詞是機械的，混著法人預估、報社轉述與公司否認；否認字眼的那 128 個另印，結果與其餘差不多
③只有台股、八年，事件在時間上成群（2017 被動元件）；窄的那兩條的差幾乎全在前段
④對照組只排除了有這種公告的股票，沒有排除其他好消息
⑤月底收盤、等權；「曾達 2 倍」是月底收盤碰到就算，不是抱到第 12 個月
⑥3 個百分點的門檻是用假結果的判讀力選的（登記第 7 條）
⑦分析的人知道這段期間的大致行情
⑧事件逐年變少（2017 165 → 2024 42），原因沒有查；後段樣本較薄

## 計數與資料

- 重訊 2,044 天（2017-01-02～2024-10-31 的每一個平日）、653,479 則；命中寬定義 2,087 則；不在宇宙內 406；12 個月內重複 816 → 寬事件 865（515 檔）；窄 193。
- 階段二：寬的事件 864（結果側資料旗標剔除 1）、同月同漲幅那一條 803（前一年漲幅算不出的 61 只進第一條）。對照 147,655 列。
- 行情與還原沿用 H17（交易所月底全市場行情、除權息／減資／面額變更因子，2011-12～2026-10）；沒有用 yfinance。

## 檔案

- [h18-stage1-events.csv](h18-stage1-events.csv)：命中寬定義的每一則公告（含沒算進去的），sha256 `af4d8d92…`（階段一登記）。
- [h18-stage2-outcomes.csv](h18-stage2-outcomes.csv)：每個事件的結果（寬、窄），sha256 前 16 碼 `1abb1ad4df328820`（以 LF 換行算）。
- 本機私有區 `library/private/measurement/b_full/`（重訊原始檔）、`h18_cache/`（腳本、私有中間檔、執行紀錄）；不進 repo。

## 獨立覆核

（使用者 2026-11-23 選「開」；審查者唯讀、不改判讀。結果交回後附在這裡。）

## 腳本（逐字）

### fetch_news.py（抓全期重訊；sha256 前 16 碼 `5a286e0992a36216`）

```python
"""回測乙：抓全期的歷史重大訊息（公開資訊觀測站，依日期）。端點與請求內容與乾跑的 probe_news.py 相同。
範圍：2017-01-02 ～ 2024-10-31 的每一個平日（假日回空頁，照存）。已有的檔跳過，可重跑續抓。
節流 6 秒；對外請求不帶任何個人資訊。只存原始回應，不解析、不看價格。
用法：python fetch_news.py [起 YYYY-MM-DD] [迄 YYYY-MM-DD]"""
import datetime as dt
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
start = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date(2017, 1, 2)
end = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2024, 10, 31)
day, n_new, n_fail = start, 0, 0
while day <= end:
    if day.weekday() < 5:
        y, m, d = "%03d" % (day.year - 1911), "%02d" % day.month, "%02d" % day.day
        dest = OUT / f"{y}_{m}_{d}.html"
        if not dest.exists():
            body = f"encodeURIComponent=1&step=1&step00=0&firstin=1&off=1&TYPEK=all&year={y}&month={m}&day={d}"
            try:
                r = requests.post(URL, data=body, headers=UA, timeout=60)
                if r.status_code == 200:
                    dest.write_bytes(r.content)
                    n_new += 1
                else:
                    n_fail += 1
                print(day, r.status_code, len(r.content), flush=True)
            except Exception as exc:  # noqa: BLE001
                n_fail += 1
                print(day, "失敗", type(exc).__name__, flush=True)
            time.sleep(6)
    day += dt.timedelta(days=1)
print("FETCH_DONE 新抓", n_new, "失敗", n_fail, flush=True)
```

### next_chunk.py（前景分段續抓的起訖；sha256 前 16 碼 `a0ac47ad94b09512`）

```python
"""前景分段續抓用：從 news/ 已有的最後一天之後算下一段的起訖（約 N 個平日，預設 45），印「起 迄」；抓完印 DONE。
不改 fetch_news.py 的抓法；只決定它的兩個參數。用法：python next_chunk.py [平日數]"""
import datetime as dt
import sys
from pathlib import Path

END = dt.date(2024, 10, 31)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 45
have = sorted(Path(__file__).parent.joinpath("news").glob("*.html"))
y, m, d = map(int, have[-1].stem.split("_"))
day = dt.date(y + 1911, m, d) + dt.timedelta(days=1)
if day > END:
    print("DONE")
    sys.exit(0)
start, k = day, 0
while day <= END:
    if day.weekday() < 5:
        k += 1
        if k == n:
            break
    day += dt.timedelta(days=1)
print(start.isoformat(), min(day, END).isoformat())
```

### check_files.py（核檔案完整；sha256 前 16 碼 `7cd6b7b566cf335c`）

```python
"""檢查 news/ 每個檔是不是完整的回應（有 </html> 收尾）；不完整的列出，帶 --delete 就刪掉（下一段續抓會重抓）。"""
import sys
from pathlib import Path

bad = []
files = sorted(Path(__file__).parent.joinpath("news").glob("*.html"))
for p in files:
    tail = p.read_bytes()[-400:].lower()
    if b"</html>" not in tail:
        bad.append(p)
print("檔", len(files), "｜不完整", len(bad), [p.name for p in bad][:20])
if "--delete" in sys.argv:
    for p in bad:
        p.unlink()
    print("已刪", len(bad))
```

### h18lib.py（共用：拆重訊、事件定義、事件月；sha256 前 16 碼 `0256af273d6b8378`）

```python
"""H18（回測乙）共用：拆重大訊息、事件定義（關鍵詞寫死）、事件月。行情與還原沿用 h17_cache/h17lib.py。這一支不判任何東西。

事件定義的兩條正規式（CL、HOT）逐字取自回測乙乾跑的 count_b.py（sha256 前 16 碼 f9d8c0c024a6dc0a，已 commit 在
docs/reports/phase7/replay-b-hard-signal-dryrun.md）；NARROW 是 HOT 的子集（只留漲價、缺貨、滿載類）；DENY 只印、不進定義。"""
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "h17_cache"))
import h17lib as L  # noqa: E402,F401

NEWS = HERE.parent / "b_full" / "news"
FIELD = re.compile(r"name='h\d*?(\d)' value='(.*?)'>", re.S)   # 欄名＝h＋列號＋欄號；欄 0 名稱、1 代號、2 發言日期、3 發言時間、4 主旨、8 說明
CL = re.compile(r"澄清|媒體報導|報載|新聞報導|說明媒體")
HOT = re.compile(r"漲價|調漲|缺貨|滿載|供不應求|產能吃緊|訂單|接單|交期")
NARROW = re.compile(r"漲價|調漲|缺貨|滿載|供不應求|產能吃緊")
DENY = re.compile(r"不實|並非|純屬臆測|揣測|未曾|非本公司")
CLOSE_HHMMSS = 133000


def parse(path):
    """一天的重訊頁 → [{code, name, date (YYYY-MM-DD), time (int HHMMSS), subject, detail}]。"""
    t = path.read_bytes().decode("utf-8", errors="replace")
    rows = []
    for form in t.split("<form ")[1:]:
        f = dict(("h0" + k, html.unescape(v)) for k, v in FIELD.findall(form))
        if "h01" in f and "h04" in f and re.fullmatch(r"\d{8}", f.get("h02", "").strip()):
            d = f["h02"].strip()
            tm = re.sub(r"\D", "", f.get("h03", "")) or "0"
            rows.append({"code": f["h01"].strip(), "name": f.get("h00", "").strip(), "date": f"{d[:4]}-{d[4:6]}-{d[6:]}",
                         "time": int(tm), "subject": f["h04"].strip(), "detail": f.get("h08", "")})
    return rows


def event_month(date, time, ME):
    """事件月 t＝第一個「月底收盤在公告之後」的月：公告日早於該月底交易日，或同一天且發言時間早於 13:30:00。"""
    for ym in sorted(ME):
        me = ME[ym]
        if date < me or (date == me and time < CLOSE_HHMMSS):
            return ym
    return None


def kinds(row):
    """回 (wide, narrow, deny)：wide＝主旨 CL 且說明 HOT；narrow＝主旨 CL 且說明 NARROW；deny 只印。"""
    if not CL.search(row["subject"]):
        return 0, 0, 0
    return int(bool(HOT.search(row["detail"]))), int(bool(NARROW.search(row["detail"]))), int(bool(DENY.search(row["detail"])))
```

### stage1.py（階段一：事件表與對照組；sha256 前 16 碼 `927e091b68657957`）

```python
"""H18 階段一：事件表與對照組（只讀每個事件月 t 以前的行情；不讀、不算任何 t 之後的東西）。
用法：python stage1.py [--news 目錄] [--dry]
  --news：重訊原始檔的資料夾（預設 b_full/news；在登記之前只准拿乾跑的 b_dryrun/news 試跑）
  --dry：只印計數、不寫輸出檔（試跑用）
輸出（不帶 --dry）：docs/reports/phase7/h18-stage1-events.csv（公開：代號、日期、旗標）、stage1_private.json（事件＋對照組）、stage1_digest.json。"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import h18lib as H

L = H.L
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
REPO = HERE.parents[3]
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else REPO / "docs" / "reports" / "phase7"   # --out 只給試跑用
T_FROM, T_TO = "2017-01", "2024-10"
DRY = "--dry" in sys.argv
NEWS = Path(sys.argv[sys.argv.index("--news") + 1]) if "--news" in sys.argv else H.NEWS

ME = L.month_ends()
YMS = sorted(ME)
IDX = {ym: i for i, ym in enumerate(YMS)}
raw, name, _market = L.load_quotes(ME, upto=T_TO)
fac, _fstat = L.load_factors()
cut = ME[T_TO]
fac = {c: [x for x in v if x[0] <= cut] for c, v in fac.items()}   # 只用 ≤ T_TO 的公司行動
dr = {c for c in raw if L.is_dr(name.get(c, ""))}
adj = {c: L.adjusted(s, ME, fac.get(c, ())) for c, s in raw.items() if c not in dr}
assert max(ym for s in raw.values() for ym in s) <= T_TO, "讀到 T_TO 之後的行情"

# ---------- 重訊 ----------
files = sorted(NEWS.glob("*.html"))
rows, n_all = [], 0
for p in files:
    for r in H.parse(p):
        n_all += 1
        if not L.CODE.match(r["code"]):
            continue
        w, n, d = H.kinds(r)
        if not w:
            continue
        t = H.event_month(r["date"], r["time"], ME)
        r.update(wide=w, narrow=n, deny=d, t=t)
        rows.append(r)
rows.sort(key=lambda r: (r["date"], r["time"], r["code"]))
print("重訊檔", len(files), "天｜重訊", n_all, "則｜澄清且說明命中寬定義", len(rows), "則（含重複、含期間外）")


def r_over(c, t, k):
    s = adj.get(c, {})
    a = YMS[IDX[t] - k] if IDX[t] - k >= 0 else None
    return s[t] / s[a] - 1 if a and t in s and a in s else None


def unadj_flag(c, t, k=12):
    s = adj.get(c, {})
    seq = [s[YMS[j]] for j in range(max(0, IDX[t] - k), IDX[t] + 1) if YMS[j] in s]
    return int(any(not (0.2 <= b / a <= 5) for a, b in zip(seq, seq[1:])))


# ---------- 每月的橫斷面：前 12 個月漲幅的五分位（只用 ≤ t） ----------
quint = {}
for t in YMS[IDX[T_FROM]:IDX[T_TO] + 1]:
    vals = sorted((r_over(c, t, 12), c) for c in adj if t in adj[c] and r_over(c, t, 12) is not None)
    n = len(vals)
    quint[t] = {c: min(4, (i * 5) // n) for i, (_v, c) in enumerate(vals)}

# ---------- 事件：去重（同一檔在一個算進去的事件之後 12 個月內不再認），寬、窄各自去重 ----------
events, seen_last = [], {"wide": {}, "narrow": {}}
announce_months = {}   # 代號 → 有寬定義公告的事件月（含沒算進去的），對照組排除用
for r in rows:
    if r["t"] is None:
        continue
    announce_months.setdefault(r["code"], set()).add(r["t"])
    if not (T_FROM <= r["t"] <= T_TO):
        continue
    in_univ = r["code"] in adj and r["t"] in adj[r["code"]]
    rec = {"code": r["code"], "name": r["name"], "date": r["date"], "time": r["time"], "t": r["t"], "wide": r["wide"], "narrow": r["narrow"],
           "deny": r["deny"], "in_universe": int(in_univ), "subject": r["subject"][:60].replace("\n", " ")}
    for d in ("wide", "narrow"):
        ok = r[d] and in_univ
        last = seen_last[d].get(r["code"])
        counted = int(bool(ok and (last is None or IDX[r["t"]] - IDX[last] >= 12)))
        if counted:
            seen_last[d][r["code"]] = r["t"]
        rec[f"counted_{d}"] = counted
    if in_univ:
        rec["r12"] = r_over(r["code"], r["t"], 12)
        rec["r24"] = r_over(r["code"], r["t"], 24)
        rec["quintile"] = quint[r["t"]].get(r["code"])
        rec["flag_unadj"] = unadj_flag(r["code"], r["t"])
    events.append(rec)

# ---------- 對照組：同月在宇宙內、前 12 個月沒有寬定義公告的股票 ----------
controls = {}
for t in YMS[IDX[T_FROM]:IDX[T_TO] + 1]:
    lst = []
    for c in adj:
        if t not in adj[c]:
            continue
        if any(0 <= IDX[t] - IDX[m] <= 12 for m in announce_months.get(c, ()) if m in IDX):
            continue
        lst.append([c, quint[t].get(c), unadj_flag(c, t)])
    controls[t] = sorted(lst)

for d in ("wide", "narrow"):
    ev = [e for e in events if e[f"counted_{d}"]]
    print("%s：算進去的事件 %d｜其中資料旗標 %d｜說明有否認字眼 %d｜前一年漲幅算不出 %d" %
          ({"wide": "寬", "narrow": "窄"}[d], len(ev), sum(e["flag_unadj"] for e in ev), sum(e["deny"] for e in ev),
           sum(e["quintile"] is None for e in ev)))
    per_year = {}
    for e in ev:
        per_year[e["t"][:4]] = per_year.get(e["t"][:4], 0) + 1
    print("   每年：", dict(sorted(per_year.items())))
print("對照組：每月平均 %.0f 檔" % (sum(len(v) for v in controls.values()) / max(1, len(controls))))

if DRY:
    print("（--dry：不寫輸出檔）")
    sys.exit(0)

cols = ["code", "name", "date", "time", "t", "wide", "narrow", "counted_wide", "counted_narrow", "deny", "in_universe", "quintile", "flag_unadj", "subject"]
csv_path = OUT / "h18-stage1-events.csv"
with csv_path.open("w", encoding="utf-8", newline="\n") as fh:
    wr = csv.writer(fh, lineterminator="\n")
    wr.writerow(cols)
    for e in events:
        wr.writerow([e.get(k, "") if e.get(k) is not None else "" for k in cols])
priv = (OUT if "--out" in sys.argv else HERE) / "stage1_private.json"
priv.write_text(json.dumps({"events": events, "controls": controls, "news_files": len(files)}, ensure_ascii=False), encoding="utf-8", newline="\n")
dg = {"events": L.sha256_lf(csv_path), "private": hashlib.sha256(priv.read_bytes()).hexdigest(),
      "stage1_py": hashlib.sha256((HERE / "stage1.py").read_bytes()).hexdigest()[:16]}
((OUT if "--out" in sys.argv else HERE) / "stage1_digest.json").write_text(json.dumps(dg, ensure_ascii=False, indent=1), encoding="utf-8")
print("寫出", csv_path.name, dg)
```

### stage1_counts.py（階段一的計數；sha256 前 16 碼 `982c41eb4d6260f4`）

```python
"""H18 階段一的計數（給登記用；只讀 stage1_private.json，不讀任何 t 之後的價格）。"""
import collections
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
S = json.loads((Path(__file__).parent / "stage1_private.json").read_text(encoding="utf-8"))
ev = S["events"]
inper = ev  # stage1 只把 t 在期間內的寫進 events
print("期間內命中寬定義的公告", len(inper), "｜在宇宙內", sum(e["in_universe"] for e in inper),
      "｜不在宇宙內（四碼以外、興櫃、DR、t 月底沒收盤）", sum(1 - e["in_universe"] for e in inper))
w = [e for e in inper if e["in_universe"]]
print("在宇宙內的寬定義公告", len(w), "｜算進去", sum(e["counted_wide"] for e in w), "｜12 個月內重複、沒算", len(w) - sum(e["counted_wide"] for e in w))
cw = [e for e in w if e["counted_wide"]]
print("算進去的寬事件：檔數", len({e["code"] for e in cw}), "｜同時也是窄事件", sum(e["counted_narrow"] for e in cw),
      "｜前 24 個月已漲一倍以上", sum(1 for e in cw if e.get("r24") is not None and e["r24"] >= 1),
      "｜五分位分布", dict(sorted(collections.Counter(e["quintile"] for e in cw).items(), key=lambda x: (x[0] is None, x[0]))))
print("事件月分布（前 5 名）", collections.Counter(e["t"] for e in cw).most_common(5))
print("主旨最常見的前 8 種（前 12 字）", collections.Counter(e["subject"][:12] for e in cw).most_common(8))
cols = ["code", "name", "date", "time", "t", "wide", "narrow", "counted_wide", "counted_narrow", "deny", "in_universe", "quintile", "flag_unadj", "subject"]
bad = [c for c in cols if any(x in c for x in ("x2", "ret", "ex_", "crash", "outcome", "after"))]
print("事件表欄名含結果用字：", bad or "無")
```

### stage2.py（階段二：結果與判讀；sha256 前 16 碼 `865d32872ef03cef`）

```python
"""H18 階段二：結果與判讀（一次）。判讀線＝registration.md「新假說 H18」；階段一的事件表與對照組先驗 digest。
用法：python stage2.py                       → 真的結果（只跑一次；寫逐事件結果檔與摘要）
      python stage2.py --synthetic 種子 [--plant 效果]
                                             → 假結果自查：每一檔（事件與對照）的結果換成「同一格對照組的比例」抽出的假結果，
                                               --plant 0.08＝事件那一邊多 8 個百分點；真的結果在任何彙總印出之前就被蓋掉，不寫輸出檔
判讀的組合由 JUDGED 決定（登記時寫死）；ALPHA＝0.05 ÷ 判讀條數。"""
import collections
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

import h18lib as H

L = H.L
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
REPO = HERE.parents[3]
TEST_OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None   # 只給試跑用：讀這裡的階段一、不寫任何輸出
OUT = TEST_OUT or REPO / "docs" / "reports" / "phase7"
PRIV = TEST_OUT or HERE
SEED, N_PERM, N_BOOT = 20261124, 10000, 2000
#: 登記時寫死：(定義, 比較)；定義 ∈ wide／narrow，比較 ∈ month（同月全市場）／month_q（同月、前一年漲幅同五分位）
JUDGED = [("wide", "month"), ("wide", "month_q")]
PRINTED = [("narrow", "month"), ("narrow", "month_q")]
ALPHA = 0.05 / len(JUDGED)
SUPPORT, DROP_TOP, MIN_N, MIN_W, WEAK_N = 0.03, 0.015, 100, 50, 150
SYN = "--synthetic" in sys.argv
syn_seed = int(sys.argv[sys.argv.index("--synthetic") + 1]) if SYN else None
PLANT = float(sys.argv[sys.argv.index("--plant") + 1]) if "--plant" in sys.argv else 0.0
FAKE_EVENTS = int(sys.argv[sys.argv.index("--fake-events") + 1]) if "--fake-events" in sys.argv else 0
assert SYN or not FAKE_EVENTS, "--fake-events 只准配 --synthetic"

# ---------- 驗階段一 ----------
assert SYN or TEST_OUT is None, "試跑（--out）只准配 --synthetic"
dg = json.loads((PRIV / "stage1_digest.json").read_text(encoding="utf-8"))
assert L.sha256_lf(OUT / "h18-stage1-events.csv") == dg["events"], "事件表 digest 不符"
assert hashlib.sha256((PRIV / "stage1_private.json").read_bytes()).hexdigest() == dg["private"], "階段一私有檔 digest 不符"
S1 = json.loads((PRIV / "stage1_private.json").read_text(encoding="utf-8"))
print("階段一 digest 相符｜事件列", len(S1["events"]), "｜對照月", len(S1["controls"]))

# ---------- 全段行情 ----------
ME = L.month_ends()
YMS = sorted(ME)
IDX = {ym: i for i, ym in enumerate(YMS)}
raw, name, _market = L.load_quotes(ME)
fac, _fstat = L.load_factors()
dr = {c for c in raw if L.is_dr(name.get(c, ""))}
mkt, _u, _d = L.market_returns(raw, fac, ME, drop_dr_names=dr)
adj = {c: L.adjusted(s, ME, fac.get(c, ())) for c, s in raw.items() if c not in dr}
LAST = YMS[-1]


def outcome(c, t):
    """以 t 月底還原收盤為起點；窗＝t 之後第 1 到第 24 個月。"""
    s, i = adj[c], IDX[t]
    p0 = s[t]
    win = [(k, s[YMS[i + k]]) for k in range(1, 25) if i + k < len(YMS) and YMS[i + k] in s]
    o = {}
    for h in (12, 24):
        sub = [(k, p) for k, p in win if k <= h]
        o[f"x2_{h}"] = int(any(p >= 2 * p0 for _k, p in sub))
        o[f"ret_{h}"] = (sub[-1][1] / p0 - 1) if sub else 0.0
        m = L.mkt_cum(mkt, t, YMS[i + h]) if i + h < len(YMS) else None
        o[f"ex_{h}"] = None if m is None else o[f"ret_{h}"] - m
    last_ym = max(s)
    o["delisted_12"] = int(last_ym < YMS[min(i + 12, len(YMS) - 1)] and last_ym < LAST)
    seq = [p0] + [p for _k, p in win]
    o["flag_unadj_out"] = int(any(not (0.2 <= b / a <= 5) for a, b in zip(seq, seq[1:])))
    return o


# ---------- 組資料：每一列＝(事件或對照, 代號, t, 五分位) ----------
def build(defn):
    ev = [e for e in S1["events"] if e[f"counted_{defn}"] and not e["flag_unadj"]]
    rows = []
    for e in ev:
        rows.append({"g": 1, "code": e["code"], "t": e["t"], "q": e["quintile"], "deny": e["deny"], "r24": e.get("r24"), **outcome(e["code"], e["t"])})
    for t, lst in S1["controls"].items():
        for c, q, flag in lst:
            if flag:
                continue
            rows.append({"g": 0, "code": c, "t": t, "q": q, "deny": 0, "r24": None, **outcome(c, t)})
    flagged_out = [r for r in rows if r["flag_unadj_out"]]
    rows = [r for r in rows if not r["flag_unadj_out"]]
    if FAKE_EVENTS:   # 只給假結果自查：從對照組隨機挑 N 列當事件（真的事件拿掉），看判讀力
        frng = np.random.default_rng(syn_seed + 7)
        rows = [r for r in rows if r["g"] == 0]
        for j in frng.choice(len(rows), size=min(FAKE_EVENTS, len(rows)), replace=False):
            rows[j]["g"] = 1
    return rows, len(ev), flagged_out


DATA = {d: build(d) for d in ("wide", "narrow")}

# ---------- 假結果（自查用）：在任何彙總印出之前蓋掉 ----------
if SYN:
    # 假的基準率是寫死的常數（不從真的結果推，免得自查時就看到真的對照組比例）；五分位越高假基準率越高，讓分層有事做。
    rng = np.random.default_rng(syn_seed)
    FAKE12 = {None: 0.10, 0: 0.06, 1: 0.07, 2: 0.09, 3: 0.12, 4: 0.16}
    for d, (rows, _n, _f) in DATA.items():
        for r in rows:
            b12 = FAKE12[r["q"]]
            add = PLANT if r["g"] == 1 else 0.0
            r["x2_12"] = int(rng.random() < min(1.0, b12 + add))
            r["x2_24"] = int(r["x2_12"] or rng.random() < 0.10 + add / 2)
            r["ret_12"] = float(rng.normal(0.0, 0.4))
            r["ex_12"] = r["ret_12"]
    print("（假結果：種子 %d、植入 %+.2f；以下數字全是假的）" % (syn_seed, PLANT))


# ---------- 統計 ----------
def strata_key(r, comp):
    return r["t"] if comp == "month" else (r["t"], r["q"])


def mh(rows, comp, y="x2_12"):
    """層內加權（Mantel–Haenszel）的「事件比例 − 對照比例」。回 (Δ, W, n_event, n_control, 事件比例, 對照比例)。"""
    cell = collections.defaultdict(lambda: [[], []])
    for r in rows:
        if comp == "month_q" and r["q"] is None:
            continue
        cell[strata_key(r, comp)][r["g"]].append(r[y])
    num = den = 0.0
    ne = nc = 0
    for c0, c1 in cell.values():
        if c1 and c0:
            w = len(c1) * len(c0) / (len(c1) + len(c0))
            num += w * (np.mean(c1) - np.mean(c0))
            den += w
            ne += len(c1)
            nc += len(c0)
    ev = [r[y] for r in rows if r["g"] == 1 and (comp == "month" or r["q"] is not None)]
    co = [r[y] for r in rows if r["g"] == 0 and (comp == "month" or r["q"] is not None)]
    return (num / den if den else float("nan")), den, ne, nc, (float(np.mean(ev)) if ev else float("nan")), (float(np.mean(co)) if co else float("nan"))


def perm_boot(rows, comp, obs):
    use = [r for r in rows if comp == "month" or r["q"] is not None]
    keys = sorted({strata_key(r, comp) for r in use}, key=str)
    ki = {k: j for j, k in enumerate(keys)}
    rng = np.random.default_rng(SEED)
    num, den = np.zeros(N_PERM), 0.0
    by = collections.defaultdict(list)
    for r in use:
        by[ki[strata_key(r, comp)]].append(r)
    for j, rs in by.items():
        y = np.array([r["x2_12"] for r in rs], dtype=float)
        g = np.array([r["g"] for r in rs])
        n, k = len(rs), int(g.sum())
        if k == 0 or k == n:
            continue
        w = k * (n - k) / n
        tot = y.sum()
        for a in range(0, N_PERM, 1000):
            b = min(N_PERM, a + 1000)
            idx = np.argpartition(rng.random((b - a, n)), k - 1, axis=1)[:, :k]
            s1 = y[idx].sum(axis=1)
            num[a:b] += w * (s1 / k - (tot - s1) / (n - k))
        den += w
    perm = num / den
    p = (1 + int((perm >= obs - 1e-12).sum())) / (N_PERM + 1)
    # bootstrap：以事件月為抽樣單位
    rng = np.random.default_rng(SEED + 1)
    months = sorted({r["t"] for r in use})
    mi = {m: j for j, m in enumerate(months)}
    em = np.array([mi[r["t"]] for r in use])
    si = np.array([ki[strata_key(r, comp)] for r in use])
    g = np.array([r["g"] for r in use], dtype=float)
    y = np.array([r["x2_12"] for r in use], dtype=float)
    boots = []
    for _ in range(N_BOOT):
        cnt = np.bincount(rng.integers(0, len(months), len(months)), minlength=len(months))[em].astype(float)
        n1 = np.bincount(si, weights=cnt * g, minlength=len(keys))
        n0 = np.bincount(si, weights=cnt * (1 - g), minlength=len(keys))
        s1 = np.bincount(si, weights=cnt * g * y, minlength=len(keys))
        s0 = np.bincount(si, weights=cnt * (1 - g) * y, minlength=len(keys))
        ok = (n1 > 0) & (n0 > 0)
        if ok.any():
            w = n1[ok] * n0[ok] / (n1[ok] + n0[ok])
            boots.append(float((w * (s1[ok] / n1[ok] - s0[ok] / n0[ok])).sum() / w.sum()))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return p, float(lo), float(hi)


def top_year(rows):
    c = collections.Counter(r["t"][:4] for r in rows if r["g"] == 1)
    return c.most_common(1)[0][0] if c else None


def judge(rows, comp, full=True):
    d, w, ne, nc, re_, rc = mh(rows, comp)
    res = {"delta": d, "W": w, "n_event": ne, "n_control": nc, "rate_event": re_, "rate_control": rc}
    if ne < MIN_N or w < MIN_W:
        res["verdict"] = "不足"
        return res
    if not full:
        return res
    res["p"], res["lo"], res["hi"] = perm_boot(rows, comp, d)
    halves = []
    for cond in (lambda r: r["t"] <= "2020-12", lambda r: r["t"] >= "2021-01"):
        h = mh([r for r in rows if cond(r)], comp)
        halves.append((h[2], h[0]))
    ty = top_year(rows)
    dropped = mh([r for r in rows if r["t"][:4] != ty], comp)[0]
    aux = mh(rows, comp, y="x2_24")[0]
    res.update(halves=halves, top_year=ty, drop_top=dropped, aux24=aux)
    if (d >= SUPPORT and res["p"] <= ALPHA and all(n >= 30 and dd > 0 for n, dd in halves) and dropped >= DROP_TOP and aux > 0):
        v = "支持"
    elif ne >= WEAK_N and res["hi"] < SUPPORT:
        v = "削弱"
    else:
        v = "不確定"
    res["verdict"] = v
    return res


def bounds(rows, mode):
    """存活者的界限：結果窗 12 個月內下市的（事件與對照都一樣），lower＝當成沒到 2 倍、upper＝當成到了 2 倍。"""
    out = []
    for r in rows:
        r2 = dict(r)
        if r["delisted_12"]:
            r2["x2_12"] = 1 if mode == "upper" else 0
        out.append(r2)
    return out


def pct(x):
    return "—" if x is None or x != x else "%.1f%%" % (100 * x)


def pp(x):
    return "—" if x is None or x != x else "%+.1f" % (100 * x)


summary = {}
print("\n## 判讀（ALPHA＝%.4f；支持要 Δ ≥ %d 個百分點）" % (ALPHA, int(SUPPORT * 100)))
for defn, comp in JUDGED + PRINTED:
    rows, n_ev, flagged_out = DATA[defn]
    judged = (defn, comp) in JUDGED
    r = judge(rows, comp, full=True)
    if judged and r["verdict"] in ("支持", "削弱"):
        lo_v, up_v = judge(bounds(rows, "lower"), comp)["verdict"], judge(bounds(rows, "upper"), comp)["verdict"]
        if lo_v != r["verdict"] or up_v != r["verdict"]:
            r["verdict_bounds"] = (lo_v, up_v)
            r["verdict"] = "不確定（存活者）"
    label = "%s × %s" % ({"wide": "寬", "narrow": "窄"}[defn], {"month": "同月全市場", "month_q": "同月同漲幅五分位"}[comp])
    summary[label] = {k: v for k, v in r.items()}
    print("%s %s｜事件 %d（結果側資料旗標剔除 %d）｜事件 12 個月內曾達 2 倍 %s、對照 %s｜Δ %s｜W %.1f｜p %s｜區間 %s～%s｜前後段 %s｜拿掉 %s 後 %s｜24 個月同向 %s｜%s"
          % ("判" if judged else "只印", label, r["n_event"], sum(1 for x in flagged_out if x["g"] == 1), pct(r["rate_event"]), pct(r["rate_control"]),
             pp(r["delta"]), r["W"], ("%.4f" % r["p"]) if "p" in r else "—", pp(r.get("lo")), pp(r.get("hi")),
             [(n, pp(d)) for n, d in r.get("halves", [])], r.get("top_year"), pp(r.get("drop_top")), pp(r.get("aux24")), r["verdict"]))

# ---------- 另印（描述，不判） ----------
print("\n## 另印：沒漲的占幾成（事件那一邊；不判）")
for defn in ("wide", "narrow"):
    rows, _n, _f = DATA[defn]
    ev = [r for r in rows if r["g"] == 1]
    co = [r for r in rows if r["g"] == 0]
    if not ev:
        continue

    def line(xs):
        ex = [x["ex_12"] for x in xs if x["ex_12"] is not None]
        return ("n %d｜12 個月內到 2 倍 %s｜24 個月內到 2 倍 %s｜24 個月都沒到 2 倍 %s｜12 個月後低於起點 %s｜12 個月超額 平均 %s 中位數 %s"
                % (len(xs), pct(np.mean([x["x2_12"] for x in xs])), pct(np.mean([x["x2_24"] for x in xs])),
                   pct(1 - np.mean([x["x2_24"] for x in xs])), pct(np.mean([x["ret_12"] < 0 for x in xs])),
                   pp(np.mean(ex)) if ex else "—", pp(np.median(ex)) if ex else "—"))
    print("%s 事件：%s" % ({"wide": "寬", "narrow": "窄"}[defn], line(ev)))
    print("   對照（同期全部）：%s" % line(co))
    for lab, sub in (("說明有否認字眼", [r for r in ev if r["deny"]]), ("沒有否認字眼", [r for r in ev if not r["deny"]]),
                     ("公告前 24 個月已漲一倍以上", [r for r in ev if r["r24"] is not None and r["r24"] >= 1]),
                     ("公告前 24 個月沒漲一倍", [r for r in ev if r["r24"] is not None and r["r24"] < 1])):
        if sub:
            print("   %s：%s" % (lab, line(sub)))
    for q in range(5):
        sub_e = [r for r in ev if r["q"] == q]
        sub_c = [r for r in co if r["q"] == q]
        if sub_e:
            print("   前一年漲幅第 %d 五分位（0 最低%s）：事件 %s｜對照 12 個月內到 2 倍 %s" % (
                q, "；這一格＝已經在風口上的那一群" if q == 4 else "", line(sub_e), pct(np.mean([x["x2_12"] for x in sub_c])) if sub_c else "—"))
    by = collections.defaultdict(list)
    for r in ev:
        by[r["t"][:4]].append(r)
    print("   依年（事件 12 個月內到 2 倍）：", {y: "%d／%d" % (sum(x["x2_12"] for x in v), len(v)) for y, v in sorted(by.items())})

if SYN:
    print("（假結果自查結束：不寫輸出檔）")
    sys.exit(0)

out_csv = OUT / "h18-stage2-outcomes.csv"
cols = ["code", "t", "q", "deny", "x2_12", "x2_24", "ret_12", "ex_12", "delisted_12"]
with out_csv.open("w", encoding="utf-8", newline="\n") as fh:
    wr = csv.writer(fh, lineterminator="\n")
    wr.writerow(["definition"] + cols)
    for defn in ("wide", "narrow"):
        for r in DATA[defn][0]:
            if r["g"] == 1:
                wr.writerow([defn] + [r.get(k) for k in cols])
(HERE / "stage2_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("寫出", out_csv.name, L.sha256_lf(out_csv)[:16])
```

### posthoc_top.py（事後：最高五分位並排；sha256 前 16 碼 `00d95c4c777f35f8`）

```python
"""H18 事後（看過階段二結果之後才加；不進判讀）：前一年漲幅最高五分位那一格，事件與對照的完整並排——
12／24 個月曾達 2 倍、12 個月後低於起點、12 個月超額中位數、以及月內加權的 Δ。回答「漲到 2 倍的比較多，是不是只是衝高又掉回來」。"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

import h18lib as H

L = H.L
sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
S1 = json.loads((HERE / "stage1_private.json").read_text(encoding="utf-8"))
ME = L.month_ends()
YMS = sorted(ME)
IDX = {ym: i for i, ym in enumerate(YMS)}
raw, name, _m = L.load_quotes(ME)
fac, _ = L.load_factors()
dr = {c for c in raw if L.is_dr(name.get(c, ""))}
mkt, _u, _d = L.market_returns(raw, fac, ME, drop_dr_names=dr)
adj = {c: L.adjusted(s, ME, fac.get(c, ())) for c, s in raw.items() if c not in dr}


def out(c, t):
    s, i = adj[c], IDX[t]
    p0 = s[t]
    win = [(k, s[YMS[i + k]]) for k in range(1, 25) if i + k < len(YMS) and YMS[i + k] in s]
    seq = [p0] + [p for _k, p in win]
    if any(not (0.2 <= b / a <= 5) for a, b in zip(seq, seq[1:])):
        return None
    o = {}
    for h in (12, 24):
        sub = [(k, p) for k, p in win if k <= h]
        o[f"x2_{h}"] = int(any(p >= 2 * p0 for _k, p in sub))
        o[f"ret_{h}"] = (sub[-1][1] / p0 - 1) if sub else 0.0
        m = L.mkt_cum(mkt, t, YMS[i + h]) if i + h < len(YMS) else None
        o[f"ex_{h}"] = None if m is None else o[f"ret_{h}"] - m
    o["x2_then_below_12"] = int(o["x2_12"] and o["ret_12"] < 1.0)   # 12 個月內曾達 2 倍，但第 12 個月已經不在 2 倍以上
    return o


for defn in ("wide", "narrow"):
    rows = []
    for e in S1["events"]:
        if e[f"counted_{defn}"] and not e["flag_unadj"] and e["quintile"] == 4:
            o = out(e["code"], e["t"])
            if o:
                rows.append({"g": 1, "t": e["t"], **o})
    for t, lst in S1["controls"].items():
        for c, q, flag in lst:
            if q == 4 and not flag:
                o = out(c, t)
                if o:
                    rows.append({"g": 0, "t": t, **o})
    ev = [r for r in rows if r["g"] == 1]
    co = [r for r in rows if r["g"] == 0]

    def stat(xs):
        ex12 = [x["ex_12"] for x in xs if x["ex_12"] is not None]
        ex24 = [x["ex_24"] for x in xs if x["ex_24"] is not None]
        return ("n %d｜12 個月內曾達 2 倍 %.1f%%（其中第 12 個月已回到 2 倍以下 %.1f%%）｜24 個月內曾達 2 倍 %.1f%%｜12 個月後低於起點 %.1f%%｜"
                "12 個月超額 中位數 %+.1f 平均 %+.1f｜24 個月超額 中位數 %+.1f 平均 %+.1f"
                % (len(xs), 100 * np.mean([x["x2_12"] for x in xs]), 100 * np.mean([x["x2_then_below_12"] for x in xs]),
                   100 * np.mean([x["x2_24"] for x in xs]), 100 * np.mean([x["ret_12"] < 0 for x in xs]),
                   100 * np.median(ex12), 100 * np.mean(ex12), 100 * np.median(ex24), 100 * np.mean(ex24)))
    cell = collections.defaultdict(lambda: [[], []])
    for r in rows:
        cell[r["t"]][r["g"]].append(r)
    res = {}
    for key in ("x2_12", "x2_24"):
        num = den = 0.0
        for c0, c1 in cell.values():
            if c0 and c1:
                w = len(c1) * len(c0) / (len(c1) + len(c0))
                num += w * (np.mean([x[key] for x in c1]) - np.mean([x[key] for x in c0]))
                den += w
        res[key] = num / den
    print("== %s、前一年漲幅最高五分位（事後）" % {"wide": "寬", "narrow": "窄"}[defn])
    print("  事件：", stat(ev))
    print("  對照：", stat(co))
    print("  月內加權 Δ：12 個月 %+.1f、24 個月 %+.1f 個百分點" % (100 * res["x2_12"], 100 * res["x2_24"]))
```
