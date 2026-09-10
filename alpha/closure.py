"""每檔閉環（research-drain 佇列段 5）的機器工單、終局判定與下一檔選取——2026-09-09 研究閉環 P3。

## 這一層回答什麼

> 哪些 tracked／已 materialize 的標的還沒到終局？終局有幾檔？下一檔該補誰、為什麼是它？

工單不是新分類：它**照抄** analyst view artifact 的 `readiness.blocker_details`（每格帶 `absence_kind`／`settled`），
那正是「這一檔還缺什麼」的機器清單（L16：分類已經存在，跟著資料走到消費端）。本模組只做三件確定性的事：
判終局、算計數、排下一檔。

## 終局（closure）——「做完」必須是機器查得出來的

| 終局 | 判準 |
|---|---|
| `ready` | readiness 是 `ready`／`ready_with_flags` |
| `settled` | readiness `blocked`，但每一個 blocker 都 `settled=true`（刻意不主張／方法不適用／能力不存在）——這是誠實的答案，不是失敗 |
| （未到終局） | 至少一個 blocker 未 settled |

⚠ 「掛在 pq2 編號上」在 v1 只**計數**不算終局：artifact 不帶 pq2 連結，要硬推會變成第二份對照表。

## 下一檔選取（確定性；寫在程式不寫在 skill 散文）

依序比較，先分出高下者定案：
1. **有同期 EPS 共識**（Engine C `consensus_estimates`）——沒有共識連兩桿拆解都做不了
2. **forward EPS 共識為正**——v1 只有本益比法，虧損公司等 P6
3. **產業能加一**——該檔所屬產業目前**沒有** ready 檔（分散度優先於主線，2026-09-09 使用者定案）
4. **瓶頸排序名次**——越前越先；不在排序內排最後
5. ticker 字典序（tie-break，讓結果可重現）

**深度優先**由 skill 執行：第 N 檔未到終局不開第 N+1 檔，除非它卡在 pq2 或世界。本模組只給順序。

## 不做的事

不寫任何 authority、不重算任何判讀、不呼叫 LLM；讀不到某個來源就把那一欄留 `None` 並在 notes 說明，不補 0。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

READY_STATES: frozenset[str] = frozenset({"ready", "ready_with_flags"})

#: 選取規則的**可讀版本**——與 `_sort_key` 一一對應；drain／skill 印這個，不另寫一份。
NEXT_PICK_RULE: tuple[str, ...] = (
    "有同期 EPS 共識",
    "forward EPS 共識為正（v1 只有本益比法）",
    "產業能加一（所屬產業尚無 ready 檔）",
    "瓶頸排序名次（不在排序內排最後）",
    "ticker 字典序",
)


@dataclass(frozen=True, slots=True)
class BacklogRow:
    ticker: str
    readiness: str
    open_panels: tuple[str, ...]
    settled_panels: tuple[str, ...]
    absence_kinds: Mapping[str, str] = field(default_factory=dict)
    has_consensus: bool | None = None
    forward_eps_positive: bool | None = None
    sector: str | None = None
    bottleneck_rank: int | None = None
    generated_at: str | None = None

    @property
    def terminal(self) -> str | None:
        if self.readiness in READY_STATES:
            return "ready"
        if not self.open_panels and self.settled_panels:
            return "settled"
        return None


# ---------------------------------------------------------------------------
# 純函式：終局／排序／摘要
# ---------------------------------------------------------------------------

def row_from_artifact(ticker: str, payload: Mapping[str, Any]) -> BacklogRow:
    """從一份 analyst view artifact 抄出工單列（不推論、不 parse 散文）。"""
    readiness = payload.get("readiness") or {}
    details = readiness.get("blocker_details") or []
    open_panels = tuple(str(d["panel"]) for d in details if not d.get("settled"))
    settled_panels = tuple(str(d["panel"]) for d in details if d.get("settled"))
    kinds = {str(d["panel"]): str(d.get("absence_kind") or "") for d in details}
    return BacklogRow(
        ticker=ticker, readiness=str(readiness.get("state") or "blocked"),
        open_panels=open_panels, settled_panels=settled_panels, absence_kinds=kinds,
        generated_at=str(payload.get("generated_at") or "") or None,
    )


def sectors_with_ready(rows: Iterable[BacklogRow]) -> frozenset[str]:
    return frozenset(r.sector for r in rows if r.terminal == "ready" and r.sector)


def _sort_key(row: BacklogRow, ready_sectors: frozenset[str]) -> tuple:
    # False 排前面：有共識（not True=False）、EPS 為正、產業尚無 ready；None（讀不到）排在 False 之後、True 之前
    def _flag(value: bool | None) -> int:
        return 0 if value is True else (1 if value is None else 2)

    return (
        _flag(row.has_consensus),
        _flag(row.forward_eps_positive),
        # 只有「產業已知、且該產業還沒有 ready 檔」才算能加一；產業未知（不在排序內）不給分散度加分
        0 if (row.sector and row.sector not in ready_sectors) else 1,
        1 if row.bottleneck_rank is None else 0,
        row.bottleneck_rank or 0,
        row.ticker,
    )


def rank_backlog(rows: Sequence[BacklogRow]) -> list[BacklogRow]:
    """未到終局的列，依 NEXT_PICK_RULE 排序。到終局的不在裡面。"""
    ready_sectors = sectors_with_ready(rows)
    pending = [r for r in rows if r.terminal is None]
    return sorted(pending, key=lambda r: _sort_key(r, ready_sectors))


def explain_pick(row: BacklogRow, ready_sectors: frozenset[str]) -> str:
    parts = [
        "有共識" if row.has_consensus else ("共識未讀到" if row.has_consensus is None else "無共識"),
        "EPS 為正" if row.forward_eps_positive else ("EPS 未讀到" if row.forward_eps_positive is None else "EPS 非正"),
        (f"產業「{row.sector}」尚無 ready 檔" if row.sector and row.sector not in ready_sectors
         else (f"產業「{row.sector}」已有 ready 檔" if row.sector else "不在瓶頸排序的產業組內")),
        (f"瓶頸排序第 {row.bottleneck_rank}" if row.bottleneck_rank else "不在瓶頸排序內"),
    ]
    return "；".join(parts)


def summarize(rows: Sequence[BacklogRow]) -> dict[str, Any]:
    ready = [r for r in rows if r.terminal == "ready"]
    settled = [r for r in rows if r.terminal == "settled"]
    ready_sectors = sectors_with_ready(rows)
    all_sectors = {r.sector for r in rows if r.sector}
    ranked = rank_backlog(rows)
    nxt = ranked[0] if ranked else None
    return {
        "total": len(rows),
        "ready": sorted(r.ticker for r in ready),
        "settled": sorted(r.ticker for r in settled),
        "terminal_count": len(ready) + len(settled),
        "open_count": len(ranked),
        "sectors_with_ready": sorted(ready_sectors),
        "sectors_seen": sorted(all_sectors),
        "next": None if nxt is None else {
            "ticker": nxt.ticker,
            "open_panels": list(nxt.open_panels),
            "absence_kinds": {p: nxt.absence_kinds.get(p) for p in nxt.open_panels},
            "why": explain_pick(nxt, ready_sectors),
        },
        "queue": [r.ticker for r in ranked[:10]],
        "rule": list(NEXT_PICK_RULE),
    }


def render_summary(summary: Mapping[str, Any], *, notes: Sequence[str] = ()) -> str:
    nxt = summary.get("next")
    line = (
        f"段5 每檔閉環：到終局 {summary['terminal_count']}（ready {len(summary['ready'])}／settled {len(summary['settled'])}）"
        f"／未到終局 {summary['open_count']}｜有 ready 檔的產業 {len(summary['sectors_with_ready'])}／{len(summary['sectors_seen'])}"
    )
    if nxt:
        line += (f"｜下一檔：{nxt['ticker']}（{nxt['why']}；缺：{'、'.join(nxt['open_panels']) or '—'}）")
    else:
        line += "｜下一檔：—（全部到終局）"
    if notes:
        line += "｜未讀到：" + "；".join(notes)
    return line


# ---------------------------------------------------------------------------
# 以下兩個 helper 接受已開好的 conn／registry 物件，不 import 任何 I/O 模組——
# 真正讀檔／連線的 `collect_backlog()` 住 `alpha/providers/closure.py`（alpha 核心層保持純淨）。
# ---------------------------------------------------------------------------

def _consensus_flags(tickers: Iterable[str], conn: Any) -> dict[str, tuple[bool, bool | None]]:
    """ticker → (有 EPS 共識, forward EPS 為正)。取每檔最新 snapshot 的 eps 列；+1y 優先、0y 兜底。"""
    rows = conn.execute(
        "SELECT ticker, snapshot_date, relative_label, estimate_avg FROM consensus_estimates WHERE metric = 'eps'"
    ).fetchall()
    latest: dict[str, str] = {}
    for ticker, snap, _label, _val in rows:
        t = str(ticker).upper()
        if t not in latest or str(snap) > latest[t]:
            latest[t] = str(snap)
    values: dict[str, dict[str, float | None]] = {}
    for ticker, snap, label, val in rows:
        t = str(ticker).upper()
        if str(snap) != latest.get(t):
            continue
        values.setdefault(t, {})[str(label)] = (float(val) if val is not None else None)
    out: dict[str, tuple[bool, bool | None]] = {}
    for t in tickers:
        vals = values.get(t.upper())
        if not vals:
            out[t] = (False, None)
            continue
        pick = vals.get("+1y") if vals.get("+1y") is not None else vals.get("0y")
        out[t] = (True, (pick > 0) if pick is not None else None)
    return out


def _sector_and_rank(ranking_payload: Mapping[str, Any], registry: Any) -> dict[str, tuple[str | None, int | None]]:
    """ticker → (產業組, 最佳全域名次)。rows 的順序就是名次；sectors[*].actionable_ranks 給名次→產業。"""
    rank_to_sector: dict[int, str] = {}
    for group in ranking_payload.get("sectors") or []:
        for rank in group.get("actionable_ranks") or []:
            rank_to_sector[int(rank)] = str(group.get("sector"))
    out: dict[str, tuple[str | None, int | None]] = {}
    for index, row in enumerate(ranking_payload.get("rows") or [], start=1):
        company_id = str(row.get("company_id") or "")
        ticker = None
        try:
            ticker = registry.research_ticker(company_id)
        except Exception:  # noqa: BLE001
            ticker = None
        if not ticker:
            continue
        ticker = str(ticker).upper()
        sector = rank_to_sector.get(index)
        prev = out.get(ticker)
        if prev is None or (prev[1] is None or index < prev[1]):
            out[ticker] = (sector or (prev[0] if prev else None), index)
    return out


# ---------------------------------------------------------------------------
# 閉包 gate（P7-c，2026-09-10）——**「這一段做完了沒」必須是機器回答的**
# ---------------------------------------------------------------------------
#
# 事發（2026-09-09，git log 可查）：skill Step 5 把段 5 的閉包條件寫成「到終局檔數在本輪
# 至少 +1」。那一句同時承載兩種語意（L12）：**進度下限**（不准開三檔各補一格）與
# **停止條件**（滿足就算做完）。執行者讀成後者——`23:18→23:28` 做完 LITE 一檔，`23:33`
# 就轉去段 4 收工，段 5 還剩 67 檔。skill 自己的開場白是「停止條件若能在任意時刻被滿足，
# 它就不是停止條件」，這次是**被滿足得太早**。
#
# 修法是先把兩種語意分開，再讓程式回答其中一種：
#   - 停止條件 → 本函式（`open_count == 0`）
#   - 進度下限 → 留在 skill，一輪 0 檔到終局要報告原因，不得靜默宣告 noop
#
# ⚠ **深度優先是「同時開幾檔」的上限（1），不是「一輪做幾檔」的上限（無上限）。**
# 兩者被混為一談正是「我是不是要說七十幾次繼續」的來源。

#: gate 的三種結果。`unknown` 存在的唯一理由是 fail closed——**讀不到 artifact 不得算閉包**
#: （INV-3：「查不到了」不是合法 lifecycle）。
GATE_STATES: tuple[str, ...] = ("closed", "open", "unknown")


@dataclass(frozen=True, slots=True)
class GateResult:
    """段 5 閉包判定。`state` 直接對應 CLI 的 exit code：closed=0／open=1／unknown=2。"""

    state: str
    open_count: int
    #: 這一輪還可以自己往前推的（未到終局，且不在 skip 裡）
    actionable: tuple[str, ...]
    #: 呼叫端顯式宣告「本輪推不動」的（卡 pq2／卡世界）。**gate 不自己猜**——
    #: pq2 歸屬今天只存在於 `todo_pool.json` 的散文標題裡，去 parse 它就是 L16 禁的那件事。
    skipped: tuple[str, ...]
    next_ticker: str | None
    reason: str


def closure_gate(rows: Sequence[BacklogRow], *, skip: Iterable[str] = ()) -> GateResult:
    """段 5 閉包成立嗎？**不看「本輪做了幾檔」**——只看還剩幾檔可做。"""
    if not rows:
        return GateResult("unknown", 0, (), (), None,
                          "讀不到任何 analyst view artifact——fail closed，不得當成閉包")
    skip_set = {str(t).upper() for t in skip}
    ranked = rank_backlog(rows)
    actionable = tuple(r.ticker for r in ranked if r.ticker.upper() not in skip_set)
    skipped = tuple(r.ticker for r in ranked if r.ticker.upper() in skip_set)
    if actionable:
        return GateResult("open", len(ranked), actionable, skipped, actionable[0],
                          f"還有 {len(actionable)} 檔可自主推進——不得宣告 noop、不得拉長 loop 間隔")
    if skipped:
        return GateResult("closed", len(ranked), (), skipped, None,
                          f"剩下的 {len(skipped)} 檔都已顯式標為卡 pq2／卡世界")
    return GateResult("closed", 0, (), (), None, "每一檔都到終局")

__all__ = [
    "GATE_STATES", "NEXT_PICK_RULE", "READY_STATES", "BacklogRow", "GateResult",
    "closure_gate", "explain_pick", "rank_backlog", "render_summary",
    "row_from_artifact", "sectors_with_ready", "summarize",
]
