---
title: "只夠用一次的機制：把一對多當成一對一，然後安靜地偏掉"
date: 2026-09-10
category: docs/solutions/architecture-patterns/
module: cross-engine
problem_type: design_smell
component: data_model
severity: high
applies_when:
  - 一個機制在你當初那個案例上完美運作，第二個案例出現時卻沒有報錯
  - 寫下 `dict[key] = value` 而 key 其實可能重複
  - 某個欄位是「後寫的蓋掉先寫的」，而先寫的沒有第二份備份
  - 一個新加的偵測／報告只在執行當下 print，沒有累積成任何數字
  - 邊有某個機制、點沒有（或反過來），而兩者面對同一種衝突
  - 驗收指標會隨「上一次重載是什麼時候」而改變
---

# 只夠用一次的機制

## 一句話

**「這個機制只處理了我當時手上那個案例」**——它不會壞、不會報錯、測試也不會紅，
只會在遇到第二種形狀時安靜地偏掉，而偏的方向通常固定。

## 為什麼它特別難抓

一般的 bug 會壞。這一類不會：

| 機制 | 當初的案例 | 第二種形狀 | 遇到時發生什麼 |
|---|---|---|---|
| `MERGE_NODE` 的 `SET n.name` | 載入一份新文件 | **重載**既有文件 | name 被靜默改寫，沒有警告 |
| `doc_id → extractions/<doc_id>.json` | 系統產生的檔案（檔名==doc_id） | 人工 addendum（檔名≠doc_id、且一對多） | 「找不到抽取檔」——但它存在 |
| `_extraction_index` 用 `dict[str, Path]` | 一個 doc_id 一份檔案 | 21 組共用 doc_id | 後掃到的覆蓋先掃到的，**少一段 provenance** |
| `edge_resolution` 衝突解決 | 邊的屬性衝突 | 節點的屬性衝突 | 節點那邊沒有機制，衝突無聲落地 |
| `unregistered_entity_ids` 報告 | 人在旁邊看著跑 | 無人值守排程 | print 到 stderr，沒有人讀 |
| publisher 的「一筆 RA 一個 commit」 | publisher 自己建的 commit | 別人順手 commit 了那些檔案 | 空 staged → 整批中止 |

六個全部來自 2026-09-10 一個 session。**沒有一個會讓測試變紅。**

## 判準：三個問句

動一個機制之前問：

1. **這個 key 真的唯一嗎？** 寫下 `dict[k] = v` 之前，先問「k 會不會重複」。
   實測值比直覺可靠：全庫 229 份抽取檔只有 206 個 doc_id。
2. **這個欄位是「覆蓋」還是「聯集」？** 覆蓋掉的那一份有沒有第二個地方留著？
   （`MERGE_NODE` 只有 `source_ids` 聯集，`name`／`attributes` 是覆蓋。）
3. **這個機制的對稱面做了嗎？** 邊做了，點呢？寫入做了，讀取呢？
   偵測做了，誰消費？

## 修法的順序

**先量測第二種形狀有幾筆，再決定要不要修。** 這一類問題的誘惑是「順手全部泛化」，
但泛化本身也可能是過度工程（L16-4）。三個檔次：

- **一行到十行、不動 contract** → 當下修掉，不進 backlog。放著的成本高於修的成本，
  因為它不會壞，所以永遠不會有人被它逼著回來修。
- **動到 contract、封閉字彙或多個 owner** → 走 development-flow 的 Z2，先給 proposal。
- **等於重寫一個既有子系統**（例：為節點屬性做一套 `edge_resolution` 等價物）
  → 進 ROADMAP 排程，不當下做。

## 反例：什麼時候不該泛化

`coverage_gaps` 的 🔴 桶曾被提議「再往下分成層與實體兩類」。逐節點查證後，
五個 🔴 在 `source_ids`、`abstraction_level`、ABOUT 文件數上**完全同形**——
沒有可機械分辨的差異。在沒有事實支撐的地方切一刀，得到的是會誤報的分類。
**「不夠 general」的相反不是「盡量 general」，是「general 到資料支持的那一格為止」。**

## 相關

- [`one-representation-two-meanings.md`](one-representation-two-meanings.md)：
  一個表示承載兩種語意。本篇是它的近親——差別在那篇是**一個值被迫代表兩件事**，
  本篇是**一個機制只認得一種形狀**。
- `AGENTS.md` L13：驗收是「產出出現在下游消費者手上」，不是「這一步回傳成功」。
- `AGENTS.md` L14：真正的防呆是會自己出現的常駐計數器，不是要人讀的段落。
