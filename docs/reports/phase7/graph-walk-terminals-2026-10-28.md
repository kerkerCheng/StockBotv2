# 段 4 走圖：10-28 新命中逐筆終局（2026-10-28）

> 主 session 讀兩端或節點自己的逐字後處置（沒有開判定 workflow）。**point-in-time 紀錄，不是 current-state truth**（AGENTS）；現值以 `python -m query.graph_walk` 為準。終局字彙同 [10-17 那份](graph-walk-terminals-2026-10-17.md)。

**今天九型的命中**（[878]–[881]、[884]–[887] 八個入圖包 apply 之後）：第 4 型 1 → 0（可插拔收發器層當天換版，下面第二張表）；其餘八型的每一筆命中逐筆對過 [10-17](graph-walk-terminals-2026-10-17.md)、[10-22](graph-walk-terminals-2026-10-22.md)、[10-27](graph-walk-terminals-2026-10-27.md) 三份終局表（`library/private/wf_tmp/diff_gw_terminals.py`：命中主詞——重複節點取兩端——沒在任何一份表出現過才算新），新的只有下面 3 筆。

| 型 | 命中 | 終局 | 理由（摘要） | 處置／指標 |
|---|---|---|---|---|
| 6 供貨走不到錨 | `co:arbe_robotics` | intentional | [881] 入圖給了座位：Arbe supplies_to `tech:imaging_radar_chipset` → is_component_of `tech:automotive_radar` → is_component_of `tech:robotaxi_fleet`。鏈沒斷；走不到是因為 `tech:robotaxi_fleet` 刻意不登記成產業錨（failure log #104：登記後結構表 36 列的需求錨被經 co:nvidia 樞紐搶走），與 10-27 那份的 `tech:robotaxi_fleet`、既有的 `co:ouster` 同一個理由。 | 照 #104；robotaxi 錨的登記方式改了，這一筆與 Ouster 會一起消失 |
| 9 重複節點 | `tech:optical_fiber ↔ tech:optical_fiber_preform` | keep_separate | 兩端唯一的共同逐字（STL 法說）本身就把它們寫成前後兩道工序：「…to create ultrapure glass preforms…」、「From there, we draw the highest grade fiber…」——預製棒是拉成光纖之前的玻璃棒。[884] 的拆解就是照這個順序開的三層（預製棒 → 光纖 → 光纜），兩端各有自己的供應商（預製棒：STL、永鼎；光纖另有 Corning 等），合併會讓「預製棒擴產 18–24 個月」這個時鐘失去主詞。名字重疊只是 id token 真子集。 | 不鑄號：兩端都不在名冊條目上，keep_separate 記不進名冊（failure log #97，Z2） |
| 9 重複節點 | `tech:optical_fiber ↔ tech:optical_fiber_cable` | keep_separate | 同一段逐字：「we draw the highest grade fiber, design high-density cables…」——光纜是把光纖成束做成纜；兩端抽象層也不同（光纖 `materials_substrate`、光纜 `module_subsystem`），光纜之上才接連接器與資料中心建置。 | 同上 |

## 第 4 型：一份讀圖當天換版

| 節點［單位］ | 舊 → 新 | 判讀 | 觸發 | 連到的敘事 |
|---|---|---|---|---|
| `tech:pluggable_transceiver`［layer］ | sr_2ef64617 → **sr_d25e6e26** | undecided（不改） | USFP 開層（`92f5e4c8`）補了一條變體邊 `tech:usfp_form_factor is_variant_of`。USFP 是可插拔的下一代外形（OSFP 大小、每通道 400G），走多源路線：需求側「繞不過」多一個一手，供給側沒有新證據（沒有交期、配額、預付，也沒有誰換不掉）。 | AAOI 換騎 `ib_8dd9c93f8af82f18`（「不要」不變，只換讀圖 id） |
