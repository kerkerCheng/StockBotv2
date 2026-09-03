"""Alpha Research Core 的例外階層。

⚠ `PointInTimeUnsupported` 不是「還沒實作」的佔位，它是一道**保險絲**：
provider 在不支援 as-of 時**必須拋它**，不得靜默回傳當前資料。
依據是 L13——最危險的形狀是成功與失敗在同一個訊號上同形；
「回傳了資料」若同時代表「as-of 生效」與「as-of 被忽略」，回測就會靜默地看到未來。
"""
from __future__ import annotations


class AlphaError(Exception):
    """Alpha Research Core 的例外基底。"""


class ContractViolation(AlphaError, ValueError):
    """契約欄位不合法——缺必填、型別錯、或違反 domain invariant。"""


class PointInTimeUnsupported(AlphaError, NotImplementedError):
    """該 provider 無法回答「T 時刻我知道什麼」。

    ⚠ **不得以回傳當前資料代替**（INV-6）。呼叫端若收到這個例外，正確處置是
    降級為「不做 as-of 研究」並記錄原因，不是假裝拿到了歷史視角。
    """


class IdentityError(AlphaError, ValueError):
    """identifier 型別不合法，或被當成另一種 identifier 使用（INV-1）。"""
