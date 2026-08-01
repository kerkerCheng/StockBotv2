"""跨 alpha／beta 的唯讀投組風險快照與低雜訊變化偵測。"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from identity.registry import IdentityRegistry, get_registry


def _finite(value: Any, *, non_negative: bool = False) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or (non_negative and parsed < 0):
        return None
    return parsed


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _direct_issuer_key(
    row: Mapping[str, Any],
    *,
    registry: IdentityRegistry,
) -> str:
    company_id = str(row.get("company_id") or "")
    research_ticker = registry.research_ticker(company_id) if company_id else None
    if research_ticker:
        return research_ticker.upper()
    ticker = str(row.get("ticker") or "").strip().upper()
    return ticker or company_id.upper() or "UNRESOLVED"


def build_portfolio_components(
    holdings_rows: Sequence[Mapping[str, Any]] | None,
    policy: Mapping[str, Any],
    *,
    nav_base: Any = None,
    base_currency: str | None = None,
    strict_reconciliation: bool = True,
    registry: IdentityRegistry | None = None,
) -> dict[str, Any]:
    """把 Sheet rows 轉成共用曝險 components；未知持股只降級、不再阻擋。"""

    if holdings_rows is None:
        return {
            "status": "unavailable",
            "blockers": ["holdings_unavailable"],
            "warnings": [],
            "nav_base": 0.0,
            "base_currency": base_currency,
            "cash_base": 0.0,
            "market_total_base": 0.0,
            "instrument_values": {},
            "leveraged_nominal_base": 0.0,
            "leveraged_effective_base": 0.0,
            "issuer_direct_base": {},
            "issuer_indirect_base": {},
            "alpha_total_base": 0.0,
            "unmodeled_lookthrough_instruments": [],
            "unclassified_instruments": [],
        }
    registry = registry or get_registry()
    aliases = {
        str(alias).upper(): instrument
        for instrument in policy["instruments"]
        for alias in instrument["sheet_aliases"]
    }
    cash_aliases = {str(item).casefold() for item in policy["capital"]["cash_bucket_aliases"]}
    explicit_nav = _finite(nav_base, non_negative=True)
    nav_values: list[float] = []
    currencies: set[str] = set()
    if isinstance(base_currency, str) and base_currency.strip():
        currencies.add(base_currency.strip().upper())
    blockers: list[str] = []
    warnings: list[str] = []
    cash = 0.0
    market_total = 0.0
    instrument_values = {str(item["ticker"]): 0.0 for item in policy["instruments"]}
    leveraged_nominal = 0.0
    leveraged_effective = 0.0
    issuer_direct: dict[str, float] = {}
    issuer_indirect: dict[str, float] = {}
    alpha_total = 0.0
    unmodeled: set[str] = set()
    unclassified: set[str] = set()
    for row in holdings_rows:
        if not isinstance(row, Mapping):
            blockers.append("holdings_malformed")
            continue
        value = _finite(row.get("market_value_base"), non_negative=True)
        ticker = str(row.get("ticker") or "").strip().upper()
        row_nav = _finite(row.get("nav_base"), non_negative=True)
        currency = str(row.get("base_currency") or "").strip().upper()
        bucket = str(row.get("bucket") or "").strip().casefold()
        if value is None or not ticker:
            blockers.append("holdings_malformed")
            continue
        if row_nav is not None:
            if row_nav <= 0:
                blockers.append("holdings_malformed")
            else:
                nav_values.append(row_nav)
        if currency:
            currencies.add(currency)
        market_total += value
        is_cash = bool(row.get("is_cash")) or bucket in cash_aliases or ticker.casefold() in cash_aliases
        if is_cash:
            cash += value
            continue
        instrument = aliases.get(ticker)
        if instrument is None:
            alpha_total += value
            issuer = _direct_issuer_key(row, registry=registry)
            issuer_direct[issuer] = issuer_direct.get(issuer, 0.0) + value
            unclassified.add(ticker)
            continue
        canonical = str(instrument["ticker"])
        instrument_values[canonical] += value
        leverage = float(instrument["leverage_multiple"])
        if leverage > 1:
            leveraged_nominal += value
            leveraged_effective += value * leverage
        issuer_loads = instrument["issuer_loads"]
        if not issuer_loads:
            unmodeled.add(canonical)
        for issuer, raw_load in issuer_loads.items():
            load = float(raw_load)
            contribution = value * leverage * load
            target = (
                issuer_direct
                if leverage == 1.0 and load == 1.0 and instrument["sleeve"] == "large_cap_tilt"
                else issuer_indirect
            )
            target[str(issuer)] = target.get(str(issuer), 0.0) + contribution

    resolved_nav = explicit_nav
    if resolved_nav is None and nav_values:
        resolved_nav = nav_values[0]
    if resolved_nav is None or resolved_nav <= 0:
        blockers.append("holdings_nav_missing")
        resolved_nav = 0.0
    if nav_values and any(
        not math.isclose(value, resolved_nav, rel_tol=1e-9, abs_tol=1e-6)
        for value in nav_values
    ):
        blockers.append("holdings_nav_inconsistent")
    if len(currencies) > 1:
        blockers.append("holdings_base_currency_inconsistent")
    if strict_reconciliation and resolved_nav > 0 and not math.isclose(
        market_total, resolved_nav, rel_tol=1e-6, abs_tol=0.01
    ):
        blockers.append("holdings_market_value_nav_mismatch")
    if unclassified:
        warnings.append("unclassified_holdings_assumed_unlevered_direct_issuer")
    if unmodeled:
        warnings.append("issuer_lookthrough_partial")
    return {
        "status": "available" if not blockers else "malformed",
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "nav_base": resolved_nav,
        "base_currency": next(iter(currencies)) if len(currencies) == 1 else None,
        "cash_base": cash,
        "market_total_base": market_total,
        "instrument_values": instrument_values,
        "leveraged_nominal_base": leveraged_nominal,
        "leveraged_effective_base": leveraged_effective,
        "issuer_direct_base": issuer_direct,
        "issuer_indirect_base": issuer_indirect,
        "alpha_total_base": alpha_total,
        "unmodeled_lookthrough_instruments": sorted(unmodeled),
        "unclassified_instruments": sorted(unclassified),
    }


def compose_risk_snapshot(
    components: Mapping[str, Any],
    capital_view: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    as_of: str,
) -> dict[str, Any]:
    """組合 ETF 槓桿、drawn debt、alpha 總量與已知 issuer 穿透。"""

    nav = float(components.get("nav_base") or 0.0)
    risk = policy["risk"]
    nominal = float(components.get("leveraged_nominal_base") or 0.0) / nav if nav > 0 else None
    effective = float(components.get("leveraged_effective_base") or 0.0) / nav if nav > 0 else None
    drawn_base = _finite(capital_view.get("drawn_debt_base"), non_negative=True)
    loan = drawn_base / nav if drawn_base is not None and nav > 0 else None
    combined = effective + loan if effective is not None and loan is not None else None
    # 負債分兩類。可被追繳的借款（IB margin 等）在遠早於自有資本歸零之前就會
    # 強制平倉——1.74x 時 Reg-T 25% 維持保證金在指數跌 43% 即追繳，而 30 年期
    # 不可追繳額度要跌 57% 才歸零且永不強制賣出。兩者不可當同類資本合計。
    callable_base = _finite(
        capital_view.get("callable_drawn_debt_base"), non_negative=True
    ) or 0.0
    callable_weight = callable_base / nav if nav > 0 else None
    # 總曝險倍數＝市場曝險 ÷ 自有資本。
    #   分子：非現金持股 ＋ 槓桿 ETF 的額外曝險。借來的錢已經買成持股、
    #         本來就在 market_total_base 裡，**不可再把負債加一次**（重複計算）。
    #   分母：Sheet 的 nav_base 是毛資產（持股＋現金，不扣負債），
    #         自有資本必須另外減去已提款負債。
    # 台股已由 holdings adapter 換算為 base currency，NAV 本身即含其匯率波動，
    # 因此分子必須納入台股，排除才是口徑錯誤。
    non_cash = (
        float(components.get("market_total_base") or 0.0)
        - float(components.get("cash_base") or 0.0)
    )
    etf_extra = float(components.get("leveraged_effective_base") or 0.0) - float(
        components.get("leveraged_nominal_base") or 0.0
    )
    own_capital = nav - (drawn_base or 0.0)
    total_exposure = (non_cash + etf_extra) / own_capital if own_capital > 0 else None
    alpha_total = float(components.get("alpha_total_base") or 0.0) / nav if nav > 0 else None
    direct = components.get("issuer_direct_base") or {}
    indirect = components.get("issuer_indirect_base") or {}
    issuers: dict[str, dict[str, float]] = {}
    for issuer in sorted(set(direct) | set(indirect)):
        direct_weight = float(direct.get(issuer, 0.0)) / nav if nav > 0 else 0.0
        indirect_weight = float(indirect.get(issuer, 0.0)) / nav if nav > 0 else 0.0
        issuers[str(issuer)] = {
            "direct_weight": direct_weight,
            "indirect_weight": indirect_weight,
            "total_weight": direct_weight + indirect_weight,
        }
    warnings = list(components.get("warnings") or [])
    hard_blocks: list[str] = []
    if nominal is not None:
        if nominal >= float(risk["leveraged_nominal_cap"]):
            hard_blocks.append("etf_leverage_nominal_cap_reached")
        elif nominal >= float(risk["leveraged_nominal_warning"]):
            warnings.append("leveraged_nominal_warning")
    if effective is not None:
        if effective >= float(risk["leveraged_effective_cap"]):
            hard_blocks.append("etf_leverage_effective_cap_reached")
        elif effective >= float(risk["leveraged_effective_warning"]):
            warnings.append("leveraged_effective_warning")
    # 總曝險硬擋。在此之前 hard_blocks 只看槓桿 ETF，已提款借款完全不受約束——
    # 全額提款買 1x 會讓總曝險升到 1.43x 而儀表板顯示一切正常。
    if total_exposure is not None:
        if total_exposure >= float(risk["total_exposure_cap"]):
            hard_blocks.append("total_exposure_cap_reached")
        elif total_exposure >= float(risk["total_exposure_warning"]):
            warnings.append("total_exposure_warning")
    if callable_weight is not None and callable_weight > float(risk["callable_debt_cap"]):
        hard_blocks.append("callable_debt_cap_reached")
    if alpha_total is not None and alpha_total >= float(risk["alpha_total_warning"]):
        warnings.append("alpha_total_warning")
    for issuer, exposure in issuers.items():
        if exposure["total_weight"] >= float(risk["issuer_concentration_warning"]):
            warnings.append(f"issuer_concentration_warning:{issuer}")
    if loan is None:
        warnings.append("loan_leverage_unavailable")
    payload = {
        "schema_version": "portfolio-risk-snapshot-v1",
        "as_of": as_of,
        "policy_version": policy["policy_version"],
        "nav_base": nav if nav > 0 else None,
        "base_currency": components.get("base_currency"),
        "etf_leverage": {
            "nominal_weight": nominal,
            "effective_weight": effective,
        },
        "loan_leverage_weight": loan,
        "combined_leverage_weight": combined,
        "total_exposure_weight": total_exposure,
        "total_exposure_cap": float(risk["total_exposure_cap"]),
        "callable_debt_weight": callable_weight,
        # 維持 L 倍時，指數跌 100/L% 自有資本歸零。這是使用者接受風險水準的
        # 唯一直觀數字，必須與倍數同時呈現。
        "wipeout_index_drawdown": (
            1.0 / total_exposure if total_exposure and total_exposure > 0 else None
        ),
        "alpha_total_weight": alpha_total,
        "issuer_exposures": issuers,
        "issuer_coverage": {
            "status": (
                "partial"
                if components.get("unmodeled_lookthrough_instruments")
                else "known_policy_loads_complete"
            ),
            "method": "policy_registered_issuer_loads_plus_direct_alpha",
            "unmodeled_lookthrough_instruments": list(
                components.get("unmodeled_lookthrough_instruments") or []
            ),
            "unclassified_instruments": list(components.get("unclassified_instruments") or []),
        },
        "warnings": sorted(set(warnings)),
        "hard_blocks": sorted(set(hard_blocks)),
    }
    payload["snapshot_digest"] = _digest(payload)
    return payload


def _band(value: Any, warning: float, cap: float | None = None) -> str:
    parsed = _finite(value, non_negative=True)
    if parsed is None:
        return "unavailable"
    if cap is not None and parsed >= cap:
        return "hard_block"
    if parsed >= warning:
        return "warning"
    return "normal"


def risk_changes(
    current: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """只回傳顯示門檻跨越、狀態翻轉或足夠大的數值變化。"""

    if previous is None:
        return [{"kind": "baseline_initialized", "metric": "portfolio_risk"}]
    risk = policy["risk"]
    display = risk["daily_display_change"]
    changes: list[dict[str, Any]] = []

    def compare(
        metric: str,
        old: Any,
        new: Any,
        *,
        threshold: float,
        warning: float,
        cap: float | None = None,
    ) -> None:
        old_value = _finite(old, non_negative=True)
        new_value = _finite(new, non_negative=True)
        old_state = _band(old_value, warning, cap)
        new_state = _band(new_value, warning, cap)
        delta = (
            new_value - old_value
            if old_value is not None and new_value is not None
            else None
        )
        if old_state != new_state or (delta is not None and abs(delta) >= threshold):
            changes.append(
                {
                    "kind": "status_flip" if old_state != new_state else "threshold_move",
                    "metric": metric,
                    "previous": old_value,
                    "current": new_value,
                    "delta": delta,
                    "previous_state": old_state,
                    "current_state": new_state,
                }
            )

    previous_etf = previous.get("etf_leverage") or {}
    current_etf = current.get("etf_leverage") or {}
    compare(
        "etf_leverage_nominal_weight",
        previous_etf.get("nominal_weight"),
        current_etf.get("nominal_weight"),
        threshold=float(display["combined_leverage_weight"]),
        warning=float(risk["leveraged_nominal_warning"]),
        cap=float(risk["leveraged_nominal_cap"]),
    )
    compare(
        "etf_leverage_effective_weight",
        previous_etf.get("effective_weight"),
        current_etf.get("effective_weight"),
        threshold=float(display["combined_leverage_weight"]),
        warning=float(risk["leveraged_effective_warning"]),
        cap=float(risk["leveraged_effective_cap"]),
    )
    compare(
        "loan_leverage_weight",
        previous.get("loan_leverage_weight"),
        current.get("loan_leverage_weight"),
        threshold=float(display["combined_leverage_weight"]),
        warning=1.0,
    )
    compare(
        "combined_leverage_weight",
        previous.get("combined_leverage_weight"),
        current.get("combined_leverage_weight"),
        threshold=float(display["combined_leverage_weight"]),
        warning=1.0,
    )
    compare(
        "alpha_total_weight",
        previous.get("alpha_total_weight"),
        current.get("alpha_total_weight"),
        threshold=float(display["alpha_total_weight"]),
        warning=float(risk["alpha_total_warning"]),
    )
    previous_issuers = previous.get("issuer_exposures") or {}
    current_issuers = current.get("issuer_exposures") or {}
    for issuer in sorted(set(previous_issuers) | set(current_issuers)):
        compare(
            f"issuer_exposure:{issuer}",
            (previous_issuers.get(issuer) or {}).get("total_weight", 0.0),
            (current_issuers.get(issuer) or {}).get("total_weight", 0.0),
            threshold=float(display["issuer_weight"]),
            warning=float(risk["issuer_concentration_warning"]),
        )
    if previous.get("policy_version") != current.get("policy_version"):
        changes.append(
            {
                "kind": "policy_changed",
                "metric": "policy_version",
                "previous": previous.get("policy_version"),
                "current": current.get("policy_version"),
            }
        )
    return changes


def event_search_requests(
    snapshot: Mapping[str, Any],
    *,
    observations_by_benchmark: Mapping[str, Mapping[str, Any] | None],
    history_by_benchmark: Mapping[str, Sequence[Mapping[str, Any]]],
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """價格首次跨越門檻時產生 ephemeral WebSearch packet，不建立 lead。"""

    event_policy = policy["risk"]["event_monitor"]
    concentration = float(event_policy["concentrated_issuer_threshold"])
    return_floor = float(event_policy["return_1d_at_most"])
    monitors: dict[str, Mapping[str, Any]] = {}
    for instrument in policy["instruments"]:
        if float(instrument["leverage_multiple"]) != 1.0:
            continue
        for issuer, load in instrument["issuer_loads"].items():
            if float(load) == 1.0:
                monitors.setdefault(str(issuer), instrument)
    requests: list[dict[str, Any]] = []
    for issuer, exposure in (snapshot.get("issuer_exposures") or {}).items():
        if float(exposure.get("total_weight") or 0.0) < concentration:
            continue
        instrument = monitors.get(str(issuer))
        if instrument is None:
            continue
        key = str(instrument["benchmark_key"])
        current = observations_by_benchmark.get(key)
        if not current or current.get("data_status") != "observed":
            continue
        current_return = _finite(current.get("return_1d"))
        if current_return is None or current_return > return_floor:
            continue
        current_session = str(current.get("session_date") or "")
        previous_return: float | None = None
        for item in history_by_benchmark.get(key, ()):
            if str(item.get("session_date") or "") == current_session:
                continue
            previous_return = _finite(item.get("return_1d"))
            if previous_return is not None:
                break
        if previous_return is not None and previous_return <= return_floor:
            continue
        symbol = str(instrument["benchmark_symbol"])
        requests.append(
            {
                "schema_version": "concentrated-exposure-event-search-v1",
                "issuer": issuer,
                "benchmark_symbol": symbol,
                "session_date": current_session or None,
                "return_1d": current_return,
                "trigger": f"return_1d<={return_floor}",
                "exposure_weight": exposure["total_weight"],
                "direct_weight": exposure["direct_weight"],
                "indirect_weight": exposure["indirect_weight"],
                "search_query": (
                    f"{issuer} {symbol} stock price drop {current_session} reason "
                    "official filing company announcement"
                ).strip(),
                "verification_status": "unverified",
                "persistence": "none",
                "authority_effect": "none",
            }
        )
    return requests


def read_latest_risk_snapshot(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    except OSError:
        return None
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema_version") == "portfolio-risk-snapshot-v1":
            return value
    return None


def append_risk_snapshot(path: str | Path, snapshot: Mapping[str, Any]) -> bool:
    """Append-only private telemetry；相同 as_of＋digest 可安全重跑。"""

    target = Path(path)
    latest = read_latest_risk_snapshot(target)
    if latest and latest.get("as_of") == snapshot.get("as_of") and latest.get(
        "snapshot_digest"
    ) == snapshot.get("snapshot_digest"):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_canonical(dict(snapshot)) + "\n")
    return True


__all__ = [
    "append_risk_snapshot",
    "build_portfolio_components",
    "compose_risk_snapshot",
    "event_search_requests",
    "read_latest_risk_snapshot",
    "risk_changes",
]
