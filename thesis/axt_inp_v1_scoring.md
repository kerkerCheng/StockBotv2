# AXT InP v1 — Thesis 評分記錄

日期：2026-08-02
版本：`axt_inp_v1_lane_memo.md`（14 條 evidence，四個 distinct origin：AXT、Reuters、
Global Semi Research、Lumentum；evidence gate 五道全過）

> **評分者揭露：** 本份 memo 與本份評分皆由同一個研究 agent（Claude Code session
> 2026-08-02）產出，屬自評。既有慣例（`cpo_v1_scoring.md`）相同，但自評對「洞見密度」
> 與「市場差異度」兩項有結構性偏誤——那正是 memo 的賣點所在。使用者應把本表視為
> 待複核的提案，而非已確認的結論。評分前已先修正一處選擇性引用（見下方「評分過程中
> 修正的缺陷」）。

---

## 評分

| 維度 | 分數 | 評語 |
|---|---|---|
| 可信度 | 4/5 | 14 條證據全屬 Tier 1/2 一手 filing 與法說會，quote 逐字可核，且全部 join 回圖中的 claim／edge／assertion ID。四個 distinct origin 滿足 L8 的 ≥3 要求，其中市場結構與可替代性來自第三方（Reuters、Global Semi Research）而非 AXT 自報。扣 1 分：所有商業與財務數字仍百分之百出自 AXT 單方揭露，三份具名客戶合約沒有任何一方自其自身 filing 或 IR 證實，且合約全文均未公開。 |
| 瓶頸清晰度 | 5/5 | 明確指向單一 chokepoint（AXT／Tongmei 的 InP 基板產能與其出口許可），並以量化數據支撐：三家業者控制逾九成、AXT 與 Sumitomo 合計近 80%、AXT 約 36% 市佔與約 30 萬片年產能。斷鏈機制有解釋（更換基板供應商需長 qualification 週期）。且誠實使用圖中 canonical 屬性 `sole_source=False`／`substitutability=4`，主動聲明不主張 AXT 不可替代，counter-path（Sumitomo competes_with）已入圖。 |
| 可證偽性 | 5/5 | 五條 disproof 條件全部具體可觀測且帶量化門檻（Q3 毛利率 < 35%、Q3 營收 < US$47.589M、PE 基金贖回累計 > RMB 200,000,000、Coherent 取得終止權、加權平均 diluted 股數再增 > 15%）。memo header 同時載明核查頻率（每季完整核查＋每週掃描）與觸發後 48 小時人工 review 動作——這正是 `cpo_v1_scoring.md` 當初被扣分的缺口。 |
| 洞見密度 | 4/5 | 非顯性論點成立：把「Coherent 與 Lumentum 都是美國法人」與「對美 InP 出口許可至今未取得」連起來，與市場三個交易日 +63% 的反應形成實質對比；leading indicator 清單可立即啟動監控。扣 1 分：該論點建立在一個未經一手文件確認的前提——這些基板是否需要進入美國關境。memo 第 8 節已誠實列出此未知，但列出未知不等於解答它，論證因此是有條件成立而非完成。 |
| 完整性 | 5/5 | 九個段落全有實質內容。需求端（AI capex 驅動、record backlog、Lumentum 自陳缺貨 30%）、供應端（產能、市場結構、具名競爭者）、技術層（InP／GaAs／Ge 三類基板與磊晶層下游路徑）三維皆覆蓋。另有兩段自我約束：第 8 節處理對本 thesis 最不利的反問，第 9 節聲明來源邊界。 |
| 市場差異度 | 4/5 | X 由實際估值數字推導而非定性描述（forward P/E 約 27.1x、EV/Revenue 約 27.4x、分析師均價 US$91.6／N=5，並指出三日內 US$36.97→US$60.43 的重定價已完成）；Y 明確；Z 是有具體日期與可驗證內容的單一文件（2026 Q3 Form 10-Q）。形式上符合 5 分定義，扣 1 分的理由與洞見密度同源：Y 的強度依賴未證實的交付地點前提，且修正後已自我限縮為「時程風險」而非「能否取得」。 |
| **總分** | **27/30** | |

---

## 評分過程中修正的缺陷

準備評分時發現 memo v1 存在**選擇性引用**：`E5` 引用的 `axti_10_k_20260317_s13` 逐字內容為
「To our knowledge, indium phosphide is rarely used in military applications and **we can
reasonably expect that export permits to ship our indium phosphide substrates to the U.S.
will be granted.** However, the timing for receiving permits remains uncertain, unclear and
beyond our control.」——正文只用了後半句，公司明確表示「預期許可會核准」的前半句被略過，
而該句直接緩和本 memo 的核心風險論點。

這不是引用錯誤（來源正確、逐字無誤），而是取捨偏誤，屬 L11（自己引用的事實要套跟圖裡
claim 同一套追源紀律）警告的「對外部 claim 嚴、對自己引用鬆」。已修正：variant perception
段新增「本 thesis 的自我約束」，補上該句原文並把風險精確定義為**時程風險**而非**能否取得**；
另新增第 8 節處理「客戶明知風險仍付錢」的反問。修正後重跑 evidence gate，五道仍全過。

若未修正，可信度應降至 3、市場差異度應降至 3，總分約 23/30——仍過線，但那個分數會建立
在一份論證失衡的文件上。

---

## 最弱環節

**洞見密度與市場差異度並列 4 分，且根因相同：** 整條風險論點成立於「Coherent 與 Lumentum
採購的基板需要出口至美國」這個前提，而該前提**沒有任何一手文件確認**。三份合約全文均未
公開，交付條款不明；兩家客戶都是跨國製造商，基板未必進入美國關境。

這使 thesis 目前處於「有條件成立」狀態：若交付不涉美國關境，出口許可對這兩份合約的影響
將大幅小於本 memo 的推論，variant perception 的強度也會隨之下降。memo 第 8 節已把它標為
「目前最大的單一未知」，但標註不等於解決。

---

## 整體評估

**PASS — 可進入 Watchlist 升格流程**

- 總分 27/30 ≥ 22 ✅
- 可信度 4 ≥ 3 ✅
- 可證偽性 5 ≥ 3 ✅
- 市場差異度 4 ≥ 2 ✅
- 財務核驗清單 5 項全部完成（`gate_pass=True`，其中 dilution 已改採一手加權平均股數
  而非 yfinance 當期快照）✅

**但升格建議附一個條件：** 本結論為自評，且最弱環節指向一個未解的事實問題而非文風問題。
建議在正式升格前，由使用者確認或以 `blind-spot-audit` 紅隊複核第 8 節的三種解釋，
特別是 (c) 交付地點。

---

## 後續行動

1. **最高優先（事件驅動）：** 2026 Q3 Form 10-Q（預計 2026-11 初）的合約 exhibit——
   一次解決交付地點、Lumentum 承諾數量、許可進展、PE 基金贖回四個未知。
   已登記於 `thesis/lifecycle.json` 的 `axt_inp.next_check = 2026-11-15`。
2. **每季：** Lumentum 10-Q 的 commitments／purchase obligations 附註是否具名 AXT——
   目前唯一可能取得客戶端獨立證實的路徑（已查證 Lumentum 未就此發布 8-K）。
3. **待補（不阻擋升格）：** Nomura 的 InP 基板 ASP 漲價報告仍為 tier-3 隔離
   （`trace_status=isolated_tier_3`），若追回原文可補強 Q2 毛利率 44.9% 的來源拆解——
   目前無法分辨漲價、稼動率與產品組合各自的貢獻。
4. **決策側：** AXT cohort 最新 decision 為 `pd_66a8e13bd0dac2866064b03fb9c70c74`，
   五軸皆無 context mismatch，coverage 已不再歸零；剩餘限制為市場資料週末 stale 與
   research intent。升格後可考慮以 paper intent 重跑取得實際 supported range。
