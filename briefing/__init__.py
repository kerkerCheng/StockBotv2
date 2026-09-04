"""Daily brief 的組裝層——把各 domain 的 pane 接成一份 brief。

## 為什麼需要一個獨立的 package（B6）

`decision_lab/brief.py` 之所以會長成 1,462 行的全系統儀表板，是因為它同時是
**決策摘要**與**組裝點**。組裝點必須看得到所有層（排序要 Neo4j、NAV 要 Google
Sheet、覆蓋分類要 beta policy），而 Engine D 依定義不得 import 那些——於是每加
一塊 pane 就多一個注入參數，`build_today_brief()` 收到 11 個為止。

把組裝拉出來之後方向就對了：`briefing → {alpha, portfolio, risk, decision_lab,
engine_d_runtime}`，單向、無環。要新增一塊 pane，正確做法是在它自己的 domain 寫
builder＋renderer，然後在這裡接一行。

## 這一層的紀律

**薄殼，不含判斷邏輯。** 這裡不決定任何 attention／blocker／覆蓋分類／排序——
那些各自有 SSOT。這裡只做三件事：取數（`sources.py`）、排順序（`today.py`）、
串 markdown（`render.py`）。任何「if 條件成立就改變語意」的程式碼出現在這裡，
就是 pane 該擁有而沒擁有的東西。
"""
