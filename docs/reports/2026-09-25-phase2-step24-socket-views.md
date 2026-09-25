---
date: 2026-09-25
topic: phase2-step24-socket-views
plan: docs/plans/2026-09-25-001-feat-phase2-reading-units-graph-walk-plan.md
step: 2.4
---

# Phase 2 Step 2.4 — 三個產品的插槽視角（工具驗收輸出）

**用途：**plan §5 驗收「三個產品的插槽視角輸出存進報告」；也是 Step 2.5（強模型寫第一份插槽讀圖）的起點。
本檔數的是**讀圖工具的輸出與圖上事實**，不是研究結論；判讀留給 2.5。

- 產生時間：2026-09-25 13:17（台北）；HEAD＝Step 2.3 `cb6c612` ＋ 本 Step 未提交的改動
- 命令：`python -m query.structure <prod:…> --unit socket [--quotes] [--json]`

## 1. 總表

| 產品 | 四個角度（需求／供給／下一層／反向） | 需求錨 | 供給側（合格狀態｜證據｜sub） | 製造者段 | 客戶端原文段 |
|---|---|---|---|---|---|
| `prod:supernova` | 1／1／0／0 | 🔴 走不到 | `co:sivers_semiconductors`（designed_in｜needs_review｜—） | ⚠ 分不出製造者還是零件供應商 | ⚠ 沒有；現有來源只有 `silicon_matter_sivers_ayar_2026_03_14`（tier 3｜silicon_matter_substack｜**解析不到**） |
| `prod:els_8ch_module` | 1／3／1／0 | ✅ tech:ai_switch → tech:cpo → 本節點 | `co:sivers_semiconductors`（designed_in｜externally_corroborated｜—）、`co:enablence_technologies`（designed_in｜self_reported｜—）、`co:o_net_technologies`（—｜externally_corroborated｜—） | ⚠ 分不出 | ⚠ 沒有；唯一來源 `enablence_sivers_onet_ofc_pr_2026_03_17`（tier 2｜Enablence Technologies）——Enablence 本身在供給側 |
| `prod:ph18da` | 1／1／0／0 | 🔴 走不到 | `co:tower_semiconductor`（—｜externally_corroborated｜4） | ⚠ 分不出 | ✅ `openlight_ph18da_volume_orders_pr_2026_03`（tier 2｜OpenLight → `co:openlight`）：«announced the first-ever volume production orders by a customer on its PH18DA … developed in collaboration with Tower Semiconductor» |

三個產品**都沒有**任何 `develops`／`deploys` 邊進來（圖上共 51＋9 條這兩種邊，沒有一條指向這三個）——與 plan §0.2「有 `supplies_to` 進來的 13 個產品中 10 個沒有 develops／deploys」一致；工具在三個上都明示缺席，沒有印空白。

## 2. 指紋與分級（驗收）

- 全圖 278 個節點的 `result_digest` 對 Step 2.2 之後重算：**變動 0**（插槽附加段不進 digest；`scratchpad/digest_compare.py`）。
- `tech:cw_dfb_laser` 現行讀圖 `--check`：仍 **current**（L11-6 ④：它若變 stale，就是附加段漏進 digest）。
- 分級：插槽讀圖遇到供給側 `evidence` 變動＝`supply_evidence`（high）→ `stale`；層讀圖同樣的變動仍是 `evidence`（low）→ `stale_low`（`tests/test_structure_reading_v3.py`）。

## 3. 工具在這三格上顯示了什麼（給 2.5 的觀察，不是結論）

1. **SuperNova（決定紀錄 §4.3 點名的插槽）**：唯一原文是一篇 tier 3 substack、origin 解析不到——依 A2，這一格現在**不能**寫成護城河
   （寫入端會以「independent 解析不到」拒收），預期是 `undecided`；缺的格子工具都印出來了：客戶端一手原文、Ayar 對它的 `develops` 邊、需求錨鏈。
2. **ELS 8ch module 是 R-4 兩義的活樣本**：原文逐字是「O-Net Technologies will serve as the OEM partner, integrating Sivers Semiconductors'
   laser arrays and Enablence's NxN Star Coupler」——讀起來 O-Net 是整合者、Sivers 與 Enablence 是零件供應商，但圖上三家都是 `supplies_to`。
   ⚠ 工具的「客戶端原文」規則（plan §5：origin 解析得到、且**不是任何一家供應商**）因此把 Enablence 的新聞稿排除——從 Sivers 那條邊看，
   Enablence 是第三方（`classify_evidence` 也給外部印證），但在這個插槽上它同時是供應商。**這是 plan 規則的字面結果，不是 bug**；
   「同插槽的另一家零件供應商算不算客戶端或第三方」要不要放寬，由 2.5 看完後決定是否提 plan 修改（L8 的精神是「不是那家供應商自己」）。
3. **PH18DA**：OpenLight 的一手新聞稿被正確認成客戶端原文；但「developed in collaboration with Tower」讀起來 OpenLight 才是平台（產品）的主人、
   Tower 是代工——同樣是 `supplies_to` 承載「製造者」的例子，工具照規則印了「分不出製造者」。

## 4. 附：SuperNova 的完整輸出（`--unit socket --quotes`）

```text
## 需求側：誰需要它、繞不繞得過（1 條）
| `prod:teraphy_chiplet` depends_on `prod:supernova` | — | — | — | needs_review | 1 |
|  «Together, they have shown multi-wavelength optical light sources (i.e. laser arrays) integrated in Ayar Labs' SuperNova™ light source
   module that feeds the TeraPHY™ optical engine»  `silicon_matter_sivers_ayar_2026_03_14`（tier 3｜silicon_matter_substack）
## 供給側：誰供它、有沒有人獨佔（1 條）
**sub 分布：（都沒填）｜另有 1 條未填**
| `co:sivers_semiconductors` supplies_to `prod:supernova` | — | — | designed_in | needs_review | 1 |
|  （同一段逐字、同一份來源）
## 下一層（0 條）／反向路徑（0 條）
## 需求錨：🔴 走不到任何已登記的需求錨
## 插槽：這是誰的產品（不進 digest）
⚠ 圖上分不出這個產品是誰的：`supplies_to` 可能是製造者自己，也可能是零件供應商（L12，見 plan R-4）
## 插槽：客戶端或可解析第三方的原文（不進 digest）
⚠ 沒有任何客戶端或可解析第三方的一手原文——現有來源：`silicon_matter_sivers_ayar_2026_03_14`（tier 3｜silicon_matter_substack｜解析不到）
```

ELS 8ch module 與 PH18DA 的完整輸出由同一條命令重跑即得（逐字見 §1、§3 引用）。

## 5. R2-b 之後的修正（2026-09-25）

R2-b（CONDITIONAL_GO）B1：製造者段原本把 `deploys` 也當製造者。`deploys` 的字彙定義是部署方（營運者／客戶），所以改成**只認 `develops`**、
`deploys` 另列「部署方（客戶，不是製造者）」。真實樣本 `prod:vera_verarubin`：修正前印六家雲端「製造者」且沒有缺席警告；修正後印「分不出製造者」
＋部署方 `co:coreweave`、`co:google`、`co:microsoft`、`co:nebius`、`co:oracle`、`co:spacexai`。本報告 §1 的三個產品不受影響（三個都沒有 develops／deploys 邊）。
