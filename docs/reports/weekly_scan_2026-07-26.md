# 週審查 — 2026-07-26

> 本次為 Codex 本機路徑的首次 bake；掃描窗為 2026-07-19～2026-07-26。只做 topic discovery、
> lifecycle 唯讀提醒與健康審查，不追源、不抽取、不入圖。

## ⚡ 30 秒 brief

- ⛔ `sivers` 仍為 `review_required`；8/27 是既定分辨點，但本週新增 insider transaction 訊號，已進統一待辦 [17]。
- 🔴 Google Sheet 24 列 holdings 全數缺 `market_value_base`、`nav_base`、`base_currency`，Engine D
  無法完成投組覆蓋，已進待辦 [16]。
- 🟡 Engine C 多數 snapshot 已超過 7 天；`SIVE.ST` 財務核驗仍缺 `customer_concentration`、`backlog`。
- 🟡 L8（來源獨立性：供應商自報不能當 sole_source 獨立佐證）仍有一條單一來源邊：
  `co:lumentum -[supplies_to]-> tech:uhp_laser`，目前 `origin_entity` 只有 Lumentum。

## 🧭 Topic Digest

### 1. Sivers lock-up 到期與 insider transactions — `research`

Sivers 7/21 公告：CEO Vickram Vathulya 增持 70,000 股；董事長 Bami Bastani 於 7/16 賣出
275,000 股；Todd Thomson 相關的 Headwaters Capital 截至 7/22 賣出 950,000 股，Kairos 亦回報出售。
公告同時確認 Q2 報告日為 8/27。材料直接觸及目前 `review_required` thesis 的 governance／資本結構面，
但方向混合，不能只用「內部人買／賣」單一標籤解讀。已加入穩定待辦 [17]，下一步才是追公司公告與
瑞典監管申報、比對既有 Ningi audit。[Sivers 公司發布（PR Newswire 轉載）](https://www.prnewswire.com/news-releases/update-on-expiry-of-lock-up-undertaking-and-insider-transactions-in-sivers-semiconductors-302831179.html)

### 2. AMD Helios 正式進入量產，但 MI500 是否採 CPO 仍未被一手公告確認 — `research（既有 [13]）`

AMD 一手公告確認 Helios 已進入生產、2026 下半年開始出貨，並獲 Microsoft、OpenAI、Anthropic、Meta
等採用；官方描述的當代 Helios 網路仍是 Pensando scale-up／scale-out，對 2027 MI500 只寫
「next-generation interconnect technologies」，未在本次公告明指 CPO 或供應商。因此本週社群把
MI500、GFS、Ayar、Sivers 串成供應鏈的說法仍是待驗證推論。既有 X channel-check 待辦 [13] 已覆蓋
這個 exact gap，不重複新增。[AMD 7/23 發布](https://www.amd.com/ja/newsroom/press-releases/2026-07-23-aai-2026-ai.html)、
[AMD／Microsoft 7/20 發布](https://newsroom.amd.com/news/microsoft-azure-ai-infrastructure/)

### 3. Soitec 矽光子成長數字被社群外推為 Sivers 雷射需求 — `FYI`

本週社群轉述「矽光子年增 25–30%、2030 年達 $10B」，再推論外部 InP laser 需求同步成長。材料具體且
與 thesis 相關，但本次只找到社群轉述，未在 weekly 邊界內追到原始 Soitec 頁面；且「矽光子成長」
不等於 Sivers capture rate。保留 FYI，不新增獨立 pq1。[社群轉述](https://www.reddit.com/r/siverssemiconductors/comments/1v2mtk3/why_soitecs_silicon_photonics_projections_are_a/)

## 📋 Thesis 核查

- `sivers`：`review_required`；既定下次核查 2026-08-27。新增 insider transactions 應納入 8/27 前的
  governance／稀釋評估，但本次 weekly 不修改 lifecycle。
- `coherent_cpo`：`active`；下次核查 2026-10-15。

## 🩺 系統健康審查

- 🔴 Thesis 到期：`sivers` 為 `review_required`。
- 🟡 sole_source 單一來源：Lumentum → UHP laser 一條。
- 🟡 Engine C：多數 snapshot 已 8 天；需重跑 ETL。
- 🟡 `SIVE.ST` 財務核驗缺 `customer_concentration`、`backlog`。
- 🟢 Claim／EdgeAssertion 缺 CITES：0。
- 🟢 Graph schema：圖與 repo 同為 `2026-07-16-u3b`。
- 🟢 未處置 edge conflict：0。
- 🟢 TICKER_MAP 漏登記：0。
- 🟢 Research Action 待 publish：0。
- 🟢 Claude Code／Codex skill adapters：無漂移。

## Triage 稽核

**通過：**

- Sivers insider transactions：公司名、日期、股數與角色可逐字核對；對 active risk 具直接關聯。
- AMD Helios：一手公告確認量產與客戶採用；CPO 供應鏈歸因仍未確認，因此保留 research gap 並併入 [13]。
- Soitec 成長數字社群轉述：有具體數字且相關，但來源未追；只列 FYI。

**篩掉／不另立 topic：**

- Broadcom CPO 常設頁：沒有本週新事件。
- GlobalFoundries SCALE（5 月）、Lumentum ELS reliability white paper（6 月）：超出本次 7 日窗。
- 多篇 Sivers／CPO 社群多頭推論：與上列三個 topic 重疊，且沒有新增可核的獨立事件。

## 建議 onboard 候選

本週沒有足以單獨 onboard 的新公司。Ayar Labs、GlobalFoundries、Astera Labs 的名稱均出現在社群供應鏈
推論中，但未出現新的可核 onboarding 觸發點。

## 🖥 本機待跑清單

- [10] 複查 `sivers` lifecycle；本週新增 [17] 應一併納入，但不提前替使用者決定 retire／revise。
- [16] 在 Google Sheet 補齊 `market_value_base`、`nav_base`、`base_currency`（不可用成本基礎代替），
  之後重跑 `python -m decision_lab today --format markdown`。
- [17] 研究 Sivers insider transactions 與既有 governance thesis 的關係。
- [13] 追 AMD MI500／Helios CPO 與實際 optical engine／laser supplier 的一手證據。
- 更新 Engine C snapshots，之後重跑 `python query/health_audit.py --local`。
