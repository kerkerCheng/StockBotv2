# 週審查 — 2026-07-26

> 本次為 Codex 本機路徑的首次 bake；掃描窗為 2026-07-19～2026-07-26。只做 topic discovery、
> lifecycle 唯讀提醒與健康審查，不追源、不抽取、不入圖。
>
> **同日流程校正：** triage PASS 後由 routine 直接進 pq1（追源＋抽取），prepared Research Action
> 才進 pq2。下文原先的 raw lead 編號 `[13]`／`[17]` 僅保留當次報告脈絡；目前已移回 pq1，
> 不再要求使用者在研究前先核准一次。

## ⚡ 30 秒 brief

- ⛔ `sivers` 仍為 `review_required`；8/27 是既定分辨點。本週 insider transaction 已在 pq1 追回
  公司公告與瑞典監管申報，結果併入既有 pq2 [10]，不另造第二個核准項。
- 🔴 Google Sheet 24 列 holdings 全數缺 `market_value_base`、`nav_base`、`base_currency`，Engine D
  無法完成投組覆蓋，已進待辦 [16]。
- 🟢 Engine C 35/35 snapshots 已於同日本機 ETL 更新；`SIVE.ST` 財務核驗仍缺
  `customer_concentration`、`backlog`，這是證據缺口而非 ETL 健康故障。
- 🟡 L8（來源獨立性：供應商自報不能當 sole_source 獨立佐證）仍有一條單一來源邊：
  `co:lumentum -[supplies_to]-> tech:uhp_laser`，目前 `origin_entity` 只有 Lumentum。

## 🧭 Topic Digest

### 1. Sivers lock-up 到期與 insider transactions — `research`

Sivers 7/21 公司公告：CEO Vickram Vathulya 增持 70,000 股；董事長 Bami Bastani 於 7/16 賣出
275,000 股；Todd Thomson 相關的 Headwaters Capital 截至 7/22 賣出 950,000 股，Kairos 亦回報出售。
公告同時確認 Q2 報告日為 8/27。材料直接觸及目前 `review_required` thesis 的 governance／資本結構面，
但方向混合，不能只用「內部人買／賣」單一標籤解讀。pq1 已追回[公司原始公告](https://www.sivers-semiconductors.com/press/update-on-expiry-of-lock-up-undertaking-and-insider-transactions-in-sivers-semiconductors/)
及[瑞典金融監管機關申報](https://marknadssok.fi.se/Publiceringsklient/en-GB/Search/Search/Insyn?SearchFunctionType=Insyn&Utgivare=Sivers+Semiconductors&button=search&page=3&paging=True)：CEO 70,000 股買進可交叉核對；
多筆 Todd Thomson 關係人處分亦可逐筆核對。這是帶日期的治理／持股 observation，依 L4 不進靜態圖；
lead 已 park 並路由到既有 lifecycle pq2 [10]。

### 2. AMD Helios 網路架構可核，但 MI500／CPO 供應鏈說法仍未被一手公告確認 — `research 完成／park`

AMD 一手資料明確描述 Helios 使用 Pensando Salina、UALoE、Vulcano 800 與 open Ethernet；AMD／Broadcom
場次另確認 Helios／UALoE 建於 Broadcom Tomahawk 與 open eSUN。這些頁面都沒有出現 co-packaged
optics；因此原 X 貼文把未來 MI500／Helios 與 CPO 串起來的部分仍是 tier 4 未證實推論，不建立 graph
claim、不產空 Research Action，lead 已 park。[AMD networking](https://www.amd.com/en/blogs/2026/ai-networking-built-for-scale.html)、
[AMD Helios](https://www.amd.com/en/products/rackscale-solutions/helios.html)、
[AMD／Broadcom 場次](https://www.amd.com/en/corporate/events/advancing-ai/sessions-catalog/ethernet-scale-up-networking-for-next-generation-ai-workloads.html)

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
- 🟢 Engine C：修前 30/35 snapshots 已 8 天；同日重跑 ETL 後 35/35 freshness 通過。
- 🟡 `SIVE.ST` 財務核驗缺 `customer_concentration`、`backlog`。
- 🟢 Claim／EdgeAssertion 缺 CITES：0。
- 🟢 Graph schema：圖與 repo 同為 `2026-07-16-u3b`。
- 🟢 未處置 edge conflict：0。
- 🟢 TICKER_MAP 漏登記：0。
- 🟢 Research Action 待 publish：0。
- 🟢 Claude Code／Codex skill adapters：無漂移。

## Triage 稽核

**通過：**

- Sivers insider transactions：公司名、日期、股數與角色可逐字核對；pq1 追源後路由到 [10]，不入圖。
- AMD Helios：一手頁面確認現行網路架構；CPO／MI500 供應鏈歸因未確認，降為 lead-only 並 park。
- Soitec 成長數字社群轉述：有具體數字且相關，但來源未追；只列 FYI。

**篩掉／不另立 topic：**

- Broadcom CPO 常設頁：沒有本週新事件。
- GlobalFoundries SCALE（5 月）、Lumentum ELS reliability white paper（6 月）：超出本次 7 日窗。
- 多篇 Sivers／CPO 社群多頭推論：與上列三個 topic 重疊，且沒有新增可核的獨立事件。

## 建議 onboard 候選

本週沒有足以單獨 onboard 的新公司。Ayar Labs、GlobalFoundries、Astera Labs 的名稱均出現在社群供應鏈
推論中，但未出現新的可核 onboarding 觸發點。

## 🖥 本機待跑清單

- [10] 複查 `sivers` lifecycle；把已核對的 insider transactions 納入，但不提前替使用者決定 retire／revise。
- [16] 在 Google Sheet 補齊 `market_value_base`、`nav_base`、`base_currency`（不可用成本基礎代替），
  之後重跑 `python -m decision_lab today --format markdown`。
- Lumentum → UHP laser 補非供應商 origin 的獨立證據；在找到證據前維持黃燈，不做假修復。
- `SIVE.ST` 的 `customer_concentration`／`backlog` 需一手披露；不得用猜測補欄。
