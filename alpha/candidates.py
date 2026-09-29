"""候選狀態板的契約與純函式（Phase 3 Step 3.6）——**零 I/O**。

推導本身（要讀 watch registry、讀圖對圖、Engine C、Sheet）住 `alpha/providers/candidates.py`；這裡只放：
封閉字彙、首屏三個字、滯留天數、Sheet 持有的索引、整板組裝、rollup。

⚠ 為什麼拆成兩個模組（2026-09-29 3.6 審查）：字彙原本住 providers，於是心跳與 APP 的 fake payload 一 import 字彙，
就經 `alpha/providers/__init__` 把 Neo4j provider、Engine C、yfinance、requests 全載進來——心跳 import 期多了一整串會失敗的
相依，而且請求路徑測試的「request path 不得載入模型／IO 模組」哨兵在 fixture 階段就被預載瞎掉（通過與失效同形，L13）。

封閉字彙：五組 `GROUPS`（可開／缺 X／已定價等回落／不要／已持有）＋四個附組 `SIDE_GROUPS`
（非倍率候選／邊緣無法量／舊版／前提失效）。**組內按 ticker 字母**；沒有分數、沒有名次（AGENTS 消費契約）。
可開為零就零——讓它非空的路是研究，不是放寬任何一條前提（硬約束 7）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, Mapping, Sequence

from .narrative.contracts import RECORD_VERSION_V2, InvestorBrief
from .three_questions import rollup as line_rollup

GROUPS: tuple[str, ...] = ("open", "missing", "priced_wait", "pass", "held")
GROUP_LABELS: Mapping[str, str] = {"open": "可開", "missing": "缺 X", "priced_wait": "已定價等回落",
                                   "pass": "不要", "held": "已持有"}
SIDE_GROUPS: tuple[str, ...] = ("not_multiple", "edge_unmeasurable", "legacy", "precondition_failed")
SIDE_LABELS: Mapping[str, str] = {"not_multiple": "非倍率候選", "edge_unmeasurable": "邊緣無法量",
                                  "legacy": "舊版（缺候選狀態）", "precondition_failed": "前提失效"}
#: 敘事宣告的兩題 → 首屏三個字（§8 第 1 點）；v1 或沒有敘事一律「未答」。
ANSWER_WORDS: Mapping[str, str] = {"yes": "是", "no": "否", "unmeasurable": "無法量"}
UNANSWERED = "未答"
#: 會死嗎：四盞燈的最差色與灰燈數（燈不是數字）。顏色字彙＝`alpha.wipeout` 的輸出。
LIGHT_ORDER: tuple[str, ...] = ("red", "amber", "green")
LIGHT_WORDS: Mapping[str, str] = {"red": "紅", "amber": "黃", "green": "綠"}
#: 「該重寫」的三種狀態（`engine_b.queue_segments.narrative_rewrite_state` 的值）→ 人讀。
REWRITE_STATE_WORDS: Mapping[str, str] = {"fired": "醒來", "touched": "觸及", "expired": "到期未判"}
PRICED_IN_LINES: tuple[str, ...] = ("own_history_pctile", "cohort_median", "rel_return_30d", "rel_return_90d")
IN_NUMBERS_LINES: tuple[str, ...] = ("in_numbers_series",)
WIPEOUT_LINES: tuple[str, ...] = ("wipeout_cash_runway", "wipeout_debt", "wipeout_dilution", "wipeout_going_concern")

#: 這份板**不是什麼**——隨 artifact 出門，畫面永遠印得出來。
CANDIDATES_THIS_IS_NOT: tuple[str, ...] = (
    "不是排序、沒有名次：組內按 ticker 字母；可開是每檔各自過的前提，不是分數，可同時多檔，也可以是 0。",
    "不給部位尺寸：買多少、什麼時候買由使用者自行判斷並手動下單。",
    "宣告來自敘事（研究 session 寫的 append-only ledger）；「已持有」來自 Sheet；本板每天重算，不寫任何 authority。",
    "本檔標的高度集中於當前題材：N 檔不等於 N 個獨立機會。",
)


def cap_label(value: Any) -> str | None:
    """市值顯示字串（前端不做任何算術，連 ÷1e9 都不做；`tests/test_webapp_api.py` 守著）。"""
    try:
        return f"{float(value) / 1e9:.1f}B USD" if value is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 已持有（Sheet）
# ---------------------------------------------------------------------------

def held_index(resolution: Mapping[str, Any] | None, *, is_beta: Callable[[str], bool],
               failure: str | None = None) -> dict[str, Any]:
    """`portfolio.holdings.resolve_holdings()` 的結果 → 候選板用的「已持有」：**alpha、股數 > 0、解析得到**。

    - `resolution=None`＝Sheet 讀不到；**`rows` 是空的也一樣**（Sheet 分頁清空時 `fetch_portfolio` 回 [] 不丟例外；
      真實帳戶至少有現金列，空表只可能是讀取失敗——硬擋對同一份 [] 回 unmeasurable，這裡不得反過來判「持有 0」）。
      整板暫停已持有判定（`upstream_unavailable`），不得把「沒讀到」當成「沒持有」。
    - beta 由 `risk/hard_caps.py` 的公開判別排除（alpha／beta 同一條線）；beta 列、現金列、股數 0 的列解析不到
      都不算進「解析不到」——它們不是要人決定的 identity 問題。"""
    rows = list((resolution or {}).get("rows") or ())
    if resolution is None or not rows:
        why = failure or ("Sheet 沒有任何可解析的持股列（連現金列都沒有）——視同讀不到" if resolution is not None
                          else "讀取失敗")
        return {"status": "upstream_unavailable",
                "reason": f"持股未讀到，已持有判定暫停（{why}）——其餘列的宣告照印，但標「持股未驗」",
                "by_company": {}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
    by_company: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []
    beta_excluded = zero_shares = 0
    for row in rows:
        if row.get("cash"):
            continue
        if is_beta(str(row.get("ticker") or "")):
            beta_excluded += 1
            continue
        if not (row.get("shares") or 0) > 0:
            zero_shares += 1
            continue
        if not row.get("company_id"):
            unresolved.append(str(row.get("ticker")))
            continue
        by_company[str(row["company_id"])] = {"sheet_ticker": row.get("ticker"), "source": row.get("source")}
    return {"status": "ok", "reason": None, "by_company": by_company, "unresolved": sorted(set(unresolved)),
            "beta_excluded": beta_excluded, "zero_shares": zero_shares}


# ---------------------------------------------------------------------------
# 三個字、滯留
# ---------------------------------------------------------------------------

def three_words(three_questions: Mapping[str, Any] | None, brief: InvestorBrief | None,
                *, not_read: str = "未讀到") -> dict[str, str]:
    """首屏三個字：會死嗎＝四盞燈的最差色（＋灰燈數）；已定價嗎／出現在數字裡＝敘事的宣告。"""
    if three_questions is None:
        will = not_read
    else:
        values = [r.get("value") for r in three_questions.get("will_it_die") or ()]
        grey = sum(1 for v in values if v not in LIGHT_ORDER)
        worst = next((c for c in LIGHT_ORDER if c in values), None)
        will = (LIGHT_WORDS[worst] + (f"（灰 {grey}）" if grey else "")) if worst else f"灰 {grey}"
    answers = brief.answers if brief is not None and brief.record_version == RECORD_VERSION_V2 else None
    return {"will_it_die": will,
            "priced_in": ANSWER_WORDS[answers.priced_in] if answers else UNANSWERED,
            "in_numbers": ANSWER_WORDS[answers.in_numbers] if answers else UNANSWERED}


def stall_since(records: Sequence[InvestorBrief], brief: InvestorBrief) -> datetime:
    """沿 `supersedes` 鏈往回，取**連續宣告同一 state** 的最早一筆 `created_at`（缺 X／等回落另要求同一 watch）——
    同 state 重寫不歸零。**撤回打斷連續**：撤回之後到重寫之前那段「沒有宣告」，不算進滯留。

    撤回用**時間**判，不看鏈上有沒有經過撤回紀錄：新版可以直接 supersede 被撤的那一筆（撤回紀錄本身不在鏈上），
    所以只要兩筆之間有任何一筆撤回紀錄落在 (prev, cur] 之間，那段時間就沒有生效的宣告（`select_brief` 回 None）。"""
    by_id = {r.brief_id: r for r in records}
    retractions = [r.created_at for r in records if r.retracted]
    state = brief.candidate_state.state if brief.candidate_state else None
    watch = brief.candidate_state.watch_id if brief.candidate_state else None
    since, cur, seen = brief.created_at, brief, {brief.brief_id}
    while cur.supersedes_id and cur.supersedes_id in by_id and cur.supersedes_id not in seen:
        prev = by_id[cur.supersedes_id]
        seen.add(prev.brief_id)
        cs = prev.candidate_state
        if prev.retracted or prev.record_version != RECORD_VERSION_V2 or cs is None or cs.state != state \
                or (state in ("missing", "priced_wait") and cs.watch_id != watch) \
                or any(prev.created_at < t <= cur.created_at for t in retractions):
            break
        since, cur = prev.created_at, prev
    return since


# ---------------------------------------------------------------------------
# 整板與 rollup
# ---------------------------------------------------------------------------

def _absence_counts(bucket: Mapping[str, int] | None, not_read: int) -> dict[str, Any]:
    bucket = dict(bucket or {})
    valued = int(bucket.pop("value", 0))
    absent = {k: int(v) for k, v in bucket.items()}
    if not_read:
        absent["not_read"] = absent.get("not_read", 0) + not_read
    return {"valued": valued, "absent": dict(sorted(absent.items())), "absent_total": sum(absent.values())}


def rollup(three_questions_by_ticker: Mapping[str, Mapping[str, Any] | None],
           edges: Mapping[str, Mapping[str, Any]], *,
           not_read_reasons: Mapping[str, str] | None = None) -> dict[str, Any]:
    """宇宙每一檔的三題與四盞燈 rollup——**只數有值與依 kind 的缺席，不是結論**。

    逐行計數沿用 `alpha.three_questions.rollup`（Step 3.3 的那一份，不另算；L16）。四盞燈另外給
    **盞數**（紅／黃／綠／**灰＝沒量到**，灰依 kind 分）與「有紅燈的檔」——「一檔亮四盞」與「四檔各亮一盞」
    是兩件事（ARCHITECTURE §4.1 段 4）；⚠ 灰不是綠。讀不到三題的檔記 `not_read` 並帶理由（INV-3）。"""
    tqs = dict(three_questions_by_ticker)
    read = [tq for tq in tqs.values() if tq is not None]
    not_read = [t for t, tq in tqs.items() if tq is None]
    lines = line_rollup(read)
    lamps: dict[str, int] = {"red": 0, "amber": 0, "green": 0, "unlit": 0}
    unlit_by_kind: dict[str, int] = {}
    red_tickers: list[str] = []
    all_four = 0
    for ticker, tq in tqs.items():
        if tq is None:
            continue
        rows = list(tq.get("will_it_die") or ())
        for r in rows:
            v = r.get("value")
            if v in LIGHT_ORDER:
                lamps[v] += 1
            else:
                lamps["unlit"] += 1
                k = str(r.get("absence_kind") or "unlit")
                unlit_by_kind[k] = unlit_by_kind.get(k, 0) + 1
        if any(r.get("value") == "red" for r in rows):
            red_tickers.append(ticker)
        if rows and all(r.get("value") in LIGHT_ORDER for r in rows):
            all_four += 1
    edge_counts: dict[str, int] = {}
    for e in edges.values():
        k = str((e or {}).get("state") or "unmeasurable")
        edge_counts[k] = edge_counts.get(k, 0) + 1
    reasons = dict(not_read_reasons or {})
    return {
        "universe": len(tqs),
        "lines": {k: dict(v) for k, v in sorted(lines.items())},
        "priced_in_own": _absence_counts(lines.get("own_history_pctile"), len(not_read)),
        "in_numbers": _absence_counts(lines.get("in_numbers_series"), len(not_read)),
        "wipeout": {"companies": len(read), "lamps": lamps, "unlit_by_kind": dict(sorted(unlit_by_kind.items())),
                    "red_tickers": sorted(red_tickers), "all_four_non_grey": all_four},
        "not_read": {"n": len(not_read), "tickers": sorted(not_read),
                     "reasons": {t: reasons.get(t, "（沒有留下理由）") for t in sorted(not_read)}},
        "edge": dict(sorted(edge_counts.items())),
    }


def assemble_board(rows: Sequence[Mapping[str, Any] | None], *, universe: Sequence[str], held: Mapping[str, Any],
                   narrative_rewrite: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """逐檔的列 → 五組＋附組＋計數（含 0）＋各組最老滯留。**組內按 ticker 字母**。

    `narrative_rewrite`：整板「敘事該重寫」的清單（連結斷了＋敘事來源 watch 醒來／觸及／到期未判），每筆帶 `kind`。"""
    groups: dict[str, list[dict[str, Any]]] = {g: [] for g in GROUPS}
    sides: dict[str, list[dict[str, Any]]] = {s: [] for s in SIDE_GROUPS}
    no_narrative = 0
    for row in rows:
        if row is None:
            no_narrative += 1
            continue
        if row.get("group"):
            groups[row["group"]].append(dict(row))
        elif row.get("side"):
            sides[row["side"]].append(dict(row))
    for bucket in (*groups.values(), *sides.values()):
        bucket.sort(key=lambda r: str(r.get("ticker")))
    held_ok = held.get("status") == "ok"
    counts = {**{g: (len(groups[g]) if (g != "held" or held_ok) else None) for g in GROUPS},
              **{s: len(sides[s]) for s in SIDE_GROUPS}, "no_narrative": no_narrative}
    oldest = {g: max((r["stall_days"] for r in groups[g] if isinstance(r.get("stall_days"), int)), default=None)
              for g in ("open", "missing", "priced_wait")}
    return {"groups": groups, "side_groups": sides, "counts": counts, "oldest_stall_days": oldest,
            "universe": sorted(universe),
            "holdings": {"status": held.get("status"), "reason": held.get("reason"),
                         "unresolved": list(held.get("unresolved") or ()),
                         "beta_excluded": held.get("beta_excluded"), "zero_shares": held.get("zero_shares")},
            "narrative_rewrite": [dict(b) for b in narrative_rewrite]}


__all__ = ["ANSWER_WORDS", "CANDIDATES_THIS_IS_NOT", "GROUPS", "GROUP_LABELS", "IN_NUMBERS_LINES", "LIGHT_ORDER",
           "LIGHT_WORDS", "PRICED_IN_LINES", "REWRITE_STATE_WORDS", "SIDE_GROUPS", "SIDE_LABELS", "UNANSWERED",
           "WIPEOUT_LINES", "assemble_board", "cap_label", "held_index", "rollup", "stall_since", "three_words"]
