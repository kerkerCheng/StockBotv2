<!-- output_type: [Research Note] | ticker: AMAT | checklist_pass: False | l9_pass: False | evidence_manifest_pass: True | evidence_gate_pass: True -->

# Directional Lane Memo — 成熟製程設備 capex 週期（AMAT / LRCX）

> ⚠️ **輸出等級：Research Note（非投資建議）**
> 這是第二條垂直切片，刻意選「**非 AI／非 CPO**」主題：成熟製程（trailing-edge / ICAPS）晶圓廠設備支出週期。
> 標的公司 AMAT／LRCX 同時有大量 AI／先進邏輯／HBM 收入——本備忘錄**把那塊 segment 分拆掉、不當作論點**；
> 論點只針對「非前沿節點」的資本支出週期。L8 來源獨立性以 AMAT 自身文件為主（memo scope 內 origin_entity=1），
> 客戶端印證（GlobalFoundries 20-F）另列於「最強證據」但未進 AMAT 的 company-scope 計數；升格 Watchlist 前須補財務核驗 5 項。

---

## 1. 一句 Thesis

市場用 leading-edge / AI-WFE 的倍數在定價 AMAT 與 LRCX，但兩家有結構性一大塊營收來自**成熟製程節點**（ICAPS：IoT／通訊／汽車／電源／感測器；200mm；非 HBM 的一般記憶體）——這塊在 2021–2024 中國 trailing-edge 擴產潮後正進入**多年消化**，同時在中國本土設備補貼夾殺下於 trailing-edge 節點**結構性流失份額**；AI 敘事遮住了一個縮水、中國集中的成熟製程基座（FY2026–2028）。

---

## 2. 需求驅動（成熟製程專屬，已分拆掉 AI/leading-edge）

- **ICAPS 才是成熟製程的需求引擎**：AMAT 明確把「非前沿節點」對應到 IoT、通訊、汽車、電源、感測器等終端市場，與 leading-edge（≤7nm）分帳列示 [E5]。這些終端的資本開支週期由汽車／工業／類比／功率庫存循環驅動，**與 AI 訓練叢集無關**。
- **成長來自 leading-edge、不是成熟製程**：AMAT FY2025 半導體系統的成長被管理層歸因於「foundry/logic 客戶對**leading-edge** 製程的投資增加」[E1]。反過來讀，就是——非前沿（成熟）那塊**不是成長來源**，比較像持平至衰退的基座。這正是本 thesis 要分拆並單獨承保的部分。
- **200mm 是純 trailing-edge 業務線**：AMAT 自 FY2026 起把 200mm 設備業務從 AGS 併入半導體系統 [E5]；200mm 幾乎全服務非前沿節點，是成熟製程曝險最乾淨的代理。
- **客戶端獨立印證（origin: GlobalFoundries）**：GF 20-F 顯示成熟製程 / essential-chip 晶圓廠仍在 capex（CHIPS Act 下 Fab 8 擴建、Fab 9 現代化），且「營運與擴產計畫**依賴少數幾家設備供應商**，交期可長達 12 個月以上」。這是非供應商自報的需求證據：成熟製程 WFE 需求真實存在，但其**西方這條腿靠補貼、且較慢**。
- LRCX 側對稱曝險：CSBG 的 **Reliant 產品線**專供「非前沿節點的沉積／蝕刻／清洗」翻新設備（origin: Lam Research），是 LRCX 成熟製程需求的直接載體。

---

## 3. Stack 摘要

- **設備層（equipment_epitaxy，本切片主體）**：AMAT／LRCX 的 WFE 同時餵兩條需求軌——(a) leading-edge（AI/HBM，被市場重估向上）與 (b) **非前沿／ICAPS／200mm（成熟，中國集中，本 thesis 標的）**。兩軌在財報裡混在同一 segment，是市場容易「一個倍數套全部」的根因 [E4][E5]。
- **記憶體分軌**：DRAM 技轉（含 HBM）是 AI 那一軌；一般 DRAM／NAND 產能才屬成熟軌。AMAT 揭露 NAND 佔比自 7%→4% [E2]——NAND（成熟記憶體）支出正在縮，與「成熟製程消化中」一致。
- **地理／法規層**：最大的集中壓力在中國。AMAT 中國營收佔比自 ~37% 降至 ~30% [E1]；中國這塊**不成比例地是成熟製程工具**（先進節點工具本就被出口管制擋住），所以中國佔比下滑幾乎等同於「成熟製程 + 服務」基座的下滑。

---

## 4. 主瓶頸（成熟製程 thesis 的 alpha 在需求／份額，不在供給卡點）

**中國 trailing-edge 的國產替代 + 出口管制 TAM 壓縮。**

- 圖中 `US Export Controls → AMAT` 依賴邊標注 `substitutability=1`、`qualification_status=none` [E7]：出口管制對可服務市場的壓縮高度不可迴避。
- 中國本土設備商（AMEC／Naura／SiCarrier 等，**產業推論，非圖中確認**）在補貼下於 trailing-edge 節點的 qualification 進度最快——正好是 AMAT／LRCX 成熟製程工具的價格帶。結果是「出口管制擋掉先進節點 + 國產替代吃掉成熟節點」兩頭夾擊 [E1][E6]。
- BIS 於 2026 年 2 月的 $253M 和解含三年稽核窗口懸置否認令 [E8]：法遵尾風險，觸發即業務中斷。

**資料缺口聲明：** 圖中沒有任何 `sole_source=✓` 邊指向具體成熟製程零件或中國競品；第 4 段的「國產替代吃份額」是產業推論 + AMAT 自我揭露風險因子，尚未由獨立第三方在圖中確認。需補中國設備商 qualification 的一手／第三方文件才能升級此條的證據等級。

---

## 5. 最強證據（Tier 1；標注 origin 以利 L8 獨立性判斷）

- **[E5]** AMAT 10-K：非前沿節點對應 IoT／通訊／汽車／電源／感測器；200mm 業務 FY2026 併入半導體系統（origin: Applied Materials）。→ 成熟製程曝險的結構定義。
- **[E1]** AMAT 10-K claim：FY2025 成長由 leading-edge 投資驅動；中國營收佔比 ~37%→~30%（origin: Applied Materials）。→ 成熟／中國基座下滑的量化錨。
- **[E7]** 圖中 `Export Controls → AMAT` 邊 `substitutability=1`（origin: Applied Materials）。→ TAM 壓縮不可迴避。
- **GF 20-F（客戶端，origin: GlobalFoundries）**：essential-chip 產能擴張仍在進行，但依賴少數設備供應商、交期 12 個月+。→ **唯一非供應商自報**的成熟製程 WFE 需求印證（L8 第三方／客戶端來源）。
- **LRCX 10-K（origin: Lam Research）**：Reliant 非前沿翻新產品線存在。→ LRCX 對稱成熟製程曝險。

---

## 6. 什麼會推翻這個 Thesis（Disproof Conditions）

- **中國成熟製程基座止跌**：若 AMAT／LRCX 中國營收佔比回穩 ≥35%，**且**非前沿／ICAPS WFE 連續 2 季 guide up → 「成熟製程多年消化」前提失效。**核查頻率**：每季 10-Q／法說會。**觸發後 48h**：降 thesis 到 `watch`，重估「中國成熟製程份額」假設，並標記需要新的一手數據。
- **國產替代停滯**：若 GF／UMC／SMIC 等 trailing-edge 客戶揭露顯示中國設備商 qualification 進度停滯、AMAT／LRCX 成熟節點份額未流失 → 「國產替代吃份額」這條腿弱化，降權此瓶頸。**核查頻率**：每季 + 上述客戶法說會。**觸發後 48h**：把主瓶頸從「份額流失」下修為「純週期消化」，重寫第 4 段。
- **市場自己重估全書**：若 leading-edge / AI 明顯降溫、倍數壓縮到成熟製程不再是「被藏起來的拖累」（即市場已把整本書一起 re-underwrite）→ variant 關閉，alpha 消失（推論，非圖中明確主張）[E2]。

---

## 7. 接下來盯什麼（Leading Indicators / Catalysts）

- **中國營收佔比**：是否續破 30%、或止跌回升；觀測頻率：每季 10-Q／10-K。
- **非前沿 / ICAPS / 200mm WFE 語調**：法說會中成熟製程設備需求 guide up 還是 down；觀測頻率：每季法說會 [E5]。
- **中國設備商 qualification 里程碑**：AMEC／Naura／SiCarrier 於 trailing-edge 產線的取單（產業新聞 + 客戶端揭露）；此為「國產替代」leg 的直接讀數。
- **GF／UMC 成熟製程 capex 指引**：CHIPS Act 補貼下的西方成熟製程擴產節奏，是中國國產替代的對沖信號（origin: GlobalFoundries／UMC）。
- **LRCX Reliant／CSBG mix**：非前沿翻新設備佔比走勢；觀測頻率：每季法說會（origin: Lam Research）。
- **BIS 稽核進度**：懸置否認令三年窗口的里程碑或延誤 [E8]；觀測頻率：每季 10-Q／重大事件。

---

## Variant Perception

- **市場現在信 X（由估值倍數反推，非用分析師目標價）**：現價 $529.66 對應 Forward P/E **31.6x**、EV/Revenue **14.46x**（最新毛利率 49%）。這個倍數把 AMAT 定價成一台「乾淨的 leading-edge / AI-WFE 複利機器」——市場隱含假設是：占營收約 **30–40% 的成熟製程 + 中國曝險那一塊，要嘛穩定、要嘛是免費的上檔選擇權**，而不是多年結構性逆風。分析師均值目標 $623（N=35）只是佐證市場仍以成長倍數承保全書，**本 X 是從倍數推得、不是取目標價**。
- **本 thesis 認為 Y**：成熟製程（ICAPS／非前沿／200mm ＋ 中國）這塊正處 2021–24 中國 trailing-edge 擴產後的**多年消化**，並在中國本土設備補貼夾殺下於 trailing-edge 節點**結構性流失份額**。31.6x 的遠期倍數**沒有為這塊的結構性下滑折價**；leading-edge/AI 成長遮住了一個縮水、中國集中的成熟製程基座。真實情況是「AI 成長軌」與「成熟製程衰退軌」被市場用同一個高倍數混合承保。
- **催化劑 Z**：中國營收佔比續破 30%、非前沿／ICAPS WFE 明確 guide down、中國設備商在 GF／UMC／SMIC 的 trailing-edge 產線拿下 qualification、或 BIS 稽核負面更新——任一發生，都會迫使市場把 AMAT／LRCX 從「純 AI-WFE 倍數」重估為「AI 成長 ＋ 成熟製程結構性衰退」的混合體，壓縮遠期倍數。

*（估值數據來源：Engine C 市場快照，AMAT，抓取於 memo 生成時；倍數為 Variant Perception 的定價錨，非時變觀測入圖。）*
