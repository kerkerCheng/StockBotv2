"""一個 Research Action 的 focus company 是誰——**prepare 與 todo sync 共用的唯一判定**（2026-10-08，Phase 7 failure log #3）。

獨立成一個模組：`intake.actions` 會被測試換成假模組（只給 `iter_actions`），判定若住在那裡，sync 的 collector 一 import 就斷；
而且判定只依賴兩個字串，不依賴 RA store。
"""
from __future__ import annotations

from typing import Iterable


def resolve_focus(declared: str | None, lead_focuses: Iterable[str] = ()) -> tuple[str | None, str | None]:
    """回 `(focus, blocker)`。

    RA 自己宣告的（`payload.focus_company_id`）優先；綁定 lead 的 `refs.focus_company_id` 只當一致性檢查——
    兩邊都說話卻說得不一樣、或沒有唯一的 focus，回 blocker（不猜，交還人工）。
    事發：prepare 不擋缺 focus、sync 才擋——同一個必填欄兩處判，第一處放行、第二處拒收，[687] 只能請使用者 drop。
    prepare 時還沒有綁定的 lead（`lead_focuses` 空），所以 prepare 等於要求 RA 自己宣告。
    """
    declared = str(declared or "").strip() or None
    focuses = sorted({str(f).strip() for f in lead_focuses if str(f).strip()})
    if declared and focuses and set(focuses) != {declared}:
        return None, (f"BLOCKER：RA 自報 focus_company_id={declared}，綁定 lead 卻是 "
                      f"{'、'.join(focuses)}；先回 pq1 對齊，不得先 apply。")
    if declared:
        return declared, None
    if len(focuses) == 1:
        return focuses[0], None
    if focuses:
        return None, ("BLOCKER：Research Action 有多個 focus_company_id："
                      f"{', '.join(focuses)}；先回 pq1 拆成明確 focus company。")
    return None, "BLOCKER：Research Action 尚未聲明唯一 focus_company_id；先回 pq1 補 focus company，不得先 apply。"


__all__ = ["resolve_focus"]
