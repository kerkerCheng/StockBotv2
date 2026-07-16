"""Append-only prospective paper-portfolio ledger and deterministic replay."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
TRANSACTIONS_PATH = ROOT / "transactions.csv"

EVENT_FIELDS = [
    "event_id",
    "timestamp_utc",
    "ticker",
    "event_type",
    "target_weight",
    "changed_weight",
    "price",
    "price_currency",
    "fx_rate_to_base",
    "fx_ref",
    "thesis_version",
    "thesis_hash",
    "policy_version",
    "policy_decision",
    "expected_horizon",
    "disproof_condition",
    "disproof_ref",
    "reason",
    "decision_author",
    "benchmark_ticker",
    "corrects_event_id",
]
TRADE_TYPES = {"open", "add", "trim", "close"}
AMENDMENT_TYPES = {"correction", "reversal"}
ALL_EVENT_TYPES = TRADE_TYPES | AMENDMENT_TYPES
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_TICKER = re.compile(r"^[A-Z0-9.^_-]{1,20}$")
_EPSILON = 1e-9
_APPEND_CLOCK_TOLERANCE = timedelta(minutes=5)


class LedgerError(ValueError):
    """Raised when an event or ledger state is unsafe or inconsistent."""


def _root_paths(root: str | Path) -> tuple[Path, Path]:
    base = Path(root).resolve()
    return base / "config.json", base / "transactions.csv"


def _positive_number(value: Any, name: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool):
        raise LedgerError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise LedgerError(f"{name} must be numeric") from exc
    if not math.isfinite(number) or number < 0 or (number == 0 and not allow_zero):
        raise LedgerError(f"{name} must be {'non-negative' if allow_zero else 'positive'}")
    return number


def _weight(value: Any, name: str) -> float:
    number = _positive_number(value, name, allow_zero=True)
    if number > 1:
        raise LedgerError(f"{name} must be between 0 and 1")
    return number


def _signed_weight(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise LedgerError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise LedgerError(f"{name} must be numeric") from exc
    if not math.isfinite(number) or not -1 <= number <= 1:
        raise LedgerError(f"{name} must be between -1 and 1")
    return number


def _utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise LedgerError("timestamp_utc must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LedgerError("timestamp_utc must include a timezone")
    return parsed.astimezone(timezone.utc)


def initialize_portfolio(
    *,
    base_currency: str,
    initial_nav: float,
    root: str | Path = ROOT,
    portfolio_id: str = "prospective-main",
    default_benchmark_ticker: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Initialize once; base currency and virtual NAV must be explicit."""

    if not isinstance(base_currency, str) or not _CURRENCY.fullmatch(base_currency.upper()):
        raise LedgerError("base_currency must be a three-letter currency code")
    nav = _positive_number(initial_nav, "initial_nav")
    if not isinstance(portfolio_id, str) or not portfolio_id.strip():
        raise LedgerError("portfolio_id is required")
    benchmark = default_benchmark_ticker.upper() if default_benchmark_ticker else None
    if benchmark and not _TICKER.fullmatch(benchmark):
        raise LedgerError("default_benchmark_ticker is invalid")

    config_path, transactions_path = _root_paths(root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        existing = json.loads(config_path.read_text(encoding="utf-8"))
        if existing.get("created_at") is not None:
            raise LedgerError("portfolio is already initialized")

    created = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    config = {
        "portfolio_id": portfolio_id.strip(),
        "schema_version": "1.0",
        "created_at": created,
        "base_currency": base_currency.upper(),
        "initial_nav": nav,
        "price_source": "engine_c.financial_snapshots",
        "fx_source": "engine_c_or_explicit_snapshot",
        "default_benchmark_ticker": benchmark,
    }
    if transactions_path.exists() and transactions_path.stat().st_size:
        with transactions_path.open("r", encoding="utf-8", newline="") as handle:
            if next(csv.reader(handle), []) != EVENT_FIELDS:
                raise LedgerError("transactions.csv header does not match schema")
    else:
        mode = "w" if transactions_path.exists() else "x"
        with transactions_path.open(mode, encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=EVENT_FIELDS).writeheader()
            handle.flush()
            os.fsync(handle.fileno())

    # Publish initialized config only after the ledger is known-good. os.replace
    # keeps readers from observing a partially written JSON document.
    temporary = config_path.with_name(f".{config_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, config_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return config


def load_config(root: str | Path = ROOT, *, require_initialized: bool = True) -> dict[str, Any]:
    config_path, _ = _root_paths(root)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"cannot load paper portfolio config: {exc}") from exc
    required = {
        "portfolio_id",
        "schema_version",
        "created_at",
        "base_currency",
        "initial_nav",
        "price_source",
        "fx_source",
        "default_benchmark_ticker",
    }
    missing = sorted(required - set(config))
    if missing:
        raise LedgerError(f"config missing keys: {', '.join(missing)}")
    if require_initialized and (
        config["created_at"] is None
        or config["base_currency"] is None
        or config["initial_nav"] is None
    ):
        raise LedgerError("portfolio is not initialized; choose base currency and virtual NAV")
    if config["base_currency"] is not None and not _CURRENCY.fullmatch(config["base_currency"]):
        raise LedgerError("config base_currency is invalid")
    if config["initial_nav"] is not None:
        config["initial_nav"] = _positive_number(config["initial_nav"], "initial_nav")
    return config


def thesis_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_review(
    *,
    ticker: str,
    review_date: str,
    thesis_ref: str,
    evidence_manifest_ref: str,
    new_evidence: str,
    disproof_status: str,
    would_open_today: str,
    decision: str,
    pnl_context: str,
    benchmark_context: str,
    root: str | Path = ROOT,
) -> Path:
    """Write one immutable review with the minimum prospective audit context."""

    normalized_ticker = ticker.upper()
    if not _TICKER.fullmatch(normalized_ticker):
        raise LedgerError("review ticker is invalid")
    try:
        datetime.strptime(review_date, "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise LedgerError("review_date must be YYYY-MM-DD") from exc
    fields = {
        "thesis_ref": thesis_ref,
        "evidence_manifest_ref": evidence_manifest_ref,
        "new_evidence": new_evidence,
        "disproof_status": disproof_status,
        "would_open_today": would_open_today,
        "decision": decision,
        "pnl_context": pnl_context,
        "benchmark_context": benchmark_context,
    }
    missing = [name for name, value in fields.items() if not isinstance(value, str) or not value.strip()]
    if missing:
        raise LedgerError(f"review fields are required: {', '.join(missing)}")
    review_root = Path(root).resolve() / "reviews"
    review_root.mkdir(parents=True, exist_ok=True)
    slug = normalized_ticker.lower().replace(".", "-")
    path = (review_root / f"{review_date}-{slug}.md").resolve()
    if path.parent != review_root.resolve():
        raise LedgerError("review path escaped reviews root")
    markdown = "\n".join(
        [
            f"# {normalized_ticker} prospective review — {review_date}",
            "",
            f"- **Original thesis:** {thesis_ref}",
            f"- **Evidence manifest:** {evidence_manifest_ref}",
            f"- **New evidence:** {new_evidence}",
            f"- **Disproof status:** {disproof_status}",
            f"- **Would open today:** {would_open_today}",
            f"- **Decision:** {decision}",
            f"- **P&L context:** {pnl_context}",
            f"- **Benchmark context:** {benchmark_context}",
            "",
            "Performance is audit context, not proof that the thesis was right or wrong.",
            "",
        ]
    )
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown)
    except FileExistsError as exc:
        raise LedgerError(f"review already exists: {path.name}") from exc
    return path


def create_event(
    *,
    ticker: str,
    event_type: str,
    target_weight: float,
    changed_weight: float,
    price: float,
    price_currency: str,
    fx_rate_to_base: float,
    fx_ref: str,
    thesis_version: str,
    thesis_hash: str,
    policy_version: str,
    policy_decision: Mapping[str, Any],
    expected_horizon: str,
    disproof_condition: str,
    disproof_ref: str,
    reason: str,
    decision_author: str,
    benchmark_ticker: str | None = None,
    corrects_event_id: str | None = None,
) -> dict[str, str]:
    """Create a CSV-ready event with program-generated identity and UTC time."""

    return {
        "event_id": f"evt_{uuid.uuid4().hex}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ticker": ticker.upper(),
        "event_type": event_type,
        "target_weight": str(target_weight),
        "changed_weight": str(changed_weight),
        "price": str(price),
        "price_currency": price_currency.upper(),
        "fx_rate_to_base": str(fx_rate_to_base),
        "fx_ref": fx_ref,
        "thesis_version": thesis_version,
        "thesis_hash": thesis_hash,
        "policy_version": policy_version,
        "policy_decision": json.dumps(policy_decision, sort_keys=True, separators=(",", ":")),
        "expected_horizon": expected_horizon,
        "disproof_condition": disproof_condition,
        "disproof_ref": disproof_ref,
        "reason": reason,
        "decision_author": decision_author,
        "benchmark_ticker": benchmark_ticker.upper() if benchmark_ticker else "",
        "corrects_event_id": corrects_event_id or "",
    }


def _validate_event_shape(event: Mapping[str, Any]) -> dict[str, Any]:
    if set(event) != set(EVENT_FIELDS):
        missing = sorted(set(EVENT_FIELDS) - set(event))
        extra = sorted(set(event) - set(EVENT_FIELDS))
        raise LedgerError(f"event schema mismatch; missing={missing}, extra={extra}")
    normalized = {key: "" if value is None else str(value) for key, value in event.items()}
    if not re.fullmatch(r"evt_[a-f0-9]{32}", normalized["event_id"]):
        raise LedgerError("event_id must be program-generated evt_<32 hex>")
    normalized["parsed_timestamp"] = _utc(normalized["timestamp_utc"])
    if not _TICKER.fullmatch(normalized["ticker"]):
        raise LedgerError("ticker is invalid")
    if normalized["event_type"] not in ALL_EVENT_TYPES:
        raise LedgerError(f"invalid event_type: {normalized['event_type']}")
    normalized["target_weight_number"] = _weight(
        normalized["target_weight"], "target_weight"
    )
    normalized["changed_weight_number"] = _signed_weight(
        normalized["changed_weight"], "changed_weight"
    )
    normalized["price_number"] = _positive_number(normalized["price"], "price")
    normalized["fx_rate_number"] = _positive_number(
        normalized["fx_rate_to_base"], "fx_rate_to_base"
    )
    if not _CURRENCY.fullmatch(normalized["price_currency"]):
        raise LedgerError("price_currency must be a three-letter code")
    for field in (
        "fx_ref",
        "thesis_version",
        "thesis_hash",
        "policy_version",
        "expected_horizon",
        "disproof_condition",
        "disproof_ref",
        "reason",
        "decision_author",
    ):
        if not normalized[field].strip():
            raise LedgerError(f"{field} is required")
    try:
        normalized["policy_decision_object"] = json.loads(normalized["policy_decision"])
    except json.JSONDecodeError as exc:
        raise LedgerError("policy_decision must be valid JSON") from exc
    decision = normalized["policy_decision_object"]
    if not isinstance(decision, dict) or decision.get("policy_version") != normalized["policy_version"]:
        raise LedgerError("policy_decision must match policy_version")
    if normalized["benchmark_ticker"] and not _TICKER.fullmatch(normalized["benchmark_ticker"]):
        raise LedgerError("benchmark_ticker is invalid")
    return normalized


def read_events(root: str | Path = ROOT) -> list[dict[str, str]]:
    _, transactions_path = _root_paths(root)
    if not transactions_path.exists():
        raise LedgerError("transactions.csv does not exist")
    with transactions_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EVENT_FIELDS:
            raise LedgerError("transactions.csv header does not match schema")
        return list(reader)


def _effective_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    last_time: datetime | None = None
    amendments: dict[str, dict[str, Any] | None] = {}
    for raw in events:
        event = _validate_event_shape(raw)
        event_id = event["event_id"]
        if event_id in seen:
            raise LedgerError(f"duplicate event_id: {event_id}")
        if last_time is not None and event["parsed_timestamp"] < last_time:
            raise LedgerError("event timestamps must be monotonic")
        last_time = event["parsed_timestamp"]
        seen[event_id] = event
        normalized.append(event)
        if event["event_type"] in AMENDMENT_TYPES:
            target = event["corrects_event_id"]
            if not target or target not in seen or target == event_id:
                raise LedgerError("amendment must reference an earlier event")
            if seen[target]["event_type"] not in TRADE_TYPES:
                raise LedgerError("amendment target must be an original trade event")
            if target in amendments:
                raise LedgerError("an event may be amended only once")
            amendments[target] = None if event["event_type"] == "reversal" else event

    effective: list[dict[str, Any]] = []
    for event in normalized:
        if event["event_type"] in AMENDMENT_TYPES:
            continue
        if event["event_id"] in amendments:
            replacement = amendments[event["event_id"]]
            if replacement is not None:
                effective.append(replacement)
            continue
        effective.append(event)
    return effective


def replay(events: Iterable[Mapping[str, Any]], *, root: str | Path = ROOT) -> dict[str, Any]:
    """Replay frozen events into cash/positions without writing derived state."""

    config = load_config(root)
    initial_nav = config["initial_nav"]
    cash = initial_nav
    realized_pnl = 0.0
    positions: dict[str, dict[str, Any]] = {}

    for event in _effective_events(events):
        ticker = event["ticker"]
        position = positions.get(ticker)
        decision = event["policy_decision_object"]
        decision_nav = _positive_number(
            decision.get("total_nav"), "policy_decision.total_nav"
        )
        base_price = event["price_number"] * event["fx_rate_number"]
        old_units = position["units"] if position else 0.0
        prior_weight = (old_units * base_price) / decision_nav
        target = event["target_weight_number"]
        changed = event["changed_weight_number"]
        inferred = (
            "open"
            if old_units == 0 and target > 0
            else "close"
            if old_units > 0 and target == 0
            else "add"
            if target > prior_weight
            else "trim"
            if 0 <= target < prior_weight
            else "invalid"
        )
        declared = event["event_type"]
        if declared == "correction":
            declared = inferred
        if declared != inferred:
            raise LedgerError(
                f"illegal state transition for {ticker}: declared={event['event_type']}, inferred={inferred}"
            )
        if not math.isclose(changed, target - prior_weight, abs_tol=_EPSILON):
            raise LedgerError(f"changed_weight does not reconcile for {ticker}")

        if decision.get("eligible_to_open") is False and target > prior_weight:
            raise LedgerError("policy decision does not allow increasing the position")
        maximum = _positive_number(
            decision.get("maximum_position"), "policy_decision.maximum_position", allow_zero=True
        )
        if decision_nav * target > maximum + _EPSILON:
            raise LedgerError(f"target_weight exceeds frozen policy decision for {ticker}")

        desired_units = (decision_nav * target) / base_price
        delta_units = desired_units - old_units
        if desired_units < -_EPSILON:
            raise LedgerError("trim exceeds units held")
        desired_units = max(0.0, desired_units)
        cash_delta = -(delta_units * base_price)
        if cash + cash_delta < -_EPSILON:
            raise LedgerError("transaction exceeds available cash")

        old_cost = position["cost_basis_base"] if position else 0.0
        if delta_units >= 0:
            new_cost = old_cost + delta_units * base_price
        else:
            sold_fraction = min(1.0, (-delta_units / old_units) if old_units else 1.0)
            released_cost = old_cost * sold_fraction
            proceeds = -delta_units * base_price
            realized_pnl += proceeds - released_cost
            new_cost = old_cost - released_cost
        cash += cash_delta

        if target == 0:
            positions.pop(ticker, None)
        else:
            positions[ticker] = {
                "ticker": ticker,
                "units": desired_units,
                "target_weight": target,
                "cost_basis_base": new_cost,
                "price_currency": event["price_currency"],
                "last_event_id": event["event_id"],
                "benchmark_ticker": event["benchmark_ticker"]
                or config.get("default_benchmark_ticker"),
            }

    return {
        "portfolio_id": config["portfolio_id"],
        "base_currency": config["base_currency"],
        "initial_nav": initial_nav,
        "cash": cash,
        "realized_pnl": realized_pnl,
        "positions": positions,
    }


def append_event(event: Mapping[str, Any], *, root: str | Path = ROOT) -> dict[str, Any]:
    """Validate the complete ledger, then append exactly one immutable row."""

    from thesis.investment_policy import calculate_position_limit, load_policy

    existing = read_events(root)
    normalized = _validate_event_shape(event)
    now = datetime.now(timezone.utc)
    if abs(now - normalized["parsed_timestamp"]) > _APPEND_CLOCK_TOLERANCE:
        raise LedgerError("new events must use the current program-generated timestamp")
    decision = normalized["policy_decision_object"]
    if normalized["event_type"] in AMENDMENT_TYPES:
        originals = {
            original["event_id"]: _validate_event_shape(original)
            for original in existing
            if original["event_type"] in TRADE_TYPES
        }
        target = originals.get(normalized["corrects_event_id"])
        if target is None:
            raise LedgerError("amendment must reference an earlier original trade event")
        if normalized["policy_version"] != target["policy_version"]:
            raise LedgerError("amendment must retain the original policy_version")
        if decision != target["policy_decision_object"]:
            raise LedgerError("amendment must retain the original frozen policy decision")
    else:
        current_policy = load_policy()
        if normalized["policy_version"] != current_policy["policy_version"]:
            raise LedgerError("new trades must use the current investment policy_version")
        try:
            recomputed = calculate_position_limit(
                total_nav=decision["total_nav"],
                high_risk_budget=decision["high_risk_budget"],
                conviction=decision["input_conviction"],
                analyst_coverage_count=decision["coverage_view"]["analyst_coverage_count"],
                policy=current_policy,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise LedgerError("policy_decision lacks reproducible sizing inputs") from exc
        for key in (
            "policy_version",
            "eligible_to_open",
            "effective_conviction",
            "conviction_coefficient",
            "maximum_position",
        ):
            if recomputed[key] != decision.get(key):
                raise LedgerError(f"policy_decision does not reproduce current policy: {key}")
    state = replay([*existing, event], root=root)
    _, transactions_path = _root_paths(root)
    with transactions_path.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=EVENT_FIELDS).writerow(
            {field: event[field] for field in EVENT_FIELDS}
        )
    return state


def value_portfolio(
    events: Iterable[Mapping[str, Any]],
    *,
    prices: Mapping[str, Any],
    fx_rates: Mapping[str, Any],
    benchmark_prices: Mapping[str, Mapping[str, float]] | None = None,
    root: str | Path = ROOT,
) -> dict[str, Any]:
    """Value replayed positions; missing market inputs produce explicit unknown."""

    state = replay(events, root=root)
    missing: list[str] = []
    market_value = 0.0
    unrealized = 0.0
    position_values: dict[str, Any] = {}
    for ticker, position in state["positions"].items():
        raw_price = prices.get(ticker)
        if raw_price is None:
            missing.append(f"price:{ticker}")
            continue
        price = raw_price.get("price") if isinstance(raw_price, Mapping) else raw_price
        currency = (
            raw_price.get("currency", position["price_currency"])
            if isinstance(raw_price, Mapping)
            else position["price_currency"]
        )
        price_number = _positive_number(price, f"price:{ticker}")
        if currency == state["base_currency"]:
            fx = 1.0
        else:
            raw_fx = fx_rates.get(currency)
            if raw_fx is None:
                missing.append(f"fx:{currency}->{state['base_currency']}")
                continue
            fx = raw_fx.get("rate") if isinstance(raw_fx, Mapping) else raw_fx
            fx = _positive_number(fx, f"fx:{currency}")
        value = position["units"] * price_number * fx
        pnl = value - position["cost_basis_base"]
        market_value += value
        unrealized += pnl
        position_values[ticker] = {"market_value": value, "unrealized_pnl": pnl}

    benchmark_context: dict[str, Any] = {}
    for position in state["positions"].values():
        benchmark = position.get("benchmark_ticker")
        if not benchmark or benchmark in benchmark_context:
            continue
        raw = (benchmark_prices or {}).get(benchmark)
        if not raw or raw.get("start") is None or raw.get("current") is None:
            benchmark_context[benchmark] = {"status": "unknown"}
        else:
            start = _positive_number(raw["start"], f"benchmark:{benchmark}:start")
            current = _positive_number(raw["current"], f"benchmark:{benchmark}:current")
            benchmark_context[benchmark] = {
                "status": "available",
                "return": current / start - 1,
            }

    if missing:
        return {
            **state,
            "valuation_status": "unknown",
            "missing_market_data": sorted(set(missing)),
            "position_values": position_values,
            "benchmark_context": benchmark_context,
        }
    return {
        **state,
        "valuation_status": "available",
        "missing_market_data": [],
        "position_values": position_values,
        "market_value": market_value,
        "unrealized_pnl": unrealized,
        "nav": state["cash"] + market_value,
        "benchmark_context": benchmark_context,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="initialize the prospective portfolio once")
    init.add_argument("--base-currency", required=True)
    init.add_argument("--initial-nav", required=True, type=float)
    init.add_argument("--benchmark")
    args = parser.parse_args()
    if args.command == "init":
        config = initialize_portfolio(
            base_currency=args.base_currency,
            initial_nav=args.initial_nav,
            default_benchmark_ticker=args.benchmark,
        )
        print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
