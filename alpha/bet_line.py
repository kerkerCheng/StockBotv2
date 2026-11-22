"""賭注句與對帳日曆的導出（A0，2026-11-22；`docs/brainstorms/2026-11-22-a0-bet-line-proposal.md`）。

一檔一句四格：押什麼｜翻倍要哪個營業數字｜下一個對帳日｜認錯看哪一條。寫的人只寫故事紀錄的 `bet`
（押什麼、翻倍要、認錯看第幾條——寫入規則在 `alpha.narrative.story.bet_problems`）；押哪一層照抄敘事的 `rides[]`，
下一個對帳日與認錯那一條的 watch **每次物化重算**——日子過了自己跳到下一個，不存進任何檔。

這是研究判斷（A3）的呈現：不 gate、不改候選狀態、不排序、不給尺寸；`doubling` 的三種只是標籤，不進任何排序鍵。
句子在這裡組好、畫面照印（前端有部位用語的全檔禁字檢查，這一類字不住前端）。
純函式、不做 I/O：輸入由 `alpha.providers.candidates.derive_row` 給。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Mapping, Sequence

from alpha.candidates import ADDON_GROUPS
from alpha.narrative.story import DOUBLING_KIND_LABELS, doubling_kind

#: 欠賭注句的組：可開與已持有——與「加碼條件還沒查」同一個範圍（`alpha.candidates.ADDON_GROUPS`）。缺 X／不要的檔
#: 寫了照印，沒寫不算欠。
BET_GROUPS: tuple[str, ...] = ADDON_GROUPS

#: 賭注句寫了沒（封閉字彙；`engine_b.todo_ledger.COVERAGE` 逐一登記去處）。
BET_LINE_STATES: Mapping[str, str] = {
    "written": "寫了",
    "not_written": "還沒寫賭注句",
    "stale": "賭注句過期了：敘事換版，照新的一版重寫",
    "no_narrative": "還沒寫賭注句：先要有敘事",
}

#: 對帳日曆每一列的種類（封閉字彙，也是同一天裡的列序）。前兩種是「哪一份文件出來」；後兩種是等待自己的到期
#: ——到期是「到時候重問」，不是哪一份文件。
CHECK_KINDS: Mapping[str, str] = {
    "when_slot": "何時格寫的日子",
    "checkpoint_registry": "名冊檢核點",
    "disproof_expiry": "反證到期",
    "confirm_expiry": "加碼條件到期",
}
#: 下一個對帳日只從這兩種取（使用者 2026-11-22 定 2B）：可開那一批最近的到期日全在一季以後，拿它當對帳日等於沒有。
NEXT_CHECK_KINDS: tuple[str, ...] = ("when_slot", "checkpoint_registry")

NO_CHECK_DAY = "下一個對帳日：沒有——何時格沒有寫得出是哪一天的日子，名冊也沒有今天以後的檢核點"


def _day(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def check_calendar(*, today: date, when_days: Iterable[Mapping[str, Any]] = (),
                   registry_days: Iterable[Mapping[str, Any]] = (),
                   disproof: Iterable[Mapping[str, Any]] = (),
                   confirm: Iterable[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """這一檔**今天以後**的對帳日：照日期、同一天照種類（`CHECK_KINDS` 的順序）——時間序不是名次。每列帶那一句原文或
    那一條條件（L18：指得回寫的人寫的字）。同一天、同一種、同一句只留一列。

    `when_days`：`alpha.narrative.checkpoints.reckoning_days` 的 `{date, sentence, yearless}`；
    `registry_days`：名冊上這一檔的檢核點 `{date, what}`；
    `disproof`：`engine_b.disproof.disproof_pointers` 的列（到期日＝盯它的 watch 的，沒有 watch 退回敘事自己寫的）；
    `confirm`：`engine_b.disproof.confirm_rows` 的列（已收掉的不列）。"""
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}

    def put(day: Any, kind: str, text: Any, **extra: Any) -> None:
        d = _day(day)
        if d is None or d < today:
            return
        text = str(text or "").strip()
        rows.setdefault((d.isoformat(), kind, text),
                        {"date": d.isoformat(), "kind": kind, "kind_label": CHECK_KINDS[kind], "text": text, **extra})

    for item in when_days:
        put(item.get("date"), "when_slot", item.get("sentence"), yearless=bool(item.get("yearless")))
    for item in registry_days:
        put(item.get("date"), "checkpoint_registry", item.get("what") or "名冊沒寫是哪一件")
    for item in disproof:
        put(item.get("expires"), "disproof_expiry", item.get("condition"), watch_id=item.get("watch_id"),
            n=item.get("n"))
    for item in confirm:
        if item.get("state") != "closed":
            put(item.get("until"), "confirm_expiry", item.get("condition"), watch_id=item.get("watch_id"),
                n=item.get("index"))
    order = {kind: i for i, kind in enumerate(CHECK_KINDS)}
    return sorted(rows.values(), key=lambda r: (r["date"], order[r["kind"]], r["text"]))


def next_check(calendar: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """下一個對帳日：日曆裡最早的那一列「何時格寫的日子」或「名冊檢核點」（同一天取何時格——它帶著寫的人的原句）。
    兩種都沒有 → None（⑤「沒有對帳日」數它）。"""
    for row in calendar:
        if row.get("kind") in NEXT_CHECK_KINDS:
            return {"date": row["date"], "sentence": row.get("text") or "", "source": row["kind"],
                    "source_label": row.get("kind_label") or CHECK_KINDS[row["kind"]],
                    "yearless": bool(row.get("yearless"))}
    return None


def next_check_line(found: Mapping[str, Any] | None) -> str:
    if found is None:
        return NO_CHECK_DAY
    guess = "；年份是照寫下那天推的" if found.get("yearless") else ""
    return f"下一個對帳日：{found['date']}｜「{found['sentence']}」（{found['source_label']}{guess}）"


def _stake_line(rides: Sequence[Mapping[str, Any]], stake: str) -> str:
    where = "、".join(f"{r['label']}（{r['unit_label']}）" if r.get("unit_label") else str(r["label"]) for r in rides)
    return f"押：{where}——{stake}" if where else f"押：{stake}（這一版敘事沒宣告押哪一層）"


def _doubling_line(doubling: Mapping[str, Any]) -> str:
    tail = f"（{DOUBLING_KIND_LABELS['vague']}）" if doubling["kind"] == "vague" else ""
    return f"翻倍要：{doubling['text']}{tail}"


def _disproof_line(n: Any, pointer: Mapping[str, Any] | None) -> str:
    if pointer is None:
        return f"認錯看：第 {n} 條——這一版敘事沒有這一條"
    if pointer.get("watch_id"):
        state = "" if pointer.get("state") == "active" else f"；{pointer.get('state_label')}"
        tail = f"（{pointer['watch_id']}，{pointer.get('expires') or '沒寫到期日'} 到期{state}）"
    else:
        tail = f"（未盯；敘事寫的到期日 {pointer.get('expires') or '沒寫'}）"
    return f"認錯看：第 {pointer['n']} 條——{pointer['condition']}{tail}"


def bet_line(*, bet: Mapping[str, Any] | None, has_narrative: bool, earlier_bet: bool, owed: bool,
             rides: Sequence[Mapping[str, Any]], pointers: Sequence[Mapping[str, Any]],
             calendar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """候選列的 `bet_line`。`bet`：這一版敘事現行故事的 `bet`（沒寫＝None）；`has_narrative`：有現行 v2 敘事；
    `earlier_bet`：這一檔更早的敘事版本寫過賭注句（→ 過期，不是從沒寫）；`owed`：落在 `BET_GROUPS`。
    `rides`：`{node, label, unit_label}`（照抄敘事的 `rides[]`，中文名由呼叫端給）；`pointers`：
    `engine_b.disproof.disproof_pointers`；`calendar`：`check_calendar` 的結果。

    `lines`：畫面照印的那幾句——寫了＝四句；沒寫而且欠＝「還沒寫賭注句」＋下一個對帳日（它不靠寫的人，照樣算得出）；
    沒寫也不欠＝空（那一塊不印）。"""
    state = ("written" if bet else "no_narrative" if not has_narrative
             else "stale" if earlier_bet else "not_written")
    found = next_check(calendar)
    out: dict[str, Any] = {
        "state": state, "state_label": BET_LINE_STATES[state], "owed": bool(owed),
        "rides": [{"node": r.get("node"), "label": r.get("label") or r.get("node"), "unit_label": r.get("unit_label")}
                  for r in rides],
        "stake": None, "doubling": None, "next_check": found, "disproof": None, "lines": [],
    }
    if bet:
        kind = doubling_kind(bet.get("doubling"))
        n = bet.get("disproof")
        pointer = next((p for p in pointers if p.get("n") == n), None)
        out["stake"] = str(bet.get("stake") or "")
        out["doubling"] = {"text": str(bet.get("doubling") or ""), "kind": kind, "kind_label": DOUBLING_KIND_LABELS[kind]}
        out["disproof"] = ({"n": pointer["n"], "condition": pointer.get("condition"), "watch_id": pointer.get("watch_id"),
                            "expires": pointer.get("expires"), "state": pointer.get("state"),
                            "state_label": pointer.get("state_label")} if pointer is not None
                           else {"n": n, "condition": None, "watch_id": None, "expires": None, "state": None,
                                 "state_label": None})
        out["lines"] = [_stake_line(out["rides"], out["stake"]), _doubling_line(out["doubling"]),
                        next_check_line(found), _disproof_line(n, pointer)]
    elif owed:
        out["lines"] = [BET_LINE_STATES[state]] + ([next_check_line(found)] if has_narrative else [])
    return out


# ---------------------------------------------------------------------------
# 計數（⑤ 待做清單與候選板共用這一份，L16）。順序照組、組內照板（ticker 字母），不是名次。
# ---------------------------------------------------------------------------

def _owed(groups: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[Mapping[str, Any]]:
    return [r for g in BET_GROUPS for r in groups.get(g) or ()]


def bet_gap_rows(groups: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[Mapping[str, Any]]:
    """可開與已持有裡還沒有賭注句的列（從沒寫、敘事換版過期、沒有敘事）。"""
    return [r for r in _owed(groups) if (r.get("bet_line") or {}).get("state") != "written"]


def doubling_rows(groups: Mapping[str, Sequence[Mapping[str, Any]]], kind: str) -> list[Mapping[str, Any]]:
    """可開與已持有裡、賭注句寫了而且翻倍條件是 `kind`（`number｜unmeasurable｜vague`）的列。待做格只數 `vague`——
    「無法量：缺 X」是合法的寫法，另印成現況、不逼人補（提案 §7：否則會為了歸零硬掰數字）。"""
    return [r for r in _owed(groups)
            if (r.get("bet_line") or {}).get("state") == "written"
            and ((r["bet_line"].get("doubling") or {}).get("kind") == kind)]


def no_check_day_rows(groups: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[Mapping[str, Any]]:
    """可開與已持有裡、有 v2 敘事卻帶不出下一個對帳日的列（沒有敘事的那幾檔已經在「賭注句還沒寫」裡，不重複數）。"""
    return [r for r in _owed(groups)
            if (r.get("bet_line") or {}).get("state") != "no_narrative" and (r.get("bet_line") or {}).get("next_check") is None]


__all__ = ["BET_GROUPS", "BET_LINE_STATES", "CHECK_KINDS", "NEXT_CHECK_KINDS", "NO_CHECK_DAY", "bet_gap_rows",
           "bet_line", "check_calendar", "doubling_rows", "next_check", "next_check_line", "no_check_day_rows"]
