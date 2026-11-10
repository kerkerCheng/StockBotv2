"""讀圖反證寫「新進」、圖上 develops 這一層的公司卻不在 entities（2026-11-10，failure log #143；使用者「#143 … 照推薦做」）。

CW DFB 層讀圖 `sr_790f15cdae054ce3` 反證①寫「不在現有 14 家之內的新進者首次量產」，entities 只列 11 家既有廠——環宇
（co:gcs_holdings，圖上 develops 這一層）不在其中。語意 watch 靠 entities 比對文件主詞：環宇自己公告量產，①不會醒。

只提醒、不擋：`alpha structure-reading --add` 寫入後印在收據；補不補由寫的人決定（換版代價是騎它的敘事換騎）。
比對字只認「新進」（新進者、新進入者、新進銅箔廠）——「第二家」「新廠」講的是買方的第二來源或既有廠擴產，不是新進者
（L16：不用會誤報的比對）。敘事那一側寫「新進」的反證現行都連到讀圖那一條（`link_source_ref`，watch 是讀圖的），補讀圖就涵蓋。
"""
from __future__ import annotations

import re
from typing import Any, Mapping

ENTRANT_WORD = re.compile(r"新進")


def developers(record: Mapping[str, Any]) -> list[str]:
    """快照裡 develops 這一層的公司（`angles.developers`；同一個角度的 `is_variant_of` 來源是節點、不是公司，不算——
    11-10 全部讀圖快照：develops 23 筆全是 co:*，is_variant_of 10 筆全是 tech:／prod:）。"""
    rows = (record.get("angles") or {}).get("developers") or ()
    return sorted({str(row[0]) for row in rows if len(row) > 1 and row[1] == "develops"})


def entrant_gaps(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """每條寫「新進」的反證 → `{n, missing}`：圖上 develops 這一層、不在那一條 entities 的公司（n＝disproof[] 的順序、從 1 起算）。"""
    devs = developers(record)
    out: list[dict[str, Any]] = []
    for n, entry in enumerate(record.get("disproof") or (), 1):
        if not ENTRANT_WORD.search(str(entry.get("condition") or "")):
            continue
        listed = {str(e) for e in entry.get("entities") or ()}
        missing = [c for c in devs if c not in listed]
        if missing:
            out.append({"n": n, "missing": missing})
    return out


__all__ = ["ENTRANT_WORD", "developers", "entrant_gaps"]
