# H16 結果：大跌當時的營收、存貨、毛利，分不出之後回不回得到前高——三個標記都是「不確定」

> 日期 2026-11-22｜判讀線：[`registration.md`](registration.md)「2026-11-22｜H16 判讀線」（commit `a63debb5`，使用者選 1B、2N2，pq2 [943]）｜
> 階段一（事件表、標記表與 digest）：commit `fe698fca`｜乾跑報告：[`replay-h16-dryrun.md`](replay-h16-dryrun.md)
> 兩個登記的 commit 都早於任何結果的計算。**一次判讀，沒有重跑、沒有改門檻。** 只進假說帳，不改任何 filter、候選狀態、排序（G10）。

## 一句話

台股 2015-01～2021-03，一檔股票漲過三倍之後第一次自高點回落四成（406 筆、372 家）：**18 個月內回到前高的只有 16%**，再跌三成的（26%）比回到前高的多。
那個月當下已公布的三個財務標記——營收動能轉弱、存貨天數上升、毛利率走低——**都分不出誰會回到前高**（差距 +1.4、−1.2、+4.0 個百分點，都沒過線）。
分得開的反而是不在標記裡的一件事：**是跟著大盤一起跌，還是自己跌**（下面「基準率」與「基線」；那是事後看到的，不算確認）。

## 判讀

判讀母體 356 筆（406 筆剔除舊劇本來源案例 50 筆，2N2）。主量＝t 之後 18 個月內月收盤曾 ≥ 事件前高點：**58／356＝16.3%**。
並列量：曾達 t 收盤 1.67 倍 23.9%；曾達 2 倍 12.9%；12 個月內自 t 收盤再跌三成 26.1%；12 個月對全市場等權的超額平均 −1.9%。

| | M1 營收動能轉弱（G＝15） | M2 存貨天數上升（G＝10） | M3 毛利率走低（G＝2） |
|---|---|---|---|
| 成立組：筆數（回到前高） | 118（16.9%） | 103（18.4%） | 115（11.3%） |
| 不成立組：筆數（回到前高） | 199（19.1%） | 184（17.4%） | 237（19.0%） |
| 季內資訊量 W | 69.0 | 58.7 | 70.2 |
| **Δ（季內加權；不成立 − 成立）** | **+1.4 個百分點** | **−1.2** | **+4.0** |
| 單尾 p（線 0.0125） | 0.4324 | 0.6701 | 0.2128 |
| 95% 區間 | −8.9 ～ +8.8 | −7.7 ～ +6.5 | −5.7 ～ +13.7 |
| 不分季合併（對照） | +2.1 | −1.1 | +7.7 |
| 拿掉 2015 夏／2018／2020-03 後的 Δ | −1.2／+4.0／+0.0 | −0.3／−0.1／−1.1 | +5.1／+3.3／+4.5 |
| 前段（成立、不成立、Δ） | 58、82、+4.0 | 51、79、+1.4 | 42、114、+3.3 |
| 後段（成立、不成立、Δ） | 60、117、−0.8 | 52、105、−3.4 | 73、123、+4.4 |
| 並列①曾達 1.67 倍的 Δ | +1.8 | −5.9 | +5.0 |
| 並列②12 個月超額的 Δ（可算筆數） | +5.5（317） | −5.0（282） | −3.9（346） |
| 回落深度分層（季 × 三分位）的 Δ | +2.3 | −2.1 | +5.3 |
| 存活者界限（全當沒回到／全當回到）的 Δ | +1.4／+1.4 | −1.2／+0.3 | +4.0／−0.1 |
| **判讀** | **不確定** | **不確定** | **不確定** |

- **為什麼是不確定、不是削弱**：削弱要兩組各 ≥ 150 筆，成立組只有 118／103／115——這一輪本來就判不出削弱（乾跑報告已寫）。M1、M2 的區間上界（+8.8、+6.5）在 10 個百分點以下，M3 的（+13.7）不在。
- **為什麼不是支持**：Δ 都不到 10 個百分點、p 都沒過線；M1 拿掉 2015 夏之後翻成負的，M2 整個是反向。
- **存活者**：結果窗內下市 8 筆；兩個界限下三個標記的判讀都不變。
- **並列印的一行**：照草稿字面（兩組都有 ≥ 5 筆的季要 8 個）——三個標記都是「不足」（這樣的季 7／6／5 個）。
- **M5 同節點廣度（只印，不判）**：成立 123（23.6%）／不成立 207（13.5%）；季內加權 Δ −0.3、p 0.59、區間 −8.1～+7.7；不分季是 −10.1——差全部來自季別（廣度差的月份集中在大跌的那幾季，而那幾季回到前高的本來就多）。

## 後果（照設計稿第三版 §5.3 的後果表，一字不改）

落在第二列「沒有支持、至少一個不確定」：

- 給你的一句：**「機械標記沒有量出分辨力，也沒有量到『沒有』。」**
- 表 B（可開所騎的層今天的列）對應的欄標「已量：不確定」。
- Phase 8 的結尾標記表對應的格降到附錄。
- 不重跑、不改門檻、不加標記重試。

## 基準率（表 A；描述，不判）

**先讀這三句**：①可開 17 檔裡台股 2 檔，這張表只在台股量過；其餘 15 檔（A 股 6、美股 5、印度 2、瑞典 1、加拿大 1）沒有對應的表（2026-11-22 的數，會變）。
②成群那幾列的有效樣本是成群月的個數，不是事件數。③這一次是哪一種，這張表答不出來。

| 列 | n | 18 個月內回到前高 | 曾達 t 收盤 1.67 倍 | 曾達 2 倍 | 12 個月內再跌三成 | 結果窗內下市 | 回到前高的兩個界限（下市全當沒回到～全當回到） |
|---|---:|---:|---:|---:|---:|---:|---|
| **回落到高點的 0.6 以下：全部** | 406 | 16.3% | 23.6% | 12.8% | 26.4% | 8 | 16.3%～18.2% |
| 回落到高點的 0.6 以下：孤立（不在成群月） | 179 | 13.4% | 16.8% | 8.4% | 43.0% | 3 | 13.4%～15.1% |
| 回落到高點的 0.6 以下：成群（7 個成群月合計） | 227 | 18.5% | 29.1% | 16.3% | 13.2% | 5 | 18.5%～20.7% |
| 　成群月 2015-06 | 17 | 2／17 | 2／17 | 2／17 | 5／17 | 1 | — |
| 　成群月 2015-07 | 36 | 8／36 | 14／36 | 9／36 | 3／36 | 0 | — |
| 　成群月 2015-08 | 21 | 5／21 | 7／21 | 3／21 | 0／21 | 1 | — |
| 　成群月 2018-04 | 18 | 2／18 | 4／18 | 2／18 | 5／18 | 0 | — |
| 　成群月 2018-09 | 36 | 2／36 | 3／36 | 2／36 | 14／36 | 2 | — |
| 　成群月 2018-10 | 75 | 9／75 | 21／75 | 8／75 | 3／75 | 1 | — |
| 　成群月 2020-03 | 24 | 14／24 | 15／24 | 11／24 | 0／24 | 0 | — |
| **回落到高點的 0.5 以下：全部** | 280 | 12.1% | 30.4% | 17.1% | 23.2% | 9 | 12.1%～15.4% |
| 回落到高點的 0.5 以下：孤立（不在成群月） | 143 | 10.5% | 23.8% | 12.6% | 37.8% | 6 | 10.5%～14.7% |
| 回落到高點的 0.5 以下：成群（4 個成群月合計） | 137 | 19／137 | 51／137 | 30／137 | 11／137 | 3 | — |
| 　成群月 2015-07 | 26 | 3／26 | 8／26 | 5／26 | 6／26 | 0 | — |
| 　成群月 2015-08 | 18 | 3／18 | 8／18 | 6／18 | 2／18 | 0 | — |
| 　成群月 2018-10 | 73 | 3／73 | 19／73 | 7／73 | 3／73 | 3 | — |
| 　成群月 2020-03 | 20 | 10／20 | 16／20 | 12／20 | 0／20 | 0 | — |
| **回落到高點的 0.4 以下：全部** | 144 | 10.4% | 33.3% | 22.2% | 27.1% | 4 | 10.4%～13.2% |
| 回落到高點的 0.4 以下：孤立（不在成群月） | 61 | 6.6% | 18.0% | 14.8% | 41.0% | 2 | 6.6%～9.8% |
| 回落到高點的 0.4 以下：成群（6 個成群月合計） | 83 | 13.3% | 44.6% | 27.7% | 16.9% | 2 | 13.3%～15.7% |
| 　成群月 2015-07 | 7 | 0／7 | 1／7 | 1／7 | 2／7 | 1 | — |
| 　成群月 2015-08 | 8 | 1／8 | 2／8 | 1／8 | 1／8 | 0 | — |
| 　成群月 2018-08 | 6 | 0／6 | 1／6 | 0／6 | 4／6 | 0 | — |
| 　成群月 2018-10 | 35 | 2／35 | 16／35 | 10／35 | 3／35 | 1 | — |
| 　成群月 2019-05 | 6 | 0／6 | 1／6 | 0／6 | 4／6 | 0 | — |
| 　成群月 2020-03 | 21 | 8／21 | 16／21 | 11／21 | 0／21 | 0 | — |

- 0.6 的列＝H16 的母體 406 筆（不剔舊劇本來源案例——這張表不判標記）。0.5、0.4 的列＝同一批事件從 t 往後，在沒有再創新高、高點後 24 個月內、月份 ≤ 2021-03 的條件下，
  第一次跌到那個深度的月份（結果窗從那個月起算；1.67 倍、2 倍、再跌三成都是對那個月的收盤）。成群月＝該深度自己的事件數 ≥ 月均（75 個月）的三倍。
- n < 20 的格只列個數；成群月的單列只印「k／n」；成群月不到 5 個的彙總列只印個數。

讀得到的幾件事（描述；單位是個股事件，歷史上可比的大跌只有三次）：

- **回到前高是少數**：跌四成之後 16%、跌五成之後 12%、跌六成之後 10%。跌得越深，反彈到 1.67 倍的越多（24% → 30% → 33%），但那是從更低的地方算。
- **跟著大盤一起跌，和自己跌，不一樣**：成群月的事件 12 個月內再跌三成的 13%，孤立的 43%；曾達 1.67 倍 29% 對 17%；回到前高 18.5% 對 13.4%。
- **三次大跌彼此差很多**：2020-03 是 14／24 回到前高、沒有一筆再跌三成；2018-10 是 9／75；2018-09（落底前一個月）是 2／36、14 筆再跌三成；2015-07 是 8／36。

## 基線（判讀母體；登記要求必印；除回落深度分層外不進判讀）

各依三分位分三組，印 18 個月內回到前高的比例：

| 基線 | 低的三分之一 | 中間 | 高的三分之一 |
|---|---|---|---|
| 回落深度（t 收盤 ÷ 高點；切點 0.536／0.576） | 16.8%（119） | 13.3%（120） | 18.8%（117） |
| 漲幅倍數（高點 ÷ 低點；切點 3.85／5.70） | 21.8%（119） | 14.4%（118） | 12.6%（119） |
| 高點到 t 的月數（切點 6／11） | 17.4%（138） | 12.3%（106） | 18.8%（112） |
| **大盤同期回落**（全市場等權自高點月底到 t 月底的累積報酬；切點 −10.4%／+3.7%） | **26.9%**（119） | 13.6%（118） | **8.4%**（119） |

**看完結果才有的說法（不能用同一份資料改判）**：四個基線裡分得最開的是「大盤同期回落」——從這一檔的高點到 t，大盤也跌超過一成的那一組有 27% 回到前高，
大盤在漲、它自己跌的那一組只有 8%。它是 t 當下就知道的量，方向也與表 A 的孤立對成群一致。但它不是登記的標記、是四個基線裡事後挑出來的那一個、
而且三次大跌占了大半——要當真得另外預先登記、換一段期間測（表 A 的延伸表往 2015 年以前做的時候可以一起測）。

## 另印（不進判讀）

| 母體 | 筆數 | M1：Δ（p） | M2：Δ（p） | M3：Δ（p） |
|---|---:|---|---|---|
| 判讀母體（2N2） | 356 | +1.4（0.43） | −1.2（0.67） | +4.0（0.21） |
| 完全不剔 | 406 | +1.7（0.40） | −1.7（0.71） | +2.3（0.34） |
| 2N1 節點全剔 | 334 | +3.1（0.30） | −0.5（0.62；成立組 96，不足） | +2.2（0.37） |
| 2C 只剔代表公司 | 382 | +2.9（0.31） | −3.0（0.80） | +2.9（0.28） |
| 判讀母體、剔除 t 在 2020-03～05 | 335 | +0.0（0.57） | −1.1（0.66；成立組 99，不足） | +4.5（0.17） |
| 判讀母體、剔除交叉核做不了的 | 343 | +2.1（0.38） | −2.5（0.77；成立組 98，不足） | +3.8（0.23） |
| 判讀母體＋放回 15 筆（未還原的下市事件 10、存託憑證 5） | 371 | +1.4（0.44） | −1.2（0.67） | +4.0（0.21） |

- 哪一種母體下方向與大小都一樣；沒有一格過線。
- **標記算不出來的事件（可算率 × 結果組）**：M1 算不出來的 39 筆**沒有一筆回到前高**（算得出來的 317 筆是 18.3%）；M2 算不出來 69 筆 10.1%（算得出來 17.8%）；M3 4 筆 0／4；M5 26 筆 3.8%（17.3%）。
  缺資料與結果相關（下市公司的月營收拿不到，乾跑的偏差標註 ⑤ 講過）——三個標記的判讀實質上只涵蓋資料查得到的公司。
- 另外三個只印的切法：M1「近三個月營收年增平均 ≤ 0」成立 160（19.4%）／不成立 157（17.2%），Δ +1.7（p 0.41）；
  M3「比前八季最高低 ≥ 3 個百分點」199（14.6%）／126（22.2%），Δ +3.0（p 0.30）；M4 合約負債季減 ≥ 20% 19（10.5%）／40（27.5%），Δ +12.6（p 0.20；W 只有 11.5）。
- **M1 在 2008–2014 的複製：沒做。** 登記寫的是「方向相反時 M1 的判讀降為不確定」；M1 已經是不確定，複製改不了這一輪的判讀。要補的話另外排。

## 計數與自查

- digest：事件表、標記表與登記的值相符（階段二開頭驗）。母體 406 筆的主量都算得出來。
- 今天還在的公司重抓了到 2022-09 的還原月線（382 檔，缺 0）：「t ÷ 高點」與階段一的回落深度相差超過 2 個百分點的 **0 筆**。
- 結果窗 18 個月都看得到的 396 筆；其餘 10 筆看得到 0–17 個月。結果窗內下市 8 筆（2475、3474、4733、4984、5255、5259、5317、5505）；並列量②不可算 7 筆。
- 全市場等權：129 個月、202,849 個月報酬；比值不在 0.33–3 之間剔除 16 個。
- **管線自測（真的結果之前）**：同一支腳本把結果換成假的跑了 7 次——植入「M1 成立組少 20 個百分點」的那一次判出 M1 支持（Δ +15.6、p 0.0029）、M2 與 M3 不確定；
  六次沒有差的假資料，三個標記的 p 落在 0.06～0.93。假結果在任何彙總印出之前就蓋上去，這個模式不寫輸出檔。
- 結果落帳之後的自查：回到前高卻沒達 1.67 倍的 0 筆（t ≤ 0.6 × 高點，兩者必須一致）；隨機抽 6 筆把高點、t、窗內最高與最低印出來人工對，都相符。
- bootstrap 2,000 次裡沒有算不出 Δ 的。

## 規格的套用與偏離（照實寫）

| # | 登記的字 | 實際怎麼做 | 什麼時候定的 |
|---|---|---|---|
| 1 | 結果窗內下市＝終止上市櫃名單上的終止日在窗內 | 多一個條件：終止那個月之後，交易所月底行情上再也沒有這個代號。上櫃轉上市也在終止上櫃名單上，照字面會把轉上市當成下市 | 寫階段二腳本時，看任何結果之前 |
| 2 | M1 在 2008–2014 的複製（另印） | 沒做（見上） | 看了主判讀之後——M1 不是支持，複製不影響判讀 |
| 3 | 表 A 的列：回落深度 0.6／0.5／0.4 × 孤立或成群 | 0.5、0.4 的列怎麼從同一批事件導出，設計稿沒寫；定義在表下 | H16 判讀落帳之後、跑表 A 之前 |
| 4 | 表 A 的延伸（2015 年以前、美股倖存者比例） | 還沒做（設計稿排在 H16 落帳之後） | — |

## 偏差標註

乾跑報告的 1–13 照舊（事件集中在三次大跌；下市公司的 M1 全部不可算；下市公司價格只有一個來源、10 筆未還原；節點名單與產業分類是今天的版本；
去年同季的成本與存貨是混版；W ≥ 50、M5 退出確認型、舊劇本的剔法都是看了事件數之後才寫的……）。這份報告新增：

14. 標記算不出來的事件結果明顯較差（M1 算不出來的 39 筆 0 回到前高）——判讀只涵蓋資料查得到的公司，而它們本來就比較好。
15. 「大盤同期回落」「孤立對成群」是事後看到的差；沒有預先登記，不是確認。
16. 判讀母體的回到前高只有 16%，成立組的回到筆數各只有 13–20 筆——區間寬（±8～10 個百分點），量得出的只有很大的差。
17. 表 A 的 0.5、0.4 列與 0.6 列是同一批事件的後續，不是獨立樣本。

## 檔案

- 逐事件的結果：[`h16-stage2-outcomes.csv`](h16-stage2-outcomes.csv)（406 筆；回到前高、1.67 倍、2 倍、12 個月內再跌三成、12 個月報酬與同期全市場等權、大盤同期回落、看得到的月數、結果窗內下市）。
- 事件表與標記表：[`h16-stage1-events.csv`](h16-stage1-events.csv)、[`h16-stage1-markers.csv`](h16-stage1-markers.csv)。
- 腳本與原始資料：`library/private/measurement/h16_cache/`（不進版控）；下面逐字附上這一輪新增的五支。乾跑的腳本在乾跑報告。

## 腳本（逐字）

### stage1.py（階段一：事件表、標記表與 digest；sha256 前 16 碼 `1016a18ef199cce5`）

```python
"""H16 階段一：輸出事件表與標記表（只含 t 當時已知的欄），算 digest。
**不讀 px.json、不讀任何 t 之後的價格**——只讀 events_all.json（每列只含 ≤ t 的東西）、markers.json、chosen.json、oldplaybook_drop.json。
公司後來有沒有下市、資料來源是哪一條（看得出下市）、哪一天終止，都不寫進表。
digest＝檔案內容（UTF-8、換行統一成 LF）的 sha256。"""
import csv
import hashlib
import io
import json
from pathlib import Path

from h16lib import in_pop

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
OUT = ROOT / "docs" / "reports" / "phase7"
FORBIDDEN = {"source", "delisted", "delist_board", "delist_reason", "last_seen", "unadjusted_why", "corp_actions_low_to_t",
             "low_px", "high_px", "t_px", "official_runup", "official_depth", "official_adj_runup", "official_adj_depth"}

events = {(e["code"], e["t_ym"]): e for e in json.loads((HERE / "events_all.json").read_text(encoding="utf-8"))}
markers = json.loads((HERE / "markers.json").read_text(encoding="utf-8"))
chosen = json.loads((HERE / "chosen.json").read_text(encoding="utf-8"))["chosen"]
drops = json.loads((HERE / "oldplaybook_drop.json").read_text(encoding="utf-8"))
drop = {name.split(" ")[0]: {tuple(x) for x in rows} for name, rows in drops.items()}
assert set(drop) == {"2N1", "2N2", "2C"}, drop.keys()
assert chosen == {"M1": 15, "M2": 10, "M3": 2, "M5": 50}, chosen

pop = sorted((r for r in markers if in_pop(r)), key=lambda r: (r["t_ym"], r["code"]))
assert len(pop) == 406, len(pop)
assert len({r["code"] for r in pop}) == 372


def hit(r, m):
    v = r.get(m)
    if v is None:
        return None
    g = chosen[m]
    return {"M1": v <= -g, "M2": v >= g, "M3": v >= g, "M5": v < g}[m]


def flag(x):
    return "" if x is None else ("1" if x else "0")


def num(x, nd=2):
    return "" if x is None else f"{x:.{nd}f}"


def quarter(ym):
    y, m = ym.split("-")
    return f"{y}Q{(int(m) - 1) // 3 + 1}"


ev_cols = ["code", "name", "t_ym", "quarter", "low_ym", "high_ym", "runup", "depth", "months_high_to_t", "sector",
           "xcheck_no_trade", "drop_2N1", "drop_2N2", "drop_2C", "judged"]
mk_cols = ["code", "t_ym", "known_quarter", "M1", "M1_on", "M1_recent", "M2", "M2_on", "M3", "M3_on", "M3_vs_max8", "M4",
           "M5", "M5_on", "M5_node", "M5_n", "why_M1", "why_M2", "why_M3", "why_M4", "why_M5"]
assert not (set(ev_cols) | set(mk_cols)) & FORBIDDEN
ev_rows, mk_rows = [], []
for r in pop:
    key = (r["code"], r["t_ym"])
    e = events[key]
    assert e["high_ym"] < e["t_ym"] and e["low_ym"] < e["high_ym"], key
    ev_rows.append({
        "code": r["code"], "name": e["name"], "t_ym": r["t_ym"], "quarter": quarter(r["t_ym"]), "low_ym": e["low_ym"],
        "high_ym": e["high_ym"], "runup": num(e["runup"], 4), "depth": num(e["depth"], 4),
        "months_high_to_t": e["months_high_to_t"], "sector": r.get("sector") or "",
        "xcheck_no_trade": flag(r["xcheck"] == "月底無成交"),
        "drop_2N1": flag(key in drop["2N1"]), "drop_2N2": flag(key in drop["2N2"]), "drop_2C": flag(key in drop["2C"]),
        "judged": flag(key not in drop["2N2"])})
    why = r.get("why") or {}
    mk_rows.append({
        "code": r["code"], "t_ym": r["t_ym"], "known_quarter": r.get("known_quarter") or "",
        "M1": num(r.get("M1")), "M1_on": flag(hit(r, "M1")), "M1_recent": num(r.get("M1_recent")),
        "M2": num(r.get("M2")), "M2_on": flag(hit(r, "M2")), "M3": num(r.get("M3")), "M3_on": flag(hit(r, "M3")),
        "M3_vs_max8": num(r.get("M3_vs_max8")), "M4": num(r.get("M4")),
        "M5": num(r.get("M5")), "M5_on": flag(hit(r, "M5")), "M5_node": r.get("M5_node") or "", "M5_n": r.get("M5_n") or "",
        **{f"why_{m}": str(why.get(m) or "") for m in ("M1", "M2", "M3", "M4", "M5")}})


def dump(name, cols, rows):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    data = buf.getvalue().encode("utf-8")
    (OUT / name).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


d_ev = dump("h16-stage1-events.csv", ev_cols, ev_rows)
d_mk = dump("h16-stage1-markers.csv", mk_cols, mk_rows)

# 放回去另印用的 15 筆（未還原的下市事件 10、存託憑證 5）：不進公開的表（看得出下市），只記它們的 digest
extra = sorted((r["code"], r["t_ym"], r["xcheck"] == "未還原", bool(events[(r["code"], r["t_ym"])].get("dr")))
               for r in markers if not in_pop(r) and (r["xcheck"] == "未還原" or events[(r["code"], r["t_ym"])].get("dr"))
               and (r.get("excluded") is None or "存託憑證" in str(r.get("excluded"))))
d_extra = hashlib.sha256(json.dumps(extra, ensure_ascii=False).encode("utf-8")).hexdigest()

judged = [(e, m) for e, m in zip(ev_rows, mk_rows) if e["judged"] == "1"]
print("母體", len(pop), "筆｜", len({r['code'] for r in pop}), "家｜判讀用", len(judged), "筆")
for m in ("M1", "M2", "M3", "M5"):
    on = sum(1 for _e, k in judged if k[f"{m}_on"] == "1")
    off = sum(1 for _e, k in judged if k[f"{m}_on"] == "0")
    print(f"  {m}（G＝{chosen[m]}）判讀母體：成立 {on}／不成立 {off}／不可算 {len(judged) - on - off}")
print("交叉核做不了（月底無成交）", sum(e["xcheck_no_trade"] == "1" for e in ev_rows), "｜t 在 2020-03～05", sum("2020-03" <= e["t_ym"] <= "2020-05" for e in ev_rows))
print("另印用放回去的列", len(extra), "（未還原", sum(x[2] for x in extra), "、存託憑證", sum(x[3] for x in extra), "）")
print("digest 事件表", d_ev)
print("digest 標記表", d_mk)
print("digest 放回去的 15 筆（代號、t、種類）", d_extra)
(HERE / "stage1_digest.json").write_text(json.dumps({"events": d_ev, "markers": d_mk, "extra": d_extra, "extra_rows": extra}, ensure_ascii=False, indent=1), encoding="utf-8")
```

### fetch_stage2.py（階段二的資料段：只抓不算；sha256 前 16 碼 `05ff2d7d0b2b4562`）

```python
"""H16 階段二的資料段（判讀線 a63debb5、階段一 digest fe698fca 之後才跑）：結果窗的原始資料，只抓不算。
①2021-04～2022-09 的月底交易日 ②那 18 個月底的全市場行情（上市、上櫃）③2021-04～2022-09 的除權息與減資
④事件公司（今天還有報價的）到 2022-09 的還原月線。零 LLM；對外請求不帶任何個人資訊。"""
import datetime as dt
import importlib
import json
import time
from pathlib import Path

import requests
import yfinance as yf

yshared = importlib.import_module("yfinance.shared")
HERE = Path(__file__).parent
OFF = HERE / "official"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}
PACE = 5.0


def log(*a):
    print(dt.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def get(url, dest, ok):
    if dest.exists():
        return "cached"
    for attempt in range(5):
        try:
            r = requests.get(url, headers=UA, timeout=90)
            body = r.content
        except requests.RequestException as exc:
            log("  連線錯誤", dest.name, type(exc).__name__)
            time.sleep(30 * (attempt + 1))
            continue
        time.sleep(PACE)
        if r.status_code != 200:
            log("  非 200：", r.status_code, dest.name)
            time.sleep(60 * (attempt + 1))
            continue
        try:
            obj = json.loads(body.decode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            log("  非 JSON：", dest.name, body[:80])
            time.sleep(60 * (attempt + 1))
            continue
        if ok(obj):
            dest.write_bytes(body)
            return "ok"
        (OFF / (dest.stem + ".other")).write_bytes(body[:2000])
        return "other"
    return "error"


# ① 月底交易日
f2 = HERE / "month_ends2.json"
if f2.exists():
    ends2 = json.loads(f2.read_text(encoding="utf-8"))
else:
    df = yf.download("2330.TW", start="2021-04-01", end="2022-10-01", interval="1d", auto_adjust=False, progress=False)
    last = {}
    for d in df.index:
        last[d.strftime("%Y-%m")] = d.strftime("%Y-%m-%d")
    ends2 = [last[k] for k in sorted(last)]
    assert len(ends2) == 18 and ends2[0].startswith("2021-04") and ends2[-1].startswith("2022-09"), ends2
    f2.write_text(json.dumps(ends2), encoding="utf-8")
log("月底交易日", len(ends2), ends2[0], "→", ends2[-1])

# ② 月底行情
stat = {"ok": 0, "cached": 0, "other": 0, "error": 0}
for d in ends2:
    ymd = d.replace("-", "")
    stat[get(f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json",
             OFF / f"twse_{ymd}.json", lambda o: o.get("stat") == "OK" and len(o.get("tables") or []) >= 9)] += 1
    stat[get(f"https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?date={d.replace('-', '/')}&id=&response=json",
             OFF / f"tpex_{ymd}.json", lambda o: o.get("stat") == "ok" and (o.get("tables") or [{}])[0].get("totalCount", 0) > 100)] += 1
log("月底行情", stat)

# ③ 除權息與減資（2021-04-01～2022-09-30）
corp = [("twse_exright_2021b", "https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate=20210401&endDate=20211231&response=json"),
        ("twse_exright_2022", "https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate=20220101&endDate=20220930&response=json"),
        ("tpex_exright_2021b", "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate=2021/04/01&endDate=2021/12/31&response=json"),
        ("tpex_exright_2022", "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate=2022/01/01&endDate=2022/09/30&response=json"),
        ("twse_reduction_2021_2022", "https://www.twse.com.tw/rwd/zh/reducation/TWTAUU?startDate=20210401&endDate=20220930&response=json"),
        ("tpex_reduction_2021_2022", "https://www.tpex.org.tw/www/zh-tw/bulletin/revivt?startDate=2021/04/01&endDate=2022/09/30&response=json")]
for name, url in corp:
    st = get(url, OFF / f"{name}.json", lambda o: bool(o))
    try:
        o = json.loads((OFF / f"{name}.json").read_text(encoding="utf-8"))
        data = o.get("data") or ((o.get("tables") or [{}])[0].get("data")) or []
        log(name, st, "stat", o.get("stat"), "筆數", len(data), "首列", [str(x)[:12] for x in (data[0][:5] if data else [])])
    except Exception as exc:  # noqa: BLE001
        log(name, st, "讀不出", type(exc).__name__)

# ④ 事件公司的還原月線（到 2022-09）
events = json.loads((HERE / "events_all.json").read_text(encoding="utf-8"))
tickers = sorted({e["ticker"] for e in events if e["source"].startswith("yfinance") and e.get("ticker")})
cache = HERE / "px2.json"
px = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
errors = {}


def pull(chunk, pause):
    try:
        yshared._ERRORS.clear()
    except Exception:  # noqa: BLE001
        pass
    try:
        df = yf.download(tickers=chunk, start="2011-12-01", end="2022-10-01", interval="1mo", auto_adjust=True,
                         progress=False, threads=True, group_by="ticker")
    except Exception as exc:  # noqa: BLE001
        for t in chunk:
            errors[t] = f"download: {exc}"
        time.sleep(pause * 3)
        return
    for t in chunk:
        try:
            s = (df[t]["Close"] if len(chunk) > 1 else df["Close"]).dropna()
            if hasattr(s, "columns"):
                s = s.iloc[:, 0]
        except Exception:  # noqa: BLE001
            s = None
        if s is not None and len(s) > 0:
            rows = [[d.strftime("%Y-%m"), float(v)] for d, v in s.items() if d.strftime("%Y-%m") <= "2022-09"]
            if rows:
                px[t] = rows
                errors.pop(t, None)
                continue
        errors[t] = str(getattr(yshared, "_ERRORS", {}).get(t, "empty"))
    time.sleep(pause)


todo = [t for t in tickers if t not in px]
for i in range(0, len(todo), 60):
    pull(todo[i:i + 60], 2.0)
    cache.write_text(json.dumps(px), encoding="utf-8")
miss = [t for t in tickers if t not in px]
log("第一輪後缺", len(miss), "／", len(tickers))
for i in range(0, len(miss), 15):
    pull(miss[i:i + 15], 6)
cache.write_text(json.dumps(px), encoding="utf-8")
miss = [t for t in tickers if t not in px]
(HERE / "px2_errors.json").write_text(json.dumps({t: errors.get(t, "") for t in miss}, ensure_ascii=False), encoding="utf-8")
log("還原月線：要", len(tickers), "｜有", len(px), "｜缺", len(miss), miss[:10], "｜最晚一根", max((r[-1][0] for r in px.values()), default=""))
log("STAGE2_FETCH_DONE")
```

### stage2.py（階段二：結果與判讀；sha256 前 16 碼 `6e42d140fee14925`）

```python
"""H16 階段二：驗階段一的 digest → 算每個事件的結果 → 照登記的判讀線判。
判讀線：registration.md「2026-11-22｜H16 判讀線」（commit a63debb5）；階段一 digest：commit fe698fca。
輸出：stage2_outcomes.json（逐事件）、stage2_summary.json（各標記各母體的數）、標準輸出（報告用的計數）。"""
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

import adjust
import official
from h16lib import mnum, ym_of

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
REP = ROOT / "docs" / "reports" / "phase7"
SEED, N_PERM, N_BOOT, ALPHA = 20261122, 10_000, 2_000, 0.0125
REGISTERED = {"h16-stage1-events.csv": "fef1a2aa2ea8b0cd9d9c6102b11ba8fbdd463af74611fcc3ccb1454af0675605",
              "h16-stage1-markers.csv": "c76252482285ac6a2bc8140153a7aff558186350916a7497a7426b88a5305728"}
CLUSTERS = {"2015 夏": ("2015-06", "2015-08"), "2018": ("2018-04", "2018-10"), "2020-03": ("2020-03", "2020-03")}
HALVES = {"前段": ("2015-01", "2017-12"), "後段": ("2018-01", "2021-03")}


def log(*a):
    print(*a, flush=True)


# ---------- 0. 驗 digest ----------
tables = {}
for name, want in REGISTERED.items():
    data = (REP / name).read_bytes().replace(b"\r\n", b"\n")
    got = hashlib.sha256(data).hexdigest()
    assert got == want, f"{name} 的 digest 不符：{got}"
    tables[name] = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
log("digest 相符：事件表", len(tables["h16-stage1-events.csv"]), "筆｜標記表", len(tables["h16-stage1-markers.csv"]), "筆")
EV = {(r["code"], r["t_ym"]): r for r in tables["h16-stage1-events.csv"]}
MK = {(r["code"], r["t_ym"]): r for r in tables["h16-stage1-markers.csv"]}
assert set(EV) == set(MK) and len(EV) == 406
private = {(e["code"], e["t_ym"]): e for e in json.loads((HERE / "events_all.json").read_text(encoding="utf-8"))}
d1 = json.loads((HERE / "stage1_digest.json").read_text(encoding="utf-8"))
EXTRA = [(c, t) for c, t, _u, _d in d1["extra_rows"]]
assert hashlib.sha256(json.dumps(d1["extra_rows"], ensure_ascii=False).encode("utf-8")).hexdigest() == d1["extra"]

# ---------- 1. 價格：交易所月底行情（130 個月底）、還原因子、事件公司的還原月線 ----------
ends = official.month_ends() + json.loads((HERE / "month_ends2.json").read_text(encoding="utf-8"))
ME = {d[:7]: d for d in ends}
YMS = sorted(ME)
assert len(YMS) == 130 and all(mnum(b) - mnum(a) == 1 for a, b in zip(YMS, YMS[1:]))
raw, last_seen = {}, {}
for d in ends:
    ym, ymd = d[:7], d.replace("-", "")
    for market in ("twse", "tpex"):
        for code, (_name, close) in official.load(market, ymd).items():
            last_seen[code] = max(last_seen.get(code, ""), ym)
            if close and close > 0:
                raw.setdefault(code, {})[ym] = close
FAC, fstat, _blocked = adjust.load_factors()
px2 = json.loads((HERE / "px2.json").read_text(encoding="utf-8"))
log("交易所月底行情：代號", len(raw), "｜月份", YMS[0], "→", YMS[-1], "｜還原因子", fstat)

# 全市場等權的月報酬（登記第 9 條）：還原後相鄰兩個月底收盤的比值；不在 0.33–3 之間的剔除
mkt, n_dropped, n_used = {}, 0, 0
for a, b in zip(YMS, YMS[1:]):
    rs = []
    for code, s in raw.items():
        if a in s and b in s:
            k = 1.0
            for date, f, _kind in FAC.get(code, ()):
                if ME[a] < date <= ME[b]:
                    k *= f
            r = s[b] / s[a] / k
            if 0.33 <= r <= 3:
                rs.append(r - 1)
            else:
                n_dropped += 1
    mkt[b] = float(np.mean(rs))
    n_used += len(rs)
log("全市場等權：月份", len(mkt), "｜用到的月報酬", n_used, "｜比值不在 0.33–3 之間剔除的", n_dropped)


def mkt_cum(a_ym, b_ym):
    """全市場等權自 a 月底到 b 月底的累積報酬（a < b；任一個月不在資料裡回 None）。"""
    out = 1.0
    for n in range(mnum(a_ym) + 1, mnum(b_ym) + 1):
        ym = ym_of(n)
        if ym not in mkt:
            return None
        out *= 1 + mkt[ym]
    return out - 1


# 終止上市櫃名單（與 stage_events.py 同一段解析）
delisted = {}
tw = json.loads((HERE / "official" / "twse_delisted_all.json").read_text(encoding="utf-8"))
for date, name, code in tw["data"]:
    y, m, d = date.split("/")
    delisted[str(code).strip()] = "%04d-%s-%s" % (int(y) + 1911, m, d)
for f in sorted((HERE / "official").glob("tpex_delisted_2*.json")):
    o = json.loads(f.read_text(encoding="utf-8"))
    for t in o.get("tables") or []:
        fl = t.get("fields") or []
        ci, di = fl.index("股票代號"), fl.index("終止上櫃日期")
        for r in t.get("data") or []:
            code = str(r[ci]).strip()
            ds = re.sub(r"[^\d/]", "", str(r[di]))
            parts = ds.split("/")
            if len(parts) != 3 and len(ds) in (6, 7):
                parts = [ds[:-4], ds[-4:-2], ds[-2:]]
            if len(parts) == 3:
                date = "%04d-%s-%s" % (int(parts[0]) + (1911 if int(parts[0]) < 1911 else 0), parts[1], parts[2])
                if code not in delisted or date > delisted[code]:
                    delisted[code] = date


def series_of(key):
    e = private[key]
    if e["source"].startswith("yfinance"):
        return {ym: v for ym, v in px2[e["ticker"]] if v and v > 0}, "yfinance"
    return dict(adjust.adjusted(raw.get(e["code"], {}), ME, FAC.get(e["code"], []))), "exchange"


# ---------- 2. 每個事件的結果 ----------
def outcome(key):
    code, t = key
    e = private[key]
    s, src = series_of(key)
    n = mnum(t)
    out = {"code": code, "t_ym": t, "src": src, "drift": None, "delisted_in_window": False, "computable": True}
    if t not in s or e["high_ym"] not in s:
        out.update(computable=False, why="重抓的序列沒有 t 或高點那個月")
        return out
    pt, ph = s[t], s[e["high_ym"]]
    out["drift"] = round(pt / ph - float(e["depth"]), 4)
    win = [(k, s[ym_of(n + k)]) for k in range(1, 19) if ym_of(n + k) in s]
    end18 = ym_of(n + 18)
    dl = delisted.get(code)
    # 結果窗內下市：終止日在窗內，而且終止那個月之後交易所行情上再也沒有這個代號（上櫃轉上市也在終止上櫃名單上，那不是下市）
    if dl and t <= dl[:7] <= end18 and last_seen.get(code, "") <= dl[:7]:
        out["delisted_in_window"] = True
        out["delisted_on"] = dl
    if not win and not out["delisted_in_window"]:
        out.update(computable=False, why="t 之後 18 個月一個月收盤都沒有、又不在終止名單上")
        return out
    out["months_seen"] = len(win)
    out["back"] = int(any(v >= ph for _k, v in win))
    out["x167"] = int(any(v >= 1.67 * pt for _k, v in win))
    out["x2"] = int(any(v >= 2 * pt for _k, v in win))
    out["down30_12m"] = int(any(v <= 0.7 * pt for k, v in win if k <= 12))
    p12 = s.get(ym_of(n + 12))
    m12 = mkt_cum(t, ym_of(n + 12))
    out["ret12"] = None if p12 is None else round(p12 / pt - 1, 4)
    out["mkt12"] = None if m12 is None else round(m12, 4)
    out["excess12"] = None if (p12 is None or m12 is None) else round(p12 / pt - 1 - m12, 4)
    md = mkt_cum(e["high_ym"], t)
    out["mkt_drawdown"] = None if md is None else round(md, 4)
    return out


OUT = {key: outcome(key) for key in sorted(set(EV) | set(EXTRA))}
# 管線自測（H16_SYNTH＝null／planted）：把真的結果換成假的再跑同一條管線——null 應該量不到差、planted（M1 成立組少 20 個百分點）
# 應該量得到。假的結果在任何彙總印出之前就蓋上去，這個模式不寫輸出檔、印不出任何真的結果。
SYNTH = os.environ.get("H16_SYNTH")
if SYNTH:
    assert SYNTH in ("null", "planted")
    srng = np.random.default_rng(int(os.environ.get("H16_SYNTH_SEED", "1")))
    for k, o in OUT.items():
        if not o["computable"]:
            continue
        hit = SYNTH == "planted" and MK.get(k, {}).get("M1_on") == "1"
        o["back"] = int(srng.random() < (0.15 if hit else 0.35))
        o["x167"] = int(srng.random() < (0.30 if hit else 0.50))
        o["x2"] = int(srng.random() < 0.3)
        o["down30_12m"] = int(srng.random() < 0.3)
        o["excess12"] = float(srng.normal(-0.10 if hit else 0.0, 0.4))
        o["mkt_drawdown"] = float(srng.normal(-0.1, 0.1))
    log("⚠ 管線自測模式", SYNTH, "——下面全部是假的結果")
else:
    (HERE / "stage2_outcomes.json").write_text(json.dumps(list(OUT.values()), ensure_ascii=False, indent=0), encoding="utf-8")
pop = sorted(EV)
bad = [k for k in pop if not OUT[k]["computable"]]
drift = [k for k in pop if OUT[k]["computable"] and OUT[k]["src"] == "yfinance" and abs(OUT[k]["drift"]) > 0.02]
dlw = [k for k in pop if OUT[k].get("delisted_in_window")]
log("母體", len(pop), "｜主量算不出來", len(bad), [(k, OUT[k]["why"]) for k in bad][:6])
log("重抓序列的「t ÷ 高點」與階段一相差超過 2 個百分點", len(drift), [(k, OUT[k]["drift"]) for k in drift][:8])
log("結果窗內下市", len(dlw), sorted(dlw), "｜②不可算（第 12 個月沒有收盤）", sum(OUT[k]["computable"] and OUT[k]["excess12"] is None for k in pop))
log("結果窗裡看得到的月數分布", dict(sorted(Counter(OUT[k].get("months_seen") for k in pop if OUT[k]["computable"]).items())))


# ---------- 3. 統計 ----------
def quarter(ym):
    y, m = ym.split("-")
    return f"{y}Q{(int(m) - 1) // 3 + 1}"


def mh(rows, ykey="y", strata="q"):
    """rows＝[{on, y, q…}]。回 (Δ, W, 各層)。Δ＝Σw(不成立組平均 − 成立組平均)÷Σw；只有一組的層權重 0。"""
    by = defaultdict(lambda: [[], []])
    for r in rows:
        if r[ykey] is not None:
            by[r[strata]][r["on"]].append(r[ykey])
    num = den = 0.0
    for off, on in by.values():
        if off and on:
            w = len(off) * len(on) / (len(off) + len(on))
            num += w * (float(np.mean(off)) - float(np.mean(on)))
            den += w
    return (num / den if den else None), den


def perm_p(rows, obs):
    rng = np.random.default_rng(SEED)
    by = defaultdict(list)
    for r in rows:
        by[r["q"]].append(r)
    num = np.zeros(N_PERM)
    den = 0.0
    for rs in by.values():
        y = np.array([r["y"] for r in rs], dtype=float)
        n_on = sum(r["on"] for r in rs)
        n_off = len(rs) - n_on
        if not n_on or not n_off:
            continue
        w = n_on * n_off / len(rs)
        idx = rng.permuted(np.tile(np.arange(len(rs)), (N_PERM, 1)), axis=1)
        s_on = y[idx[:, :n_on]].sum(axis=1)
        num += w * ((y.sum() - s_on) / n_off - s_on / n_on)
        den += w
    stat = num / den
    return float((1 + np.sum(stat >= obs - 1e-12)) / (1 + N_PERM))


def boot_ci(rows):
    rng = np.random.default_rng(SEED)
    by_month = defaultdict(list)
    for r in rows:
        by_month[r["t"]].append(r)
    months = sorted(by_month)
    vals, skipped = [], 0
    for _ in range(N_BOOT):
        pick = rng.integers(0, len(months), len(months))
        sample = [r for i in pick for r in by_month[months[i]]]
        d, _w = mh(sample)
        if d is None:
            skipped += 1
        else:
            vals.append(d)
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), skipped


def rows_for(marker, keys, ymode="observed", extra_on=None):
    """ymode：observed（看得到的月份）｜lower（窗內下市全當沒回到）｜upper（全當回到）。"""
    rows = []
    for k in keys:
        o = OUT[k]
        if extra_on is not None:
            on = extra_on(k)
        else:
            flag = MK[k][f"{marker}_on"] if k in MK else ""
            on = None if flag == "" else int(flag)
        if on is None or not o["computable"]:
            continue
        y = o["back"]
        if o["delisted_in_window"] and ymode != "observed":
            y = 0 if ymode == "lower" else 1
        rows.append({"key": k, "t": k[1], "q": quarter(k[1]), "on": on, "y": y, "x167": o["x167"], "ex": o["excess12"],
                     "depth": float((EV.get(k) or private[k])["depth"])})
    return rows


def judge(rows, label):
    n_on, n_off = sum(r["on"] for r in rows), sum(1 - r["on"] for r in rows)
    d, w = mh(rows)
    res = {"label": label, "n_on": n_on, "n_off": n_off, "W": round(w, 1), "delta": d,
           "rate_on": float(np.mean([r["y"] for r in rows if r["on"]])) if n_on else None,
           "rate_off": float(np.mean([r["y"] for r in rows if not r["on"]])) if n_off else None}
    pooled = (res["rate_off"] - res["rate_on"]) if n_on and n_off else None
    res["pooled"] = pooled
    res["p"] = perm_p(rows, d) if d is not None else None
    lo, hi, skipped = boot_ci(rows) if d is not None else (None, None, 0)
    res.update(ci_lo=lo, ci_hi=hi, boot_skipped=skipped)
    res["drop_cluster"] = {name: mh([r for r in rows if not (a <= r["t"] <= b)])[0] for name, (a, b) in CLUSTERS.items()}
    res["halves"] = {}
    for name, (a, b) in HALVES.items():
        sub = [r for r in rows if a <= r["t"] <= b]
        res["halves"][name] = {"n_on": sum(r["on"] for r in sub), "n_off": sum(1 - r["on"] for r in sub), "delta": mh(sub)[0]}
    res["delta_x167"] = mh(rows, ykey="x167")[0]
    ex_rows = [r for r in rows if r["ex"] is not None]
    res["delta_excess12"] = mh(ex_rows, ykey="ex")[0]
    res["n_excess"] = len(ex_rows)
    cut1, cut2 = np.quantile([r["depth"] for r in rows], [1 / 3, 2 / 3])
    for r in rows:
        r["ter"] = 0 if r["depth"] <= cut1 else (1 if r["depth"] <= cut2 else 2)
        r["q_ter"] = f"{r['q']}|{r['ter']}"
    res["delta_depth_strata"] = mh(rows, strata="q_ter")[0]
    res["delta_depth_only"] = mh(rows, strata="ter")[0]
    res["depth_cuts"] = [round(float(cut1), 4), round(float(cut2), 4)]
    qc = Counter()
    for r in rows:
        qc[(r["q"], r["on"])] += 1
    res["quarters_both_ge5"] = sum(1 for q in {r["q"] for r in rows} if qc[(q, 0)] >= 5 and qc[(q, 1)] >= 5)
    return res


def verdict(res):
    if res["n_on"] < 100 or res["n_off"] < 100 or res["W"] < 50:
        return "不足"
    h = res["halves"]
    support = (res["delta"] >= 0.10 and res["p"] <= ALPHA
               and all(v is not None and v >= 0.05 for v in res["drop_cluster"].values())
               and all(x["n_on"] >= 30 and x["n_off"] >= 30 and x["delta"] is not None and x["delta"] > 0 for x in h.values())
               and res["delta_x167"] is not None and res["delta_x167"] > 0
               and res["delta_excess12"] is not None and res["delta_excess12"] > 0
               and res["delta_depth_strata"] is not None and res["delta_depth_strata"] > 0)
    if support:
        return "支持"
    if res["n_on"] >= 150 and res["n_off"] >= 150 and res["ci_hi"] < 0.10:
        return "削弱"
    return "不確定"


def pct(x):
    return "—" if x is None else f"{x * 100:+.1f}"


def show(res, v):
    log(f"  [{res['label']}] 成立 {res['n_on']}（回到 {pct(res['rate_on'])[1:]}%）／不成立 {res['n_off']}（回到 {pct(res['rate_off'])[1:]}%）｜W {res['W']}"
        f"｜Δ {pct(res['delta'])}pp｜p {res['p']:.4f}｜95% [{pct(res['ci_lo'])}, {pct(res['ci_hi'])}]｜不分季 {pct(res['pooled'])}｜→ {v}")
    log("     拿掉成群期：", {k: pct(x) for k, x in res["drop_cluster"].items()},
        "｜前後段：", {k: (x["n_on"], x["n_off"], pct(x["delta"])) for k, x in res["halves"].items()})
    log(f"     並列① 1.67 倍 Δ {pct(res['delta_x167'])}｜並列② 12 個月超額 Δ {pct(res['delta_excess12'])}（n={res['n_excess']}）"
        f"｜回落深度分層（季×三分位）Δ {pct(res['delta_depth_strata'])}｜只照三分位 {pct(res['delta_depth_only'])}｜切點 {res['depth_cuts']}"
        f"｜兩組都 ≥5 筆的季 {res['quarters_both_ge5']}")


judged = [k for k in pop if EV[k]["judged"] == "1"]
log("\n===== 判讀母體", len(judged), "筆（2N2）=====")
base = [OUT[k] for k in judged if OUT[k]["computable"]]
log("主量：18 個月內回到前高", sum(o["back"] for o in base), "／", len(base), f"（{np.mean([o['back'] for o in base]) * 100:.1f}%）",
    "｜曾達 1.67 倍", f"{np.mean([o['x167'] for o in base]) * 100:.1f}%", "｜曾達 2 倍", f"{np.mean([o['x2'] for o in base]) * 100:.1f}%",
    "｜12 個月內再跌三成", f"{np.mean([o['down30_12m'] for o in base]) * 100:.1f}%",
    "｜12 個月超額平均", f"{np.mean([o['excess12'] for o in base if o['excess12'] is not None]) * 100:+.1f}%")
SUMMARY = {"judged": {}, "bounds": {}, "other": {}}
for m in ("M1", "M2", "M3", "M5"):
    res = judge(rows_for(m, judged), m)
    v = verdict(res) if m != "M5" else "只印"
    flips = {}
    for mode in ("lower", "upper"):
        rb = judge(rows_for(m, judged, ymode=mode), f"{m} 存活者-{mode}")
        flips[mode] = (verdict(rb), rb["delta"], rb["p"])
        SUMMARY["bounds"][f"{m}|{mode}"] = rb
    final = v
    if m != "M5" and any(x[0] != v for x in flips.values()):
        final = "不確定（存活者）"
    show(res, final)
    log("     存活者界限（全當沒回到／全當回到）：", {k: (x[0], pct(x[1]), round(x[2], 4)) for k, x in flips.items()},
        "｜照草稿字面（兩組都 ≥5 筆的季要 8 個）：", "不足" if res["quarters_both_ge5"] < 8 else "過")
    res["verdict"], res["verdict_before_survivor"] = final, v
    SUMMARY["judged"][m] = res

log("\n===== 基線（判讀母體；各依三分位，印主量的比例）=====")
base_rows = [{"y": OUT[k]["back"], "depth": float(EV[k]["depth"]), "runup": float(EV[k]["runup"]),
              "months": int(EV[k]["months_high_to_t"]), "mktdd": OUT[k]["mkt_drawdown"]} for k in judged if OUT[k]["computable"]]
SUMMARY["baselines"] = {}
for name in ("depth", "runup", "months", "mktdd"):
    xs = [r for r in base_rows if r[name] is not None]
    c1, c2 = np.quantile([r[name] for r in xs], [1 / 3, 2 / 3])
    groups = [[r["y"] for r in xs if r[name] <= c1], [r["y"] for r in xs if c1 < r[name] <= c2], [r["y"] for r in xs if r[name] > c2]]
    SUMMARY["baselines"][name] = {"cuts": [float(c1), float(c2)], "n": [len(g) for g in groups], "rate": [float(np.mean(g)) if g else None for g in groups]}
    log(f"  {name}：切點 {c1:.3f}／{c2:.3f}｜低 {len(groups[0])} 筆 {np.mean(groups[0]) * 100:.1f}%｜中 {len(groups[1])} 筆 {np.mean(groups[1]) * 100:.1f}%｜高 {len(groups[2])} 筆 {np.mean(groups[2]) * 100:.1f}%")

log("\n===== 另印（不進判讀）=====")
variants = {
    "完全不剔（406）": pop,
    "2N1 節點全剔": [k for k in pop if EV[k]["drop_2N1"] == "0"],
    "2C 只剔代表公司": [k for k in pop if EV[k]["drop_2C"] == "0"],
    "判讀母體、剔除 t 在 2020-03～05": [k for k in judged if not ("2020-03" <= k[1] <= "2020-05")],
    "判讀母體、剔除交叉核做不了的": [k for k in judged if EV[k]["xcheck_no_trade"] == "0"],
    "判讀母體、剔除重抓序列對不上的": [k for k in judged if k not in drift],
}
for name, keys in variants.items():
    log(f" {name}：{len(keys)} 筆")
    for m in ("M1", "M2", "M3", "M5"):
        res = judge(rows_for(m, keys), f"{m}")
        show(res, verdict(res) if m != "M5" else "只印")
        SUMMARY["other"][f"{name}|{m}"] = res
# 放回 15 筆（未還原的下市事件、存託憑證）：標記值取私有的 markers.json
mk_private = {(r["code"], r["t_ym"]): r for r in json.loads((HERE / "markers.json").read_text(encoding="utf-8"))}
G = {"M1": 15, "M2": 10, "M3": 2, "M5": 50}


def on_private(m):
    def f(k):
        if k in MK:
            flag = MK[k][f"{m}_on"]
            return None if flag == "" else int(flag)
        v = mk_private[k].get(m)
        if v is None:
            return None
        return int({"M1": v <= -G[m], "M2": v >= G[m], "M3": v >= G[m], "M5": v < G[m]}[m])
    return f


keys15 = judged + EXTRA
log(f" 判讀母體＋放回 15 筆：{len(keys15)} 筆（其中主量算得出來的放回列 {sum(OUT[k]['computable'] for k in EXTRA)}）")
for m in ("M1", "M2", "M3"):
    res = judge(rows_for(m, keys15, extra_on=on_private(m)), m)
    show(res, verdict(res))
    SUMMARY["other"][f"放回 15 筆|{m}"] = res
# 標記算不出來的事件的結果率（可算率 × 結果組）
log(" 標記算不出來的事件（判讀母體）回到前高的比例：")
SUMMARY["uncomputable"] = {}
for m in ("M1", "M2", "M3", "M5"):
    un = [OUT[k]["back"] for k in judged if MK[k][f"{m}_on"] == "" and OUT[k]["computable"]]
    ok = [OUT[k]["back"] for k in judged if MK[k][f"{m}_on"] != "" and OUT[k]["computable"]]
    SUMMARY["uncomputable"][m] = {"n_un": len(un), "rate_un": float(np.mean(un)) if un else None, "n_ok": len(ok), "rate_ok": float(np.mean(ok))}
    log(f"   {m}：算不出來 {len(un)} 筆 {np.mean(un) * 100 if un else float('nan'):.1f}%｜算得出來 {len(ok)} 筆 {np.mean(ok) * 100:.1f}%")
# 另外三個只印的切法
alts = {"M1 近三個月平均 ≤ 0": lambda k: None if MK[k]["M1_recent"] == "" else int(float(MK[k]["M1_recent"]) <= 0),
        "M3 對前八季最高低 ≥ 3 個百分點": lambda k: None if MK[k]["M3_vs_max8"] == "" else int(float(MK[k]["M3_vs_max8"]) >= 3),
        "M4 合約負債季減 ≥ 20%": lambda k: None if MK[k]["M4"] == "" else int(float(MK[k]["M4"]) <= -20)}
for name, fn in alts.items():
    rows = rows_for("M1", judged, extra_on=fn)
    res = judge(rows, name) if len({r["on"] for r in rows}) == 2 else None
    if res is None:
        log(f" {name}：只有一組，算不出來")
        continue
    show(res, "只印")
    SUMMARY["other"][f"{name}"] = res

if not SYNTH:
    (HERE / "stage2_summary.json").write_text(json.dumps(SUMMARY, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
log("\nSTAGE2_DONE", "（管線自測，假的結果）" if SYNTH else "", "numpy", np.__version__, "python", sys.version.split()[0])
```

### table_a.py（表 A；sha256 前 16 碼 `23ebaa3b26baa3b3`）

```python
"""表 A：大跌之後的基準率（描述，不判；零 LLM）。設計稿第三版 §5.2。H16 的判讀已落在 stage2.out 之後才跑。
列：回落深度（月收盤第一次 ≤ 高點的 0.6／0.5／0.4）× 孤立或成群；每一個成群月自己一列。
0.6 的列＝H16 的母體 406 筆；0.5、0.4 的列＝同一批事件從 t 往後、在沒有再創新高、高點後 24 個月內、事件月 ≤ 2021-03 的條件下，
第一次跌到那個深度的月份（t′；結果窗從 t′ 起算）。成群月＝該深度自己的事件數 ≥ 月均（2015-01～2021-03 共 75 個月）的三倍。
規則：n < 20 的格只列個數；成群月的單列只印「k／n」；「成群」彙總列要成群月 ≥ 5 個才印比例。"""
import csv
import io
import json
import re
from collections import Counter
from pathlib import Path

import adjust
import official
from h16lib import mnum, ym_of

HERE = Path(__file__).parent
REP = HERE.parents[3] / "docs" / "reports" / "phase7"
N_MONTHS = 75

EV = list(csv.DictReader(io.StringIO((REP / "h16-stage1-events.csv").read_bytes().replace(b"\r\n", b"\n").decode("utf-8"))))
private = {(e["code"], e["t_ym"]): e for e in json.loads((HERE / "events_all.json").read_text(encoding="utf-8"))}
ends = official.month_ends() + json.loads((HERE / "month_ends2.json").read_text(encoding="utf-8"))
ME = {d[:7]: d for d in ends}
raw, last_seen = {}, {}
for d in ends:
    ym, ymd = d[:7], d.replace("-", "")
    for market in ("twse", "tpex"):
        for code, (_name, close) in official.load(market, ymd).items():
            last_seen[code] = max(last_seen.get(code, ""), ym)
            if close and close > 0:
                raw.setdefault(code, {})[ym] = close
FAC, _stat, _blocked = adjust.load_factors()
px2 = json.loads((HERE / "px2.json").read_text(encoding="utf-8"))
delisted = {}
tw = json.loads((HERE / "official" / "twse_delisted_all.json").read_text(encoding="utf-8"))
for date, _name, code in tw["data"]:
    y, m, d = date.split("/")
    delisted[str(code).strip()] = "%04d-%s-%s" % (int(y) + 1911, m, d)
for f in sorted((HERE / "official").glob("tpex_delisted_2*.json")):
    o = json.loads(f.read_text(encoding="utf-8"))
    for t in o.get("tables") or []:
        fl = t.get("fields") or []
        ci, di = fl.index("股票代號"), fl.index("終止上櫃日期")
        for r in t.get("data") or []:
            code = str(r[ci]).strip()
            ds = re.sub(r"[^\d/]", "", str(r[di]))
            parts = ds.split("/")
            if len(parts) != 3 and len(ds) in (6, 7):
                parts = [ds[:-4], ds[-4:-2], ds[-2:]]
            if len(parts) == 3:
                date = "%04d-%s-%s" % (int(parts[0]) + (1911 if int(parts[0]) < 1911 else 0), parts[1], parts[2])
                if code not in delisted or date > delisted[code]:
                    delisted[code] = date


def series_of(key):
    e = private[key]
    if e["source"].startswith("yfinance"):
        return {ym: v for ym, v in px2[e["ticker"]] if v and v > 0}
    return dict(adjust.adjusted(raw.get(e["code"], {}), ME, FAC.get(e["code"], [])))


def outcome(code, s, ph, t):
    n, pt = mnum(t), s[t]
    win = [(k, s[ym_of(n + k)]) for k in range(1, 19) if ym_of(n + k) in s]
    dl = delisted.get(code)
    gone = bool(dl and t <= dl[:7] <= ym_of(n + 18) and last_seen.get(code, "") <= dl[:7])
    return {"t": t, "back": int(any(v >= ph for _k, v in win)), "x167": int(any(v >= 1.67 * pt for _k, v in win)),
            "x2": int(any(v >= 2 * pt for _k, v in win)), "down30": int(any(v <= 0.7 * pt for k, v in win if k <= 12)),
            "delisted": gone}


rows = {0.6: [], 0.5: [], 0.4: []}
for r in EV:
    key = (r["code"], r["t_ym"])
    e = private[key]
    s = series_of(key)
    ph, nh = s[e["high_ym"]], mnum(e["high_ym"])
    rows[0.6].append(outcome(r["code"], s, ph, r["t_ym"]))
    for thr in (0.5, 0.4):
        n = mnum(r["t_ym"])
        while n - nh <= 24 and ym_of(n) <= "2021-03":
            v = s.get(ym_of(n))
            if v is not None:
                if v > ph:
                    break
                if v <= thr * ph:
                    rows[thr].append(outcome(r["code"], s, ph, ym_of(n)))
                    break
            n += 1


def cell(xs, key):
    if len(xs) < 20:
        return f"{sum(x[key] for x in xs)}／{len(xs)}"
    return f"{sum(x[key] for x in xs) / len(xs) * 100:.1f}%"


def line(label, xs, ratios=True):
    gone = [x for x in xs if x["delisted"]]
    if not ratios:
        body = " | ".join(f"{sum(x[k] for x in xs)}／{len(xs)}" for k in ("back", "x167", "x2", "down30"))
        return f"| {label} | {len(xs)} | {body} | {len(gone)} | — |"
    lo = sum(x["back"] for x in xs if not x["delisted"])
    hi = lo + len(gone)
    bounds = f"{lo / len(xs) * 100:.1f}%～{hi / len(xs) * 100:.1f}%" if len(xs) >= 20 else f"{lo}～{hi}／{len(xs)}"
    return (f"| {label} | {len(xs)} | {cell(xs, 'back')} | {cell(xs, 'x167')} | {cell(xs, 'x2')} | {cell(xs, 'down30')} | {len(gone)} | {bounds} |")


print("| 列 | n | 18 個月內回到前高 | 曾達 t 收盤 1.67 倍 | 曾達 2 倍 | 12 個月內再跌三成 | 結果窗內下市 | 回到前高的兩個界限（下市全當沒回到～全當回到） |")
print("|---|---:|---:|---:|---:|---:|---:|---|")
summary = {}
for thr in (0.6, 0.5, 0.4):
    xs = rows[thr]
    by_month = Counter(x["t"] for x in xs)
    mean = len(xs) / N_MONTHS
    cluster_months = sorted(m for m, c in by_month.items() if c >= 3 * mean)
    iso = [x for x in xs if x["t"] not in cluster_months]
    clu = [x for x in xs if x["t"] in cluster_months]
    name = f"回落到高點的 {thr:.1f} 以下"
    print(line(f"**{name}：全部**", xs))
    print(line(f"{name}：孤立（不在成群月）", iso))
    print(line(f"{name}：成群（{len(cluster_months)} 個成群月合計）", clu, ratios=len(cluster_months) >= 5))
    for m in cluster_months:
        print(line(f"　成群月 {m}", [x for x in xs if x["t"] == m], ratios=False))
    summary[str(thr)] = {"n": len(xs), "monthly_mean": round(mean, 2), "cluster_months": cluster_months, "n_iso": len(iso), "n_cluster": len(clu),
                         "back_all": sum(x["back"] for x in xs), "back_iso": sum(x["back"] for x in iso), "back_cluster": sum(x["back"] for x in clu)}
print()
print(json.dumps(summary, ensure_ascii=False))
(HERE / "table_a.json").write_text(json.dumps({"rows": {str(k): v for k, v in rows.items()}, "summary": summary}, ensure_ascii=False), encoding="utf-8")
```

### sanity2.py（結果落帳之後的自查；sha256 前 16 碼 `593bb7becce9cb84`）

```python
"""階段二的自查（結果落帳之後）：①全市場等權月報酬看幾個已知的月份 ②隨機抽 6 筆事件，把高點、t、結果窗的最高月收盤印出來人工對
③主量與並列量的內部一致（回到前高 ⇒ 曾達 1.67 倍，因為 t ≤ 0.6×高點）④判讀母體與表 A 的計數對得起來。"""
import json
import random
from pathlib import Path

from h16lib import mnum, ym_of

HERE = Path(__file__).parent
out = json.loads((HERE / "stage2_outcomes.json").read_text(encoding="utf-8"))
ev = {(e["code"], e["t_ym"]): e for e in json.loads((HERE / "events_all.json").read_text(encoding="utf-8"))}
px2 = json.loads((HERE / "px2.json").read_text(encoding="utf-8"))
ok = [o for o in out if o["computable"]]
print("回到前高卻沒達 1.67 倍的（應該是 0）：", sum(o["back"] and not o["x167"] for o in ok))
print("曾達 2 倍卻沒達 1.67 倍的（應該是 0）：", sum(o["x2"] and not o["x167"] for o in ok))
random.seed(7)
for o in random.sample([x for x in ok if x["src"] == "yfinance"], 6):
    e = ev[(o["code"], o["t_ym"])]
    s = dict(px2[e["ticker"]])
    n = mnum(o["t_ym"])
    win = [s[ym_of(n + k)] for k in range(1, 19) if ym_of(n + k) in s]
    print(o["code"], e["name"], "高點", e["high_ym"], round(s[e["high_ym"]], 2), "｜t", o["t_ym"], round(s[o["t_ym"]], 2),
          "｜窗內最高", round(max(win), 2), "最低(12m)", round(min(win[:12]), 2), "｜回到", o["back"], "1.67倍", o["x167"], "再跌三成", o["down30_12m"],
          "｜12m 報酬", o["ret12"], "大盤", o["mkt12"])
print("2020-03 的事件 12 個月的大盤等權報酬（應該很高）：", sorted({o["mkt12"] for o in ok if o["t_ym"] == "2020-03"}))
print("2018-10 的事件：", sorted({o["mkt12"] for o in ok if o["t_ym"] == "2018-10"}), "｜2015-08：", sorted({o["mkt12"] for o in ok if o["t_ym"] == "2015-08"}))
```

### stage2.py 的輸出（逐字）

```text
digest 相符：事件表 406 筆｜標記表 406 筆
交易所月底行情：代號 1916 ｜月份 2011-12 → 2022-09 ｜還原因子 {'除權息': 17065, '減資': 541, '重複列': 5, '擋掉（缺值或 ≤ 0）': 1, '比值在 0.2–8 之外（照用）': 6}
全市場等權：月份 129 ｜用到的月報酬 202849 ｜比值不在 0.33–3 之間剔除的 16
母體 406 ｜主量算不出來 0 []
重抓序列的「t ÷ 高點」與階段一相差超過 2 個百分點 0 []
結果窗內下市 8 [('2475', '2018-10'), ('3474', '2015-06'), ('4733', '2015-08'), ('4984', '2017-06'), ('5255', '2018-09'), ('5259', '2019-10'), ('5317', '2018-09'), ('5505', '2015-04')] ｜②不可算（第 12 個月沒有收盤） 7
結果窗裡看得到的月數分布 {0: 2, 1: 1, 6: 1, 10: 1, 11: 2, 13: 1, 16: 1, 17: 1, 18: 396}

===== 判讀母體 356 筆（2N2）=====
主量：18 個月內回到前高 58 ／ 356 （16.3%） ｜曾達 1.67 倍 23.9% ｜曾達 2 倍 12.9% ｜12 個月內再跌三成 26.1% ｜12 個月超額平均 -1.9%
  [M1] 成立 118（回到 16.9%）／不成立 199（回到 19.1%）｜W 69.0｜Δ +1.4pp｜p 0.4324｜95% [-8.9, +8.8]｜不分季 +2.1｜→ 不確定
     拿掉成群期： {'2015 夏': '-1.2', '2018': '+4.0', '2020-03': '+0.0'} ｜前後段： {'前段': (58, 82, '+4.0'), '後段': (60, 117, '-0.8')}
     並列① 1.67 倍 Δ +1.8｜並列② 12 個月超額 Δ +5.5（n=317）｜回落深度分層（季×三分位）Δ +2.3｜只照三分位 +2.5｜切點 [0.5403, 0.578]｜兩組都 ≥5 筆的季 7
     存活者界限（全當沒回到／全當回到）： {'lower': ('不確定', '+1.4', 0.4324), 'upper': ('不確定', '+1.4', 0.4324)} ｜照草稿字面（兩組都 ≥5 筆的季要 8 個）： 不足
  [M2] 成立 103（回到 18.4%）／不成立 184（回到 17.4%）｜W 58.7｜Δ -1.2pp｜p 0.6701｜95% [-7.7, +6.5]｜不分季 -1.1｜→ 不確定
     拿掉成群期： {'2015 夏': '-0.3', '2018': '-0.1', '2020-03': '-1.1'} ｜前後段： {'前段': (51, 79, '+1.4'), '後段': (52, 105, '-3.4')}
     並列① 1.67 倍 Δ -5.9｜並列② 12 個月超額 Δ -5.0（n=282）｜回落深度分層（季×三分位）Δ -2.1｜只照三分位 -0.9｜切點 [0.5377, 0.576]｜兩組都 ≥5 筆的季 6
     存活者界限（全當沒回到／全當回到）： {'lower': ('不確定', '-1.2', 0.6701), 'upper': ('不確定', '+0.3', 0.5455)} ｜照草稿字面（兩組都 ≥5 筆的季要 8 個）： 不足
  [M3] 成立 115（回到 11.3%）／不成立 237（回到 19.0%）｜W 70.2｜Δ +4.0pp｜p 0.2128｜95% [-5.7, +13.7]｜不分季 +7.7｜→ 不確定
     拿掉成群期： {'2015 夏': '+5.1', '2018': '+3.3', '2020-03': '+4.5'} ｜前後段： {'前段': (42, 114, '+3.3'), '後段': (73, 123, '+4.4')}
     並列① 1.67 倍 Δ +5.0｜並列② 12 個月超額 Δ -3.9（n=346）｜回落深度分層（季×三分位）Δ +5.3｜只照三分位 +8.1｜切點 [0.537, 0.576]｜兩組都 ≥5 筆的季 5
     存活者界限（全當沒回到／全當回到）： {'lower': ('不確定', '+4.0', 0.2128), 'upper': ('不確定', '-0.1', 0.5783)} ｜照草稿字面（兩組都 ≥5 筆的季要 8 個）： 不足
  [M5] 成立 123（回到 23.6%）／不成立 207（回到 13.5%）｜W 52.0｜Δ -0.3pp｜p 0.5902｜95% [-8.1, +7.7]｜不分季 -10.1｜→ 只印
     拿掉成群期： {'2015 夏': '+1.9', '2018': '+0.5', '2020-03': '-1.3'} ｜前後段： {'前段': (78, 70, '-4.6'), '後段': (45, 137, '+5.0')}
     並列① 1.67 倍 Δ -1.3｜並列② 12 個月超額 Δ +13.1（n=330）｜回落深度分層（季×三分位）Δ +0.4｜只照三分位 -10.2｜切點 [0.54, 0.578]｜兩組都 ≥5 筆的季 5
     存活者界限（全當沒回到／全當回到）： {'lower': ('不確定', '-0.3', 0.5902), 'upper': ('不確定', '-0.3', 0.5902)} ｜照草稿字面（兩組都 ≥5 筆的季要 8 個）： 不足

===== 基線（判讀母體；各依三分位，印主量的比例）=====
  depth：切點 0.536／0.576｜低 119 筆 16.8%｜中 120 筆 13.3%｜高 117 筆 18.8%
  runup：切點 3.853／5.703｜低 119 筆 21.8%｜中 118 筆 14.4%｜高 119 筆 12.6%
  months：切點 6.000／11.000｜低 138 筆 17.4%｜中 106 筆 12.3%｜高 112 筆 18.8%
  mktdd：切點 -0.104／0.037｜低 119 筆 26.9%｜中 118 筆 13.6%｜高 119 筆 8.4%

===== 另印（不進判讀）=====
 完全不剔（406）：406 筆
  [M1] 成立 131（回到 16.8%）／不成立 234（回到 18.4%）｜W 77.7｜Δ +1.7pp｜p 0.3952｜95% [-8.6, +10.2]｜不分季 +1.6｜→ 不確定
     拿掉成群期： {'2015 夏': '-0.5', '2018': '+5.7', '2020-03': '-0.4'} ｜前後段： {'前段': (61, 82, '+3.4'), '後段': (70, 152, '+0.5')}
     並列① 1.67 倍 Δ +2.6｜並列② 12 個月超額 Δ +4.6（n=365）｜回落深度分層（季×三分位）Δ +2.8｜只照三分位 +1.6｜切點 [0.537, 0.576]｜兩組都 ≥5 筆的季 7
  [M2] 成立 123（回到 17.9%）／不成立 212（回到 17.5%）｜W 70.6｜Δ -1.7pp｜p 0.7138｜95% [-8.3, +6.0]｜不分季 -0.4｜→ 不確定
     拿掉成群期： {'2015 夏': '-1.1', '2018': '-2.7', '2020-03': '-1.7'} ｜前後段： {'前段': (53, 81, '+1.2'), '後段': (70, 131, '-3.6')}
     並列① 1.67 倍 Δ -4.1｜並列② 12 個月超額 Δ -6.5（n=330）｜回落深度分層（季×三分位）Δ -2.6｜只照三分位 -0.2｜切點 [0.533, 0.573]｜兩組都 ≥5 筆的季 6
  [M3] 成立 124（回到 11.3%）／不成立 278（回到 18.7%）｜W 78.2｜Δ +2.3pp｜p 0.3366｜95% [-6.6, +11.5]｜不分季 +7.4｜→ 不確定
     拿掉成群期： {'2015 夏': '+2.9', '2018': '+2.9', '2020-03': '+2.7'} ｜前後段： {'前段': (43, 117, '+3.4'), '後段': (81, 161, '+1.7')}
     並列① 1.67 倍 Δ +2.0｜並列② 12 個月超額 Δ -3.8（n=396）｜回落深度分層（季×三分位）Δ +3.5｜只照三分位 +8.1｜切點 [0.5337, 0.575]｜兩組都 ≥5 筆的季 6
  [M5] 成立 134（回到 23.9%）／不成立 245（回到 13.5%）｜W 55.5｜Δ +1.0pp｜p 0.4808｜95% [-7.4, +10.1]｜不分季 -10.4｜→ 只印
     拿掉成群期： {'2015 夏': '+3.4', '2018': '+2.0', '2020-03': '-0.6'} ｜前後段： {'前段': (80, 72, '-3.3'), '後段': (54, 173, '+5.9')}
     並列① 1.67 倍 Δ -0.1｜並列② 12 個月超額 Δ +13.0（n=379）｜回落深度分層（季×三分位）Δ +1.4｜只照三分位 -10.2｜切點 [0.536, 0.576]｜兩組都 ≥5 筆的季 5
 2N1 節點全剔：334 筆
  [M1] 成立 109（回到 15.6%）／不成立 187（回到 19.3%）｜W 63.2｜Δ +3.1pp｜p 0.3020｜95% [-7.1, +11.3]｜不分季 +3.7｜→ 不確定
     拿掉成群期： {'2015 夏': '-0.3', '2018': '+5.4', '2020-03': '+1.7'} ｜前後段： {'前段': (52, 76, '+6.1'), '後段': (57, 111, '+0.7')}
     並列① 1.67 倍 Δ +2.7｜並列② 12 個月超額 Δ +2.8（n=296）｜回落深度分層（季×三分位）Δ +3.1｜只照三分位 +4.0｜切點 [0.539, 0.577]｜兩組都 ≥5 筆的季 7
  [M2] 成立 96（回到 17.7%）／不成立 172（回到 16.9%）｜W 54.3｜Δ -0.5pp｜p 0.6156｜95% [-8.8, +8.1]｜不分季 -0.8｜→ 不足
     拿掉成群期： {'2015 夏': '-0.2', '2018': '+0.6', '2020-03': '-0.3'} ｜前後段： {'前段': (48, 72, '+2.6'), '後段': (48, 100, '-3.0')}
     並列① 1.67 倍 Δ -4.2｜並列② 12 個月超額 Δ -1.7（n=263）｜回落深度分層（季×三分位）Δ -1.0｜只照三分位 -0.4｜切點 [0.533, 0.575]｜兩組都 ≥5 筆的季 6
  [M3] 成立 109（回到 11.9%）／不成立 221（回到 18.1%）｜W 65.8｜Δ +2.2pp｜p 0.3697｜95% [-8.6, +12.0]｜不分季 +6.2｜→ 不確定
     拿掉成群期： {'2015 夏': '+4.3', '2018': '+1.4', '2020-03': '+2.7'} ｜前後段： {'前段': (39, 105, '+0.8'), '後段': (70, 116, '+3.1')}
     並列① 1.67 倍 Δ +4.2｜並列② 12 個月超額 Δ -5.1（n=324）｜回落深度分層（季×三分位）Δ +3.9｜只照三分位 +6.5｜切點 [0.5337, 0.576]｜兩組都 ≥5 筆的季 5
  [M5] 成立 114（回到 22.8%）／不成立 194（回到 13.4%）｜W 48.9｜Δ +1.2pp｜p 0.4802｜95% [-7.5, +9.0]｜不分季 -9.4｜→ 只印
     拿掉成群期： {'2015 夏': '+1.5', '2018': '+2.8', '2020-03': '+0.3'} ｜前後段： {'前段': (70, 66, '-1.6'), '後段': (44, 128, '+4.5')}
     並列① 1.67 倍 Δ -0.1｜並列② 12 個月超額 Δ +13.4（n=308）｜回落深度分層（季×三分位）Δ +2.1｜只照三分位 -9.4｜切點 [0.5373, 0.577]｜兩組都 ≥5 筆的季 4
 2C 只剔代表公司：382 筆
  [M1] 成立 124（回到 16.1%）／不成立 217（回到 18.9%）｜W 72.4｜Δ +2.9pp｜p 0.3061｜95% [-7.5, +12.1]｜不分季 +2.8｜→ 不確定
     拿掉成群期： {'2015 夏': '-0.0', '2018': '+6.7', '2020-03': '+0.7'} ｜前後段： {'前段': (59, 80, '+4.8'), '後段': (65, 137, '+1.3')}
     並列① 1.67 倍 Δ +2.1｜並列② 12 個月超額 Δ +5.0（n=341）｜回落深度分層（季×三分位）Δ +3.9｜只照三分位 +3.0｜切點 [0.54, 0.577]｜兩組都 ≥5 筆的季 7
  [M2] 成立 112（回到 18.8%）／不成立 201（回到 16.9%）｜W 65.1｜Δ -3.0pp｜p 0.7980｜95% [-10.4, +4.6]｜不分季 -1.8｜→ 不確定
     拿掉成群期： {'2015 夏': '-2.2', '2018': '-3.6', '2020-03': '-3.0'} ｜前後段： {'前段': (52, 79, '+0.0'), '後段': (60, 122, '-5.1')}
     並列① 1.67 倍 Δ -5.9｜並列② 12 個月超額 Δ -5.3（n=308）｜回落深度分層（季×三分位）Δ -4.1｜只照三分位 -1.5｜切點 [0.534, 0.574]｜兩組都 ≥5 筆的季 6
  [M3] 成立 121（回到 10.7%）／不成立 257（回到 19.1%）｜W 74.6｜Δ +2.9pp｜p 0.2802｜95% [-6.3, +12.2]｜不分季 +8.3｜→ 不確定
     拿掉成群期： {'2015 夏': '+4.0', '2018': '+2.9', '2020-03': '+3.4'} ｜前後段： {'前段': (43, 113, '+3.3'), '後段': (78, 144, '+2.7')}
     並列① 1.67 倍 Δ +3.9｜並列② 12 個月超額 Δ -3.7（n=372）｜回落深度分層（季×三分位）Δ +4.2｜只照三分位 +8.8｜切點 [0.536, 0.576]｜兩組都 ≥5 筆的季 6
  [M5] 成立 130（回到 23.8%）／不成立 225（回到 13.3%）｜W 54.8｜Δ +0.8pp｜p 0.5104｜95% [-8.1, +10.4]｜不分季 -10.5｜→ 只印
     拿掉成群期： {'2015 夏': '+2.8', '2018': '+2.1', '2020-03': '-0.8'} ｜前後段： {'前段': (76, 72, '-3.2'), '後段': (54, 153, '+5.4')}
     並列① 1.67 倍 Δ -1.1｜並列② 12 個月超額 Δ +11.9（n=355）｜回落深度分層（季×三分位）Δ +1.1｜只照三分位 -10.5｜切點 [0.539, 0.577]｜兩組都 ≥5 筆的季 5
 判讀母體、剔除 t 在 2020-03～05：335 筆
  [M1] 成立 111（回到 15.3%）／不成立 185（回到 15.7%）｜W 64.3｜Δ +0.0pp｜p 0.5702｜95% [-11.4, +7.7]｜不分季 +0.4｜→ 不確定
     拿掉成群期： {'2015 夏': '-3.4', '2018': '+2.2', '2020-03': '+0.0'} ｜前後段： {'前段': (58, 82, '+4.0'), '後段': (53, 103, '-4.0')}
     並列① 1.67 倍 Δ +1.5｜並列② 12 個月超額 Δ +0.9（n=296）｜回落深度分層（季×三分位）Δ +0.3｜只照三分位 +0.2｜切點 [0.541, 0.579]｜兩組都 ≥5 筆的季 6
  [M2] 成立 99（回到 16.2%）／不成立 170（回到 13.5%）｜W 55.3｜Δ -1.1pp｜p 0.6615｜95% [-7.6, +7.6]｜不分季 -2.6｜→ 不足
     拿掉成群期： {'2015 夏': '+0.0', '2018': '+0.2', '2020-03': '-1.1'} ｜前後段： {'前段': (51, 79, '+1.4'), '後段': (48, 91, '-3.4')}
     並列① 1.67 倍 Δ -6.0｜並列② 12 個月超額 Δ -8.3（n=264）｜回落深度分層（季×三分位）Δ -2.1｜只照三分位 -2.8｜切點 [0.54, 0.577]｜兩組都 ≥5 筆的季 5
  [M3] 成立 112（回到 9.8%）／不成立 219（回到 16.0%）｜W 67.6｜Δ +4.5pp｜p 0.1709｜95% [-6.0, +14.4]｜不分季 +6.2｜→ 不確定
     拿掉成群期： {'2015 夏': '+5.9', '2018': '+4.2', '2020-03': '+4.5'} ｜前後段： {'前段': (42, 114, '+3.3'), '後段': (70, 105, '+5.4')}
     並列① 1.67 倍 Δ +5.4｜並列② 12 個月超額 Δ -5.0（n=325）｜回落深度分層（季×三分位）Δ +6.1｜只照三分位 +6.9｜切點 [0.54, 0.578]｜兩組都 ≥5 筆的季 5
  [M5] 成立 110（回到 20.0%）／不成立 199（回到 11.6%）｜W 47.0｜Δ -1.3pp｜p 0.6676｜95% [-9.5, +8.5]｜不分季 -8.4｜→ 只印
     拿掉成群期： {'2015 夏': '+0.7', '2018': '-0.9', '2020-03': '-1.3'} ｜前後段： {'前段': (78, 70, '-4.6'), '後段': (32, 129, '+3.7')}
     並列① 1.67 倍 Δ -3.9｜並列② 12 個月超額 Δ +3.9（n=309）｜回落深度分層（季×三分位）Δ -0.1｜只照三分位 -8.5｜切點 [0.541, 0.579]｜兩組都 ≥5 筆的季 4
 判讀母體、剔除交叉核做不了的：343 筆
  [M1] 成立 117（回到 17.1%）／不成立 193（回到 19.7%）｜W 67.8｜Δ +2.1pp｜p 0.3756｜95% [-8.0, +9.5]｜不分季 +2.6｜→ 不確定
     拿掉成群期： {'2015 夏': '-0.5', '2018': '+5.1', '2020-03': '+0.7'} ｜前後段： {'前段': (57, 78, '+4.9'), '後段': (60, 115, '-0.3')}
     並列① 1.67 倍 Δ +2.6｜並列② 12 個月超額 Δ +6.9（n=310）｜回落深度分層（季×三分位）Δ +2.9｜只照三分位 +2.8｜切點 [0.541, 0.578]｜兩組都 ≥5 筆的季 7
  [M2] 成立 98（回到 19.4%）／不成立 183（回到 17.5%）｜W 57.0｜Δ -2.5pp｜p 0.7651｜95% [-9.4, +5.3]｜不分季 -1.9｜→ 不足
     拿掉成群期： {'2015 夏': '-2.0', '2018': '-2.3', '2020-03': '-2.2'} ｜前後段： {'前段': (47, 79, '+0.4'), '後段': (51, 104, '-4.9')}
     並列① 1.67 倍 Δ -7.5｜並列② 12 個月超額 Δ -7.1（n=276）｜回落深度分層（季×三分位）Δ -4.4｜只照三分位 -1.7｜切點 [0.5377, 0.5757]｜兩組都 ≥5 筆的季 6
  [M3] 成立 110（回到 11.8%）／不成立 229（回到 19.7%）｜W 66.9｜Δ +3.8pp｜p 0.2307｜95% [-6.3, +14.0]｜不分季 +7.8｜→ 不確定
     拿掉成群期： {'2015 夏': '+5.4', '2018': '+3.1', '2020-03': '+4.4'} ｜前後段： {'前段': (39, 108, '+2.6'), '後段': (71, 121, '+4.7')}
     並列① 1.67 倍 Δ +4.9｜並列② 12 個月超額 Δ -4.5（n=333）｜回落深度分層（季×三分位）Δ +5.1｜只照三分位 +8.2｜切點 [0.5383, 0.576]｜兩組都 ≥5 筆的季 5
  [M5] 成立 116（回到 25.0%）／不成立 201（回到 13.9%）｜W 49.5｜Δ -1.4pp｜p 0.6747｜95% [-9.3, +6.2]｜不分季 -11.1｜→ 只印
     拿掉成群期： {'2015 夏': '+0.5', '2018': '-1.0', '2020-03': '-2.6'} ｜前後段： {'前段': (73, 66, '-5.8'), '後段': (43, 135, '+3.7')}
     並列① 1.67 倍 Δ -2.6｜並列② 12 個月超額 Δ +12.6（n=317）｜回落深度分層（季×三分位）Δ -0.7｜只照三分位 -11.2｜切點 [0.5403, 0.5777]｜兩組都 ≥5 筆的季 5
 判讀母體、剔除重抓序列對不上的：356 筆
  [M1] 成立 118（回到 16.9%）／不成立 199（回到 19.1%）｜W 69.0｜Δ +1.4pp｜p 0.4324｜95% [-8.9, +8.8]｜不分季 +2.1｜→ 不確定
     拿掉成群期： {'2015 夏': '-1.2', '2018': '+4.0', '2020-03': '+0.0'} ｜前後段： {'前段': (58, 82, '+4.0'), '後段': (60, 117, '-0.8')}
     並列① 1.67 倍 Δ +1.8｜並列② 12 個月超額 Δ +5.5（n=317）｜回落深度分層（季×三分位）Δ +2.3｜只照三分位 +2.5｜切點 [0.5403, 0.578]｜兩組都 ≥5 筆的季 7
  [M2] 成立 103（回到 18.4%）／不成立 184（回到 17.4%）｜W 58.7｜Δ -1.2pp｜p 0.6701｜95% [-7.7, +6.5]｜不分季 -1.1｜→ 不確定
     拿掉成群期： {'2015 夏': '-0.3', '2018': '-0.1', '2020-03': '-1.1'} ｜前後段： {'前段': (51, 79, '+1.4'), '後段': (52, 105, '-3.4')}
     並列① 1.67 倍 Δ -5.9｜並列② 12 個月超額 Δ -5.0（n=282）｜回落深度分層（季×三分位）Δ -2.1｜只照三分位 -0.9｜切點 [0.5377, 0.576]｜兩組都 ≥5 筆的季 6
  [M3] 成立 115（回到 11.3%）／不成立 237（回到 19.0%）｜W 70.2｜Δ +4.0pp｜p 0.2128｜95% [-5.7, +13.7]｜不分季 +7.7｜→ 不確定
     拿掉成群期： {'2015 夏': '+5.1', '2018': '+3.3', '2020-03': '+4.5'} ｜前後段： {'前段': (42, 114, '+3.3'), '後段': (73, 123, '+4.4')}
     並列① 1.67 倍 Δ +5.0｜並列② 12 個月超額 Δ -3.9（n=346）｜回落深度分層（季×三分位）Δ +5.3｜只照三分位 +8.1｜切點 [0.537, 0.576]｜兩組都 ≥5 筆的季 5
  [M5] 成立 123（回到 23.6%）／不成立 207（回到 13.5%）｜W 52.0｜Δ -0.3pp｜p 0.5902｜95% [-8.1, +7.7]｜不分季 -10.1｜→ 只印
     拿掉成群期： {'2015 夏': '+1.9', '2018': '+0.5', '2020-03': '-1.3'} ｜前後段： {'前段': (78, 70, '-4.6'), '後段': (45, 137, '+5.0')}
     並列① 1.67 倍 Δ -1.3｜並列② 12 個月超額 Δ +13.1（n=330）｜回落深度分層（季×三分位）Δ +0.4｜只照三分位 -10.2｜切點 [0.54, 0.578]｜兩組都 ≥5 筆的季 5
 判讀母體＋放回 15 筆：371 筆（其中主量算得出來的放回列 15）
  [M1] 成立 118（回到 16.9%）／不成立 200（回到 19.0%）｜W 69.1｜Δ +1.4pp｜p 0.4358｜95% [-9.0, +8.8]｜不分季 +2.1｜→ 不確定
     拿掉成群期： {'2015 夏': '-1.3', '2018': '+3.9', '2020-03': '-0.0'} ｜前後段： {'前段': (58, 82, '+4.0'), '後段': (60, 118, '-0.9')}
     並列① 1.67 倍 Δ +1.8｜並列② 12 個月超額 Δ +5.7（n=318）｜回落深度分層（季×三分位）Δ +2.2｜只照三分位 +2.4｜切點 [0.5407, 0.578]｜兩組都 ≥5 筆的季 7
  [M2] 成立 103（回到 18.4%）／不成立 184（回到 17.4%）｜W 58.7｜Δ -1.2pp｜p 0.6701｜95% [-7.7, +6.5]｜不分季 -1.1｜→ 不確定
     拿掉成群期： {'2015 夏': '-0.3', '2018': '-0.1', '2020-03': '-1.1'} ｜前後段： {'前段': (51, 79, '+1.4'), '後段': (52, 105, '-3.4')}
     並列① 1.67 倍 Δ -5.9｜並列② 12 個月超額 Δ -5.0（n=282）｜回落深度分層（季×三分位）Δ -2.1｜只照三分位 -0.9｜切點 [0.5377, 0.576]｜兩組都 ≥5 筆的季 6
  [M3] 成立 115（回到 11.3%）／不成立 237（回到 19.0%）｜W 70.2｜Δ +4.0pp｜p 0.2128｜95% [-5.7, +13.7]｜不分季 +7.7｜→ 不確定
     拿掉成群期： {'2015 夏': '+5.1', '2018': '+3.3', '2020-03': '+4.5'} ｜前後段： {'前段': (42, 114, '+3.3'), '後段': (73, 123, '+4.4')}
     並列① 1.67 倍 Δ +5.0｜並列② 12 個月超額 Δ -3.9（n=346）｜回落深度分層（季×三分位）Δ +5.3｜只照三分位 +8.1｜切點 [0.537, 0.576]｜兩組都 ≥5 筆的季 5
 標記算不出來的事件（判讀母體）回到前高的比例：
   M1：算不出來 39 筆 0.0%｜算得出來 317 筆 18.3%
   M2：算不出來 69 筆 10.1%｜算得出來 287 筆 17.8%
   M3：算不出來 4 筆 0.0%｜算得出來 352 筆 16.5%
   M5：算不出來 26 筆 3.8%｜算得出來 330 筆 17.3%
  [M1 近三個月平均 ≤ 0] 成立 160（回到 19.4%）／不成立 157（回到 17.2%）｜W 68.5｜Δ +1.7pp｜p 0.4118｜95% [-6.9, +9.9]｜不分季 -2.2｜→ 只印
     拿掉成群期： {'2015 夏': '+6.2', '2018': '-0.8', '2020-03': '+0.7'} ｜前後段： {'前段': (87, 53, '-4.8'), '後段': (73, 104, '+6.9')}
     並列① 1.67 倍 Δ +2.3｜並列② 12 個月超額 Δ -2.3（n=317）｜回落深度分層（季×三分位）Δ +1.8｜只照三分位 -2.0｜切點 [0.5403, 0.578]｜兩組都 ≥5 筆的季 6
  [M3 對前八季最高低 ≥ 3 個百分點] 成立 199（回到 14.6%）／不成立 126（回到 22.2%）｜W 70.5｜Δ +3.0pp｜p 0.3049｜95% [-6.1, +13.5]｜不分季 +7.6｜→ 只印
     拿掉成群期： {'2015 夏': '+5.7', '2018': '+0.4', '2020-03': '+4.4'} ｜前後段： {'前段': (80, 63, '-4.0'), '後段': (119, 63, '+9.0')}
     並列① 1.67 倍 Δ +2.6｜並列② 12 個月超額 Δ -0.2（n=325）｜回落深度分層（季×三分位）Δ +4.2｜只照三分位 +7.7｜切點 [0.539, 0.577]｜兩組都 ≥5 筆的季 6
  [M4 合約負債季減 ≥ 20%] 成立 19（回到 10.5%）／不成立 40（回到 27.5%）｜W 11.5｜Δ +12.6pp｜p 0.1969｜95% [-6.9, +43.5]｜不分季 +17.0｜→ 只印
     拿掉成群期： {'2015 夏': '+12.6', '2018': '+27.0', '2020-03': '+2.2'} ｜前後段： {'前段': (0, 0, '—'), '後段': (19, 40, '+12.6')}
     並列① 1.67 倍 Δ +9.0｜並列② 12 個月超額 Δ +8.1（n=58）｜回落深度分層（季×三分位）Δ +12.5｜只照三分位 +16.4｜切點 [0.5323, 0.5747]｜兩組都 ≥5 筆的季 2

STAGE2_DONE  numpy 2.5.1 python 3.14.6
```
