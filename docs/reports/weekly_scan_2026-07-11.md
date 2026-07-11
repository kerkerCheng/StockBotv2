# 本週訊號掃描 — 2026-07-11

> 本次為 U7 cloud routine 第一次執行（`gh pr list --label weekly-scan` 查無歷史紀錄，Stage 0 無待入圖項目）。
> MCP 連線正常：`get_extraction_rules` / `get_graph_context` / `run_read_query` 皆可呼叫。

## ⚡ 30 秒 brief

**Sivers Semiconductors（本專案 sivers 主題核心持股）本季捲入短賣機構指控 + 審計「持續經營疑慮」，且事態延燒到本週（7/9 內部人買股、財報時程二度延後）。** 這不直接命中圖裡任何現有 `disproof_condition` 的字面條件，但圖中多筆 Sivers「confirmed/guided」主張的來源正是 `sivers_ar_2025`（Sivers 自己的年報）——而這份年報現在正是被指控「浮報營收」、且審計師已提出重編的文件。**建議人工複核以 `sivers_ar_2025` 為唯一來源的主張，评估是否要調降 confidence 或標記待驗證，直到重編財報/訴訟結果明朗。** 詳見下方「可能觸發 disproof 的訊號」。

其餘：找到一則值得列入「建議 onboard 候選」的獨立來源（AXT/Tongmei ×Coherent 的 InP 晶圆供應協議），可用來升級 Coherent InP 依賴主張的來源獨立性（L8）。本週兩個主題都沒有找到需要立即抽取入圖的全新一手文件。

## 各主題發現

### cpo（Co-Packaged Optics 供應鏈）

過去 7 天內沒有一手文件等級的新事件（法說會 / IR 新聞稿）。市場面持續消化 OFC 2026（3 月）與 Nvidia 對 Lumentum/Coherent 各 20 億美元投資後的估值波動，7/2 起 photonics 類股一度重挫（AAOI -17%、COHR/LITE -10%），7/9 又反彈（JPMorgan 重申 Overweight，channel check 稱 CPO 採用「on track」）——這些屬於股價/分析師意見層級的時變觀測,依 L4 規則不進圖,此處僅記錄脈絡。

唯一具體、可查核的新素材是 **AXT-Tongmei 與 Coherent 簽署三年期 6 吋 InP 晶圆《Master Development and Supply Agreement》**（2026-06-25 公告，Coherent 預付 2,228.85 萬美元換取承諾供應量,AXT 承諾 2026–2028 擴充北京廠產能）。這則稍早於嚴格 7 天窗口，但因為與圖裡既有的 Coherent `DEPENDS_ON` 6-inch indium phosphide fabrication 邊（confidence 0.90,來源全部是 Coherent 自己的法說會）高度相關,且是**目前罕見的、非 Coherent 自報的獨立佐證**,列入本週重點,詳見下方「建議 onboard 候選」。

Broadcom Tomahawk 6「Davisson」102.4T CPO 交換器已進入出貨階段(原 2025/10 公告的第三代 CPO 平台)——屬於既有主張的進度更新,新聞稿沒有具體點名光學元件供應商,故無法補強任何 edge(供應商名稱未逐字出現於文件中),不做抽取。

### sivers（Sivers Semiconductors InP 雷射）

本主題本週的核心事件不是供應鏈進展,而是**公司治理/財報可信度危機**（見 30 秒 brief）。時間線:
- 2026 年 6 月初:做空機構 Ningi Research 指控 Sivers 將約 31%（約 9,700 萬瑞典克朗）的 2025 年營收不當認列——把政府研究補助當商業營收入帳,並認列尚未生產產品的營收。
- 隨後:董事會成員辭職、瑞典檢方對內線交易展開調查、外部審計師對「持續經營能力」提出重大疑慮,公司被迫依 US GAAP/PCAOB 標準重編 2024/2025 財報。
- **本週（7/9）**:財報時程二度延後（Q2 report 延到 8/27,Q3 延到 11/26）;CEO 與多名董事於 7/9 買進股票（CEO Vickram Vathulya 買進 24,000 股,約 9.86 萬美元）,市場解讀為信心信號,但股價一個月內仍重挫逾 40%。管理層鎖股期至 7/16 到期。

供應鏈面(GlobalFoundries 矽光子合作、$799M pipeline)本身沒有本週新進展——上次更新是 6 月初,已在圖中(`sivers_ar_2025` 來源)。

## 抽取草稿

**本週無抽取草稿。** 兩個主題都沒有一手文件(法說會逐字稿 / IR 簡報 / filing)等級的新素材通過 triage;僅有的高價值素材(AXT-Coherent 協議)因為 AXT 不在 `config/themes.txt` 或 `TICKER_MAP` 中,依規則不做抽取,改列 onboard 候選(見下)。Sivers 的做空機構指控屬於財務可信度議題,不是供應鏈關係,依 schema 設計不進圖(見 CLAUDE.md:consensus/財務數字進 Engine C,不進 Engine A)。

## Triage 稽核

本次 harvest 約 10 則原始材料(web search,7 個查詢;engine_b 管道搜尋 `site:aleabitoreddit.substack.com` 僅命中舊文,無新貼文)。

**通過(1 則):**
- AXT-Tongmei × Coherent InP 晶圆供應協議(2026-06-25 公告)— 判斷理由:關聯性高(直接命中 Coherent 既有 `DEPENDS_ON` 6-inch InP fabrication 節點)、可引用性強(協議金額/期限/雙方名稱具體可查)、**潛在獨立性是四要素裡最高分項**——Coherent 目前所有 InP 依賴主張的來源都是自己的法說會,這是第一個第三方(供應商)獨立佐證。因不在 TICKER_MAP,轉為「建議 onboard 候選」而非抽取。

**篩掉(約 9 則):**
- JPMorgan 7/9 channel check note(稱 CPO 採用 on track)— 篩掉理由:可引用性不足,分析師意見無具體逐字可查核內容。
- Photonics 類股 7/2 重挫、7/9 反彈的股價/資金流報導 — 篩掉理由:屬時變股價觀測,依 L4 規則二不進圖,且非供應鏈事實。
- Broadcom Q1/Q2 2026 法說會「客戶傾向 direct-attach copper 到 2028」的評論(3/5 已發生,非本週新聞)— 篩掉理由:非本週新素材,且圖中既有 disproof_condition 未涵蓋此字面情境(是關於 pluggable 效率提升或 on-chip laser,不是 copper vs optical 的 scale-up 選型),為避免誤植錯誤 disproof 觸發,不列入本週 disproof 段落,僅供人工參考。
- AAOI Sugar Land 廠擴產/Oxford Instruments 設備訂單 — 篩掉理由:公告於 2026 年 1–2 月,非本週新聞,且該擴產計畫已是圖中 Sivers thesis 既有 `disproof_condition` 文字的一部分(不是新觸發,是舊已知計畫的延續執行,無新增資訊判斷是否已提前/延後)。
- Sivers CEO/董事 7/9 買股、財報時程延後公告 — 篩掉理由:屬時變公司治理/內部人交易觀測,不是供應鏈關係,不適合抽取入圖(但已寫入本週報告脈絡,供人工評估來源可信度)。
- Sivers GlobalFoundries 合作(6/2)、$799M pipeline 成長(對外揭露於年報)— 篩掉理由:非本週新素材,已存在圖中(來源 sivers_ar_2025)。
- aleabitoreddit 近期貼文搜尋 — 篩掉理由:最新一篇是 2026-05-20 的 Sivers 客戶地圖文章,已在圖中(`aleabitoreddit_sivers_*`),本週查無新貼文。
- Gaetano(@crux_capital_)在 X 上提及「為 $poet/$almu/$cohr/$axti 的 InP constraint 寫了完整分析」— 篩掉理由:僅為推文轉發連結,未能定位到獨立可讀的原文全文與確切發布日期,追源未果;若之後能找到原文,可重新評估(R14 轉發追源原則)。

## 建議 onboard 候選

- **AXT Inc.(NASDAQ: AXTI,及其中國子公司 Tongmei)** — 理由:與 Coherent 簽署三年期 6 吋 InP 晶圆《Master Development and Supply Agreement》(2026-06-25,Coherent 預付 2,228.85 萬美元),是目前圖中 Coherent InP 依賴鏈**唯一非自報的獨立來源候選**,直接呼應 CLAUDE.md 開發優先序第 2 項(SIVE/CPO 來源品質升級——找不同 origin_entity 的獨立來源)。Onboard 後建議優先抽取這份協議與 AXT 近期法說會(Q1 2026 InP backlog 破 $100M),並在 `TICKER_MAP` 補上 `co:axt: "AXTI"`。

## 可能觸發 disproof 的訊號

⚠ **Sivers Semiconductors — 主要來源可信度疑慮(非既有 disproof_condition 字面觸發,但影響來源品質判斷)**

圖中多筆 Sivers 相關「confirmed/guided」主張(CW 雷射短缺、$799M pipeline、O-Net/GlobalFoundries 產能規劃等)以 `sivers_ar_2025`(Sivers 2025 年報)為唯一或主要來源。現況:
- 做空機構 Ningi Research 指控約 31% 的 2025 年營收(約 9,700 萬 SEK)為不當認列(研究補助 vs 商業營收、認列未生產產品營收)。
- 外部審計師已對「持續經營能力」提出重大疑慮;公司正依 PCAOB/US GAAP 標準重編 2024/2025 財報。
- 本週(7/9)財報時程二度延後至 8/27(Q2)/11/26(Q3),管理層鎖股至 7/16 到期。

這不是任何現有 `disproof_condition` 的字面觸發條件(現有條件談的是 AAOI/Lumentum 產能競爭,不是財報可信度),**但依 CLAUDE.md L8(自我報告確認偏誤)判準,`sivers_ar_2025` 現在的角色從「單一 origin_entity 自報」升級為「正被指控浮報、審計中的自報文件」,獨立性/可信度應視為進一步降級,而非維持原判**。建議人工複核:(a) 是否要暫時調降以 `sivers_ar_2025` 為單一來源之主張的 confidence;(b) 是否需要新增一條追蹤性的 disproof_condition,綁定「若重編財報證實指控成立,或審計師出具持續經營保留意見」;(c) 待 8/27 Q2 財報與重編結果出爐後排入下次掃描重點追蹤。
