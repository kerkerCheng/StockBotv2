"""Point-in-time daily technical observations for the fixed beta universe。"""
from __future__ import annotations

import hashlib
import io
import json
import math
import statistics
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from .twse import twse_code


_STATUS = {"observed", "insufficient_history", "unavailable", "quarantined"}
_METRIC_COLUMNS = (
    "close_raw",
    "close_adjusted",
    "return_1d",
    "return_5d",
    "return_20d",
    "drawdown_252",
    "rsi_14",
    "macd_line",
    "macd_signal",
    "macd_histogram",
    "macd_histogram_slope",
    "sma_20",
    "sma_50",
    "sma_200",
    "distance_sma_20",
    "distance_sma_50",
    "distance_sma_200",
    "sma_50_slope_5",
    "realized_vol_20",
    "realized_vol_60",
)


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _finite(value: Any, *, positive: bool = False) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        return None
    return parsed


def _time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return parsed if parsed.tzinfo is not None else None


def _sma(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema_series(values: Sequence[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    previous = seed
    for index in range(period, len(values)):
        previous = alpha * values[index] + (1.0 - alpha) * previous
        result[index] = previous
    return result


def _rsi_wilder(values: Sequence[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    deltas = [values[index] - values[index - 1] for index in range(1, len(values))]
    gains = [max(delta, 0.0) for delta in deltas]
    losses = [max(-delta, 0.0) for delta in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = ((period - 1) * avg_gain + gain) / period
        avg_loss = ((period - 1) * avg_loss + loss) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def _macd(values: Sequence[float]) -> tuple[float | None, float | None, float | None, float | None]:
    ema_12 = _ema_series(values, 12)
    ema_26 = _ema_series(values, 26)
    macd_values: list[float] = []
    for fast, slow in zip(ema_12, ema_26):
        if fast is not None and slow is not None:
            macd_values.append(fast - slow)
    signal_values = _ema_series(macd_values, 9)
    histograms: list[float] = []
    latest_line: float | None = None
    latest_signal: float | None = None
    for line, signal in zip(macd_values, signal_values):
        if signal is not None:
            latest_line = line
            latest_signal = signal
            histograms.append(line - signal)
    if latest_line is None or latest_signal is None or not histograms:
        return None, None, None, None
    slope = histograms[-1] - histograms[-2] if len(histograms) >= 2 else None
    return latest_line, latest_signal, histograms[-1], slope


def _realized_vol(values: Sequence[float], sessions: int) -> float | None:
    if len(values) <= sessions:
        return None
    trailing = values[-(sessions + 1) :]
    returns = [math.log(trailing[index] / trailing[index - 1]) for index in range(1, len(trailing))]
    if len(returns) < 2:
        return None
    return statistics.stdev(returns) * math.sqrt(252.0)


def _period_return(values: Sequence[float], sessions: int) -> float | None:
    if sessions < 1 or len(values) <= sessions:
        return None
    prior = values[-(sessions + 1)]
    return values[-1] / prior - 1.0 if prior > 0 else None


def unavailable_observation(
    *,
    benchmark_key: str,
    provider_symbol: str,
    fetched_at: str,
    blocker: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "benchmark_key": benchmark_key.strip().casefold(),
        "provider_symbol": provider_symbol.strip().upper(),
        "session_date": None,
        "session_count": 0,
        "data_status": "unavailable",
        "source": f"yfinance://history/{provider_symbol.strip().upper()}",
        "series_digest": None,
        "fetched_at": fetched_at,
        "blockers": [blocker],
        "warnings": [],
    }
    result.update({key: None for key in _METRIC_COLUMNS})
    return result


def reconcile_twse_freshness(
    observation: Mapping[str, Any],
    *,
    reference: Mapping[str, Any] | None,
    oracle_error: str | None = None,
    provider_symbol: str | None = None,
) -> dict[str, Any]:
    """Attach the TWSE reference row and quarantine a lagging Yahoo bar.

    The reference is intentionally transient (``_twse_reference``).  It is
    carried by the current refresh into the public beta report, while the
    TechnicalObservation ledger remains an adjusted-close projection and does
    not mix raw TWSE prices into its indicator series.
    """

    result = dict(observation)
    symbol = str(provider_symbol or result.get("provider_symbol") or "")
    if twse_code(symbol) is None:
        return result

    blockers = {str(item) for item in result.get("blockers") or []}
    warnings = {str(item) for item in result.get("warnings") or []}
    if reference is None:
        result["_twse_reference"] = {
            "status": "unavailable",
            "source": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            "error": oracle_error or "twse_symbol_missing",
        }
        blockers.add("technical_twse_freshness_unavailable")
        if str(result.get("data_status")) == "observed":
            result["data_status"] = "quarantined"
        result["blockers"] = sorted(blockers)
        result["warnings"] = sorted(warnings)
        return result

    reference_payload = dict(reference)
    yahoo_session = str(result.get("session_date") or "")
    twse_session = str(reference_payload.get("session_date") or "")
    if not twse_session:
        reference_payload["status"] = "unavailable"
        blockers.add("technical_twse_freshness_unavailable")
        if str(result.get("data_status")) == "observed":
            result["data_status"] = "quarantined"
    elif not yahoo_session:
        reference_payload["status"] = "reference_only"
    elif twse_session > yahoo_session:
        reference_payload["status"] = "provider_lagging"
        blockers.add("technical_session_stale_vs_twse")
        if str(result.get("data_status")) in {"observed", "insufficient_history"}:
            result["data_status"] = "quarantined"
    elif twse_session == yahoo_session:
        reference_payload["status"] = "matched"
    else:
        reference_payload["status"] = "provider_ahead"
        warnings.add("twse_reference_older_than_provider")

    result["_twse_reference"] = reference_payload
    result["blockers"] = sorted(blockers)
    result["warnings"] = sorted(warnings)
    return result


def build_technical_observation(
    *,
    benchmark_key: str,
    provider_symbol: str,
    rows: Iterable[Mapping[str, Any]],
    fetched_at: str,
    source: str,
) -> dict[str, Any]:
    """Build scalar indicators from complete, adjusted daily sessions。"""

    key = benchmark_key.strip().casefold() if isinstance(benchmark_key, str) else ""
    symbol = provider_symbol.strip().upper() if isinstance(provider_symbol, str) else ""
    fetched = _time(fetched_at)
    blockers: list[str] = []
    warnings: list[str] = []
    if not key:
        blockers.append("technical_benchmark_key_invalid")
    if not symbol:
        blockers.append("technical_provider_symbol_invalid")
    if fetched is None:
        blockers.append("technical_fetched_at_invalid")
    if not isinstance(source, str) or not source.strip():
        blockers.append("technical_source_missing")

    sessions: dict[str, tuple[datetime, float, float]] = {}
    invalid_rows = 0
    incomplete_rows = 0
    for row in rows:
        if row.get("complete") is False:
            incomplete_rows += 1
            continue
        as_of = _time(row.get("as_of"))
        raw = _finite(row.get("close_raw"), positive=True)
        adjusted = _finite(row.get("close_adjusted"), positive=True)
        if as_of is None or raw is None or adjusted is None:
            invalid_rows += 1
            continue
        sessions[as_of.date().isoformat()] = (as_of, raw, adjusted)
    if invalid_rows:
        warnings.append("technical_history_rows_skipped")
    if incomplete_rows:
        warnings.append("forming_session_excluded")

    ordered = [sessions[key] for key in sorted(sessions)]
    base: dict[str, Any] = {
        "benchmark_key": key,
        "provider_symbol": symbol,
        "session_date": ordered[-1][0].date().isoformat() if ordered else None,
        "session_count": len(ordered),
        "data_status": "quarantined" if blockers else "insufficient_history",
        "source": source.strip() if isinstance(source, str) else "",
        "series_digest": None,
        "fetched_at": fetched_at,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }
    base.update({column: None for column in _METRIC_COLUMNS})
    if blockers:
        return base
    if not ordered:
        base["data_status"] = "unavailable"
        base["blockers"] = ["technical_history_missing"]
        return base

    raw_values = [item[1] for item in ordered]
    adjusted_values = [item[2] for item in ordered]
    series_payload = [
        [item[0].date().isoformat(), round(item[1], 12), round(item[2], 12)]
        for item in ordered
    ]
    base["series_digest"] = _digest(json.dumps(series_payload, separators=(",", ":")))
    base["close_raw"] = raw_values[-1]
    base["close_adjusted"] = adjusted_values[-1]
    base["return_1d"] = _period_return(adjusted_values, 1)
    base["return_5d"] = _period_return(adjusted_values, 5)
    base["return_20d"] = _period_return(adjusted_values, 20)
    base["rsi_14"] = _rsi_wilder(adjusted_values)
    (
        base["macd_line"],
        base["macd_signal"],
        base["macd_histogram"],
        base["macd_histogram_slope"],
    ) = _macd(adjusted_values)
    for period in (20, 50, 200):
        average = _sma(adjusted_values, period)
        base[f"sma_{period}"] = average
        base[f"distance_sma_{period}"] = (
            adjusted_values[-1] / average - 1.0 if average is not None else None
        )
    if len(adjusted_values) >= 55:
        prior_sma_50 = sum(adjusted_values[-55:-5]) / 50.0
        current_sma_50 = base["sma_50"]
        if current_sma_50 is not None and prior_sma_50 > 0:
            base["sma_50_slope_5"] = current_sma_50 / prior_sma_50 - 1.0
    base["realized_vol_20"] = _realized_vol(adjusted_values, 20)
    base["realized_vol_60"] = _realized_vol(adjusted_values, 60)
    if len(adjusted_values) >= 252:
        high = max(adjusted_values[-252:])
        base["drawdown_252"] = adjusted_values[-1] / high - 1.0

    if len(adjusted_values) < 252:
        base["blockers"] = ["technical_history_insufficient_252_sessions"]
        return base
    missing_metrics = [column for column in _METRIC_COLUMNS if base[column] is None]
    if missing_metrics:
        base["data_status"] = "quarantined"
        base["blockers"] = [f"technical_metric_missing:{column}" for column in missing_metrics]
        return base
    if any(_finite(base[column]) is None for column in _METRIC_COLUMNS):
        base["data_status"] = "quarantined"
        base["blockers"] = ["technical_metric_non_finite"]
        return base
    base["data_status"] = "observed"
    base["blockers"] = []
    return base


def _session_complete(session: datetime, fetched_at: datetime) -> bool:
    """Conservatively exclude today's forming bar before 18:00 exchange-local。"""

    if session.tzinfo is None:
        return False
    local_now = fetched_at.astimezone(session.tzinfo)
    if session.date() > local_now.date():
        return False
    if session.date() == local_now.date() and local_now.hour < 18:
        return False
    return True


def fetch_technical_observation(
    benchmark_key: str,
    provider_symbol: str,
    *,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    """Fetch two years from yfinance and return a safe normalized observation。"""

    fetched = _time(fetched_at) if fetched_at is not None else datetime.now(timezone.utc)
    if fetched is None:
        raise ValueError("fetched_at must include timezone")
    fetched_text = fetched.astimezone(timezone.utc).isoformat()
    try:
        import yfinance as yf
    except ImportError:
        return unavailable_observation(
            benchmark_key=benchmark_key,
            provider_symbol=provider_symbol,
            fetched_at=fetched_text,
            blocker="yfinance_unavailable",
        )
    last_result: dict[str, Any] | None = None
    for _attempt in range(2):
        try:
            # yfinance may print provider transport failures directly to stdout/stderr;
            # public Daily output exposes stable blocker codes, not provider text.
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                history = yf.Ticker(provider_symbol).history(
                    period="2y",
                    auto_adjust=False,
                    actions=False,
                )
            rows = []
            has_adjusted = "Adj Close" in history.columns
            for index, row in history.iterrows():
                session = index.to_pydatetime()
                rows.append(
                    {
                        "as_of": session.isoformat(),
                        "close_raw": row.get("Close"),
                        "close_adjusted": row.get("Adj Close") if has_adjusted else None,
                        "complete": _session_complete(session, fetched),
                    }
                )
            last_result = build_technical_observation(
                benchmark_key=benchmark_key,
                provider_symbol=provider_symbol,
                rows=rows,
                fetched_at=fetched_text,
                source=f"yfinance://history/{provider_symbol}?period=2y&auto_adjust=false",
            )
            if last_result["data_status"] != "unavailable":
                return last_result
        except Exception:
            last_result = None
    return last_result or unavailable_observation(
        benchmark_key=benchmark_key,
        provider_symbol=provider_symbol,
        fetched_at=fetched_text,
        blocker="technical_history_unavailable",
    )


def ensure_technical_schema(conn) -> None:
    """Non-destructively ensure SQLite technical ledger schema。"""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS technical_observations (
            observation_id TEXT PRIMARY KEY,
            benchmark_key TEXT NOT NULL,
            provider_symbol TEXT NOT NULL,
            session_date TEXT,
            session_count INTEGER NOT NULL CHECK (session_count >= 0),
            data_status TEXT NOT NULL CHECK (
                data_status IN ('observed', 'insufficient_history', 'unavailable', 'quarantined')
            ),
            close_raw REAL,
            close_adjusted REAL,
            return_1d REAL,
            return_5d REAL,
            return_20d REAL,
            drawdown_252 REAL,
            rsi_14 REAL,
            macd_line REAL,
            macd_signal REAL,
            macd_histogram REAL,
            macd_histogram_slope REAL,
            sma_20 REAL,
            sma_50 REAL,
            sma_200 REAL,
            distance_sma_20 REAL,
            distance_sma_50 REAL,
            distance_sma_200 REAL,
            sma_50_slope_5 REAL,
            realized_vol_20 REAL,
            realized_vol_60 REAL,
            source TEXT NOT NULL,
            series_digest TEXT,
            fetched_at TEXT NOT NULL,
            blockers_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            payload_digest TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_technical_benchmark_session
            ON technical_observations (benchmark_key, session_date DESC, fetched_at DESC);
        CREATE INDEX IF NOT EXISTS idx_technical_benchmark_fetched
            ON technical_observations (benchmark_key, fetched_at DESC);
        """
    )
    existing_columns = {
        str(row[1]) for row in conn.execute("PRAGMA table_info(technical_observations)")
    }
    for column in ("return_1d", "return_5d", "return_20d"):
        if column not in existing_columns:
            conn.execute(f"ALTER TABLE technical_observations ADD COLUMN {column} REAL")


def _validated_storage_payload(observation: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "benchmark_key",
        "provider_symbol",
        "session_date",
        "session_count",
        "data_status",
        "source",
        "series_digest",
        "fetched_at",
        "blockers",
        "warnings",
        *_METRIC_COLUMNS,
    }
    if set(observation) != required:
        raise ValueError("technical observation fields do not match schema")
    status = observation.get("data_status")
    if status not in _STATUS:
        raise ValueError("technical observation status is invalid")
    if _time(observation.get("fetched_at")) is None:
        raise ValueError("technical observation fetched_at is invalid")
    if not isinstance(observation.get("session_count"), int) or observation["session_count"] < 0:
        raise ValueError("technical observation session_count is invalid")
    blockers = observation.get("blockers")
    warnings = observation.get("warnings")
    if not isinstance(blockers, list) or not all(isinstance(item, str) for item in blockers):
        raise ValueError("technical observation blockers are invalid")
    if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
        raise ValueError("technical observation warnings are invalid")
    if status == "observed" and (blockers or any(_finite(observation.get(key)) is None for key in _METRIC_COLUMNS)):
        raise ValueError("observed technical row requires every finite metric and no blockers")
    payload = dict(observation)
    payload["blockers"] = sorted(set(blockers))
    payload["warnings"] = sorted(set(warnings))
    return payload


def append_technical_observation(conn, observation: Mapping[str, Any], *, commit: bool = True) -> str:
    """Append one idempotent TechnicalObservation and return its stable ID。"""

    payload = _validated_storage_payload(observation)
    payload_json = _canonical_json(payload)
    payload_digest = _digest(payload_json)
    observation_id = "to_" + payload_digest[:32]
    params = {
        "observation_id": observation_id,
        **{key: payload.get(key) for key in (
            "benchmark_key",
            "provider_symbol",
            "session_date",
            "session_count",
            "data_status",
            *_METRIC_COLUMNS,
            "source",
            "series_digest",
            "fetched_at",
        )},
        "blockers_json": _canonical_json({"items": payload["blockers"]}),
        "warnings_json": _canonical_json({"items": payload["warnings"]}),
        "payload_digest": payload_digest,
    }
    columns = list(params)
    try:
        from engine_c.db import DB_TYPE
    except ImportError:
        DB_TYPE = "sqlite"
    if DB_TYPE == "postgres":
        placeholders = ",".join(f"%({column})s" for column in columns)
        with conn.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO technical_observations ({','.join(columns)}) "
                f"VALUES ({placeholders}) ON CONFLICT (payload_digest) DO NOTHING",
                params,
            )
    else:
        ensure_technical_schema(conn)
        conn.execute(
            f"INSERT OR IGNORE INTO technical_observations ({','.join(columns)}) "
            f"VALUES ({','.join('?' for _ in columns)})",
            tuple(params[column] for column in columns),
        )
    if commit:
        conn.commit()
    return observation_id


def _row_to_observation(row: Mapping[str, Any]) -> dict[str, Any]:
    session_date = row["session_date"]
    fetched_at = row["fetched_at"]
    result = {
        "observation_id": str(row["observation_id"]),
        "benchmark_key": str(row["benchmark_key"]),
        "provider_symbol": str(row["provider_symbol"]),
        "session_date": (
            session_date.isoformat() if hasattr(session_date, "isoformat") else session_date
        ),
        "session_count": int(row["session_count"]),
        "data_status": str(row["data_status"]),
        **{
            key: float(row[key]) if row[key] is not None else None
            for key in _METRIC_COLUMNS
        },
        "source": str(row["source"]),
        "series_digest": str(row["series_digest"]) if row["series_digest"] is not None else None,
        "fetched_at": fetched_at.isoformat() if hasattr(fetched_at, "isoformat") else str(fetched_at),
        "payload_digest": str(row["payload_digest"]),
    }
    result["blockers"] = json.loads(str(row["blockers_json"]))["items"]
    result["warnings"] = json.loads(str(row["warnings_json"]))["items"]
    return result


def recent_technical_observations(conn, benchmark_key: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Return latest distinct observed sessions for signal transition checks。"""

    if limit < 1:
        raise ValueError("limit must be positive")
    key = benchmark_key.strip().casefold()
    try:
        from engine_c.db import DB_TYPE
    except ImportError:
        DB_TYPE = "sqlite"
    sql = (
        "SELECT * FROM technical_observations WHERE benchmark_key = %s "
        "AND data_status = 'observed' ORDER BY session_date DESC, fetched_at DESC"
        if DB_TYPE == "postgres"
        else "SELECT * FROM technical_observations WHERE benchmark_key = ? "
        "AND data_status = 'observed' ORDER BY session_date DESC, fetched_at DESC"
    )
    if DB_TYPE == "postgres":
        with conn.cursor() as cursor:
            cursor.execute(sql, (key,))
            columns = [item[0] for item in cursor.description]
            rows = [dict(zip(columns, values)) for values in cursor.fetchall()]
    else:
        ensure_technical_schema(conn)
        rows = [dict(row) for row in conn.execute(sql, (key,)).fetchall()]
    result: list[dict[str, Any]] = []
    seen_sessions: set[str] = set()
    for row in rows:
        session = str(row.get("session_date") or "")
        if not session or session in seen_sessions:
            continue
        seen_sessions.add(session)
        result.append(_row_to_observation(row))
        if len(result) >= limit:
            break
    return result


def latest_technical_status(conn, benchmark_key: str) -> dict[str, Any] | None:
    """Return newest fetch status, including unavailable／partial states。"""

    key = benchmark_key.strip().casefold()
    try:
        from engine_c.db import DB_TYPE
    except ImportError:
        DB_TYPE = "sqlite"
    if DB_TYPE == "postgres":
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM technical_observations WHERE benchmark_key = %s "
                "ORDER BY fetched_at DESC, observation_id DESC LIMIT 1",
                (key,),
            )
            values = cursor.fetchone()
            if values is None:
                return None
            columns = [item[0] for item in cursor.description]
            row = dict(zip(columns, values))
    else:
        ensure_technical_schema(conn)
        raw = conn.execute(
            "SELECT * FROM technical_observations WHERE benchmark_key = ? "
            "ORDER BY fetched_at DESC, observation_id DESC LIMIT 1",
            (key,),
        ).fetchone()
        if raw is None:
            return None
        row = dict(raw)
    return _row_to_observation(row)


__all__ = [
    "append_technical_observation",
    "build_technical_observation",
    "ensure_technical_schema",
    "fetch_technical_observation",
    "latest_technical_status",
    "recent_technical_observations",
    "reconcile_twse_freshness",
    "unavailable_observation",
]
