# H17 結果（回測甲）：大漲之後六成二兩年內回落四成；漲得急、漲得多的崩得更多，但平均報酬分不出差別；發股分不出

> 日期 2026-11-23｜判讀線：[`registration.md`](registration.md)「2026-11-23｜新假說 H17」（commit `86e9fe86`）｜階段一（事件表、標記表、切點與 digest）：commit `6c27d646`｜
> 假結果自查與判讀力：commit `801ecede`。三筆都早於任何結果的計算。**一次判讀，沒有重跑、沒有改門檻。** 只進假說帳，不改任何 filter、候選狀態、排序（G10）。
> 載體：Phase 8 第二個修正案「劇本時間線」第 0 步（使用者 2026-11-23：「我以為反例的洞是要先做回測的」）。方法骨架取自 Greenwood、Shleifer、You〈Bubbles for Fama〉，搬到台股個股上；不是複製，只能比方向。

## 白話版（先讀這段）

> 2026-11-23 使用者說報告太複雜之後加的。數字都出自下面各節，沒有新的主張、不改任何判讀。

**問的問題**：一檔台股兩年內已經漲一倍、而且比大盤多漲一倍，接下來會怎樣？（2016–2024 年，共 1,078 次、867 檔）

1. **多數會崩**：62% 在兩年內從高點跌掉四成。隨便一檔、隨便一個月起算，這個比例約 29%。
2. **崩之前常常還會再漲一段**：崩的那些，中位數再漲 26%、約 2 個月後才見高點；當月就是最高點的只有四分之一。
3. **繼續飛的不比平常少**：13% 在一年內再翻一倍（隨便一檔約 8%）。
4. **買在那個月、放一年**：典型的一檔（中位數）輸大盤 19%，平均只輸 2%——輸的多、贏的少，但贏的贏很大。

**哪種更容易崩**：漲得越來越快的（80% 對 52%）、漲得特別多的（76% 對 55%）。但這兩種一年後的平均報酬沒有比較差；
而且可能有一部分只是「波動大的股票本來就容易跌四成」。公司有沒有發新股，樣本太少、分不出來。

**它回答不了的**：哪一檔會是那 13%；也看不到「劇本對了、股價卻沒漲」——它是從「已經漲了」出發的。後者要從事件出發（回測乙），還沒做。

**怎麼用**：只當「已定價嗎」那一句的脈絡（已經漲一倍的東西，崩是常態、再翻倍是少數），不是買賣訊號、不接任何門檻。
上面 1、3 的「隨便一檔」對照是看過結果之後才加的，只當脈絡。

## 一句話

台股 2016-12～2024-10，一檔股票兩年漲一倍以上、而且比大盤多漲一倍（1,078 筆、867 檔）之後：

- **兩年內從高點回落四成的占 62%。** 同一段時間隨便一檔股票的隨便一個月，照同一個定義是三成左右。
- **一年內再翻一倍的占 13%**（隨便一檔約 8%）；**兩年內 20%**（隨便一檔也是兩成）。
- 一年後的超額報酬**平均 −2%、中位數 −19%**：三分之二輸大盤，少數大贏把平均拉回來（超額為正的 348 筆裡，最大的 54 筆占了正超額的 55%）。

三個特徵：**漲得急（加速）與漲得多**的崩得更多（80% 對 52%、76% 對 55%，兩個都判「支持」），但一年的平均超額分不出差別（「不確定」）。
**發股**兩邊都分不出（「不確定」）——這一組只有 119 筆，真的差 10 個百分點時大約三次只有一次判得出來（判讀力先寫在登記），所以能說的是「這個樣本量分不出」，不是「發股沒有用」。

## 判讀

判讀母體 1,078 筆（階段二剔除「疑似未還原（結果側）」0 筆）。顯著線：單尾 p ≤ 0.05 ÷ 6＝0.0083。Δ 的方向：崩＝成立組 − 不成立組；籃子＝不成立組 − 成立組（正的＝成立組比較差）。

| 標記 | 家族 | 成立組 | 不成立組 | 季內資訊量 W | Δ | p | 95% 區間 | 前段／後段 Δ | 拿掉 2021 年 | 同向量 | 判讀 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I 發股 | 崩 | 119 筆 67.2% | 947 筆 61.0% | 103.4 | +4.9 | 0.165 | −4.2～+13.1 | +0.8／+8.5 | +3.5 | +8.0 | **不確定** |
| A 加速 | 崩 | 356 筆 80.1% | 710 筆 52.1% | 199.9 | **+23.4** | 0.0001 | +17.1～+29.9 | +30.1／+19.7 | +25.9 | +21.7 | **支持** |
| S 漲幅大小 | 崩 | 360 筆 76.1% | 718 筆 54.5% | 229.3 | **+19.6** | 0.0001 | +14.3～+24.8 | +21.9／+18.0 | +22.1 | +16.7 | **支持** |
| I 發股 | 籃子 | 119 筆 −8.1% | 947 筆 −2.3% | 103.4 | +6.2 | 0.164 | −5.3～+16.0 | +8.4／+4.4 | +8.9 | −3.6 | **不確定** |
| A 加速 | 籃子 | 356 筆 −7.7% | 710 筆 +0.7% | 199.9 | +2.6 | 0.312 | −9.9～+14.3 | −4.3／+6.4 | +1.9 | −4.7 | **不確定** |
| S 漲幅大小 | 籃子 | 360 筆 −6.5% | 718 筆 −0.2% | 229.3 | +2.6 | 0.287 | −7.9～+12.4 | +3.1／+2.3 | +1.6 | +1.6 | **不確定** |

- Δ、區間、前後段、拿掉年、同向量的單位都是百分點。「成立組」「不成立組」那兩欄是沒有分層的原始比例（崩的比例，或 12 個月平均超額）；Δ 是季內加權之後的差，所以不等於兩欄相減。
- 「同向量」：崩＝把門檻換成回落五成重算的 Δ；籃子＝季內加權的「不成立組 12 個月內曾達 2 倍的比例 − 成立組」。
- 前段＝t ≤ 2020-12、後段＝t ≥ 2021-01。兩段各組的筆數：I 56／386、63／561；A 96／344、260／366；S 145／301、215／417。
- **存活者**：結果窗內下市的 4 筆（12 個月內 1 筆）。崩的兩個界限（全當崩、全當沒崩）與籃子的界限（下市當 −100%）各判一次，六格的判讀都沒有變。
- **資料**：yfinance 另算一次，兩個來源結果不同的 7 筆、沒得比的 23 筆；剔除那 7 筆之後六格的判讀都沒有變。
- 籃子三格不是「削弱」：削弱要區間上界低於 10 個百分點，三格的上界是 16.0、14.3、12.4。也就是說，**這份資料排除不了「成立組一年少賺十個百分點」**，只是也量不出來。

## 讀這個結果要一起看的三件事

1. **加速與漲幅大小不是兩個獨立的發現。** 兩個都成立的 249 筆（A 成立 356、S 成立 360）。拆成四格（事後看的，不進判讀）：只有加速 107 筆崩 74%、只有漲幅大 103 筆崩 58%、兩個都有 249 筆崩 83%、兩個都沒有 607 筆崩 51%——看起來帶得動的比較像是加速，但這是事後看的四格、沒有分層、只有 107 對 103 筆，只能當之後要量的假說。
2. **它們很可能有一部分只是在量波動。** 只印的「波動」（過去 12 個月月報酬的標準差在全市場的百分位，上三分之一）差得比兩個判的標記都多：79% 對 52%（Δ +27.5 個百分點）。「從高點回落四成」對波動大的股票本來就容易成立。波動沒有登記成判的標記，這裡只能照實寫。
3. **「崩」不等於「從 t 那天起賠錢」。** 崩的 665 筆裡，回落之前還再漲了中位數 26%（平均 59%），離 t 的中位數是 2 個月（平均 4.2 個月；論文在美國產業上看到的是平均約 6 個月、30%）；t 當月就是最高的只有 173 筆（26%）。崩的 665 筆裡有 130 筆在兩年內也曾經達到 t 的兩倍。

## 後果（照登記第 9 條，一字不改地套）

- I 的「崩」是不確定 → 事件字彙裡「供應商籌錢」那一種**留在字彙、標「回測沒有量出分辨力」**；卡 6 上的發股維持是一段的觀察。
- 沒有任何一個標記的「籃子」是支持 → 給使用者的一句：**「大漲之後這幾個特徵沒有量出能讓籃子變好的分辨力。」**
- 第 8 條的基準率表交付（下一節）。**階段一的事件表（[h17-stage1-events.csv](h17-stage1-events.csv)）就是 Phase 8 的彙編**；之後補劇本卡從這張表挑，挑的規則另在劇本卡 README 的補樣本登記寫下。
- 登記沒有替「A、S 的崩是支持」寫後果。它進假說帳，**不接任何東西**：不進「已定價嗎」、不成為任何一檔的條件。要用它得另外決定。
- 不改任何 filter、候選狀態、排序、門檻。

## 基準率（登記第 8 條；描述，不判）

| 母體 | 筆數 | 兩年內回落四成 | 12 個月內曾達 2 倍 | 24 個月內曾達 2 倍 | 6 個月內先跌三成 | 12 個月超額 平均 | 中位數 | 24 個月超額 平均 |
|---|---|---|---|---|---|---|---|---|
| **判讀母體** | 1,078 | **61.7%** | **12.6%** | **20.2%** | 21.4% | −2.3% | −18.7% | −11.3% |
| 漲幅最小的三分之一 | 359 | 52.4% | 12.3% | 20.3% | 13.1% | −1.0% | −13.7% | −9.7% |
| 中間 | 359 | 56.5% | 14.8% | 23.7% | 21.4% | +0.6% | −17.5% | −11.0% |
| 漲幅最大的三分之一 | 360 | 76.1% | 10.8% | 16.7% | 29.7% | −6.5% | −26.8% | −13.0% |
| 2017 年 | 148 | 74.3% | 12.8% | 18.2% | 9.5% | −1.6% | −12.2% | −11.5% |
| 2018 年 | 74 | 77.0% | 6.8% | 10.8% | 45.9% | −10.5% | −20.2% | −21.5% |
| 2019 年 | 65 | 43.1% | 15.4% | 27.7% | 18.5% | +8.6% | −18.7% | −21.3% |
| 2020 年 | 158 | 56.3% | 22.2% | 27.2% | 13.3% | −2.3% | −25.2% | −30.4% |
| 2021 年 | 202 | 73.3% | 5.9% | 10.4% | 29.7% | −14.3% | −26.1% | −32.2% |
| 2022 年 | 76 | 38.2% | 14.5% | 26.3% | 22.4% | −1.0% | −17.1% | −17.8% |
| 2023 年 | 172 | 44.2% | 16.3% | 23.3% | 16.9% | +12.9% | −17.2% | +21.4% |
| 2024 年（到 10 月） | 182 | 69.8% | 8.8% | 22.5% | 23.6% | −4.9% | −14.1% | +8.3% |

- 2016 年只有 1 筆（t＝2016-12），沒有列。
- 各年的回落比例從 38% 到 77%，年與年的差距比任何一個標記的 Δ 都大：**大漲之後會不會回落，跟那一年的環境關係很大**（描述，沒有檢定）。
- 單檔最大貢獻：判讀母體的 12 個月超額合計是負的，登記的那個比例（最大一檔 ÷ 總超額）算不出來；改看「超額為正的 348 筆合計 +221.6（單位：一筆的 100%），最大的 10 筆占 19%、最大的 54 筆（5% 的事件）占 55%；為負的 730 筆合計 −246.5」。
- 崩 × 兩年內曾達 2 倍的四格：崩而沒達 2 倍 535 筆（50%）、沒崩也沒達 2 倍 325 筆（30%）、崩而且曾達 2 倍 130 筆（12%）、沒崩而且達 2 倍 88 筆（8%）。
- 12 個月報酬（不扣大盤）的分位：10% 是 −44%、25% 是 −28%、中位數 −7%、75% 是 +28%、90% 是 +77%、95% 是 +135%、99% 是 +298%。

## 對照脈絡（看過結果之後才加；不進判讀、不改任何判讀線）

沒有對照，六成二沒有東西可以比。對照母體＝同一段時間每個月底、未還原收盤 ≥ 5 元的每一檔（含下市），160,012 個「檔 × 月」，照同一個定義算。

| | 兩年內回落四成 | 12 個月內曾達 2 倍 | 24 個月內曾達 2 倍 | 6 個月內先跌三成 | 12 個月超額 平均 | 中位數 | 12 個月後比 t 高 |
|---|---|---|---|---|---|---|---|
| 大漲之後（判讀母體） | 61.7% | 12.6% | 20.2% | 21.4% | −2.3% | −18.7% | 43.3% |
| 隨便一檔的隨便一個月 | 29.4% | 8.4% | 20.2% | 6.6% | +0.2% | −9.6% | 57.2% |
| 同上，照事件的月份分布加權 | 31.6% | 8.5% | 18.8% | 6.3% | +0.1% | — | 54.7% |

- 大漲之後，**回落的機會是平常的兩倍、短期急跌的機會是三倍多，再翻一倍的機會沒有比較差**（一年內還略高），**一年的平均超額沒有量出差別、中位數差一截**（事件的平均 −2.3%，以事件月為抽樣單位的 95% 區間約 −7%～+3%，審查者算的）。
- 這跟論文在美國產業上的主要發現同一個方向：大漲之後平均報酬沒有可預期地變差，但崩的機率明顯升高。
- 對照母體裡同一檔股票相鄰的月高度重疊，這張表只能當描述，不能做檢定。

## 另印（登記第 8 條；不進判讀）

| 母體 | 筆數 | 回落四成 | 12 個月曾達 2 倍 | 24 個月 | 12 個月超額 平均 | 中位數 | 崩的 Δ：I／A／S | 籃子的 Δ：I／A／S |
|---|---|---|---|---|---|---|---|---|
| t 在 2013-12～2016-11 | 343 | 54.2% | 6.7% | 12.5% | −4.6% | −15.1% | +7.8／+17.2／+17.8 | −5.4／−9.1／+4.3 |
| 免除五年條件的那一組 | 60 | 66.7% | 8.3% | 18.3% | −7.7% | −27.3% | 0.0／+15.7／+16.2 | −18.5／+3.4／−3.4 |
| 放回資料旗標的事件 | 1,091 | 61.5% | 13.0% | 20.6% | −1.9% | −18.7% | +3.9／+23.6／+19.7 | +5.3／+1.2／+1.1 |
| 剔除交叉核做不了的 | 1,054 | 61.4% | 12.7% | 20.2% | −2.2% | −18.7% | +5.8／+23.7／+19.7 | +5.5／+2.5／+2.4 |
| 剔除金融保險與建材營造 | 1,016 | 61.7% | 13.3% | 21.2% | −1.7% | −18.0% | +5.0／+24.4／+19.3 | +6.7／+0.8／+1.7 |
| 不加五年條件（重新偵測） | 1,159 | 61.9% | 12.6% | 20.6% | −2.9% | −19.0% | — | — |
| 不設底價（重新偵測） | 1,111 | 61.7% | 12.9% | 20.4% | −2.8% | −18.9% | — | — |

- 更早的那一段（2013-12～2016-11，343 筆）方向一樣：崩 54%、加速與漲幅大的 Δ 是 +17 個百分點上下。那一段不在判讀母體裡（面板不足 60 個月、五年條件做不了，登記時就排除），只印。
- 只印的標記（判讀母體）：

| 只印的標記 | 成立組 | 不成立組 | 崩的 Δ | 籃子的 Δ |
|---|---|---|---|---|
| 發股 G ≥ 10% | 78 筆（崩 65.4%、超額 −12.3%） | 988 筆（61.4%、−2.2%） | +3.1 | +10.1 |
| 波動（全市場百分位，上三分之一） | 342 筆（79.2%、−5.8%） | 682 筆（52.2%、−1.3%） | +27.5 | +4.1 |
| 波動相對前 12 個月（上三分之一） | 324 筆（71.6%、−6.1%） | 646 筆（56.2%、−0.9%） | +15.4 | +5.6 |
| 年資不滿 36 個月 | 60 筆（66.7%、−7.7%） | 205 筆（68.3%、−1.8%） | −6.8 | −1.2 |
| 近三個月營收年增（上三分之一） | 293 筆（64.5%、−0.2%） | 586 筆（57.8%、−2.2%） | +6.0 | −5.6 |

- 交叉表（判讀母體，成立＝1）：I×A（0,0）624、（0,1）315、（1,0）76、（1,1）39；I×S（0,0）634、（0,1）313、（1,0）74、（1,1）45；A×S（0,0）607、（1,1）249、（1,0）107、（0,1）103。其餘是有一邊不可算的。

## 計數與自查

- 階段二開頭先驗階段一兩個 CSV 的 sha256，相符才往下。
- 腳本另有一條斷言：用登記的預設參數重新偵測，事件集合與階段一的事件表完全相同（過）。
- 假結果自查六次（登記「H17 假結果自查」那一筆）：沒植入時沒有誤判成支持；植入的差判得出來，I 的崩植入 20 個百分點那一次判成不確定——跟先寫下的判讀力一致。
- 真的結果跑了一次（`stage2.py` sha256 前 16 碼 `574924f158b0c7e3`）。輸出逐字附在檔尾。
- 獨立審查者的覆核：`GO_WITH_NOTES`，六格與基準率都逐位重現、沒有任何一格翻面（見下一節「獨立覆核」）。

## 規格的套用與偏離（照實寫）

1. 上市的除權息表分不出無償配股與現金增資，另抓 130 筆逐筆明細（全數取得）。登記第 4 條已預告。
2. 減資原因欄有登記沒列出的第三種「現金減資」（全表 89 列），照登記「不是這兩種的不還原」處理。
3. 登記要印的「單檔最大貢獻占總超額的比例」在總超額為負時沒有意義，改成上面那一句（正的合計裡最大幾筆占多少）。
4. 「對照脈絡」那一節與加速 × 漲幅大小的四格，是看過結果之後才加的描述，不進判讀。
5. 登記第 8 條「崩的那些從 t 到窗內最高月收盤」：算的是「回落到四成那個月之前的最高月收盤」，不是整個 24 個月窗的最高。
6. 沒有其他偏離。六格判讀的門檻、樣本、檢定都照登記。

## 偏差標註

登記第 10 條的七項全部適用（個股、等權、月底收盤；單一市場、八年、事件成群；發股的股數來自持股統計表；上櫃 2013 年前的減資；營收拿不到下市公司；分析的人知道這段行情；底價與資料旗標的值沒量過別的）。另外三項是結果出來之後才看得到的：

- **崩的定義與波動綁在一起**（上面第 2 點）。A、S 的「支持」說的是「這一種股票之後比較常回落四成」，沒有說「這一種股票之後比較不值得」——籃子三格都是不確定。
- **月底收盤看不到月中的回落**，也看不到月中曾經達到的兩倍。兩個比例都偏低，偏多少沒有量。
- **事件之間不獨立**：同一個月、同一個題材的股票一起漲一起跌。季內排列與以事件月為單位的 bootstrap 處理了一部分；1,078 筆不等於 1,078 個獨立的觀察。

## 檔案

- 判讀線、階段一 digest、假結果自查、結果：[`registration.md`](registration.md) 2026-11-23 的四筆。
- [`h17-stage1-events.csv`](h17-stage1-events.csv)、[`h17-stage1-markers.csv`](h17-stage1-markers.csv)（階段一；只含 t 當時已知的欄）。
- [`h17-stage2-outcomes.csv`](h17-stage2-outcomes.csv)（逐事件結果；sha256 前 16 碼 `eab510701b69f144`）。
- 原始資料（交易所月底行情、除權息、減資、面額變更、發行股數、yfinance 月線）與腳本在本機 `library/private/measurement/h17_cache/`，不進 repo；腳本逐字附在下面。

## 獨立覆核（2026-11-23；使用者選「開」）

- **誰**：乾淨 context 的唯讀審查者（第一位在開工時撞到模型額度中斷、沒有核到任何東西，改用另一個模型重開一位）。不對外連線、不改任何檔、不改判讀。
- **Verdict：`GO_WITH_NOTES`**——六格判讀沒有一格會翻面，基準率沒有一個差到 3 個百分點。
- **它怎麼核**：自己照登記的文字重寫一份（只透過 `h17lib` 讀原始資料，偵測、標記、結果、排列檢定、bootstrap、判讀都重寫），
  事件 1,446、判讀母體 1,078、兩個切點、各組筆數與 W、基準率、六格的 Δ、前後兩段、拿掉 2021 年、同向量、存活者界限**逐位相同**；p 與區間的差只來自亂數流
  （離線最近的是籃子 S 的區間上界：它算 11.9、這裡 12.4，離削弱的線 10 約 2 個百分點）。
  另外：從原始檔用欄名重新解析出的 27,550 個還原因子與 `load_factors` 完全相同；手算 20 檔還原與 14 筆結果都相符；沒有找到偷看未來的地方；
  I 成立的 119 筆裡 117 筆是股數單月跳 5% 以上、附近的除權列全是有償現金增資；報告約 200 個數字與輸出一致。
- **發現**（都是低嚴重度；照一次判讀的規則，不重跑、不改判讀，只把讀法寫清楚）：
  1. **五年條件的起點有兩種讀法。** 實作是「t−60 那個月底沒有收盤就改用整個面板最早有收盤的月」；另一種讀法「t−60 之後最早有收盤的月」比較貼近「掛牌不滿五年」的本意。
     照另一種讀法事件集合差 12 筆（多 7、少 5），A、S 崩的區間下界都在 14 以上，不會翻。
  2. **yfinance 交叉核比登記假設的弱：它不還原台股的減資與面額變更。** 減資月份有 16% 兩邊差超過一成；13 筆「對不上」被剔除的事件裡至少 7 筆是 yfinance 錯、官方對。
     所以登記偏差④「靠交叉核與資料旗標擋」對 2011-12～2012-12 起點的情形不成立；審查者直接核了那 75 筆，只有 3219 一筆像是漏掉減資（R60 從 11.1 修正後約 5.0，仍過五年條件）。
     之後的回測把 yfinance 當成「對減資無效的弱核對」。
  3. **I 成立的 4503 金雨（t＝2017-04）分不出真假**：G＝32.5% 全來自還原一筆彌補虧損減資，但股數表前後沒變——可能是減資同時私募同樣的股數，也可能是股數表沒有反映減資。119 筆中的 1 筆，不會翻。
  4. **措辭**：「一年的平均超額沒有差」「帶得動的比較像是加速」「先看的是那一年的環境」三句超出數字能支持的範圍——已在提交覆核的同一個 commit 改寫（上面正文）。
  5. （資訊）切點用整個判讀母體的分布算，2017 年事件的分類取決於之後事件的 A、S 值——登記就是這樣寫的，沒有洩漏結果，但不是當時就算得出來的門檻。
  6. （資訊）兩筆下市前最後一個月的價格分不出是真跌還是下市相關的價格；兩筆都在存活者界限裡，界限判讀沒有翻面。
- **它沒有核到的**：原始檔是否忠於交易所網站（沒有對外連線）；月底日期是否是最後一個交易日；只印的 V、Y、Q；抓資料的腳本本身；假結果種子 2–6；論文的數字；4503。

## 腳本（逐字）

### h17lib.py（共用：月底、行情、還原因子、全市場等權、發行股數；sha256 前 16 碼 `3df0e876cf950fc4`）

```python
"""H17 共用：月底清單、交易所行情、還原因子（除權息＋減資＋面額變更）、還原月收盤、全市場等權、發行股數。
資料來源＝h16_cache/official（唯讀沿用）＋ h17_cache/official。這一支不判任何東西。"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
H16 = HERE.parent / "h16_cache"
DIRS = (H16 / "official", HERE / "official")
CODE = re.compile(r"^(?!00)\d{4}$")


def mnum(ym):
    y, m = map(int, ym.split("-"))
    return y * 12 + m - 1


def ym_of(n):
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def month_ends():
    ends = (json.loads((H16 / "month_ends.json").read_text(encoding="utf-8"))
            + json.loads((H16 / "month_ends2.json").read_text(encoding="utf-8"))
            + json.loads((HERE / "month_ends3.json").read_text(encoding="utf-8")))
    yms = [d[:7] for d in ends]
    assert len(set(yms)) == len(yms) == 179 and all(mnum(b) - mnum(a) == 1 for a, b in zip(yms, yms[1:]))
    return {d[:7]: d for d in ends}


def _num(s):
    s = re.sub(r"<[^>]+>", "", str(s)).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def roc_date(s):
    s = str(s).strip()
    m = re.match(r"(\d+)年(\d+)月(\d+)日", s) or re.match(r"(\d+)/(\d+)/(\d+)", s)
    if m:
        y, mo, d = map(int, m.groups())
    elif re.fullmatch(r"\d{7}", s):
        y, mo, d = int(s[:3]), int(s[3:5]), int(s[5:])
    else:
        return None
    return "%04d-%02d-%02d" % (y + 1911, mo, d)


def _find(market, ymd):
    for d in DIRS:
        f = d / f"{market}_{ymd}.json"
        if f.exists():
            return f
    raise FileNotFoundError(f"{market}_{ymd}")


def load_quotes(ME, upto=None):
    """回 (raw, name, market)：raw[代號][ym]＝未還原收盤（> 0 才收）；name[代號]＝最後一次看到的簡稱；
    market[代號][ym]＝twse／tpex。upto＝只讀到這個 ym（含）。"""
    raw, name, market = {}, {}, {}
    for ym in sorted(ME):
        if upto and ym > upto:
            break
        ymd = ME[ym].replace("-", "")
        for mk in ("twse", "tpex"):
            o = json.loads(_find(mk, ymd).read_text(encoding="utf-8"))
            for t in o.get("tables") or []:
                f = t.get("fields") or []
                ci = next((i for i, x in enumerate(f) if x in ("證券代號", "代號")), None)
                ni = next((i for i, x in enumerate(f) if x in ("證券名稱", "名稱")), None)
                pi = next((i for i, x in enumerate(f) if x in ("收盤價", "收盤")), None)
                if ci is None or pi is None:
                    continue
                for r in t.get("data") or []:
                    code = str(r[ci]).strip()
                    if not CODE.match(code):
                        continue
                    if ni is not None:
                        name[code] = str(r[ni]).strip()
                    close = _num(r[pi])
                    if close and close > 0:
                        raw.setdefault(code, {})[ym] = close
                        market.setdefault(code, {})[ym] = mk
    return raw, name, market


def _rows(f):
    o = json.loads(f.read_text(encoding="utf-8"))
    t0 = (o.get("tables") or [{}])[0]
    return (o.get("fields") or t0.get("fields") or []), (o.get("data") or t0.get("data") or [])


def load_factors():
    """回 (fac, stat)：fac[代號]＝[(日期, 因子, 種類, 附註)]，種類 ∈ 除權息／減資／面額變更。
    因子＝參考價 ÷ 前收。附註：除權息＝{'market','type','stock_per_1000'（上櫃才有）}；減資＝{'reason'}。
    只擋缺值與 ≤ 0；同一代號同一天同一種類的重複列只算一次。"""
    fac, seen = {}, set()
    stat = {"除權息": 0, "減資": 0, "面額變更": 0, "重複列": 0, "擋掉（缺值或 ≤ 0）": 0}
    for d in DIRS:
        for kind, pat in (("除權息", "*_exright_*.json"), ("減資", "*_reduction_*.json"), ("面額變更", "*_parvalue_*.json")):
            for f in sorted(d.glob(pat)):
                mk = f.name.split("_")[0]
                fields, data = _rows(f)
                for r in data:
                    date, code, prev, ref = roc_date(r[0]), str(r[1]).strip(), _num(r[3]), _num(r[4])
                    if not date or not prev or not ref or prev <= 0 or ref <= 0:
                        stat["擋掉（缺值或 ≤ 0）"] += 1
                        continue
                    if (code, date, kind) in seen:
                        stat["重複列"] += 1
                        continue
                    seen.add((code, date, kind))
                    note = {"market": mk}
                    if kind == "除權息":
                        ti = fields.index("權/息") if "權/息" in fields else None
                        note["type"] = str(r[ti]).strip() if ti is not None else ""
                        if "每仟股無償配股" in fields:
                            note["stock_per_1000"] = _num(r[fields.index("每仟股無償配股")])
                    elif kind == "減資":
                        note["reason"] = str(r[fields.index("減資原因")]).strip() if "減資原因" in fields else ""
                    fac.setdefault(code, []).append((date, ref / prev, kind, note))
                    stat[kind] += 1
    for v in fac.values():
        v.sort(key=lambda x: x[0])
    return fac, stat


def adjusted(series, ME, factors):
    """series＝{ym: 未還原收盤}。回 {ym: 還原收盤}（乘上日期晚於該月底的所有因子）。"""
    out = {}
    for ym, close in series.items():
        d, k = ME[ym], 1.0
        for date, f, _kind, _note in factors:
            if date > d:
                k *= f
        out[ym] = close * k
    return out


def market_returns(raw, fac, ME, drop_dr_names=None):
    """全市場等權月報酬 {ym: r}（還原後相鄰兩個月底收盤的比值，不在 0.33–3 之間的剔除）。回 (mkt, 用到的筆數, 剔除的筆數)。"""
    yms = sorted(ME)
    mkt, n_used, n_drop = {}, 0, 0
    for a, b in zip(yms, yms[1:]):
        rs = []
        for code, s in raw.items():
            if drop_dr_names and code in drop_dr_names:
                continue
            if a in s and b in s:
                k = 1.0
                for date, f, _kind, _note in fac.get(code, ()):
                    if ME[a] < date <= ME[b]:
                        k *= f
                r = s[b] / s[a] / k
                if 0.33 <= r <= 3:
                    rs.append(r - 1)
                else:
                    n_drop += 1
        if rs:
            mkt[b] = sum(rs) / len(rs)
            n_used += len(rs)
    return mkt, n_used, n_drop


def mkt_cum(mkt, a_ym, b_ym):
    """全市場等權自 a 月底到 b 月底的累積報酬；任一個月不在資料裡回 None。"""
    out = 1.0
    for n in range(mnum(a_ym) + 1, mnum(b_ym) + 1):
        r = mkt.get(ym_of(n))
        if r is None:
            return None
        out *= 1 + r
    return out - 1


def load_shares(ME, upto=None):
    """回 shares[代號][ym]＝發行股數。"""
    out = {}
    for ym in sorted(ME):
        if upto and ym > upto:
            break
        ymd = ME[ym].replace("-", "")
        for mk, ckey, skey in (("twse", "證券代號", "發行股數"), ("tpex", "代號", "發行股數(A)")):
            fields, data = _rows(HERE / "official" / f"{mk}_shares_{ymd}.json")
            ci, si = fields.index(ckey), fields.index(skey)
            for r in data:
                code = str(r[ci]).strip()
                v = _num(r[si])
                if CODE.match(code) and v and v > 0:
                    out.setdefault(code, {})[ym] = v
    return out


def is_dr(name):
    return str(name).strip().upper().endswith("DR")


def sha256_lf(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
```

### stage1.py（階段一：事件表、標記表與 digest；sha256 前 16 碼 `438798f374d3c7ef`）

```python
"""H17 階段一：事件表與標記表。**只讀 ≤ t 的資料**（行情、股數、yfinance 交叉核都截在各事件的 t；腳本結尾有斷言）。
判讀線＝docs/reports/phase7/registration.md 的「新假說 H17」那一筆（commit 86e9fe86）；這裡逐條照做，不判任何結果。
用法：python stage1.py            → 偵測事件、列出要抓的上市除權息明細（缺就停，不寫輸出）
      python stage1.py --write    → 明細齊了之後寫事件表、標記表與 digest
"""
import collections
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

import numpy as np

import h17lib as L

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
REPO = HERE.parents[3]
OUT = REPO / "docs" / "reports" / "phase7"
T_FROM, T_TO = "2016-12", "2024-10"          # 判讀母體的 t
SCAN_FROM = "2013-12"                         # 偵測從面板能算的第一個月起連續跑
FLOOR = 5.0

ME = L.month_ends()
YMS = sorted(ME)
IDX = {ym: i for i, ym in enumerate(YMS)}
raw, name, market = L.load_quotes(ME, upto=T_TO)           # 只讀到最後一個可能的 t
assert max(ym for s in raw.values() for ym in s) <= T_TO
fac, fstat = L.load_factors()
dr = {c for c in raw if L.is_dr(name.get(c, ""))}
mkt, _used, _dropped = L.market_returns(raw, fac, {ym: ME[ym] for ym in YMS if ym <= T_TO}, drop_dr_names=dr)
adj = {c: L.adjusted(s, ME, [x for x in fac.get(c, ()) if x[0] <= ME[T_TO]]) for c, s in raw.items() if c not in dr}
# 還原只用到比值，所以「日期晚於 T_TO 月底的因子」拿掉不影響任何 ≤ T_TO 的比值；拿掉是為了不讀 t 之後的公司行動。


def ratio_ok(series, a_ym, b_ym):
    """a..b 之間相鄰兩個有收盤的月底，還原比值都在 0.2–5 之內。"""
    yms = [ym for ym in sorted(series) if a_ym <= ym <= b_ym]
    return all(0.2 <= series[y2] / series[y1] <= 5 for y1, y2 in zip(yms, yms[1:]))


# ---------- 事件偵測 ----------
events = []
for code in sorted(adj):
    s, r = adj[code], raw[code]
    first = min(s)
    locked_until = -1
    for i in range(IDX[SCAN_FROM], IDX[T_TO] + 1):
        if i <= locked_until:
            continue
        t, t24 = YMS[i], YMS[i - 24]
        if t not in s or t24 not in s:
            continue
        r24 = s[t] / s[t24] - 1
        if r24 < 1.0:
            continue
        m24 = L.mkt_cum(mkt, t24, t)
        if m24 is None or r24 - m24 < 1.0:
            continue
        if r[t24] < FLOOR:
            continue
        t60 = YMS[i - 60] if i >= 60 else None
        if t60 and t60 in s:
            base, five = t60, "t-60"
        elif L.mnum(first) <= L.mnum(t) - 36:
            base, five = first, "最早有收盤的月"
        else:
            base, five = None, "免除（掛牌或面板不滿三年）"
        r60 = s[t] / s[base] - 1 if base else None
        if base and r60 < 0.5:
            continue
        locked_until = i + 24
        events.append({"code": code, "t": t, "t24": t24, "r24": r24, "m24": m24, "net": r24 - m24, "five": five,
                       "base": base, "r60": r60, "floor_px": r[t24], "first": first})
print("事件（全部，t", SCAN_FROM, "→", T_TO, "）", len(events), "｜各年", dict(sorted(collections.Counter(e["t"][:4] for e in events).items())))

# ---------- 資料旗標 ----------
px = json.loads((HERE / "px_all.json").read_text(encoding="utf-8"))
for e in events:
    s = adj[e["code"]]
    e["flag_unadj"] = not ratio_ok(s, e["base"] or e["t24"], e["t"])
    yf_rows = None
    for sfx in (".TW", ".TWO"):
        if e["code"] + sfx in px:
            yf_rows = {ym: v for ym, v in px[e["code"] + sfx] if ym <= e["t"]}        # 只取 ≤ t
            break
    if yf_rows is None or e["t"] not in yf_rows or e["t24"] not in yf_rows or yf_rows[e["t24"]] <= 0:
        e["xcheck"] = "交叉核做不了"
    else:
        a, b = 1 + e["r24"], yf_rows[e["t"]] / yf_rows[e["t24"]]
        e["yf_r24"] = b - 1
        e["xcheck"] = "對不上" if max(a / b, b / a) > 1.15 else "相符"
    e["in_window"] = T_FROM <= e["t"] <= T_TO
    e["in_pop"] = e["in_window"] and not e["flag_unadj"] and e["xcheck"] != "對不上"
win = [e for e in events if e["in_window"]]
pop = [e for e in events if e["in_pop"]]
print("t 在", T_FROM, "→", T_TO, "的事件", len(win), "｜疑似未還原（事件側）", sum(e["flag_unadj"] for e in win),
      "｜對不上", sum(e["xcheck"] == "對不上" for e in win), "｜交叉核做不了", sum(e["xcheck"] == "交叉核做不了" for e in win),
      "｜**判讀母體**", len(pop), "（", len({e["code"] for e in pop}), "檔）")
print("  判讀母體各年", dict(sorted(collections.Counter(e["t"][:4] for e in pop).items())),
      "｜五年條件", dict(collections.Counter(e["five"] for e in pop)))
print("  t 在", SCAN_FROM, "→ 2016-11 的事件（只印）", sum(e["t"] < T_FROM for e in events))

# ---------- 標記 I：發股 ----------
shares = L.load_shares(ME, upto=T_TO)
DETAIL = HERE / "detail"
DETAIL.mkdir(exist_ok=True)


def day_minus(d, n):
    return (dt.date.fromisoformat(d) - dt.timedelta(days=n)).isoformat()


def stock_per_1000_twse(code, date):
    f = DETAIL / f"{code}_{date.replace('-', '')}.json"
    if not f.exists():
        return None
    o = json.loads(f.read_text(encoding="utf-8"))
    fields, data = o.get("fields") or [], o.get("data") or []
    ai = next((i for i, x in enumerate(fields) if "無償配股" in x), None)
    if ai is None or not data:
        return None
    m = re.search(r"[-\d.,]+", str(data[0][ai]))
    return float(m.group(0).replace(",", "")) if m else None


need_detail = set()
for e in events:
    code, t = e["code"], e["t"]
    t12 = YMS[IDX[t] - 12]
    e["t12"] = t12
    lo_d, hi_d = ME[t12], ME[t]
    sh_t, sh_b = shares.get(code, {}).get(t), shares.get(code, {}).get(t12)
    e["G"], e["I_why"] = None, None
    if not sh_t or not sh_b:
        e["I_why"] = "沒有發行股數（t 或 t−12）"
        continue
    base_k, lo_k, hi_k, missing, other_reason = 1.0, 1.0, 1.0, False, 0
    for date, f, kind, note in fac.get(code, ()):
        if not (day_minus(lo_d, 90) < date <= hi_d):
            continue
        if kind == "除權息":
            if note["market"] == "tpex":
                x = note.get("stock_per_1000") or 0.0
            else:
                if note.get("type") not in ("權", "權息"):
                    continue
                x = stock_per_1000_twse(code, date)
                if x is None:
                    need_detail.add((code, date))
                    missing = True
                    continue
            if x <= 0:
                continue
            k = 1.0 / (1.0 + x / 1000.0)
        elif kind == "減資":
            if "彌補虧損" not in note.get("reason", ""):
                other_reason += note.get("reason") not in ("退還股款",)
                continue
            k = f
        else:                                   # 面額變更
            k = f
        pre_start = date <= lo_d                # 在 t−12 月底之前 90 天內：預設不還原，另一種算法是還原
        near_end = date > day_minus(hi_d, 90)   # 在 t 月底之前 90 天內：預設還原，另一種算法是不還原
        if pre_start:
            lo_k, hi_k = lo_k * min(1.0, k), hi_k * max(1.0, k)
        elif near_end:
            base_k *= k
            lo_k, hi_k = lo_k * min(1.0, k) , hi_k * max(1.0, k)
        else:
            base_k, lo_k, hi_k = base_k * k, lo_k * k, hi_k * k
    e["I_other_reduction"] = other_reason
    if missing:
        e["I_why"] = "上市除權明細還沒取到"
        continue
    g, g_lo, g_hi = sh_t * base_k / sh_b - 1, sh_t * lo_k / sh_b - 1, sh_t * hi_k / sh_b - 1
    e["G"], e["G_lo"], e["G_hi"] = g, g_lo, g_hi
    if (g_lo >= 0.05) != (g_hi >= 0.05):
        e["I_why"] = "跨界（還原與不還原對 5% 的判定不同）"
print("發股標記：要取的上市除權明細", len(need_detail), "筆")
if need_detail:
    (HERE / "need_detail.json").write_text(json.dumps(sorted(need_detail)), encoding="utf-8")
    print("  已寫 need_detail.json；跑 fetch_detail.py 之後再跑一次")
    if "--write" in sys.argv:
        sys.exit("明細不齊，不寫輸出")

# ---------- 標記 A、S 與只印的三個 ----------
allr = {}                                       # 只印的波動：每個月全市場的 12 個月標準差
rev = {}
for f in sorted((L.H16 / "rev").glob("rev_*.json")):
    for row in json.loads(f.read_text(encoding="utf-8")):
        c, m = row.get("company_code"), row.get("data_month")
        if c and m and row.get("revenue_current") is not None and row.get("revenue_year_ago"):
            rev.setdefault(c, {})[m] = (row["revenue_current"], row["revenue_year_ago"])


def vol12(series, end_i):
    rs = []
    for j in range(end_i - 11, end_i + 1):
        a, b = YMS[j - 1], YMS[j]
        if a not in series or b not in series:
            return None
        rs.append(series[b] / series[a] - 1)
    return float(np.std(rs, ddof=1))


vol_cache = {}


def vol_rank(code, end_i):
    if end_i not in vol_cache:
        vals = {c: vol12(s, end_i) for c, s in adj.items()}
        vol_cache[end_i] = {c: v for c, v in vals.items() if v is not None}
    d = vol_cache[end_i]
    if code not in d:
        return None, None
    v = d[code]
    return v, sum(1 for x in d.values() if x < v) / len(d)


for e in events:
    s, i = adj[e["code"]], IDX[e["t"]]
    e["A"] = (1 + e["r24"]) - s[e["t12"]] / s[e["t24"]] if e["t12"] in s else None
    e["S"] = e["net"]
    v, rank = vol_rank(e["code"], i)
    v_prev = vol12(s, i - 12)
    e["V"], e["V_rank"], e["V_chg"] = v, rank, (v / v_prev - 1 if v and v_prev else None)
    e["Y"] = None if e["first"] == YMS[0] else int(L.mnum(e["t"]) - L.mnum(e["first"]) < 36)
    months = [L.ym_of(L.mnum(e["t"]) - k) for k in (1, 2, 3)]
    rr = rev.get(e["code"], {})
    if all(m in rr for m in months) and sum(rr[m][1] for m in months) > 0:
        e["Q"] = sum(rr[m][0] for m in months) / sum(rr[m][1] for m in months) - 1
    else:
        e["Q"] = None

a_vals = [e["A"] for e in pop if e["A"] is not None]
s_vals = [e["S"] for e in pop]
A_CUT, S_CUT = float(np.quantile(a_vals, 2 / 3)), float(np.quantile(s_vals, 2 / 3))
for e in events:
    e["I"] = None if (e["G"] is None or e["I_why"]) else int(e["G"] >= 0.05)
    e["I10"] = None if (e["G"] is None or e["I_why"]) else int(e["G"] >= 0.10)
    e["A_hit"] = None if e["A"] is None else int(e["A"] >= A_CUT)
    e["S_hit"] = int(e["S"] >= S_CUT)
    e["quarter"] = "%sQ%d" % (e["t"][:4], (int(e["t"][5:7]) - 1) // 3 + 1)
print("切點（判讀母體、看任何結果之前）：A ≥ %.4f｜S ≥ %.4f" % (A_CUT, S_CUT))


def groups(key):
    on = [e for e in pop if e[key] == 1]
    off = [e for e in pop if e[key] == 0]
    na = [e for e in pop if e[key] is None]
    byq = collections.defaultdict(lambda: [0, 0])
    for e in on:
        byq[e["quarter"]][0] += 1
    for e in off:
        byq[e["quarter"]][1] += 1
    w = sum(a * b / (a + b) for a, b in byq.values() if a + b)
    return len(on), len(off), len(na), w


for key, label in (("I", "I 發股（G ≥ 5%）"), ("A_hit", "A 加速（上三分之一）"), ("S_hit", "S 漲幅大小（上三分之一）"), ("I10", "〔只印〕發股 G ≥ 10%"), ("Y", "〔只印〕年資不滿 36 個月")):
    on, off, na, w = groups(key)
    print("  %s：成立 %d／不成立 %d／不可算 %d｜季內資訊量 W %.1f" % (label, on, off, na, w))
print("  I 不可算的原因", dict(collections.Counter(e["I_why"] for e in pop if e["I_why"])),
      "｜減資原因不是兩種之一而沒還原的事件", sum(1 for e in pop if e.get("I_other_reduction")))
print("  G 的分布（判讀母體可算）：", [round(float(x), 3) for x in np.quantile([e["G"] for e in pop if e["I"] is not None], [0, .1, .25, .5, .75, .9, .99, 1])])
print("  〔只印〕波動可算", sum(e["V"] is not None for e in pop), "｜營收年增可算", sum(e["Q"] is not None for e in pop))
print("  三個判的標記兩兩同時成立：I∩A", sum(1 for e in pop if e["I"] == 1 and e["A_hit"] == 1), "I∩S", sum(1 for e in pop if e["I"] == 1 and e["S_hit"] == 1),
      "A∩S", sum(1 for e in pop if e["A_hit"] == 1 and e["S_hit"] == 1))

if "--write" not in sys.argv:
    sys.exit(0)

# ---------- 輸出（只含 t 當時已知的欄） ----------
name_at = {}
_raw2, _n2, _m2 = None, None, None
for e in events:
    name_at[(e["code"], e["t"])] = None
by_t = collections.defaultdict(list)
for e in events:
    by_t[e["t"]].append(e["code"])
for t, codes in by_t.items():
    ymd = ME[t].replace("-", "")
    for mk in ("twse", "tpex"):
        o = json.loads(L._find(mk, ymd).read_text(encoding="utf-8"))
        for tb in o.get("tables") or []:
            f = tb.get("fields") or []
            ci = next((i for i, x in enumerate(f) if x in ("證券代號", "代號")), None)
            ni = next((i for i, x in enumerate(f) if x in ("證券名稱", "名稱")), None)
            if ci is None or ni is None:
                continue
            for r in tb.get("data") or []:
                c = str(r[ci]).strip()
                if (c, t) in name_at:
                    name_at[(c, t)] = str(r[ni]).strip()


def fmt(x, n=4):
    return "" if x is None else (("%." + str(n) + "f") % x)


ev_cols = ["代號", "名稱（t 當月）", "t", "事件季", "兩年報酬", "同期全市場等權", "淨漲幅", "五年條件", "五年條件的起點月", "起點到 t 的報酬",
           "t−24 未還原收盤", "疑似未還原（事件側）", "交叉核", "進判讀母體"]
mk_cols = ["代號", "t", "I 發股（1 成立）", "G 還原後股數增幅", "G 下界", "G 上界", "I 不可算的原因", "〔只印〕G ≥ 10%", "A 加速（1 成立）", "A 值",
           "S 漲幅大小（1 成立）", "S 值", "〔只印〕波動", "〔只印〕波動的全市場百分位", "〔只印〕波動相對前 12 個月", "〔只印〕年資不滿 36 個月", "〔只印〕近三個月營收年增"]
FORBIDDEN = ("下市", "終止", "結果", "崩", "之後")
assert not any(w in c for c in ev_cols + mk_cols for w in FORBIDDEN)
events.sort(key=lambda e: (e["t"], e["code"]))
with open(OUT / "h17-stage1-events.csv", "w", encoding="utf-8", newline="\n") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(ev_cols)
    for e in events:
        w.writerow([e["code"], name_at[(e["code"], e["t"])] or "", e["t"], e["quarter"], fmt(e["r24"]), fmt(e["m24"]), fmt(e["net"]), e["five"], e["base"] or "",
                    fmt(e["r60"]), fmt(e["floor_px"], 2), int(e["flag_unadj"]), e["xcheck"], int(e["in_pop"])])
with open(OUT / "h17-stage1-markers.csv", "w", encoding="utf-8", newline="\n") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(mk_cols)
    for e in events:
        w.writerow([e["code"], e["t"], "" if e["I"] is None else e["I"], fmt(e["G"]), fmt(e.get("G_lo")), fmt(e.get("G_hi")), e["I_why"] or "",
                    "" if e["I10"] is None else e["I10"], "" if e["A_hit"] is None else e["A_hit"], fmt(e["A"]), e["S_hit"], fmt(e["S"]),
                    fmt(e["V"]), fmt(e["V_rank"]), fmt(e["V_chg"]), "" if e["Y"] is None else e["Y"], fmt(e["Q"])])
digest = {"events": L.sha256_lf(OUT / "h17-stage1-events.csv"), "markers": L.sha256_lf(OUT / "h17-stage1-markers.csv"),
          "A_CUT": A_CUT, "S_CUT": S_CUT, "n_events": len(events), "n_pop": len(pop),
          "script": __import__("hashlib").sha256(Path(__file__).read_bytes()).hexdigest()[:16],
          "lib": __import__("hashlib").sha256((HERE / "h17lib.py").read_bytes()).hexdigest()[:16]}
(HERE / "stage1_digest.json").write_text(json.dumps(digest, ensure_ascii=False, indent=1), encoding="utf-8")
(HERE / "stage1_private.json").write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")
print("已寫", OUT / "h17-stage1-events.csv", OUT / "h17-stage1-markers.csv")
print("digest", json.dumps(digest, ensure_ascii=False))
assert max(e["t"] for e in events) <= T_TO
```

### stage2.py（階段二：結果與判讀；`--synthetic` 是假結果自查；sha256 前 16 碼 `574924f158b0c7e3`）

```python
"""H17 階段二：結果與判讀（一次）。判讀線＝registration.md「新假說 H17」（commit 86e9fe86）；階段一的事件表、標記表先驗 digest。
用法：python stage2.py                         → 真的結果（只跑一次；寫逐事件結果檔與摘要）
      python stage2.py --synthetic 種子 [--plant 標記 家族 效果]
                                               → 假結果自查：真的結果在任何彙總印出之前就被蓋掉，不寫輸出檔
        標記 ∈ I／A_hit／S_hit；家族 ∈ crash／basket；效果＝植入的差（0.2＝20 個百分點）
"""
import collections
import csv
import json
import sys
from pathlib import Path

import numpy as np

import h17lib as L

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
REPO = HERE.parents[3]
OUT = REPO / "docs" / "reports" / "phase7"
SEED, N_PERM, N_BOOT, ALPHA = 20261123, 10000, 2000, 0.05 / 6
T_FROM, T_TO, SCAN_FROM, FLOOR = "2016-12", "2024-10", "2013-12", 5.0
SYN = "--synthetic" in sys.argv
syn_seed = int(sys.argv[sys.argv.index("--synthetic") + 1]) if SYN else None
PLANT = sys.argv[sys.argv.index("--plant") + 1:sys.argv.index("--plant") + 4] if "--plant" in sys.argv else None

# ---------- 驗階段一 ----------
dg = json.loads((HERE / "stage1_digest.json").read_text(encoding="utf-8"))
assert L.sha256_lf(OUT / "h17-stage1-events.csv") == dg["events"], "事件表 digest 不符"
assert L.sha256_lf(OUT / "h17-stage1-markers.csv") == dg["markers"], "標記表 digest 不符"
events = json.loads((HERE / "stage1_private.json").read_text(encoding="utf-8"))
print("階段一 digest 相符｜事件", len(events), "｜階段一的判讀母體", sum(e["in_pop"] for e in events))

# ---------- 全段資料 ----------
ME = L.month_ends()
YMS = sorted(ME)
IDX = {ym: i for i, ym in enumerate(YMS)}
raw, name, market = L.load_quotes(ME)
fac, _fstat = L.load_factors()
dr = {c for c in raw if L.is_dr(name.get(c, ""))}
mkt, _u, _d = L.market_returns(raw, fac, ME, drop_dr_names=dr)
adj = {c: L.adjusted(s, ME, fac.get(c, ())) for c, s in raw.items() if c not in dr}
px = json.loads((HERE / "px_all.json").read_text(encoding="utf-8"))
LAST = YMS[-1]


def path_outcomes(s, t):
    """s＝{ym: 價}（同一條序列）；回以 t 為起點的結果。窗＝t 之後第 1 到第 24 個月。"""
    i = IDX[t]
    p0 = s[t]
    win = [(k, s[YMS[i + k]]) for k in range(1, 25) if i + k < len(YMS) and YMS[i + k] in s]
    out = {"n_months": len(win)}
    runmax, peak_k = p0, 0
    crash = crash50 = 0
    crash_k = peak_at_crash = peak_k_at_crash = None
    for k, p in win:
        if p > runmax:
            runmax, peak_k = p, k
        if not crash and p <= 0.6 * runmax:
            crash, crash_k, peak_at_crash, peak_k_at_crash = 1, k, runmax / p0 - 1, peak_k
        if p <= 0.5 * runmax:
            crash50 = 1
    out.update(crash=crash, crash50=crash50, crash_k=crash_k, gain_to_peak=peak_at_crash, months_to_peak=peak_k_at_crash)
    for h in (12, 24):
        sub = [(k, p) for k, p in win if k <= h]
        out[f"ever2x_{h}"] = int(any(p >= 2 * p0 for _k, p in sub))
        exit_p = sub[-1][1] if sub else p0
        out[f"ret_{h}"] = exit_p / p0 - 1
        out[f"exit_k_{h}"] = sub[-1][0] if sub else 0
    out["dd30_6"] = int(any(p <= 0.7 * p0 for k, p in win if k <= 6))
    seq = [p0] + [p for _k, p in win]
    out["flag_unadj_out"] = int(any(not (0.2 <= b / a <= 5) for a, b in zip(seq, seq[1:])))
    return out


for e in events:
    s, t, i = adj[e["code"]], e["t"], IDX[e["t"]]
    o = path_outcomes(s, t)
    e.update(o)
    last_close = max(s)
    e["delisted_in_win"] = int(last_close < YMS[min(i + 24, len(YMS) - 1)] and last_close < LAST)
    e["delisted_in_12"] = int(last_close < YMS[min(i + 12, len(YMS) - 1)] and last_close < LAST)
    for h in (12, 24):
        m = L.mkt_cum(mkt, t, YMS[i + h]) if i + h < len(YMS) else None
        e[f"mkt_{h}"] = m
        e[f"ex_{h}"] = None if m is None else e[f"ret_{h}"] - m
    # yfinance 另算一次（只有今天還有報價的公司）
    e["yf_crash"] = e["yf_ever2x_12"] = None
    for sfx in (".TW", ".TWO"):
        rows = px.get(e["code"] + sfx)
        if rows:
            ys = {ym: v for ym, v in rows if v and v > 0}
            if t in ys and any(YMS[i + k] in ys for k in range(1, 25) if i + k < len(YMS)):
                yo = path_outcomes(ys, t)
                e["yf_crash"], e["yf_ever2x_12"] = yo["crash"], yo["ever2x_12"]
            break
    e["discordant"] = int(e["yf_crash"] is not None and (e["yf_crash"] != e["crash"] or e["yf_ever2x_12"] != e["ever2x_12"]))

# ---------- 假結果（自查用）：在任何彙總印出之前蓋掉 ----------
if SYN:
    rng = np.random.default_rng(syn_seed)
    for e in events:
        pc, shift = 0.45, 0.0
        if PLANT and e.get(PLANT[0]) == 1:
            if PLANT[1] == "crash":
                pc += float(PLANT[2])
            else:
                shift = -float(PLANT[2])
        e["crash"] = int(rng.random() < pc)
        e["crash50"] = int(e["crash"] and rng.random() < 0.6)
        e["ex_12"] = float(rng.standard_t(4) * 0.5 + 0.05 + shift)
        e["ret_12"] = e["ex_12"] + (e["mkt_12"] or 0)
        e["ever2x_12"] = int(e["ret_12"] >= 1.0)
        e["ex_24"], e["ever2x_24"], e["dd30_6"] = e["ex_12"] * 1.3, e["ever2x_12"], int(rng.random() < 0.3)
        e["flag_unadj_out"] = e["delisted_in_win"] = e["delisted_in_12"] = e["discordant"] = 0
    print("【假結果】種子", syn_seed, "植入", PLANT)

pop1 = [e for e in events if e["in_pop"]]
pop = [e for e in pop1 if not e["flag_unadj_out"]]
print("判讀母體：階段一", len(pop1), "→ 剔除疑似未還原（結果側）", len(pop1) - len(pop), "→", len(pop),
      "｜結果窗內下市", sum(e["delisted_in_win"] for e in pop), "（12 個月內", sum(e["delisted_in_12"] for e in pop), "）",
      "｜兩個來源結果不同", sum(e["discordant"] for e in pop), "｜yfinance 沒得比", sum(e["yf_crash"] is None for e in pop))
TOP_YEAR = collections.Counter(e["t"][:4] for e in pop1).most_common(1)[0][0]


# ---------- 統計 ----------
def strat_delta(on_y, off_y, on_q, off_q):
    """季內加權（Mantel–Haenszel）的「成立組平均 − 不成立組平均」。回 (Δ, W)。"""
    qs = sorted(set(on_q) | set(off_q))
    num = den = 0.0
    for q in qs:
        a = [y for y, qq in zip(on_y, on_q) if qq == q]
        b = [y for y, qq in zip(off_y, off_q) if qq == q]
        if a and b:
            w = len(a) * len(b) / (len(a) + len(b))
            num += w * (np.mean(a) - np.mean(b))
            den += w
    return (num / den if den else float("nan")), den


def test(sub, key, ykey, sign):
    """sub＝事件；key＝標記欄；ykey＝結果欄；sign＝+1（Δ＝成立 − 不成立）或 −1（Δ＝不成立 − 成立）。"""
    rows = [e for e in sub if e[key] is not None and e[ykey] is not None]
    on = [e for e in rows if e[key] == 1]
    off = [e for e in rows if e[key] == 0]
    res = {"n_on": len(on), "n_off": len(off)}
    if not on or not off:
        res.update(delta=float("nan"), W=0.0, p=float("nan"), lo=float("nan"), hi=float("nan"), rate_on=float("nan"), rate_off=float("nan"))
        return res
    d, w = strat_delta([e[ykey] for e in on], [e[ykey] for e in off], [e["quarter"] for e in on], [e["quarter"] for e in off])
    res.update(delta=sign * d, W=w, rate_on=float(np.mean([e[ykey] for e in on])), rate_off=float(np.mean([e[ykey] for e in off])))
    return res, rows


def perm_and_boot(rows, key, ykey, sign, obs):
    y = np.array([e[ykey] for e in rows], dtype=float)
    g = np.array([e[key] for e in rows], dtype=int)
    q = np.array([e["quarter"] for e in rows])
    rng = np.random.default_rng(SEED)
    num = np.zeros(N_PERM)
    den = 0.0
    for qq in sorted(set(q)):
        m = q == qq
        n, k = int(m.sum()), int(g[m].sum())
        if k == 0 or k == n:
            continue
        w = k * (n - k) / n
        yq = y[m]
        idx = rng.random((N_PERM, n)).argsort(axis=1)[:, :k]
        s1 = yq[idx].sum(axis=1)
        num += w * (s1 / k - (yq.sum() - s1) / (n - k))
        den += w
    perm = sign * num / den
    p = (1 + int((perm >= obs - 1e-12).sum())) / (N_PERM + 1)
    rng = np.random.default_rng(SEED)
    months = sorted({e["t"] for e in rows})
    mi = {m: j for j, m in enumerate(months)}
    em = np.array([mi[e["t"]] for e in rows])
    qs = sorted(set(q))
    qi = np.array([qs.index(x) for x in q])
    boots = []
    for _ in range(N_BOOT):
        cnt = np.bincount(rng.integers(0, len(months), len(months)), minlength=len(months))[em].astype(float)
        n1 = np.bincount(qi, weights=cnt * g, minlength=len(qs))
        n0 = np.bincount(qi, weights=cnt * (1 - g), minlength=len(qs))
        s1 = np.bincount(qi, weights=cnt * g * y, minlength=len(qs))
        s0 = np.bincount(qi, weights=cnt * (1 - g) * y, minlength=len(qs))
        ok = (n1 > 0) & (n0 > 0)
        if not ok.any():
            continue
        w = n1[ok] * n0[ok] / (n1[ok] + n0[ok])
        boots.append(sign * float((w * (s1[ok] / n1[ok] - s0[ok] / n0[ok])).sum() / w.sum()))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return p, float(lo), float(hi)


FAM = {"crash": ("crash", +1, "crash50", +1, "崩（回落四成）"), "basket": ("ex_12", -1, "ever2x_12", -1, "籃子（12 個月平均超額）")}


def judge(sub, key, fam, full=True):
    """照第 7 條判。回 dict（含 verdict）。full＝False 時不做排列與 bootstrap（另印用）。"""
    ykey, sign, aux_key, aux_sign, _label = FAM[fam]
    r = test(sub, key, ykey, sign)
    if isinstance(r, dict):
        r["verdict"] = "不足"
        return r
    res, rows = r
    if not full:
        return res
    res["p"], res["lo"], res["hi"] = perm_and_boot(rows, key, ykey, sign, res["delta"])
    halves = []
    for cond in (lambda e: e["t"] <= "2020-12", lambda e: e["t"] >= "2021-01"):
        h = test([e for e in rows if cond(e)], key, ykey, sign)
        h = h if isinstance(h, dict) else h[0]
        halves.append((h["n_on"], h["n_off"], h["delta"]))
    dropped = test([e for e in rows if e["t"][:4] != TOP_YEAR], key, ykey, sign)
    dropped = dropped if isinstance(dropped, dict) else dropped[0]
    aux = test(rows, key, aux_key, aux_sign)
    aux = aux if isinstance(aux, dict) else aux[0]
    res.update(halves=halves, drop_top=dropped["delta"], aux=aux["delta"])
    if min(res["n_on"], res["n_off"]) < 100 or res["W"] < 50:
        v = "不足"
    elif (res["delta"] >= 0.10 and res["p"] <= ALPHA and all(a >= 30 and b >= 30 and d > 0 for a, b, d in halves)
          and dropped["delta"] >= 0.05 and (aux["delta"] > 0 if fam == "crash" else aux["delta"] >= 0)):
        v = "支持"
    elif min(res["n_on"], res["n_off"]) >= 150 and res["hi"] < 0.10:
        v = "削弱"
    else:
        v = "不確定"
    res["verdict"] = v
    return res


def with_bounds(sub, fam, mode):
    """存活者的界限：回一份改過結果的複本。"""
    out = []
    for e in sub:
        e2 = dict(e)
        if fam == "crash" and e["delisted_in_win"]:
            e2["crash"] = e2["crash50"] = 1 if mode == "upper" else 0
        if fam == "basket" and e["delisted_in_12"] and mode == "lower":
            e2["ret_12"] = -1.0
            e2["ex_12"] = None if e["mkt_12"] is None else -1.0 - e["mkt_12"]
            e2["ever2x_12"] = e["ever2x_12"]
        out.append(e2)
    return out


def show(label, r):
    if "p" not in r:
        print("  %-22s 成立 %d／不成立 %d｜%s" % (label, r["n_on"], r["n_off"], r.get("verdict", "")))
        return
    print("  %-22s 成立 %d（%.3f）／不成立 %d（%.3f）｜W %.1f｜Δ %+.3f｜p %.4f｜區間 %+.3f～%+.3f｜前後兩段 %s｜拿掉 %s 年 %+.3f｜同向量 %+.3f → **%s**"
          % (label, r["n_on"], r["rate_on"], r["n_off"], r["rate_off"], r["W"], r["delta"], r["p"], r["lo"], r["hi"],
             ["%d/%d %+.3f" % h for h in r["halves"]], TOP_YEAR, r["drop_top"], r["aux"], r["verdict"]))


MARKERS = (("I", "I 發股"), ("A_hit", "A 加速"), ("S_hit", "S 漲幅大小"))
print("\n== 判讀（判讀母體 %d；顯著線 p ≤ %.4f；事件最多的年 %s）" % (len(pop), ALPHA, TOP_YEAR))
final = {}
for fam in ("crash", "basket"):
    print(" 家族：", FAM[fam][4])
    for key, label in MARKERS:
        r = judge(pop, key, fam)
        show(label, r)
        v = r["verdict"]
        bounds = []
        for mode in (("upper", "lower") if fam == "crash" else ("lower",)):
            rb = judge(with_bounds(pop, fam, mode), key, fam)
            bounds.append((mode, rb["verdict"], rb.get("delta")))
        rd = judge([e for e in pop if not e["discordant"]], key, fam)
        note = ""
        if any(b[1] != v for b in bounds):
            note = "不確定（存活者）"
        elif rd["verdict"] != v:
            note = "不確定（資料）"
        print("     存活者界限", [(m, vv, None if d is None else round(d, 3)) for m, vv, d in bounds], "｜剔除兩個來源結果不同的", rd["verdict"],
              ("%+.3f" % rd["delta"]) if "delta" in rd else "", "→ 最終：**%s**" % (note or v))
        final[(fam, key)] = note or v


# ---------- 另印 ----------
def base(sub, label):
    if not sub:
        print("  %-30s n 0" % label)
        return
    ex = [e["ex_12"] for e in sub if e["ex_12"] is not None]
    ex24 = [e["ex_24"] for e in sub if e["ex_24"] is not None]
    tot = sum(ex)
    print("  %-30s n %4d｜崩 %.3f｜12 個月曾達 2 倍 %.3f｜24 個月 %.3f｜6 個月先跌三成 %.3f｜12 個月超額 平均 %+.3f 中位數 %+.3f｜24 個月平均 %+.3f｜單檔最大貢獻占總超額 %s"
          % (label, len(sub), np.mean([e["crash"] for e in sub]), np.mean([e["ever2x_12"] for e in sub]), np.mean([e["ever2x_24"] for e in sub]),
             np.mean([e["dd30_6"] for e in sub]), np.mean(ex), np.median(ex), np.mean(ex24) if ex24 else float("nan"),
             ("%.2f" % (max(ex) / tot)) if tot > 0 else "總超額 ≤ 0"))


print("\n== 另印：基準率")
base(pop, "判讀母體")
s_all = sorted(e["S"] for e in pop)
c1, c2 = np.quantile(s_all, [1 / 3, 2 / 3])
for lab, cond in (("漲幅最小的三分之一", lambda e: e["S"] < c1), ("中間", lambda e: c1 <= e["S"] < c2), ("漲幅最大的三分之一", lambda e: e["S"] >= c2)):
    base([e for e in pop if cond(e)], lab)
for y in sorted({e["t"][:4] for e in pop}):
    base([e for e in pop if e["t"][:4] == y], y + " 年")
for key, label in MARKERS:
    base([e for e in pop if e[key] == 1], label + " 成立")
    base([e for e in pop if e[key] == 0], label + " 不成立")
cr = [e for e in pop if e["crash"] and e.get("months_to_peak") is not None]
if cr and not SYN:
    print("  崩的那些（%d）：從 t 到回落前最高月收盤 平均 %.1f 個月（中位數 %.0f）、再漲 平均 %+.3f（中位數 %+.3f）；t 當月就是最高的 %d"
          % (len(cr), np.mean([e["months_to_peak"] for e in cr]), np.median([e["months_to_peak"] for e in cr]),
             np.mean([e["gain_to_peak"] for e in cr]), np.median([e["gain_to_peak"] for e in cr]), sum(e["months_to_peak"] == 0 for e in cr)))
print("\n== 另印：其他母體與標記（只有 Δ，不做檢定）")
variants = [("t 在 2013-12～2016-11", [e for e in events if e["t"] < T_FROM and not e["flag_unadj"] and e["xcheck"] != "對不上" and not e["flag_unadj_out"]]),
            ("免除五年條件的那一組", [e for e in pop if e["five"].startswith("免除")]),
            ("放回資料旗標的事件", [e for e in events if e["in_window"]]),
            ("剔除交叉核做不了的", [e for e in pop if e["xcheck"] != "交叉核做不了"])]
sector = {}
for row in json.loads((L.H16 / "official" / "sector_twse.json").read_text(encoding="utf-8")):
    sector[str(row["公司代號"]).strip()] = str(row["產業別"]).strip()
for row in json.loads((L.H16 / "official" / "sector_tpex.json").read_text(encoding="utf-8")):
    sector[str(row["SecuritiesCompanyCode"]).strip()] = str(row["SecuritiesIndustryCode"]).strip()
variants.append(("剔除金融保險與建材營造（今天的產業別）", [e for e in pop if sector.get(e["code"]) not in ("14", "17")]))
for label, sub in variants:
    base(sub, label)
    for fam in ("crash", "basket"):
        for key, mlabel in MARKERS:
            r = judge(sub, key, fam, full=False)
            if "delta" in r:
                print("      %s｜%s：成立 %d／不成立 %d｜Δ %+.3f" % (FAM[fam][4], mlabel, r["n_on"], r["n_off"], r["delta"]))
print(" 只印的標記（判讀母體；Δ 同一個方向定義）")
v_ok = [e for e in pop if e["V_rank"] is not None]
vc = np.quantile([e["V_rank"] for e in v_ok], 2 / 3)
vch = [e for e in pop if e["V_chg"] is not None]
vcc = np.quantile([e["V_chg"] for e in vch], 2 / 3)
q_ok = [e for e in pop if e["Q"] is not None]
qc = np.quantile([e["Q"] for e in q_ok], 2 / 3)
for e in pop:
    e["V_hit"] = None if e["V_rank"] is None else int(e["V_rank"] >= vc)
    e["Vc_hit"] = None if e["V_chg"] is None else int(e["V_chg"] >= vcc)
    e["Q_hit"] = None if e["Q"] is None else int(e["Q"] >= qc)
for key, mlabel in (("I10", "發股 G ≥ 10%"), ("V_hit", "波動（全市場百分位，上三分之一）"), ("Vc_hit", "波動相對前 12 個月（上三分之一）"), ("Y", "年資不滿 36 個月"), ("Q_hit", "近三個月營收年增（上三分之一）")):
    for fam in ("crash", "basket"):
        r = judge(pop, key, fam, full=False)
        if "delta" in r:
            print("      %s｜%s：成立 %d（%.3f）／不成立 %d（%.3f）｜Δ %+.3f" % (FAM[fam][4], mlabel, r["n_on"], r["rate_on"], r["n_off"], r["rate_off"], r["delta"]))
print(" 交叉表（判讀母體）：", {"I×A": collections.Counter((e["I"], e["A_hit"]) for e in pop), "I×S": collections.Counter((e["I"], e["S_hit"]) for e in pop),
                        "A×S": collections.Counter((e["A_hit"], e["S_hit"]) for e in pop)})

# ---------- 不加五年條件、不設底價的版本（重新偵測；先核對預設參數重現階段一） ----------
def detect(five_year=True, floor=FLOOR):
    out = []
    for code in sorted(adj):
        s, r = adj[code], raw[code]
        first = min(s)
        locked = -1
        for i in range(IDX[SCAN_FROM], IDX[T_TO] + 1):
            if i <= locked:
                continue
            t, t24 = YMS[i], YMS[i - 24]
            if t not in s or t24 not in s:
                continue
            r24 = s[t] / s[t24] - 1
            if r24 < 1.0:
                continue
            m24 = L.mkt_cum(mkt, t24, t)
            if m24 is None or r24 - m24 < 1.0 or r[t24] < floor:
                continue
            if five_year:
                t60 = YMS[i - 60] if i >= 60 else None
                b = t60 if (t60 and t60 in s) else (first if L.mnum(first) <= L.mnum(t) - 36 else None)
                if b and s[t] / s[b] - 1 < 0.5:
                    continue
            locked = i + 24
            out.append({"code": code, "t": t})
    return out


d0 = detect()
assert {(e["code"], e["t"]) for e in d0} == {(e["code"], e["t"]) for e in events}, "預設參數重現不了階段一的事件"
if not SYN:
    for label, kw in (("不加五年條件", {"five_year": False}), ("不設底價", {"floor": 0.0})):
        sub = []
        for e in detect(**kw):
            if not (T_FROM <= e["t"] <= T_TO):
                continue
            o = path_outcomes(adj[e["code"]], e["t"])
            i = IDX[e["t"]]
            for h in (12, 24):
                m = L.mkt_cum(mkt, e["t"], YMS[i + h])
                o[f"ex_{h}"] = o[f"ret_{h}"] - m
            if not o["flag_unadj_out"]:
                sub.append(o)
        base(sub, label + "（重新偵測、沒有套事件側的旗標）")

print("\n最終判讀：", {f"{FAM[f][4]}｜{dict(MARKERS)[k]}": v for (f, k), v in final.items()})
if SYN:
    sys.exit(0)

# ---------- 輸出 ----------
cols = ["代號", "t", "進判讀母體", "疑似未還原（結果側）", "之後 24 個月回落四成", "回落五成", "第幾個月回落到四成", "回落前最高月收盤距 t 幾個月", "回落前再漲",
        "12 個月內曾達 2 倍", "24 個月內曾達 2 倍", "6 個月內先跌三成", "12 個月報酬", "同期全市場等權", "12 個月超額", "24 個月超額",
        "結果窗看得到的月數", "結果窗內下市", "12 個月內下市", "yfinance 另算的回落四成", "yfinance 另算的曾達 2 倍", "兩個來源結果不同"]


def f4(x):
    return "" if x is None else "%.4f" % x


with open(OUT / "h17-stage2-outcomes.csv", "w", encoding="utf-8", newline="\n") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(cols)
    for e in sorted(events, key=lambda e: (e["t"], e["code"])):
        w.writerow([e["code"], e["t"], int(e["in_pop"] and not e["flag_unadj_out"]), e["flag_unadj_out"], e["crash"], e["crash50"], e["crash_k"] or "",
                    "" if e["months_to_peak"] is None else e["months_to_peak"], f4(e["gain_to_peak"]), e["ever2x_12"], e["ever2x_24"], e["dd30_6"],
                    f4(e["ret_12"]), f4(e["mkt_12"]), f4(e["ex_12"]), f4(e["ex_24"]), e["n_months"], e["delisted_in_win"], e["delisted_in_12"],
                    "" if e["yf_crash"] is None else e["yf_crash"], "" if e["yf_ever2x_12"] is None else e["yf_ever2x_12"], e["discordant"]])
(HERE / "stage2_outcomes.json").write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")
print("已寫", OUT / "h17-stage2-outcomes.csv", "sha256", L.sha256_lf(OUT / "h17-stage2-outcomes.csv")[:16])
```

### context_baseline.py（對照脈絡（看過結果之後才加）；sha256 前 16 碼 `d5ef953f80a5e279`）

```python
"""H17 的對照脈絡（**看過階段二結果之後才加的；不進判讀、不改任何判讀線**）。
問的是：同一段時間裡「隨便一檔股票的隨便一個月」，照同一個定義算，崩與曾達 2 倍各占幾成？
沒有這個數，事件後的六成二沒有東西可以比。只讀，不寫任何輸出檔。"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

import h17lib as L

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
T_FROM, T_TO = "2016-12", "2024-10"
ME = L.month_ends()
YMS = sorted(ME)
IDX = {ym: i for i, ym in enumerate(YMS)}
raw, name, market = L.load_quotes(ME)
fac, _ = L.load_factors()
dr = {c for c in raw if L.is_dr(name.get(c, ""))}
mkt, _u, _d = L.market_returns(raw, fac, ME, drop_dr_names=dr)
adj = {c: L.adjusted(s, ME, fac.get(c, ())) for c, s in raw.items() if c not in dr}
events = json.loads((HERE / "stage2_outcomes.json").read_text(encoding="utf-8"))
pop = [e for e in events if e["in_pop"] and not e["flag_unadj_out"]]
ev_keys = {(e["code"], e["t"]) for e in events}


def outcomes(s, t):
    i, p0 = IDX[t], s[t]
    win = [(k, s[YMS[i + k]]) for k in range(1, 25) if i + k < len(YMS) and YMS[i + k] in s]
    if not win:
        return None
    runmax, crash = p0, 0
    seq = [p0] + [p for _k, p in win]
    if any(not (0.2 <= b / a <= 5) for a, b in zip(seq, seq[1:])):
        return None
    for _k, p in win:
        runmax = max(runmax, p)
        if p <= 0.6 * runmax:
            crash = 1
            break
    sub = [(k, p) for k, p in win if k <= 12]
    exit_p = sub[-1][1] if sub else p0
    m = L.mkt_cum(mkt, t, YMS[i + 12])
    return dict(crash=crash, ever2x_12=int(any(p >= 2 * p0 for _k, p in sub)), ever2x_24=int(any(p >= 2 * p0 for _k, p in win)),
                dd30_6=int(any(p <= 0.7 * p0 for k, p in win if k <= 6)), ex_12=exit_p / p0 - 1 - m, ret_12=exit_p / p0 - 1)


by_month = collections.defaultdict(list)
for code, s in adj.items():
    r = raw[code]
    for t in s:
        if not (T_FROM <= t <= T_TO) or r.get(t, 0) < 5.0:
            continue
        o = outcomes(s, t)
        if o:
            o["is_event"] = (code, t) in ev_keys
            by_month[t].append(o)
allrows = [o for rows in by_month.values() for o in rows]
print("對照母體：2016-12～2024-10 每個月底、未還原收盤 ≥ 5 元的每一檔（含下市）", len(allrows), "個「檔×月」")


def line(label, rows):
    ex = [o["ex_12"] for o in rows]
    print("  %-34s n %6d｜崩 %.3f｜12 個月曾達 2 倍 %.3f｜24 個月 %.3f｜6 個月先跌三成 %.3f｜12 個月超額 平均 %+.3f 中位數 %+.3f｜12 個月後比 t 高的比例 %.3f"
          % (label, len(rows), np.mean([o["crash"] for o in rows]), np.mean([o["ever2x_12"] for o in rows]), np.mean([o["ever2x_24"] for o in rows]),
             np.mean([o["dd30_6"] for o in rows]), np.mean(ex), np.median(ex), np.mean([o["ret_12"] > 0 for o in rows])))


line("全部檔×月（每一列等權）", allrows)
# 照事件的月份分布加權：每個事件月取那個月全市場的比例，再照事件筆數加權平均
w = collections.Counter(e["t"] for e in pop)
keys = ("crash", "ever2x_12", "ever2x_24", "dd30_6", "ex_12")
agg = {k: sum(w[t] * np.mean([o[k] for o in by_month[t]]) for t in w) / sum(w.values()) for k in keys}
pos = sum(w[t] * np.mean([o["ret_12"] > 0 for o in by_month[t]]) for t in w) / sum(w.values())
print("  %-34s          ｜崩 %.3f｜12 個月曾達 2 倍 %.3f｜24 個月 %.3f｜6 個月先跌三成 %.3f｜12 個月超額 平均 %+.3f｜12 個月後比 t 高的比例 %.3f"
      % ("同月全市場（照事件的月份分布加權）", agg["crash"], agg["ever2x_12"], agg["ever2x_24"], agg["dd30_6"], agg["ex_12"], pos))
print("  事件（判讀母體 %d）：崩 %.3f｜12 個月曾達 2 倍 %.3f｜24 個月 %.3f｜6 個月先跌三成 %.3f｜12 個月超額 平均 %+.3f 中位數 %+.3f｜12 個月後比 t 高的比例 %.3f｜12 個月超額為正的比例 %.3f"
      % (len(pop), np.mean([e["crash"] for e in pop]), np.mean([e["ever2x_12"] for e in pop]), np.mean([e["ever2x_24"] for e in pop]),
         np.mean([e["dd30_6"] for e in pop]), np.mean([e["ex_12"] for e in pop]), np.median([e["ex_12"] for e in pop]),
         np.mean([e["ret_12"] > 0 for e in pop]), np.mean([e["ex_12"] > 0 for e in pop])))
# 事件裡 12 個月報酬的分位
q = np.quantile([e["ret_12"] for e in pop], [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
print("  事件的 12 個月報酬分位（10／25／50／75／90／95／99）：", [round(float(x), 3) for x in q])
exs = sorted((e["ex_12"] for e in pop), reverse=True)
tot_pos = sum(x for x in exs if x > 0)
print("  事件的 12 個月超額：為正的 %d 筆合計 %+.1f；最大的 10 筆占正的合計 %.2f、最大的 54 筆（5%%）占 %.2f；為負的 %d 筆合計 %+.1f"
      % (sum(x > 0 for x in exs), tot_pos, sum(exs[:10]) / tot_pos, sum(exs[:54]) / tot_pos, sum(x <= 0 for x in exs), sum(x for x in exs if x <= 0)))
# 崩與曾達 2 倍的交叉
c = collections.Counter((e["crash"], e["ever2x_24"]) for e in pop)
print("  事件：崩 × 24 個月內曾達 2 倍 ＝", dict(c))
# A、S 的四格
for a in (1, 0):
    for s_ in (1, 0):
        sub = [e for e in pop if e["A_hit"] == a and e["S_hit"] == s_]
        if sub:
            print("  A=%d S=%d：n %4d｜崩 %.3f｜12 個月曾達 2 倍 %.3f｜12 個月超額 平均 %+.3f 中位數 %+.3f"
                  % (a, s_, len(sub), np.mean([e["crash"] for e in sub]), np.mean([e["ever2x_12"] for e in sub]),
                     np.mean([e["ex_12"] for e in sub]), np.median([e["ex_12"] for e in sub])))
```

### fetch_ext.py（資料段之一：交易所月底行情、公司行動、發行股數（只抓不算）；sha256 前 16 碼 `382bffdb0f555111`）

```python
"""H17 的資料段：只抓不算。原始檔存 h17_cache/official；H16 的資料夾不動（之後的腳本兩邊都讀）。
①2022-10～2026-10 的月底交易日 ②那些月底的全市場行情（上市、上櫃）③2022-10～2026-10 的除權息與減資
④終止上市櫃名單（到今天）⑤2011-12～2026-10 每個月底的全市場發行股數（上市 MI_QFIIS、上櫃僑外資持股表）。
節流 5 秒；到 05:00（台北）自動停。零 LLM；對外請求不帶任何個人資訊。"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import requests
import yfinance as yf

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
OFF = HERE / "official"
OFF.mkdir(exist_ok=True)
H16 = HERE.parent / "h16_cache"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}
PACE = 5.0


def log(*a):
    print(dt.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def past_stop():
    return dt.time(5, 0) <= dt.datetime.now().time() < dt.time(7, 10)


def get(url, dest, ok):
    if dest.exists():
        return "cached"
    for attempt in range(5):
        if past_stop():
            return "stopped"
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
f3 = HERE / "month_ends3.json"
if f3.exists():
    ends3 = json.loads(f3.read_text(encoding="utf-8"))
else:
    df = yf.download("2330.TW", start="2022-10-01", end="2026-11-01", interval="1d", auto_adjust=False, progress=False)
    last = {}
    for d in df.index:
        s = d.strftime("%Y-%m-%d")
        last[s[:7]] = s
    ends3 = [last[k] for k in sorted(last)]
    assert ends3 and ends3[0][:7] == "2022-10" and ends3[-1][:7] == "2026-10", (ends3[:1], ends3[-1:])
    f3.write_text(json.dumps(ends3), encoding="utf-8")
log("新的月底交易日", len(ends3), ends3[0], "→", ends3[-1])

# ② 月底行情
stat = {"ok": 0, "cached": 0, "other": 0, "error": 0, "stopped": 0}
for n, d in enumerate(ends3, 1):
    ymd = d.replace("-", "")
    stat[get(f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json",
             OFF / f"twse_{ymd}.json", lambda o: o.get("stat") == "OK" and len(o.get("tables") or []) >= 9)] += 1
    stat[get(f"https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?date={d.replace('-', '/')}&id=&response=json",
             OFF / f"tpex_{ymd}.json", lambda o: o.get("stat") == "ok" and (o.get("tables") or [{}])[0].get("totalCount", 0) > 100)] += 1
    if n % 12 == 0:
        log("行情進度", n, "/", len(ends3), d, stat)
log("月底行情", stat)

# ③ 除權息與減資
corp = [("twse_exright_2022c", "https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate=20221001&endDate=20221231&response=json"),
        ("tpex_exright_2022c", "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate=2022/10/01&endDate=2022/12/31&response=json")]
for y, end in ((2023, "1231"), (2024, "1231"), (2025, "1231"), (2026, "1031")):
    corp.append((f"twse_exright_{y}", f"https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate={y}0101&endDate={y}{end}&response=json"))
    corp.append((f"tpex_exright_{y}", f"https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate={y}/01/01&endDate={y}/{end[:2]}/{end[2:]}&response=json"))
corp += [("twse_reduction_2022_2026", "https://www.twse.com.tw/rwd/zh/reducation/TWTAUU?startDate=20221001&endDate=20261031&response=json"),
         ("tpex_reduction_2022_2026", "https://www.tpex.org.tw/www/zh-tw/bulletin/revivt?startDate=2022/10/01&endDate=2026/10/31&response=json")]
# ④ 終止上市櫃名單
corp += [("twse_delisted_all_now", "https://www.twse.com.tw/rwd/zh/company/suspendListing?response=json")]
for y in (2023, 2024, 2025, 2026):
    corp.append((f"tpex_delisted_{y}_now", f"https://www.tpex.org.tw/www/zh-tw/company/deListed?date={y}&response=json"))
for name, url in corp:
    st = get(url, OFF / f"{name}.json", lambda o: bool(o))
    try:
        o = json.loads((OFF / f"{name}.json").read_text(encoding="utf-8"))
        t0 = (o.get("tables") or [{}])[0]
        data = o.get("data") or t0.get("data") or []
        log(name, st, "stat", o.get("stat"), "筆數", len(data), "首列", [str(x)[:12] for x in (data[0][:4] if data else [])],
            "末列", [str(x)[:12] for x in (data[-1][:4] if data else [])])
    except Exception as exc:  # noqa: BLE001
        log(name, st, "讀不出", type(exc).__name__)

# ⑤ 發行股數（每個月底）
ends_all = (json.loads((H16 / "month_ends.json").read_text(encoding="utf-8"))
            + json.loads((H16 / "month_ends2.json").read_text(encoding="utf-8")) + ends3)
assert len({d[:7] for d in ends_all}) == len(ends_all)
stat = {"ok": 0, "cached": 0, "other": 0, "error": 0, "stopped": 0}


def ok_twse(ymd):
    return lambda o: o.get("stat") == "OK" and str(o.get("date")) == ymd and len(o.get("data") or []) > 100


def ok_tpex(ymd):
    return lambda o: o.get("stat") == "ok" and str(o.get("date")) == ymd and len(((o.get("tables") or [{}])[0].get("data")) or []) > 100


for n, d in enumerate(ends_all, 1):
    ymd = d.replace("-", "")
    stat[get(f"https://www.twse.com.tw/rwd/zh/fund/MI_QFIIS?date={ymd}&selectType=ALLBUT0999&response=json",
             OFF / f"twse_shares_{ymd}.json", ok_twse(ymd))] += 1
    stat[get(f"https://www.tpex.org.tw/www/zh-tw/insti/qfii?date={d.replace('-', '/')}&response=json",
             OFF / f"tpex_shares_{ymd}.json", ok_tpex(ymd))] += 1
    if n % 12 == 0:
        log("股數進度", n, "/", len(ends_all), d, stat)
log("發行股數", stat)
log("EXT_DONE" if not past_stop() else "EXT_STOPPED_BY_CLOCK")
```

### fetch_px17.py（資料段之二：yfinance 月線（交叉核用）；sha256 前 16 碼 `77393fae6a59aee9`）

```python
"""H17 的資料段之二：yfinance 還原月線（只用來交叉核交易所的還原序列；主序列是交易所月底行情）。
宇宙＝交易所月底行情 2011-12～2026-10 出現過的四碼普通股代號；板別照它最後一次出現在哪個交易所的行情。
只抓不算；取不到的照數並記下錯誤訊息（限流不會 raise，要讀 yfinance.shared._ERRORS）。對外請求不帶任何個人資訊。"""
import importlib
import json
import re
import sys
import time
from pathlib import Path

import yfinance as yf

sys.stdout.reconfigure(encoding="utf-8")
yshared = importlib.import_module("yfinance.shared")
HERE = Path(__file__).parent
H16 = HERE.parent / "h16_cache"
START, END = "2011-12-01", "2026-11-01"
CODE = re.compile(r"^(?!00)\d{4}$")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def codes_in(path):
    o = json.loads(path.read_text(encoding="utf-8"))
    out = set()
    for t in o.get("tables") or []:
        f = t.get("fields") or []
        ci = next((i for i, x in enumerate(f) if x in ("證券代號", "代號")), None)
        if ci is None:
            continue
        for r in t.get("data") or []:
            c = str(r[ci]).strip()
            if CODE.match(c):
                out.add(c)
    return out


last_market = {}
files = []
for folder in (H16 / "official", HERE / "official"):
    for f in folder.glob("*.json"):
        m = re.fullmatch(r"(twse|tpex)_(\d{8})", f.stem)
        if m:
            files.append((m.group(2), m.group(1), f))
for ymd, market, f in sorted(files):
    for c in codes_in(f):
        last_market[c] = market          # 檔案照日期排序，留下的是最後一次出現的板
tickers = sorted(c + (".TW" if m == "twse" else ".TWO") for c, m in last_market.items())
log("宇宙", len(tickers))

cache = HERE / "px_all.json"
px = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
errors = {}


def pull(chunk, pause):
    try:
        yshared._ERRORS.clear()
    except Exception:  # noqa: BLE001
        pass
    try:
        df = yf.download(tickers=chunk, start=START, end=END, interval="1mo", auto_adjust=True,
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
            px[t] = [[d.strftime("%Y-%m"), float(v)] for d, v in s.items()]
            errors.pop(t, None)
            continue
        errors[t] = str(getattr(yshared, "_ERRORS", {}).get(t, "empty"))
    time.sleep(pause)


for rnd, (size, pause) in enumerate(((60, 6), (20, 12), (5, 20)), 1):
    todo = [t for t in tickers if t not in px]
    if rnd > 1:
        todo = [t for t in todo if "limit" in errors.get(t, "").lower() or "too many" in errors.get(t, "").lower()
                or errors.get(t, "").startswith("download")]
    log("第", rnd, "輪待抓", len(todo))
    for i in range(0, len(todo), size):
        pull(todo[i:i + size], pause)
        if (i // size) % 5 == 0:
            cache.write_text(json.dumps(px), encoding="utf-8")
            log("  進度", i + size, "/", len(todo), "有價", len(px))
    cache.write_text(json.dumps(px), encoding="utf-8")
missing = [t for t in tickers if t not in px]
(HERE / "px_all_errors.json").write_text(json.dumps({t: errors.get(t, "") for t in missing}, ensure_ascii=False), encoding="utf-8")
lim = sum(1 for t in missing if "limit" in errors.get(t, "").lower() or "too many" in errors.get(t, "").lower())
log("有價", len(px), "｜缺", len(missing), "｜其中錯誤訊息像限流的", lim, "｜最晚一根", max((v[-1][0] for v in px.values()), default=None))
log("PX_DONE")
```

### fetch_detail.py（資料段之三：上市除權息逐筆明細；sha256 前 16 碼 `bf2736f87220b5f5`）

```python
"""H17 的資料段之三：上市除權息的逐筆明細（分得出無償配股與現金增資）。只抓 stage1.py 列在 need_detail.json 的那幾筆。
只存原始檔；節流 5 秒；對外請求不帶任何個人資訊。"""
import json
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
OUT = HERE / "detail"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}
need = json.loads((HERE / "need_detail.json").read_text(encoding="utf-8"))
stat = {"ok": 0, "cached": 0, "empty": 0, "error": 0}
for n, (code, date) in enumerate(need, 1):
    ymd = date.replace("-", "")
    dest = OUT / f"{code}_{ymd}.json"
    if dest.exists():
        stat["cached"] += 1
        continue
    got = "error"
    for attempt in range(4):
        try:
            r = requests.get(f"https://www.twse.com.tw/rwd/zh/exRight/TWT49UDetail?STK_NO={code}&T1={ymd}&response=json", headers=UA, timeout=60)
            time.sleep(5)
            o = json.loads(r.content.decode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            print("  重試", code, ymd, type(exc).__name__, flush=True)
            time.sleep(30 * (attempt + 1))
            continue
        if o.get("fields") and o.get("data"):
            dest.write_bytes(r.content)
            got = "ok"
        else:
            (OUT / f"{code}_{ymd}.empty").write_bytes(r.content[:1000])
            got = "empty"
        break
    stat[got] += 1
    if n % 20 == 0:
        print(time.strftime("%H:%M:%S"), "進度", n, "/", len(need), stat, flush=True)
print(time.strftime("%H:%M:%S"), "結束", stat, flush=True)
print("DETAIL_DONE")
```

### sanity_lib.py（資料層自查（登記之前跑的）；sha256 前 16 碼 `b47cf2862ddfbef2`）

```python
"""h17lib 的自查（唯讀；不算任何事件或結果）：筆數、因子統計、與 H16 的全市場等權逐月比對（重疊的月份）、發行股數涵蓋。"""
import json
import sys

import h17lib as L

sys.stdout.reconfigure(encoding="utf-8")
ME = L.month_ends()
YMS = sorted(ME)
raw, name, market = L.load_quotes(ME)
fac, fstat = L.load_factors()
print("月份", YMS[0], "→", YMS[-1], len(YMS), "｜有收盤的代號", len(raw), "｜存託憑證（簡稱結尾 DR）", sum(L.is_dr(name.get(c, "")) for c in raw))
print("還原因子", fstat, "｜面額變更列", [(c, d, round(f, 3)) for c, v in fac.items() for d, f, k, _ in v if k == "面額變更"])
print("減資原因", {r: sum(1 for v in fac.values() for _d, _f, k, n in v if k == "減資" and n.get("reason") == r)
                 for r in sorted({n.get("reason") for v in fac.values() for _d, _f, k, n in v if k == "減資"})})
print("除權息的種類（上市）", {t: sum(1 for v in fac.values() for _d, _f, k, n in v if k == "除權息" and n["market"] == "twse" and n.get("type") == t)
                          for t in sorted({n.get("type") for v in fac.values() for _d, _f, k, n in v if k == "除權息" and n["market"] == "twse"})})
print("上櫃除權息有無償配股的列", sum(1 for v in fac.values() for _d, _f, k, n in v if k == "除權息" and n["market"] == "tpex" and (n.get("stock_per_1000") or 0) > 0))

# 與 H16 的全市場等權比（H16 含存託憑證、沒有面額變更因子；這裡先用同樣的口徑重算一次，只比重疊月份）
import importlib.util
spec = importlib.util.spec_from_file_location("adjust16", L.H16 / "adjust.py")
adj16 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adj16)
FAC16, _s, _b = adj16.load_factors()
fac_h16style = {c: [(d, f, k, {}) for d, f, k in v] for c, v in FAC16.items()}
m16, _u, _d = L.market_returns({c: {ym: v for ym, v in s.items() if ym <= "2022-09"} for c, s in raw.items()}, fac_h16style, {ym: ME[ym] for ym in YMS if ym <= "2022-09"})
dr = {c for c in raw if L.is_dr(name.get(c, ""))}
m17, used, dropped = L.market_returns(raw, fac, ME, drop_dr_names=dr)
diffs = sorted(((abs(m16[ym] - m17[ym]), ym) for ym in m16), reverse=True)[:5]
print("全市場等權：H17 月數", len(m17), "用到", used, "剔除", dropped, "｜與 H16 口徑差最大的五個月（絕對差, 月）", [(round(a, 5), ym) for a, ym in diffs])
print("全市場等權各年累積（H17 口徑）", {y: round(L.mkt_cum(m17, f"{int(y) - 1}-12", f"{y}-12") or 0, 3) for y in map(str, range(2012, 2026))})

shares = L.load_shares(ME)
both = [c for c in raw if c in shares]
print("發行股數：代號", len(shares), "｜行情上有而股數表沒有的代號", len(set(raw) - set(shares)),
      "｜（代號×月）有收盤也有股數的比例 %.3f" % (sum(1 for c in raw for ym in raw[c] if ym in shares.get(c, {})) / sum(len(s) for s in raw.values())))
px = json.loads((L.HERE / "px_all.json").read_text(encoding="utf-8"))
print("yfinance：有價的代號", len(px), "｜行情上有而 yfinance 沒有的", len({c for c in raw} - {t.split('.')[0] for t in px}))
```

### stage2.py 的輸出（真的結果，一次）（逐字）

```text
階段一 digest 相符｜事件 1446 ｜階段一的判讀母體 1078
判讀母體：階段一 1078 → 剔除疑似未還原（結果側） 0 → 1078 ｜結果窗內下市 4 （12 個月內 1 ） ｜兩個來源結果不同 7 ｜yfinance 沒得比 23

== 判讀（判讀母體 1078；顯著線 p ≤ 0.0083；事件最多的年 2021）
 家族： 崩（回落四成）
  I 發股                   成立 119（0.672）／不成立 947（0.610）｜W 103.4｜Δ +0.049｜p 0.1649｜區間 -0.042～+0.131｜前後兩段 ['56/386 +0.008', '63/561 +0.085']｜拿掉 2021 年 +0.035｜同向量 +0.080 → **不確定**
     存活者界限 [('upper', '不確定', np.float64(0.057)), ('lower', '不確定', np.float64(0.042))] ｜剔除兩個來源結果不同的 不確定 +0.051 → 最終：**不確定**
  A 加速                   成立 356（0.801）／不成立 710（0.521）｜W 199.9｜Δ +0.234｜p 0.0001｜區間 +0.171～+0.299｜前後兩段 ['96/344 +0.301', '260/366 +0.197']｜拿掉 2021 年 +0.259｜同向量 +0.217 → **支持**
     存活者界限 [('upper', '支持', np.float64(0.233)), ('lower', '支持', np.float64(0.237))] ｜剔除兩個來源結果不同的 支持 +0.234 → 最終：**支持**
  S 漲幅大小                 成立 360（0.761）／不成立 718（0.545）｜W 229.3｜Δ +0.196｜p 0.0001｜區間 +0.143～+0.248｜前後兩段 ['145/301 +0.219', '215/417 +0.180']｜拿掉 2021 年 +0.221｜同向量 +0.167 → **支持**
     存活者界限 [('upper', '支持', np.float64(0.198)), ('lower', '支持', np.float64(0.195))] ｜剔除兩個來源結果不同的 支持 +0.193 → 最終：**支持**
 家族： 籃子（12 個月平均超額）
  I 發股                   成立 119（-0.081）／不成立 947（-0.023）｜W 103.4｜Δ +0.062｜p 0.1644｜區間 -0.053～+0.160｜前後兩段 ['56/386 +0.084', '63/561 +0.044']｜拿掉 2021 年 +0.089｜同向量 -0.036 → **不確定**
     存活者界限 [('lower', '不確定', np.float64(0.078))] ｜剔除兩個來源結果不同的 不確定 +0.063 → 最終：**不確定**
  A 加速                   成立 356（-0.077）／不成立 710（0.007）｜W 199.9｜Δ +0.026｜p 0.3118｜區間 -0.099～+0.143｜前後兩段 ['96/344 -0.043', '260/366 +0.064']｜拿掉 2021 年 +0.019｜同向量 -0.047 → **不確定**
     存活者界限 [('lower', '不確定', np.float64(0.025))] ｜剔除兩個來源結果不同的 不確定 +0.024 → 最終：**不確定**
  S 漲幅大小                 成立 360（-0.065）／不成立 718（-0.002）｜W 229.3｜Δ +0.026｜p 0.2866｜區間 -0.079～+0.124｜前後兩段 ['145/301 +0.031', '215/417 +0.023']｜拿掉 2021 年 +0.016｜同向量 +0.016 → **不確定**
     存活者界限 [('lower', '不確定', np.float64(0.033))] ｜剔除兩個來源結果不同的 不確定 +0.027 → 最終：**不確定**

== 另印：基準率
  判讀母體                           n 1078｜崩 0.617｜12 個月曾達 2 倍 0.126｜24 個月 0.202｜6 個月先跌三成 0.214｜12 個月超額 平均 -0.023 中位數 -0.187｜24 個月平均 -0.113｜單檔最大貢獻占總超額 總超額 ≤ 0
  漲幅最小的三分之一                      n  359｜崩 0.524｜12 個月曾達 2 倍 0.123｜24 個月 0.203｜6 個月先跌三成 0.131｜12 個月超額 平均 -0.010 中位數 -0.137｜24 個月平均 -0.097｜單檔最大貢獻占總超額 總超額 ≤ 0
  中間                             n  359｜崩 0.565｜12 個月曾達 2 倍 0.148｜24 個月 0.237｜6 個月先跌三成 0.214｜12 個月超額 平均 +0.006 中位數 -0.175｜24 個月平均 -0.110｜單檔最大貢獻占總超額 3.28
  漲幅最大的三分之一                      n  360｜崩 0.761｜12 個月曾達 2 倍 0.108｜24 個月 0.167｜6 個月先跌三成 0.297｜12 個月超額 平均 -0.065 中位數 -0.268｜24 個月平均 -0.130｜單檔最大貢獻占總超額 總超額 ≤ 0
  2016 年                         n    1｜崩 1.000｜12 個月曾達 2 倍 0.000｜24 個月 0.000｜6 個月先跌三成 1.000｜12 個月超額 平均 -0.473 中位數 -0.473｜24 個月平均 -0.071｜單檔最大貢獻占總超額 總超額 ≤ 0
  2017 年                         n  148｜崩 0.743｜12 個月曾達 2 倍 0.128｜24 個月 0.182｜6 個月先跌三成 0.095｜12 個月超額 平均 -0.016 中位數 -0.122｜24 個月平均 -0.115｜單檔最大貢獻占總超額 總超額 ≤ 0
  2018 年                         n   74｜崩 0.770｜12 個月曾達 2 倍 0.068｜24 個月 0.108｜6 個月先跌三成 0.459｜12 個月超額 平均 -0.105 中位數 -0.202｜24 個月平均 -0.215｜單檔最大貢獻占總超額 總超額 ≤ 0
  2019 年                         n   65｜崩 0.431｜12 個月曾達 2 倍 0.154｜24 個月 0.277｜6 個月先跌三成 0.185｜12 個月超額 平均 +0.086 中位數 -0.187｜24 個月平均 -0.213｜單檔最大貢獻占總超額 0.48
  2020 年                         n  158｜崩 0.563｜12 個月曾達 2 倍 0.222｜24 個月 0.272｜6 個月先跌三成 0.133｜12 個月超額 平均 -0.023 中位數 -0.252｜24 個月平均 -0.304｜單檔最大貢獻占總超額 總超額 ≤ 0
  2021 年                         n  202｜崩 0.733｜12 個月曾達 2 倍 0.059｜24 個月 0.104｜6 個月先跌三成 0.297｜12 個月超額 平均 -0.143 中位數 -0.261｜24 個月平均 -0.322｜單檔最大貢獻占總超額 總超額 ≤ 0
  2022 年                         n   76｜崩 0.382｜12 個月曾達 2 倍 0.145｜24 個月 0.263｜6 個月先跌三成 0.224｜12 個月超額 平均 -0.010 中位數 -0.171｜24 個月平均 -0.178｜單檔最大貢獻占總超額 總超額 ≤ 0
  2023 年                         n  172｜崩 0.442｜12 個月曾達 2 倍 0.163｜24 個月 0.233｜6 個月先跌三成 0.169｜12 個月超額 平均 +0.129 中位數 -0.172｜24 個月平均 +0.214｜單檔最大貢獻占總超額 0.41
  2024 年                         n  182｜崩 0.698｜12 個月曾達 2 倍 0.088｜24 個月 0.225｜6 個月先跌三成 0.236｜12 個月超額 平均 -0.049 中位數 -0.141｜24 個月平均 +0.083｜單檔最大貢獻占總超額 總超額 ≤ 0
  I 發股 成立                        n  119｜崩 0.672｜12 個月曾達 2 倍 0.160｜24 個月 0.235｜6 個月先跌三成 0.252｜12 個月超額 平均 -0.081 中位數 -0.233｜24 個月平均 -0.253｜單檔最大貢獻占總超額 總超額 ≤ 0
  I 發股 不成立                       n  947｜崩 0.610｜12 個月曾達 2 倍 0.122｜24 個月 0.199｜6 個月先跌三成 0.210｜12 個月超額 平均 -0.023 中位數 -0.180｜24 個月平均 -0.118｜單檔最大貢獻占總超額 總超額 ≤ 0
  A 加速 成立                        n  356｜崩 0.801｜12 個月曾達 2 倍 0.132｜24 個月 0.185｜6 個月先跌三成 0.354｜12 個月超額 平均 -0.077 中位數 -0.277｜24 個月平均 -0.161｜單檔最大貢獻占總超額 總超額 ≤ 0
  A 加速 不成立                       n  710｜崩 0.521｜12 個月曾達 2 倍 0.125｜24 個月 0.214｜6 個月先跌三成 0.144｜12 個月超額 平均 +0.007 中位數 -0.149｜24 個月平均 -0.083｜單檔最大貢獻占總超額 1.38
  S 漲幅大小 成立                      n  360｜崩 0.761｜12 個月曾達 2 倍 0.108｜24 個月 0.167｜6 個月先跌三成 0.297｜12 個月超額 平均 -0.065 中位數 -0.268｜24 個月平均 -0.130｜單檔最大貢獻占總超額 總超額 ≤ 0
  S 漲幅大小 不成立                     n  718｜崩 0.545｜12 個月曾達 2 倍 0.135｜24 個月 0.220｜6 個月先跌三成 0.173｜12 個月超額 平均 -0.002 中位數 -0.152｜24 個月平均 -0.104｜單檔最大貢獻占總超額 總超額 ≤ 0
  崩的那些（665）：從 t 到回落前最高月收盤 平均 4.2 個月（中位數 2）、再漲 平均 +0.591（中位數 +0.261）；t 當月就是最高的 173

== 另印：其他母體與標記（只有 Δ，不做檢定）
  t 在 2013-12～2016-11            n  343｜崩 0.542｜12 個月曾達 2 倍 0.067｜24 個月 0.125｜6 個月先跌三成 0.128｜12 個月超額 平均 -0.046 中位數 -0.151｜24 個月平均 -0.070｜單檔最大貢獻占總超額 總超額 ≤ 0
      崩（回落四成）｜I 發股：成立 53／不成立 281｜Δ +0.078
      崩（回落四成）｜A 加速：成立 92／不成立 247｜Δ +0.172
      崩（回落四成）｜S 漲幅大小：成立 120／不成立 223｜Δ +0.178
      籃子（12 個月平均超額）｜I 發股：成立 53／不成立 281｜Δ -0.054
      籃子（12 個月平均超額）｜A 加速：成立 92／不成立 247｜Δ -0.091
      籃子（12 個月平均超額）｜S 漲幅大小：成立 120／不成立 223｜Δ +0.043
  免除五年條件的那一組                     n   60｜崩 0.667｜12 個月曾達 2 倍 0.083｜24 個月 0.183｜6 個月先跌三成 0.200｜12 個月超額 平均 -0.077 中位數 -0.273｜24 個月平均 -0.288｜單檔最大貢獻占總超額 總超額 ≤ 0
      崩（回落四成）｜I 發股：成立 9／不成立 51｜Δ +0.000
      崩（回落四成）｜A 加速：成立 20／不成立 39｜Δ +0.157
      崩（回落四成）｜S 漲幅大小：成立 30／不成立 30｜Δ +0.162
      籃子（12 個月平均超額）｜I 發股：成立 9／不成立 51｜Δ -0.185
      籃子（12 個月平均超額）｜A 加速：成立 20／不成立 39｜Δ +0.034
      籃子（12 個月平均超額）｜S 漲幅大小：成立 30／不成立 30｜Δ -0.034
  放回資料旗標的事件                      n 1091｜崩 0.615｜12 個月曾達 2 倍 0.130｜24 個月 0.206｜6 個月先跌三成 0.213｜12 個月超額 平均 -0.019 中位數 -0.187｜24 個月平均 -0.107｜單檔最大貢獻占總超額 總超額 ≤ 0
      崩（回落四成）｜I 發股：成立 122／不成立 955｜Δ +0.039
      崩（回落四成）｜A 加速：成立 360／不成立 718｜Δ +0.236
      崩（回落四成）｜S 漲幅大小：成立 367／不成立 724｜Δ +0.197
      籃子（12 個月平均超額）｜I 發股：成立 122／不成立 955｜Δ +0.053
      籃子（12 個月平均超額）｜A 加速：成立 360／不成立 718｜Δ +0.012
      籃子（12 個月平均超額）｜S 漲幅大小：成立 367／不成立 724｜Δ +0.011
  剔除交叉核做不了的                      n 1054｜崩 0.614｜12 個月曾達 2 倍 0.127｜24 個月 0.202｜6 個月先跌三成 0.212｜12 個月超額 平均 -0.022 中位數 -0.187｜24 個月平均 -0.108｜單檔最大貢獻占總超額 總超額 ≤ 0
      崩（回落四成）｜I 發股：成立 114／不成立 928｜Δ +0.058
      崩（回落四成）｜A 加速：成立 352／不成立 690｜Δ +0.237
      崩（回落四成）｜S 漲幅大小：成立 352／不成立 702｜Δ +0.197
      籃子（12 個月平均超額）｜I 發股：成立 114／不成立 928｜Δ +0.055
      籃子（12 個月平均超額）｜A 加速：成立 352／不成立 690｜Δ +0.025
      籃子（12 個月平均超額）｜S 漲幅大小：成立 352／不成立 702｜Δ +0.024
  剔除金融保險與建材營造（今天的產業別）            n 1016｜崩 0.617｜12 個月曾達 2 倍 0.133｜24 個月 0.212｜6 個月先跌三成 0.213｜12 個月超額 平均 -0.017 中位數 -0.180｜24 個月平均 -0.098｜單檔最大貢獻占總超額 總超額 ≤ 0
      崩（回落四成）｜I 發股：成立 116／不成立 889｜Δ +0.050
      崩（回落四成）｜A 加速：成立 332／不成立 675｜Δ +0.244
      崩（回落四成）｜S 漲幅大小：成立 342／不成立 674｜Δ +0.193
      籃子（12 個月平均超額）｜I 發股：成立 116／不成立 889｜Δ +0.067
      籃子（12 個月平均超額）｜A 加速：成立 332／不成立 675｜Δ +0.008
      籃子（12 個月平均超額）｜S 漲幅大小：成立 342／不成立 674｜Δ +0.017
 只印的標記（判讀母體；Δ 同一個方向定義）
      崩（回落四成）｜發股 G ≥ 10%：成立 78（0.654）／不成立 988（0.614）｜Δ +0.031
      籃子（12 個月平均超額）｜發股 G ≥ 10%：成立 78（-0.123）／不成立 988（-0.022）｜Δ +0.101
      崩（回落四成）｜波動（全市場百分位，上三分之一）：成立 342（0.792）／不成立 682（0.522）｜Δ +0.275
      籃子（12 個月平均超額）｜波動（全市場百分位，上三分之一）：成立 342（-0.058）／不成立 682（-0.013）｜Δ +0.041
      崩（回落四成）｜波動相對前 12 個月（上三分之一）：成立 324（0.716）／不成立 646（0.562）｜Δ +0.154
      籃子（12 個月平均超額）｜波動相對前 12 個月（上三分之一）：成立 324（-0.061）／不成立 646（-0.009）｜Δ +0.056
      崩（回落四成）｜年資不滿 36 個月：成立 60（0.667）／不成立 205（0.683）｜Δ -0.068
      籃子（12 個月平均超額）｜年資不滿 36 個月：成立 60（-0.077）／不成立 205（-0.018）｜Δ -0.012
      崩（回落四成）｜近三個月營收年增（上三分之一）：成立 293（0.645）／不成立 586（0.578）｜Δ +0.060
      籃子（12 個月平均超額）｜近三個月營收年增（上三分之一）：成立 293（-0.002）／不成立 586（-0.022）｜Δ -0.056
 交叉表（判讀母體）： {'I×A': Counter({(0, 0): 624, (0, 1): 315, (1, 0): 76, (1, 1): 39, (None, 0): 10, (0, None): 8, (1, None): 4, (None, 1): 2}), 'I×S': Counter({(0, 0): 634, (0, 1): 313, (1, 0): 74, (1, 1): 45, (None, 0): 10, (None, 1): 2}), 'A×S': Counter({(0, 0): 607, (1, 1): 249, (1, 0): 107, (0, 1): 103, (None, 1): 8, (None, 0): 4})}
  不加五年條件（重新偵測、沒有套事件側的旗標）         n 1159｜崩 0.619｜12 個月曾達 2 倍 0.126｜24 個月 0.206｜6 個月先跌三成 0.215｜12 個月超額 平均 -0.029 中位數 -0.190｜24 個月平均 -0.092｜單檔最大貢獻占總超額 總超額 ≤ 0
  不設底價（重新偵測、沒有套事件側的旗標）           n 1111｜崩 0.617｜12 個月曾達 2 倍 0.129｜24 個月 0.204｜6 個月先跌三成 0.217｜12 個月超額 平均 -0.028 中位數 -0.189｜24 個月平均 -0.111｜單檔最大貢獻占總超額 總超額 ≤ 0

最終判讀： {'崩（回落四成）｜I 發股': '不確定', '崩（回落四成）｜A 加速': '支持', '崩（回落四成）｜S 漲幅大小': '支持', '籃子（12 個月平均超額）｜I 發股': '不確定', '籃子（12 個月平均超額）｜A 加速': '不確定', '籃子（12 個月平均超額）｜S 漲幅大小': '不確定'}
已寫 docs\reports\phase7\h17-stage2-outcomes.csv sha256 eab510701b69f144
```

### context_baseline.py 的輸出（逐字）

```text
對照母體：2016-12～2024-10 每個月底、未還原收盤 ≥ 5 元的每一檔（含下市） 160012 個「檔×月」
  全部檔×月（每一列等權）                       n 160012｜崩 0.294｜12 個月曾達 2 倍 0.084｜24 個月 0.202｜6 個月先跌三成 0.066｜12 個月超額 平均 +0.002 中位數 -0.096｜12 個月後比 t 高的比例 0.572
  同月全市場（照事件的月份分布加權）                           ｜崩 0.316｜12 個月曾達 2 倍 0.085｜24 個月 0.188｜6 個月先跌三成 0.063｜12 個月超額 平均 +0.001｜12 個月後比 t 高的比例 0.547
  事件（判讀母體 1078）：崩 0.617｜12 個月曾達 2 倍 0.126｜24 個月 0.202｜6 個月先跌三成 0.214｜12 個月超額 平均 -0.023 中位數 -0.187｜12 個月後比 t 高的比例 0.433｜12 個月超額為正的比例 0.323
  事件的 12 個月報酬分位（10／25／50／75／90／95／99）： [-0.437, -0.284, -0.065, 0.279, 0.774, 1.347, 2.982]
  事件的 12 個月超額：為正的 348 筆合計 +221.6；最大的 10 筆占正的合計 0.19、最大的 54 筆（5%）占 0.55；為負的 730 筆合計 -246.5
  事件：崩 × 24 個月內曾達 2 倍 ＝ {(1, 0): 535, (0, 0): 325, (1, 1): 130, (0, 1): 88}
  A=1 S=1：n  249｜崩 0.827｜12 個月曾達 2 倍 0.124｜12 個月超額 平均 -0.063 中位數 -0.302
  A=1 S=0：n  107｜崩 0.738｜12 個月曾達 2 倍 0.150｜12 個月超額 平均 -0.108 中位數 -0.235
  A=0 S=1：n  103｜崩 0.583｜12 個月曾達 2 倍 0.078｜12 個月超額 平均 -0.061 中位數 -0.197
  A=0 S=0：n  607｜崩 0.511｜12 個月曾達 2 倍 0.133｜12 個月超額 平均 +0.018 中位數 -0.136
```
