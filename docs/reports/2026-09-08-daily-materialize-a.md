# 呈現責任重切 A：讓 daily 排程自動更新 APP 的所有畫面

**日期：** 2026-09-08　**Zoom／Review：** Z1／R1（unattended surface 變更：權限邊界、fail-soft、清單腐壞）　**Verdict：** GO

## 1. 為什麼這一步必須在「Daily 收斂」之前

Daily 之所以還在每天重印那些持久狀態，是因為它是唯一保證會更新的東西。**一旦 Daily 不再印，APP 就必須每天被 materialize**——否則使用者打開看到的是幾天前的數字，而那正是 L13（管子只接一頭：驗收要驗下游消費者手上的東西）。所以順序是 A 先於 C，不是相反。

## 2. Sandbox impact review 五步（`docs/OPERATIONS.md` 的規格）

**① path ＋ side effect ＋ capability**

| 入口 | side effect | capability |
|---|---|---|
| `python -m webapp materialize --tracked --ranking --beta --coverage --watches` | 寫 ignored derived cache（`library/private/app/{analyst_view,state}/*.json`，atomic）。**不寫任何 authority**：不入圖、不寫 Engine C、不建 decision、不 append 風險快照、不碰 `.git` 或 tracked 檔 | Neo4j bolt（本機）＋Engine C SQLite＋private ledger（唯讀）＋Google Sheet `spreadsheets.readonly`＋yfinance FX——**與既有 fixed entry `daily_beta_snapshot.py`／`decision_lab today` 完全同一組**，無新增網路主機或憑證 |
| `python -m webapp serve` | 綁定本機 port | **新增 listener surface**——刻意留在禁止側 |

**② 更新 canonical skill／prompt 與 OPERATIONS**：`crons/daily_brief_prompt.md` 第 8 步、`skills/daily-brief/SKILL.md` Step 7、`docs/OPERATIONS.md`（現況句 16 → 17、新增本次 review 段、舊 review 的「互動專用」列標明已改判）。

**③ 最窄的 exact prefix**：`[".venv\Scripts\python.exe", "-m", "webapp", "materialize"]`。
**放行的是子命令不是模組**——`materialize` 只寫 derived cache，`serve` 會開 listener 且外部認證邊界在 Cloudflare Access 而非程式本身。放行整個 `-m webapp` 會把 serve 一併帶進去，那正是 AGENTS.md 說的「用 broad permission 掩蓋整合缺口」。serve 由開機自啟的 vbs 長駐，排程不需要也不該啟動它。

**④ permission contract test**：`prefix_rule(` 16 → 17；fixed entry 清單加 `"-m", "webapp", "materialize"`；新增一條測試明確斷言三個**相鄰但禁止**的寫法不得出現（`"-m","webapp","serve"`／裸 `-m webapp`／`"-m","webapp","verify"`）。
**兩個突變證明**：① 整條 rule 移除 → 2 failed；② 放寬成整個 `-m webapp` → 2 failed。守衛不是空跑。

**⑤ 端到端 smoke test**：以排程會用的 exact command 實跑一次——**108 秒**跑完 34 份 artifact（30 檔 analyst view ＋ 4 種 state），exit 0；`webapp verify` 34/34 通過 fail-closed 驗證

## 3. ticker 清單不手寫

`--tracked` 由 `engine_b.routine_config.discover_tracked_tickers()` 導出（非 retired lifecycle ＋ non-terminal Decision cohort ＋主題核心公司），**與 pq1 drain 是同一個權威**。

理由不是省事：手寫清單會腐壞，而腐壞的方式是「某一檔安靜地不再被 materialize」——沒有任何東西會報錯，使用者只會看到那一檔的畫面永遠停在某一天。同一個判準在本專案已經記過一次（「清單會腐壞，判準不會」）。

## 4. 為什麼 materialize 失敗是 fail-soft，而 harvest 失敗必須中止

刻意不同：

- **harvest 失敗 → 整輪 Daily 中止**。它持有 writer lock、會寫共用檔；跳過它續跑會讓兩個 writer 撞上。
- **materialize 失敗 → 只記健康段**。它不碰任何共用檔；失敗的代價只是「畫面舊了一天」，而**那是看得見的**——APP 自己會標 stale，artifact 也還在。

把兩者用同一條規則處理，會讓一個無害的失敗炸掉整輪 Daily。

## 5. 驗收

| 條件 | 結果 |
|---|---|
| fixed entry 16 → 17，且只放行 materialize | ✅ `grep -c "prefix_rule(" .codex/rules/…` ＝ 17；`grep webapp` 只有 materialize 一行 |
| 相鄰動詞被明確禁止 | ✅ 新測試斷言 serve／裸 webapp／verify 不得出現；兩個突變證明皆變紅 |
| artifact 由 4 檔變全 cohort | ✅ **4 → 34 份**（analyst view 4 → 30；state 4 種齊）；最舊 artifact 年齡 0.03 小時 |
| 端到端可跑 | **108 秒**跑完 34 份 artifact（30 檔 analyst view ＋ 4 種 state），exit 0；`webapp verify` 34/34 通過 fail-closed 驗證 |
| 測試 | 焦點 133 passed（權限＋四種 state＋request-path＋流程守衛）；完整套件 **2,094 passed／1 skipped**（2,091 → 2,094：權限守衛 1＋流程守衛 2） |

## 6. 誠實邊界

- **Codex sandbox 的 escalation 行為只能在下一次排程實跑時驗證。** 我在本機跑的是同一個 exact command，但無法重現 Codex 的 workspace-write sandbox；rule 是否被正確命中，要看明天 06:30 那一輪。
- **Daily 的耗時會增加**（見驗收表的實測秒數）。現行中位 19 分／p90 30 分，writer lock TTL 90 分鐘，餘裕充足。
- `materialize --beta` 會再讀一次 Google Sheet（`daily_beta_snapshot.py` 已讀過一次）。readonly、量小，但確實是同一天第二次讀。要消除得把 materialize 併進 beta snapshot，那會讓兩個責任混在一起，不划算。

## 7. 下一步（只是建議）

**C — 把 Daily 收斂成心跳**：現在 APP 每天是新的，Daily 才可以不再重印那些段落。同一個 commit 要改 `AGENTS.md` 的 Beta 呈現契約（逐檔表每日心跳 → 只印門檻跨越／狀態翻轉），並重審 SessionStart hooks。
