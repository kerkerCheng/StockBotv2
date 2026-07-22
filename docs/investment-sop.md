# 最小投資規則 SOP（人工執行版）

> **版本：** v4 — Formal Position 規則 + Engine D／Probe／paper／live 決策邊界。
> **用途：** L9 前置條件 #2。這份文件存在且非空，代表「最小投資規則已定義」。
> **性質：** 方向備忘，不是法律或財務建議。本機單人自用。

本文件是**規則語意與人工流程權威**；目前百分比、門檻、天數與 `policy_version` 的唯一數值權威是 `config/investment_policy.json`。調整數字只改 JSON，不修改 Engine C 的歷史觀測。

本文件中的 Decision Lab 正式定位為 **Engine D — Decision & Accountability Engine**：它消費 Engine A/B/C 與持股／policy context，保存決策時點與責任紀錄；它不是第四個資料來源，也不是自動下單引擎。「凍結圖譜」只表示凍結該次決策使用的 Engine A context slice，不是複製整張 Neo4j。

## 先判斷現在處在哪一層

收到推文、報導或自己的投資想法時，不先問「能不能正式建倉」，而依序走：

1. 通過輕量 Probe Gate 後，立即保存 Signal 與零資本的 Shadow Observation。
2. Coverage Gate 檢查 identity、可追溯來源、claim-to-economics path、counter-path、財務／價格 baseline、catalyst、disproof 與 expiry。資料不足仍保留 Probe，但只產生有界的 Minimum Viable Research Packet 工作單。
3. Coverage 通過後，以五軸 Confidence Envelope 找出 weakest link，分開計算 `paper_target` 與 `live_supported_range`。不同題材不能線性相加抵銷缺失的必要環節。
4. Eligible paper 由 Decision Store 在 system decision 同一 transaction 內建立；live 必須由使用者明確選擇、手動下單，成交後再回報。Google Sheet 仍是 live inventory 唯一權威。
5. 第一眼只讀 Action Card：`NO ACTION / REVIEW / TRADE / HEDGE`、urgency、alpha/beta context、weakest link、兩個 lane、blockers 與下一步。`NO ACTION` 是正式結果，不為了每日輸出製造交易。

Probe 是研究探針，不等於模擬投資；Shadow 是零資本觀測，paper 是使用可配置虛擬 NAV 的 funded simulation，live 才是使用者實際持股。Probe lane 不會降低下方 Formal Position 的升格條件。

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

- 數值由 `config/investment_policy.json` 的 `probe_lane` 管理；預設虛擬 NAV 只是可配置計算基準，不代表真實資產。
- `paper_portfolio/` 保留 domain／replay 介面；paper event 的 runtime authority 與 system decision 共用 ignored private Decision Store，確保 decision + paper apply 原子且可追溯。
- `paper_portfolio/config.json`、`transactions.csv` 與 `engine_c/stockbot.db` 已退出 Git/runtime authority；現存本機檔只是 ignored legacy，fresh clone 不依賴它們。
- 每筆模擬 open/add/trim/close 必須在當下凍結 thesis 版本、價格/FX、部位、理由、預期期間與 disproof condition；事後更正用新 event，不改寫舊紀錄。
- 每季、disproof 觸發或 close 時做 review；績效是決策稽核 context，不自動證明或推翻 thesis。
- `SOXX` 僅是半導體標的可選機會成本對照，不作 gate 或系統成功判準。不維護自訂 AI 供應鏈籃子。
- 此帳本不是歷史回測、不會自動下實盤，也不以少量樣本宣稱 alpha。

完整 recovery backup／export 只能留在 `library/private/`；可進 Git 的診斷輸出必須是明確 allowlist 的 redacted summary。Engine C 的 ETL projection 可重建；帶 `source/as-of/author` 的 append-only manual observation ledger 本身仍是 private authority，因此刪除／重建整個 Engine C 前必須把它納入 recovery backup。Frozen decision、paper event 與 outcome 只允許 backup／restore，不做破壞性 reset。

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
| v3 | 2026-07-21 | 加入 Signal → Shadow → Coverage → Confidence → paper/live 的 Decision Lab 邊界與 private runtime authority |
| v4 | 2026-07-22 | 正式將 Decision Lab 定位為 Engine D；釐清 point-in-time Engine A context slice 並非全圖 snapshot |
