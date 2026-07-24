"""Daily brief 批次核准語法 parser（plan U4/R5）。

把 `1 3 7 go 4 drop 5 6 pending` 解析成 {verb: [編號]}，讓 daily-brief skill 的
dispatch 有 deterministic 依據（不靠 agent 自由心證解析數字）。純函式、無 engine
耦合——number→item 的對映由 skill 在該次 brief 的上下文持有。

verbs（封閉集合）：go／drop／pending／skip。type-aware dispatch（go 對 lead＝
研究、對 prepared action＝apply、對到期 thesis＝reassess…）由 skill 決定。
"""
from __future__ import annotations

import re

VERBS = ("go", "drop", "pending", "skip")

_TOKEN = re.compile(r"[,\s]+")


def parse_batch_reply(text: str) -> dict[str, list[int]]:
    """回 {verb: sorted unique 編號}。累積的數字遇到 verb 就歸給該 verb。

    容錯：逗號/空白皆分隔；未知 token 略過但**不**清掉已累積的數字（等下一個
    verb）；同 verb 多次出現會合併。空輸入或無任何 (數字→verb) 配對回空 dict。
    """
    result: dict[str, set[int]] = {v: set() for v in VERBS}
    pending: list[int] = []
    for token in _TOKEN.split((text or "").strip().lower()):
        if not token:
            continue
        if token.isdigit():
            pending.append(int(token))
        elif token in VERBS:
            result[token].update(pending)
            pending = []
        # 未知 token（動詞打錯等）：略過，保留已累積數字給下一個合法 verb
    return {v: sorted(nums) for v, nums in result.items() if nums}
