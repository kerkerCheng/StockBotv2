# Coverage Pilot — Evidence → … → Analyst View 是否只對 COHR 成立

- **日期：** 2026-09-07
- **授權：** pq2 **[484]**（使用者 2026-09-07 明示指示；鑄號僅為稽核，受理時即 `go` resolve）
- **標的：** LYC.AX（Lynas Rare Earths）、6324.T（ハーモニック・ドライブ・システムズ）、IQE.L（IQE plc）
- **判定：GO**
- **刻意不做：** APP／API（Step 5）、Portfolio、Post-MVP Alpha Edge、任何新的 valuation method
  或金融模型、graph admission、thesis／variant view 變更、資本動作。

> **這份 Pilot 要買的不是覆蓋率。** 到 Step 4 為止整條鏈只在 COHR 一檔上跑過，
> 所有「fail closed」都是在**同一組資料形狀**上驗的。成功的定義是：
> **對不同資料形態，系統要嘛產生可追溯的完整 view，要嘛在正確的層級明確 fail closed**——
> 不能靠 COHR-specific assumption 或 hidden default 假裝泛化。
> 結果是 **1 檔完整、2 檔在正確的層級 blocked**，
> 並在過程中揪出 **6 個 generic 缺陷，其中 4 個會產生看起來確定、實際錯誤的數字**。
>
> ⚠ **本報告自己犯過一次 L11-4 並修正：** 第一版判定「IQE.L 沒有年報」，依據是官方 IR 頁
> JS 動態載入、`href="*.pdf"` 0 命中。**實際上年報的直接 URL 早就在自家庫裡**
> （`library/raw/iqe_ar2025_raw_material_counterpath.txt` 的 `Source URL`）。
> 「追源前先 grep 自家庫」不是文件裡的一句話，是這次真的漏掉的一步——修正後 IQE 的基期建立完成，
> 並因此再揪出第 6 個 generic 缺陷（§3.6）。

---

## 1. 為什麼選這三檔

候選池：`config/company_identity.json` 100 家中 34 家 USD、22 家非 USD、44 家未上市。
篩選條件是**資料形態**而不是投資吸引力，且刻意避開「三檔都是 AI 光互連」——
Pilot 測的是 architecture applicability，不是擴同一個 thesis。

| 標的 | 選它的理由 | 預期會撞到什麼 | 實際撞到什麼 |
|---|---|---|---|
| **LYC.AX**（稀土開採冶煉，ASX） | 商業模式與 COHR 最遠：**價格接受者**、單一報導分部、AASB／IFRS、AUD、6 月會計年度；一手 FY2026 Appendix 4E 已在 `library/raw/` | 分部模型不適用；商品價格是模型最大變數但系統對它沒有 authority | 兩者都成立，但**整條鏈仍然走得完**（total scope ＋ 明示 session judgment）。**Analyst View ready** |
| **6324.T**（諧波減速機，東證） | 產業與 COHR 完全不同（機器人）；JPY；**3 月**會計年度；日本基準（経常利益／特別損益）；報導分部是**所在地別**；圖裡只有 1 條邊 | 日本基準的損益結構塞不進 v1 的橋；分部軸不一致 | 橋塞得進去（`interest_and_other_net` 夠通用），但**揪出共識資料的合併範圍錯誤**（見 §3.3），且**目標倍數無證據可錨 → 刻意不寫**。**blocked at valuation** |
| **IQE.L**（III-V 磊晶，AIM） | 唯一一檔報價單位是 **minor unit（GBp）** 的持股；分析師預估**兩個年度都是虧損**；EPS 以**便士**計，是全池唯一的小尺度 EPS | 報價單位 ≠ 結算幣別的 100 倍陷阱；本益比法對虧損公司無定義 | 兩者都證實，且**兩者原本都不會被擋**（見 §3.1、§3.2）；另外揪出口徑判定的容忍度在便士級失效（§3.6）。**基期已建立，blocked at model applicability** |

⚠ 相關性揭露：IQE.L 與 COHR 同屬化合物半導體／光通訊上游，兩者不是獨立標的；
LYC.AX 與 6324.T 與 COHR 無供應鏈關係。選 IQE 不是為了擴 thesis，是因為它是本圖裡
**唯一**能讓 GBp 路徑走真資料的持股。

---

## 2. 逐檔泛化報告

### 2.1 LYC.AX — Lynas Rare Earths｜**Analyst View ready**

| 面向 | 結果 |
|---|---|
| fiscal-period identity | 基期 FY2026（至 **2026-06-30**）→ 目標 FY2027（至 **2027-06-30**）。與 COHR 同為 6 月制，`FiscalPeriod.shifted(1)` 正確 |
| accounting basis | **`gaap`**——實際是 AASB／IFRS。字彙是美式的，語意上 `gaap` ＝「as reported」、`non_gaap` ＝「公司調整後」（見 §4.1） |
| quote unit／currency | `market_currency=AUD`、`execution_currency=AUD`、`execution_venue=ASX`；報表幣別 AUD。`units_comparable("AUD","AUD") = comparable` |
| consensus availability | ✅ Engine C `consensus_estimates` 4 列（EPS／營收 × 0y／+1y）。FY2027 EPS 共識 0.565（13 位）、營收 A$1,650.8M（13 位） |
| base actual quality | ✅ **tier 1 一手**：FY2026 Appendix 4E／Annual Report（董事會 2026-08-26 於 Brisbane 簽署；目錄列有 Independent Auditor's Report，本次未逐字核對其意見類型）。損益表逐行 ＋ Note A.1／A.3／A.4。`mo_468c4a7c84b39c90d8246b454206ff6a` |
| consensus 對帳 | ✅ EPS `year_ago_actual` **0.2206 ＝** 一手稀釋 EPS 22.06 分／股 → 口徑判定 `gaap`；營收 `year_ago_actual` 977,900,000 vs 一手 977,945,000（差 0.005%）→ 對帳通過 |
| operating assumptions provenance | 6 條，全部 supporting ref 指回 `mo_468c…`（＋ JARE ASX 公告與 `supplies_to` 邊）。3 條 `session_judgment`（revenue_growth +43%、operating_margin_delta +16.0pp、tax_rate 22%）、3 條 `heuristic_proxy`。同期共識只出現在 `calibration_refs` |
| valuation method 適用性 | ✅ 適用。內部 FY2027 稀釋 EPS **0.4522** 為正；`target_pe = 22.0x`（`session_judgment`），fair value **A$9.949** |
| horizon semantics | `value_date_convention=target_period_end` → value_date **2027-06-30**；horizon 判斷取同一日（`aligned`），持有期 296 天 |
| implied return | 現價 **A$15.62**（bar 2026-09-07）→ **−36.3% simple／−42.7% 年化**；`input_dependency=session_judgment` |
| Analyst View readiness | **ready**（blockers 空）。entry `missing` 但 optional，不計入 |
| missing／not_modeled／review_required | `not_modeled`：內部毛利率、內部 FCF、total return、機率加權期望報酬、內部 vs 價格隱含。`missing`：營益率共識（Engine C 無此指標共識）、entry criterion（optional）。`review_required`：無 |

**這一檔證明了什麼：** 非美元、非美國會計準則、單一報導分部、價格接受者商業模式，
整條鏈**一格 COHR-specific 假設都沒用到**。`revenue_growth` 走 `total` scope、
`interest_and_other_net` 走**負值**（Lynas 是淨財務收益，COHR 是淨費用）、
`nci_attribution` 明示為 0——三個地方都證明 driver 契約本身是通用的。

**研究面的誠實話：** 這一檔最大的單一變數是 FY2027 的稀土實現價格，而它是時變市場觀測——
**Engine A 依 L4（屬性歸位：時變數字不入圖）不收、Engine C 也沒有稀土價格序列，本系統對它沒有 authority。**
假設只能以年報揭露的期末價位（NdPr 中國內銷價 2026-06 為 US$100.8/kg）與已簽約下限價
（JARE US$110/kg）當錨。這不是資料缺漏，是**這個商業模式與本系統能力邊界的真實交會點**，
已逐字寫在 `oa_a9de11465274887a` 的 rationale 裡。

**另一個結構觀察：** 對價格接受者而言，`revenue_growth` 與 `operating_margin_delta`
**不是獨立輸入**——兩者的主導變數同為實現售價。橋的敏感度分析逐條微擾會低估真實的聯合風險。
本次的處理是讓兩條假設共用同一個 machine-readable `review_condition`
（Q2 FY27 季營收 < A$300M → review），並在 rationale 逐字寫明它們不獨立。

### 2.2 6324.T — Harmonic Drive Systems｜**blocked at valuation（刻意）**

| 面向 | 結果 |
|---|---|
| fiscal-period identity | 基期 FY2026（至 **2026-03-31**）→ 目標 FY2027（至 **2027-03-31**）。**3 月制**，`shifted(1)` 正確；`label="FY2027"` 與日文「2027年3月期」一致 |
| accounting basis | **`gaap`**——實際是**日本基準**。損益結構多兩層（経常利益／特別損益），見 §4.2 |
| quote unit／currency | `market_currency=JPY`、`execution_venue=TSE`；報表幣別 JPY。`comparable` |
| consensus availability | ✅ 4 列。FY2027 EPS 69.28（9 位）、營收 74,682M（9 位） |
| base actual quality | ✅ **tier 1 一手**：2026年3月期 決算短信（TDnet 2026-05-13）連結損益計算書逐行。⚠ **決算短信不受會計師查核**（文件自述），有価証券報告書（2026-06-16 提出）**未取得**。`mo_fe968212bf73ba34861db56944a568d0` |
| consensus 對帳 | ⚠ **一半通過一半不通過**。EPS `year_ago_actual` **16.99 ＝ 連結** EPS → 口徑判定 `gaap`、比較成立；營收 `year_ago_actual` **33,438,000,000 ＝ 單體**（決算短信第 2 頁「(参考) 個別業績の概要」），連結營收是 **59,557,877 千円**，差 **−43.9%** → **`unreconciled_base`，營收不比較**（這道 gate 是本 Pilot 新增的，見 §3.3） |
| operating assumptions provenance | 6 條。**2 條 `observation`**——值直接等於公司自家 FY2027/3 通期連結業績予想（売上高 68,000 百万円、営業利益 6,200 百万円），不是我們的獨立判斷；4 條 `heuristic_proxy`。**0 條 `session_judgment`** |
| valuation method 適用性 | ⛔ **型別上適用，但無法錨定，故刻意不寫**。內部 FY2027 EPS **47.32** 為正；但現價 ¥5,970 對它是 **126.2x**（`implied_multiple_at_price`），任何合理區間（30–80x）的倍數都會產出 −50%～−80% 的 gap，而那個數字的資訊**全部來自隨手選的倍數**。要定倍數需要 FY2029+ 的獲利能力證據（客戶端量產承諾、單機用量、份額）——圖裡沒有，共識只到 +1y |
| horizon semantics | 未寫（沒有 fair value 就沒有可實現的目標值） |
| implied return | `missing` |
| Analyst View readiness | **blocked**：`headline: missing`（無估值假設）、`why: missing`（valuation／implied_return 缺席）。**`fundamental` 與 `research` 兩段 available** |
| missing／not_modeled／review_required | `missing`：fair value、value_date、horizon、implied return、entry、營收比較（`unreconciled_base`）、營益率共識。`not_modeled`：同 LYC。`review_required`：無 |

**這一檔證明了什麼：** ① **橋的 driver 契約塞得下日本基準**——`interest_and_other_net`
一格同時承載営業外損益與特別損益，本次刻意只沿用**経常性**的営業外損益、把特別損益排除
（FY2026/3 有 減損損失 526,923 千円與 棚卸資産評価損 293,364 千円；外推非經常項等於預測明年會再減損一次），
並在 rationale 逐字寫明。② **公司指引可以當一等公民的 `observation` 來源**，
讓內部估計不必是 session judgment。③ **「刻意不估值」是研究結論，不是未完成的工作**——
而系統目前把它和「還沒寫」顯示成同一句話（§4.3）。

**expectation gap 的實質內容：** 內部 FY2027 EPS 47.32 ≈ 公司指引 47.54；賣方共識 69.28
**比公司自家指引高 46%**。⚠ 這不是「我們發現了利多的錯價」——日本企業的期初通期予想向來偏保守、
期中上修是常態，而「這次也會上修」是我們**沒有系統內證據**可以支持的主張。判斷檔的
`expectation_gap` 因此給 **weak**，並把這個推理逐字寫進 reason。

### 2.3 IQE.L — IQE plc｜**blocked at model applicability（基期已建立）**

| 面向 | 結果 |
|---|---|
| fiscal-period identity | 基期 FY2025（至 **2025-12-31**）→ 目標 FY2026（至 **2026-12-31**）。**12 月制**；`shifted(1)` 與共識的 0y 對得上 |
| accounting basis | 基期同時有 `gaap`（as reported，IFRS）與 `non_gaap`（公司 adjusted）兩塊。橋會選 `non_gaap`（該塊有 `operating_income`），與共識判定一致 |
| quote unit／currency | ⚠ **`market_currency = "GBp"`（便士，minor unit）**，registry 無 `execution_currency`／`execution_venue`。**報表幣別是 `GBP`**，共識的 `currency` 也是 `GBP`。**兩者差 100 倍**，且年報本身把 EPS 印成便士（`(3.77p)`）——寫入時已換算成 GBP（−0.0377）並在 `unit_note` 逐字註明 |
| consensus availability | ✅ 4 列。FY2026 EPS **−0.01158 GBP**（3 位）、FY2027 EPS **−0.00196 GBP**（3 位）；營收 £128.2M（+31.8%）／£151.2M |
| base actual quality | ✅ **tier 1 一手**：Annual Report and Accounts 2025（查核報告日 2026-05-28）合併損益表逐行 ＋ Note 4.3 分部 ＋ Note EPS／加權平均股數。`mo_48bb916496c97b4cef20d1fda140b3d5`。⚠ 取得路徑見上方 L11-4 的自我修正 |
| consensus 對帳 | ✅ **兩項都通過**。EPS `year_ago_actual` **−0.0282 ＝** 一手 **adjusted** 稀釋 EPS（2.82p）→ 口徑判定 `non_gaap`（⚠ 這個判定原本會失敗，見 §3.6）；營收 `year_ago_actual` **97,300,000 ＝** 一手營收，逐字相等 |
| operating assumptions provenance | **0 條，刻意不建**——這是研究決定，理由見下 |
| valuation method 適用性 | ⛔ **結構性不適用**：唯一登記的 method 是 `forward_earnings_multiple`，要求正的 forward EPS；而分析師對 IQE **兩個建模年度都預估虧損**（−0.01158／−0.00196 GBP），基期本身也是虧損（adjusted −0.0282）。**補資料解不掉這一條** |
| horizon semantics／implied return | `missing` |
| Analyst View readiness | **blocked**：headline／fundamental／why／research 四段全 missing。⚠ 但**共識段落已完全可用**，且口徑正確標成 `non_gaap` |
| missing／not_modeled／review_required | `missing`：內部估計全鏈（無 operating assumption）、fair value、horizon、implied return、entry。`not_modeled`：同 LYC。`review_required`：無 |

**為什麼刻意不建 operating assumptions（這是研究決定，不是沒做完）：**

1. **無論假設是什麼，估值層都會拒絕。** 內部 EPS 一定是負的（基期 adjusted −0.0282、
   共識對兩個建模年度都預估虧損），而唯一登記的 method 對非正盈餘無定義（§3.2）。
   一組 forecast 只會餵給共識比較那一格。
2. **更關鍵：本次刻意沒有完成 IQE 的流動性／going-concern 評估。**
   年報查核報告該段是雙欄重疊排版，可逐字讀出的只有兩件事——查核人員**評估過**
   「償還既有 loan notes 與 facilities 所需的再融資」是否構成 material uncertainty，
   以及「We inspected confirmation of the **waiver of the December 2025 covenant requirements**
   by the Group's lenders in that month」。**是否實際出具 material uncertainty 陳述，
   本次抽取無法判定。** 依 L11-1（具體審計術語的措辭精度本身就是一個 claim），
   不得推論、不得沿用二手措辭。
   **在那個問題沒解決之前對一家上一個報告期才被債權人豁免 covenant 的公司做盈餘預測，
   正是 L11-2 記過的「對外部 claim 嚴、對自己引用鬆」。**

因此 IQE 的 forward view 另鑄 pq2 提案（**[486]**），等使用者決定是否啟動。

**這一檔證明了什麼：** 它是**唯一**能讓 §3.1 的 100 倍陷阱與 §3.6 的尺度陷阱走真資料的持股，
而**兩個陷阱原本都不會被擋**。它也示範了 blocker 的分層：補齊年報解掉了資料層，
方法層的 blocker 一動也沒動——那正是「資料問題」與「model applicability」必須分開報告的理由。

## 3. 發現的 generic 缺陷（全部已修 ＋ 已測）

> 六個缺陷的共同形狀：**它們在 COHR 上都不可能出現**。COHR 是 USD 報價、獲利、
> 美國 GAAP、EPS 以美元計、有目標倍數、且確實屬於 AI 光互連——每一個缺陷的觸發條件
> 它剛好都不滿足。這正是 Pilot 的價值：**單一標的上的「全綠」不構成泛化證據。**

### 3.1 報價單位判準自己折疊了大小寫（correctness／嚴重）

`alpha/valuation/model.py::units_comparable` 原本寫 `a.upper() != b.upper()`。
於是 **`GBp`（便士）與 `GBP`（英鎊）被判為同尺度**——而**那正是這道 gate 唯一要擋的 case**。
`GBX`／`ILA`／`ZAc` 之所以被攔下，是因為字母剛好不同，不是因為判準對。

實測後果（重現腳本已成測試）：fair value **0.05 GBP** 對現價 **47.518 GBp** 被判 `comparable`，
`relative_gap` 算成 **−99.9%**，並以〔確定性規則〕呈現成隱含報酬。

**這是 L16（分類已有 SSOT 時要讓它跟著資料走）的教科書形狀**：
`identity/currency.py` 早就是唯一的 quote-unit registry
（`config/currency_units.json`，大小寫敏感，且註解逐字寫著「折疊會讓結算幣別被誤判成 minor unit」），
但**那個分類沒有跟著資料走到估值層**，於是估值層自己記了一份，而重造品立刻開始偏離。
⚠ golden fixture `minor_unit_quotes.json` 守的是 registry 本身，**不是它的消費端**——
所以它一直是綠的。

**修法：** `units_comparable` 改為呼叫 `resolve_quote_unit()`；結算幣別不同 → `incompatible_unit`，
同幣別但 factor 不同（GBP vs GBp）→ `incompatible_unit` 並寫出「差 100 倍」；
任一邊解析不出來 → `unverified_unit`。**本層仍然不換算。**
測試以 `config/currency_units.json` 參數化——日後新增一個 minor unit 即自動受測。

### 3.2 本益比法被套在虧損公司身上（correctness／嚴重）

`_fair_value()` 對 `forward_earnings_multiple` 就是 `eps × target_pe`，**沒有任何
盈餘為正的前提**。`target_pe` 的 `ParameterSpec` 有 `lower=0.0`（擋負倍數），但**負 EPS 沒人擋**。

實測後果：內部 EPS −0.02 × 25x → fair value **−0.40**，`status='available'`，
gap 判 **`comparable`**、`relative_gap` **−100.8%**、`implied_multiple_at_price` **−2,375.9**。
**一個做多部位不可能跌超過 100%**——那不是估值結果，是把方法套在它不適用的資料上。

**修法：** 新增 `alpha/valuation/contracts.py::method_applicability(method, value)`。
它與「缺料」刻意分成兩種語意（L12：一個表示不得承載兩種語意）：
缺料＝我們還沒算出這個數；不適用＝數算出來了，但這個 method 套在它身上沒有意義。
訊息也分得開（測試逐字斷言「不適用」不含「缺席」、反之亦然）。
虧損公司要估值需要另一個 method（EV/Sales、DCF…），**v1 沒有，本次也不加**。

### 3.3 共識的營收從來沒有跟基期對過帳（correctness／中）

`verify_consensus_basis` 用 `year_ago_actual` 判 EPS 口徑，**順帶**也對了帳
（對不上就是 `unverified` → `incompatible_basis`）。**營收沒有口徑之分，於是什麼都沒對**——
直接回 `not_applicable`，比較照減。

6324.T 實測：**同一批 yfinance 共識紀錄裡，EPS 的 `year_ago_actual` 16.99 是「連結」、
營收的 `year_ago_actual` 33,438,000,000 是「單體」**，而連結營收是 59,557,877 千円，
差 **−43.9%**。更糟的是那一年的營收**估計值** 74,682M 又高於公司自家的連結指引 68,000M，
所以估計值本身看起來是連結的：**這筆紀錄內部就不自洽**。

**修法：** 新增 `reconcile_consensus_base()`，只管營收（EPS 已由口徑判定覆蓋，
再做一次會讓同一個問題有兩個名字）；對不上回新的比較狀態 **`unreconciled_base`**，
訊息寫出差幾 %、並列出常見成因（單體 vs 合併、重編、幣別）。**不猜、不換算。**

**量測（L14：這會讓哪個現有數字變？）：** 對所有已有基期的標的實跑——
COHR FY2027 營收 **通過**、LYC.AX FY2027 營收 **通過**、6324.T FY2027 營收 **攔下**。
**3 個裡改變 1 個**：不是恆亮的牆，也不是永遠不會響的閘門。

⚠ 同一次修改在讀模型端補了 `_COMPARISON_STATUS_TO_DATUM["unreconciled_base"]`——
那張表是**直接索引**（不是 `.get`），漏一個就是整個 fundamental section 在該檔上爆掉。
已加測試斷言它涵蓋 `COMPARISON_STATUSES` 全集（同樣是 L16：字彙有 SSOT 就不要在下游自己記）。

### 3.4 「市場為我們的 EPS 付幾倍」被綁在 fair value 存在才算（可用性／中）

`implied_multiple_at_price = 現價 ÷ 內部 EPS` 是**純算術**，不需要目標倍數。
但它原本寫在 `if gap.is_known` 之下——於是「沒有目標倍數」這件事同時把它也一起藏掉了，
**而那正是最需要看它的時候**：6324.T 的 126.2x 才是「為什麼沒有可錨定的目標倍數」的直接證據。

**修法：** 條件改成「現價已知 ＋ 內部 EPS **為正** ＋ 單位同尺度」，並額外走 `ValuationStep`
（trace 是既有通道，讀模型 schema 不變）。
⚠ `> 0` 不是防禦性程式碼：測試以 −0.02 代入得到 **−14,093x**，負的本益比與負的 fair value
是同一種無意義——**這個 bug 是我自己的第一版修法引進的，被同一批測試當場擋下**。

**量測：** COHR 31.5x（原本就有，值不變）、LYC.AX 34.5x（原本就有）、
**6324.T 126.2x（原本沒有，現在有）**。3 個裡改變 1 個。

### 3.5 相關性警語無條件斷言每一檔都屬於 AI 光互連（呈現正確性／低但是假話）

`CORRELATION_WARNING` 是常數，掛在**每一檔**的單檔 Analyst View 上：
「本圖標的高度集中於 AI 光互連：列出 N 檔不等於 N 個獨立機會」。
對 **LYC.AX（稀土開採）與 6324.T（機器人減速機）這是一句假話**。

⚠ **修法刻意不是「按產業條件化」**：那需要一份「這檔屬於哪個群」的分類，而系統沒有那個 SSOT，
在下游自己猜一份正是 L16 記過的形狀。改成把主詞放回**這份圖的組成**，
並明寫「不是對本檔所屬產業的斷言」——對任何一檔都為真，且 AGENTS.md
「相關性警告每次都要講、不因每天一樣而省略」的要求不變。

### 3.6 口徑判定的絕對容忍是以美元級 EPS 校準的，在便士級把判準稀釋掉（correctness／中）

`verify_consensus_basis` 用 `math.isclose(rel_tol=0.01, abs_tol=0.011)` 把 provider 的
`year_ago_actual` 對一手的 GAAP／non-GAAP 稀釋 EPS 比對，**剛好命中其中一個**才判定口徑。
`abs_tol=0.011` 是拿 COHR 校準的——美元級 EPS 印到分位，0.011 剛好蓋住一次進位。

IQE.L 實測：一手 GAAP 稀釋 EPS **−0.0377**、adjusted **−0.0282**，兩者**只差 0.0095 < 0.011**
→ 兩個候選一起命中 → 函式回 **`unverified`**。
而 provider 的 `year_ago_actual` **−0.0282 精確等於 adjusted**——
**那不是「無法判定」，是尺度把判準稀釋掉了**（L15-1：這個 gate 攔下的不是它想攔的東西）。
後果是 fail closed（方向對）但理由誤導，而且它會對**每一個以便士／agorot／分計價的發行人**
都這樣做——正好是 `config/currency_units.json` 登記的那一整類市場。

**修法：** `_BASIS_MATCH_ABS_TOL` **0.011 → 0.0**，只留相對容忍。
相對容忍本身與尺度無關，是正確的判準；`math.isclose` 對 0.0 vs 0.0 仍為真、
對 0.0 vs 任何非零仍為偽，所以「EPS 恰為零」的邊界不需要靠絕對容忍撐。

**量測（L14）：** 對四檔有基期的標的逐一實跑 `abs_tol=0.011` vs `0.0`——
COHR（non_gaap）、LYC.AX（gaap）、6324.T（gaap）**三檔完全不變**；
**IQE.L FY2026 由 `unverified` 變成 `non_gaap`**，也就是可證明正確的那個答案。
**4 個裡改變 1 個。**

---

## 4. COHR-special-case 清點（結構觀察，本次**不修**）

> 這一節列的是**已知的適用性邊界**，不是 bug。每一條都寫出「為什麼現在不動」。

### 4.1 `accounting_basis` 字彙是美式的

`ACCOUNTING_BASES = ("gaap", "non_gaap", "not_applicable", "unverified")`。
Lynas 是 AASB／IFRS、HDS 是日本基準、聯亞是台灣 IFRS——三者都被標成 `gaap`。
語意上它其實是「as reported（法定）」vs「公司調整後」，功能完全正確；
但**面向使用者的字面是錯的**。
**現在不動的理由：** 這是封閉字彙，且已寫進三本 private append-only ledger 的每一筆紀錄
（`accounting_basis` 是假設身分的一部分）。改字彙等於改既有紀錄的身分，違反 L10
（private ledger 只能 append）。正確做法是加一層呈現別名，屬 Step 5 呈現層的事。

### 4.2 日本基準的損益結構與 v1 的橋不是一對一

日本基準是 `営業利益 →（営業外損益）→ 経常利益 →（特別損益）→ 税金等調整前当期純利益`，
而 v1 的橋只有一格 `interest_and_other_net`。本次的處理是**只沿用経常性的営業外損益、
把特別損益排除**，並在 rationale 逐字寫明——**這是對的做法**，
但它是靠寫假設的人記得，不是靠契約強制。
**現在不動的理由：** 多一個 driver 就要多一段橋的算術（driver 是 contract 不是 taxonomy），
而目前只有一個實例。要動應等到第二個日本基準標的出現。

### 4.3 「刻意不寫估值假設」與「還沒寫」是同一句話

6324.T 的 blocker 逐字是「尚未寫入任何估值假設（forward_earnings_multiple.target_pe）」。
但本次的真實狀態是**研究結論：無法錨定倍數，所以不寫**。
**兩種語意共用一個表示（L12），而下一個讀者無從分辨。**
**現在不動的理由：** 修法是給 ValuationAssumption ledger 增加一種 `declined` 紀錄
（帶理由與 disproof：什麼證據出現才會改寫），那是**新增能力**不是修 bug，
使用者已明示本次不新增。**已寫進 ROADMAP 待排。**
本次的緩解：理由逐字寫在 `library/private/alpha/judgments/6324.T.json` 的 `risks[0]`
與 `thesis` 裡，而那兩段會在 Analyst View 的 research 段落顯示。

### 4.4 分部軸沒有宣告，而同一家公司可以有兩種軸

6324.T 的 `segment_revenue_share`（Q3 earnings_exposure 用）是**產品線別**
（減速装置 77.8%／メカトロニクス 22.2%），而 `fiscal_year_results.segment_revenue`（橋用）
是**所在地別**（日本／中国／北米／欧州，因決算短信注 3 載明「事業の種類別セグメントは単一」）。
兩個欄位裝著兩種分部軸，**而欄位本身沒有宣告軸別**。
今天不會出錯（HDS 走 `total` scope），但若有人寫 `revenue_growth[減速装置]`，
橋會找不到對應的基期分部而報 missing——fail closed 但訊息會誤導。
**現在不動的理由：** 需要在 `config/engine_c_observation_fields.json` 為兩個欄位加
`segmentation_axis` 宣告並在橋比對，屬字彙擴充；只有一個實例，先記錄。

### 4.5 `FiscalPeriod.label = f"FY{end.year}"` 是命名慣例，不是身分

三檔都對得上（LYC FY27 ＝ 2027-06 ✓、HDS「2027年3月期」✓、NVDA fiscal 2027 ＝ 2027-01 ✓），
但對**1 月底結帳的零售商**（多數稱該年度為前一年）會標錯。
身分是 `end` 日期、`label` 只是呈現，所以不影響任何計算。
**現在不動的理由：** 圖裡沒有這種標的；先記錄判準，不做預防性抽象。

### 4.6 軸判斷的 evidence scope 排除了最豐富的那份文件

`packet.evidence_scope` 把 `engine_c://manual_observation/` 排除在四軸判斷之外
（理由正確：ResearchContext 先建、模型層後擴充，反向會循環）。
後果是 **LYC.AX 與 6324.T 的 `catalyst` 軸都只能回 `unknown`**——
兩檔已知的、有日期的前瞻事件（Lynas 的 Sm 氧化物 Q1 FY27 首批交付、
HDS 的 H1 FY27 予想在 2026-11 被驗證）都只住在年報／決算短信裡。
**這是 deliberate boundary 的真實代價，本次把它量出來了。**
**現在不動的理由：** 放寬 resolver 會製造 provenance 循環。正解是把這些文件走 graph admission
變成 SourceDoc——那是人工 gate，需要使用者核准，不在本次授權範圍。

---

## 5. 哪些能力真的泛化了

| 能力 | 泛化證據 |
|---|---|
| **會計期間身分** | 6 月制（LYC）／3 月制（HDS）／12 月制（IQE）三種都正確解析；`shifted(1)` 與 `same_as`（±10 天容忍）在三種曆上都對 |
| **財務橋的 driver 契約** | 單一分部（LYC）與地理分部（HDS）都能走 `total` scope；`interest_and_other_net` 承載**負值**（淨財務收益）與日本基準的営業外損益；`nci_attribution=0` 可明示宣告而不與「缺假設」混淆 |
| **假設 provenance 三態** | 同一批六條 driver 在 LYC 以 `session_judgment` 為主、在 HDS 以 `observation`（公司指引）為主——`input_dependency` 逐格傳播正確（HDS 的內部營收標 `observation`、內部 EPS 標 `heuristic_proxy`，因為股數是代理） |
| **共識口徑機械核實** | 四種市場、四種幣別都以 `year_ago_actual` 對一手稀釋 EPS 成功判定口徑（COHR 5.61 → non_gaap、LYC 0.2206 → gaap、HDS 16.99 → gaap、**IQE −0.0282 → non_gaap，且 EPS 尺度小到 0.03**） |
| **共識與基期的量對帳** | 四檔逐筆比對 `year_ago_actual` 與一手營收：COHR／LYC／IQE 逐字相等，6324.T 差 −43.9% 而被攔下 |
| **幣別／報價單位分離** | AUD／JPY 走 `comparable`；GBp 走 `incompatible_unit`（修正後） |
| **fail closed 的層級正確性** | 四種不同的 blocker 落在四個不同層級：對帳層（6324.T 營收 `unreconciled_base`）、方法層（IQE 負 EPS）、證據層（6324.T 錨不住倍數）、研究前置（IQE 流動性未評估），**沒有一個被壓成同一個 `unavailable`**；而 IQE 的資料層 blocker 補上年報後**單獨消失、其餘三個不動** |
| **第二檔不污染第一檔** | **COHR baseline 核心 10 格一格未動**（見 §7） |

## 6. 哪些 blocker 是資料問題、哪些是 model applicability

| 標的 | blocker | 分類 | 補什麼才會解掉 |
|---|---|---|---|
| ~~IQE.L 無 `fiscal_year_results`~~ | **資料** | ✅ **本次已解**：年報直接 URL 早在自家庫裡（L11-4），已建立基期 `mo_48bb9164…` |
| IQE.L | 唯一 method 要求正 forward EPS，而共識兩年皆虧損 | **model applicability** | 需要新的 valuation method（EV/Sales 或 DCF）——**補資料解不掉** |
| IQE.L | 無 operating assumption（刻意） | **研究前置**：流動性／going-concern 未評估 | pq2 **[486]**——先做 IQE 的流動性評估（covenant waiver、CLN、RCF），再談 forward view |
| 6324.T | 營收 `unreconciled_base` | **資料**（provider 側：yfinance 混用單體／連結） | 換共識來源，或人工建立連結口徑的營收共識觀測 |
| 6324.T | 無 `target_pe`，故無 fair value | **model applicability ＋ 證據不足** | 需要 FY2029+ 獲利能力證據才錨得住倍數；或 v2 加 mid-cycle／multi-year 概念 |
| LYC.AX、6324.T | `catalyst` 軸 `unknown` | **架構邊界**（evidence scope） | 把年報／決算短信走 graph admission 變成 SourceDoc（人工 gate） |
| 三檔 | 營益率共識 `consensus_missing` | **資料**（provider 不提供） | 無便宜解；已明標為 missing 而非 0 |
| 三檔 | entry criterion `missing` | **設計如此**（optional，不計入 core readiness） | 使用者宣告要求報酬判準時才建 |

---

## 7. Baseline 回歸（ROADMAP 對 Coverage Pilot 的硬性驗收）

> ROADMAP 的驗收條件逐字是：「**每加一檔，既有那幾檔的 baseline 數字必須 0 格改變**」。

| COHR 核心格 | Step 4 收盤值 | Pilot 後實測 | |
|---|---|---|---|
| 內部 FY2027 稀釋 EPS | 8.9441 | **8.94413801476208** | ✅ |
| FY2027 EPS 共識 | 9.4163 | **avg=9.4163** | ✅ |
| Q4 expectation_gap | weak 0.25 current | **declared=0.25、effective=0.25、weak** | ✅ |
| fair value | 223.6034 | **223.603450369052** | ✅ |
| 現價 | 281.86 | **281.86** | ✅ |
| value_date | 2027-06-30 | **2027-06-30** | ✅ |
| 隱含報酬 simple | −20.67% | **−0.20668611945983106** | ✅ |
| 隱含報酬 年化 | −24.64% | **−0.24635833235156035** | ✅ |
| entry | missing，不進 blockers | **missing，blockers=[]** | ✅ |
| readiness | ready | **ready** | ✅ |
| 判斷與 context | 一致 | **一致** | ✅ |

**10/10（＋ context 一致）未動。** 新增三檔的資料與三個 generic gate 都沒有污染既有標的。

⚠ **一筆未能重現的觀察，誠實記下：** 在一次 LYC.AX 的批次執行中，畫面顯示
「判斷與目前 context：**不一致**」，但緊接著的 7 次執行（markdown 4 次、JSON 1 次、
packet digest 3 次）全部顯示一致、且 digest 逐字相同
（`sha256:42f325ea…` ＝ 判斷檔的 `_packet_digest`）。**無法重現，也就無法歸因**——
可能是圖讀取的一次瞬時差異。不宣稱它已修好，記在這裡供日後對照。

---

## 8. 驗收

| 項目 | 結果 |
|---|---|
| `pytest tests/` | **1,884 passed／1 skipped**（Step 4 收盤 1,860／1；新增 **24** 條在 `tests/test_coverage_pilot_generalization.py`） |
| 突變非空跑 | **156 → 163 個突變、空跑 0**（新增 7 條，逐一對應 §3 的六個缺陷 ＋ 我自己引進又被同批測試擋下的那一個） |
| `python -m audit invariants` | **FAIL 0｜PASS 12｜SKIPPED 0**（共檢查 2,097 筆） |
| golden fixtures | **14/14 擷取、失敗 0、漂移 1**——`stale_observations`，因為 `total_manual_observations` **116 → 120**（本次新增 LYC／6324.T／IQE.L 的 `fiscal_year_results` 與 6324.T 的 `company_guidance`）。**EXPECTED_CHANGE**，已重新擷取 |
| `tests/test_full_chain_acceptance.py` | 35 條**全綠**（Step 4 的對抗式場景在新資料下不受影響） |

⚠ **執行環境注意：** golden fixture 的 `multi_account_holding` 在**全域 python** 下會誤報漂移
（缺 `google-auth`，Sheet 讀不到）。必須用 `.venv/Scripts/python.exe` 跑，
否則會把環境問題讀成回歸——這正是 L13-2「成功與失敗在同一個訊號上同形」的一個實例。

---

## 9. 判定：**GO**

**成功的定義不是「三檔全部 ready」**，而是「對不同資料形態，系統要嘛產生可追溯的完整 view，
要嘛在正確的層級明確 fail closed」。實際結果：

1. **LYC.AX ready** — 非 USD、非美國準則、單一分部、價格接受者，整條鏈走完且每個數字指得回一手。
2. **6324.T blocked at valuation** — 前面每一層都 available，**只有**估值層因為證據錨不住倍數而停下；
   而且停下的同時仍然給出了 126.2x 這個讓人看懂「為什麼停」的診斷。
3. **IQE.L blocked at model applicability** — 基期已建立、共識口徑已機械核實（`non_gaap`）、
   營收已對帳；停下來的是**方法層**（虧損公司沒有可用的 method），加上一個明說出來的
   研究前置（流動性未評估）。**補資料解不掉的東西沒有被偽裝成資料問題。**
4. **沒有一格 hidden default、沒有一筆假資料**——每一條假設都指回一手文件的確切位置。
5. **六個 generic 缺陷全部在 COHR 上不可能出現**，其中四個會產生看起來確定、實際錯誤的數字。
6. **本報告自己犯的那次 L11-4 也被逐字記下**（第一版誤判「IQE 沒有年報」）——
   `historical-failure-matrix` 的紀律要求記錄的是形狀，不是只記錄成功。

**是否已安全進 Step 5 APP／API：是。** 理由：Step 5 是**呈現層**，它消費的是 read model
（`AlphaInvestmentView`／`AnalystView`）。本次證明了 read model 在三種資料形態下都能正確表達
available／missing／not_applicable／not_modeled 四種狀態，且 blocker 訊息帶得動「哪一層、為什麼」。
⚠ 兩個前置提醒：① **§4.3 的「刻意不寫 vs 還沒寫」建議在 Step 5 之前處理**——APP 會把
blocker 直接顯示給使用者，那句話在 APP 上會比在 CLI 上更容易被誤讀；
② **§4.1 的 `gaap` 字面**在 APP 上同樣會被使用者看到，需要呈現別名。

---

## 10. 本次寫入的 authority（稽核清單）

| 種類 | 標的 | id | 內容 |
|---|---|---|---|
| Engine C mechanical 觀測 | LYC.AX | `mo_468c4a7c84b39c90d8246b454206ff6a` | `fiscal_year_results` FY2026（Appendix 4E） |
| Engine C mechanical 觀測 | 6324.T | `mo_fe968212bf73ba34861db56944a568d0` | `fiscal_year_results` FY2026/3（決算短信 連結） |
| Engine C mechanical 觀測 | 6324.T | `mo_4f5c0bd6adc0d0cae0278fa5402195d6` | `company_guidance` FY2027/3 通期連結予想 |
| Engine C mechanical 觀測 | IQE.L | `mo_48bb916496c97b4cef20d1fda140b3d5` | `fiscal_year_results` FY2025（Annual Report 2025） |
| OperatingAssumption ×6 | LYC.AX | `oa_a9de1146…`／`oa_420b305a…`／`oa_50006ac1…`／`oa_fbf181e9…`／`oa_ca95baff…`／`oa_76849fab…` | FY2027 六條 driver |
| OperatingAssumption ×6 | 6324.T | `oa_ce022104…`／`oa_ba0c8f35…`／`oa_608d5193…`／`oa_c715cbe5…`／`oa_e7ef2c93…`／`oa_255bb7e1…` | FY2027/3 六條 driver |
| ValuationAssumption | LYC.AX | `va_ab6864695268792d` | `target_pe=22.0`、`value_date_convention=target_period_end` |
| HorizonAssumption | LYC.AX | `ha_8bdd00a9faf87def` | horizon_end 2027-06-30 |
| session judgment | LYC.AX | `library/private/alpha/judgments/LYC.AX.json` | 四軸 ＋ thesis ＋ variant view ＋ 4 條 disproof |
| session judgment | 6324.T | `library/private/alpha/judgments/6324.T.json` | 四軸 ＋ thesis ＋ variant view ＋ 4 條 disproof |
| library 文件 | 6324.T | `library/raw/hds_6324_tanshin_fy2026_20260513_financials.txt` | 決算短信財務補篇（tracked，非 private） |
| library 文件 | IQE.L | `library/raw/iqe_annual_report_2025_financials.txt` | 年報財務摘錄（tracked，非 private） |
| Engine C projection | 6 檔 | `financial_snapshots`／`consensus_estimates` | 對 IQE.L／6324.T／LYC.AX／3081.TWO／AXTI／SIVE.ST 跑一次 yfinance ETL（A2 projection，可重建，無 gate） |

⚠ **沒有做的：** graph admission（0 筆新節點／邊）、thesis 或 variant view 變更、
evidence tier 升級、任何資本動作、IQE.L 的任何 A3 寫入（只寫了 mechanical 觀測）。

⚠ **private authority 備份：** 本次新增 2 本 assumption ledger、1 本 valuation、1 本 horizon、
2 份判斷檔。**Pilot 收尾必須再跑一次 `python scripts/backup_private.py run --no-drive`**，
否則 `unbacked_files` 會再度非零（這正是 Step 4 修出來的那個計數器要抓的東西）。
異地副本（`drive: skipped`）仍缺。
