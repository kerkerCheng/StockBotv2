# Confidence 五軸重構需求（2026-08-02）

> 起因：使用者在 AXT 決策複查後提出兩個問題——「我們很常卡在 source gate，但如果 gate
> 真的過了，alpha 是不是也沒了？」以及「是不是該用減法：有人提出觀點，如果沒有任何證據
> 否定它，就假設有機率成立？」本檔記錄診斷、被否決的方案、被採納的方向，以及已實作到
> 哪一步。要動工先讀完本檔，不要重新發明。

## 1. 觸發本次討論的實測

AXT（AXTI）2026-07 的時間線：

| 日期 | 事件 | 股價 |
|---|---|---|
| 2026-07-26 | 與 Lumentum 簽六年 InP 產能保留協議 | — |
| 2026-07-29 | 8-K 揭露該協議（首期 US$43.5M deposit） | — |
| 2026-07-30 | Q2 財報：營收 +164% YoY、GAAP 毛利率 44.9% | $36.97 |
| 2026-08-02 | 系統首次把上述全部吸收進決策 | $60.43 |

三個交易日 +63%。而系統在 2026-08-02 完成五軸重評後的結論仍是 `DATA_NEEDED`、
supported range `(0, 0)`。**證據補齊的速度慢於價格重定價的速度**，這不是研究做得不夠
勤，而是 gate 的結構決定的。

## 2. 診斷：五軸其實是同一種東西

`decision_lab/sizing.py` 的五軸——`source_reliability`、`technical_causal_link`、
`commercial_maturity`、`financial_resilience`、`valuation_payoff`——全部在問同一個問題：
**證據有多強**。沒有任何一軸在問「如果對能賺多少、如果錯會賠多少」。

後果有二：

1. **高度相關 + 取 min = 最弱那份文件決定一切。** 一份好文件同時抬高數軸，一個缺口同時
   壓低數軸。AXT 的 `technical_causal_link` 是 `corroborated`，但因為取最小值，它對結果
   的貢獻是零——這個軸在實務上只有拖累的可能、沒有幫助的可能，除非它是最弱的一個，
   而它幾乎永遠不會是。
2. **系統只能用「不參與」來表達不確定性。** 沒有賠率維度，就沒有別的旋鈕可以轉。

`valuation_payoff` 名字像賠率，但它的等級一樣是 `unknown` / `bounded_hypothesis` /
`corroborated`，實際衡量的仍是「估值證據夠不夠」，不是「賠率好不好」。

## 3. 被否決的方案：「沒有否證就假設成立」

使用者提出的減法框架方向正確（不該等證據完備），但**具體做法會壞在否證證據的供給
不對稱**：

- 沒有公司會發新聞稿說「我們沒有跟 AXT 簽約」或「我們的良率沒有改善」。
- 空頭報告極罕見——要花錢做、還可能被告。

因此「找不到否定證據」在絕大多數情況下不帶任何資訊：它反映的是這個世界不生產那種
文件，不是反映主張的真假。實務上這個框架會退化成**把「我沒查」誤讀成「查不到反面」**。

Sivers 是完整的反例：若沒有 Ningi 那份罕見的做空報告，它所有說法都會是「沒有被否定」。
而實際情況（公司自揭 going-concern material uncertainty、2023–25 PCAOB 重編、董事會
出走）是主動追一手文件才挖出來的，不是否證證據自己找上門。參見 L11（自己引用的事實
要套跟圖裡 claim 同一套追源紀律）與 L8（來源獨立性：供應商自報不算獨立佐證）。

## 4. 採納的方向：把「證據強度」與「部位大小」解耦

不是「證據不夠就不能動」，而是「證據不夠就只能小注，但可以動」。對應的結構是把現在
的五軸拆成三類，各用不同的數學：

### 4.1 否決類（二元，一票否決，不打折）

會歸零的東西：going concern、審計保留意見、財務造假、流動性斷裂、監管禁令、公司身分
無法解析。這些不是「還沒被證實的好消息」，而是「還沒被排除的災難」，賠付結構不對稱。

現況：散落在 `source_reliability` 與 `financial_resilience` 裡，與時效性的缺口混在一起。

### 4.2 信心類（序數，取 min）

證據強度，即現在五軸做的事，但可收斂成兩軸：

- **主張可信度**：`source_reliability` + `technical_causal_link` + `commercial_maturity`
  合併，三者本來就在問「這件事是真的嗎」。
- **財務承受力**：公司會不會在 thesis 兌現前先死。

### 4.3 賠率類（連續數值，乘法）

目前**完全不存在**的維度：如果對能賺多少倍、如果錯會賠多少。這應該是乘數而非 gate。

最終部位 = 賠率決定的基準尺寸 × 信心折扣，再被否決類一票否決。

## 5. 已實作（2026-08-02）：coverage 嚴重度分類

沒有一次動軸的結構，先改真正把資本打成零的那一行。原本：

```python
coverage_cap = probe["single_probe_nav_cap"] if coverage.status == "analyzable" else 0.0
```

只要有任何一個 coverage blocker，資本上限就是 0，五軸算出的 `axis_ceiling` 完全不作數。
AXT 就是被單一個「算不出 runway」打成零的。

改法是把 blocker 分成兩類（`decision_lab/coverage.py` 的 `fatal_blockers`）：

- **致命（仍歸零）**：`identity_unresolved`、`graph_company_missing`、`best_source_missing`、
  `causal_path_missing`、`financial_missing/unavailable/quarantined`、`disproof_missing`、
  `expiry_invalid`。這些讓決策無法稽核或事後檢驗。
- **研究不完整（只降尺寸，讓 `axis_ceiling` 生效）**：`independent_source_missing`、
  `counter_path_missing`、五項財務核驗清單的各種缺漏、`financial_runway_manual_required`、
  `catalyst_missing`。

兩個判準值得記住：

- **`disproof_missing` 刻意留在致命類。** 不是因為它是災難風險，而是 L7（thesis 生命週期：
  disproof 條件要附核查頻率與觸發後 48 小時動作）的整個紀律建立在它上面。允許沒有證偽
  條件就下注，等於允許一個永遠不會響的警報。`catalyst_missing` 則不致命——可以先小注
  再補。
- **未分類的 blocker 一律 fail closed。** 新增 blocker 時 `tests/test_coverage_severity.py`
  會失敗，強迫做出分類決定，而不是靠預設安靜放行。

實測效果：AXT 的 `coverage_gate` 從 `cap=0.0 / blocked` 變成 `cap=0.005 / available`，
`axis_ceiling` 0.002 得以生效。改動不碰任何軸的定義，不影響既有 frozen decision。

## 6. 未實作，以及動工前要知道的事

### 改動成本（2026-08-02 查證）

- **數值已可 config。** `config/investment_policy.json` 的 `probe_lane` 已含 `axis_ceilings`、
  `rubric_version`、`calculator_version`。調數字零程式改動。
- **軸定義寫死但範圍窄。** `decision_lab/sizing.py` 的 `AXES`、`LEVELS`、
  `AXIS_REFERENCE_AUTHORITIES`；引用處只有它自己、`decision_lab/workflow.py` 一處迴圈、
  與測試。**`skills/` 完全沒有寫死軸名**，改軸不波及研究流程文件。
- **不需要資料遷移。** 每筆決策凍結自己的 `rubric_version` 與 `policy_version`，舊決策永遠
  用舊骨架解讀，新舊共存。

⚠ [`docs/solutions/architecture-patterns/closed-vocabulary-registry.md`](../solutions/architecture-patterns/closed-vocabulary-registry.md)
把五軸／三級列為「刻意凍結（不要打開）」，理由是「評分骨架，已凍進所有既有 decision
payload」。**該理由已因版本化機制而失效**，但登記表尚未更新。真正該保持嚴格的是
`AXIS_REFERENCE_AUTHORITIES`（它擋的是「拿 Engine A 文件冒充 Engine C 財務證據」），
不過嚴格與 config 化並不衝突——`config/authority_tokens.json` 已是先例。動工時一併修
登記表，否則下一個 session 會以為不能碰。

### config 化的邊界

沿用專案既有的 taxonomy 對 contract 判準：

- **可 config（會隨策略演化）**：軸有哪些、每軸接受哪些 authority、各級 ceiling、賠率如何
  換算成基準尺寸。
- **不該 config（改了等於換系統）**：聚合方式（取 min 還是相乘）、否決類的一票否決語意、
  「舊 decision 引用原 digest 不回寫」。

關於使用者提出的「強制只讀不改除非我同意」：**不建議另建權限系統**。`config/*.json` 是
tracked，agent 的改動會出現在 git diff，push 前看得到；且 `policy_version` 凍進每筆決策，
改 config 不會污染舊決策。禁止寫入反而讓提案要繞路。若日後需要更硬的保護，再考慮在
config 加 `approved_by` 欄位讓未簽名版本不被 sizing 採用。

### 尚未決定

- 賠率該怎麼量化才不會變成另一個「看起來精確的錯誤答案」（隱含上漲空間／下檔風險的
  比值？期望值？），以及它的輸入從哪個 authority 來。
- 合併三軸為「主張可信度」後，各來源類型的 authority 對照要怎麼重寫而不放寬 L8。
- 否決類要不要獨立成 Engine C 的一個欄位（目前 `litigation_and_audit_flags` 已存在，
  但沒有任何軸強制讀它）。

## 7. 下一步的判準

先讓 coverage 分類跑一兩週，看實際 daily brief 裡有多少標的從「零」變成「小注可評估」，
以及那些小注的品質。**若多數變成可評估的標的其實不值得看，問題就不在 gate 而在 pq1
的選題**，屆時重構三類軸也救不了。有實際樣本再決定是否動軸結構。
