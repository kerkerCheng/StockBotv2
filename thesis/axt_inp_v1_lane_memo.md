<!-- output_type: [Watchlist Candidate] | ticker: AXTI | checklist_pass: True | l9_pass: True | evidence_manifest_pass: True | evidence_gate_pass: True -->

# Directional Lane Memo — AXT（InP 基板 / AI 光通訊上游瓶頸）
**生成日期：** 2026-08-02
**核查頻率與觸發動作：** 每季完整核查（下次為 2026 Q3 Form 10-Q，預計 2026-11 初）；
每週掃描監控出口許可與客戶端揭露訊號。任一 disproof 條件觸發 → 48 小時內人工 review，
決定降評／維持／退場。

## 1. 一句 thesis

AXT 是 InP 基板的結構性瓶頸，需求已由三份帶對價的產能保留合約落地；但這條 thesis 的
成敗不在需求或產能，而在一個尚未解除的監管前提——對美 InP 出口許可至今未取得。

> **Variant Perception：** 當前股價 US$60.43（Forward P/E 約 27.1x、EV/Revenue 約 27.4x、
> 分析師目標均價 US$91.6 但樣本僅 5 家）隱含的假設 X 是：Q2 2026 的 44.9% GAAP 毛利率與
> +164% YoY 營收是新常態，且 Coherent 三年期六吋 InP 協議 [E2] 與 Lumentum 六年產能保留
> [E3] 會如期轉為交付——股價在三個交易日內從 US$36.97 漲到 US$60.43（+63%），已完成這個
> 重定價。本 thesis 認為真實情況 Y 是：這三份合約中金額最大的兩份，交易對手 Coherent Corp
> 與 Lumentum Operations LLC 都是美國法人，而 AXT 對美國的 InP 出口許可**至今仍未取得**
> ——2025-06-11 的初始許可逐字僅涵蓋「certain customers in Europe and Japan」[E5]，
> 到 2026-05-14 的 Q1 10-Q 仍是「unable to estimate when we will receive the necessary
> export permits」且有訂單積壓 [E6]，管理層本人稱這是「the most significant single factor
> to our growth in Q2 and beyond」[E7]。市場正把「產能承諾」與「可交付營收」當成同一件事，
> 而兩者之間隔著一個 AXT 自己說無法預估時程的許可。Q2 營收未做地區與客戶分項揭露，
> 因此它究竟證明了許可已鬆綁、還是只證明歐日與中國內需夠強，目前無法分辨。
>
> **本 thesis 的自我約束（必須與上段一起讀）：** 同一份 10-K 的同一段落另有一句逐字陳述
> ——「we can reasonably expect that export permits to ship our indium phosphide substrates
> to the U.S. will be granted. However, the timing for receiving permits remains uncertain,
> unclear and beyond our control」[E5]。公司認為許可**會**核准，不確定的是**時點**。因此
> 本 memo 主張的風險精確定義為「時程風險」而非「能否取得」：它壓縮的是 Coherent 與
> Lumentum 承諾轉為認列營收的節奏，而非否定該營收最終存在。把它寫成「許可拿不到」會是
> 對一手文件的過度延伸——依 L11（自己引用的事實要套跟圖裡 claim 同一套追源紀律），本段
> 刻意保留這句對本 thesis 不利的原文。
>
> 催化劑 Z：2026 Q3 Form 10-Q（預計 11 月初）將同時揭露 Lumentum 合約全文、許可進展、
> 以及 Q3 的 InP 營收與毛利率是否延續——單一文件一次解決三個未知。

## 2. 需求驅動

- AI 資料中心對高速光傳輸的 InP 需求已從預測轉為硬訂單：Q1 2026 InP backlog 突破
  US$100M 創新高，當季 InP 營收 US$13.6M，管理層明指驅動來自美國雲端與 AI 平台業者的
  資本支出 [E1]。
- 需求進一步以帶對價的合約落地，且三個交易對手具名：Coherent 支付 US$22,288,500 預付款
  換取 AXT 於 2026-2028 擴充北京六吋 InP 產能 [E2]；Lumentum 取得為期六年的最低年度產能
  保留 [E3]；Casela 承諾 2027 年 RMB 173,000,000、附 50% 預付與 80% 最低採購門檻 [E4]。
- 同業側佐證需求為產業級現象而非單一敘事：Lumentum 自陳 InP 晶圓產能「fully allocated」，
  即使增產 20% 後仍較客戶需求少出貨約 30%，且全部產能已被鎖進到 2027 年的長約 [E11]。

## 3. Stack 摘要

AXT 位於光通訊 stack 的最上游——化合物半導體基板。它同時供應 InP、GaAs 與 Ge 三類基板
[E9]，其中 InP 是資料中心高速光傳輸的關鍵材料。往下游走，基板先進入磊晶層廠商（AXT
自陳主要客戶類型），再到光元件與模組廠。目前圖中已建立的下游具名路徑包括 Coherent
[E9]、Lumentum [E3]、Casela [E4]，以及受許可延遲波及的台灣廠商 LandMark 與 VPEC [E14]。

## 4. 主瓶頸

- **公司／材料：** AXT（含中國子公司 Tongmei）的 InP 基板產能與其出口許可。
- **為什麼是瓶頸：** 全球 InP 基板市場高度集中——三家業者控制逾九成，AXT 與 Sumitomo
  合計接近 80%，AXT 自身約 36% 市佔、年產能約 30 萬片 [E8]。且更換基板供應商需要漫長的
  qualification 週期，下游不易切換 [E9]。
- **但它不是 sole source：** 圖中 AXT→Coherent 邊的 canonical 屬性明載 `sole_source=False`、
  `substitutability=4`、`qualification_status=qualified`，且該屬性來自第三方（Reuters）
  而非 AXT 自報 [E9]；競爭邊 Sumitomo Electric 亦已入圖 [E8]。依 L8（來源獨立性：供應商
  自報不能當 sole_source 獨立佐證），本 memo 不主張 AXT 不可替代。
- **真正的卡點是監管而非產能：** 中國於 2025-02-04 將 InP 基板列入出口管制 [E5]；
  初始許可只放行歐洲與日本部分客戶，對美出貨許可仍在等待且時程「beyond our control」
  [E5]；一年後的 Q1 10-Q 仍未取得，訂單持續積壓 [E6]。2026-03-01 生效的修訂《對外貿易法》
  進一步擴大政府限制出口的權限，構成既有制度之上的尾部風險 [E12]。

## 5. 最強證據

- [E2][E3] 兩家美國光元件龍頭各以真實對價鎖定 AXT 產能（Coherent 預付款 US$22.3M、
  Lumentum 六年最低年度承諾）。客戶願意先付錢，是比法說會措辭更難偽造的行為證據。
- [E1] InP backlog 突破 US$100M 創新高，且管理層明確歸因於 AI 資料中心資本支出——
  需求是已下單，不是預測。
- [E8] 第三方（Global Semi Research、Reuters）確認的市場結構：三家控制逾九成，
  AXT 約 36%。這是非自報的集中度證據。
- [E14] Reuters 引述具名分析師指出 VPEC 與 LandMark 已因 AXT 許可延遲而遭遇 InP 基板
  供應中斷——許可風險不是理論推演，已有下游實際受害案例。

## 6. 什麼會推翻這個 thesis

- Q3 2026 GAAP 毛利率跌回 35% 以下，或 Q3 營收低於 Q2 的 US$47.589M，代表 Q2 的
  step-function 未能成為 run-rate。
- 對美 InP 出口許可遭拒、範圍受限或持續延宕，導致 AXT 對 Coherent 連續逾六個月未達
  Capacity Commitment 而使對方取得終止權 [E2]；或 Coherent、Lumentum 任一方要求退還
  預付款／保證金。
- Q3 10-Q 揭露 11 家中國 PE 基金實際行使贖回累計逾 RMB 200,000,000 [E10]。
- 出現第二輪重大股權稀釋（加權平均 diluted 股數再增逾 15%）而未伴隨等比例的營收或
  產能承諾增長。
- Sumitomo 或 JX Advanced Metals 擴產並在關鍵客戶處完成 qualification，使 AXT 的
  結構性議價地位下降 [E8]。

## 7. 接下來盯什麼

- **2026 Q3 Form 10-Q（預計 11 月初，最高優先）：** Lumentum 合約全文將作為 exhibit
  揭露 [E3]，可逐字核對最低年度產能承諾的數量與違約救濟；同一份文件應揭露出口許可進展、
  PE 基金實際贖回情形 [E10]，以及 Q3 的 InP 營收與毛利率。
- **出口許可（事件驅動）：** 中國商務部對美 InP 許可的任何核發或範圍變更 [E5][E6]。
  這是本 thesis 唯一的單點否決風險。
- **客戶端獨立證實（每季）：** Lumentum 的 10-Q commitments／purchase obligations 附註
  是否具名 AXT。已查證 Lumentum 未就此發布 8-K，故客戶端證據只會出現在定期報告或法說會。
- **地區與客戶分項（每季）：** AXT 是否揭露營收的地區組成——這是分辨「許可已鬆綁」與
  「歐日中國需求夠強」的唯一方法。
- **合約交付條款（Q3 10-Q exhibit）：** Coherent 與 Lumentum 的基板交付地點是否涉及美國
  關境。這決定第 8 節的風險論點是否成立，優先度等同許可本身 [E2][E3]。
- **競爭格局（每季）：** Sumitomo 產能動向與 Lumentum 自建 InP 產能的進度 [E8][E11]。

## 8. 本 memo 尚未回答的反問

**如果對美許可真的是主要風險，為什麼 Coherent 與 Lumentum 在明知的情況下，仍各自付出
數千萬美元的預付款與保證金？** 這個反問本 memo 無法用一手文件回答，只能列出三種彼此
不互斥的解釋並標明其證據地位：

- **(a) 他們同意公司對「會核准」的判斷，買的是排隊位置而非即期交付。** 與 [E5] 的逐字
  陳述一致；且兩份合約的期間（Coherent 三年、Lumentum 六年 [E2][E3]）都遠長於許可爭議的
  時間尺度，deposit 轉為 shipment credit 的設計也支持「鎖產能」而非「鎖當期出貨」。
  此為合約條款的合理推論，非文件明述。
- **(b) 他們沒有替代選擇。** InP 基板三家控制逾九成，Sumitomo 產能雖大但同樣吃緊，
  Lumentum 自建的 Greensboro 廠約六季後才會貢獻營收 [E8][E11]。若增量產能只有 AXT 能提供，
  付錢排隊是理性的，即使帶著監管風險。
- **(c) 交付地點可能不全在美國。** Coherent 與 Lumentum 都是跨國製造商，基板未必需要進入
  美國關境。**本 memo 沒有任何證據支持或否定這一點**——三份合約全文均未公開，交付條款
  不明。這是目前最大的單一未知。

在 (c) 被釐清之前，本 memo 的風險論點應被理解為「有條件成立」：它成立於「這些基板需要
出口至美國」的前提，而該前提尚未被任何一手文件確認。Q3 10-Q 的合約 exhibit 是最可能
解答它的文件。

## 9. 本 memo 的邊界

本 memo 是方向備忘，不是可操作的投資建議。所有商業與財務數字的來源仍百分之百是 AXT
自己的揭露 [E13]，三份合約全文均尚未公開，客戶端沒有任何一方獨立證實過這些協議。
依 L8，客戶付款屬行為證據但仍透過 AXT 單方轉述，不得自我升格為客戶端確認。
