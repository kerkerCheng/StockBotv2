# 段 4 走圖：11-07 新命中逐筆終局（2026-11-07）

> 主 session 讀兩端或節點自己的逐字後處置（沒有開判定 workflow）。**point-in-time 紀錄，不是 current-state truth**（AGENTS）；現值以 `python -m query.graph_walk` 為準。終局字彙同 [10-17 那份](graph-walk-terminals-2026-10-17.md)。

**今天九型的命中**（[910]–[912] 三個入圖包 apply 之後）：第 4 型 1 → 0（模組 DSP 層當天換版，下面第二張表）；其餘八型的每一筆命中逐筆對過 [10-17](graph-walk-terminals-2026-10-17.md)、[10-22](graph-walk-terminals-2026-10-22.md)、[10-27](graph-walk-terminals-2026-10-27.md)、[10-28](graph-walk-terminals-2026-10-28.md) 四份終局表（`library/private/wf_tmp/diff_gw_terminals_1107.py`：命中主詞——重複節點取兩端——沒在任何一份表出現過才算新），56 筆裡新的只有下面 1 筆。

| 型 | 命中 | 終局 | 理由（摘要） | 處置／指標 |
|---|---|---|---|---|
| 6 供貨走不到錨 | `co:navitas` | intentional | [911] 入圖給了座位：Navitas supplies_to `tech:power_gan`（第三季財報稿：首批美國製 Gen 5 GaNFast 經 GlobalFoundries 出貨、用來加速 AI 基礎設施）。這一層需求側在圖上 0 條，是 [911] 刻意只建供貨邊：客戶沒具名（10-Q 只到經銷商，Distributor A 占 55%；法說那張 100 萬顆 800V DC-DC 的 GaN 訂單沒寫是誰；與 NVIDIA 是合作開發 800V 轉 12V 電源板、不是採購），沒有買方一手可以接到 AI capex 錨。同日寫的這一層第一份讀圖 `sr_33e1591376daceef` 判不出，寫明缺的就是需求側那一格。GlobalFoundries 也供這一層，但另有走得到錨的供貨邊，所以只剩 Navitas 被報。 | 能讓它接上錨的只有伺服器電源廠、雲端業者或 GPU 平台 800V 架構文件的一手，具名 GaN 供應商並寫出量；拿到就研究包另走 pq2 補需求邊。等待：NVTS 敘事 `ib_c6498238f5b2fb2e`（缺 X，missing_kind＝layer）的 ew_2242（2027-03-01，2026 年報）；既有追源 watch ew_0744–0748（台達、Navitas、NVIDIA、X-FAB 的一手，2027-02-14 到期） |

## 第 4 型：一份讀圖當天換版

| 節點［單位］ | 舊 → 新 | 判讀 | 觸發 | 連到的敘事 |
|---|---|---|---|---|
| `tech:optical_module_dsp`［layer］ | sr_59fdb499 → **sr_ad028e11** | volume（不改） | [910] 入圖 `co:zhongji_innolight depends_on`：中際旭創 10-29、11-03 兩份投資者關係活動記錄表由圖外改成圖上引用（需求側 4 → 5 條），沒有新事實；反證①–③一字不改，出處改寫成沿用上一版。 | MXL 換騎 `ib_440dd84748e6056f`（缺 X 不變，只換讀圖 id） |

另：`tech:power_gan` 的第一份讀圖（`sr_33e1591376daceef`，undecided）是段 5 NVTS 閉環缺讀圖的那一格，不是走圖命中；NVTS 換騎 `ib_c6498238f5b2fb2e`、故事 `st_608408b3686943ba`。
