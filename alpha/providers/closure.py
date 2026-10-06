"""每檔閉環的 I/O 收集端（alpha/providers 是 alpha 底下唯一准碰外部世界的子套件）。

讀幾個來源，各自 fail-soft：analyst view artifact（必要）、Engine C 基期觀測（選）、structure_table state＋registry（選）、
候選板 state（選；閉環母體要的邊緣判定、持有、候選狀態）、thesis lifecycle（選）、敘事 ledger（選；短檢查日）。
⚠ 2026-10-07（Phase 7 Step 7.0g-2）：EPS 共識那一份退役（兩條 EPS 排序是 Phase 0 殭屍）；加閉環母體的取數。
純函式（終局、排序、摘要）住 `alpha/closure.py`；本檔只負責把資料送進去。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from alpha.closure import (
    BacklogRow,
    SHORT_CHECK_DAYS,
    _base_observation_tickers,
    _sector_and_structure_edge,
    deferred_tickers,
    population_for,
    row_from_artifact,
)


def collect_backlog(*, artifact_dir: Path | None = None, state_dir: Path | None = None,
            conn: Any = None) -> tuple[list[BacklogRow], list[str]]:
    """讀 artifact（必要）＋基期觀測（選）＋結構表的產業、結構邊與供貨座位（選）＋閉環母體的輸入（選）。回 (rows, notes)。"""
    from webapp.store import ArtifactStore, StateArtifactStore, resolve_state_dir

    notes: list[str] = []
    store = ArtifactStore(artifact_dir)
    rows: list[BacklogRow] = []
    for ticker, payload, _fresh, reason in store.read_all():
        if payload is None:
            notes.append(f"{ticker} artifact 壞掉：{reason}")
            continue
        rows.append(row_from_artifact(ticker, payload, today=date.today()))
    if not rows:
        return [], notes + ["尚無 materialized analyst view（python -m webapp materialize --registry-listed）"]

    # 基期觀測：Engine C。讀不到時留 None（＝「未讀到」），不是 False——False 會把整批推到最後面（L12）。
    base_obs: frozenset[str] | None = None
    try:
        if conn is None:
            from engine_c.db import get_conn

            conn = get_conn()
        base_obs = _base_observation_tickers(conn)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"Engine C 基期觀測讀不到：{type(exc).__name__}")

    # 目標期間是不是已經結束（＝財報空窗）**現在由 `row_from_artifact` 自己判**（2026-09-19）：
    # artifact 的 `headline.context.period_end` 就是那一格，而它與共識 `0y` 的期末實測
    # **73/73 相同、0 例外**。先前這裡另查一次 Engine C，等於同一個分類有兩份實作——
    # 而 APP 端拿不到這一份，於是「等財報」在 APP 變成「還沒做」（L16）。
    # ⚠ **時鐘仍然住在這一層**：`row_from_artifact` 只在收到 `today` 時才判，純函式不看時鐘。

    # 產業與結構邊：structure_table state ＋ registry ＋ config/sector_anchors.json（錨→產業的 SSOT）
    sector_edge: dict[str, tuple[str | None, bool]] = {}
    seats: frozenset[str] | None = None
    state_store = StateArtifactStore(resolve_state_dir(artifact_dir, state_dir))
    try:
        payload, _fresh = state_store.read("structure_table")
        from identity import get_registry

        sector_edge = _sector_and_structure_edge(payload, get_registry(), _anchor_to_sector())
        seats = supply_seats(payload, get_registry())
    except Exception as exc:  # noqa: BLE001
        notes.append(f"structure_table state 讀不到：{type(exc).__name__}")

    # 閉環母體的輸入（7.0g-2）：候選板（邊緣判定、持有、候選狀態）＋ thesis lifecycle。讀不到 → 該格 None → 留在母體。
    board: dict[str, dict[str, Any]] = {}
    board_day: str | None = None
    try:
        cand, _fresh = state_store.read("candidates")
        board, board_day = board_inputs(cand)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"候選板 state 讀不到，本輪閉環母體照舊（全部留在母體）：{type(exc).__name__}")
    thesis: frozenset[str] | None = None
    try:
        from engine_b.routine_config import DEFAULT_LIFECYCLE, lifecycle_tickers

        thesis = frozenset(str(x).upper() for x in lifecycle_tickers(DEFAULT_LIFECYCLE))
    except Exception as exc:  # noqa: BLE001
        notes.append(f"thesis lifecycle 讀不到：{type(exc).__name__}")
    today = date.today()

    # pq2 的使用者 defer：讀結構化欄位，讀不到就是空集合（不猜、不 parse 標題）
    deferred: frozenset[str] = frozenset()
    try:
        from engine_b.todo import load as load_pool
        from identity import get_registry

        registry = get_registry()

        def _resolve(company_id: str) -> str | None:
            try:
                return getattr(registry.company(company_id), "research_ticker", None)
            except Exception:  # noqa: BLE001
                return None

        deferred = deferred_tickers(load_pool(), _resolve)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"pq2 待辦池讀不到，本輪不套「使用者已 defer」：{type(exc).__name__}")

    enriched: list[BacklogRow] = []
    for r in rows:
        awaiting = r.awaiting_report_since      # 已由 row_from_artifact 判好，這裡只照抄
        sector, has_edge = sector_edge.get(r.ticker.upper(), (None, (False if sector_edge else None)))
        info = board.get(r.ticker.upper()) or {}
        population, code = population_for(
            held=info.get("held") if board else None,
            has_thesis=(None if thesis is None else r.ticker.upper() in thesis),
            candidate_state=info.get("candidate_state"),
            edge_state=info.get("edge_state"),
            has_seat=(None if seats is None else r.ticker.upper() in seats))
        reason, due = population_detail(population, code, info, board_day=board_day,
                                        last_brief=_last_brief_day(r.ticker) if population == "edge_no_seat" else None,
                                        today=today)
        enriched.append(BacklogRow(
            ticker=r.ticker, readiness=r.readiness, open_panels=r.open_panels, settled_panels=r.settled_panels,
            absence_kinds=r.absence_kinds,
            sector=sector, has_structure_edge=has_edge,
            has_base_observation=(None if base_obs is None else r.ticker.upper() in base_obs),
            user_deferred=r.ticker.upper() in deferred,
            awaiting_report_since=awaiting,
            generated_at=r.generated_at,
            population=population, population_reason=reason, short_check_due=due,
        ))
    return enriched, notes


def supply_seats(structure_payload: Any, registry: Any) -> frozenset[str]:
    """結構表上**供給側**有座位的 research ticker：`relation == "supplies_to"` 的列（7.0g-2）。

    `depends_on`／`constrained_by` 是買方那一側，不算座位；`develops`／`invests_in` 結構表本來就不收
    （只有開發中或只有投資邊的公司會落到「邊緣沒座位」，由短檢查分辨，plan §6b 的 L11-6 ④）。
    """
    out: set[str] = set()
    for row in (structure_payload or {}).get("rows") or ():
        if row.get("relation") != "supplies_to":
            continue
        ticker = registry.research_ticker(str(row.get("company_id") or ""))
        if ticker:
            out.add(str(ticker).upper())
    return frozenset(out)


def board_inputs(candidates_payload: Any) -> tuple[dict[str, dict[str, Any]], str | None]:
    """候選板 artifact → `{ticker: {held, candidate_state, edge_state, edge}}`（7.0g-2）。**照抄 artifact，不重算**（L16）。

    候選狀態取列所在的組（open／missing／priced_wait／pass／held）；附組（例：邊緣量不到）的列取它宣告的狀態。
    沒有敘事那幾檔（`no_narrative`）只有邊緣判定。
    """
    payload = candidates_payload or {}
    out: dict[str, dict[str, Any]] = {}

    def _put(row: Any, group: str | None) -> None:
        ticker = str(row.get("ticker") or "").upper()
        if not ticker:
            return
        edge = row.get("edge") if isinstance(row.get("edge"), dict) else None
        entry = out.setdefault(ticker, {"held": False, "candidate_state": None, "edge_state": None, "edge": None})
        if group == "held":
            entry["held"] = True
        state = group if group not in (None, "held") else row.get("declared")
        if state and not entry["candidate_state"]:
            entry["candidate_state"] = state
        if edge is not None:
            entry["edge"], entry["edge_state"] = edge, edge.get("state")

    for group, rows_ in (payload.get("groups") or {}).items():
        for row in rows_ or ():
            _put(row, str(group))
    for rows_ in (payload.get("side_groups") or {}).values():
        for row in rows_ or ():
            _put(row, None)
    for row in payload.get("no_narrative") or ():
        _put(row, None)
    return out, (str(payload.get("today")) if payload.get("today") else None)


def population_detail(population: str, code: str, info: Any, *, board_day: str | None,
                      last_brief: date | None, today: date) -> tuple[str | None, bool | None]:
    """→ (逐檔列名用的理由, 短檢查是否到期)。時鐘住這一層（`alpha/closure.py` 無時鐘）。"""
    if population == "non_multiple":
        edge = (info or {}).get("edge") or {}
        cap = edge.get("market_cap_label") or "市值未知"
        cov = edge.get("analyst_count")
        return f"非邊緣：{cap}、分析師 {cov if cov is not None else '未知'} 位（判定 {board_day or '日期未知'}）", None
    if population == "edge_no_seat":
        if last_brief is None:
            return "從沒做過短檢查", True
        age = (today - last_brief).days
        due = age > SHORT_CHECK_DAYS
        nxt = date.fromordinal(last_brief.toordinal() + SHORT_CHECK_DAYS).isoformat()
        return (f"上次短檢查 {last_brief.isoformat()}（已過 {age} 天，到期重問）" if due
                else f"上次短檢查 {last_brief.isoformat()}，{nxt} 重問"), due
    return None, None


def _last_brief_day(ticker: str) -> date | None:
    """這一檔最新一份 v2 敘事的寫入日（短檢查的完成證據）。讀不到回 None＝當作沒查過（寧可多排一檔，INV-3）。"""
    try:
        from alpha.narrative.contracts import RECORD_VERSION_V2
        from alpha.providers import briefs as briefs_provider

        records, _errors = briefs_provider.read_brief_records(ticker)
    except Exception:  # noqa: BLE001
        return None
    days: list[date] = []
    for rec in records:
        if getattr(rec, "record_version", None) != RECORD_VERSION_V2:
            continue
        raw = str(getattr(rec, "created_at", "") or "")[:10]
        try:
            days.append(date.fromisoformat(raw))
        except ValueError:
            continue
    return max(days) if days else None



def _anchor_to_sector() -> dict[str, str]:
    """錨→產業對照。SSOT 是 `config/sector_anchors.json`；讀不到就回空（全部落入「產業未知」，不猜）。"""
    import json

    path = Path(__file__).resolve().parents[2] / "config" / "sector_anchors.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(anchor): str(sector)
            for sector, anchors in (data.get("sectors") or {}).items()
            for anchor in (anchors or [])}


__all__ = ["collect_backlog"]
