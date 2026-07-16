# 最小投資規則 SOP（人工執行版）

> **版本：** v2 — 人工決策、機器驗證政策數字。
> **用途：** L9 前置條件 #2。這份文件存在且非空，代表「最小投資規則已定義」。
> **性質：** 方向備忘，不是法律或財務建議。本機單人自用。

本文件是**規則語意與人工流程權威**；目前百分比、門檻、天數與 `policy_version` 的唯一數值權威是 `config/investment_policy.json`。調整數字只改 JSON，不修改 Engine C 的歷史觀測。

---

## 進場條件（全部滿足才進場）

1. Lane Memo 輸出標籤為 `[Watchlist Candidate]`，非 `[Research Note]`
2. Variant Perception 已明確填寫：「市場現在信 X，本 thesis 認為 Y，催化劑 Z」（不能空白或泛泛而談）
3. 5 項財務核驗清單全部 `ok` 或 `manual_reviewed`（不能有 `missing`）：
   - 客戶集中度 — 前三大客戶合計佔收入是否超過 50%？
   - 毛利率趨勢 — 近 4 季毛利率方向（上升 / 持平 / 下滑）
   - Backlog / 訂單能見度 — 是否有明確的 backlog 或 guided revenue
   - 稀釋分析 — SBC、可轉債、內部人賣股動向
   - 估值壓力 — 與同業 EV/Revenue、P/E 的相對位置
4. `disproof_condition` 已定義，且過去 30 天無觸發跡象
5. L9 三個前置條件全部達標（`thesis/preconditions.py check_all()` 全 True）

---

## 單檔上限

單檔可配置金額取「總資產上限」與「high-risk budget × conviction 係數」兩者較小。低於最低 conviction 不建倉。分析師覆蓋家數達政策門檻時，conviction 係數依政策降級；缺覆蓋資料時明標「擁擠度未知」，不臆測分類。半導體相關標的另受共同因子曝險上限約束。

計算一律呼叫 `thesis/investment_policy.py`，並在回答或模擬事件保存 `policy_version`。Engine C 只保存原始覆蓋家數與估值觀測；`crowding`、係數折扣與「估值是否已反映 thesis」都不寫回 DB。

---

## 持有期

- **最短持有：** 依當前 policy 的 `minimum_holding_days`（避免短線噪音影響 thesis 驗證）
- **定期評估：** 每季至少執行一次 `disproof_condition` 核查
- **最長持有：** 無硬上限，但每年至少做一次完整 thesis re-review

最短持有不是禁止停損：任何 disproof／退出條件一旦觸發，立即進入 48 小時 review，優先於最短持有期。

---

## 出場條件（任一觸發即強制 review，48 小時內決定）

| 觸發條件 | 預設動作 |
|---|---|
| `disproof_condition` 觸發（如指定客戶轉為內部開發光源） | 強制 review → retire 或 revise thesis |
| 連續 2 季毛利率下降超過 5pp | 強制 review → 判斷是週期還是結構性惡化 |
| Sole-source 認定被推翻（出現第二供應商） | 降低 `substitutability` edge 值，重新評估 thesis |
| 財務核驗清單任一項出現重大惡化 | 即時標記 `thesis.status = watch`，升高監控頻率 |
| Lane Memo 重新評分低於失敗閾值（可信度 < 3 或可證偽性 < 3）| 降級為 `[Research Note]`，考慮出場 |
| **主要證據來源可信度危機**（thesis 賴以成立的文件涉造假指控／審計持續經營疑慮／財報重編） | 即時 `review_required`（比照 disproof 觸發，48h 內決策）；圖內以該文件為**唯一來源**的主張標注 `source_under_audit` 並依風險調降 confidence；新增以「重編/審計結果出爐日」為核查點的 disproof 條件。首例：2026-07-12 Sivers（`sivers_ar_2025` 涉 Ningi 指控），見 `docs/solutions/` 與 GitHub Issue #2 |

---

## 前瞻模擬投資

- 實作與操作說明見 `paper_portfolio/README.md`；第一次使用必須明確選擇 base currency 與虛擬 NAV，未初始化時 fail closed。
- 模擬帳本獨立放在 `paper_portfolio/`，不與 thesis、Neo4j 或 Engine C 的事實資料混存。
- 每筆模擬 open/add/trim/close 必須在當下凍結 thesis 版本、價格/FX、部位、理由、預期期間與 disproof condition；事後更正用新 event，不改寫舊紀錄。
- 每季、disproof 觸發或 close 時做 review；績效是決策稽核 context，不自動證明或推翻 thesis。
- `SOXX` 僅是半導體標的可選機會成本對照，不作 gate 或系統成功判準。不維護自訂 AI 供應鏈籃子。
- 此帳本不是歷史回測、不會自動下實盤，也不以少量樣本宣稱 alpha。

---

## Thesis 生命週期提示

```
active → (每季核查 disproof_condition)
       → 若 leading indicator 惡化 → watch
       → 若 disproof 觸發 → review_required（48h 內行動）
              → retire（出場，記錄推翻原因）
              → revised（修正 thesis，重新 active）
```

---

## 版本歷史

| 版本 | 日期 | 變更 |
|---|---|---|
| v1 | 2026-07-08 | 初版，人工執行，對應 L9 前置條件 #2 |
| v2 | 2026-07-16 | 數值移至 versioned JSON；新增覆蓋折扣、因子曝險與退出優先規則 |
