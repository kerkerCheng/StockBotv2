# 成像雷達晶片組開層＋Arbe 座位：Tier-2 晶片組（GlobalFoundries 代工），Hirain 的 L4 專案已開始出貨、L3 專案 2027 年第四季量產交貨（聯合新聞稿）；Arbe 另賣整套雷達給 robotaxi 業者

- Research Action: `ra_2cdabb0bd2babf5bf1d06ad48c9c8b6b`
- Approved digest: `15a036425e3ea532301d318a1c66dc10b90d3429502f3b6d3921139d0ecc2428`
- Prepared (UTC): `2026-10-27T14:58:57.310235+00:00`

## 為何此時入圖

①decompose R7（robotaxi，lead_34ef9086）停放成 partial，等「Arbe 的 6-K／20-F 具名 Tier 1 量產單」——20-F 寫了 Hirain 的具約束力訂單，Q1 新聞稿寫已出貨，但這些申報早於名冊登記，叫不醒它；②段 5 閉環 ARBE 的讀圖格卡在「圖上沒有它供貨或開發的層」（co:arbe_robotics 0 條邊），照 SKILL 的路是補座位走 pq2。

## 研究發現

①新層 tech:imaging_radar_chipset is_component_of tech:automotive_radar（既有，is_component_of tech:robotaxi_fleet）：20-F「we supply imaging radar chipset to Tier 1 manufacturers who are building imaging radar systems」；聯合新聞稿「Hirain’s imaging radar, powered by Arbe’s ultra-high-resolution radar chipset」。②co:arbe_robotics supplies_to 本層（20-F、Q1 出貨、聯合新聞稿 designed_in）。③co:globalfoundries supplies_to co:arbe_robotics：「We rely on GlobalFoundries for manufacturing and testing our chipset」。④co:arbe_robotics supplies_to tech:automotive_radar：Q1 開始賣整套雷達、robotaxi 業者用 Phoenix 追加訂單（自述、客戶未具名）。⑤Hirain：2022 年預訂 34 萬顆、2026 年出貨數千顆的具約束力訂單（20-F）；L4 專案 2026-12 SOP、2027 年數千台（2025-12-29 6-K，本包未入、只在節錄檔）；L3 專案 2027 年第四季量產交貨。

## 文件清單

- `arbe_20f_fy2025_20260327` — Arbe Robotics Ltd. Form 20-F（FY2025，2026-03-27）：Tier-2 成像雷達晶片組（多通道 RF IC＋雷達處理器），GlobalFoundries 代工與測試；Hirain 2022 年預訂 34 萬顆、2026 年出貨的數千顆具約束力訂單；具名競爭者 TI、NXP、Mobileye; storage=`repo_excerpt`; nodes=4, edges=3, claims=2
  - 發文者：origin=Arbe Robotics ｜ source_type=filing ｜ tier=1
  - URL: https://www.sec.gov/Archives/edgar/data/1861841/000121390026035653/ea0283041-20f_arbe.htm
- `arbe_6k_q1_2026_pr_20260528` — Arbe Robotics 6-K（2026-05-28，Q1 2026 財報新聞稿）：開始出貨晶片組給 Hirain 的 L4 專案、開始賣整套雷達（自建產線）、robotaxi 業者用 Phoenix 追加訂單; storage=`repo_excerpt`; nodes=3, edges=2, claims=1
  - 發文者：origin=Arbe Robotics ｜ source_type=filing ｜ tier=1
  - URL: https://www.sec.gov/Archives/edgar/data/1861841/000121390026061736/ea029225201ex99-1.htm
- `arbe_hirain_l3_joint_pr_20260908` — Hirain 與 Arbe 聯合新聞稿（Arbe 6-K 2026-09-08）：全球最大汽車集團之一為中國 L3 乘用車專案選用 Hirain 成像雷達（Arbe 晶片組），Hirain 製造與整合，2027 年第四季開始量產交貨; storage=`repo_excerpt`; nodes=3, edges=2, claims=1
  - 發文者：origin=Arbe Robotics ｜ source_type=filing ｜ tier=1
  - URL: https://www.sec.gov/Archives/edgar/data/1861841/000121390026097831/ea030464401ex99-1.htm

## 入圖副作用（prepare 當下對圖核對；只印、不放閘）

- 圖的增量：新增 2 節點、4 邊、4 claims（另 2 筆已在圖上或逐字保留）
- `arbe_20f_fy2025_20260327`：不會改到圖上任何既有節點屬性、SourceDoc 欄位或 claim（新節點 2 個）
- `arbe_6k_q1_2026_pr_20260528`：不會改到圖上任何既有節點屬性、SourceDoc 欄位或 claim（新節點 2 個）
- `arbe_hirain_l3_joint_pr_20260908`：不會改到圖上任何既有節點屬性、SourceDoc 欄位或 claim（新節點 2 個）
- 入圖後證據等級會變的邊 4 條：
  - `co:arbe_robotics supplies_to tech:automotive_radar`：新邊 → 自報·filing
  - `co:arbe_robotics supplies_to tech:imaging_radar_chipset`：新邊 → 自報·filing
  - `co:globalfoundries supplies_to co:arbe_robotics`：新邊 → 外部印證
  - `tech:imaging_radar_chipset is_component_of tech:automotive_radar`：新邊 → 外部印證
- 「會被覆寫」＝載入時以本包的節點宣告／SourceDoc 欄位直接 SET 圖上既有值（最後載入者贏）；讀不到圖時印「副作用無法核對」，不是「無副作用」。
- 證據等級預告＝本包照 loader 的 MERGE 語意併進當下的圖，用分類的唯一 owner 前後各算一次（逐來源具名＋轉述）；它是預告，入圖後以真的圖重算為準。

## 搜尋過程摘要

讀了 library/raw 的三份 Arbe 一手節錄（20-F FY2025、2025-12 至 2026-09 的 6-K 新聞稿、流動性與稀釋），都是本機抓 SEC HTML 逐字核對。Hirain（经纬恒润）不在公司名冊，沒讀它自己的公告——聯合新聞稿是 Hirain 唯一的聲音，所以不建 Hirain 節點。NVIDIA 的 Hyperion 合格感測器名單只出現在 Arbe 自述與敘事引用的 NVIDIA 部落格，本包不建 NVIDIA 邊。

## L8 確認備註

三份都由 Arbe 申報；其中 2026-09-08 是 Hirain 與 Arbe 的聯合新聞稿（客戶 Tier 1 共同署名），是三份裡唯一帶客戶聲音的。邊是「Arbe 供晶片組／雷達」，不是瓶頸或唯一來源主張——20-F 自己點名 TI、NXP、Mobileye、Huawei、Calterah 等競爭者，不設 sole_source。

## 反向證據與缺口

①量很小：營收 2025 全年 100 萬美元、2026 年 Q1 0.5、Q2 0.7 百萬美元，6-30 backlog 100 萬美元（時變數字，不入圖，L4）；2026 全年展望 400–600 萬美元。②設計勝選延後：20-F 寫兩家前五大車廠的選型從 2024 延到 2026、2027；Q2 新聞稿不再給設計勝選時程。③9 顆雷達裡幾顆是成像雷達、其餘 MMIC 誰供應（R7 的另一半問題）仍沒答——NVIDIA Hyperion 一手沒寫。④本層的供給側目前只有 Arbe 一家在圖上，是因為只讀了 Arbe；這不是『只有一家』的證據（競爭者 claim 已寫）。⑤現金跑道黃燈、持續增資稀釋（見敘事）。

## Server-verified apply receipt

- Applied documents: 3
- Open graph conflict IDs: none
- `arbe_20f_fy2025_20260327` — graph status=`loaded_or_already_complete`; storage=`repo_excerpt`
- `arbe_6k_q1_2026_pr_20260528` — graph status=`loaded_or_already_complete`; storage=`repo_excerpt`
- `arbe_hirain_l3_joint_pr_20260908` — graph status=`loaded_or_already_complete`; storage=`repo_excerpt`
