"""Lane memo 的兩個機械規則——產生器（`thesis/generate_lane_memo.py`）與反證對帳（`engine_b/disproof.py`）共用。

1. **`memo_text_sha256`**：sidecar 的 `memo_sha256` 是對**LF 文字**算的；本機 `core.autocrlf=true`，
   working tree 的 memo 是 CRLF，直接 hash 檔案位元組會恆不符（P0 第 3 輪 R3-3）。算法寫死在這裡：
   讀成文字、CRLF→LF、`sha256(text.encode("utf-8"))`。兩邊呼叫同一個函式——不各寫一份。
2. **`disproof_items`**：memo 的反證條目＝標題含「推翻」的那一節、到下一個**任何層級**標題為止、
   以 `- ` 或 `1. ` 開頭的行。三份現行 memo 的格式不一（AXT §7 用 `-` 後接 `### 7b`；COHR §6 用 `-`；
   Sivers §6 用 `1.`），所以不看編號、只看標題與行首。**縮排的續行併入前一條**（AXT §7 第 2 條跨兩行；
   只取第一行會把條件截在「→ 「防禦性鎖客」」——Phase 1 Step 1.6 實測）；中日文直接接、其餘補一個空格；空行結束一條。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

_ITEM = re.compile(r"^(?:- |\d+\. )(?P<text>.+)$")
_CJK = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uff00-\uffef]")


def _join(head: str, tail: str) -> str:
    if _CJK.match(tail[:1]) or _CJK.match(head[-1:]):
        return head + tail
    return f"{head} {tail}"


def normalize_newlines(text: str) -> str:
    return str(text).replace("\r\n", "\n").replace("\r", "\n")


def memo_text_sha256(text: str) -> str:
    return hashlib.sha256(normalize_newlines(text).encode("utf-8")).hexdigest()


def memo_file_sha256(path: Path | str) -> str:
    return memo_text_sha256(Path(path).read_text(encoding="utf-8"))


def disproof_items(text: str) -> list[str]:
    """「推翻」那一節的條目文字（去掉行首的 `- `／`1. `）。沒有那一節回空 list。"""
    lines = normalize_newlines(text).split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith("#") and "推翻" in line), None)
    if start is None:
        return []
    items: list[str] = []
    open_item = False
    for line in lines[start + 1:]:
        if line.startswith("#"):
            break
        match = _ITEM.match(line)
        if match:
            items.append(match["text"].strip())
            open_item = True
        elif open_item and line[:1] in (" ", "\t") and line.strip():
            items[-1] = _join(items[-1], line.strip())
        else:
            open_item = False
    return items


__all__ = ["disproof_items", "memo_file_sha256", "memo_text_sha256", "normalize_newlines"]
