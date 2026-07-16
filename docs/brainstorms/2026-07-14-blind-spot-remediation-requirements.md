---
date: 2026-07-14
topic: blind-spot-remediation
planned_in: docs/plans/2026-07-15-008-feat-unified-workplan-plan.md
---

# 盲點修補批次 — Requirements

## Summary

把 2026-07-13 盲點審查的十一條發現落成一批修補：閘門從存在性檢查改為品質檢查、錢的規則統一為單一權威並加擁擠折扣、建立決策帳本、注意力層三個一行修。修尺（Issue #3/#4）提到 M1 之前執行。

---

## Problem Frame

盲點審查對現行設計逐 lens 開火後，發現最危險的不是缺設計，而是**「寫下來的規則」與「程式實際檢查的東西」之間的落差**：L9 gate 用檔名子字串判定里程碑完成、品質閘門在公司層級計數而 L8 風險活在單一邊上、benchmark 有欄位沒有帳。這是 L7 教訓（「欄位存在不等於流程存在」）在三個新地方重演。同時 sizing 規則存在兩套互相矛盾的權威，而它是系統唯一直接輸出金額的地方。

---

## Key Decisions

- **Sizing 雙重上限取 min。** 保留總資產曝險（sop 的 5%）與 bucket 內集中度（conviction 分級）兩套邏輯，明定取小值；數字只住在 `docs/investment-sop.md`，skill 引用不重複。
- **M2 維持 AMAT/LRCX，用因子上限補償。** 換題成本高、L9 時程會後延；接受因子集中，加半導體因子總曝險上限，並承諾第三切片強制出半導體——方法論的跨產業驗證延後但不取消。
- **先修尺再量。** Issue #3（邊身分）與 #4（SourceDoc 節點化）提到 M1 之前：M1 的驗收標準是 origin_entity 計數，不能用已知損壞的 source_ids 量測達標。代價是 M1 晚一個 session。
- **決策帳本住 repo。** `thesis/decisions.csv`——與 thesis 檔同居、進 git 有歷史、任何 session（含手機經 MCP）都能順手補一行。否決 Google Sheets（不進 git）與雙軌（同步是新維運面）。
- **擁擠折扣走數據路線，不走自評路線。** 用 sell-side 覆蓋家數等第三方可驗證觀測，不用「variant perception 強度」自評分——自評落差大小本身有確認偏誤，與 L8「自我報告不能當獨立佐證」同構。variant perception 維持 Lane Memo 必填 gate，不進 sizing 公式。`consensus_coverage` 空槽因此留用。

---

## Requirements

**閘門真實性**

- R1. L9 gate 的 second_slice 檢查驗證內容品質：非 CPO Lane Memo 須含非空 variant perception 段落，且對應 scoring 檔存在並通過失敗閾值（`thesis/scoring_rubric.md`），檔名存在不足以判定完成。
- R2. L9 gate 的財務清單檢查以被建議的標的為對象；清單含未完成的 `manual_required` 項時不得視為通過。
- R3. Lane Memo 品質閘門在公司層級 ≥3 origin_entity 之外，對 thesis 引用的每條 `sole_source=true` 或 `substitutability≥4` 邊單獨檢查來源獨立性；來源全為自報時，該主張在 memo 內強制標 weak。
- R4. Issue #3（邊身分 `(src,type,dst)` + 去重 migration）與 Issue #4（SourceDoc 節點化）先於 M1 完成；M1 達標計數以修復後的圖為準。

**錢的規則**

- R5. 單檔上限的唯一權威規則寫入 `docs/investment-sop.md`：`min(總可投資資產 × 5%, high_risk_budget × conviction 係數)`，係數 5→15% / 4→10% / 3→8% / <3→不建倉；分母綁定 Google Sheets 的 `total_assets` 與 `high_risk_budget` 欄位。U5 skill 改為引用 sop。
- R6. 擁擠折扣：sell-side 覆蓋家數 ≥N、或 forward 估值已隱含 thesis 情境時，conviction 係數降一級（15→10→8→不建倉）；查無擁擠度數據時不折扣，但建議輸出標注「擁擠度未知」。
- R7. `consensus_coverage` 觀測落地為 Engine C 的觀測記錄（ticker、日期、覆蓋家數、crowding 分類、來源）：覆蓋家數由 yfinance ETL 自動抓取；主題層級 crowding 分類由週掃輸出於週報 PR，本機處理 load 時寫入。
- R8. 新增半導體因子總曝險上限：≤ 總可投資資產 25%；sop 內所有百分比上限標明分母。
- R9. 出場條件觸發優先於最短持有 90 天，明文寫入 sop；最短持有僅約束無觸發時的主動出場。

**決策帳本**

- R10. 建 `thesis/decisions.csv`：每筆進/出/hold 決議一行，欄位為日期、ticker、動作、當日價格、thesis 版本、一句理由。
- R11. 定義等權 AI 供應鏈籃子的成分與起算日並記錄——benchmark（對 SOXX 與對籃子）自此可計算。
- R12. 補登 2026-07-12「hold SIVE 至 8/27」決議為帳本第一筆。

**注意力層**

- R13. 核准協定：PR merged 即核准；routine 每次掃描所有 merged 且無 `loaded` label 的週掃 PR（不限上一週），load 成功後打 label，重複執行不重複入圖。
- R14. signal-triage 判斷要素新增矛盾性：與現有 claim/thesis 方向相反的材料，與新 origin_entity 同等優先放行。
- R15. `config/themes.txt` 每主題加 1–2 個替代路徑關鍵字（如 in-house laser、LPO），讓反向訊號有自己的搜尋詞。

---

## Acceptance Examples

- AE1. **Covers R1.** 建立一個只有檔名、無 scoring 檔、無 variant perception 段落的 `thesis/amat_draft_lane_memo.md` → `python thesis/preconditions.py` 的 second_slice 仍為 ❌。
- AE2. **Covers R2.** L9 其餘條件全綠、SIVE 清單含未完成的 `manual_required` 項 → 問「SIVE 買多少」時回答不含 sizing 數字，並說明缺哪一項。
- AE3. **Covers R3.** 某公司有 4 個 distinct origin_entity，但其 `sole_source=true` 邊的來源全為該公司自報 → Lane Memo 正常生成，該主張標 weak。
- AE4. **Covers R5, R6.** conviction 5、bucket 使用率低、但覆蓋家數 ≥N → 建議上限為 `min(總資產5%, bucket×10%)`，非 15%。
- AE5. **Covers R13.** 一個晚兩週才 merge 的週掃 PR → 下一次 routine 執行仍將其 load 入圖並打 `loaded` label。

---

## Success Criteria

- 對修補後的設計重跑 blind-spot-audit 的 A3（證據稽核）、B8（訊號落地）、C10（整合縫隙）三個 lens，原三條 🔴 不再成立。
- benchmark 可實際計算：任取帳本中一筆決議，能算出「該決議 vs SOXX 同期」。

---

## Scope Boundaries

**Deferred for later**

- 換掉 M2 主題——由 R8 因子上限補償；第三切片強制出半導體。
- `consensus_coverage` 的 crowding 分類直寫 Engine C——依賴 Issue #5（Engine C 上 MCP），完成前走「週報 PR 記錄 → 本機落庫」的間接路。
- n=2 的方法論統計效力——記為 assumption，不採取行動。

**已否決**

- Google Sheets 帳本與雙軌帳本。
- variant perception 自評分數作為 sizing 輸入。

---

## Dependencies / Assumptions

- Google Sheets 已有 `total_assets` 與 `high_risk_budget` 欄位（U4 既定格式）。
- yfinance 提供分析師覆蓋家數欄位（`numberOfAnalystOpinions`）——規劃時驗證，不可用則改為手動記錄。
- 方法論 review 在樣本 n<3 時，結論限於「調整」，不做「放棄」級判斷（單一樣本的輸贏都不構成方法論級證據）。

---

## Outstanding Questions

**Resolve Before Planning**

- 擁擠折扣的覆蓋家數閾值 N（建議預設 8，使用者拍板）。

**Deferred to Planning**

- 帳本「當日價格」欄位的取值來源（手填 vs Engine C 快照自動帶入）。
- R3 的邊層檢查實作位置（`generate_lane_memo.py` gate 內 vs `validate.py` 第四層擴充）。

---

## Sources & Research

- 2026-07-13 盲點審查（本批次的 origin；十一條發現與 file:line 錨點）
- `docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md` — U1/U5/U7 現行設計
- `docs/investment-sop.md` — 修訂主對象
- `thesis/preconditions.py` — R1/R2 修改對象
- `schema/graph_schema.md` §5–§7 — source_ids 已知限制與 L8 鐵律
- `skills/signal-triage/SKILL.md` — R14 修改對象
- GitHub Issue #3（重複邊）、#4（SourceDoc 節點化）、#5（Engine C 上 MCP）
