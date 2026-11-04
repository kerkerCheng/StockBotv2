"""深挖清單（2026-10-31 使用者「都做」；failure log #119；ROADMAP「宣告可開前的深挖清單」）——**純規則，不讀不寫任何檔**。

## 它解什麼

可開最容易出現在研究最淺的地方：SLNG 的可開來自新鏈入圖隔天寫的第一版讀圖，讀圖自己列的缺格（單價有沒有溢價）正好是「量」的
核心前提；深讀後層改判不出、可開變缺 X。研究越淺，找到的反證越少——所以這十項要有人查。

## 2026-11-03 起：加碼的門，不是起始的門（盲點修法第 18＋16 條；AGENTS「讀到邊是加碼的門、不是起始的門」）

決定紀錄 §10.1 條 2 作答 (a)：十項對邊緣小公司天生答不齊——拿它擋可開，可開自 10-02 起每天都是 0。可開改由起始門決定
（`alpha.providers.candidates.open_preconditions`）；這份清單搬去當**加碼條件**，寫法四種：

- 引用（開頭是 `CITATION_PREFIXES` 之一：`library/raw/…`、`sr_…`、網址……）＝查過、答案在那份文件裡；
- 「不適用：理由」＝這一項對這一檔不成立（沒有法說的小公司不該永遠卡在缺）；
- 「加碼條件：c<n>」＝查過、現有文件答不了——寫成這一版 `confirm[]` 第 n 條（各自鑄 watch，新文件對上就醒）；
- 「缺：…」＝還沒查。

清單**存進敘事**（`InvestorBrief.depth_check`；只在有寫時進 id，之前的紀錄 id 不變）。可開或已持有的檔還有沒查的項目，
⑤ 待做清單「加碼條件還沒查」就數它：watch 只會被**新**文件叫醒，答案若在已經存在的年報、法說裡不會自己醒——要有一格叫研究
session 去查，不靠使用者自主。

項目是封閉清單：AGENTS「出投資建議前必看五項」＋最新定期報告與法說＋讀到邊（2026-10-06）＋所押讀圖的核心前提（L8）。
"""
from __future__ import annotations

import re
from typing import Any, Mapping

#: (鍵, 印給人看的名字)。新增一項＝改清單，不是加一個字串。
DEPTH_CHECK_ITEMS: tuple[tuple[str, str], ...] = (
    ("latest_report", "最新一份定期報告（季報／年報）"),
    ("latest_call", "最新一場法說或股東會的逐字"),
    ("customer_concentration", "客戶集中度"),
    ("margin_utilization", "毛利率／產能利用率"),
    ("backlog_mix", "backlog／營收結構"),
    ("dilution", "稀釋"),
    ("valuation_pressure", "估值壓力"),
    ("why_chosen", "讀到邊：客戶為什麼選它的變體"),
    ("replaced_by", "讀到邊：什麼會讓它被換掉"),
    ("core_premise", "所押讀圖的核心前提有供應商自述以外的證據（L8）"),
)
DEPTH_CHECK_KEYS: tuple[str, ...] = tuple(k for k, _ in DEPTH_CHECK_ITEMS)
#: 一項的三種前綴（第四種寫法＝引用，見下）。
NOT_APPLICABLE_PREFIX = "不適用："
ADDON_PREFIX = "加碼條件："
UNCHECKED_PREFIX = "缺"
#: 「引用」這一種寫法的開頭——敘事 evidence_refs 實際用的那幾種（一手節錄、私人節錄、讀圖 id、圖、Engine C、alpha 推導、
#: thesis memo、網址）。四種寫法都不是的字（「待查」「看過了」）不算查過、寫入端拒收（2026-11-04 R2：原本任何不以「缺」
#: 開頭的字都算查過，寫「待查」就能把 ⑤「加碼條件還沒查」歸零——L18：標籤要指得回證據；L16：同義詞也拒收）。
CITATION_PREFIXES: tuple[str, ...] = ("library/raw/", "library/private/", "sr_", "graph:", "engine_c:", "alpha://",
                                      "thesis/", "https://", "http://")
_ADDON_REF = re.compile(r"^加碼條件：c([1-9][0-9]*)(?![0-9])")


def addon_index(value: Any) -> int | None:
    """「加碼條件：c<n>」→ n（1 起算，指這一版 `confirm[]` 第 n 條）；不是這種寫法回 None。"""
    match = _ADDON_REF.match(str(value or "").strip())
    return int(match.group(1)) if match else None


def value_form(value: Any) -> str | None:
    """一項的寫法：`cite`（引用）｜`not_applicable`｜`addon`｜`unchecked`；四種都不是（空的、非字串、「不適用：」沒理由、
    「加碼條件：」後面不是 c<n>、不認得的字）回 None。「查過」與寫入端的形狀檢查共用這一個判斷（L16）。"""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.startswith(UNCHECKED_PREFIX):
        return "unchecked"
    if text.startswith(NOT_APPLICABLE_PREFIX):
        return "not_applicable" if text[len(NOT_APPLICABLE_PREFIX):].strip() else None
    if text.startswith(ADDON_PREFIX):
        return "addon" if addon_index(text) is not None else None
    return "cite" if text.startswith(CITATION_PREFIXES) else None


def is_checked(value: Any) -> bool:
    """查過＝引用（開頭是 `CITATION_PREFIXES` 之一）、「不適用：理由」、「加碼條件：c<n>」；「缺…」、空的、四種都不是的都不算。"""
    return value_form(value) in ("cite", "not_applicable", "addon")


def unchecked_items(depth_check: Mapping[str, Any] | None) -> list[str]:
    """還沒查的項目名（沒寫的鍵、寫「缺…」的鍵），照清單順序——⑤「加碼條件還沒查」與 CLI 共用這一份（L16）。"""
    given = dict(depth_check) if isinstance(depth_check, Mapping) else {}
    return [label for key, label in DEPTH_CHECK_ITEMS if not is_checked(given.get(key))]


def depth_check_problems(depth_check: Any, *, confirm_count: int) -> list[str]:
    """寫在紀錄上就違規的（契約層用，舊紀錄沒有這一欄＝沒有問題）：不認得的鍵、不是非空字串、「加碼條件：」後面不是
    c<n>、c<n> 指不到這一版的 confirm[]、「不適用：」沒寫理由。"""
    if depth_check is None:
        return []
    if not isinstance(depth_check, Mapping):
        return ["depth_check 必須是 {鍵: 寫法} 的物件（鍵見 alpha.narrative.depth_check）"]
    problems: list[str] = []
    unknown = sorted(str(k) for k in depth_check if k not in DEPTH_CHECK_KEYS)
    if unknown:
        problems.append(f"depth_check 有不認得的鍵：{unknown}（鍵見 alpha.narrative.depth_check）")
    for key in DEPTH_CHECK_KEYS:
        if key not in depth_check:
            continue
        value = depth_check[key]
        if not isinstance(value, str) or not value.strip():
            problems.append(f"depth_check.{key} 必須是非空字串（引用｜不適用：理由｜加碼條件：c<n>｜缺：…）")
            continue
        text = value.strip()
        if text.startswith(ADDON_PREFIX):
            n = addon_index(text)
            if n is None:
                problems.append(f"depth_check.{key}：「加碼條件：」後面要接 c<n>（這一版 confirm[] 第幾條）——"
                                f"收到 {text[:30]!r}")
            elif n > confirm_count:
                problems.append(f"depth_check.{key}：指向 confirm[{n}]，但這一版只有 {confirm_count} 條加碼條件")
        elif text.startswith(NOT_APPLICABLE_PREFIX) and not text[len(NOT_APPLICABLE_PREFIX):].strip():
            problems.append(f"depth_check.{key}：「不適用：」後面要寫理由")
        elif value_form(text) is None:
            problems.append(f"depth_check.{key}：寫法要是四種之一——引用（開頭 {'、'.join(CITATION_PREFIXES)}）｜"
                            f"不適用：理由｜加碼條件：c<n>｜缺：…（收到 {text[:30]!r}；沒查就寫「缺：…」）")
    return problems


def depth_check_lines(depth_check: Mapping[str, Any] | None) -> list[str]:
    """寫敘事時印的一行（CLI 用）：沒有清單／還沒查幾項（⑤ 會數）／十項都查過（各幾種）。只印——形狀不合由契約擋。"""
    if not depth_check:
        return ["  ⚠ 這一版沒有深挖清單（depth_check）——可開或已持有的檔，⑤「加碼條件還沒查」會數它（research-drain 段 5）"]
    missing = unchecked_items(depth_check)
    if missing:
        return [f"  ⚠ 加碼條件還沒查 {len(missing)} 項（⑤ 會數，drain 歸零）：" + "、".join(missing)]
    values = [str(depth_check[k]).strip() for k in DEPTH_CHECK_KEYS]
    addon = sum(1 for v in values if v.startswith(ADDON_PREFIX))
    na = sum(1 for v in values if v.startswith(NOT_APPLICABLE_PREFIX))
    return [f"  ✓ 深挖清單 {len(DEPTH_CHECK_ITEMS)} 項都查過（引用 {len(values) - addon - na}｜不適用 {na}"
            f"｜加碼條件 {addon}）"]


def dropped_checks_line(previous: Mapping[str, Any] | None, current: Mapping[str, Any] | None) -> str | None:
    """重寫時上一版查過、這一版沒寫成查過的項目（2026-11-04 R2：為別的原因重寫——換騎、處置醒來的 watch——沒抄清單，
    ⑤ 那一檔就跳回還沒查）→ 一行提醒；沒有掉的回 None。只印、不擋：這一版沒查就是沒查，不自動沿用（敘事是當時的判斷）。"""
    before = dict(previous) if isinstance(previous, Mapping) else {}
    after = dict(current) if isinstance(current, Mapping) else {}
    dropped = [label for key, label in DEPTH_CHECK_ITEMS if is_checked(before.get(key)) and not is_checked(after.get(key))]
    if not dropped:
        return None
    return (f"  ⚠ 上一版查過的 {len(dropped)} 項這一版沒寫（⑤ 會把它們數回還沒查）：" + "、".join(dropped)
            + "——還成立就把那幾項抄過來（只提醒、不擋）")


__all__ = ["ADDON_PREFIX", "CITATION_PREFIXES", "DEPTH_CHECK_ITEMS", "DEPTH_CHECK_KEYS", "NOT_APPLICABLE_PREFIX",
           "UNCHECKED_PREFIX",
           "addon_index", "depth_check_lines", "depth_check_problems", "dropped_checks_line", "is_checked",
           "unchecked_items", "value_form"]
