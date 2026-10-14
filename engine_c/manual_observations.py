"""Append-only Engine C manual observations and rebuildable projection。"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date, datetime, time, timezone
from typing import Any, Mapping

from shared.redaction import sensitive_payload_path

_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _is_sqlite(conn: Any) -> bool:
    return isinstance(conn, sqlite3.Connection)


def normalize_as_of(value: str) -> str:
    """把 as_of 正規化成 UTC ISO-8601；這是 as_of 形式的唯一權威。

    刻意分開兩種輸入：純日期（財報／財季結束日就是這樣揭露的，日內時刻沒有意義）
    補該日 UTC 午夜；帶時刻但沒有時區的字串仍然拒絕——那是「寫了時刻卻沒說哪個
    時區」，替它猜一個等於製造無聲的偏移。

    提案層必須 import 本函式而不是自己複製規則：2026-08-14 的 LITE 客戶集中度
    提案就是因為兩端各有一套 as_of 契約，提案建立成功、進池取得編號、使用者核准
    完成，卻在最後一刻寫入 ledger 時才失敗。
    """

    text = str(value).strip()
    if _DATE_ONLY.match(text):
        return datetime.combine(
            date.fromisoformat(text), time.min, tzinfo=timezone.utc
        ).isoformat()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(
            "manual observation as_of must be an ISO-8601 date or timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise ValueError("manual observation as_of must include timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def ensure_manual_observation_schema(conn: Any) -> None:
    """Bootstrap SQLite; Postgres schema is owned by versioned migrations。"""

    if not _is_sqlite(conn):
        return
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS manual_observations (
            observation_id TEXT PRIMARY KEY,
            ticker         TEXT NOT NULL,
            field_name     TEXT NOT NULL,
            value          TEXT NOT NULL,
            source_ref     TEXT NOT NULL,
            as_of          TEXT NOT NULL,
            author         TEXT NOT NULL,
            supersedes_id  TEXT REFERENCES manual_observations(observation_id),
            recorded_at    TEXT NOT NULL DEFAULT (datetime('now')),
            payload_digest TEXT NOT NULL UNIQUE
        );
        CREATE INDEX IF NOT EXISTS idx_manual_observation_field_time
            ON manual_observations (ticker, field_name, as_of, observation_id);
        CREATE TABLE IF NOT EXISTS manual_observation_relations (
            relation_id    TEXT PRIMARY KEY,
            observation_id TEXT NOT NULL REFERENCES manual_observations(observation_id),
            target_id      TEXT NOT NULL REFERENCES manual_observations(observation_id),
            relation       TEXT NOT NULL CHECK (relation IN ('supersedes', 'parallel')),
            reason         TEXT NOT NULL,
            author         TEXT NOT NULL,
            approval_ref   TEXT,
            recorded_at    TEXT NOT NULL DEFAULT (datetime('now')),
            payload_digest TEXT NOT NULL UNIQUE,
            CHECK (observation_id <> target_id)
        );
        CREATE INDEX IF NOT EXISTS idx_manual_observation_relations_target
            ON manual_observation_relations (target_id);
        """
    )


# ---------------------------------------------------------------------------
# 取代關係與「哪幾筆生效」（2026-10-14 取代鏈 A；ROADMAP「人工觀測的取代鏈收多值」，使用者選 A）
# ---------------------------------------------------------------------------

#: 兩筆人工觀測之間的關係（封閉字彙）。`supersedes`＝這一筆讓目標不再生效——**一筆可以關掉多筆**：`supersedes_id` 是單值
#: 而且帶 FK，兩條互不相干的鏈在那個欄位上合併不了（2026-09-13 實測 14 組）。`parallel`＝兩筆都算數的刻意並存
#: （例：TSM 同一年的台幣報表與 20-F 美元換算）——以前 `allow_parallel` 不留紀錄，讀取端分不出刻意並存與重複。
#: 只能 append（L10 不適用於 private append-only authority）；既有列一個欄位都不改。
RELATIONS: tuple[str, ...] = ("supersedes", "parallel")
MIN_RELATION_REASON_CHARS = 10


class RelationError(ValueError):
    """取代／並存關係不合法（不存在的列、跨欄位、目標已失效、判斷欄位沒有核准收據……）。"""


def _relation_rows(conn: Any, *, recorded_by: str | None = None) -> list[tuple[str, str, str]]:
    """`(observation_id, target_id, relation)`；表還不存在＝沒有任何關係。`recorded_by`（YYYY-MM-DD）：只看那天以前記錄的。"""
    try:
        rows = conn.execute(
            "SELECT observation_id, target_id, relation, recorded_at FROM manual_observation_relations").fetchall()
    except Exception:                                  # noqa: BLE001 — 表還不存在（舊庫、唯讀庫）時當成沒有
        return []
    return [(str(o), str(t), str(r)) for o, t, r, at in rows if recorded_by is None or str(at)[:10] <= recorded_by]


def live_rows(conn: Any, *, ticker: str | None = None, field_names: Any = None,
              recorded_by: str | None = None) -> list[dict[str, Any]]:
    """生效的人工觀測列——**「哪幾筆生效」的唯一規則**（L16：三題、會不會死、營收結構、基期、APP 計數器都從這裡取，不各自算）。

    一列不再生效＝被某一筆的 `supersedes_id` 指到，或被一筆 `supersedes` 關係指到。`recorded_by`（YYYY-MM-DD）＝as-of：只看
    那天以前**記錄**的列與關係（記錄日是我們確定知道的那天；T 以後才寫的更正在 T 時還不算數，INV-6）。表還不存在＝空。"""
    sql = ("SELECT observation_id, ticker, field_name, value, source_ref, as_of, recorded_at, supersedes_id, author "
           "FROM manual_observations")
    where: list[str] = []
    params: list[Any] = []
    if ticker:
        where.append("ticker = ?")
        params.append(str(ticker).upper().strip())
    names = [str(f).strip() for f in (field_names or ())]
    if names:
        where.append(f"field_name IN ({','.join('?' for _ in names)})")
        params.extend(names)
    try:
        raw = conn.execute(sql + (" WHERE " + " AND ".join(where) if where else ""), params).fetchall()
    except Exception:                                  # noqa: BLE001 — 表還不存在時當成沒有
        return []
    keys = ("observation_id", "ticker", "field_name", "value", "source_ref", "as_of", "recorded_at", "supersedes_id",
            "author")
    rows = [dict(zip(keys, r)) for r in raw]
    if recorded_by is not None:
        rows = [r for r in rows if str(r["recorded_at"])[:10] <= recorded_by]
    dead = {str(r["supersedes_id"]) for r in rows if r["supersedes_id"]}
    dead |= {target for _obs, target, relation in _relation_rows(conn, recorded_by=recorded_by) if relation == "supersedes"}
    return [r for r in rows if str(r["observation_id"]) not in dead]


def relation_map(conn: Any, *, relation: str = "supersedes", recorded_by: str | None = None) -> dict[str, list[str]]:
    """`{這一筆: [它關掉（或並存）的那幾筆]}`——只含取代關係表；`supersedes_id` 欄位的單值鏈由呼叫端自己帶著。
    給要走祖先鏈的讀取端用（基期的「已被 X 取代」引用、變更偵測的前一版）。"""
    out: dict[str, list[str]] = {}
    for obs, target, kind in _relation_rows(conn, recorded_by=recorded_by):
        if kind == relation:
            out.setdefault(obs, []).append(target)
    return {k: sorted(v) for k, v in out.items()}


def parallel_components(conn: Any, *, recorded_by: str | None = None) -> list[frozenset[str]]:
    """`parallel` 關係連起來的幾群 observation_id（刻意並存的那幾組）。"""
    neighbours: dict[str, set[str]] = {}
    for obs, target, relation in _relation_rows(conn, recorded_by=recorded_by):
        if relation == "parallel":
            neighbours.setdefault(obs, set()).add(target)
            neighbours.setdefault(target, set()).add(obs)
    seen: set[str] = set()
    out: list[frozenset[str]] = []
    for start in sorted(neighbours):
        if start in seen:
            continue
        group, stack = set(), [start]
        while stack:
            node = stack.pop()
            if node in group:
                continue
            group.add(node)
            stack.extend(neighbours.get(node, ()))
        seen |= group
        out.append(frozenset(group))
    return out


def declared_parallel(conn: Any, ids: Any, *, recorded_by: str | None = None) -> bool:
    """這幾筆（≥2）是不是**全部**在同一群登記過的刻意並存裡。"""
    wanted = {str(i) for i in ids}
    return len(wanted) > 1 and any(wanted <= group for group in parallel_components(conn, recorded_by=recorded_by))


def live_groups(conn: Any, *, recorded_by: str | None = None) -> dict[tuple[str, str, str], list[str]]:
    """全庫 `{(ticker, field_name, as_of 那一天): [生效 observation_id]}`。⚠ as_of 一定要在鍵裡：同一欄位的不同期間本來就該
    同時生效（2026-09-13 第一版漏掉它，把 7 組不同期間誤報成重複）。"""
    groups: dict[tuple[str, str, str], list[str]] = {}
    for r in live_rows(conn, recorded_by=recorded_by):
        groups.setdefault((str(r["ticker"]), str(r["field_name"]), str(r["as_of"])[:10]), []).append(str(r["observation_id"]))
    return {k: sorted(v) for k, v in groups.items()}


def duplicate_live_groups(conn: Any, *, recorded_by: str | None = None) -> dict[tuple[str, str, str], list[str]]:
    """同一期間多於一筆生效、**而且不是登記過的刻意並存**的那幾組（常駐計數器的母體）。"""
    return {key: ids for key, ids in live_groups(conn, recorded_by=recorded_by).items()
            if len(ids) > 1 and not declared_parallel(conn, ids, recorded_by=recorded_by)}


def _numeric_leaves(payload: Any) -> int:
    """JSON 裡有幾個可比對的數值葉節點（bool 不算）。"""
    if isinstance(payload, bool):
        return 0
    if isinstance(payload, (int, float)):
        return 1
    if isinstance(payload, Mapping):
        return sum(_numeric_leaves(v) for v in payload.values())
    if isinstance(payload, (list, tuple)):
        return sum(_numeric_leaves(v) for v in payload)
    return 0


_SHARE_FIELDS = ("segment_revenue_share", "product_line_revenue_share")


def _require_machine_comparable_if_mechanical(field_name: str, value: str) -> None:
    """`verifiability=mechanical` 的欄位，value 必須是可機械比對的 JSON 數值。

    ## 為什麼這條存在

    2026-09-04 使用者定案：Engine C 人工 ledger 的 pq2 gate 改成按「**可不可以確定性
    重導**」分，不再按「存哪張表」分。`mechanical` 欄位因此**不再需要人工核准**。

    這一條就是拿掉那道人工閘門的**補償控制**。`mechanical` 的定義是「任何人重讀同
    一份文件都得到同一個數」，而**散文無法被 diff**——把它存成散文等於宣稱這筆可以
    被核對，卻讓任何人都核不了。放行與收緊必須同時發生（L15：分開之後兩邊都要更嚴；
    L14 第 3 點：先量測後放閘，不得拆煞車而不裝儀表板）。

    ⚠ **刻意不驗 `source_ref` 的格式。** 現有 85 筆橫跨 SEC／AMF／HKEX／ASX／TDnet
    五種轄區、五種寫法（`EDGAR 0001654954-26-006919`、`AMF 2026-06-10 notes 9.1/8.14`、
    `HKEX 2023033100951.pdf`…）。用 regex 驗只會攔下格式而不是風險，而且會擋掉完全
    合法的法國 URD 引用——那正是 L15 記過的坑。provenance 仍然必填。
    """
    from engine_c.observation_fields import get_observation_field_registry

    spec = get_observation_field_registry().get(field_name)
    if spec is None or spec.requires_user_approval:
        return
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} 是 verifiability=mechanical 欄位，value 必須是 JSON——"
            "散文無法被未來的重導 diff，等於宣稱可核對卻沒人核得了"
        ) from None
    if _numeric_leaves(payload) == 0:
        raise ValueError(
            f"{field_name} 是 verifiability=mechanical 欄位，value 至少要有一個數值——"
            "沒有數字就沒有可比對的東西"
        )
    # 占比欄位：頂層每個數值鍵都會被讀成一個分部的占比（alpha/providers/fundamentals.py `_segment_revenue_share`），
    # 所以契約寫的「0..1 的小數」要在這裡擋。2026-10-05：42 筆裡 11 筆把總額寫成頂層數值（total_usd 等）。
    if field_name in _SHARE_FIELDS and isinstance(payload, Mapping):
        out = sorted(str(k) for k, v in payload.items()
                     if isinstance(v, (int, float)) and not isinstance(v, bool) and not -1.0 <= v <= 1.0)
        if out:
            raise ValueError(
                f"{field_name} 的頂層數值必須是佔總營收的比例（-1..1；負值只給抵減行）——{out} 超出範圍。"
                "總額或金額請放進一個物件（例 \"_amounts\": {…}）：頂層的每個數值鍵都會被讀成一個分部的占比"
            )


#: 損益恆等式的相對容差。表上的數字是四捨五入後的百萬／千元，所以不能要求完全相等；
#: 0.5% 足以吃掉捨入，又遠小於「符號搞反」造成的偏差（符號錯 ＝ 2×利息項）。
_PNL_IDENTITY_TOLERANCE = 0.005


def _require_pnl_sign_convention(field_name: str, value: str) -> None:
    """`fiscal_year_results` 的 `interest_and_other_net` 必須用「正值＝費用」的符號。

    ## 為什麼需要機械檢查而不是一句註解

    同一個欄位名在兩個相鄰的 ledger 裡有相反的符號慣例：損益表**印出來**的
    `Other income (expense), net` 正值是**收益**，而 `ASSUMPTION_DRIVERS` 的
    `interest_and_other_net` 契約寫的是**正值＝費用**（橋算的是
    `pretax = operating_income − interest_and_other_net`）。

    2026-09-12 實測：LRCX 的基期觀測照抄損益表符號填 `+62,678,000`（實際是收益），
    再沿用到假設，結果橋算出內部稀釋 EPS 9.38 而不是校準目標 9.469——**差 0.94%，
    而且沒有任何東西會報錯**。只有先算出期望值再去對，才抓得到（L17：不會壞、不會
    報錯、測試不會紅，只會安靜地偏）。

    檢查方式是恆等式而不是符號規則本身：同一個 basis 區塊裡若三個數都在，就必須滿足
    `operating_income − interest_and_other_net ≈ pretax_income`。符號填反時這條會差
    兩倍的利息項，一定攔得到；而恆等式同時也攔得到單純抄錯數字。
    """

    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return  # JSON 合法性由 _require_machine_comparable_if_mechanical 負責
    if field_name != "fiscal_year_results" or not isinstance(payload, Mapping):
        return
    for basis in ("gaap", "non_gaap"):
        block = payload.get(basis)
        if not isinstance(block, Mapping):
            continue
        try:
            operating = float(block["operating_income"])
            interest = float(block["interest_and_other_net"])
            pretax = float(block["pretax_income"])
        except (KeyError, TypeError, ValueError):
            continue  # 三個數沒有到齊就沒有恆等式可驗——不猜
        implied = operating - interest
        scale = max(abs(pretax), abs(operating), 1.0)
        if abs(implied - pretax) / scale <= _PNL_IDENTITY_TOLERANCE:
            continue
        raise ValueError(
            f"fiscal_year_results.{basis} 的損益恆等式不成立："
            f"operating_income({operating:,.0f}) − interest_and_other_net({interest:,.0f})"
            f" = {implied:,.0f}，但 pretax_income 是 {pretax:,.0f}。"
            "最常見的成因是 interest_and_other_net 的符號——本欄位與 ASSUMPTION_DRIVERS "
            "同慣例：**正值＝費用**，所以損益表上印成收益的 "
            f"`Other income (expense), net` 要寫成 {-interest:,.0f}。"
        )


#: `going_concern_opinion` 的判讀封閉字彙（Phase 3 Step 3.2，使用者 2026-09-26 定案 #6）。
#: `not_reviewed` 是「讀過目錄、刻意記下還沒讀查核意見」——與「沒有紀錄」不同形（燈都是灰，但理由不同）。
GOING_CONCERN_OPINIONS: tuple[str, ...] = ("substantial_doubt", "no_substantial_doubt", "not_reviewed")
_GOING_CONCERN_KEYS = frozenset({"opinion", "quote", "page", "report_date"})


def _validate_going_concern_opinion(value: str) -> None:
    """`{opinion, quote, page, report_date}`；判讀了（非 not_reviewed）就必須帶逐字、頁碼與查核報告日。"""
    try:
        payload = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"going_concern_opinion.value 必須是 JSON 物件：{exc}") from None
    if not isinstance(payload, Mapping):
        raise ValueError("going_concern_opinion.value 必須是 JSON 物件")
    unknown = sorted(set(payload) - _GOING_CONCERN_KEYS)
    if unknown:
        raise ValueError(f"going_concern_opinion.value 有未登記的鍵 {unknown}；只收 {sorted(_GOING_CONCERN_KEYS)}")
    opinion = payload.get("opinion")
    if opinion not in GOING_CONCERN_OPINIONS:
        raise ValueError(f"going_concern_opinion.opinion 必須是 {GOING_CONCERN_OPINIONS} 之一，收到 {opinion!r}")
    if opinion == "not_reviewed":
        return
    quote = payload.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("going_concern_opinion 判讀了就必須帶 quote（查核意見的逐字原文）——措辭精度本身是 claim（L11-1）")
    page = payload.get("page")
    if page is None or isinstance(page, bool) or not str(page).strip():
        raise ValueError("going_concern_opinion 判讀了就必須帶 page（頁碼或段落定位）——逐字要指得回原文（L18）")
    report_date = payload.get("report_date")
    if not isinstance(report_date, str) or not _DATE_ONLY.match(report_date.strip()):
        raise ValueError("going_concern_opinion.report_date 必須是 YYYY-MM-DD（查核報告日期）")
    try:
        date.fromisoformat(report_date.strip())
    except ValueError as exc:
        raise ValueError(f"going_concern_opinion.report_date 不是合法日期：{exc}") from None


#: 欄位值的形狀驗證（封閉表）。**提案層（`pending_observations.propose`，發編號之前）與 ledger 寫入層
#: （`append_manual_observation`）都呼叫 `validate_field_value`**——只在 ledger 端驗，錯誤會遲到使用者核准
#: 之後才出現（2026-08-14 LITE 事故）。沒登記的欄位不驗形狀（照舊）。
_FIELD_VALUE_VALIDATORS = {"going_concern_opinion": _validate_going_concern_opinion}


def validate_field_value(field_name: str, value: str) -> None:
    """欄位有登記形狀就驗；不合法 raise `ValueError`。"""
    validator = _FIELD_VALUE_VALIDATORS.get(str(field_name).strip())
    if validator is not None:
        validator(value)


def live_observation_ids(conn: Any, ticker: str, field_name: str, as_of: str, *,
                         recorded_by: str | None = None) -> list[str]:
    """這個 (ticker, field_name, as_of) 目前有幾筆「生效」紀錄——規則住 `live_rows`（`supersedes_id` 與取代關係都沒指到的那些）。

    ⚠ **`as_of` 一定要在鍵裡**：同一個欄位的不同期間本來就該同時生效
    （`fiscal_year_results` 的 FY2024 與 FY2025 是兩筆不同的事實，讀取端按 as_of 取最新）。
    把它漏掉會把「不同期間」誤判成「重複」——2026-09-13 第一版就是這樣，
    實測 21 組「重複」裡有 7 組其實只是不同期間。

    ⚠ 為什麼會有多於一筆：`supersedes_id` 是**單值**欄位（而且帶 FK），所以一筆新紀錄只能
    關掉一條 supersession 鏈。實際發生的模式是「先有一筆最小組合（例 `xbrl_backfill` 只寫
    revenue 與 operating_income），之後有人寫一筆完整的但沒有指向它」——
    於是同一個 (ticker, field) 有兩條互不相干的鏈，**單靠 `supersedes_id` 合併不了**。
    2026-09-13 實測全庫（鍵含 as_of）：**14 組**有多於一筆生效，其中 `fiscal_year_results` **8 檔**
    （`xbrl_backfill` 先寫最小組合、之後有人寫完整版但沒指向它），其餘 6 組散在 5 個欄位。
    2026-10-14 起由取代關係（`manual_observation_relations`，一筆可以關掉多筆）合併——`append_relation`。
    """
    day = str(as_of)[:10]
    return sorted(str(r["observation_id"]) for r in live_rows(conn, ticker=ticker, field_names=[field_name],
                                                                 recorded_by=recorded_by)
                  if str(r["as_of"])[:10] == day)


_WINNER_SQL = """
    SELECT ticker, field_name, value, source_ref, as_of
    FROM manual_observations
    WHERE ticker = {ph} AND field_name = {ph}
      AND observation_id NOT IN (SELECT supersedes_id FROM manual_observations WHERE supersedes_id IS NOT NULL)
      AND observation_id NOT IN (SELECT target_id FROM manual_observation_relations WHERE relation = 'supersedes')
    ORDER BY as_of DESC, recorded_at DESC, observation_id DESC
    LIMIT 1
"""


def _refresh_projection(conn: Any, ticker: str, field_name: str) -> None:
    """`manual_fields` 投影的勝出者＝**生效列**裡最新的一筆（as_of、記錄時間）。2026-10-14 以前它不看取代鏈：
    取代關係讓較早記錄的那筆成為生效列時（例：AXTI runway 的閘門測試列晚一天寫），投影會留著被取代的那一筆。"""
    if _is_sqlite(conn):
        winner = conn.execute(_WINNER_SQL.format(ph="?"), (ticker, field_name)).fetchone()
        if winner is None:
            conn.execute("DELETE FROM manual_fields WHERE ticker = ? AND field_name = ?", (ticker, field_name))
            return
        conn.execute(
            """
            INSERT INTO manual_fields (ticker, field_name, value, source_note, updated_at) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ticker, field_name) DO UPDATE SET
                value=excluded.value, source_note=excluded.source_note, updated_at=excluded.updated_at
            """, tuple(winner))
        return
    with conn.cursor() as cursor:
        cursor.execute(_WINNER_SQL.format(ph="%s"), (ticker, field_name))
        winner = cursor.fetchone()
        if winner is None:
            cursor.execute("DELETE FROM manual_fields WHERE ticker = %s AND field_name = %s", (ticker, field_name))
            return
        cursor.execute(
            """
            INSERT INTO manual_fields (ticker, field_name, value, source_note, updated_at) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(ticker, field_name) DO UPDATE SET
                value=EXCLUDED.value, source_note=EXCLUDED.source_note, updated_at=EXCLUDED.updated_at
            """, tuple(winner))


def is_judgment_field(field_name: str) -> bool:
    """這個欄位的寫入要不要過 Engine C 判讀寫入 gate（未登記的一律當判斷，AGENTS「未宣告一律當 judgment」）。"""
    from engine_c.observation_fields import get_observation_field_registry

    spec = get_observation_field_registry().get(field_name)
    return spec is None or bool(spec.requires_user_approval)


def check_relation(
    conn: Any,
    *,
    observation_id: str,
    target_ids: Any,
    relation: str,
    reason: str,
    author: str,
    approval_ref: str | None = None,
    require_approval: bool = True,
) -> tuple[str, str, list[str]]:
    """取代／並存關係寫得進去嗎——寫入端與提案層（發 pq2 編號之前）同一套檢查。回傳 (ticker, field_name, 目標們)。

    拒收（`RelationError`）：①關係不在字彙裡、理由太短、沒有作者；②任何一端不存在、兩端不是同一個 ticker 與欄位、
    自己指自己；③兩端現在都要生效——取代一筆已失效的會讓取代鏈分岔、讓已失效的那筆去取代別人是讓它復活；
    ④`require_approval` 時，**判斷欄位要有核准收據**（`approval_ref`：只有 `engine_b.todo complete-observation`
    在使用者 go 之後帶得出來；mechanical 欄位不需要）。"""
    if relation not in RELATIONS:
        raise RelationError(f"relation 未登記：{relation!r}（可用：{RELATIONS}）")
    reason, author = str(reason or "").strip(), str(author or "").strip()
    if len(reason) < MIN_RELATION_REASON_CHARS:
        raise RelationError(f"reason 至少 {MIN_RELATION_REASON_CHARS} 字：為什麼這一筆取代（或與）那一筆並存")
    if not author:
        raise RelationError("author 必填")
    targets = [str(t).strip() for t in (target_ids or ()) if str(t).strip()]
    if not targets:
        raise RelationError("至少要一個目標")
    if str(observation_id) in targets or len(set(targets)) != len(targets):
        raise RelationError("目標不得包含自己、也不得重複")
    if not _is_sqlite(conn):
        raise RelationError("Postgres 後端的取代關係寫入還沒接（runtime 是 SQLite；migration 已備好表）")
    ids = [str(observation_id), *targets]
    found = {str(r[0]): r for r in conn.execute(
        f"SELECT observation_id, ticker, field_name FROM manual_observations WHERE observation_id IN "
        f"({','.join('?' for _ in ids)})", ids).fetchall()}
    missing = [i for i in ids if i not in found]
    if missing:
        raise RelationError(f"ledger 裡沒有：{missing}")
    ticker, field_name = str(found[str(observation_id)][1]), str(found[str(observation_id)][2])
    off = [i for i in targets if (str(found[i][1]), str(found[i][2])) != (ticker, field_name)]
    if off:
        raise RelationError(f"目標 {off} 不是 {ticker}／{field_name}——取代與並存只在同一家公司同一個欄位之內")
    if require_approval and is_judgment_field(field_name) and not str(approval_ref or "").strip():
        raise RelationError(f"{field_name} 是判斷欄位（或未登記）：取代關係要走 pq2——"
                            "`python -m engine_c.observation_relations add …` 只建提案，使用者 go 之後由 "
                            "`python -m engine_b.todo complete-observation <編號>` 寫入")
    live = {str(r["observation_id"]) for r in live_rows(conn, ticker=ticker, field_names=[field_name])}
    dead = [i for i in ids if i not in live]
    if dead:
        raise RelationError(f"{dead} 現在已經不生效——取代或並存只在生效的列之間（否則取代鏈會分岔，或讓失效的那筆復活）")
    return ticker, field_name, sorted(targets)


def _relation_payload(observation_id: str, target: str, relation: str, reason: str, author: str,
                      approval_ref: str | None) -> tuple[str, str, dict[str, Any]]:
    payload = {"observation_id": str(observation_id), "target_id": str(target), "relation": relation,
               "reason": str(reason or "").strip(), "author": str(author or "").strip(),
               "approval_ref": str(approval_ref).strip() if approval_ref else None}
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return "mr_" + digest[:32], digest, payload


def _existing_relation_ids(conn: Any, *, observation_id: str, target_ids: Any, relation: str, reason: str,
                           author: str, approval_ref: str | None) -> list[str] | None:
    """這一組關係是不是**每一筆**都已經寫過（同內容）——是就回原本的 id，否則 None。"""
    targets = sorted(str(t).strip() for t in (target_ids or ()) if str(t).strip())
    if not targets:
        return None
    wanted = [_relation_payload(observation_id, t, relation, reason, author, approval_ref) for t in targets]
    try:
        found = {str(r[0]) for r in conn.execute(
            f"SELECT payload_digest FROM manual_observation_relations WHERE payload_digest IN "
            f"({','.join('?' for _ in wanted)})", [digest for _rid, digest, _p in wanted]).fetchall()}
    except Exception:                                  # noqa: BLE001 — 表還不存在＝沒寫過
        return None
    return [rid for rid, _d, _p in wanted] if all(digest in found for _rid, digest, _p in wanted) else None


def append_relation(
    conn: Any,
    *,
    observation_id: str,
    target_ids: Any,
    relation: str,
    reason: str,
    author: str,
    approval_ref: str | None = None,
    commit: bool = True,
) -> list[str]:
    """寫入取代／並存關係（append-only、冪等：同內容重寫不長第二列）。回傳 relation_id（每個目標一列）。
    檢查全在 `check_relation`（一筆都不合法就一筆都不寫）；寫完重建那個 (ticker, 欄位) 的投影。"""
    ensure_manual_observation_schema(conn)
    # 冪等：完全相同的關係已經寫過就照回原本的 id——不能讓「目標已經不生效」把重跑擋下來（第一次寫完它本來就失效了）
    previous = _existing_relation_ids(conn, observation_id=observation_id, target_ids=target_ids, relation=relation,
                                      reason=reason, author=author, approval_ref=approval_ref)
    if previous is not None:
        return previous
    ticker, field_name, targets = check_relation(
        conn, observation_id=observation_id, target_ids=target_ids, relation=relation, reason=reason, author=author,
        approval_ref=approval_ref, require_approval=True)
    reason, author = str(reason).strip(), str(author).strip()
    out: list[str] = []
    try:
        for target in targets:
            relation_id, digest, payload = _relation_payload(observation_id, target, relation, reason, author, approval_ref)
            conn.execute(
                "INSERT OR IGNORE INTO manual_observation_relations (relation_id, observation_id, target_id, relation, "
                "reason, author, approval_ref, payload_digest) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (relation_id, payload["observation_id"], target, relation, reason, author, payload["approval_ref"], digest))
            out.append(relation_id)
        _refresh_projection(conn, ticker, field_name)
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    return out


def _reject_unlinked_duplicate(
    conn: Any, ticker: str, field_name: str, as_of: str, supersedes_id: str | None,
    allow_parallel: bool, *, observation_id: str,
) -> None:
    """已經有生效紀錄時，**新的一筆必須說出它跟舊的是什麼關係**（2026-09-13）。

    三種合法關係，二擇一必須明示：
    - `supersedes_id=<舊 id>`：這是更正，舊的不再生效。
    - `allow_parallel=True`：這是**並存**的另一筆觀測（不同來源／不同口徑，兩筆都算數）。
    - 舊的那一筆已經被 supersede（＝現在沒有生效紀錄）：直接寫。

    ⚠ **不給預設**：先前「多寫一筆」永遠成功，而讀取端靠 `ORDER BY as_of DESC, recorded_at DESC`
    取第一筆——**那是排序的副作用，不是宣告**（L17-3②：這個欄位是覆蓋還是聯集，
    覆蓋掉的那份還有第二個地方留著嗎）。
    """
    if allow_parallel:
        return
    live = live_observation_ids(conn, ticker, field_name, as_of)
    if not live:
        return
    if observation_id in live:
        return                      # 同一筆重寫（content-addressed id 相同）＝冪等，不是重複
    if supersedes_id and str(supersedes_id) in live:
        return
    raise ValueError(
        f"{ticker} 的 {field_name} @ {str(as_of)[:10]} 已經有 {len(live)} 筆生效紀錄"
        f"（{'、'.join(live)}），"
        "而本次沒有說出新紀錄與它們的關係。"
        "二擇一：①`--supersedes <舊 id>`（這是更正，舊的不再生效）；"
        "②明示 `allow_parallel=True`（這是並存的另一筆觀測，兩筆都算數）。"
        "⚠ **不給預設是刻意的**：`supersedes_id` 是單值欄位，"
        "一旦長出兩條互不相干的鏈就要另外寫取代關係才合併得了"
        "（`python -m engine_c.observation_relations add`；判斷欄位走 pq2），"
        "而讀取端不猜哪一筆算數——猜不是宣告。"
        + (f"（本次給的 supersedes_id={supersedes_id} 不在生效清單裡）" if supersedes_id else ""))


def append_manual_observation(
    conn: Any,
    *,
    ticker: str,
    field_name: str,
    value: str,
    source_ref: str,
    as_of: str,
    author: str,
    supersedes_id: str | None = None,
    allow_parallel: bool = False,
    commit: bool = True,
) -> str:
    fields = {
        "ticker": ticker.upper().strip(),
        "field_name": field_name.strip(),
        "value": value.strip(),
        "source_ref": source_ref.strip(),
        "as_of": as_of.strip(),
        "author": author.strip(),
        "supersedes_id": supersedes_id,
    }
    if any(not fields[key] for key in (
        "ticker", "field_name", "value", "source_ref", "as_of", "author"
    )):
        raise ValueError("manual observation requires value, provenance, as_of, and author")
    _require_machine_comparable_if_mechanical(str(fields["field_name"]), str(fields["value"]))
    _require_pnl_sign_convention(str(fields["field_name"]), str(fields["value"]))
    validate_field_value(str(fields["field_name"]), str(fields["value"]))
    fields["as_of"] = normalize_as_of(str(fields["as_of"]))
    sensitive = sensitive_payload_path(fields, "manual_observation")
    if sensitive is not None:
        raise ValueError(f"secret-bearing manual observation rejected at {sensitive}")
    ensure_manual_observation_schema(conn)
    payload = _canonical(fields)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    observation_id = "mo_" + digest[:32]
    # ⚠ 順序重要：guard 要在 id 算出來**之後**才問，因為「同一筆重寫」（content-addressed id
    # 相同）是冪等操作而不是重複紀錄——`INSERT OR IGNORE` 本來就會忽略它。
    _reject_unlinked_duplicate(conn, str(fields["ticker"]), str(fields["field_name"]),
                               str(fields["as_of"]), supersedes_id, allow_parallel,
                               observation_id=observation_id)
    # 明示並存：寫入之後把它與那時生效的列登記成 `parallel`（2026-10-14 起留紀錄——以前不留，讀取端分不出刻意並存與重複）
    parallel_with = ([i for i in live_observation_ids(conn, str(fields["ticker"]), str(fields["field_name"]),
                                                      str(fields["as_of"])) if i != observation_id]
                     if allow_parallel and _is_sqlite(conn) else [])
    try:
        values = (
            observation_id,
            fields["ticker"],
            fields["field_name"],
            fields["value"],
            fields["source_ref"],
            fields["as_of"],
            fields["author"],
            supersedes_id,
            digest,
        )
        if _is_sqlite(conn):
            conn.execute(
                """
                INSERT OR IGNORE INTO manual_observations (
                    observation_id, ticker, field_name, value, source_ref,
                    as_of, author, supersedes_id, payload_digest
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            for other in parallel_with:
                payload = {"observation_id": observation_id, "target_id": other, "relation": "parallel",
                           "reason": "寫入時明示 allow_parallel：並存的另一筆觀測（不同來源或口徑，兩筆都算數）",
                           "author": fields["author"], "approval_ref": None}
                digest_rel = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
                conn.execute(
                    "INSERT OR IGNORE INTO manual_observation_relations (relation_id, observation_id, target_id, relation, "
                    "reason, author, approval_ref, payload_digest) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("mr_" + digest_rel[:32], observation_id, other, "parallel", payload["reason"], payload["author"],
                     None, digest_rel))
            # 投影的勝出者只從生效列挑（`_refresh_projection`；2026-10-14 以前不看取代鏈）
            _refresh_projection(conn, str(fields["ticker"]), str(fields["field_name"]))
        else:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO manual_observations (
                        observation_id, ticker, field_name, value, source_ref,
                        as_of, author, supersedes_id, payload_digest
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(payload_digest) DO NOTHING
                    """,
                    values,
                )
            _refresh_projection(conn, str(fields["ticker"]), str(fields["field_name"]))
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    return observation_id


def rebuild_manual_projection(conn: Any, *, commit: bool = True) -> int:
    """從 ledger 重建 `manual_fields` 投影；回傳重播的**生效列**數（被取代的列留在 ledger、不重播）。"""
    ensure_manual_observation_schema(conn)
    # 只從生效列重建（與 `_refresh_projection` 同一條規則；被取代的列不得因為記錄得晚而勝出）
    select_sql = """
        SELECT ticker, field_name, value, source_ref, as_of
        FROM manual_observations
        WHERE observation_id NOT IN (SELECT supersedes_id FROM manual_observations WHERE supersedes_id IS NOT NULL)
          AND observation_id NOT IN (SELECT target_id FROM manual_observation_relations WHERE relation = 'supersedes')
        ORDER BY as_of, recorded_at, observation_id
    """
    if _is_sqlite(conn):
        rows = conn.execute(select_sql).fetchall()
    else:
        with conn.cursor() as cursor:
            cursor.execute(select_sql)
            rows = cursor.fetchall()
    try:
        if _is_sqlite(conn):
            conn.execute("DELETE FROM manual_fields")
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO manual_fields (
                        ticker, field_name, value, source_note, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(ticker, field_name) DO UPDATE SET
                        value=excluded.value,
                        source_note=excluded.source_note,
                        updated_at=excluded.updated_at
                    """,
                    tuple(row),
                )
        else:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM manual_fields")
                for row in rows:
                    cursor.execute(
                        """
                        INSERT INTO manual_fields (
                            ticker, field_name, value, source_note, updated_at
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT(ticker, field_name) DO UPDATE SET
                            value=EXCLUDED.value,
                            source_note=EXCLUDED.source_note,
                            updated_at=EXCLUDED.updated_at
                        """,
                        tuple(row),
                    )
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    return len(rows)
