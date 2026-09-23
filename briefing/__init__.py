"""Daily 的組裝層——把各 domain 的 pane 接成一份 brief。

## 為什麼需要一個獨立的 package（B6）

Engine D 的 `brief.py` 之所以曾長成 1,462 行的全系統儀表板，是因為它同時是
**決策摘要**與**組裝點**。組裝點必須看得到所有層（NAV 要 Google Sheet、覆蓋分類要 beta policy），
而 Engine D 依定義不得 import 那些——於是每加一塊 pane 就多一個注入參數。

把組裝拉出來之後方向就對了：`briefing → {alpha, portfolio, risk}`，單向、無環。
要新增一塊 pane，正確做法是在它自己的 domain 寫 builder＋renderer，然後在這裡接一行。

⚠ 2026-09-23（Phase 0 Step 0b.4）：decision brief 的組裝（`today.py`／`public_view.py`／
`render_today_markdown`）隨 decision_lab 研究側退役；`briefing/` 現在只剩 `alpha_view/`（個股頁 read model）、
`analyst_view/`、`sources.py`（備份狀態／outcome aggregate／position events 取數）與 `render.py`（備份計數器）。

## 這一層的紀律

**薄殼，不含判斷邏輯。** 這裡不決定任何 attention／blocker／覆蓋分類——那些各自有 SSOT。
這裡只做取數（`sources.py`）、串 markdown（`render.py`）、以及**組 canonical read model**
（`alpha_view/`，2026-09-05）。任何「if 條件成立就改變語意」的程式碼出現在這裡，就是 pane 該擁有而沒擁有的東西。

## `alpha_view/`：單一公司的 Alpha Investment View

它是 read model 不是 authority：把 Engine A／Engine C／AlphaSignal／Engine D 凍結歷史／
thesis lifecycle **選取、正規化、語意標註（status／basis）、組裝、序列化**成一份
presentation-independent 的 DTO；`python -m briefing alpha-card` 與 Web／API 都消費同一份。
住這裡的理由與 daily brief 相同——它必須同時看得到所有層，而 `alpha/` 不得。詳見 `docs/ARCHITECTURE.md` §6.1。
"""
