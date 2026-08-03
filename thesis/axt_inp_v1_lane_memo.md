<!-- output_type: [Watchlist Candidate] | ticker: AXTI | checklist_pass: True | l9_pass: True | evidence_manifest_pass: True | evidence_gate_pass: True -->

# Directional Lane Memo — AXT（InP 基板 / AI 光通訊上游）
**生成日期：** 2026-08-03（v3，經 blind-spot-audit 紅隊後重寫）
**核查頻率與觸發動作：** 每季完整核查（下次為 2026 Q3 財報與 Form 10-Q）；每週掃描監控
出口許可與客戶端揭露訊號。任一 disproof 條件觸發 → 48 小時內人工 review，決定降評／
維持／退場。

> **v3 修訂說明：** v1 的核心論點是「對美出口許可未取得會壓縮營收認列節奏」。紅隊審查
> 指出該風險是 AXT 自己 10-K Risk Factors 的首項、公開揭露逾一年，因此不構成 variant
> perception，只是已定價的風險揭露。同時查出 v1 有兩處選擇性引用與兩處遺漏的同源反證。
> v3 把核心論點改為「週期 vs 結構」，並把許可降級為已知的時程風險。

## 1. 一句 thesis

AXT 是 InP **增量**產能的關鍵供應者，需求已由三份帶對價的合約落地；但市場正把一次與
2022 年同型的週期性毛利率回升，定價成結構性的瓶頸議價權。

> **Variant Perception：** 當前股價 US$60.43（Forward P/E 約 27.1x、EV/Revenue 約 27.4x、
> 分析師目標均價 US$91.6／N=5）隱含的假設 X 是：Q2 2026 的 44.9% GAAP 毛利率與 +164% YoY
> 營收是新常態——股價三個交易日內從 US$36.97 漲到 US$60.43（+63%），已完成這個重定價。
>
> 本 thesis 認為真實情況 Y 是：**44.9% 不是前所未見的水準。** AXT 自己的 FY2025 10-K 在
> Risk Factors 逐字記載「in the third quarter of 2022 our gross margin was 42.0% but it
> dropped to 10.7% in the third quarter of 2023」——上一次同量級的高點，四個季度內崩掉
> 31.3 個百分點。完整序列為 2022Q3 42.0% → 2023Q3 10.7% → 2025Q1 -6.4% → 2025Q2 8.0%
> → 2025Q3 22.3% → 2026Q1 29.6% → 2026Q2 44.9%（Engine C manual observation，來源為
> 10-K 與 Q2 8-K Exhibit 99.1）。且本次改善的驅動看起來是稼動率而非單價：Q2 營收年增
> 164.8%，銷貨成本卻只增 58.5%（US$16.541M → US$26.223M），符合固定成本攤薄的營運槓桿，
> 而 10-K 自述「Because many portions of our manufacturing costs are relatively fixed,
> high utilization rates are critical to our gross margins」。營運槓桿是對稱的——需求
> 回落時毛利率會同樣快地反轉。
>
> 這一點之所以是 variant，是因為它需要主動翻查 Risk Factors 裡的歷史數字才看得到；
> 相對地，出口許可是 10-K Risk Factors 的**首項**、公開逾一年，屬已定價的風險揭露而非
> 認知差異（v1 誤把它當作 variant perception，v3 已降級，見第 6 節）。
>
> 催化劑 Z：**2026 Q3 財報的毛利率**——若延續 44%+ 並揭露 ASP 貢獻，結構解釋勝出；
> 若回落至 30% 附近，週期解釋確立。同期的 Q3 Form 10-Q 另將揭露 Lumentum 合約全文
> （含交付條款）、出口許可進展與 PE 基金贖回情形 [E3][E10]。

## 2. 需求驅動

- 需求以帶對價的合約落地，三個交易對手具名：Coherent 支付 US$22,288,500 預付款換取
  AXT 於 2026-2028 擴充北京六吋 InP 產能 [E2]；Lumentum 取得為期六年的最低年度產能保留
  [E3]；Casela 承諾 2027 年 RMB 173,000,000、附 50% 預付與 80% 最低採購門檻 [E4]。
  客戶願意先付錢，是比法說會措辭更難偽造的行為證據。
- 訂單能見度：Q1 2026 InP backlog 突破 US$100M 創新高，當季 InP 營收 US$13.6M，
  管理層歸因於美國雲端與 AI 平台業者的資本支出 [E1]。
- 同業側佐證這是產業級現象：Lumentum 自陳 InP 晶圓產能「fully allocated」，即使增產
  20% 後仍較客戶需求少出貨約 30%，且產能已被鎖進到 2027 年的長約 [E11]。
- **但 Q2 的分項揭露缺席，且這個空白是雙向的。** 公司未揭露 Q2 的 InP 營收與地區組成。
  這既讓我們無法判斷許可是否已鬆綁，**也讓本 memo 無法主張許可仍在壓抑營收**——
  US$47.589M 的總營收若主要來自 InP，反而是對「許可壓抑論」的反證。v1 只寫了前半，
  v3 補上後半。

## 3. Stack 摘要

AXT 位於光通訊 stack 的最上游——化合物半導體基板，同時供應 InP、GaAs 與 Ge 三類 [E9]。
往下游走，基板先進入磊晶層廠商，再到光元件與模組廠。

圖中已建立的下游具名路徑需要區分性質：Coherent 是 AXT 的既有主要客戶（Reuters 逐字：
「Coherent, mainly supplied by AXT」）[E9]；**Lumentum 則相反——同一句話載明「Lumentum,
mainly supplied by Sumitomo and JX Advanced Metals」**[E9]。因此 2026-07-26 的六年產能
保留協議 [E3] 對 Lumentum 而言更可能是**新增的第二來源或增量產能**，而非既有依賴關係的
延續。v1 把兩者並列為「下游具名路徑」而未作此區分，會讓讀者高估 AXT 對 Lumentum 的
議價地位。另有受許可延遲波及的台灣廠商 LandMark 與 VPEC [E14]。

## 4. 主瓶頸（限縮為增量產能）

- **公司／材料：** AXT（含中國子公司 Tongmei）的 InP 基板**增量**產能。
- **為什麼仍是關鍵：** InP 基板市場高度集中，三家業者控制逾九成 [E8]；更換基板供應商
  需要漫長的 qualification 週期，下游不易切換 [E9]。在總量吃緊（Lumentum 自陳少出貨
  30% [E11]）的環境下，能提供增量產能的來源具有議價權。
- **但總量上 AXT 並非最大者。** 同一份市場研究的相鄰數據：Sumitomo Electric 約 42% 市佔、
  約 80 萬片年產能；AXT 約 36% 市佔、約 30 萬片年產能 [E8]。**Sumitomo 的產能是 AXT 的
  約 2.67 倍。** v1 只引用了 AXT 的數字而略過對比，會讓讀者誤以為 AXT 在總量上舉足輕重。
  正確的定位是：AXT 是邊際產能的關鍵來源，不是總量瓶頸。
- **也不是 sole source：** 圖中 AXT→Coherent 邊的 canonical 屬性明載 `sole_source=False`、
  `substitutability=4`（schema 定義 5 為完全不可替代）、`qualification_status=qualified`，
  且該屬性來自第三方 Reuters 而非 AXT 自報 [E9]；競爭邊 Sumitomo Electric 亦已入圖 [E8]。
  依 L8（來源獨立性：供應商自報不能當 sole_source 獨立佐證），本 memo 不主張不可替代。

## 5. 週期還是結構（本 memo 的核心問題）

支持**結構**的證據：三份帶對價的長約，期間分別為三年、六年與一年 [E2][E3][E4]；
InP backlog 創新高 [E1]；同業自陳結構性缺貨並鎖長約至 2027 [E11]；下游 qualification
轉換成本高 [E9]。

支持**週期**的證據：2022 Q3 毛利率已達 42.0%，四季內崩至 10.7%；當前 44.9% 與該次高點
同量級。Q2 成本僅增 58.5% 而營收增 164.8%，指向稼動率而非單價驅動；10-K 自述固定成本
比重高、稼動率對毛利率至為關鍵，並明列「compound semiconductor industry has historically
been cyclical」（以上均為 Engine C manual observation `gross_margin_trend`，一手來源為
FY2025 10-K Risk Factors 與 Q2 8-K Exhibit 99.1）。

**分辨兩者的唯一缺口是 ASP。** 若 InP 基板售價確實大幅上漲，本次改善的黏著度會顯著高於
純稼動率驅動。目前唯一線索是市場流傳的 Nomura 報告（稱 2 吋 InP 漲 42-76%、3 吋漲 78%），
但該報告仍為 tier-3 隔離、未取得原文，依 source-trace 規則不得採用。在 ASP 貢獻被釐清前，
本 memo 對 44.9% 的可延續性不表態。

## 6. 出口許可：已定價的時程風險（v1 誤列為 variant perception）

事實仍然成立且重要，只是它不是認知差異：中國於 2025-02-04 將 InP 基板列入出口管制 [E5]；
2025-06-11 的初始許可逐字僅涵蓋「certain customers in Europe and Japan」[E5]；至
2026-05-14 的 Q1 10-Q 對美許可仍未取得、訂單積壓、無法預估時點 [E6]；管理層稱這是
「the most significant single factor to our growth in Q2 and beyond」[E7]。2026-03-01
生效的修訂《對外貿易法》擴大出口禁限權限 [E12]。第三方佐證顯示風險已實際發生於下游：
VPEC 與 LandMark 曾因 AXT 許可延遲遭遇供應中斷 [E14]。

**但三件事限制了它作為 thesis 的地位：** (a) 它是 10-K Risk Factors 的首項，公開逾一年，
賣方不可能不知道——分析師均價 US$91.6 對現價 US$60.43 隱含 +51% 空間，顯示市場已知而
不視為致命；(b) 同一段落另有逐字陳述「we can reasonably expect that export permits...
will be granted. However, the timing for receiving permits remains uncertain」[E5]，
公司認為許可**會**核准，不確定的是**時點**；(c) 這些基板是否需要進入美國關境，
沒有任何一手文件確認（見第 8 節）。因此正確的定性是「已公開的時程風險」，
而非本 thesis 的差異來源。

## 7. 什麼會推翻這個 thesis

- **Q3 2026 GAAP 毛利率維持 44% 以上，且公司揭露 ASP 上漲為主要驅動** → 結構解釋勝出，
  本 memo 的核心 variant perception 失效，需上修對可延續性的評估。
- Q3 2026 營收低於 Q2 的 US$47.589M，或毛利率跌回 35% 以下 → Q2 未成為 run-rate。
- Q3 10-Q 揭露 11 家中國 PE 基金實際行使贖回累計逾 RMB 200,000,000 [E10]。
- Coherent 或 Lumentum 任一方要求退還預付款／保證金，或 AXT 連續逾六個月未達 Capacity
  Commitment 使對方取得終止權 [E2]。
- 出現第二輪重大股權稀釋（加權平均 diluted 股數再增逾 15%）而未伴隨等比例的營收或產能
  承諾增長。
- Sumitomo 或 JX Advanced Metals 宣布 InP 擴產並在關鍵客戶完成 qualification [E8]。

## 8. 本 memo 尚未回答的反問

**如果對美許可真的構成重大風險，為什麼 Coherent 與 Lumentum 明知仍各付數千萬美元？**
三種不互斥的解釋，證據地位不同：

- **(a) 他們同意公司對「會核准」的判斷，買的是排隊位置而非即期交付。** 與 [E5] 逐字陳述
  一致；合約期間（三年、六年 [E2][E3]）遠長於許可爭議的時間尺度，deposit 轉為 shipment
  credit 的設計也支持「鎖產能」而非「鎖當期出貨」。屬合約條款的合理推論，非文件明述。
- **(b) 他們沒有替代選擇——此解釋對 Lumentum 明確不成立。** Reuters 逐字載明 Lumentum
  主要由 Sumitomo 與 JX Advanced Metals 供應 [E9]，且 Sumitomo 產能為 AXT 的約 2.67 倍
  [E8]。Lumentum 顯然有替代來源，它選擇加簽 AXT 更可能是分散來源或搶增量產能。
  對 Coherent 而言（Reuters 稱其 mainly supplied by AXT）此解釋較有力，但仍未經證實。
- **(c) 交付地點可能不全在美國。** 兩者都是跨國製造商，基板未必需要進入美國關境。
  **本 memo 沒有任何證據支持或否定這一點**——三份合約全文均未公開，交付條款不明。
  這是第 6 節論點成立與否的前提，也是目前最大的單一未知。

## 9. 接下來盯什麼

- **2026 Q3 財報（最高優先）：** 毛利率是否維持 44%+、是否揭露 ASP 貢獻與 InP 分項營收。
  這一個數字直接裁決第 5 節的週期／結構之爭。
- **2026 Q3 Form 10-Q：** Lumentum 合約全文 exhibit [E3]，特別是**交付條款是否涉及美國
  關境**——它決定第 6 節的風險論點是否成立，優先度等同許可本身。同份文件另揭露許可進展
  與 PE 基金贖回情形 [E10]。
- **ASP 追源（不阻擋，但影響核心判斷）：** 取得 Nomura 報告原文或發行人價格揭露，
  補上分辨週期與結構的關鍵證據。
- **客戶端獨立證實（每季）：** Lumentum 的 10-Q commitments／purchase obligations 附註
  是否具名 AXT。已查證 Lumentum 未就此發布 8-K，故客戶端證據只會出現在定期報告或法說會。
- **競爭格局（每季）：** Sumitomo 產能動向與 Lumentum 自建 InP 產能進度 [E8][E11]。

## 10. 本 memo 的邊界

方向備忘，不是可操作的投資建議。所有商業與財務數字仍百分之百出自 AXT 自己的揭露 [E13]，
三份合約全文均未公開，客戶端沒有任何一方獨立證實過這些協議。依 L8，客戶付款屬行為證據
但仍透過 AXT 單方轉述，不得自我升格為客戶端確認。

本 memo 未定義部位規則。對應的資本上限由 Engine D 另行計算（AXT cohort 當前 axis_ceiling
為 0.2% NAV），不由本 memo 推定。組合層面亦須注意：圖中已有 Coherent 與 Lumentum 的
thesis 與證據，AXT 是兩者的上游，同時持有等於在同一條 InP 鏈上疊加曝險而非分散。
