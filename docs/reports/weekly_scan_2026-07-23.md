# 本週訊號掃描 — 2026-07-23

> Stage 0 檢查：`weekly-scan` label 下 merged PR 僅 #1（`weekly-scan/2026-07-11`），已有 `loaded` label，無待入圖項目。
> MCP 連線正常：`get_graph_context` / `run_read_query` / `get_research_action_status` 皆可呼叫。

## ⚡ 30 秒 brief

**Sivers（`sivers`，本週仍 `review_required`）沒有新的明確觸發跡象**：本週新增的是 SEK 700M 增資已完成定價（超額認購，較 6/30 收盤折價 9.7%，稀釋約 3.3%）與鎖股到期後內部人交易（CEO 加碼買進 7 萬股／董事長賣出 27.5 萬股＋捐贈及贈與 13 萬股）。這些是治理與流動性面的觀察，**不構成 Ningi 指控核心（營收認列）的新證據**，維持 `review_required` 至 8/27 分辨點不變。另需注意：本週搜尋撈到的二手來源仍有「審計師出具 going-concern 保留意見」措辭，這與既有一手核實結論（公司自揭 material uncertainty，非審計正式保留意見）不符，見下方說明。

**CPO 供應鏈（`cpo`，coherent_cpo 尚未到期，2026-10-15）**：NVIDIA 對 Coherent／Lumentum 的雷射產能鎖定規模持續擴大（合計約 $4B，出貨量指引由年初約 4000 萬顆上修至 4–5 月約 1 億顆）——方向上加強而非動搖現有 thesis，值得列入下次核查的補充證據，本週不觸發 Stage 4 動作。

**新發現：Aeluma（$ALMU）**——一家 III-V-on-silicon 光子平台公司，訴求繞開 InP 基板瓶頸，且已與圖中既有節點 Tower Semiconductor 有合作關係。若屬實，這對本圖 CPO/Sivers 主題「InP 稀缺性即護城河」的核心假設是潛在的技術替代反證角度，建議列為 onboard 候選（見下）。

## 🧭 Topic Digest

### Topic 1 — NVIDIA 對 Coherent/Lumentum 雷射產能鎖定持續加碼（cpo，建議動作：`research`）

- **摘要：** 市場報導稱 NVIDIA 已合計支付約 $4B 鎖定 Coherent 與 Lumentum 的高功率 CW 雷射產能，對兩家的出貨量指引從 2026 年 1 月約 4000 萬顆上修至 4–5 月約 1 億顆，雙方預計 2027 年開始出貨進 scale-up 硬體。
- **來源：** SDxCentral（"Nvidia's aggressive laser procurement spurs supply chain fears"）等聚合報導；轉述性質，未追一手（NVIDIA/Coherent/Lumentum 申報文件）。
- **對圖的影響：** 與圖中既有 `coherent_cpo_v2_lane_memo` 的 [E1][E2]（NVIDIA $2B 股權＋多年協議至 2030）方向一致，屬於**加碼確認**而非矛盾；「1 億顆」「$4B」是比現有圖內容更具體的新數字。
- **值得 research 的理由：** 若能追到一手來源（如 NVIDIA/Coherent 法說會或 8-K 附件逐字數字），可以补強 coherent_cpo 需求驱动段落的量化強度，且是**客戶端（NVIDIA）而非供應商自報**的證據，對 L8（來源獨立性：供應商自報不能當獨立佐證）有直接補強價值。
- **建議動作：** `research`（本機點名後可依 source-trace 流程追一手）。

### Topic 2 — LPO／主動銅纜與 CPO 於 2026 年仍並存，CPO 部署形容為「narrow」（cpo，反證關鍵字命中，建議動作：`FYI`）

- **摘要：** 多篇 2026 年技術綜述指出，資料中心互連 2026 年仍是傳統插拔式、LPO、CPO、主動銅纜四種方案並存；CPO 已出貨但範圍「narrow」，集中在 AI fabric。
- **來源：** semiengineering.com、eedesignit.com 等技術媒體綜述，屬於泛用市場現況描述，無具體公司/數字可逐字查核。
- **對圖的影響：** 與 `config/themes.txt` 的反證關鍵字（LPO、copper interconnect）相符，但內容過於泛化，答不出對應到圖中哪條 thesis/邊——暫記「新領域／需要更具體事件才能掛勾」。
- **值得 research 的理由：** 目前不夠具體，僅供留意；若未來出現「某 hyperscaler 明確選擇 LPO 而非 CPO」的具名事件，才是真正的 disproof 候選訊號。
- **建議動作：** `FYI`（不建議現在研究，可引性不足）。

### Topic 3 — Sivers：SEK 700M 增資完成定價 + 鎖股到期內部人交易（sivers，併入 Stage 4 核查，建議動作：`FYI`）

- 詳見下方「Thesis 核查」段落，此處不重複列。

### Topic 4 — Aeluma（$ALMU）III-V-on-silicon 光子平台，訴求繞開 InP 瓶頸（onboard 候選，建議動作：`onboard`）

- 詳見下方「建議 onboard 候選」段落。

**排序依據：** Topic 1（對 active thesis coherent_cpo 有直接加碼證據價值）> Topic 4（新公司，且對 InP 稀缺性假設有潛在反證角度）> Topic 3（已在 Stage 4 處理）> Topic 2（新穎性/可引用性皆弱，僅 FYI）。

## 📋 Thesis 核查

### `sivers`（到期：`review_required` 恆視為到期）

- **核查結果：** 本核查週期（2026-07-20 至今）內沒有 Ningi 指控核心（營收不當認列 ~31%／97M SEK）的新一手證據浮現。新增觀察到的兩件事：
  1. **SEK 700M 定向增資已完成定價**（董事會依 6/15 AGM 授權，發行 12,280,701 股，每股 SEK 57，較 6/30 收盤價折價約 9.7%，超額認購；完全稀釋下約 3.3% 稀釋）。市場反應偏懷疑（股價未因增資而止跌）。此舉緩解流動性/going-concern 壓力，但揭露理由僅稱「成長用途」，未如既有 lifecycle 註記所述明確提及 going-concern 動機——中性偏正面看待現金部位，但**不是**對指控本身的反駁或證實。
  2. **鎖股期（至 7/16）到期後內部人交易**（7/21 公告）：CEO Vickram Vathulya 加碼買進 70,000 股（總持股達 4,540,076 股）；董事長 Bami Bastani 賣出 275,000 股、另捐贈 60,000 股及贈與家族成員 70,000 股。訊號混合（CEO 買進偏信心信號，董事長賣出/贈與可能是財務規劃而非基本面訊號，兩者都非決定性）。
  3. Q2 財報（含重編結果）確認仍排定 **2026-08-27** 發布，與既有 `next_check` 一致。
- **L11（自己引用的事實要套用跟圖裡 claim 同一套追源紀律，尤其審計／法律術語）提醒：** 本週搜尋另外撈到多篇二手聚合報導使用「auditors expressed 'significant doubt' about going concern」（即『審計師出具持續經營保留意見』）的措辭。這與 2026-07-20 一手追源結論（`docs/reports/sive-ningi-audit-trace-2026-07-20.md`：AR PDF 逐字核對後只支持「公司自揭 material going-concern uncertainty」，非審計正式保留意見）不一致。**本報告不採用二手來源的這個措辭**，維持既有一手認定；此分歧本身值得記錄，因為它顯示外部媒體持續以更強烈的措辭轉述，8/27 正式文件出爐前應保持警覺，不要被二手措辭「拉走」既有判斷。
- **分級：** 無新增明確觸發跡象 → 維持 `review_required`（原觸發未解除，非本週新觸發），`next_check` 維持 `2026-08-27` 不變（該日期本身就是既有 review 週期的分辨點，非泛用 30 天滾動）。`last_checked` 更新為 `2026-07-23`。
- **lifecycle.json 更新：** 見本 PR diff（`note` 欄位附加本週發現摘要）。

### `coherent_cpo`（下次核查：2026-10-15，未到期）

- 一行記錄：`coherent_cpo`：下次核查 2026-10-15。本週 Topic 1（NVIDIA 產能鎖定加碼）屬於支持性新證據，非 disproof 訊號，故不觸發本 stage 動作；留待下次到期核查或使用者點名時一併採用。

## 🩺 系統健康審查

### 🟢 圖層巡檢

- **sole_source 單一來源（L8 weak）：** 1 條——`co:lumentum -[supplies_to]-> tech:uhp_laser`（origin_entities=["Lumentum"]，僅供應商自報）。與既有 memo 認知一致（Lumentum UHP laser「近乎唯一來源」但僅自陳），非新增問題，維持黃燈觀察。
- **Claim/EdgeAssertion 缺 CITES：** 0 筆。🟢
- **Graph schema 版本：** 圖 `2026-07-16-u3b` / repo 期望 `2026-07-16-u3b`，一致。🟢

### 🟡 未處置 edge conflict（M1：active 引用邊必須為零）

雲端 `CONFLICT_CANDIDATES_CYPHER` 回傳 13 個 over-inclusive 候選；比對 `library/resolutions/*.json`（20 份，以 edge_key 對照）後：

- **9 個已處置**（有對應 resolution 檔）：`2822777d…`、`9a77a192…`、`35435d7e…`、`941281f4…`、`9ef3c3cb…`（此邊同時出現在 sole_source 清單，是同一條 Lumentum UHP laser 邊）、`bc3b0f94…`、`dadc511c…`、`e9616068…`、`f4330d37…`。
- **4 個無對應 resolution，未處置：**
  - `edge:df74dbde…`（AMAT 相關，assertion: `amat_10_k_20251212_e11`／`amat_10_q_20260521_e7`）——**⚠ 此邊被 `thesis/amat_lrcx_mature_node_v1_lane_memo.evidence.json` 引用**，依 M1 規則「active 引用邊必須為零」應為紅燈。
  - `edge:446ebbfe…`（LRCX，`lrcx_10_q_20260423_e4`／`lrcx_10_q_20260129_e2`）——未被任何 evidence manifest 引用。
  - `edge:9f2656ee…`（Lumentum CPO，`lumentum_q2fy26_cpo_e8`／`lumentum_q3fy26_cpo_e4`）——未被任何 evidence manifest 引用；注意這與已解決的 `9ef3c3cb…` 是不同的邊（hash 前綴相近但不同，人工比對時容易看錯）。
  - `edge:f84029ec…`（LRCX，`lrcx_10_k_20250811_e1`／`lrcx_10_q_20260423_e3`）——未被任何 evidence manifest 引用。
- **精確衝突判定以本機 `python query/edge_conflicts.py` 為準**（此處為雲端啟發式，over-inclusive）。

**🔴 紅燈：** `df74dbde…` 是 active-referenced 未處置衝突，違反 M1 規則，建議本機優先處理（`python loader/edge_resolution.py` 或人工核准 resolution proposal）。
**🟡 黃燈：** 另外 3 個未處置但非 active 引用，優先度較低。

### 🟢 TICKER_MAP 覆蓋率

圖中 47 個 Company 節點與 `TICKER_MAP` 全部對齊，無未登記項目（私人公司如 Anthropic/OpenAI/Ayar Labs 等映射 `None` 為合法標記）。

### 🟢 Research Action 待 publish

`get_research_action_status` 回傳 `count: 0`——無卡在 `pending_graph` 的 action。

### 待印證清單（single-origin / orphan evidence）

`SINGLE_ORIGIN_CYPHER`（`$company_id=null`，MCP 端回傳上限 50 筆）：**0 筆 orphan**（所有 claim/assertion 都至少有 1 個 CITES 與 1 個 origin_entity）；single-origin（僅 1 個 origin_entity）筆數多、以個別公司自身法說會/filing 為主（Broadcom、NVIDIA、AMAT、AXT、Coherent 自身數據皆屬此類），這是財報/法說會類一手文件的正常型態，非問題本身——真正需要留意的是**同時是 sole_source=true 或 substitutability≥4 瓶頸邊、且仍單一來源**的子集，已在上方「sole_source 單一來源」段落單獨列出。完整逐公司清單以本機 `python query/single_origin_report.py --company-id co:<slug>` 為準。

### 🟡 L7 欄位完整性

`coherent_cpo_v2_lane_memo.md`、`sivers_v3_lane_memo.md` 皆含「核查頻率」與「48h」欄位，通過。另外 `amat_lrcx_mature_node_v1_lane_memo.md` 也含這兩個欄位，但**該 thesis 未登記進 `thesis/lifecycle.json`**（不在到期核查機制內）——若使用者已決定此切片僅作 L9 前置條件驗證用、非長期監控標的，可忽略；若打算納入常態追蹤，建議本機補登記。列黃燈供確認。

### 🟢 Memo 新鮮度（>90 天）

`crons/thesis_freshness_check.py` 對 lifecycle.json 追蹤的兩條 thesis（coherent_cpo 07-17 已核查、sivers 07-20 已核查）均無超過 90 天未核查項目。

### 🟢 Skills 同步

`python scripts/sync_agent_skills.py --check` 通過，Claude Code / Codex 轉接層無漂移。

### 本機才能查的項目

Engine C（SQLite/Postgres 財務快照）與深度 conflict queue（`query/edge_conflicts.py`）雲端無法直接檢查，見下方「本機待跑清單」。

## Triage 稽核

本次 harvest 共 12 則原始材料（web search 9 次查詢 + aleabitoreddit RSS/site: fallback 2 次 + Aeluma 針對性查證 1 次）。

**通過（4 則）：**
- NVIDIA 對 Coherent/Lumentum 雷射產能鎖定加碼（$4B／1 億顆指引）— 判斷理由：關聯性高（核心公司 COHR/LITE/NVDA）、與既有 thesis 方向一致的加碼證據、潛在獨立性高（客戶端而非供應商自報，對 L8 有補強價值）。
- Sivers SEK 700M 增資完成定價 — 判斷理由：關聯性高（sivers thesis 核心持股）、可引用性強（具體金額/價格/稀釋比例）、直接餵入 Stage 4 核查。
- Sivers 鎖股到期內部人交易 — 判斷理由：關聯性高、可引用性強（具體股數/人名/日期）、對 review_required 核查有輔助價值（雖非決定性）。
- Aeluma（$ALMU）III-V-on-silicon InP 替代平台 — 判斷理由：矛盾/反證價值高（對 InP 稀缺性護城河假設的潛在技術替代反證）、已有 Tower Semiconductor 合作可直接掛勾圖中既有節點，潛在獨立性高（全新未追蹤公司）。

**篩掉（8 則）：**
- LPO／主動銅纜 2026 市場綜述（多篇）— 篩掉理由：可引用性不足（無具體公司/數字可逐字查核），已改列 Topic Digest 的 FYI 項目而非直接篩除記錄於此，供稽核。
- Coherent OFC 2026 展示新聞稿 — 篩掉理由：新穎性不足，內容與圖中既有 `coherent_q3fy26_cpo`/`coherent-corp-cohr...` 主張重複。
- Lumentum OFC 2026 展示新聞稿 — 篩掉理由：新穎性不足，與既有 `lumentum_q3fy26_cpo` 主張重複。
- Sivers 財報時程重申（Q2 於 8/27）— 篩掉理由：新穎性不足，`thesis/lifecycle.json` 已記錄同一日期。
- Sivers AGM 董事購股（7/13）— 篩掉理由：可引用性尚可但與 7/21 鎖股到期交易重複性高、且發生在 7/16 週窗口邊緣之前，重要性低於已列入項目，不重複記錄。
- 「$poet $almu $cohr $axti InP constraint」X 討論串本身（非 aleabitoreddit 原文）— 篩掉理由：來源鏈為三手轉述（第三人回覆 aleabitoreddit 推文提及自己的文章），本身不可引用；但由此線索追出的 Aeluma 公司資訊已獨立驗證通過（見上）。
- aleabitoreddit RSS feed（`https://aleabitoreddit.substack.com/feed`）— **HTTP 403，非「查無新文」**：依規定 fallback 至 `site:aleabitoreddit.substack.com` 搜尋，但 fallback 搜尋也未能命中可判定日期的本週（07-16～07-23）新貼文標題——**判定為「無法確認」而非「本週無新文」**，與 AGENTS.md 既有警語一致（解析失敗 ≠ 無新文）。本機若有 X 帳號可直接查看 timeline，建議本機核對。

## 建議 onboard 候選

### Aeluma（$ALMU）

- **它為什麼值得看：** III-V-on-silicon 異質整合平台，訴求把 InP 雷射直接整合到矽晶圓（200mm/300mm），繞開傳統 InP 基板供應瓶頸；已與圖中既有節點 **Tower Semiconductor**（`co:tower_semiconductor`）及 Sumitomo Chemical 有合作關係。
- **為何現在列入：** 本圖目前 CPO/InP 相關 thesis（Coherent、Lumentum、Sivers、AXT）的核心論點都建立在「InP 基板/雷射產能結構性稀缺」上；Aeluma 若技術路線成立，是對此護城河假設的**潛在技術替代反證**，也是 L8（來源獨立性）意義上一個全新、非既有供應商生態圈的視角。
- **待驗證：** 目前所有描述均來自二手/Substack/Seeking Alpha 分析，尚未追一手（SEC filing、Tower Semiconductor 官方合作公告）；市值小（約 $230M），須留意流動性與資訊品質。
- **建議動作：** `onboard`（人工點名後走 `skills/company-onboard` 流程找一手文件）。

## 🖥 本機待跑清單

1. `python query/health_audit.py --local`——補齊 Engine C 新鮮度、財務核驗清單可跑性、本機精確 conflict queue（`query/edge_conflicts.py`）。
2. **優先：** 處理 `edge:df74dbde…`（AMAT，active thesis 引用）未處置衝突——`python loader/edge_resolution.py` 產生 resolution proposal 或人工核准；另 3 個非 active 引用的衝突（`446ebbfe…`、`9f2656ee…`、`f84029ec…`）次優先處理。
3. 確認 `amat_lrcx_mature_node_v1_lane_memo` 是否要納入 `thesis/lifecycle.json` 常態追蹤，或維持僅作 L9 前置條件驗證用途。
4. Aeluma（$ALMU）若決定 research：先走 `skills/company-onboard` 找一手文件（SEC filing、Tower Semiconductor 合作公告逐字稿）。
5. NVIDIA 對 Coherent/Lumentum 產能鎖定的「$4B／1 億顆」數字：若要正式補進 `coherent_cpo` memo，需先 source-trace 到一手（NVIDIA/Coherent/Lumentum 申報文件或法說會逐字稿），目前只有二手聚合報導。
6. Sivers 8/27 Q2 財報＋重編結果出爐後：依 memo 既有規則執行 48h 內人工決策（retired／revised／維持觀望）。
7. aleabitoreddit 本週貼文無法透過 RSS/web search 確認——若本機可存取 X，建議直接核對 timeline 補齊本週 Engine B 策展面掃描缺口。
8. 追源 backlog aging：目前 GitHub 上唯一 `weekly-scan` label 的 Issue（#2，Sivers 可信度警訊）已開 12 天，未超過 30 天門檻，暫不需提醒；另外 AGENTS.md 記載的 M1 遺留 backlog（TSEM oversupply watch、MACOM/Semtech tier-3 客戶、GF 對 Tower 專利訴訟）目前**沒有對應的 GitHub Issue 可查 aging**，僅存於文字紀錄——如需自動化 aging 追蹤，建議補開對應 Issue。
