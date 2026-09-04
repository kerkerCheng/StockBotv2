"""Engine D — Decision & Accountability Engine application boundary。"""

from .brief import build_decision_brief
from .store import DecisionStore
from .workflow import (
    EvaluationRequest,
    ensure_shadow_for_company,
    evaluate_signal,
    reassess,
)

# ⚠ `build_today_brief` 自 B6 起住 `briefing.today`——它是**組裝**函式，要看得到
# alpha／portfolio 兩層，而 Engine D 依定義不得 import 它們。這裡只留決策 pane。
__all__ = [
    "DecisionStore",
    "EvaluationRequest",
    "build_decision_brief",
    "ensure_shadow_for_company",
    "evaluate_signal",
    "reassess",
]
