"""跨層共用的中立基礎設施。

## 為什麼需要這個 package

這些模組**有多個消費端，而它們分屬不同層**——把它們留在 `decision_lab/` 會讓
Engine C 為了讀一個字彙表而 import Engine D，形成相依環（實測 2026-09-03：
`engine_c.technical → decision_lab.beta_policy`、
`engine_c.cutover → decision_lab.redaction`）。

判準：**一個模組若被兩個以上不同層的消費端使用，且它本身不擁有任何 authority，
它就屬於 shared。** 擁有 authority 的（Decision Store、圖、Engine C ledger）永遠不進來。
"""
