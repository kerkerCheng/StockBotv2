# Phase 7 回放 — H16 乾跑報告（零結果）：大跌當時的標記算不算得出來、兩組各有幾筆

> 執行：2026-11-22（台北）。規格＝[`registration.md`](registration.md) 2026-11-22「H16 乾跑規格」（commit `df1b72b2`，早於任何標記的計算）；設計＝[第三版 §5.3](../../brainstorms/2026-11-21-playbook-replay-design-v3.md)。
> **這份報告沒有任何結果。** 沒有算、也沒有看任何事件在事件月（t）之後的價格。它只回答：事件有幾筆、標記算不算得出來、照機械規則選出哪個門檻、兩組各多少——給使用者簽判讀線用。
> 判讀線還沒登記。簽了才登記，登記的 commit 之後才算結果。
> 兩位乾淨 context 的唯讀審查者核過：沒有時間洩漏；第一位指出兩個要修的，已修；第二位核修正後的程式、舊劇本對照與本報告每一個數字（檔尾「複核」）。
> 它量在哪一層：追蹤表（基準率回放）。它不是買點、不是 filter、不改任何候選狀態（G10）。

## 一句話

事件 406 筆，四個標記都算得出來，照登記的機械規則各選出一個門檻，兩組都過 100 筆。但 **56% 的事件擠在七個月**（2015 夏、2018、2020-03 三次大跌），所以草稿判讀線有兩條在簽之前要你定：「不足」那一條照字面四個標記全過不了；「舊劇本的來源案例要剔除」那一條還沒寫成可以執行的字，而它怎麼寫會決定 M2 留不留得住。

## 要你定的兩件事

**① 「不足」那一條**

草稿：不足＝任一組 < 100，**或兩組都有 ≥ 5 筆的季不到 8 個**。乾跑：這樣的季只有 7／6／6／5 個（M1／M2／M3／M5）——照字面四個標記全是「不足」，照設計稿 §14 第 1 支就是不登記確認型、只交基準率表。

| 選項 | 寫法 | 後果 |
|---|---|---|
| **1A** | 照草稿字面 | 四個標記全「不足」；不登記確認型，只交表 A。標記對結果的任何數字都不印（印了就再也不能當確認型量） |
| **1B（建議）** | **放寬一處**：後半句改成「季內資訊量 W < 50」。**同時收緊三處**：①支持要「拿掉三次大跌裡的任何一次之後，差仍 ≥ 5 個百分點」（草稿只拿掉事件最多的一季）②M5 退出確認型、只印 ③p 的線仍照四個標記算（0.0125），不因 M5 退出而放寬。階段二的報告並列印一行「照草稿字面：全部不足」 | 確認型＝M1、M2、M3。量得出的差約 18–20 個百分點以上，量不出 10 |

- W 是什麼：每一季的「成立筆數 × 不成立筆數 ÷ 兩者相加」，逐季加總。兩組各 100 筆、不分季時 W 正好是 50——也就是把前半句已經簽過的「各 100」換算到分季比較上。乾跑的 W 在 §5、§8。
- 為什麼建議 1B：「8 個季」是我在看到事件有多擠之前寫的，它要的東西這份資料給不出來（有事件的 24 個季裡，事件數 ≥ 10 的只有 10 個）。事件總數落在設計稿 §5.1 的中情境（324）與高情境（540）之間——照 §5.1 自己的說法，這個量是「量得出 15–20 個百分點以上的差」，不是「全部不足」。
- 為什麼要同時收緊：這是看過兩組的大小之後，把一道會判「全部不足」的門改成會過，方向上是放寬（沒有看過任何結果，但看過事件數）。「8 個季」原本要擋的是「效果只來自一兩次崩跌」，W 量不到這件事，所以改由「拿掉任一次大跌都還在」來擋。M5 的值在同一個節點、同一個月裡完全相同（379 筆裡有 72 筆擠在 20 個這樣的群），名目的 W（照 2N2 剔除之後 52.0；不剔是 55.5）高估了它；拿掉任何一次大跌它都掉到 50 以下。
- 反方：這份資料實質上只有三次大跌。就算過了，判讀也只能寫成「在這三次裡」。若你不接受任何事後修改，1A 也完全合乎預先寫定的後果。

**② 「舊劇本的來源案例」怎麼剔**

草稿：「舊劇本清單各段對應的櫃買節點成員是這些標記的來源案例：從判讀線剔除，含它們的版本另印。」哪一段對哪個節點沒有寫。實際攤開櫃買的節點，比想像的粗：矽晶圓、記憶體、砷化鎵代工、八吋代工全在同一個 34 家的「IC/晶圓製造」；ABF 載板在 45 家的「硬板、軟板、IC載板製造」。三種寫法（對照表在 §8）：

| 選項 | 寫法 | 剔掉 | 剔完的成立／不成立（M1、M2、M3） | 後果 |
|---|---|---:|---|---|
| **2N1** | 節點成員的事件全剔（草稿字面） | 72 筆 | 109／187、**96**／172、109／221 | M2 的成立組不到 100 → 不足。確認型剩 M1、M3 |
| **2N2（建議）** | 節點成員、而且事件月落在那一段的期間內（起年 1 月到訖年次年 12 月）才剔 | 50 筆 | 118／199、103／184、115／237 | 三個都留；M2 的成立組 103，剛過線 |
| **2C** | 只剔各段的代表公司（39 家，名單在 §8） | 24 筆 | 124／217、112／201、121／257 | 三個都留 |

- 為什麼建議 2N2：剔除的目的是不拿「設計標記時腦子裡已經有的案例」來驗標記。一個案例是「某一段在它那幾年」——2015 年一檔電路板廠的事件不是「ABF 2019–2022」的案例，2N1 把它也剔掉，只損失樣本、不增加乾淨；2C 則把同一場崩跌裡的二線同業留在樣本裡，偏向支持。
- 反方：2N2 的期間規則是我現在才寫的，M2（103）只比線高 3 筆——所以三種寫法與「完全不剔」的版本階段二都會印，判讀只掛在你選的那一種上。這個選擇只用到事件數，沒有用到任何結果。

**其餘照草稿，不用你定**：檢定、支持與削弱的線、存活者的兩個界限、後果表——定稿文字在 §9。

## 計數

### 1. 事件：從偵測到母體

| 步驟 | 筆數 |
|---|---:|
| 第一次偵測（登記前；今天還在的公司；不限掛牌月份） | 501 |
| 照登記的母體規則，只用代號在交易所月底行情上出現的月份（興櫃時期的價不算）重偵測 | 425 |
| 照登記的文字，高點後超過 24 個月才跌破的不算（§7 ⑤） | 421 |
| 加下市公司（交易所月底收盤，照除權息與減資還原） | ＋34 → **455**（416 家） |
| 排除：建材營造（金融保險 0 筆） | −11 |
| 排除：t−1 月的去年同月營收 < 1,000 萬元 | −18 |
| 排除：存託憑證（不是普通股；§7 ⑦） | −5 |
| 排除後 | 421 |
| 交叉核對不上，剔除 | −5 |
| 下市事件標「未還原」，剔除（§3） | −10 |
| **母體** | **406**（372 家） |

- 交叉核（今天還在的 421 筆）：三個月底都有成交、可比 400；其中待核 32 → 照交易所的除權息與減資還原後對得上 27、對不上 5（剔除）。三個月底裡有一天沒成交、做不了的 21 筆照留（排除後剩 15；規格沒有定這種情況，階段二另印剔除版）。漲幅 ≥ 10 倍的 33 筆裡對不上的 0 筆。
- 查不到產業分類的 32 筆（照留）；查不到 t−1 月營收的 36 筆（照規格不排除，歸「標記不可算」）。
- 全部 455 筆的漲幅：3–5 倍 262、5–10 倍 153、10 倍以上 40。高點到 t 的月數：1–3 個月 73、4–6 個月 125、7–12 個月 154、13–24 個月 103。

### 2. 事件擠在哪

母體 406 筆落在 75 個月裡的 64 個月，月均 5.41。**成群月**（≥ 月均三倍，也就是 ≥ 17 筆）七個，共 227 筆（56%）：2015-06（17）、2015-07（36）、2015-08（21）、2018-04（18）、2018-09（36）、2018-10（75）、2020-03（24）。
**成群期**＝同一年內第一個成群月到最後一個成群月：2015-06～08（74 筆）、2018-04～10（161 筆）、2020-03（24 筆）。

- 2015：01 月 1、02 月 3、03 月 2、04 月 3、05 月 11、06 月 17、07 月 36、08 月 21、09 月 5、10 月 2、11 月 1、12 月 2
- 2016：01 月 3、03 月 1、04 月 2、05 月 4、06 月 3、07 月 1、08 月 3、09 月 1、10 月 6、11 月 4、12 月 1
- 2017：01 月 4、02 月 2、03 月 2、04 月 1、05 月 3、06 月 2、07 月 2、08 月 1、09 月 2、11 月 3、12 月 8
- 2018：01 月 2、02 月 4、03 月 6、04 月 18、05 月 9、06 月 7、07 月 5、08 月 11、09 月 36、10 月 75、11 月 2、12 月 2
- 2019：01 月 1、02 月 1、04 月 2、05 月 2、07 月 3、08 月 2、09 月 1、10 月 1、11 月 2、12 月 2
- 2020：01 月 2、02 月 5、03 月 24、07 月 1、10 月 4、11 月 4、12 月 3
- 2021：01 月 6

### 3. 下市公司

- 34 筆、34 家（t 在 2015 年 15 筆、2016 年 2、2017 年 1、2018 年 13、2019 年 1、2020 年 2）。4 筆是存託憑證（排除）；5 筆不在終止上市櫃名單上（3 筆是行情到 2021-03 都還在的存託憑證，2 筆是行情上消失、名單上沒有）。
- 還原：低點到 t 之間有除權息或減資的 25 筆，照交易所資料還原。**標「未還原」的 10 筆**：低點早於 2013-01、而且低點到 2012-12 之間它在上櫃——櫃買的減資資料從 2013-01 才有，中間有沒有減資查不到。照登記的規則列出、不進母體（裡面有一筆算出來「漲 109 倍」，多半就是漏掉的減資）。低點到 t 之間碰到被擋掉的因子列的 0 筆。
- 沒有第二個價格來源可以交叉核（今天還在的公司有）。
- 進母體的 20 筆的標記：季報改讀 MOPS 的 XBRL 財報檔（§7 ③），M2 算得出 14 筆、M3 18 筆、M4 1 筆。**月營收拿不到**（MOPS 個別查詢回「不繼續公開發行」；月營收歷史頁只有今天還在的公司；FinMind 對探針的兩家回空）——M1 全部不可算，M5 只有 4 筆。

### 4. 標記：可算率、各格點成立率、選出的門檻、兩組筆數

門檻照登記的規則機械選：取成立率最接近 37.5% 的那一格，平手取較嚴的。

| 標記 | 可算／母體 | 各格點的成立率 | 選出 | 成立 | 不成立 | 前段（～2017-12）成立／不成立 | 後段 | 兩組都有 ≥ 5 筆的季 |
|---|---|---|:-:|---:|---:|---|---|:-:|
| M1 營收動能轉弱 | 365／406（89.9%） | 5→58.4%、10→47.9%、**15→35.9%** | 15 | 131 | 234 | 61／82 | 70／152 | 7 |
| M2 存貨天數上升 | 335／406（82.5%） | **10→36.7%**、20→27.8%、30→20.0% | 10 | 123 | 212 | 53／81 | 70／131 | 6 |
| M3 毛利率走低 | 402／406（99.0%） | **2→30.8%**、3→24.9%、5→12.7% | 2 | 124 | 278 | 43／117 | 81／161 | 6 |
| M5 同節點廣度 | 379／406（93.3%） | 40→17.9%、**50→35.4%**、60→62.5% | 50 | 134 | 245 | 80／72 | 54／173 | 5 |

- **M2 過了進確認型的門**：可算率 82.5%（要 ≥ 60%）、兩組 123／212（各要 ≥ 100）。
- M1 與 M3 選到的都是格點的邊（M1 最嚴的一格、M3 最鬆的一格）；照規則不加格點。門檻不會因為這一輪的修正翻面：每個標記選出的那一格離 37.5% 都比鄰格近 5 個百分點以上。
- 四個標記都算得出來的事件 303 筆；至少一個算得出來 405；一個都算不出來 1。
- 標記之間幾乎互不相干（兩個都算得出來的事件裡，「兩個都成立」的筆數對「若互不相干」的期望）：M1×M2 28 對 41、M1×M3 40 對 39、M1×M5 52 對 46、M2×M3 33 對 35、M2×M5 51 對 41、M3×M5 35 對 40。

### 5. 逐季的兩組筆數與季內資訊量

粗體＝兩組都有 ≥ 5 筆的季。

| 季 | 事件 | M1 成立／不成立 | M2 | M3 | M5 |
|---|---:|---|---|---|---|
| 2015Q1 | 6 | 1／5 | 0／5 | 1／5 | 1／5 |
| 2015Q2 | 31 | **12／16** | **17／10** | **10／21** | **19／10** |
| 2015Q3 | 62 | **27／33** | **18／34** | **17／45** | **39／19** |
| 2015Q4 | 5 | 1／4 | 2／2 | 0／5 | 4／1 |
| 2016Q1 | 4 | 2／2 | 1／2 | 1／3 | 3／1 |
| 2016Q2 | 9 | 5／3 | 5／3 | 1／7 | 4／4 |
| 2016Q3 | 5 | 3／2 | 1／4 | 1／4 | 0／5 |
| 2016Q4 | 11 | 4／5 | 4／4 | **5／5** | 2／9 |
| 2017Q1 | 8 | 1／2 | 2／4 | 0／7 | 4／2 |
| 2017Q2 | 6 | 0／1 | 2／2 | 2／4 | 1／4 |
| 2017Q3 | 5 | 1／4 | 1／3 | 2／3 | 2／3 |
| 2017Q4 | 11 | 4／5 | 0／8 | 3／8 | 1／9 |
| 2018Q1 | 12 | **5／6** | 3／7 | 3／9 | 2／10 |
| 2018Q2 | 34 | **16／14** | **9／17** | **17／17** | **5／28** |
| 2018Q3 | 52 | **11／34** | **18／25** | **18／34** | 0／45 |
| 2018Q4 | 79 | **18／55** | **23／43** | **23／55** | **10／62** |
| 2019Q1 | 2 | 0／2 | 0／2 | 1／1 | 0／2 |
| 2019Q2 | 4 | 1／3 | 2／1 | 4／0 | 4／0 |
| 2019Q3 | 6 | 1／5 | 1／4 | 2／4 | 4／2 |
| 2019Q4 | 5 | 3／1 | 4／1 | 3／2 | 4／0 |
| 2020Q1 | 31 | **10／21** | **7／20** | 4／27 | **20／11** |
| 2020Q3 | 1 | 0／1 | 0／1 | 1／0 | 1／0 |
| 2020Q4 | 11 | 4／6 | 2／8 | 4／7 | 2／9 |
| 2021Q1 | 6 | 1／4 | 1／2 | 1／5 | 2／4 |
| 合計 | 406 | 131／234 | 123／212 | 124／278 | 134／245 |

| 標記 | 兩組都有至少 1 筆的季（有事件的 24 季裡） | W | 拿掉成群期之後的 W：2015 夏／2018／2020-03 | 量得出的最小差 |
|---|:-:|---:|---|---|
| M1 | 21 | 77.7 | 60.2／49.4／72.4 | 約 17 個百分點 |
| M2 | 20 | 70.6 | 56.7／39.3／67.0 | 約 18 |
| M3 | 20 | 78.2 | 63.2／42.5／75.6 | 約 17 |
| M5 | 18 | 55.5 | 40.2／42.6／49.8 | 約 21 |

- W＝Σ（成立 × 不成立 ÷ 兩者相加），逐季加總，是季內比較的權重和；兩組各 100 筆、不分季時 W＝50。這張表是剔除舊劇本來源案例**之前**的數；剔除之後的在 §8。
- 「量得出的最小差」＝單尾 0.0125、檢定力 80%、把比例的變異取到最大（0.25）時的粗估：3.08 × √(0.25 ÷ W)。**三個但書**：它假設事件互相獨立，實際上同一次大跌、同一個節點的事件結果相關，所以真正量得出的差比這個數大；它只算 p 過不過線，「支持」另外還有五個條件；0.0125 的前提是四個標記。同一個算法（W 取 70）：真實的差是 10 個百分點時 p 過線的機率約三成、15 約六成、20 約八成五；要過 p 的線，觀測到的差至少要約 13–15 個百分點——10 個百分點那條支持線實際上不會是卡住的那一條。
- **「削弱」在這份資料上判不出來**：削弱要兩組各 ≥ 150，四個標記的成立組都只有 123–134 筆。這一輪的結果只會是「支持」「不確定」或「不足」——量不到「沒有用」。
- M5 的成立率隨季大幅擺動（2018Q3 是 0／45、2015Q3 是 39／19）：它有一大半是「那一季的大環境」。它的值在同一個節點、同一個事件月裡完全相同：379 筆分成 300 個這樣的群，3 筆以上的群 20 個、涵蓋 72 筆，最大的群 6 筆。

### 6. 算不出來的原因（每一筆算不出來的事件都歸到一個原因；逐筆在階段一的標記表）

| 標記 | 算不出來 | 原因（筆數） |
|---|---:|---|
| M1 | 41 | 月營收頁查不到 29（進母體的下市 20 筆全在這裡）；六個月裡有去年同月沒有值或 < 1,000 萬元 12 |
| M2 | 71 | 存貨 < 資產總額 5%（規格不收）58；沒有存貨或資產總額那一列 9；資產負債表查無資料 2；單季營業成本算不出來或 ≤ 0 2 |
| M3 | 4 | 彙總表與財報檔都沒有這家（或不是一般業版型）2；前四季不齊或單季營收 ≤ 0 2 |
| M5 | 27 | 不在任何 ≥ 5 家的節點 23；節點裡算得出來的成員 < 5 家 4 |
| M4（只印） | 337 | 沒有合約負債這一列（2018 年以前沒有這個科目）279；前一季合約負債 < 單季營收 2% 49；前一季沒有數 7；資產負債表查無資料 2 |

### 7. 另印（都不進判讀）

- M1「近三個月平均年增 ≤ 0」：177／365。
- M3「比前八季最高低 ≥ 3 個百分點」：213／374（下市公司只抓四季財報檔，這一格沒算）。
- M4 合約負債季減 ≥ 20%：22／69。
- t 在三月的事件 35 筆（2020-03 占 24）；t 在 2020-03～2020-05（可能有延期申報）的 24 筆——階段二另印剔除版。

## 規格的套用與偏離（照實寫）

登記之後、這份報告之前動過的東西。**每一項動的時候都沒有任何結果可看**；看過的只有本報告印的這些計數。⑥–⑨ 是複核指出之後才改的。

| # | 動了什麼 | 為什麼 | 影響 |
|---|---|---|---|
| ① | 事件由 501 變 425（今天還在的公司） | 登記的母體是「交易所月底行情上的代號」；第一次偵測用的月線帶了公司掛牌前（興櫃）的價。照母體規則只用掛牌月份重偵測 | 漲幅 ≥ 10 倍的事件由 59 降到 33——興櫃時期的低價是主要來源 |
| ② | 三月事件的可知季，由年報改成去年第三季 | 登記寫「沿用 H12」又寫「1–2 月只用得到去年第三季」，兩句矛盾。H12 的規則是法定期限**嚴格早於**月底；年報期限 3/31 與三月底同一天。照 H12。腳本對每一筆加了兩條斷言（用到的那一季期限嚴格早於 t 的月底；而且是這樣的季裡最新的） | 母體裡 35 筆（2020-03 占 24）。改之前的 M2、M3 用的是當時還不一定看得到的年報 |
| ③ | 下市公司的季報改讀 MOPS 的 XBRL 財報檔（`t164sb01`） | 登記寫「下市公司的月營收與季報多半查不到」。使用者的指示是算不出來就去拿：個別查詢回「不繼續公開發行」，但同一份申報的財報檔還在。只補下市事件的公司，今天還在的公司照原路線 | 進母體的下市 20 筆裡 M2 可算 14、M3 可算 18。兩條路線的對照：機械抽 12 筆今天還在的事件，118 個數裡 117 個相同；不同的那一個是去年同季的累計毛利（財報檔的比較欄是重編後的數）——腳本先用每份報表自己的當期數，比較欄只補缺 |
| ④ | 多印了季內資訊量 W 與「量得出的最小差」 | 「兩組都有 ≥ 5 筆的季」數不出資料到底夠不夠 | 不改任何登記的東西；要不要拿 W 當線是上面第 ① 件事 |
| ⑤ | 高點後超過 24 個月才跌破的，不算事件 | 登記寫「三倍狀態在高點後 24 個月沒觸發就解除」；程式先判跌破、後判到期，第 25 個月才跌破的也收了。照登記的文字改；登記前那一次的偵測程式（`detect.py`，sha256 前 16 碼 `1c345cb2210c3c57`）沒有動，`stage_events.py` 仍斷言舊順序逐列重現它的 501 筆 | 今天還在的少 4 筆（425 → 421）、下市的少 1 筆 |
| ⑥ | 還原因子：拿掉「參考價÷前收要在 0.2 到 8 之間」這道過濾；同一筆重複列只算一次 | 這道過濾是我自己加的，規格沒有。它擋掉的 7 列都是真的（10:1 的減資、11.5:1 的配股）。交易所的減資表會把同一筆用兩個簡稱各列一次（5 列），拿掉過濾之後要去重 | 一筆下市事件原本是假的（配股沒還原、看起來像跌七成），現在是另一個月的真事件；一筆今天還在的事件原本被判「對不上」剔除，現在對得上、回到母體（對不上 6 → 5） |
| ⑦ | 補上「未還原」旗標（10 筆下市事件，剔除） | 登記要「還原不了的事件標未還原、列出、不進判讀線」，原本沒做 | §3 |
| ⑧ | 存託憑證排除（5 筆） | 登記的「四碼、非 00 開頭」照字面會收進 91 開頭的存託憑證；設計稿 §5.2 寫的是普通股，它們在 MOPS 也沒有財報。用交易所行情上的簡稱（結尾是 DR）認 | 母體少 5 筆 |
| ⑨ | 「月底無成交、交叉核做不了」的 15 筆照留 | 規格沒有定這種情況 | 階段二另印剔除版 |
| ⑩ | 終止上櫃日期的格式（不帶斜線的民國年月日）讀錯 | 程式錯 | 只影響下市事件的說明欄，不影響事件 |
| ⑪ | 舊劇本來源案例的節點對照（§8） | 草稿沒寫；它會動兩組的大小，所以放在簽之前 | 上面第 ② 件事 |

沒有動的：事件的門檻（三倍、0.6、36 個月、24 個月、12 個月歷史）、格點、機械選法、M2 的進場規則、M4 的地位。

## 8. 舊劇本來源案例的對照（要你定的第 ② 件事的細節）

事件期（2015-01～2021-03）裡有期間重疊的是清單的 #1–#9；#10–#12 在事件期之前，沒有東西要剔。節點＝櫃買產業價值鏈平台今天的名單。

| # | 段與期間 | 對到的節點（家數） | 節點成員的母體事件 | 其中事件月在期間內 | 代表公司（2C 用）與它們的事件數 |
|---|---|---|---:|---:|---|
| 1 | ABF 載板 2019–2022 | L610 硬板、軟板、IC載板製造（45）；D700 基板（11） | 13 | 5 | 欣興、南電、景碩（0） |
| 2 | 矽晶圓 2016–2019 | D300 IC/晶圓製造（34） | 24 | 21 | 環球晶、合晶、台勝科、中美晶、嘉晶（5） |
| 3 | 被動元件 MLCC 2017–2018 | J600 電容器（17）；J200 電容器材料（4） | 15 | 13 | 國巨、華新科、禾伸堂（3） |
| 4 | 記憶體 2016–2018 | F500 記憶體（17）；I300 記憶體（10）；D300 | 31 | 27 | 南亞科、華邦電、旺宏、威剛、群聯（7） |
| 5 | 5G 基地台板材 2019–2020 | L630 銅箔基板（18） | 5 | 1 | 台光電、聯茂、台燿（2） |
| 6 | 3D 感測雷射 2017–2018 | D300 | 24 | 19 | 穩懋、宏捷科、全新、聯亞（3） |
| 7 | 驅動 IC／八吋產能 2020–2022 | G900 驅動IC（4）；D300 | 24 | 0 | 聯詠、敦泰、天鈺、矽創、世界先進（0） |
| 8 | 挖礦顯示卡 2017–2018 與 2021 | FD00 顯示卡（11） | 8 | 6 | 技嘉、微星、撼訊、映泰、華擎（4） |
| 9 | mini-LED 2020–2021 | A230 光源/磊晶（13）；A240 封裝/模組（33）；G400 背光源（11） | 9 | 1 | 晶電、隆達、億光、聚積、惠特、富采（0） |
| | **聯集（一筆事件只算一次）** | | **72** | **50** | **24** |

- 期間內＝事件月落在那一段起年的 1 月到訖年次年的 12 月（事件期到 2021-03 為止）。回落四成的事件通常發生在那一段的尾巴或結束之後，所以往後多留一年。
- 對照是照節點名稱對的，不是照結果：驅動 IC 的設計公司在 105 家的「IC設計」節點，太寬，沒有納入（代表公司在母體裡也沒有事件）。
- 各寫法下的兩組筆數與 W（括號裡是 W；斜線後是三個成群期各拿掉一次之後最低的那個 W——M1、M2、M3 是拿掉 2018，M5 是拿掉 2015 夏）：

| 寫法 | 剩 | M1 成立／不成立（W／拿掉一個成群期後最低的 W） | M2 | M3 | M5 |
|---|---:|---|---|---|---|
| 完全不剔 | 406 | 131／234（77.7／49.4） | 123／212（70.6／39.3） | 124／278（78.2／42.5） | 134／245（55.5／40.2） |
| 2N1 節點全剔 | 334 | 109／187（63.2／43.1） | 96／172（54.3／34.3） | 109／221（65.8／38.1） | 114／194（48.9／35.1） |
| 2N2 節點、期間內 | 356 | 118／199（69.0／46.7） | 103／184（58.7／36.5） | 115／237（70.2／40.3） | 123／207（52.0／36.7） |
| 2C 代表公司 | 382 | 124／217（72.4／48.3） | 112／201（65.1／38.9） | 121／257（74.6／42.1） | 130／225（54.8／39.7） |

## 9. 判讀線定稿（待簽；簽了原文登記進 `registration.md`，登記的 commit 早於任何結果）

> **2026-11-22 使用者簽：1B、2N2（原話「H16 1B 2N2」；pq2 [943]）。** 定稿已登記進 [`registration.md`](registration.md)「2026-11-22｜H16 判讀線」那一筆，連同本節沒寫死的算法細節（結果窗、全市場等權的算法、分層與檢定的做法）。下面的文字不再動。

粗體是要你定的兩處，先照建議（1B、2N2）填。這是對設計稿 §5.3 草稿的**修訂**：改動的地方與看過什麼，登記時照寫。

1. **母體**：本報告的 406 筆。**判讀用的母體＝406 筆剔除舊劇本來源案例**：§8 對照表的節點成員、而且事件月在那一段的期間內（50 筆）→ 356 筆。階段一 commit 的事件表與標記表只含 t 當時已知的欄（公司後來有沒有下市、哪一天終止，不在表上），附 digest。
2. **確認型標記與門檻（凍結）**：M1 G＝15、M2 G＝10、M3 G＝2；成立＝「壞」。**M5（G＝50）與 M4 只印，不判。**
3. **結果**（階段二才算）：主量＝t 起 18 個月內月收盤曾 ≥ 事件前高點（那段漲勢的最高月收盤，與事件偵測同一個還原口徑）。並列兩個量：①18 個月內月收盤曾達 t 收盤的 1.67 倍；②t 起 12 個月的報酬減同期全市場等權報酬，取平均。四個基線必印：回落深度、漲幅倍數、高點到 t 的月數、大盤同期回落。
4. **檢定**：事件季內打亂「成立／不成立」標籤的排列檢定，10,000 次，種子 20261122。效果量 Δ＝季內「不成立組回到前高的比例 − 成立組的比例」的加權平均，權重＝成立 × 不成立 ÷ 兩者相加（Mantel–Haenszel）。預期方向 Δ > 0。單尾 p ≤ 0.05 ÷ 4＝**0.0125（照四個標記算，不因 M5 退出而放寬）**。區間＝以事件月為抽樣單位的 bootstrap（2,000 次，同一個種子），取 2.5 與 97.5 百分位。不分季合併算的版本只當對照印。
5. **判讀**（M1、M2、M3 各判）：
   - **支持**：Δ ≥ 10 個百分點；p 過線；**拿掉三個成群期（2015-06～08、2018-04～10、2020-03）裡的任何一個之後，Δ 仍 ≥ 5 個百分點**（這一條擋的是「拿掉某一次大跌，差就翻向或縮到沒有」，不是另一道顯著性檢定——拿掉 2018 之後 W 只剩 37–47）；前後兩段（2015-01～2017-12、2018-01～2021-03）各組 ≥ 30 筆而且 Δ 同向；兩個並列量同向；依回落深度三分位再分層之後 Δ 仍 > 0。
   - **削弱**：兩組各 ≥ 150，而且 Δ 的 95% 區間上界 < 10 個百分點。（乾跑：成立組都不到 150，這一輪判不出削弱。）
   - **不足**：任一組 < 100，**或季內資訊量 W < 50**。（乾跑：M1 69.0、M2 58.7、M3 70.2，都過；M2 的成立組 103 筆。）
   - 其餘＝**不確定**。
   - 存活者：結果窗內下市的事件，全當沒回到、全當回到各判一次；判讀翻面就寫「不確定（存活者）」。
   - **並列印一行**：照草稿字面（兩組都有 ≥ 5 筆的季要 8 個）的結論——全部不足。
6. **另印（不進判讀）**：完全不剔、2N1、2C 三種母體；M5 的全部數字；剔除 t 在 2020-03～2020-05 的版本；剔除交叉核做不了的 15 筆的版本；把 10 筆未還原的下市事件與 5 筆存託憑證放回去的版本；標記算不出來的事件的結果率（可算率 × 結果組）；M1「近三個月平均 ≤ 0」、M3「對前八季最高」、M4；M1 在 2008–2014 的複製（月營收抓得到才做，抓不到寫量不到）——方向與本判讀相反時，M1 的判讀降為不確定。
7. **後果**：照設計稿 §5.3 的後果表，一字不改。只進假說帳，不改任何 filter、候選狀態、排序。
8. **不改的**：登記之後，上面每一項都不再動；要更正只能在那一筆之後追加，並寫明是在看任何結果之前還是之後。

## 偏差標註

登記那一筆的 ①–⑥ 照舊（節點名單與產業分類是今天的版本；事後更正的財報認不出來；去年同季的成本與存貨是混版；2020 年可能延期申報；下市公司缺資料可能與結果相關；事件偵測先於登記跑過一次）。這份報告新增：

7. 事件高度集中在三次大跌；任何判讀都只在「這三次」裡成立，下一次是不是同一種，這份資料答不出來。
8. 下市公司的 M1 全部不可算——M1 的判讀實質上只涵蓋今天還在的公司。
9. 下市公司的價格只有交易所一個來源；10 筆因為查不到 2013 年以前的上櫃減資而剔除——被剔掉的是下市公司，方向上偏向倖存者。
10. 交叉核做不了的 15 筆（三個月底裡有一天沒成交）留在母體。
11. 舊劇本的節點對照、期間規則、「W ≥ 50」與 M5 退出確認型，都是看了事件數之後才寫的；沒有看過任何結果。
12. 同一次大跌、同一個節點的事件結果彼此相關，名目的 W 高估了資訊量。
13. 沒有核的：轉上市的公司在還原月線上有沒有被截掉早期歷史（會少偵測事件，不會多）；2020 年延期申報實際影響了哪幾家。

## 複核

### 2026-11-22｜第一位（乾淨 context、唯讀）：CONDITIONAL_GO——條件已落字

範圍：腳本有沒有照登記的乾跑規格做、有沒有用到 t 之後的東西、「不足」那一條的改法站不站得住。它原樣重跑 `stage_events.py`、`markers.py`（輸出逐位元相同）、全量獨立重算 M1 與 M3（0 筆不同）、獨立重寫可知季（全部相同）、手算 6 筆事件的標記。沒有讀任何 t 之後的價格。

**結論：沒有找到時間洩漏。** 每個取值點（月營收到 t−1、季報到可知季、比較欄、單季相減）逐條核過；下市公司還原時乘上 t 之後的因子，對 t 之前所有月份是同一個倍數，比值不變。

| # | 等級 | 指出的事 | 處置 |
|---|---|---|---|
| R-1 | BLOCKING | 還原因子有一道規格沒有的過濾（比值 0.2–8），擋掉的 7 列都是真的大型減資或配股，造成一筆假事件、一筆誤剔 | 採納：拿掉過濾、只擋缺值與 ≤ 0、重複列去重（偏離 ⑥）。兩筆都核過 |
| R-2 | BLOCKING | 規格要的「未還原」旗標沒做；低點早於 2013-01 的上櫃下市事件無從確認 | 採納：機械旗標，10 筆剔除（偏離 ⑦；它估的是 12 筆，照「低點到 2012-12 之間在上櫃」逐月認是 10 筆） |
| R-3 | NOTE | 「月底無成交」的 15 筆沒做交叉核就照留，規格沒定義 | 採納：列為偏離 ⑨，階段二另印剔除版 |
| R-4 | NOTE | 程式先判跌破、後判到期，第 25 個月才跌破仍算事件（5 筆） | 採納，而且比它建議的多做一步：照登記的文字改順序（偏離 ⑤），不只列偏差 |
| R-5 | NOTE | 「四碼、非 00 開頭」會收進存託憑證（5 筆） | 採納：排除（偏離 ⑧） |
| R-6 | NOTE | 事件檔帶著 t 之後才知道的欄（終止日、最後出現月、來源欄透露今天還在不在）；標記計算沒有用到 | 採納：寫進判讀線第 1 條——階段一 commit 的表不含這些欄 |
| R-7 | NOTE | 規格要印每月事件數，程式只印成群月 | 採納：§2 |
| R-8 | NOTE | M5 的值在同一節點同一個月完全相同，名目 W 高估 | 採納：M5 退出確認型（要你定的第 ① 件事）、偏差標註 12 |

對「不足」那一條的四個問題：
- (a) W 的算法與「兩組各 100＝W 50」的等值——對。限制：同節點、同一次大跌的事件結果相關，名目 W 高估。
- (b) 算不算自利的事後調整——照程序不算違規（判讀線本來就排在乾跑之後簽、乾跑不含結果），但方向上是放寬：要當修訂登記、寫明看過什麼、並列印照字面的結論，而且同一次修訂要補收緊（放行與收緊同時發生）。→ 採納：1B 的三處收緊與並列那一行。
- (c) 更站得住的寫法——「8 個季」要擋的是效果只來自少數幾次崩跌，W 量不到；改成「拿掉任一成群期後仍 ≥ 5 個百分點且同向」。照字面判全部不足也合乎預先寫定的後果，這是使用者的選擇。→ 採納：兩個選項都留給使用者。
- (d) 「量得出的最小差」的式子——對；要標明假設獨立、只算 p 線、α 的前提。→ 採納：§5 的三個但書。

它標「未核」的：兩檔大型減資被擋之後有沒有影響其他月份（修正後已照用）；轉上市的公司有沒有被截掉早期歷史（偏差標註 13）；缺價有沒有分清限流與真的沒有（抓取當時核過：1,769 檔有價、157 檔缺、沒有限流）；2020 年延期申報的實際影響（偏差標註 13）。

### 2026-11-22｜第二位（乾淨 context、唯讀、窄範圍）：GO——三條註記已落字

範圍：第一位之後才改的四處程式、全新的 `oldplaybook.py`、本報告正文每一個數字對不對得上腳本輸出。它沒有重跑任何會寫檔的腳本，沒有讀任何價格。

- **四處改動都改對**：還原因子只擋缺值與 ≤ 0，去重的鍵沒有誤併不同事件（重複的 5 列前收與參考價逐項相同；同代號同日跨種類 0 筆），還原方向對；到期順序對，事件檔裡高點到 t 超過 24 個月的 0 筆；未還原 10 筆、存託憑證 5 筆，代號 91 開頭而沒標到的 0 筆；照母體定義數出來 406 筆、372 家。
- **`oldplaybook.py` 沒有用到任何 t 之後的資料**；三種剔除集合與 §8 的文字一致；它用標記檔獨立重算四種母體下各標記的兩組筆數與 W，全部相同。
- **報告的數字逐節核過**，對不上的只有一處：

| # | 等級 | 指出的事 | 處置 |
|---|---|---|---|
| N-1 | NOTE | 代表公司寫 37 家，實際是 39 家（事件數 24 沒錯） | 已改 |
| N-2 | NOTE | 「M5 名目的 W（52）」沒標是剔除之後的數，與 §5 的 55.5 並排會以為矛盾 | 已補 |
| N-3 | NOTE | 「拿掉任一成群期仍 ≥ 5 個百分點」在拿掉 2018 之後 W 只剩 37–47，這一條擋方向翻轉、擋不了雜訊，文字沒講 | 已在 §9 那一條補一句 |

它標「未核」的（找不到來源，不是不存在）：偏離 ⑥ 那一筆由假變真的下市事件是哪一筆（主 session 核過：配股 11.5 比 1 沒還原時看起來像單月跌七成；還原之後是配股後單月急漲、次月急跌，事件月往後一個月）；到期順序少掉的 4 筆是不是正好是第 25 個月才跌破的那幾筆（它只核了差額）；轉上市的公司有沒有被截掉早期歷史（偏差標註 13）。

**兩位審查者都沒有看過、也不需要看的**：任何事件在 t 之後的價格。

## 腳本（逐字）

資料與腳本在 `library/private/measurement/h16_cache/`（不進版控）。抓取腳本的 User-Agent 都是寫死的通用字串，請求不帶任何個人資訊。

### 計算

#### h16lib.py（sha256 前 16 碼 `56c0fcf385f36d6b`）

```python
"""H16 乾跑共用：月份換算、事件偵測（邏輯與 detect.py 逐行相同，stage_events.py 會斷言重現 events.json）、可知季。"""
MULT, LOOKBACK, DROP, EXPIRE, MIN_HIST = 3.0, 36, 0.6, 24, 12
EVENT_FROM, EVENT_TO = "2015-01", "2021-03"


def mnum(ym):
    y, m = map(int, ym.split("-"))
    return y * 12 + m - 1


def ym_of(n):
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def detect_series(code, s, strict_expiry=True):
    """s＝[(ym, 收盤)]（已排序、收盤 > 0）。回事件列表；每列只含 ≤ t 的東西。
    strict_expiry＝True（正式用）：照登記的文字，高點後超過 24 個月就解除，那個月才跌破不算事件。
    strict_expiry＝False：detect.py 當初的順序（先判跌破、後判到期），只用來斷言重現登記前那一次的 501 筆。"""
    out = []
    if len(s) <= MIN_HIST:
        return out
    mn = [mnum(ym) for ym, _ in s]
    cl = [v for _, v in s]
    state, prev_high = None, None
    for i in range(MIN_HIST, len(s)):
        if state is None:
            win = [k for k in range(i) if mn[i] - mn[k] <= LOOKBACK]
            if not win:
                continue
            lo = min(win, key=lambda k: cl[k])
            hi = max(range(lo, i + 1), key=lambda k: cl[k])
            if cl[hi] >= MULT * cl[lo] and mn[i] - mn[hi] <= EXPIRE and (prev_high is None or cl[hi] > prev_high):
                state = {"lo": lo, "hi": hi, "entry": i}
            else:
                continue
        if cl[i] > cl[state["hi"]]:
            state["hi"] = i
        elif strict_expiry and mn[i] - mn[state["hi"]] > EXPIRE:
            state = None
        elif cl[i] <= DROP * cl[state["hi"]]:
            lo, hi = state["lo"], state["hi"]
            if EVENT_FROM <= s[i][0] <= EVENT_TO:
                assert s[lo][0] <= s[hi][0] < s[i][0]
                out.append({"code": code, "low_ym": s[lo][0], "low_px": round(cl[lo], 4), "high_ym": s[hi][0],
                            "high_px": round(cl[hi], 4), "t_ym": s[i][0], "t_px": round(cl[i], 4),
                            "runup": round(cl[hi] / cl[lo], 2), "depth": round(cl[i] / cl[hi], 3),
                            "months_high_to_t": mn[i] - mn[hi]})
            prev_high = cl[hi]
            state = None
        elif mn[i] - mn[state["hi"]] > EXPIRE:
            state = None
    return out


def known_quarter(ym):
    """法定期限**嚴格早於** t 當月底的最近一季（H12 的規則；Q1 5/15、Q2 8/14、Q3 11/14、年報 3/31）。
    年報期限 3/31 與三月底同一天，所以三月還用不到年報：1–3 月用去年第三季。"""
    y, m = map(int, ym.split("-"))
    if m >= 11:
        return y, 3
    if m >= 8:
        return y, 2
    if m >= 5:
        return y, 1
    if m >= 4:
        return y - 1, 4
    return y - 1, 3


def in_pop(r):
    """母體＝沒被排除（建材營造、金融保險、基期太小、存託憑證），而且交叉核沒有對不上、不是還原不了的下市事件。"""
    return not r["excluded"] and r["xcheck"] not in ("對不上", "未還原")


def deadline(y, q):
    """一般業的法定申報期限（上界，不是實際公告日），回 'YYYY-MM-DD'。"""
    return {1: "%04d-05-15" % y, 2: "%04d-08-14" % y, 3: "%04d-11-14" % y, 4: "%04d-03-31" % (y + 1)}[q]


def month_end(ym):
    y, m = map(int, ym.split("-"))
    last = 31 if m in (1, 3, 5, 7, 8, 10, 12) else 30 if m != 2 else (29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28)
    return "%04d-%02d-%02d" % (y, m, last)


def qshift(y, q, k):
    n = y * 4 + (q - 1) + k
    return n // 4, n % 4 + 1
```

#### official.py（sha256 前 16 碼 `b1085e87eaa70a09`）

```python
"""交易所月底行情的解析（上市 MI_INDEX、上櫃每日收盤行情）→ {代號: (名稱, 收盤價或 None)}。只收四碼、非 00 開頭的代號（普通股）。"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
OFF = HERE / "official"
CODE = re.compile(r"^(?!00)\d{4}$")


def _num(s):
    s = re.sub(r"<[^>]+>", "", str(s)).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def load(market, ymd):
    """market ∈ twse／tpex；ymd＝YYYYMMDD。回 dict。"""
    o = json.loads((OFF / f"{market}_{ymd}.json").read_text(encoding="utf-8"))
    out = {}
    for t in o.get("tables") or []:
        f = t.get("fields") or []
        ci = next((i for i, x in enumerate(f) if x in ("證券代號", "代號")), None)
        ni = next((i for i, x in enumerate(f) if x in ("證券名稱", "名稱")), None)
        pi = next((i for i, x in enumerate(f) if x in ("收盤價", "收盤")), None)
        if ci is None or pi is None:
            continue
        for r in t.get("data") or []:
            code = str(r[ci]).strip()
            if CODE.match(code):
                out[code] = (str(r[ni]).strip() if ni is not None else "", _num(r[pi]))
    return out


def month_ends():
    return json.loads((HERE / "month_ends.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    import sys
    ymd = sys.argv[1] if len(sys.argv) > 1 else "20141128"
    tw, tp = load("twse", ymd), load("tpex", ymd)
    print(ymd, "上市", len(tw), "上櫃", len(tp), "無收盤價的", sum(v[1] is None for v in {**tw, **tp}.values()))
    rev = HERE.parent / "dryrun" / "rev"
    ym = f"{ymd[:4]}-{ymd[4:6]}"
    page = set()
    for m in ("twse", "tpex"):
        page |= {r["company_code"] for r in json.loads((rev / f"rev_{m}_{ym}.json").read_text(encoding="utf-8")) if r.get("company_code")}
    page = {c for c in page if CODE.match(c)}
    exch = set(tw) | set(tp)
    print("交易所當天有掛牌", len(exch), "｜月營收頁（同月）", len(page), "｜交易所有、頁上沒有", len(exch - page), "｜頁上有、交易所沒有", len(page - exch))
    print("交易所有、頁上沒有（前 12）：", [(c, ({**tw, **tp})[c][0]) for c in sorted(exch - page)[:12]])
```

#### adjust.py（sha256 前 16 碼 `c31f284fd1ae18ce`）

```python
"""交易所的除權息計算結果表與減資恢復買賣參考價 → 每個代號的還原因子；把未還原的月底收盤還原成可比的序列。
因子＝參考價 ÷ 前一交易日收盤；月底收盤要乘上「日期晚於那個月底」的所有因子（往回還原）。"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
OFF = HERE / "official"


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


def _num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return None


def load_factors():
    """回 ({代號: [(日期, 因子, 種類)]}, 統計, 擋掉的列 [(代號, 日期或 None, 種類)])。
    只擋缺值與前收或參考價 ≤ 0 的列——比值多大都照用（10:1 的減資、11.5:1 的配股都是真的）。
    同一代號同一天同一種類的重複列只算一次（交易所的減資表會把同一筆用兩個簡稱各列一次）。"""
    fac, stat, blocked, seen = {}, {"除權息": 0, "減資": 0, "重複列": 0, "擋掉（缺值或 ≤ 0）": 0, "比值在 0.2–8 之外（照用）": 0}, [], set()
    files = [(f, "除權息") for f in sorted(OFF.glob("*_exright_*.json"))] + [(f, "減資") for f in sorted(OFF.glob("*_reduction_*.json"))]
    for f, kind in files:
        o = json.loads(f.read_text(encoding="utf-8"))
        data = o.get("data") or ((o.get("tables") or [{}])[0].get("data")) or []
        for r in data:
            date, code, prev, ref = roc_date(r[0]), str(r[1]).strip(), _num(r[3]), _num(r[4])
            if not date or not prev or not ref or prev <= 0 or ref <= 0:
                stat["擋掉（缺值或 ≤ 0）"] += 1
                blocked.append((code, date, kind))
                continue
            if (code, date, kind) in seen:
                stat["重複列"] += 1
                continue
            seen.add((code, date, kind))
            fac.setdefault(code, []).append((date, ref / prev, kind))
            stat[kind] += 1
            stat["比值在 0.2–8 之外（照用）"] += not (0.2 <= ref / prev <= 8)
    for v in fac.values():
        v.sort()
    return fac, stat, blocked


def adjusted(series, month_end_date, factors):
    """series＝{ym: 未還原收盤}；month_end_date＝{ym: 'YYYY-MM-DD'}；factors＝[(日期, 因子, 種類)]。回 [(ym, 還原收盤)]。"""
    out = []
    for ym in sorted(series):
        d = month_end_date[ym]
        k = 1.0
        for date, f, _ in factors:
            if date > d:
                k *= f
        out.append((ym, series[ym] * k))
    return out
```

#### stage_events.py（sha256 前 16 碼 `e17a30b10aeedb6e`）

```python
"""H16 乾跑：母體（交易所月底行情）、下市公司的事件、交叉核。只用 ≤ t 的月收盤；不算任何 t 之後的東西。
輸出 events_all.json（今天還在的＋下市的；每列帶旗標）與摘要。規格：registration.md 2026-11-22「H16 乾跑規格」。"""
import json
import re
from collections import Counter
from pathlib import Path

import adjust
import official
from h16lib import EVENT_TO, detect_series, mnum

HERE = Path(__file__).parent
px = json.loads((HERE / "px.json").read_text(encoding="utf-8"))
uni = json.loads((HERE / "universe.json").read_text(encoding="utf-8"))

# ---------- 交易所月底行情 → 每個代號的未還原月收盤 ----------
series, names, last_seen, listed, tpex_months = {}, {}, {}, {}, {}
for d in official.month_ends():
    ym, ymd = d[:7], d.replace("-", "")
    for market in ("twse", "tpex"):
        for code, (name, close) in official.load(market, ymd).items():
            names[code] = name
            listed.setdefault(code, set()).add(ym)
            if market == "tpex":
                tpex_months.setdefault(code, set()).add(ym)
            last_seen[code] = max(last_seen.get(code, ""), ym)
            if close and close > 0:
                series.setdefault(code, {})[ym] = close
# ---------- 今天還在的：重現 events.json（偵測邏輯搬進 h16lib 之後的一致性斷言） ----------
by_code = {}
for t, rows in px.items():
    code = t.split(".")[0]
    if code not in by_code or len(rows) > len(px[by_code[code]]):
        by_code[code] = t
surv = []
for code, t in sorted(by_code.items()):
    s = [(ym, v) for ym, v in px[t] if v and v > 0 and ym <= EVENT_TO]
    for e in detect_series(code, s, strict_expiry=False):
        e.update({"ticker": t, "name": uni.get(t, {}).get("name", ""), "source": "yfinance 還原"})
        surv.append(e)
old = json.loads((HERE / "events.json").read_text(encoding="utf-8"))
key = lambda e: (e["code"], e["t_ym"], e["low_ym"], e["high_ym"])  # noqa: E731
assert sorted(map(key, surv)) == sorted(map(key, old)), "h16lib 的偵測與 detect.py 不一致"
print("今天還在的（不限掛牌月份）：事件", len(surv), "（與 events.json 逐列相同）")
# 母體規則：只用代號在交易所月底行情上出現的月份（興櫃時期的價不算）
surv_all, surv, loose = surv, [], 0
for code, t in sorted(by_code.items()):
    s = [(ym, v) for ym, v in px[t] if v and v > 0 and ym <= EVENT_TO and ym in listed.get(code, ())]
    loose += len(detect_series(code, s, strict_expiry=False))
    for e in detect_series(code, s):
        e.update({"ticker": t, "name": uni.get(t, {}).get("name", ""), "source": "yfinance 還原"})
        surv.append(e)
same = len(set(map(key, surv)) & set(map(key, surv_all)))
print("今天還在的（只用掛牌月份）：事件", len(surv), "｜相異公司", len({e["code"] for e in surv}), "｜與不限版逐列相同的", same,
      "｜不限版有、這版沒有", len(surv_all) - same, "｜這版新出現", len(surv) - same)
print("  其中因為「高點後超過 24 個月才跌破」照登記的文字不算事件而少掉的：", loose - len(surv), "（先判跌破的舊順序是", loose, "筆）")
print("交易所月底行情上出現過的代號", len(names), "｜有還原月線的", len(set(names) & set(by_code)), "｜沒有的", len(set(names) - set(by_code)))

# ---------- 終止上市櫃名單 ----------
delisted = {}
tw = json.loads((HERE / "official" / "twse_delisted_all.json").read_text(encoding="utf-8"))
for date, name, code in tw["data"]:
    y, m, d = date.split("/")
    delisted[str(code).strip()] = {"date": "%04d-%s-%s" % (int(y) + 1911, m, d), "name": name, "board": "上市", "reason": ""}
for f in sorted((HERE / "official").glob("tpex_delisted_2*.json")):
    o = json.loads(f.read_text(encoding="utf-8"))
    for t in o.get("tables") or []:
        fl = t.get("fields") or []
        ci, ni, di, ri = (fl.index(x) for x in ("股票代號", "公司名稱", "終止上櫃日期", "終止上櫃原因"))
        for r in t.get("data") or []:
            code = str(r[ci]).strip()
            ds = re.sub(r"[^\d/]", "", str(r[di]))
            parts = ds.split("/")
            if len(parts) != 3 and len(ds) in (6, 7):      # 櫃買的日期是不帶斜線的民國年月日（991230、1040716）
                parts = [ds[:-4], ds[-4:-2], ds[-2:]]
            date = "%04d-%s-%s" % (int(parts[0]) + (1911 if int(parts[0]) < 1911 else 0), parts[1], parts[2]) if len(parts) == 3 else ds
            if code not in delisted or date > delisted[code]["date"]:
                delisted[code] = {"date": date, "name": str(r[ni]).strip(), "board": "上櫃", "reason": str(r[ri]).strip()}
gone = sorted(set(names) - set(by_code))
print("沒有還原月線的代號裡，在終止上市櫃名單上的", sum(c in delisted for c in gone), "／", len(gone))

# ---------- 還原因子 ----------
FAC, fstat, BLOCKED = adjust.load_factors()
ME = {d[:7]: d for d in official.month_ends()}
print("還原因子：", fstat, "｜有因子的代號", len(FAC), "｜擋掉的列", BLOCKED)

# ---------- 下市公司：用交易所月底收盤、照除權息與減資還原之後偵測 ----------
dele, loose_d = [], 0
for code in gone:
    raw = series.get(code, {})
    s = adjust.adjusted(raw, ME, FAC.get(code, []))
    loose_d += len(detect_series(code, s, strict_expiry=False))
    for e in detect_series(code, s):
        acts = [(d, round(f, 3), k) for d, f, k in FAC.get(code, []) if e["low_ym"] <= d[:7] <= e["t_ym"]]
        info = delisted.get(code, {})
        e.update({"ticker": None, "name": names.get(code, ""), "source": "交易所月底收盤（照除權息與減資還原）", "last_seen": last_seen.get(code),
                  "delisted": info.get("date"), "delist_board": info.get("board"), "delist_reason": info.get("reason"),
                  "corp_actions_low_to_t": acts})
        # 還原不了的（登記：標「未還原」、列出、不進判讀線）：①低點到 t 之間有被擋掉的因子列；
        # ②低點早於 2013-01、而且低點到 2012-12 之間它在上櫃——櫃買的減資資料 2013-01 才開始，中間有沒有減資查不到。
        why = []
        if any(c == code and (d is None or e["low_ym"] <= d[:7] <= e["t_ym"]) for c, d, _ in BLOCKED):
            why.append("低點到 t 之間有被擋掉的因子列")
        if e["low_ym"] < "2013-01" and any(e["low_ym"] <= m <= "2012-12" for m in tpex_months.get(code, ())):
            why.append("低點早於上櫃減資資料的起點（2013-01）")
        e["unadjusted_why"] = why
        dele.append(e)
print("下市公司（照交易所資料還原）：事件", len(dele), "（先判跌破的舊順序是", loose_d, "筆）｜相異公司", len({e["code"] for e in dele}),
      "｜低點到 t 之間有除權息或減資的", sum(bool(e["corp_actions_low_to_t"]) for e in dele))
print("  依年：", dict(sorted(Counter(e["t_ym"][:4] for e in dele).items())))
print("今天還在的依年：", dict(sorted(Counter(e["t_ym"][:4] for e in surv).items())))
print("  終止原因（上櫃才有）：", Counter((e["delist_reason"] or "（上市或不在名單）")[:12] for e in dele).most_common(8))

# ---------- 交叉核：還原比值對未還原比值 ----------
n_check = n_flag = n_missing = 0
for e in surv:
    off = series.get(e["code"], {})
    lo, hi, tt = off.get(e["low_ym"]), off.get(e["high_ym"]), off.get(e["t_ym"])
    if not (lo and hi and tt):
        e["xcheck"] = "月底無成交"
        n_missing += 1
        continue
    n_check += 1
    r_run, r_dep = hi / lo, tt / hi
    e["official_runup"], e["official_depth"] = round(r_run, 2), round(r_dep, 3)
    bad_run = not (2 / 3 <= r_run / (e["high_px"] / e["low_px"]) <= 1.5)
    bad_dep = abs(r_dep - e["t_px"] / e["high_px"]) > 0.10
    e["xcheck"] = "待核" if (bad_run or bad_dep) else "相符"
    n_flag += e["xcheck"] == "待核"
    if e["xcheck"] == "待核":
        adj = dict(adjust.adjusted(off, ME, FAC.get(e["code"], [])))
        a_run, a_dep = adj[e["high_ym"]] / adj[e["low_ym"]], adj[e["t_ym"]] / adj[e["high_ym"]]
        e["official_adj_runup"], e["official_adj_depth"] = round(a_run, 2), round(a_dep, 3)
        ok = (2 / 3 <= a_run / (e["high_px"] / e["low_px"]) <= 1.5) and abs(a_dep - e["t_px"] / e["high_px"]) <= 0.10
        e["xcheck"] = "相符（除權息或減資對得上）" if ok else "對不上"
print("交叉核：可比", n_check, "｜待核", n_flag, "｜三個月底裡有無成交的", n_missing)
flag = [e for e in surv if e["xcheck"] in ("相符（除權息或減資對得上）", "對不上")]
print("  待核 →", dict(Counter(e["xcheck"] for e in flag)))
print("  漲幅 ≥ 10 倍的事件", sum(e["runup"] >= 10 for e in surv), "｜其中對不上的", sum(e["runup"] >= 10 and e["xcheck"] == "對不上" for e in surv))
print("  待核依年：", dict(sorted(Counter(e["t_ym"][:4] for e in flag).items())))
for e in [x for x in flag if x["xcheck"] == "對不上"]:
    print("   對不上", e["code"], e["low_ym"], e["high_ym"], e["t_ym"], "yfinance", e["runup"], e["depth"], "交易所未還原", e["official_runup"], e["official_depth"], "交易所還原", e["official_adj_runup"], e["official_adj_depth"])

for e in dele:
    e["xcheck"] = "未還原" if e["unadjusted_why"] else "下市（交易所還原）"
print("下市事件裡標「未還原」的", sum(e["xcheck"] == "未還原" for e in dele), dict(Counter(w for e in dele for w in e["unadjusted_why"])))
allev = surv + dele
for e in allev:                      # 存託憑證不是普通股（設計稿 §5.2）：用交易所行情上的簡稱認
    e["dr"] = names.get(e["code"], "").endswith("DR")
print("存託憑證的事件", sorted((e["code"], e["t_ym"]) for e in allev if e["dr"]))
(HERE / "events_all.json").write_text(json.dumps(allev, ensure_ascii=False), encoding="utf-8")
assert all(mnum(e["t_ym"]) > mnum(e["high_ym"]) >= mnum(e["low_ym"]) for e in allev)
print("寫出 events_all.json：", len(allev))
```

#### xbrl.py（sha256 前 16 碼 `7f75423a25fb29be`）

```python
"""MOPS 的 XBRL 財報檔（t164sb01）→ 資產負債表三列與損益表的累計營收、累計毛利。
下市公司的個別查詢回「不繼續公開發行」，但這個入口還拿得到同一份申報。只解析、不對外。"""
import re
from pathlib import Path

HERE = Path(__file__).parent
DIR = HERE / "xbrl"
DATE = re.compile(r"(\d{4})年(\d{2})月(\d{2})日")
PERIOD = re.compile(r"(\d{4})年(\d{2})月(\d{2})日至(\d{4})年(\d{2})月(\d{2})日")
QOF = {(3, 31): 1, (6, 30): 2, (9, 30): 3, (12, 31): 4}
BS_ROWS = {"存貨合計": "存貨", "存貨": "存貨", "資產總計": "資產總計", "資產總額": "資產總計", "合約負債－流動": "合約負債－流動", "合約負債－流動合計": "合約負債－流動"}
IS_ROWS = {"營業收入合計": "rev", "營業毛利（毛損）": "gp"}


def _num(s):
    s = s.replace(",", "").replace("&nbsp;", "").strip()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    try:
        v = float(s.strip("()"))
    except ValueError:
        return None
    return -v if neg else v


def _clean(s):
    return re.sub(r"<[^>]+>", "", s).replace("&nbsp;", " ").replace("　", "").strip()


IX = re.compile(r"<ix:nonFraction\s+([^>]*)>([^<]*)</ix:nonFraction>")
IX_BS = {"ifrs-full:Inventories": "存貨", "ifrs-full:Assets": "資產總計", "ifrs-full:CurrentContractLiabilities": "合約負債－流動"}
IX_IS = {"ifrs-full:Revenue": 0, "tifrs-bsci-ci:GrossProfitLossFromOperations": 1}


def parse_ix(txt):
    """2019 年起的版型（行內 XBRL）：直接讀標了科目與期間的數。金額照頁面顯示的仟元。"""
    asof, dur = {}, {}
    for attrs, val in IX.findall(txt):
        name, ctx = re.search(r'name="([^"]+)"', attrs), re.search(r'contextRef="([^"]+)"', attrs)
        if not name or not ctx:
            continue
        name, ctx = name.group(1), ctx.group(1)
        v = _num(val)
        if v is not None and 'sign="-"' in attrs:
            v = -v
        m = re.fullmatch(r"AsOf(\d{4})(\d{2})(\d{2})", ctx)
        if m and name in IX_BS:
            asof.setdefault((IX_BS[name], tuple(map(int, m.groups()))), v)
        m = re.fullmatch(r"From(\d{4})0101To(\d{4})(\d{2})(\d{2})", ctx)
        if m and name in IX_IS and m.group(1) == m.group(2):
            q = QOF.get((int(m.group(3)), int(m.group(4))))
            if q:
                dur.setdefault((int(m.group(1)), q), [None, None])
                if dur[(int(m.group(1)), q)][IX_IS[name]] is None:
                    dur[(int(m.group(1)), q)][IX_IS[name]] = v
    dates = sorted({d for (k, d) in asof if k == "資產總計"}, reverse=True)
    if not dates or QOF.get(dates[0][1:]) is None:
        return None
    rows = {}
    for key in ("存貨", "資產總計", "合約負債－流動"):
        vals = [asof.get((key, d)) for d in dates]
        if any(v is not None for v in vals):
            rows[key] = vals
    return {"bs": {"dates": dates, "rows": rows}, "cum": {k: v for k, v in dur.items() if None not in v},
            "own": (dates[0][0], QOF[dates[0][1:]])}


def parse(raw):
    """回 {'bs': {'dates': [(y,m,d)], 'rows': {科目: [金額]}}, 'cum': {(y,q): [累計營收, 累計毛利]}, 'own': (y,q)}；看不懂回 None。"""
    txt = raw.decode("big5", errors="replace")
    if "<ix:nonFraction" in txt:
        return parse_ix(txt)
    heads = [m.start() for m in re.finditer(r"<th[^>]*>\s*會計項目\s*</th>", txt)]
    if len(heads) < 2:
        return None
    out = {"bs": None, "cum": {}, "own": None}
    for i, h in enumerate(heads[:2]):
        seg = txt[h: heads[i + 1] if i + 1 < len(heads) else len(txt)]
        head_end = seg.find("</tr>")
        cols = [_clean(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", seg[:head_end], flags=re.S)][1:]
        rows = {}
        for tr in seg[head_end:].split("<tr")[1:]:
            cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
            if len(cells) < 2:
                continue
            vals = [_num(c) for c in cells[1: 1 + len(cols)]]
            if all(v is None for v in vals):
                continue
            rows.setdefault(cells[0], vals)   # 同名列只取第一次出現的
        if i == 0:
            dates = [tuple(map(int, DATE.search(c).groups())) if DATE.search(c) else None for c in cols]
            if not dates or None in dates:
                return None
            picked = {}
            for label, key in BS_ROWS.items():
                if label in rows and key not in picked:
                    picked[key] = rows[label] + [None] * (len(dates) - len(rows[label]))
            out["bs"] = {"dates": dates, "rows": picked}
            y, m, d = dates[0]
            out["own"] = (y, QOF.get((m, d)))
        else:
            for ci, c in enumerate(cols):
                p, a = PERIOD.search(c), re.fullmatch(r"(\d{4})年度", c)
                if a:                                  # 年報的欄頭是「2014年度」＝全年累計
                    y2, q = int(a.group(1)), 4
                elif p:
                    y1, m1, d1, y2, m2, d2 = map(int, p.groups())
                    q = QOF.get((m2, d2))
                    if (m1, d1) != (1, 1) or y1 != y2 or q is None:
                        continue
                else:
                    continue
                rev = rows.get("營業收入合計", [None] * len(cols))
                gp = rows.get("營業毛利（毛損）", [None] * len(cols))
                r, g = (rev[ci] if ci < len(rev) else None), (gp[ci] if ci < len(gp) else None)
                if r is not None and g is not None:
                    out["cum"].setdefault((y2, q), [r, g])
    if out["bs"] is None:
        return None
    return out


def load_all():
    """讀 xbrl/ 下所有檔。回 (bs_by_key, cum)：bs_by_key[(代號, y, q)]＝資產負債表；cum[(代號, y, q)]＝[累計營收, 累計毛利]。
    cum 先收每份報表自己的當期（原始版），再用比較欄（可能是重編版）補沒有的。"""
    bs_by_key, own, comp = {}, {}, {}
    for f in sorted(DIR.glob("*.html")):
        m = re.fullmatch(r"(\d{4})_(\d{4})Q(\d)", f.stem)
        if not m:
            continue
        code, y, q = m.group(1), int(m.group(2)), int(m.group(3))
        p = parse(f.read_bytes())
        if p is None or p["own"] != (y, q):
            continue
        bs_by_key[(code, y, q)] = p["bs"]
        for (cy, cq), v in p["cum"].items():
            (own if (cy, cq) == (y, q) else comp).setdefault((code, cy, cq), v)
    cum = dict(comp)
    cum.update(own)
    return bs_by_key, cum


if __name__ == "__main__":
    import sys
    for name in sys.argv[1:]:
        p = parse((HERE / name).read_bytes())
        print(name, "→", None if p is None else {"own": p["own"], "dates": p["bs"]["dates"], "rows": p["bs"]["rows"], "cum": p["cum"]})
```

#### markers.py（sha256 前 16 碼 `6d47d90bc0533d89`）

```python
"""H16 乾跑：排除、標記（M1–M5）的可算率與各格點成立率、機械選門檻。規格：registration.md 2026-11-22「H16 乾跑規格」。
**只用 ≤ t 的資料**：月營收到 t−1 月、季報到 known_quarter(t)；每個取值點都有斷言。不讀任何價格、不算任何結果。"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from h16lib import deadline, in_pop, known_quarter, mnum, month_end, qshift, ym_of

HERE = Path(__file__).parent
GRID = {"M1": [5, 10, 15], "M2": [10, 20, 30], "M3": [2, 3, 5], "M5": [40, 50, 60]}
STRICTER = {"M1": max, "M2": max, "M3": max, "M5": min}
TARGET = 37.5
BASE = 10000  # 千元＝1,000 萬元
EXCLUDE_SECTORS = {"14": "建材營造", "17": "金融保險"}

events = json.loads((HERE / "events_all.json").read_text(encoding="utf-8"))

# ---------- 月營收 ----------
rev = {}
for f in sorted((HERE / "rev").glob("rev_*.json")):
    ym = f.stem[-7:]
    for r in json.loads(f.read_text(encoding="utf-8")):
        c = r.get("company_code")
        if c:
            rev[(c, ym)] = (r.get("revenue_current"), r.get("revenue_year_ago"))
rev_months = {ym for _, ym in rev}

# ---------- 損益表彙總（累計）→ 單季 ----------
cum = {}
for f in sorted((HERE / "is").glob("is_*.json")):
    m = re.fullmatch(r"is_(twse|tpex)_(\d{4})Q(\d)", f.stem)
    for c, v in json.loads(f.read_text(encoding="utf-8"))["general"].items():
        cum[(c, int(m.group(2)), int(m.group(3)))] = v
is_quarters = {(y, q) for _, y, q in cum}

# ---------- 下市公司：個別查詢回「不繼續公開發行」，改讀同一份申報的 XBRL 財報檔（只補下市事件的公司） ----------
import xbrl  # noqa: E402

XB_CODES = {e["code"] for e in events if e["xcheck"].startswith("下市")}
xb_bs, xb_cum = xbrl.load_all()
xb_used = set()
for k, v in xb_cum.items():
    if k[0] in XB_CODES and k not in cum:
        cum[k] = v
        xb_used.add(k[0])


def single(code, y, q):
    a = cum.get((code, y, q))
    if a is None or None in a:
        return None
    if q == 1:
        return tuple(a)
    b = cum.get((code, y, q - 1))
    if b is None or None in b:
        return None
    return a[0] - b[0], a[1] - b[1]


# ---------- 產業分類（今天的版本） ----------
sector = {}
for name, ck, sk in (("sector_twse", "公司代號", "產業別"), ("sector_tpex", "SecuritiesCompanyCode", "SecuritiesIndustryCode")):
    f = HERE / "official" / f"{name}.json"
    if f.exists():
        for r in json.loads(f.read_text(encoding="utf-8")):
            if r.get(ck):
                sector[str(r[ck]).strip()] = str(r.get(sk, "")).strip()

# ---------- 櫃買節點 ----------
node_members = defaultdict(set)
for f in sorted((HERE / "tpex").glob("*.html")):
    if f.stem == "index":
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    for part in re.split(r'<div id="companyList_', t)[1:]:
        m = re.match(r'([A-Za-z0-9]+)"', part)
        if m:
            for code in set(re.findall(r"stk_code=(\d{4})\b", part)):
                node_members[f"{f.stem}:{m.group(1)}"].add(code)
co_nodes = defaultdict(list)
for n, ms in node_members.items():
    if len(ms) >= 5:
        for c in ms:
            co_nodes[c].append(n)

# ---------- 資產負債表 ----------
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
DATE = re.compile(r"(\d+)年(\d+)月(\d+)日")
_bs_cache = {}


def bs(code, y, q):
    """回 {'dates': [(y,m,d)...], 'rows': {科目: [各期金額]}} 或 None。"""
    k = (code, y, q)
    if k in _bs_cache:
        return _bs_cache[k]
    f = HERE / "bs" / f"{code}_{y}Q{q}.html"
    out = None
    if f.exists():
        body = f.read_text(encoding="utf-8", errors="replace")
        dates, rows = None, {}
        for tr in ROW.findall(body):
            c = [re.sub(r"<[^>]+>", "", x).replace("&nbsp;", " ").strip() for x in CELL.findall(tr)]
            if not c:
                continue
            if c[0] == "會計項目":
                dates = [(int(a) + 1911, int(b), int(d)) for a, b, d in (DATE.search(x).groups() for x in c[1:] if DATE.search(x))]
            elif dates and c[0] in ("存貨", "資產總額", "資產總計", "合約負債－流動") and c[0] not in rows:
                vals = []
                for i in range(len(dates)):
                    s = c[1 + 2 * i].replace(",", "") if len(c) > 1 + 2 * i else ""
                    try:
                        vals.append(float(s))
                    except ValueError:
                        vals.append(None)
                rows[c[0]] = vals
        if dates:
            out = {"dates": dates, "rows": rows}
    elif code in XB_CODES and k in xb_bs:
        out = xb_bs[k]
    _bs_cache[k] = out
    return out


QEND = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def col(st, y, q):
    want = (y, *QEND[q])
    return st["dates"].index(want) if want in st["dates"] else None


def mean(xs):
    return sum(xs) / len(xs)


# ---------- 逐事件 ----------
out = []
for e in events:
    code, t = e["code"], e["t_ym"]
    tn = mnum(t)
    y0, q0 = known_quarter(t)
    assert deadline(y0, q0) < month_end(t), (code, t, y0, q0)          # 用到的那一季，法定期限嚴格早於 t 的月底
    assert not deadline(*qshift(y0, q0, 1)) < month_end(t), (code, t)  # 而且是這樣的季裡最新的一季
    r = {"code": code, "t_ym": t, "xcheck": e["xcheck"], "source": e["source"], "known_quarter": f"{y0}Q{q0}", "why": {}}
    # 排除
    sec = sector.get(code)
    r["sector"] = sec
    r1 = rev.get((code, ym_of(tn - 1)))
    if e.get("dr"):
        r["excluded"] = "存託憑證（不是普通股）"
    elif sec in EXCLUDE_SECTORS:
        r["excluded"] = EXCLUDE_SECTORS[sec]
    elif r1 and r1[1] is not None and r1[1] < BASE:
        r["excluded"] = "基期 < 1,000 萬元"
    else:
        r["excluded"] = None
    r["has_rev"] = r1 is not None
    # M1
    yoy = []
    for k in range(1, 7):
        ym = ym_of(tn - k)
        assert mnum(ym) <= tn - 1
        v = rev.get((code, ym))
        if v is None:
            r["why"]["M1"] = "月營收頁查不到" if ym in rev_months else "那個月的頁沒抓"
            break
        cur, ya = v
        if cur is None or ya is None or ya < BASE:
            r["why"]["M1"] = "去年同月沒有值或 < 1,000 萬元"
            break
        yoy.append(min((cur / ya - 1) * 100, 300.0))
    if len(yoy) == 6:
        r["M1"] = round(mean(yoy[:3]) - mean(yoy[3:]), 2)   # 近三個月平均 − 再前三個月平均（負＝轉弱）
        r["M1_recent"] = round(mean(yoy[:3]), 2)
    # M3
    gms = []
    for k in range(0, 9):
        y, q = qshift(y0, q0, -k)
        assert (y, q) <= (y0, q0)
        s = single(code, y, q)
        if s is None or s[0] <= 0:
            break
        gms.append(s[1] / s[0] * 100)
    if len(gms) >= 5:
        r["M3"] = round(mean(gms[1:5]) - gms[0], 2)          # 前四季平均 − 最近一季（正＝走低）
        if len(gms) >= 9:
            r["M3_vs_max8"] = round(max(gms[1:9]) - gms[0], 2)
    else:
        r["why"]["M3"] = "彙總表上沒有這家（或不是一般業版型）" if (code, y0, q0) not in cum else "前四季不齊或單季營收 ≤ 0"
    # M5
    nodes = sorted(co_nodes.get(code, []), key=lambda n: (-len(node_members[n]), n))
    if not nodes:
        r["why"]["M5"] = "不在任何 ≥ 5 家的節點"
    else:
        pos = tot = 0
        for mcode in node_members[nodes[0]]:
            vals = [rev.get((mcode, ym_of(tn - k))) for k in (1, 2, 3)]
            if any(v is None or v[0] is None or v[1] is None for v in vals):
                continue
            ya = sum(v[1] for v in vals)
            if ya <= 0:
                continue
            tot += 1
            pos += sum(v[0] for v in vals) > ya
        if tot >= 5:
            r["M5"] = round(pos / tot * 100, 1)                # 年增為正的成員比例（低＝壞）
            r["M5_node"], r["M5_n"] = nodes[0], tot
        else:
            r["why"]["M5"] = "節點裡算得出來的成員 < 5"
    # M2、M4
    st = bs(code, y0, q0)
    if st is None:
        r["why"]["M2"] = r["why"]["M4"] = "資產負債表沒抓到或查無資料"
    else:
        c0, cya = col(st, y0, q0), col(st, y0 - 1, q0)
        inv, ta = st["rows"].get("存貨"), st["rows"].get("資產總額") or st["rows"].get("資產總計")
        s0, sya = single(code, y0, q0), single(code, y0 - 1, q0)
        if c0 is None or cya is None:
            r["why"]["M2"] = "報表上沒有當季或去年同季那一欄"
        elif not inv or inv[c0] is None or inv[cya] is None or not ta or ta[c0] is None:
            r["why"]["M2"] = "沒有存貨或資產總額那一列"
        elif inv[c0] < 0.05 * ta[c0]:
            r["why"]["M2"] = "存貨 < 資產總額 5%"
        elif s0 is None or sya is None or (s0[0] - s0[1]) <= 0 or (sya[0] - sya[1]) <= 0 or inv[cya] <= 0:
            r["why"]["M2"] = "單季營業成本算不出來或 ≤ 0"
        else:
            d0, dya = inv[c0] / (s0[0] - s0[1]) * 91, inv[cya] / (sya[0] - sya[1]) * 91
            r["M2"] = round((d0 / dya - 1) * 100, 1)           # 存貨天數年增 %（高＝壞）
        cl = st["rows"].get("合約負債－流動")
        py, pq = qshift(y0, q0, -1)
        prev = None
        if cl and c0 is not None and cl[c0] is not None:
            if q0 == 1:
                pc = col(st, py, pq)
                prev = cl[pc] if pc is not None else None
            else:
                st2 = bs(code, py, pq)
                if st2 and st2["rows"].get("合約負債－流動") and col(st2, py, pq) is not None:
                    prev = st2["rows"]["合約負債－流動"][col(st2, py, pq)]
            sp = single(code, py, pq)
            if prev is None:
                r["why"]["M4"] = "前一季沒有合約負債的數"
            elif sp is None or sp[0] <= 0 or prev < 0.02 * sp[0]:
                r["why"]["M4"] = "前一季合約負債 < 單季營收 2%（或營收算不出來）"
            else:
                r["M4"] = round((cl[c0] / prev - 1) * 100, 1)   # 季變動 %（≤ −20＝壞）
        elif "M4" not in r["why"]:
            r["why"]["M4"] = "沒有合約負債這一列（2018 年以前沒有這個科目）"
    out.append(r)

(HERE / "markers.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

# ---------- 摘要 ----------
print("事件", len(out), "｜來源", dict(Counter(r["source"] for r in out)))
print("產業分類查得到的", sum(r["sector"] is not None for r in out), "｜事件的產業別分布（前 12）", Counter(r["sector"] for r in out).most_common(12))
print("排除：", dict(Counter(r["excluded"] for r in out if r["excluded"])), "｜查不到月營收（不排除）", sum(not r["has_rev"] for r in out))
kept = [r for r in out if not r["excluded"]]
print("排除後", len(kept), "｜交叉核：", dict(Counter(r["xcheck"] for r in kept)))
MODE = sys.argv[1] if len(sys.argv) > 1 else "登記的母體"
pop = [r for r in out if in_pop(r)]   # 交叉核對不上的、還原不了的下市事件都不進（registration.md 的規則）
print(f"\n== 選門檻的母體（{MODE}）：{len(pop)} 筆")


def hit(r, m, g):
    v = r.get(m)
    if v is None:
        return None
    return {"M1": v <= -g, "M2": v >= g, "M3": v >= g, "M5": v < g}[m]


def quarter(ym):
    return "%sQ%d" % (ym[:4], (int(ym[5:]) - 1) // 3 + 1)


chosen = {}
for m in ("M1", "M2", "M3", "M5"):
    comp = [r for r in pop if r.get(m) is not None]
    rates = {g: sum(hit(r, m, g) for r in comp) / len(comp) * 100 for g in GRID[m]} if comp else {}
    best = min(abs(v - TARGET) for v in rates.values()) if rates else None
    ties = [g for g, v in rates.items() if abs(abs(v - TARGET) - best) < 1e-9] if rates else []
    g = STRICTER[m](ties) if ties else None
    chosen[m] = g
    a = [r for r in comp if hit(r, m, g)]
    b = [r for r in comp if not hit(r, m, g)]
    qa, qb = Counter(quarter(r["t_ym"]) for r in a), Counter(quarter(r["t_ym"]) for r in b)
    both5 = sum(1 for q in set(qa) | set(qb) if qa[q] >= 5 and qb[q] >= 5)
    early = lambda rs: sum(r["t_ym"] <= "2017-12" for r in rs)  # noqa: E731
    print(f"{m}: 可算 {len(comp)}／{len(pop)}（{len(comp) / len(pop) * 100:.1f}%）｜各格點成立率 "
          + "、".join(f"{g_}→{v:.1f}%" for g_, v in rates.items()) + f"｜選 {g}｜成立 {len(a)}、不成立 {len(b)}"
          + f"｜前段（～2017-12）成立 {early(a)}、不成立 {early(b)}；後段 成立 {len(a) - early(a)}、不成立 {len(b) - early(b)}｜兩組都 ≥ 5 筆的季 {both5}")
    print("    算不出來的原因：", dict(Counter(r["why"].get(m, "?") for r in pop if r.get(m) is None)))
    # 季內比較的資訊量：W＝Σ 成立×不成立÷(成立＋不成立)；兩組各 100、不分層時 W＝50
    qs = sorted(set(qa) | set(qb))
    W = sum(qa[q] * qb[q] / (qa[q] + qb[q]) for q in qs)
    big = max(qs, key=lambda q: qa[q] + qb[q])
    W_wo = W - qa[big] * qb[big] / (qa[big] + qb[big])
    info = sum(1 for q in qs if qa[q] >= 1 and qb[q] >= 1)
    mdd = lambda w: 3.08 * (0.25 / w) ** 0.5 * 100  # noqa: E731  單尾 0.0125、檢定力 80%、p(1−p) 取最大值 0.25
    print(f"    季內資訊量：兩組都有的季 {info}／{len(qs)}｜W＝{W:.1f}（偵測得到的最小差約 {mdd(W):.0f} 個百分點）｜事件最多的季 {big}（{qa[big] + qb[big]} 筆）拿掉後 W＝{W_wo:.1f}（約 {mdd(W_wo):.0f} 個百分點）")
    print("    逐季（成立／不成立）：", "、".join(f"{q[2:]} {qa[q]}／{qb[q]}" for q in qs))
dl = [r for r in pop if r["xcheck"].startswith("下市")]
print(f"下市事件 {len(dl)} 筆的可算數：" + "、".join(f"{m} {sum(r.get(m) is not None for r in dl)}" for m in ("M1", "M2", "M3", "M4", "M5"))
      + f"｜有 XBRL 財報檔的公司 {len({c for c, _, _ in xb_bs if c in XB_CODES})}")
for m in ("M2", "M3"):
    print(f"    下市事件 {m} 算不出來的原因：", dict(Counter(r["why"].get(m, "?") for r in dl if r.get(m) is None)))
m4 = [r for r in pop if r.get("M4") is not None]
print(f"M4（只印）: 可算 {len(m4)}／{len(pop)}｜季減 ≥ 20% 的 {sum(r['M4'] <= -20 for r in m4)}")
print("    算不出來的原因：", dict(Counter(r["why"].get("M4", "?") for r in pop if r.get("M4") is None)))
m1r = [r for r in pop if r.get("M1_recent") is not None]
print(f"另印 M1「近三個月平均年增 ≤ 0」：{sum(r['M1_recent'] <= 0 for r in m1r)}／{len(m1r)}")
m38 = [r for r in pop if r.get("M3_vs_max8") is not None]
print(f"另印 M3「比前八季最高低 ≥ 3 個百分點」：{sum(r['M3_vs_max8'] >= 3 for r in m38)}／{len(m38)}")
m2ok = chosen.get("M2") is not None
if m2ok:
    comp = [r for r in pop if r.get("M2") is not None]
    a = sum(hit(r, "M2", chosen["M2"]) for r in comp)
    print(f"M2 進不進確認型：可算率 {len(comp) / len(pop) * 100:.1f}%（要 ≥ 60%）、成立 {a}、不成立 {len(comp) - a}（各要 ≥ 100）→",
          "進" if len(comp) / len(pop) >= 0.6 and a >= 100 and len(comp) - a >= 100 else "只印")
(HERE / "chosen.json").write_text(json.dumps({"mode": MODE, "chosen": chosen, "population": len(pop)}, ensure_ascii=False), encoding="utf-8")
pm = Counter(r["t_ym"] for r in pop)
avg = len(pop) / 75
print("母體每月事件：月均 %.2f｜成群月（≥ 月均三倍）" % avg, sorted((m, n) for m, n in pm.items() if n >= 3 * avg))
print("母體每季事件：", dict(sorted(Counter(quarter(r["t_ym"]) for r in pop).items())))
```

#### oldplaybook.py（sha256 前 16 碼 `9967d572515d6eca`）

```python
"""H16：舊劇本清單（設計稿第三版 §7.3 的 #1–#9）的來源案例怎麼剔，三種寫法下各標記兩組各剩幾筆、季內資訊量多少。
只讀 markers.json、chosen.json、櫃買節點快取與交易所月底行情的名稱欄；不讀任何價格、不含任何 t 之後的東西。
節點＝櫃買產業價值鏈平台今天的名單；對照是照節點名稱對的。"""
import json
import re
from collections import Counter
from pathlib import Path

import official
from h16lib import in_pop

H = Path(__file__).parent
mk = json.loads((H / "markers.json").read_text(encoding="utf-8"))
ch = json.loads((H / "chosen.json").read_text(encoding="utf-8"))["chosen"]
pop = [r for r in mk if in_pop(r)]
HIT = {"M1": lambda v, g: v <= -g, "M2": lambda v, g: v >= g, "M3": lambda v, g: v >= g, "M5": lambda v, g: v < g}
# 成群期＝同一年內第一個成群月到最後一個成群月（成群月＝事件數 ≥ 月均三倍；乾跑報告 §2）
EPISODES = {"2015 夏": ("2015-06", "2015-08"), "2018": ("2018-04", "2018-10"), "2020-03": ("2020-03", "2020-03")}

# ---------- 節點：代碼、名稱、成員 ----------
nodes = {}
for f in sorted((H / "tpex").glob("*.html")):
    if f.stem == "index":
        continue
    t = f.read_text(encoding="utf-8", errors="replace")
    for part in re.split(r'<div id="companyList_', t)[1:]:
        m = re.match(r'([A-Za-z0-9]+)" title="([^"]*)"', part)
        if m:
            nodes.setdefault(f"{f.stem}:{m.group(1)}", {"name": m.group(2), "members": set()})["members"] |= set(re.findall(r"stk_code=(\d{4})\b", part))

# ---------- 對照（段、節點、事件月的期間、代表公司）----------
# 期間＝那一段起年的 1 月到訖年次年的 12 月；事件期到 2021-03 為止。
SEG = [
    ("1 ABF 載板 2019–2022", ["L000:L610", "D000:D700"], [("2019-01", "2021-03")], ["3037", "8046", "3189"]),
    ("2 矽晶圓 2016–2019", ["D000:D300"], [("2016-01", "2020-12")], ["6488", "6182", "3532", "5483", "3016"]),
    ("3 被動元件 MLCC 2017–2018", ["J000:J600", "J000:J200"], [("2017-01", "2019-12")], ["2327", "2492", "3026"]),
    ("4 記憶體 2016–2018", ["F000:F500", "I000:I300", "D000:D300"], [("2016-01", "2019-12")], ["2408", "2344", "2337", "3260", "8299"]),
    ("5 5G 基地台板材 2019–2020", ["L000:L630"], [("2019-01", "2021-03")], ["2383", "6213", "6274"]),
    ("6 3D 感測雷射 2017–2018", ["D000:D300"], [("2017-01", "2019-12")], ["3105", "8086", "2455", "3081"]),
    ("7 驅動 IC／八吋產能 2020–2022", ["G000:G900", "D000:D300"], [("2020-01", "2021-03")], ["3034", "3545", "4961", "8016", "5347"]),
    ("8 挖礦顯示卡 2017–2018 與 2021", ["F000:FD00"], [("2017-01", "2019-12"), ("2021-01", "2021-03")], ["2376", "2377", "6150", "2399", "3515"]),
    ("9 mini-LED 2020–2021", ["A200:A230", "A200:A240", "G000:G400"], [("2020-01", "2021-03")], ["2448", "3698", "2393", "3527", "6706", "3714"]),
]
names = {}
for ymd in ("20150130", "20210331"):
    for market in ("twse", "tpex"):
        for code, (name, _) in official.load(market, ymd).items():
            names[code] = name


def key(r):
    return r["code"], r["t_ym"]


def quarter(ym):
    return "%sQ%d" % (ym[:4], (int(ym[5:]) - 1) // 3 + 1)


drop = {"2N1 節點全剔": set(), "2N2 節點、期間內": set(), "2C 代表公司": set()}
for seg, ks, wins, anchors in SEG:
    members = set().union(*(nodes[k]["members"] for k in ks))
    n1 = {key(r) for r in pop if r["code"] in members}
    n2 = {key(r) for r in pop if r["code"] in members and any(a <= r["t_ym"] <= b for a, b in wins)}
    c = {key(r) for r in pop if r["code"] in anchors}
    drop["2N1 節點全剔"] |= n1
    drop["2N2 節點、期間內"] |= n2
    drop["2C 代表公司"] |= c
    print(f"{seg}｜" + "；".join(f"{k.split(':')[1]} {nodes[k]['name']}（{len(nodes[k]['members'])}）" for k in ks)
          + f"｜節點成員的母體事件 {len(n1)}｜期間內 {len(n2)}｜代表公司 " + "、".join(f"{a} {names.get(a, '？')}" for a in anchors) + f"（事件 {len(c)}）")


def wsum(a, b):
    qa, qb = Counter(quarter(r["t_ym"]) for r in a), Counter(quarter(r["t_ym"]) for r in b)
    qs = sorted(set(qa) | set(qb))
    return sum(qa[q] * qb[q] / (qa[q] + qb[q]) for q in qs), sum(1 for q in qs if qa[q] >= 5 and qb[q] >= 5)


def report(label, dropped):
    kept = [r for r in pop if key(r) not in dropped]
    print(f"\n== {label}：剔除 {len(pop) - len(kept)}，剩 {len(kept)}")
    for m in ("M1", "M2", "M3", "M5"):
        comp = [r for r in kept if r.get(m) is not None]
        a = [r for r in comp if HIT[m](r[m], ch[m])]
        b = [r for r in comp if not HIT[m](r[m], ch[m])]
        w, both5 = wsum(a, b)
        early = lambda rs: sum(r["t_ym"] <= "2017-12" for r in rs)  # noqa: E731
        epi = []
        for name, (lo, hi) in EPISODES.items():
            out = lambda rs: [r for r in rs if not lo <= r["t_ym"] <= hi]  # noqa: E731
            epi.append(f"{name} {wsum(out(a), out(b))[0]:.1f}")
        print(f"  {m}：成立 {len(a)}、不成立 {len(b)}｜前段 {early(a)}／{early(b)}、後段 {len(a) - early(a)}／{len(b) - early(b)}"
              f"｜兩組都 ≥ 5 筆的季 {both5}｜W {w:.1f}｜拿掉成群期之後的 W：" + "、".join(epi))


report("完全不剔", set())
for label, dropped in drop.items():
    report(label, dropped)
print("\n成群期的母體事件數：", {n: sum(lo <= r["t_ym"] <= hi for r in pop) for n, (lo, hi) in EPISODES.items()})
(H / "oldplaybook_drop.json").write_text(json.dumps({k: sorted(map(list, v)) for k, v in drop.items()}, ensure_ascii=False), encoding="utf-8")
```

### 核對與報告用的計數

#### validate_xbrl.py（sha256 前 16 碼 `4514f07b34196b37`）

```python
"""驗證：XBRL 財報檔與原本兩條路線（個別資產負債表、損益表彙總）對同一家公司同一季給的數是不是一樣。
樣本＝fetch_xbrl.py 機械抽的 12 筆今天還在的事件。只比 ≤ known_quarter(t) 的數。"""
import json
import re
from pathlib import Path

import xbrl
from h16lib import known_quarter

HERE = Path(__file__).parent
sample = json.loads((HERE / "xbrl_sample.json").read_text(encoding="utf-8"))
cum = {}
for f in sorted((HERE / "is").glob("is_*.json")):
    m = re.fullmatch(r"is_(twse|tpex)_(\d{4})Q(\d)", f.stem)
    for c, v in json.loads(f.read_text(encoding="utf-8"))["general"].items():
        cum[(c, int(m.group(2)), int(m.group(3)))] = v

ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
DATE = re.compile(r"(\d+)年(\d+)月(\d+)日")


def old_bs(code, y, q):
    f = HERE / "bs" / f"{code}_{y}Q{q}.html"
    if not f.exists():
        return None
    dates, rows = None, {}
    for tr in ROW.findall(f.read_text(encoding="utf-8", errors="replace")):
        c = [re.sub(r"<[^>]+>", "", x).replace("&nbsp;", " ").strip() for x in CELL.findall(tr)]
        if not c:
            continue
        if c[0] == "會計項目":
            dates = [(int(a) + 1911, int(b), int(d)) for a, b, d in (DATE.search(x).groups() for x in c[1:] if DATE.search(x))]
        elif dates and c[0] in ("存貨", "資產總額", "資產總計") and c[0] not in rows:
            vals = []
            for i in range(len(dates)):
                s = c[1 + 2 * i].replace(",", "") if len(c) > 1 + 2 * i else ""
                try:
                    vals.append(float(s))
                except ValueError:
                    vals.append(None)
            rows["資產總計" if c[0].startswith("資產總") else c[0]] = vals
    return {"dates": dates, "rows": rows} if dates else None


n = same = diff = missing = 0
for code, t in sample:
    y, q = known_quarter(t)
    f = HERE / "xbrl" / f"{code}_{y}Q{q}.html"
    p = xbrl.parse(f.read_bytes()) if f.exists() else None
    ob = old_bs(code, y, q)
    if p is None or ob is None:
        missing += 1
        print(code, f"{y}Q{q}", "缺：XBRL", p is not None, "原路線", ob is not None)
        continue
    pairs = []
    for key in ("存貨", "資產總計"):
        for d in ob["dates"]:
            if d in p["bs"]["dates"] and key in ob["rows"] and key in p["bs"]["rows"]:
                pairs.append((f"{key}@{d}", ob["rows"][key][ob["dates"].index(d)], p["bs"]["rows"][key][p["bs"]["dates"].index(d)]))
    for (cy, cq), v in p["cum"].items():
        o = cum.get((code, cy, cq))
        if o and None not in o:
            pairs.append((f"累計營收@{cy}Q{cq}", o[0], v[0]))
            pairs.append((f"累計毛利@{cy}Q{cq}", o[1], v[1]))
    for name, a, b in pairs:
        n += 1
        if a is not None and b is not None and abs(a - b) <= max(1.0, 1e-6 * abs(a)):
            same += 1
        else:
            diff += 1
            print("  不同", code, f"{y}Q{q}", name, "原路線", a, "XBRL", b)
print("對照筆數", len(sample), "｜缺檔", missing, "｜比了", n, "個數｜相同", same, "｜不同", diff)
```

#### dryrun_extra.py（sha256 前 16 碼 `04c62628220aa446`）

```python
"""乾跑報告要的其餘計數（都不含 t 之後的東西）：漏斗、下市事件、三月事件、標記重疊、腳本雜湊。"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from h16lib import in_pop

H = Path(__file__).parent
ev = json.loads((H / "events_all.json").read_text(encoding="utf-8"))
mk = json.loads((H / "markers.json").read_text(encoding="utf-8"))
pop = [r for r in mk if in_pop(r)]
print("事件", len(ev), "｜相異公司", len({e["code"] for e in ev}), "｜母體", len(pop), "｜母體相異公司", len({r["code"] for r in pop}))
print("依來源", dict(Counter(e["source"][:8] for e in ev)))
print("漏斗：排除", dict(Counter(r["excluded"] for r in mk if r["excluded"])),
      "｜沒被排除的裡面：", dict(Counter(r["xcheck"] for r in mk if not r["excluded"])))
print("查不到產業分類", sum(r["sector"] is None for r in mk), "｜查不到 t−1 月營收", sum(not r["has_rev"] for r in mk))
dl = [e for e in ev if e["source"].startswith("交易所")]
print("下市事件", len(dl), "｜存託憑證", sum(e["dr"] for e in dl), "｜標未還原", sum(e["xcheck"] == "未還原" for e in dl),
      "｜不在終止名單上", sum(not e.get("delisted") for e in dl), "｜低點到 t 之間有除權息或減資", sum(bool(e.get("corp_actions_low_to_t")) for e in dl))
print("  下市事件依 t 年：", dict(sorted(Counter(e["t_ym"][:4] for e in dl).items())))
dlp = [r for r in pop if r["source"].startswith("交易所")]
print("  進母體的下市事件", len(dlp), "｜各標記可算：" + "、".join(f"{m} {sum(r.get(m) is not None for r in dlp)}" for m in ("M1", "M2", "M3", "M4", "M5")))
print("存託憑證的事件（今天還在的＋下市）", sum(e["dr"] for e in ev))
print("漲幅分布（全部事件）：3–5 倍", sum(3 <= e["runup"] < 5 for e in ev), "｜5–10 倍", sum(5 <= e["runup"] < 10 for e in ev), "｜≥ 10 倍", sum(e["runup"] >= 10 for e in ev))
mh = Counter(e["months_high_to_t"] for e in ev)
print("高點到 t 的月數（全部事件）：1–3", sum(v for k, v in mh.items() if k <= 3), "｜4–6", sum(v for k, v in mh.items() if 4 <= k <= 6),
      "｜7–12", sum(v for k, v in mh.items() if 7 <= k <= 12), "｜13–24", sum(v for k, v in mh.items() if 13 <= k <= 24), "｜超過 24", sum(v for k, v in mh.items() if k > 24))
mar = [r for r in pop if r["t_ym"].endswith("-03")]
print("t 在三月的母體事件", len(mar), dict(sorted(Counter(r["t_ym"] for r in mar).items())), "｜用的季", dict(Counter(r["known_quarter"] for r in mar)))
print("t 在 2020-03～2020-05 的母體事件", sum("2020-03" <= r["t_ym"] <= "2020-05" for r in pop))
MS = ("M1", "M2", "M3", "M5")
print("四個標記都算得出來", sum(all(r.get(m) is not None for m in MS) for r in pop), "｜至少一個", sum(any(r.get(m) is not None for m in MS) for r in pop),
      "｜一個都算不出來", sum(all(r.get(m) is None for m in MS) for r in pop))
ch = json.loads((H / "chosen.json").read_text(encoding="utf-8"))["chosen"]
hitf = {"M1": lambda v, g: v <= -g, "M2": lambda v, g: v >= g, "M3": lambda v, g: v >= g, "M5": lambda v, g: v < g}
for a, b in (("M1", "M2"), ("M1", "M3"), ("M1", "M5"), ("M2", "M3"), ("M2", "M5"), ("M3", "M5")):
    both = [r for r in pop if r.get(a) is not None and r.get(b) is not None]
    ha = sum(hitf[a](r[a], ch[a]) for r in both)
    hb = sum(hitf[b](r[b], ch[b]) for r in both)
    hab = sum(hitf[a](r[a], ch[a]) and hitf[b](r[b], ch[b]) for r in both)
    print(f"  {a}×{b}：都算得出來 {len(both)}｜{a} 成立 {ha}｜{b} 成立 {hb}｜兩個都成立 {hab}（若互不相干約 {ha * hb / len(both):.0f}）")
# M5 的值在同一節點、同一個事件月裡完全相同：群有多大
m5 = [r for r in pop if r.get("M5") is not None]
grp = Counter((r["M5_node"], r["t_ym"]) for r in m5)
print("M5：可算", len(m5), "｜節點×事件月的群", len(grp), "｜≥ 3 筆的群", sum(v >= 3 for v in grp.values()), "涵蓋", sum(v for v in grp.values() if v >= 3), "筆｜最大的群", max(grp.values()))
print("腳本 sha256 前 16 碼：")
for n in ("h16lib.py", "official.py", "adjust.py", "stage_events.py", "xbrl.py", "markers.py", "detect.py"):
    print("  ", n, hashlib.sha256((H / n).read_bytes()).hexdigest()[:16], len((H / n).read_text(encoding="utf-8").splitlines()), "行")
```

#### dryrun_tables.py（sha256 前 16 碼 `aed545df0884be27`）

```python
"""乾跑報告的表（markdown）：逐季事件數與各標記的成立／不成立、逐月事件數。只讀 markers.json、chosen.json；不含任何 t 之後的東西。"""
import json
from collections import Counter
from pathlib import Path

from h16lib import in_pop

H = Path(__file__).parent
mk = json.loads((H / "markers.json").read_text(encoding="utf-8"))
ch = json.loads((H / "chosen.json").read_text(encoding="utf-8"))["chosen"]
pop = [r for r in mk if in_pop(r)]
hitf = {"M1": lambda v, g: v <= -g, "M2": lambda v, g: v >= g, "M3": lambda v, g: v >= g, "M5": lambda v, g: v < g}


def quarter(ym):
    return "%sQ%d" % (ym[:4], (int(ym[5:]) - 1) // 3 + 1)


qs = sorted({quarter(r["t_ym"]) for r in pop})
tot = Counter(quarter(r["t_ym"]) for r in pop)
cells = {}
for m in ("M1", "M2", "M3", "M5"):
    a, b = Counter(), Counter()
    for r in pop:
        if r.get(m) is None:
            continue
        (a if hitf[m](r[m], ch[m]) else b)[quarter(r["t_ym"])] += 1
    cells[m] = (a, b)
print("| 季 | 事件 | M1 成立／不成立 | M2 | M3 | M5 |")
print("|---|---:|---|---|---|---|")
for q in qs:
    row = [q, str(tot[q])]
    for m in ("M1", "M2", "M3", "M5"):
        a, b = cells[m]
        s = f"{a[q]}／{b[q]}"
        row.append(f"**{s}**" if a[q] >= 5 and b[q] >= 5 else s)
    print("| " + " | ".join(row) + " |")
row = ["合計", str(len(pop))]
for m in ("M1", "M2", "M3", "M5"):
    a, b = cells[m]
    row.append(f"{sum(a.values())}／{sum(b.values())}")
print("| " + " | ".join(row) + " |")
print()
pm = Counter(r["t_ym"] for r in pop)
print("每月事件數（母體；沒列的月份是 0）：")
for y in range(2015, 2022):
    print(f"- {y}：" + "、".join(f"{m:02d} 月 {pm['%d-%02d' % (y, m)]}" for m in range(1, 13) if pm["%d-%02d" % (y, m)]))
avg = len(pop) / 75
big = {k: v for k, v in pm.items() if v >= 3 * avg}
print(f"有事件的月份 {len(pm)}／75｜月均 {avg:.2f}｜成群月（≥ 月均三倍）{len(big)} 個、合計 {sum(big.values())} 筆（{sum(big.values()) / len(pop) * 100:.0f}%）｜事件數 ≥ 10 的季 {sum(v >= 10 for v in tot.values())}／{len(tot)}")
```

### 抓取（只抓、不算）

#### detect.py（sha256 前 16 碼 `1c345cb2210c3c57`）

```python
"""H16 乾跑的資料段之二：事件偵測（設計稿 v3 §5.3 的事件定義；只用 ≤ t 的月收盤，px.json 本身截在 2021-03）。
事件＝月收盤自過去 36 個月內最低月收盤起算曾達 ≥ 3 倍；之後第一次月收盤 ≤ 0.6 × 這段漲勢的最高月收盤，那個月＝t。
三倍狀態在高點後 24 個月沒觸發就解除；同一段只記一次（下一次要先再創新高）。至少 12 個月價格歷史才判。
**不算任何 t 之後的東西**（沒有結果欄、沒有更深的回落月）。只寫 scratchpad。"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
MULT, LOOKBACK, DROP, EXPIRE, MIN_HIST = 3.0, 36, 0.6, 24, 12
EVENT_FROM, EVENT_TO = "2015-01", "2021-03"


def mnum(ym):
    y, m = map(int, ym.split("-"))
    return y * 12 + m - 1


px = json.loads((HERE / "px.json").read_text(encoding="utf-8"))
uni = json.loads((HERE / "universe.json").read_text(encoding="utf-8"))

# 同一個代號在兩個板都有價時（轉板），取根數多的那一個
by_code = {}
for t, rows in px.items():
    code = t.split(".")[0]
    if code not in by_code or len(rows) > len(px[by_code[code]]):
        by_code[code] = t

events, n_series, short = [], 0, 0
for code, t in sorted(by_code.items()):
    s = [(ym, v) for ym, v in px[t] if v and v > 0]
    if len(s) <= MIN_HIST:
        short += 1
        continue
    n_series += 1
    mn = [mnum(ym) for ym, _ in s]
    cl = [v for _, v in s]
    state, prev_high = None, None
    for i in range(MIN_HIST, len(s)):
        if state is None:
            win = [k for k in range(i) if mn[i] - mn[k] <= LOOKBACK]
            if not win:
                continue
            lo = min(win, key=lambda k: cl[k])
            hi = max(range(lo, i + 1), key=lambda k: cl[k])
            if cl[hi] >= MULT * cl[lo] and mn[i] - mn[hi] <= EXPIRE and (prev_high is None or cl[hi] > prev_high):
                state = {"lo": lo, "hi": hi, "entry": i}
            else:
                continue
        if cl[i] > cl[state["hi"]]:
            state["hi"] = i
        elif cl[i] <= DROP * cl[state["hi"]]:
            lo, hi = state["lo"], state["hi"]
            if EVENT_FROM <= s[i][0] <= EVENT_TO:
                events.append({"code": code, "ticker": t, "name": uni.get(t, {}).get("name", ""),
                               "low_ym": s[lo][0], "low_px": round(cl[lo], 4), "high_ym": s[hi][0], "high_px": round(cl[hi], 4),
                               "t_ym": s[i][0], "t_px": round(cl[i], 4), "runup": round(cl[hi] / cl[lo], 2),
                               "depth": round(cl[i] / cl[hi], 3), "months_high_to_t": mn[i] - mn[hi]})
            assert s[lo][0] <= s[hi][0] < s[i][0], (code, s[lo][0], s[hi][0], s[i][0])  # 事件列只含 ≤ t 的月
            prev_high = cl[hi]
            state = None
        elif mn[i] - mn[state["hi"]] > EXPIRE:
            state = None

(HERE / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=0), encoding="utf-8")
print("有價序列", n_series, "（歷史不足", short, "）｜事件", len(events), "｜相異公司", len({e["code"] for e in events}))
print("依年：", dict(sorted(Counter(e["t_ym"][:4] for e in events).items())))
pm = Counter(e["t_ym"] for e in events)
months = (mnum(EVENT_TO) - mnum(EVENT_FROM) + 1)
avg = len(events) / months
print("月均 %.2f；事件最多的月：" % avg, pm.most_common(8))
print("成群月（≥ 月均三倍）：", sorted((m, n) for m, n in pm.items() if n >= 3 * avg))
pq = Counter("%sQ%d" % (e["t_ym"][:4], (int(e["t_ym"][5:]) - 1) // 3 + 1) for e in events)
print("依季：", dict(sorted(pq.items())))
print("漲幅倍數分布：3–5 倍", sum(e["runup"] < 5 for e in events), "5–10 倍", sum(5 <= e["runup"] < 10 for e in events),
      "≥10 倍", sum(e["runup"] >= 10 for e in events))
print("高點到 t 的月數：≤3", sum(e["months_high_to_t"] <= 3 for e in events), "4–6", sum(4 <= e["months_high_to_t"] <= 6 for e in events),
      "7–12", sum(7 <= e["months_high_to_t"] <= 12 for e in events), ">12", sum(e["months_high_to_t"] > 12 for e in events))
if len(sys.argv) > 1:
    for e in events[:int(sys.argv[1])]:
        print(e)
```

#### fetch_px.py（sha256 前 16 碼 `1a790e402f324209`）

```python
"""H16 乾跑的資料段之一：全台股月線，**截在 2021-03**（事件期末；結果窗的價格不下載）。
宇宙＝月營收歷史頁 2014-11～2023-12 出現過的所有代號（含後來下市的；取不到價的照數）。
零 LLM；只寫 scratchpad；對外請求不帶任何個人資訊。"""
import json
import re
import time
from pathlib import Path

import importlib

import yfinance as yf

yshared = importlib.import_module("yfinance.shared")

HERE = Path(__file__).parent
REV = HERE.parent / "dryrun" / "rev"
START, END = "2011-12-01", "2021-04-01"
LAST_OK = "2021-03"


def log(*a):
    print(*a, flush=True)


# ---------- 宇宙 ----------
seen = {}  # ticker -> {"name", "first", "last"}
for f in sorted(REV.glob("rev_*.json")):
    m = re.fullmatch(r"rev_(twse|tpex)_(\d{4}-\d{2})", f.stem)
    if not m:
        continue
    suffix = ".TW" if m.group(1) == "twse" else ".TWO"
    for r in json.loads(f.read_text(encoding="utf-8")):
        code = r.get("company_code")
        if not code or not re.fullmatch(r"\d{4}", code):
            continue
        t = code + suffix
        d = seen.setdefault(t, {"name": r.get("company_name") or code, "first": m.group(2), "last": m.group(2)})
        d["first"] = min(d["first"], m.group(2))
        d["last"] = max(d["last"], m.group(2))
tickers = sorted(seen)
(HERE / "universe.json").write_text(json.dumps(seen, ensure_ascii=False), encoding="utf-8")
log("宇宙", len(tickers), "（代號×板）；相異代號", len({t.split('.')[0] for t in tickers}))

cache = HERE / "px.json"
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
            rows = [[d.strftime("%Y-%m"), float(v)] for d, v in s.items() if d.strftime("%Y-%m") <= LAST_OK]
            if rows:
                px[t] = rows
                errors.pop(t, None)
                continue
        errors[t] = str(getattr(yshared, "_ERRORS", {}).get(t, "empty"))
    time.sleep(pause)


todo = [t for t in tickers if t not in px]
for i in range(0, len(todo), 80):
    pull(todo[i:i + 80], 1.5)
    if (i // 80) % 5 == 0:
        log("第一輪", min(i + 80, len(todo)), "/", len(todo), "已有", len(px))
        cache.write_text(json.dumps(px), encoding="utf-8")
cache.write_text(json.dumps(px), encoding="utf-8")
miss = [t for t in tickers if t not in px]
log("第一輪後缺", len(miss))
for i in range(0, len(miss), 20):
    pull(miss[i:i + 20], 5)
cache.write_text(json.dumps(px), encoding="utf-8")
miss = [t for t in tickers if t not in px]
limited = [t for t in miss if re.search(r"rate|too many|429", errors.get(t, ""), flags=re.I)]
(HERE / "px_errors.json").write_text(json.dumps({t: errors.get(t, "") for t in miss}, ensure_ascii=False), encoding="utf-8")
last = max((rows[-1][0] for rows in px.values()), default="")
log("最後缺", len(miss), "其中錯誤訊息像限流的", len(limited), "｜有價", len(px), "｜最晚一根", last)
assert last <= LAST_OK, last
log("PX_DONE")
```

#### fetch_official.py（sha256 前 16 碼 `0ccbb0028af9a584`）

```python
"""H16 乾跑的資料段之四：交易所官方的月底全市場行情（含後來下市的公司）與終止上市櫃名單。
月底交易日由 2330.TW 的日線定；每個月底各抓上市（MI_INDEX）與上櫃（每日收盤行情）一次，原始 JSON 全部存檔。
只抓到 2021-03；不解析、不算任何東西。節流 5 秒；到 04:40（台北）自動停。
零 LLM；只寫 scratchpad；對外請求不帶任何個人資訊。"""
import datetime as dt
import json
import time
from pathlib import Path

import requests
import yfinance as yf

HERE = Path(__file__).parent
OUT = HERE / "official"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}
PACE = 5.0
STOP_AT = dt.time(4, 40)


def log(*a):
    print(dt.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def past_stop():
    return STOP_AT <= dt.datetime.now().time() < dt.time(7, 0)


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
            log("  非 200：", r.status_code, dest.name, "退避")
            time.sleep(120 * (attempt + 1))
            continue
        try:
            obj = json.loads(body.decode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            log("  非 JSON：", dest.name, body[:80])
            time.sleep(120 * (attempt + 1))
            continue
        if ok(obj):
            dest.write_bytes(body)
            return "ok"
        (OUT / (dest.stem + ".other")).write_bytes(body[:2000])
        return "other"
    return "error"


# ---------- 月底交易日 ----------
dates_file = HERE / "month_ends.json"
if dates_file.exists():
    month_ends = json.loads(dates_file.read_text(encoding="utf-8"))
else:
    df = yf.download("2330.TW", start="2011-12-01", end="2021-04-01", interval="1d", auto_adjust=False, progress=False)
    days = [d.strftime("%Y-%m-%d") for d in df.index]
    last = {}
    for d in days:
        last[d[:7]] = d
    month_ends = [last[k] for k in sorted(last)]
    dates_file.write_text(json.dumps(month_ends), encoding="utf-8")
log("月底交易日", len(month_ends), month_ends[0], "→", month_ends[-1])
assert month_ends[-1] <= "2021-03-31"

# ---------- 終止上櫃名單（上市那份探針已存）：試幾種參數，只記回來的筆數 ----------
for tag, url in [("tpex_delisted_default", "https://www.tpex.org.tw/www/zh-tw/company/deListed?response=json"),
                 ("tpex_delisted_date2018", "https://www.tpex.org.tw/www/zh-tw/company/deListed?date=2018&response=json"),
                 ("tpex_delisted_year2018", "https://www.tpex.org.tw/www/zh-tw/company/deListed?year=2018&response=json"),
                 ("tpex_delisted_all", "https://www.tpex.org.tw/www/zh-tw/company/deListed?date=&type=all&response=json")]:
    st = get(url, OUT / f"{tag}.json", lambda o: True)
    try:
        o = json.loads((OUT / f"{tag}.json").read_text(encoding="utf-8"))
        t0 = (o.get("tables") or [{}])[0]
        log(tag, st, "date", o.get("date"), "筆數", t0.get("totalCount"), "欄", t0.get("fields"))
    except Exception as exc:  # noqa: BLE001
        log(tag, st, "讀不出", type(exc).__name__)

# ---------- 月底行情 ----------
stat = {"ok": 0, "cached": 0, "other": 0, "error": 0}
for n, d in enumerate(month_ends, 1):
    if past_stop():
        log("到停止時間，停；已處理", n - 1, "/", len(month_ends))
        break
    ymd = d.replace("-", "")
    s1 = get(f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json",
             OUT / f"twse_{ymd}.json", lambda o: o.get("stat") == "OK" and len(o.get("tables") or []) >= 9)
    s2 = get(f"https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?date={d.replace('-', '/')}&id=&response=json",
             OUT / f"tpex_{ymd}.json", lambda o: o.get("stat") == "ok" and (o.get("tables") or [{}])[0].get("totalCount", 0) > 100)
    stat[s1] += 1
    stat[s2] += 1
    if n % 12 == 0:
        log("進度", n, "/", len(month_ends), d, stat)
log("結束", stat, "｜已存", len(list(OUT.glob("twse_*.json"))), "＋", len(list(OUT.glob("tpex_2*.json"))))
log("OFFICIAL_DONE" if not past_stop() else "OFFICIAL_STOPPED_BY_CLOCK")
```

#### fetch_delisted.py（sha256 前 16 碼 `dd10367d7d3bd9d2`）

```python
"""終止上櫃名單逐年抓（上市那份一次回全部，探針已存）。只存原始檔、只印筆數。對外請求不帶任何個人資訊。"""
import json
import shutil
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
OUT = HERE / "official"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}

src = HERE / "probe_twse_delisted.bin"
if src.exists():
    shutil.copyfile(src, OUT / "twse_delisted_all.json")
tw = json.loads((OUT / "twse_delisted_all.json").read_text(encoding="utf-8"))
print("終止上市", len(tw["data"]), "筆；欄", tw["fields"], "；最早", tw["data"][-1][0], "最晚", tw["data"][0][0])

total, by_year = 0, {}
for y in range(2007, 2027):
    f = OUT / f"tpex_delisted_{y}.json"
    if not f.exists():
        r = requests.get(f"https://www.tpex.org.tw/www/zh-tw/company/deListed?date={y}&response=json", headers=UA, timeout=60)
        time.sleep(4)
        if r.status_code != 200:
            print(y, "status", r.status_code)
            continue
        f.write_bytes(r.content)
    o = json.loads(f.read_text(encoding="utf-8"))
    t0 = (o.get("tables") or [{}])[0]
    ok = str(o.get("date")) == str(y)
    by_year[y] = (t0.get("totalCount"), "ok" if ok else f"回的是 {o.get('date')}")
    total += (t0.get("totalCount") or 0) if ok else 0
print("終止上櫃逐年：", by_year)
print("終止上櫃合計（年份對得上的）", total)
```

#### fetch_fin.py（sha256 前 16 碼 `90ea358254946f11`）

```python
"""H16 乾跑的資料段之五：損益表彙總（MOPS ajax_t163sb04，2013Q1..2020Q4）、缺的月營收頁（2014-05..2014-10）、
交易所產業分類、除權息與減資資料的探針。只存原始或最小轉寫，不算任何標記。
零 LLM；對外請求不帶任何個人資訊（UA 寫死；匯入 repo 抓取器前先把聯絡信箱環境變數蓋成佔位值）。到 04:40（台北）自動停。"""
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ["EDGAR_CONTACT_EMAIL"] = "research@example.com"
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[3]))

import requests  # noqa: E402

from fetchers.mops_open_data import fetch_monthly_revenue_month  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}
IS_DIR = HERE / "is"
IS_DIR.mkdir(exist_ok=True)
OFF = HERE / "official"
IS_URL = "https://mopsov.twse.com.tw/mops/web/ajax_t163sb04"
SEG = {"twse": "sii", "tpex": "otc"}
TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.I | re.S)
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
TAG = re.compile(r"<[^>]+>")
CODE = re.compile(r"^\d{4,6}$")


def log(*a):
    print(dt.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def past_stop():
    return dt.time(4, 40) <= dt.datetime.now().time() < dt.time(7, 0)


def txt(c):
    return TAG.sub("", c).replace("&nbsp;", " ").strip()


def num(s):
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


# ---------- 1. 損益表彙總（照 H12 的抓法：一般業版型，代號 → [累計營收, 累計營業毛利]） ----------
fails = []
for market in ("twse", "tpex"):
    for y in range(2013, 2021):
        for q in (1, 2, 3, 4):
            f = IS_DIR / f"is_{market}_{y}Q{q}.json"
            if f.exists() or past_stop():
                continue
            data = {"encodeURIComponent": "1", "step": "1", "firstin": "1", "off": "1", "isQuery": "Y",
                    "TYPEK": SEG[market], "year": str(y - 1911), "season": f"{q:02d}"}
            body = None
            for attempt in range(4):
                try:
                    r = requests.post(IS_URL, data=data, headers=UA, timeout=90)
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
            general, rejected = {}, {}
            for t in TABLE.findall(body):
                trs = ROW.findall(t)
                if not trs:
                    continue
                head = [txt(c) for c in CELL.findall(trs[0])]
                idx = {h: i for i, h in enumerate(head)}
                n_codes = sum(1 for tr in trs[1:] if CODE.match(txt((CELL.findall(tr) or [""])[0])))
                if not n_codes:
                    continue
                if "公司代號" in idx and "營業收入" in idx and "營業毛利（毛損）" in idx:
                    for tr in trs[1:]:
                        cells = [txt(c) for c in CELL.findall(tr)]
                        if not cells or not CODE.match(cells[0]) or len(cells) != len(head):
                            continue
                        general[cells[0]] = [num(cells[idx["營業收入"]]), num(cells[idx["營業毛利（毛損）"]])]
                else:
                    rejected[f"{len(head)}欄:{'｜'.join(head[2:4])}"] = n_codes
            f.write_text(json.dumps({"general": general, "rejected": rejected}, ensure_ascii=False), encoding="utf-8")
            log("損益表", market, f"{y}Q{q}", "一般業", len(general), "其他版型", sum(rejected.values()))
            time.sleep(2.5)

# ---------- 2. 缺的月營收頁 ----------
REV = HERE / "rev"
for y, m in [(2014, 5), (2014, 6), (2014, 7), (2014, 8), (2014, 9), (2014, 10)]:
    for market in ("twse", "tpex"):
        f = REV / f"rev_{market}_{y}-{m:02d}.json"
        if f.exists() or past_stop():
            continue
        try:
            rows = fetch_monthly_revenue_month(market, y, m)
            f.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            log("月營收", market, f"{y}-{m:02d}", len(rows))
        except Exception as exc:  # noqa: BLE001
            fails.append(f"rev {market} {y}-{m}: {exc}")
        time.sleep(1.0)

# ---------- 3. 產業分類（今天的版本）與 4. 除權息、減資資料的探針 ----------
PROBES = [
    ("sector_twse", "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"),
    ("sector_tpex", "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"),
    ("twse_exright_2015", "https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate=20150101&endDate=20151231&response=json"),
    ("twse_reduction_2011_2021", "https://www.twse.com.tw/rwd/zh/reducation/TWTAUU?startDate=20110101&endDate=20210331&response=json"),
    ("tpex_exright_2015", "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate=2015/01/01&endDate=2015/12/31&response=json"),
    ("tpex_reduction_2011_2021", "https://www.tpex.org.tw/www/zh-tw/bulletin/revivt?startDate=2011/01/01&endDate=2021/03/31&response=json"),
]
for name, url in PROBES:
    f = OFF / f"{name}.json"
    if f.exists() or past_stop():
        continue
    try:
        r = requests.get(url, headers=UA, timeout=90)
        time.sleep(5)
        if r.status_code != 200:
            log(name, "status", r.status_code)
            continue
        obj = json.loads(r.content.decode("utf-8", errors="replace"))
        f.write_bytes(r.content)
        if isinstance(obj, list):
            log(name, "list", len(obj), "欄", list(obj[0].keys())[:8] if obj else None)
        else:
            tables = obj.get("tables") or []
            n = len(obj.get("data") or []) or (tables[0].get("totalCount") if tables else None)
            log(name, "stat", obj.get("stat"), "筆數", n, "欄", (obj.get("fields") or (tables[0].get("fields") if tables else None)))
    except Exception as exc:  # noqa: BLE001
        log(name, "失敗", type(exc).__name__, str(exc)[:100])
log("失敗清單", fails)
log("FIN_DONE" if not past_stop() else "FIN_STOPPED_BY_CLOCK")
```

#### fetch_corp.py（sha256 前 16 碼 `78d47b77483f000b`）

```python
"""H16 乾跑的資料段之六：交易所的除權息計算結果表（逐年）。減資那兩份探針已抓到 2011–2021-03 全段。
只存原始檔、印筆數與一列樣本。對外請求不帶任何個人資訊。"""
import json
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
OFF = HERE / "official"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}

for y in range(2011, 2022):
    end = "0331" if y == 2021 else "1231"
    for name, url in ((f"twse_exright_{y}", f"https://www.twse.com.tw/rwd/zh/exRight/TWT49U?startDate={y}0101&endDate={y}{end}&response=json"),
                      (f"tpex_exright_{y}", f"https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ?startDate={y}/01/01&endDate={y}/{end[:2]}/{end[2:]}&response=json")):
        f = OFF / f"{name}.json"
        if not f.exists():
            for attempt in range(4):
                try:
                    r = requests.get(url, headers=UA, timeout=90)
                    time.sleep(5)
                    if r.status_code == 200 and json.loads(r.content.decode("utf-8", errors="replace")):
                        f.write_bytes(r.content)
                        break
                except Exception as exc:  # noqa: BLE001
                    print(name, "重試", type(exc).__name__)
                time.sleep(30 * (attempt + 1))
        if not f.exists():
            print(name, "抓不到")
            continue
        o = json.loads(f.read_text(encoding="utf-8"))
        t0 = (o.get("tables") or [{}])[0]
        data = o.get("data") or t0.get("data") or []
        print(name, "stat", o.get("stat"), "筆數", len(data), "樣本", [str(x)[:12] for x in (data[0][:5] if data else [])])
for name in ("twse_reduction_2011_2021", "tpex_reduction_2011_2021"):
    o = json.loads((OFF / f"{name}.json").read_text(encoding="utf-8"))
    t0 = (o.get("tables") or [{}])[0]
    data = o.get("data") or t0.get("data") or []
    print(name, "筆數", len(data), "樣本", [str(x)[:14] for x in (data[0][:5] if data else [])], "…", [str(x)[:14] for x in (data[-1][:5] if data else [])])
print("CORP_DONE")
```

#### fetch_bs.py（sha256 前 16 碼 `c71132cb192a4624`）

```python
"""H16 乾跑的資料段之三：事件公司的個別資產負債表（MOPS ajax_t164sb03），取存貨、資產總計、合約負債。
每個事件抓「t 當月底已過法定期限的最近一季」；合約負債要前一季時（2018Q2 以後、且當季有這一列、且不是第一季）再多抓一次。
原始 HTML 全部存檔（之後可重解析）。節流 3.5 秒；被擋就退避；**到 04:40（台北）自動停**，避開 daily 的寫入窗。
零 LLM；只寫 scratchpad；對外請求不帶任何個人資訊（UA 寫死，不讀環境變數）。"""
import datetime as dt
import json
import re
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
OUT = HERE / "bs"
OUT.mkdir(exist_ok=True)
URL = "https://mopsov.twse.com.tw/mops/web/ajax_t164sb03"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}
PACE = 3.5
STOP_AT = dt.time(4, 40)
THROTTLE = ("頻繁", "Overrun", "請稍後", "Too many")
NODATA = ("查無", "不存在", "無此", "沒有符合")


def log(*a):
    print(dt.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def past_stop():
    now = dt.datetime.now().time()
    return STOP_AT <= now < dt.time(7, 0)


from h16lib import known_quarter  # noqa: E402  法定期限嚴格早於 t 當月底的最近一季（三月用去年第三季）


def prev_quarter(y, q):
    return (y, q - 1) if q > 1 else (y - 1, 4)


def fetch(code, y, q):
    """回 (status, body)。status ∈ ok／nodata／unknown／error。存檔。"""
    f = OUT / f"{code}_{y}Q{q}.html"
    if f.exists():
        body = f.read_text(encoding="utf-8", errors="replace")
        return ("ok" if body.count("<tr") >= 20 else "cached_other"), body
    data = {"encodeURIComponent": "1", "step": "1", "firstin": "1", "off": "1", "keyword4": "", "code1": "",
            "TYPEK2": "", "checkbtn": "", "queryName": "co_id", "inpuType": "co_id", "TYPEK": "all",
            "isnew": "false", "co_id": code, "year": str(y - 1911), "season": f"{q:02d}"}
    for attempt in range(6):
        try:
            r = requests.post(URL, data=data, headers=UA, timeout=60)
            body = r.content.decode("utf-8", errors="replace")
        except requests.RequestException as exc:
            log("  連線錯誤", code, y, q, type(exc).__name__)
            time.sleep(20 * (attempt + 1))
            continue
        time.sleep(PACE)
        if r.status_code != 200 or any(w in body for w in THROTTLE):
            wait = 90 * (attempt + 1)
            log("  被擋或非 200（", r.status_code, "）退避", wait, "秒")
            time.sleep(wait)
            continue
        if body.count("<tr") >= 20:
            f.write_bytes(body.encode("utf-8"))
            return "ok", body
        if any(w in body for w in NODATA):
            (OUT / f"{code}_{y}Q{q}.nodata").write_text(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))[:300], encoding="utf-8")
            return "nodata", body
        (OUT / f"{code}_{y}Q{q}.unknown").write_bytes(body.encode("utf-8"))
        return "unknown", body
    return "error", ""


events = json.loads((HERE / ("events_all.json" if (HERE / "events_all.json").exists() else "events.json")).read_text(encoding="utf-8"))
todo = []
for e in events:
    y, q = known_quarter(e["t_ym"])
    todo.append((e["code"], y, q))
todo = sorted(set(todo))
log("事件", len(events), "→ 要抓的公司季", len(todo))
stat = {"ok": 0, "nodata": 0, "unknown": 0, "error": 0, "cached_other": 0, "second": 0, "skipped_done": 0}
status_log = {}
for n, (code, y, q) in enumerate(todo, 1):
    if past_stop():
        log("到停止時間，停；已處理", n - 1, "/", len(todo))
        break
    if (OUT / f"{code}_{y}Q{q}.nodata").exists() or (OUT / f"{code}_{y}Q{q}.unknown").exists():
        stat["skipped_done"] += 1
        continue
    st, body = fetch(code, y, q)
    stat[st] += 1
    status_log[f"{code}_{y}Q{q}"] = st
    if st == "ok" and (y, q) >= (2018, 2) and q != 1 and "合約負債" in body:
        py, pq = prev_quarter(y, q)
        st2, _ = fetch(code, py, pq)
        stat["second"] += 1
        status_log[f"{code}_{py}Q{pq}"] = st2
    if n % 25 == 0:
        log("進度", n, "/", len(todo), stat)
(HERE / "bs_status.json").write_text(json.dumps(status_log, ensure_ascii=False), encoding="utf-8")
log("結束", stat, "｜已存 HTML", len(list(OUT.glob("*.html"))))
log("BS_DONE" if not past_stop() else "BS_STOPPED_BY_CLOCK")
```

#### fetch_xbrl.py（sha256 前 16 碼 `7d4b932333c04e3a`）

```python
"""H16 乾跑的資料段之七：下市公司事件的 XBRL 財報檔（MOPS t164sb01），q0..q-3 四季；
另抽 12 筆今天還在的公司的 q0 當對照（驗證兩條路線的數字一致）。只存原始檔。對外請求不帶任何個人資訊。"""
import datetime as dt
import json
import time
from pathlib import Path

import requests

from h16lib import known_quarter, qshift

HERE = Path(__file__).parent
OUT = HERE / "xbrl"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-script"}
URL = "https://mopsov.twse.com.tw/server-java/t164sb01?step=1&CO_ID={c}&SYEAR={y}&SSEASON={q}&REPORT_ID={rid}"

events = json.loads((HERE / "events_all.json").read_text(encoding="utf-8"))
dele = [e for e in events if e["xcheck"].startswith("下市")]
surv = sorted((e for e in events if e["xcheck"] == "相符"), key=lambda e: (e["code"], e["t_ym"]))
sample = [surv[i * len(surv) // 12] for i in range(12)]
targets = []
for e in dele:
    y0, q0 = known_quarter(e["t_ym"])
    for k in range(4):
        targets.append((e["code"],) + qshift(y0, q0, -k))
for e in sample:
    targets.append((e["code"],) + known_quarter(e["t_ym"]))
targets = list(dict.fromkeys(targets))
(HERE / "xbrl_sample.json").write_text(json.dumps([[e["code"], e["t_ym"]] for e in sample]), encoding="utf-8")
print("目標", len(targets), "｜下市事件", len(dele), "｜對照", len(sample), flush=True)

stat = {"ok": 0, "nodata": 0, "error": 0, "skipped": 0}
for i, (code, y, q) in enumerate(targets):
    now = dt.datetime.now()
    if (now.hour, now.minute) >= (4, 40) and now.hour < 7:
        print("XBRL_STOPPED 到 04:40 停", stat, flush=True)
        break
    f, nd = OUT / f"{code}_{y}Q{q}.html", OUT / f"{code}_{y}Q{q}.nodata"
    if f.exists() or nd.exists():
        stat["skipped"] += 1
        continue
    got = False
    last = b""
    for rid in ("C", "A"):
        try:
            r = requests.get(URL.format(c=code, y=y, q=q, rid=rid), headers=UA, timeout=90)
            last = r.content
            time.sleep(4)
            if r.status_code == 200 and r.content.decode("big5", errors="replace").count("會計項目") >= 2:
                f.write_bytes(r.content)
                (OUT / f"{code}_{y}Q{q}.rid").write_text(rid, encoding="utf-8")
                got = True
                break
        except Exception as exc:  # noqa: BLE001
            print(code, y, q, rid, "失敗", type(exc).__name__, flush=True)
            stat["error"] += 1
            time.sleep(20)
    if got:
        stat["ok"] += 1
    else:
        nd.write_bytes(last[:600])
        stat["nodata"] += 1
    if i % 20 == 0:
        print(dt.datetime.now().strftime("%H:%M:%S"), i, "／", len(targets), stat, flush=True)
else:
    print("XBRL_DONE", stat, flush=True)
```
