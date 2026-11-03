"""Sheet／券商代號的寫法正規化——**純函式、零 I/O**（2026-11-03 批次三 D 從 `fetchers/gsheets.py` 搬出）。

搬家的理由：資本硬擋（`risk/hard_caps.py`、`risk/snapshot.py`）也要用同一條規則比對「是不是同一檔」——
成交紀錄遺留 ②（5% 單筆上限的已持有加總按原字串）與 ③（beta 判別不先正規化）都是同一個洞：同一檔的兩種寫法
被當成兩檔。`risk/` 不該為了一個字串規則去 import I/O 層，所以規則住這裡，`fetchers.gsheets.canonical_symbol` 照舊可用
（同一個函式物件）。
"""
from __future__ import annotations

import re

__all__ = ["canonical_symbol"]


def canonical_symbol(symbol: str) -> str:
    """比對同一檔用，照 Sheet 市值公式的規則（公式把它們當同一檔，比對也要）；正規化的方向一律是**公司名冊的寫法**：
    大寫；`TPE:XXXX` 與裸的台股數字代號補成 `XXXX.TW`；日股 `TYO:XXXX` 補成 `XXXX.T`（R2 覆核 2026-09-30：只處理台股時，
    同一檔日股的兩種寫法被當成兩檔——同券商開出重複列、5% 上限少算已持有；同日使用者定案 Sheet 改用名冊寫法，
    這裡跟著以名冊寫法為準，不為 Sheet 另做別名）。"""
    s = symbol.strip().upper()
    if re.fullmatch(r"TPE:[0-9]{4,6}[A-Z]?", s):
        s = s[4:]
    if re.fullmatch(r"TYO:[0-9]+", s):
        return s[4:] + ".T"
    return f"{s}.TW" if re.fullmatch(r"[0-9]{4,6}[A-Z]?", s) else s
