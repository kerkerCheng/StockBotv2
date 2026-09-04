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
        """
    )


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
    fields["as_of"] = normalize_as_of(str(fields["as_of"]))
    sensitive = sensitive_payload_path(fields, "manual_observation")
    if sensitive is not None:
        raise ValueError(f"secret-bearing manual observation rejected at {sensitive}")
    ensure_manual_observation_schema(conn)
    payload = _canonical(fields)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    observation_id = "mo_" + digest[:32]
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
            winner = conn.execute(
                """
                SELECT ticker, field_name, value, source_ref, as_of
                FROM manual_observations
                WHERE ticker = ? AND field_name = ?
                ORDER BY as_of DESC, recorded_at DESC, observation_id DESC
                LIMIT 1
                """,
                (fields["ticker"], fields["field_name"]),
            ).fetchone()
            assert winner is not None
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
                tuple(winner),
            )
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
                cursor.execute(
                    """
                    SELECT ticker, field_name, value, source_ref, as_of
                    FROM manual_observations
                    WHERE ticker = %s AND field_name = %s
                    ORDER BY as_of DESC, recorded_at DESC, observation_id DESC
                    LIMIT 1
                    """,
                    (fields["ticker"], fields["field_name"]),
                )
                winner = cursor.fetchone()
                if winner is None:
                    raise RuntimeError("manual observation insert has no projection winner")
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
                    tuple(winner),
                )
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    return observation_id


def rebuild_manual_projection(conn: Any, *, commit: bool = True) -> int:
    ensure_manual_observation_schema(conn)
    select_sql = """
        SELECT ticker, field_name, value, source_ref, as_of
        FROM manual_observations
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
