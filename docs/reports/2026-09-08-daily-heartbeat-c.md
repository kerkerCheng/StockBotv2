# 呈現責任重切 C：Daily 收斂成心跳

**日期：** 2026-09-08　**Zoom／Review：** Z2（改 `AGENTS.md` 契約句與 Daily 呈現契約）／R1（operational profile：責任重疊、hook ownership、silent degradation、只有入口沒有出口）　**Verdict：** GO

## 1. 做了什麼

Daily Brief 不再重印已經住在 APP 的四段：**瓶頸排序（含產業分組）／資產配置（目標配置表＋逐檔行情表）／研究缺口／事件監看清單**。取而代之的是一張四列小表，只給計數與「較昨變動」。

**留在 Daily 的**（一格未動）：pq2 四段、pq1 研究進度、部位與問責（**還沒有 APP 畫面**）、賣出側證偽條件、健康降級、建議摘要與批次指令。

## 2. 契約改動（`AGENTS.md`）

兩條 Beta 呈現契約改寫，各自明文寫出廢止：

| 原規則 | 現在 | 為什麼可以改 |
|---|---|---|
| 「即使沒有配置缺口，逐檔表仍**不得省略**」 | 逐檔表與目標配置表住 `#/beta`；Daily 只印門檻跨越與狀態翻轉 | 該規則成立的前提是「Daily 是唯一會更新的 surface」——APP 每天 materialize（Step A）之後前提不再成立 |
| 「兩條相關性警告**每天都要講一次**」 | 由 APP 每個畫面的頁尾常駐 | 「每天講一次」→「每次看都看得到」，後者**不依賴使用者當天有沒有讀 brief**，其實更嚴 |

**invariant 本身沒有放寬**，且新增一條反向保險：**APP 當天沒被 materialize 時，Daily 必須把這件事印出來**——否則「看不到」與「沒發生」又同形（L12）。另在 APP 呈現契約新增「Daily 與 APP 的分工」，把順序寫成 invariant：**APP 先讀得到，Daily 才能不印**；還沒有 APP 畫面的段落（目前是部位與問責）一律留在 Daily。

## 3. hooks 重審：結論與計畫相反

ROADMAP 原本寫「thesis 到期三個嘴 → 一個」。**查證後不成立，所以沒有照做**：

- hook 對**已進待辦池**的項目會靜默（`active_lifecycle_todo_refs`），只講尚未進池的新到期項目。
- `thesis/lifecycle.json` 有 3 條 active、都有 `next_check`（最近 2026-09-28）——**它會觸發，不是死機制**。
- 它是 Daily 沒跑時唯一會說話的東西。2026-09-05→09-08 排程停了三天，那三天只有它。

判準是「這個機制實際產出過幾筆」，不是「看起來像不像重複」。三者的觸發時機、對象與週期都不同，分工已寫進 `docs/OPERATIONS.md`。

**真正刪掉的是 `crons/weekly_scan_digest.py`**：它自 U7b（2026-07-11）之後就沒有掛在任何 `hooks.json` 上，weekly prompt 也不呼叫它——**沒有呼叫端的提醒不是提醒**。連同其測試一起刪；`tests/test_identity_registry.py` 的消費端清單與 ROADMAP 的「5 個消費端」同步改成 4。

## 4. 驗收

| 條件 | 結果 |
|---|---|
| 模板具名 section 瘦身 | ✅ **6,030 → 2,569 字元（−57%）** |
| 實際 brief 具名 section 14.4K → ≤ 7K | 🔶 **估算 ~6.9K**（08-31 實測基準：移除 Alpha 現況 3,958 中的三個 pane、Beta 3,434、外部事件 1,117，新增現況段 ~400）。**實測要等下一份 brief**——這是誠實的未完成項 |
| hooks 由 2 個減為 1 或 0 | ❌ **維持 2 個**，並附不減的理由（見 §3）。原驗收條件本身是錯的：它假設重複，查證後不成立 |
| 死碼清除 | ✅ `weekly_scan_digest.py` 與其測試刪除；活躍引用歸零 |
| 契約與模板同一個 commit 一致 | ✅ `AGENTS.md`／`skills/daily-brief`／`crons/daily_brief_prompt.md`／`skills/alpha-status`／`docs/{OPERATIONS,ARCHITECTURE}.md` 同一次改完 |
| 測試 | **2,088 passed／1 skipped**（2,094 → 2,088：刪掉死碼 `weekly_scan_digest` 的 6 條測試）；五條合約守衛**改家不刪除**（見 §5） |

## 5. R1（operational profile）發現

- **只有入口沒有出口**：新的「現況」段若 APP 沒更新就照印昨天的計數，使用者無從察覺——所以契約要求改印「APP 未更新：<原因>」。這條是這次改動唯一新增的失效模式，已寫進 `AGENTS.md` 與模板。
- **責任重疊**：`$alpha-status` 仍是四 pane 的完整權威，但 Daily 不再嵌入它。skill 的 description 與「與其他 skill 的分工」表同步更新，避免它繼續宣稱自己被嵌入。
- **Daily 少跑四支命令**（`query.bottleneck`／`--by-sector`／`alpha_purity_snapshot`／`query.coverage_gaps`），因為排序資料 `decision_lab today` 已含、覆蓋缺口由 materialize 產出。這順帶縮短 daily 耗時，但**不是**這次的目的，也沒有量測。

## 6. 誠實邊界

- **≤ 7K 是估算不是實測。** 下一份實跑的 brief 才是證據；若超出，該修的是模板而不是改驗收條件。
- 「較昨變動」目前只有**排序**有機器基準（`ranking_order_snapshots.jsonl`）。缺口／watch／sleeve 的變動靠 agent 比對當日輸出與前一份 artifact，沒有持久基準——若之後發現它常常寫不出來，該做的是加一份 counters 快照，不是把這行拿掉。
- 部位與問責仍在 Daily，因為 `positions` kind 還沒做。
