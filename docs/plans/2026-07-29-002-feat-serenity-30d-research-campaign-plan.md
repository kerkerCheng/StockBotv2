---
title: Serenity 30-Day Research Campaign - Plan
type: feat
date: 2026-07-29
topic: serenity-30d-research-campaign
artifact_contract: ce-unified-plan/v1
artifact_readiness: implemented
status: completed
product_contract_source: user-request
execution: code-and-research
---

# Serenity 30-Day Research Campaign - Plan

## Goal Capsule

- 目標：補齊 `aleabitoreddit`（Serenity）過去 30 天的 X 貼文、全文與圖片，避免舊的單頁 25 則上限造成永久漏抓，並以新領域探索規則重新 triage。
- 時間窗：2026-06-29T23:01:04Z 至 2026-07-28T22:52:49Z。
- 成本邊界：historical backfill 使用分頁與 `max_posts` 硬上限；不推進 daily `since_id`。
- 權限邊界：campaign 只放寬「已追蹤主題」相關性，不放寬 source-trace、evidence tier、graph admission 或 live 資本 gate。

## Product Contract

### Key Decisions

- KD1. 歷史回補使用 bounded time window＋pagination token；daily 仍走 `since_id`，兩者不能共用游標。
- KD2. 納入 replies 以保留 thread continuation，但先做事件去重；raw post PASS 率不是調鬆指標。
- KD3. 未追蹤公司只要有具名實體／技術機制與可追查 claim 就可 PASS；純績效、喊單、情緒與重複敘事仍 FILTER。
- KD4. 使用者指定 campaign 取得 pq1 排程優先權，但不構成 pq2 或 graph authority。
- KD5. Robotics 研究先停在來源包與 ontology 核准。現行 extraction vocabulary 寫死半導體／光通訊層級，直接套用會污染 Engine A。

### Acceptance

- 279 則貼文全有 `raw_text`；126 則含 media，187 個 media item 均有 ignored private cache。
- 20 筆舊 no-go 重新 triage 時保留原 receipt；daily `since_id` 維持 `2082230983487803755`。
- 初始 campaign triage 為 47 PASS、229 FILTER、3 PARKED；完成 bundle research 後，15 則 robotics 代表 leads 已 checkpoint 為 PARKED 等 pq2 [61]，目前為 32 `triaged_go`、229 `triaged_no_go`、18 `parked`。
- Robotics 核心主張已追回 Agility SEC、GXO、Schaeffler、Hyundai Mobis／Boston Dynamics 一手來源；FCC 禁令未找到官方文本，維持未證實。
- pq2 [61] 保存 robotics ontology mini-slice＋四 origin source bundle 的 exact 核准邊界。

## Verification

```powershell
& '.venv\Scripts\python.exe' -m pytest tests/test_x_harvest.py tests/test_engine_b_leads.py tests/test_engine_b_cli.py tests/test_engine_b_priority.py tests/test_signal_triage_skill.py tests/test_lead_intake_skill.py
python scripts/sync_agent_skills.py --check
```
