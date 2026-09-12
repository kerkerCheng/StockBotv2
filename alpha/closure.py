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
    "使用者沒有明示 defer（pq2 有 deferred_at 的往後排，仍列出不藏）",
    "有同期 EPS 共識",
    "forward EPS 共識為正（v1 只有本益比法）",
    "產業能加一（所屬產業尚無 ready 檔）",
    "瓶頸排序名次（不在排序內排最後）",
    "已有基期觀測（缺的要另外找一手年報／決算短信，實測成本約 3 倍）",
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
    has_base_observation: bool | None = None
    #: 這一檔在 pq2 有未結案且被使用者明示 defer 的項目。
    #: **它不是啟發法，是使用者的一句話**，所以排在四條研究判準之前。
    user_deferred: bool = False
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
        # 第 0 條（2026-09-11）：「使用者剛說先不要」與「系統排第一」不得同時成立（L12）。
        # 往後排、**不過濾**——藏起來會讓「沒做」與「不存在」同形（INV-3）。
        # 它排在四條研究判準之前，因為那四條是機器對研究價值的啟發法，而這一條是
        # 使用者的明示指示；讓啟發法蓋過指示，方向就反了。
        1 if row.user_deferred else 0,
        _flag(row.has_consensus),
        _flag(row.forward_eps_positive),
        # 只有「產業已知、且該產業還沒有 ready 檔」才算能加一；產業未知（不在排序內）不給分散度加分
        0 if (row.sector and row.sector not in ready_sectors) else 1,
        1 if row.bottleneck_rank is None else 0,
        row.bottleneck_rank or 0,
        # 成本維度（2026-09-11 使用者定案）：**只破平手**——放在四條判準之後、ticker 之前。
        # 不放在 ticker 之後：那一格永遠碰不到（ticker 唯一），會變成看起來生效的死設定。
        # 它不是「先做簡單的」——前四條的相對順序一格都沒動；它只在前四條完全同分時，
        # 讓順序不再對「這一檔要不要另外去找一手年報」盲目（實測成本差約 3 倍）。
        _flag(row.has_base_observation),
        row.ticker,
    )


def rank_backlog(rows: Sequence[BacklogRow]) -> list[BacklogRow]:
    """未到終局的列，依 NEXT_PICK_RULE 排序。到終局的不在裡面。"""
    ready_sectors = sectors_with_ready(rows)
    pending = [r for r in rows if r.terminal is None]
    return sorted(pending, key=lambda r: _sort_key(r, ready_sectors))


def explain_pick(row: BacklogRow, ready_sectors: frozenset[str]) -> str:
    parts = [
        *(["⚠ 使用者已 defer 相關 pq2——已往後排，仍列出"] if row.user_deferred else []),
        "有共識" if row.has_consensus else ("共識未讀到" if row.has_consensus is None else "無共識"),
        "EPS 為正" if row.forward_eps_positive else ("EPS 未讀到" if row.forward_eps_positive is None else "EPS 非正"),
        (f"產業「{row.sector}」尚無 ready 檔" if row.sector and row.sector not in ready_sectors
         else (f"產業「{row.sector}」已有 ready 檔" if row.sector else "不在瓶頸排序的產業組內")),
        (f"瓶頸排序第 {row.bottleneck_rank}" if row.bottleneck_rank else "不在瓶頸排序內"),
        ("已有基期觀測" if row.has_base_observation
         else ("基期觀測未讀到" if row.has_base_observation is None else "無基期觀測（要先找一手年報）")),
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


#: 未到終局那一批「卡在哪」的彙總欄位。**刻意只用 `_sort_key` 已經在讀的那幾個**——
#: 新造一組分類就會是 L16 說的「我需要一個分類，系統有，但我手上的介面沒帶」的第二份。
OPEN_PROFILE_FIELDS: tuple[tuple[str, str], ...] = (
    ("no_bottleneck_edge", "不在瓶頸排序內（Q1 結構分算不出：沒有帶 substitutability 的結構邊）"),
    ("no_consensus", "沒有同期 EPS 共識"),
    ("forward_eps_not_positive", "forward EPS 共識非正（v1 只有本益比法）"),
    ("no_base_observation", "沒有基期觀測（要先自己找一手年報／決算短信，實測成本約 3 倍）"),
    ("user_deferred", "使用者已 defer 相關 pq2（已往後排，仍列出）"),
)


def open_profile(rows: Sequence[BacklogRow], *, skip: Iterable[str] = ()) -> dict[str, Any]:
    """未到終局的那批各自卡在哪——**計數器要自己出現，不能靠人記得去查**（L14）。

    事發（2026-09-11）：段5 一次卡在 60 檔時，執行者得自己去讀 Neo4j export 才算得出
    「59 檔的 Q1 結構分是 None」。那個數字每輪都該在眼前，因為它決定的不是「還有幾檔」，
    而是**剩下的檔寫得出有資訊的判斷嗎**——`bottleneck_rank is None` 代表這檔沒有任何
    帶 substitutability 的結構邊，硬寫判斷只會得到「2 軸 unknown ＋ 2 軸只靠行情快照」。

    ⚠ 三個計數**可以重疊**（同一檔可能同時沒共識又不在排序內），所以不相加、不算百分比。
    ⚠ `None` 是「讀不到」不是「否」：只數明確為否的那些（Missing != Zero，L12）。
    """
    skip_set = {str(t).upper() for t in skip}
    open_rows = [r for r in rows if r.terminal is None and r.ticker.upper() not in skip_set]
    return {
        "open_count": len(open_rows),
        "no_bottleneck_edge": sorted(r.ticker for r in open_rows if r.bottleneck_rank is None),
        "no_consensus": sorted(r.ticker for r in open_rows if r.has_consensus is False),
        "forward_eps_not_positive": sorted(
            r.ticker for r in open_rows if r.forward_eps_positive is False),
        "no_base_observation": sorted(
            r.ticker for r in open_rows if r.has_base_observation is False),
        "user_deferred": sorted(r.ticker for r in open_rows if r.user_deferred),
    }


def render_open_profile(profile: Mapping[str, Any]) -> list[str]:
    """把 `open_profile` 印成人看得懂的幾行。空集合仍然印出來——0 也是資訊。"""
    total = int(profile.get("open_count") or 0)
    if not total:
        return ["未到終局 0 檔"]
    out = []
    for key, label in OPEN_PROFILE_FIELDS:
        hit = list(profile.get(key) or [])
        out.append(f"{label}：{len(hit)}／{total} 檔")
    return out


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

def deferred_tickers(pool: Mapping[str, Any], resolve: Any) -> frozenset[str]:
    """pq2 裡**未結案且使用者明示 defer** 的項目對應到哪些 ticker。

    只讀結構化欄位（`ticker`／`company_id`），**不 parse 標題**——標題裡的 `co:xxx：`
    前綴是散文，去 parse 它就是 L16 禁的那件事（同一個理由讓 `closure_gate` 的
    `--skip` 是呼叫端顯式宣告而不是 gate 自己猜）。舊項目在下一次 `todo sync`
    upsert 時補上欄位；在那之前它們就是讀不到，**寧可少排也不要猜錯**。

    `resolve` 是 company_id → ticker 的解析函式（registry），失敗回 None。
    """
    out: set[str] = set()
    for item in pool.get("items") or ():
        if item.get("resolved_at") or item.get("resolution"):
            continue
        if not item.get("deferred_at"):
            continue
        ticker = str(item.get("ticker") or "").strip()
        if not ticker and item.get("company_id"):
            ticker = str(resolve(str(item["company_id"])) or "").strip()
        if ticker:
            out.add(ticker.upper())
    return frozenset(out)


def _base_observation_tickers(conn: Any) -> frozenset[str]:
    """有 `fiscal_year_results` 基期觀測的 ticker 集合（Engine C 人工 ledger）。

    這是 `NEXT_PICK_RULE` 倒數第二格（ticker 之前）的成本代理：沒有基期觀測的檔，
    session 要自己去找一手年報／決算短信／業績發表，2026-09-10 實測工具呼叫數差約 3 倍。
    ⚠ 它只回答「基期在不在手上」，不回答基期對不對——後者是研究判斷，不進排序鍵。
    """
    rows = conn.execute(
        "SELECT DISTINCT ticker FROM manual_fields WHERE field_name = 'fiscal_year_results'"
    ).fetchall()
    return frozenset(str(r[0]).upper() for r in rows if r and r[0])


def _consensus_flags(tickers: Iterable[str], conn: Any) -> dict[str, tuple[bool, bool | None]]:
    """ticker → (有 EPS 共識, forward EPS 為正)。取每檔最新 snapshot 的 eps 列。

    ⚠ **要求 0y 與 +1y 同時為正**（2026-09-11 改；原本是「+1y 優先、0y 兜底」）。

    事發（2026-09-10 實測 MP）：舊規則刻意優先 +1y，但 `alpha/fundamental/bridge.py` 建模的
    目標期間是「基期後一個會計年度」——對 12 月結算的公司就是 **0y**。MP 的 +1y（FY2027）
    共識 EPS 是 +0.89562，於是 gate 判「EPS 為正」並把它選為下一檔；而實際建模的 FY2026
    同期共識是 **−0.00374**，內部 GAAP EPS 推出來 −0.2685，forward_earnings_multiple
    型別上不適用，整檔只能走 Abstention（[521]）。
    **這條規則會系統性地把虧損年的檔選成「可以做」，而它存在的理由正是要避開那些檔。**

    為什麼是「兩者皆正」而不是「只讀 0y」：0y 缺值的檔不少（新上市、換會計年度），
    只讀 0y 會把它們全判成 None 而排到後面；要求兩者皆正在資料完整時等於讀 0y，
    在 0y 缺值時退回 +1y——**方向一致地偏保守**，不會把虧損年放進來。
    """
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
        near, far = vals.get("0y"), vals.get("+1y")
        present = [v for v in (near, far) if v is not None]
        # 兩者皆正才算正；任一為負就不算——虧損年不得被選成「可以做」。
        out[t] = (True, all(v > 0 for v in present) if present else None)
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

# ---------------------------------------------------------------------------
# 品質計數器（P7-b，2026-09-10）——**衝檔數最容易犧牲的東西，要自己出現**
# ---------------------------------------------------------------------------
#
# 68 檔的 blocker 完全同形，意味著最省事的做法是套同一份模板；而模板化的判斷在 readiness
# 上看起來跟真的一模一樣（ready 就是 ready）。所以「品質沒被犧牲」不能靠自律，要有數字。
#
# 印的三個數直接對應 `AGENTS.md`「隱含報酬的兩個桿」：
#   - **沒有 re-rating 證據時目標倍數預設等於校準倍數** → `multiple_contribution` 應該 ≈ 0
#   - 折價或溢價必須指得出證據 → 非零的那幾檔要點名，讓人回頭看 rationale
#   - 正負分布 → 這正是 ROADMAP 研究閉環 P0 的 goal：**「全部是負的，是方法偏空還是市場太貴」**
#     只有在這張表上答得出來。倍數貢獻接近 0 而報酬仍為負 ＝ 市場太貴；
#     負值大半來自倍數折價 ＝ 方法偏空。

#: `multiple_contribution` 小於這個絕對值就視為「目標倍數＝校準倍數」（沒有主張折溢價）。
#: **不在這裡定義**——唯一 SSOT 是 `alpha/implied_return/contracts.py`，卡片散文與本計數器
#: 必須用同一個數（2026-09-11：先前是兩份，TSM +1.7% 同時被寫成「一致」與「有折溢價主張」）。
from alpha.implied_return.contracts import MULTIPLE_NEUTRAL_TOLERANCE  # noqa: E402


@dataclass(frozen=True, slots=True)
class QualityScore:
    """已到終局那幾檔的品質分布。**不打分、不排序**——只把數字放到看得見的地方。"""

    positive: tuple[str, ...]
    negative: tuple[str, ...]
    multiple_neutral: tuple[str, ...]
    multiple_priced: tuple[tuple[str, float], ...]
    unreadable: tuple[str, ...]
    #: 倍數桿比它自己的換算殘差還小——**既不是校準也不是主張，是讀不出來**。
    #: 把它算進 `multiple_priced` 會送人去找一份不需要存在的證據（TSM +1.7% vs 殘差 2.11%）。
    multiple_in_noise: tuple[tuple[str, float, float], ...] = ()
    #: `derivation=calibrated_to_market` 但桿已經非零——**這不是主張，是校準價過期了**。
    #:
    #: 代數上校準型的桿恆等於 `calibration_price / current_price − 1`（同分母消掉），
    #: 所以它就是價格漂移、符號相反。實測（2026-09-12，13 本校準 ledger）逐檔對齊到
    #: 小數第二位：AEHR −0.93%／漂移 +0.94%、GFS −2.12%／+2.17%、HIMX −6.45%／+6.89%…
    #:
    #: ⚠ 它要的動作與 `multiple_priced` **完全不同**：主張要的是「指得出證據」，
    #: 漂移要的是「重跑一次 valuation」。混在一欄時只能取兩者的下限，也就是
    #: 送人去替十幾檔找一份依定義不存在的折溢價證據。
    multiple_drifted: tuple[tuple[str, float], ...] = ()

    @property
    def scored(self) -> int:
        return len(self.positive) + len(self.negative)


def _find_attribution(payload: Any) -> Mapping[str, Any] | None:
    """在 artifact 裡找兩欄拆解。刻意用結構搜尋而不是寫死路徑——它住在
    `view.headline.lines[*].datum.value`，而那個索引會隨呈現層調整而變。"""
    if isinstance(payload, Mapping):
        if "eps_contribution" in payload and "multiple_contribution" in payload:
            return payload
        for value in payload.values():
            found = _find_attribution(value)
            if found is not None:
                return found
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            found = _find_attribution(item)
            if found is not None:
                return found
    return None


def score_quality(artifacts: Mapping[str, Mapping[str, Any]]) -> QualityScore:
    """`{ticker: analyst view payload}` → 品質分布。讀不到就進 `unreadable`，**不當成 0**。"""
    positive: list[str] = []
    negative: list[str] = []
    neutral: list[str] = []
    priced: list[tuple[str, float]] = []
    unreadable: list[str] = []
    multiple_in_noise: list[tuple[str, float, float]] = []
    drifted: list[tuple[str, float]] = []
    for ticker in sorted(artifacts):
        payload = artifacts[ticker]
        simple = (((payload.get("overview") or {}).get("implied_return") or {}).get("simple") or {})
        value = simple.get("value") if simple.get("status") == "available" else None
        if not isinstance(value, (int, float)):
            unreadable.append(ticker)
            continue
        (positive if value > 0 else negative).append(ticker)
        attribution = _find_attribution(payload.get("view"))
        contribution = (attribution or {}).get("multiple_contribution")
        if not isinstance(contribution, (int, float)):
            continue
        # 換算殘差是這個桿的雜訊下限：桿小於它 ＝ 我們沒有主張任何東西，也沒有確認校準。
        # 三分而不是二分——二分時它只能被歸進其中一邊，而兩邊都是錯的（L12）。
        residual = (attribution or {}).get("fx_translation_delta")
        if isinstance(residual, (int, float)) and abs(contribution) < abs(residual):
            multiple_in_noise.append((ticker, float(contribution), float(residual)))
        elif abs(contribution) <= MULTIPLE_NEUTRAL_TOLERANCE:
            neutral.append(ticker)
        elif (attribution or {}).get("multiple_derivation") == "calibrated_to_market":
            # ledger 自己宣告這是校準倍數（零折溢價），而桿非零——那是**校準價過期**，
            # 不是主張。判準讀 `derivation` 而不是數值門檻：門檻調不動這件事，
            # 因為隔天開盤又會漂走（L16：分類有 SSOT 就不要在消費端重算一份）。
            drifted.append((ticker, float(contribution)))
        else:
            priced.append((ticker, float(contribution)))
    return QualityScore(tuple(positive), tuple(negative), tuple(neutral),
                        tuple(priced), tuple(unreadable), tuple(multiple_in_noise),
                        tuple(drifted))


def render_quality(score: QualityScore) -> list[str]:
    """成績單三行。**沒有到終局的檔就誠實說沒有**，不印 0/0 假裝有量測。"""
    if not score.scored and not score.unreadable:
        return ["品質計數器：尚無可評分的檔（沒有隱含報酬就沒有兩桿可看）"]
    lines = [f"隱含報酬分布：正 {len(score.positive)}／負 {len(score.negative)}"
             + (f"（讀不到 {len(score.unreadable)}：{'、'.join(score.unreadable)}）"
                if score.unreadable else "")]
    lines.append(
        f"倍數＝校準倍數（未主張折溢價）：{len(score.multiple_neutral)} 檔"
        + (f"｜有折溢價主張：{len(score.multiple_priced)} 檔——"
           + "、".join(f"{t} {c:+.1%}" for t, c in score.multiple_priced)
           + "（每一筆的 rationale 都必須指得出證據，AGENTS.md「隱含報酬的兩個桿」）"
           if score.multiple_priced else "｜有折溢價主張：0 檔"))
    if score.multiple_drifted:
        lines.append(
            f"校準倍數但校準價已過期（**不是折溢價主張，別去找證據**）：{len(score.multiple_drifted)} 檔——"
            + "、".join(f"{t} {c:+.1%}" for t, c in score.multiple_drifted)
            + "。ledger 宣告 derivation=calibrated_to_market，桿卻非零；代數上它等於"
            "（校準當天價 ÷ 現價 − 1），也就是價格漂移。要的動作是**重跑一次 valuation**，"
            "不是補一份依定義不存在的折溢價證據。")
    if score.multiple_in_noise:
        lines.append(
            f"倍數桿落在換算殘差以下（讀不出來，不是校準也不是主張）：{len(score.multiple_in_noise)} 檔——"
            + "、".join(f"{t} {c:+.1%}（殘差 {r:+.1%}）" for t, c, r in score.multiple_in_noise)
            + "。要拿到有意義的數字得用同一條 FX 路徑重算共識，不是調容差。")
    if score.negative and not score.positive and score.scored >= 3:
        lines.append(
            "⚠ 全部為負：倍數貢獻接近 0 ＝**市場太貴**；負值大半來自倍數折價 ＝**方法偏空**。"
            "在分得出這兩者之前，不要把「全負」讀成結論（ROADMAP 研究閉環 P0 的 goal）。")
    return lines

__all__ = [
    "GATE_STATES", "MULTIPLE_NEUTRAL_TOLERANCE", "NEXT_PICK_RULE", "READY_STATES",
    "deferred_tickers",
    "BacklogRow", "GateResult", "QualityScore", "closure_gate", "explain_pick",
    "rank_backlog", "render_quality", "render_summary", "row_from_artifact",
    "score_quality", "sectors_with_ready", "summarize",
]
