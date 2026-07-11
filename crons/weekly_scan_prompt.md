# Weekly Signal Scan — Cloud Routine Prompt

> 這份 prompt 由 claude.ai 的 cloud routine 每週觸發執行。執行環境是 Anthropic 雲端沙盒：
> 有整份 repo 的 clone、有 web search、有 `stockbotv2-graph` MCP connector（讀寫知識圖譜的唯一管道）。
> **連不到使用者本機的任何東西**（Engine C SQLite、本機檔案）——需要圖譜一律走 MCP 工具。
> 設計出處：`docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md` 的 U7。

## 你的任務（四階段 pipeline）

### Stage 0 — 前置

1. 讀 `config/themes.txt` 取得活躍主題清單（`#` 開頭與空行忽略）
2. 讀 `skills/signal-triage/SKILL.md`——Stage 2 的判斷標準全在裡面
3. 呼叫 MCP 工具 `get_extraction_rules` 取得抽取規則書（Stage 3 用；也順便確認 MCP 連線正常）
4. **檢查上週核准待入圖的項目**：用 `gh pr list --repo kerkerCheng/StockBotv2 --label weekly-scan --state all --limit 10` 看上次的 PR/Issue 有沒有使用者留言核准但尚未入圖的抽取草稿（PR 描述中標記 `[待入圖]` 且有使用者的核准留言）。有的話：對每一份呼叫 `load_extraction` 入圖，然後在該 PR/Issue 留言記錄結果並標記 `[已入圖]`

### Stage 1 — Harvest（廣撒網）

對每個活躍主題：
- 用 web search 搜尋過去 7 天內的新訊號：法說會提及、供應鏈/設計窗口/產能變化、競爭者動向、可能觸發 disproof_condition 的消息、下游客戶 M&A、新命名客戶
- 檢查 Engine B 策展來源：搜 `site:aleabitoreddit.substack.com` 或 aleabitoreddit 近期貼文提及追蹤中的公司
- **轉發追源（R14）**：若某則訊號是「轉發第三方研究」（如截圖券商筆記），額外搜尋原始文件。追不到是常態不是阻擋——但 `origin_entity` 必須誠實標記（見 Stage 3）

### Stage 2 — Triage（初篩，照 signal-triage skill 執行）

對每則 harvest 到的原始材料跑四要素判斷（關聯性、新穎性、可引用性、潛在獨立性）：
- 新穎性判斷用 MCP 工具 `get_graph_context` 或 `run_read_query` 比對圖中現有內容；**MCP 連不上時不要卡住——跳過新穎性判斷、寬鬆放行、在稽核紀錄註明**
- 寬鬆原則：軟指標（新穎性、獨立性）不確定時一律放行
- **每一則被篩掉的材料都要記錄摘要 + 理由**，寫進最終報告的稽核段落

### Stage 3 — Extract（對通過 triage 的每一則做完整抽取）

- 嚴格依照 `get_extraction_rules` 回傳的規則書執行（尤其 L6：具體型號/公司名必須逐字出現在 quote；L4：屬性歸位三問）
- `origin_entity` = 誰發出這份文件。轉發型來源追到原文 → 標原始機構；追不到 → 標 `<原始機構>（經 <轉發者> 轉發，未能獨立取得原文）`
- 產出完整的 intermediate-format JSON 草稿（不呼叫 load_extraction——入圖必須等使用者核准）
- **全新公司（不在 `config/themes.txt` 或 `loader/load_to_neo4j.py` 的 TICKER_MAP）不做抽取**，只在報告中列為「建議 onboard 候選」（R13）

### Stage 4 — Report & Approve（開 PR，等人工核准）

1. 把週報寫到 `docs/reports/weekly_scan_<YYYY-MM-DD>.md`，開一個 **PR**（分支名 `weekly-scan/<YYYY-MM-DD>`，**打上 `weekly-scan` label**，不直接 push main）
2. 週報結構：
   ```
   ## 本週訊號掃描 — <日期>
   ### ⚡ 30 秒 brief（若有高訊號事件才寫；沒有就整段省略）
   ### 各主題發現（每主題一段；無動向就一句話說明，不湊字數）
   ### 抽取草稿（每份完整 JSON + 一句「這份能為 L8 帶來什麼」）
   ### Triage 稽核（篩掉了哪些、各自理由）
   ### 建議 onboard 候選（若有）
   ### 可能觸發 disproof 的訊號（若有，標 ⚠ 並引述對應 thesis 的 disproof_condition）
   ```
3. PR 描述開頭放 30 秒摘要 + 待核准清單：每份草稿一個核取項「回覆『核准 #N』即入圖」
4. 純提醒、無可合併產出的事項（如 disproof 觸發跡象）→ 另開 **Issue**（同樣打 `weekly-scan` label）

## 鐵律

- 繁體中文輸出
- 不確定的訊號標「？」，不假裝確定；某主題本週無動向就直說
- **絕不自行呼叫 `load_extraction` 入庫本週新抽取的草稿**——只有 Stage 0 處理「上週已獲使用者核准」的項目時才允許呼叫
- 找不到任何值得說的事 → PR 照開（週報說明這是 sparse week），讓使用者知道系統有在跑
