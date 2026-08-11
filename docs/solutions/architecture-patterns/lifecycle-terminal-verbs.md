---
title: "終態動詞：叫 terminal 的參數裡有一個值不是 terminal"
date: 2026-08-11
category: docs/solutions/architecture-patterns/
module: engine-d
problem_type: closed_vocabulary_misuse
component: lifecycle
severity: medium
applies_when:
  - 要從封閉字彙挑一個值，而沒有任何一個值精確等於你的意圖
  - 參數名稱對它的所有合法值做了統一斷言（terminal_status、is_deleted、final_state）
  - 操作成功回傳，但症狀延遲出現在別的子系統
  - 這個欄位的值會被下游當成評分／校準輸入
tags:
  - closed-vocabulary
  - lifecycle
  - engine-d
  - decision-store
  - append-only
  - design-smell
---

# 終態動詞：叫 terminal 的參數裡有一個值不是 terminal

## 事發

2026-08-11 合併四個重複的 `co:agility_robotics` Decision cohort。要把三個併入
canonical 的那個，於是找 `decision_lab close` 的 `--terminal-status`，四個合法值：

```
promoted | rejected | expired | revised
```

我選了 `revised`——「這筆被修正、併入別處」讀起來最貼近意圖。三次 close 全部成功回傳
`OutcomeResult(..., terminal_status='revised')`，沒有任何警告。

然後 `todo sync` 把三個編號原封不動地重生成 `[121]/[122]/[123]`。

原因在 `decision_lab/store.py` 的 `close_lifecycle_with_outcome`：

```python
if terminal_status == "revised":
    # INSERT probe_lifecycle_epochs (epoch + 1, status='active')
elif terminal_status in {"promoted", "rejected", "expired"}:
    # 真正終止
```

`revised` 是**刻意**的延續語意，忠實實作 AGENTS.md 的 L7（thesis 生命週期：
`revised` = 修正後的 thesis 成立，**重新進入 `active`** 並更新 disproof 條件）。
`decision_lab/brief.py` 的過濾器也同樣刻意地把它排除在終態之外：

```python
_TERMINAL_LIFECYCLE = frozenset({"promoted", "rejected", "expired"})
# 已終結的 probe 不再是今日待辦（promoted／rejected／expired）。`revised`
# 不算終結——它開新 epoch 且需要 reassess，仍要出現。
```

**程式碼從頭到尾都是對的，而且都有註解說明。是我挑錯了值。**

## 為什麼這個錯特別容易犯

參數叫 `--terminal-status`。這個名字對它的**所有**合法值做了統一斷言：這四個都是終態。
實際上其中一個不是。挑值的人不會為了選一個 enum 去讀 store 的實作——名稱已經
承諾過了。

這跟 [`one-representation-two-meanings.md`](one-representation-two-meanings.md)
不同：那裡是一個表示承載兩種語意、下游被迫二選一。這裡的字彙定義乾淨、下游處理正確，
**混淆發生在呼叫端**——封閉字彙沒有任何一個值精確等於「重複、併入他處」，於是操作者
挑了最近似的那個名字，而它的生命週期效果剛好相反。

## 更危險的那個選項

發現 `revised` 錯了之後，剩下三個候選看起來都能終止。`rejected` 很誘人——「這筆
記錄被否決了」也讀得通。

**不能選。** `close_probe` 組出的 payload 裡有：

```python
"source_calibration_inputs": {
    "source_ids": store.signal_sources_for_cohort(cohort_id),
    "claim_correctness": claim_correctness,
    "market_return_status": market["market_return_status"],
},
```

outcome 會回饋去校準**來源可信度**。標 `rejected` 等於宣告 Agility thesis 已被證偽——
而它只是一筆重複記錄，thesis 從未被檢驗過。用一次資料整併去污染來源評分，錯誤會擴散到
所有共用該 source 的判斷，而且沒有任何症狀提示你這件事發生過。

正確答案是 `expired`：結束，且**未產生定論**。`claim_correctness` 同理填 `unknown`——
CLI 的說明文字本身就寫著「unknown 是合法答案，不要硬猜」。

## 判準

**選終態動詞前先問兩件事：**

1. **這個值會終止 lifecycle，還是延續它？** 不要從名稱推斷。生命週期字彙裡經常混著
   「結束」與「轉換」兩類（`revised`、`superseded`、`migrated` 都是轉換），而參數名
   通常只反映多數。
2. **這個 outcome 會被誰讀？** 若它會餵進評分、校準、歸因或任何後續統計，那麼欄位值
   就不只是一筆狀態紀錄，而是一個**斷言**。挑一個「意思差不多」的值，等於在下游偷偷
   建立一個你沒打算做的主張。第 2 點比第 1 點嚴重：第 1 點會用症狀提醒你，第 2 點不會。

**沒有任何值精確符合意圖時，選「最少斷言」的那個，不要選「最貼近字面」的那個。**
`expired`（沒有定論）比 `rejected`（有定論且為否）安全，即使後者讀起來更像「這筆不要了」。

## 驗證方式的教訓

三次 `revised` 都**成功回傳**。`close` 沒理由報錯——我要求的操作它完全做到了。

**狀態轉移要驗效果，不驗回傳值。** 這次的檢查點是「`sync` 之後那三個編號還在不在」，
而不是「close 有沒有回 OutcomeResult」。後者永遠會過。

修正後的完整驗證鏈：

```
close(expired) → 確認 lifecycle_status 進入 _TERMINAL_LIFECYCLE
              → drop 對應 pq2 編號
              → 再跑一次 sync，確認「新增 0」
```

最後那一步才是真的驗證。AGENTS.md §10.11 記著「使用者已 drop 三輪，全部無效」——
少了這步，前面每一輪看起來都成功了。

## 更正方式

Decision Store 是 append-only，不做破壞性 reset。epoch 1 的 `revised` 留在歷史，
在 epoch 2 補一筆 `expired`，reason 寫明這是對前一次動詞選擇的更正。歷史保留「我當時
判斷錯了」這件事本身，比抹掉它有價值——這也是 outcome 欄位存在的理由。

## 相關

- [`one-representation-two-meanings.md`](one-representation-two-meanings.md)：相鄰但不同的
  形狀（那裡是下游被迫二選一，這裡是呼叫端挑錯值）
- [`closed-vocabulary-registry.md`](closed-vocabulary-registry.md)：這個字彙是 contract
  不是 taxonomy——它刻意有限，缺一個「merged」不是該補的洞，而是要求呼叫端誠實回答
  「這筆到底有沒有定論」
- AGENTS.md 的 L7（thesis 生命週期：`revised` 重新進入 active、disproof 條件要附核查頻率
  與 48h 觸發動作）：`revised` 的延續語意就是從這條來的
- AGENTS.md 的 L11（自己引用的事實要套跟圖裡 claim 同一套追源紀律）：`rejected` 會是
  同型錯誤的加強版——把一個從未檢驗過的 thesis 記成已證偽
