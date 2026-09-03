"""Engine D beta 監控：行情心跳、相對水位與目標配置差距。

2026-08-29 定案：整組技術訊號（三態系統動作、pace／單輪 campaign budget、RSI／MACD
tier 判定）已移除。2026-08-01 的三次回測全部失敗——以訊號 gate 現金投入終值輸給無腦
定投 8.5%；訊號調節借款提取無可測得效果；訊號決定投給哪一檔輸給固定單押最佳標的 22%。

本模組因此只回答使用者自己做不動的兩件事：
  1. **各 sleeve 距目標配置多遠**（決定「這次投哪一檔」的錨點）；
  2. **每檔的行情心跳與相對水位**（純脈絡，不排序、不建議、不換算成金額）。
投多少、什麼時候投由使用者決定；真實風控（槓桿 cap、總曝險 cap）完全不變。
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .policy import instrument_price_key, load_beta_policy, load_target_allocation
from shared.capital_authority import build_capital_view
from risk.snapshot import (
    build_portfolio_components,
    compose_risk_snapshot,
    event_search_requests,
    risk_changes,
)


_PRIMARY_DISPLAY_ORDER = (
    "QQQ",
    "TQQQ",
    "LON:VWRA",
    "SOXX",
    "00631L.TW",
    "2330.TW",
    "00981A.TW",
)
# 行情心跳：AGENTS.md「行情表是每日心跳」——即使今天不投入也不得省略，
# 每列必須明示商品自身的最新完整交易日與 1 日漲跌。
_HEARTBEAT_KEYS = ("session_date", "return_1d", "return_5d", "return_20d")
# 相對水位：只用位置指標，不含任何動能成分（RSI／MACD 已於 2026-08-29 移除）。
_WATER_LEVEL_KEYS = (
    "range_percentile_252",
    "drawdown_252",
    "distance_sma_200",
)


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


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("as_of must include timezone")
    return parsed.isoformat()


def _fresh_observation(
    observation: Mapping[str, Any] | None,
    *,
    evaluation_at: str,
    max_age_hours: int,
) -> Mapping[str, Any] | None:
    """行情鮮度降級：過期標 stale，時戳壞掉或未來標 quarantined。"""

    if observation is None:
        return None
    fetched_raw = observation.get("fetched_at")
    if not isinstance(fetched_raw, str):
        return {
            "data_status": "quarantined",
            "blockers": ["technical_fetched_at_missing"],
        }
    try:
        fetched = datetime.fromisoformat(fetched_raw.replace("Z", "+00:00"))
        evaluated = datetime.fromisoformat(evaluation_at.replace("Z", "+00:00"))
    except ValueError:
        return {
            "data_status": "quarantined",
            "blockers": ["technical_fetched_at_invalid"],
        }
    if fetched.tzinfo is None or evaluated.tzinfo is None:
        return {
            "data_status": "quarantined",
            "blockers": ["technical_fetched_at_invalid"],
        }
    age_hours = (evaluated.astimezone(timezone.utc) - fetched.astimezone(timezone.utc)).total_seconds() / 3600
    if age_hours < -1:
        return {
            "data_status": "quarantined",
            "blockers": ["technical_fetched_at_future"],
        }
    if age_hours > max_age_hours:
        return {
            "data_status": "stale",
            "blockers": ["technical_observation_stale"],
        }
    return observation


def water_level(observation: Mapping[str, Any] | None) -> dict[str, Any]:
    """把一筆自身價格觀測轉成不帶判斷的「現在站在哪裡」。

    只有位置指標，沒有動能指標。RSI 量的是最近漲跌的單邊程度，與位置可以完全
    脫鉤（高檔橫盤 RSI 回到 50、崩 40% 後急彈 RSI 可以到 70），且它正是 2026-08-01
    測失敗的那個輸入，以「水位」之名放回來等於把測過失敗的東西換名字重來。

    ⚠ 長期上漲的標的多數時間會落在高百分位（0.8–1.0）。**那是正確資訊，不是
    「該等回檔」的訊號**——2026-07-31 回測結論是等回檔才投入對 30 年終值是負貢獻。
    因此水位不參與任何排序或建議；投哪一格由目標配置缺口決定。
    """

    values = {key: _finite((observation or {}).get(key)) for key in _WATER_LEVEL_KEYS}
    return {
        "status": str((observation or {}).get("data_status") or "missing"),
        # 主要欄位：0.0＝52 週低點、1.0＝52 週高點。
        "range_percentile_52w": values["range_percentile_252"],
        "pct_from_52w_high": values["drawdown_252"],
        "pct_from_sma200": values["distance_sma_200"],
        "interpretation": "position_only_no_momentum_not_a_timing_signal",
    }


def _heartbeat(observation: Mapping[str, Any] | None) -> dict[str, Any]:
    """商品自身的最新完整交易日與短期漲跌，外加 TWSE 官方參考列。"""

    result: dict[str, Any] = {
        key: (observation or {}).get(key) for key in _HEARTBEAT_KEYS
    }
    reference = (observation or {}).get("_twse_reference")
    if isinstance(reference, Mapping):
        result.update(
            {
                "twse_session_date": reference.get("session_date"),
                "twse_close_raw": reference.get("close_raw"),
                "twse_change_raw": reference.get("change_raw"),
                "twse_change_pct": reference.get("change_pct"),
                "twse_status": reference.get("status"),
                "twse_source": reference.get("source"),
            }
        )
    return result


def _portfolio_snapshot(
    holdings_rows: Sequence[Mapping[str, Any]] | None,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    components = build_portfolio_components(holdings_rows, policy)
    blockers = list(components["blockers"])
    cash = float(components["cash_base"])
    if holdings_rows is not None and cash <= 0:
        blockers.append("cash_bucket_missing")
    return dict(components) | {
        "status": "available" if not blockers else "malformed",
        "blockers": sorted(set(blockers)),
    }


def build_allocation_gap(
    *,
    portfolio: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """輸出每個 sleeve 的目標 vs 實際差距，只給差距、不給金額也不排名。

    分母是已投入的非現金部位。落在 band 內視為到位、沒有偏好；超出 band 才標示。
    Sleeve 分類直接用 beta policy instrument 既有的 `sleeve` 欄位，不另建對照表。
    """

    policy_sleeves = {str(item["sleeve"]) for item in policy["instruments"]}
    target_sleeves = {str(name) for name in target_policy["sleeves"]}
    # 目標配置比 beta policy 多出來的那一格（alpha）在 beta 清單裡沒有任何
    # instrument；它的實際佔比只能由「非現金持股扣掉所有 beta instrument」導出。
    # 名字從兩份設定相減得到，不寫死（L16：分類要跟著資料走，不在下游自己猜）。
    residual_sleeves = sorted(target_sleeves - policy_sleeves)

    sleeve_order: list[str] = []
    for instrument in policy["instruments"]:
        sleeve = str(instrument["sleeve"])
        if sleeve in target_sleeves and sleeve not in sleeve_order:
            sleeve_order.append(sleeve)
    sleeve_order.extend(name for name in sorted(target_sleeves) if name not in sleeve_order)

    available = str(portfolio.get("status")) == "available"
    invested: float | None = None
    if available:
        candidate = float(portfolio.get("market_total_base") or 0.0) - float(
            portfolio.get("cash_base") or 0.0
        )
        invested = candidate if candidate > 0 else None
    report_reason = (
        None
        if invested is not None
        else "holdings_unavailable"
        if not available
        else "invested_non_cash_zero"
    )

    sleeve_by_ticker = {
        str(item["ticker"]): str(item["sleeve"]) for item in policy["instruments"]
    }
    invested_by_sleeve: dict[str, float] = {}
    for ticker, value in (portfolio.get("instrument_values") or {}).items():
        sleeve = sleeve_by_ticker.get(str(ticker))
        if sleeve is None:
            continue
        invested_by_sleeve[sleeve] = invested_by_sleeve.get(sleeve, 0.0) + float(value or 0.0)
    residual_base = float(portfolio.get("alpha_total_base") or 0.0)
    if len(residual_sleeves) == 1 and available:
        invested_by_sleeve[residual_sleeves[0]] = residual_base

    entries: list[dict[str, Any]] = []
    for name in sleeve_order:
        spec = target_policy["sleeves"][name]
        target = float(spec["target"])
        band = float(spec["band"])
        is_residual = name in residual_sleeves
        base_value = invested_by_sleeve.get(name)
        reason = report_reason
        if base_value is None and reason is None:
            # 只有殘量 sleeve 會走到這裡：目標配置多出兩格以上時無法歸屬殘量，
            # 誠實標成「算不到」，不得當成 0——0 會把新資金推向一個沒算過的格子。
            reason = (
                "residual_sleeve_ambiguous"
                if is_residual and len(residual_sleeves) != 1
                else "sleeve_value_unavailable"
            )
        actual = (
            base_value / invested
            if base_value is not None and invested is not None and reason is None
            else None
        )
        if actual is None:
            state = "unknown"
        # band 是容忍區間，邊界本身算到位；1e-9 只是吸收浮點誤差，
        # 不讓 0.40−0.05 這種算式把剛好落在邊界的值判成偏離。
        elif actual < target - band - 1e-9:
            state = "below_band"
        elif actual > target + band + 1e-9:
            state = "above_band"
        else:
            state = "on_target"
        entry: dict[str, Any] = {
            "sleeve": name,
            "role": str(spec["role"]),
            "target": target,
            "band": band,
            "actual": actual,
            "gap": actual - target if actual is not None else None,
            "state": state,
            "invested_base": base_value if reason is None else None,
            "actual_source": (
                "residual_non_beta_holdings" if is_residual else "policy_instruments"
            ),
            "unavailable_reason": reason if actual is None else None,
        }
        if is_residual:
            entry["residual_instruments"] = list(
                portfolio.get("unclassified_instruments") or []
            )
        entries.append(entry)

    return {
        "schema_version": "engine-d-allocation-gap-v1",
        "policy_version": str(target_policy["policy_version"]),
        "status": "available" if invested is not None else "unavailable",
        "basis": str(target_policy["basis"]),
        "invested_non_cash_base": invested,
        "unavailable_reason": report_reason,
        "sleeves": entries,
        # 每次配置建議都必須講一次，不得因為它每天一樣就省略。
        "correlation_warnings": [dict(item) for item in target_policy["correlation_warnings"]],
        "rebalancing": dict(target_policy["rebalancing"]),
    }


def build_beta_monitor(
    *,
    observations_by_benchmark: Mapping[str, Mapping[str, Any] | None],
    history_by_benchmark: Mapping[str, Sequence[Mapping[str, Any]]],
    holdings_rows: Sequence[Mapping[str, Any]] | None,
    capital_authority_rows: Sequence[Mapping[str, Any]] | None = None,
    fx_fetcher=None,
    as_of: str,
    policy: Mapping[str, Any] | None = None,
    target_policy: Mapping[str, Any] | None = None,
    previous_risk_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one public, non-executing beta report：心跳＋水位＋配置差距。"""

    evaluation_at = _timestamp(as_of)
    resolved_policy = dict(policy or load_beta_policy())
    resolved_target = dict(target_policy or load_target_allocation())
    max_age_hours = int(resolved_policy["market_data"]["max_refresh_age_hours"])
    portfolio = _portfolio_snapshot(holdings_rows, resolved_policy)
    nav = float(portfolio["nav_base"])

    items: list[dict[str, Any]] = []
    for instrument in resolved_policy["instruments"]:
        price_key = instrument_price_key(instrument)
        # 心跳與水位一律取自商品自身的價格序列：TQQQ 不冒用 QQQ、
        # 00631L／006208 不冒用 0050。
        price_observation = _fresh_observation(
            observations_by_benchmark.get(price_key),
            evaluation_at=evaluation_at,
            max_age_hours=max_age_hours,
        )
        price_status = (
            str(price_observation.get("data_status") or "missing")
            if price_observation
            else "missing"
        )
        blockers = sorted(
            {str(value) for value in (price_observation or {}).get("blockers") or []}
            or ({"technical_observation_missing"} if price_observation is None else set())
        )
        current_value = float(portfolio["instrument_values"].get(instrument["ticker"], 0.0))
        items.append(
            {
                "ticker": instrument["ticker"],
                "sleeve": instrument["sleeve"],
                "price_symbol": instrument["provider_symbol"],
                "price_series_key": price_key,
                "price_status": price_status,
                "heartbeat": _heartbeat(price_observation),
                "water_level": water_level(price_observation),
                "current_nominal_weight": current_value / nav if nav > 0 else None,
                "current_effective_weight": (
                    current_value * float(instrument["leverage_multiple"]) / nav
                    if nav > 0
                    else None
                ),
                "blockers": blockers,
                "warnings": sorted(
                    {str(value) for value in (price_observation or {}).get("warnings") or []}
                ),
            }
        )

    capital_view = build_capital_view(
        authority_rows=capital_authority_rows,
        portfolio_cash_base=portfolio["cash_base"],
        base_currency=portfolio["base_currency"],
        evaluation_at=evaluation_at,
        max_authority_age_days=int(resolved_policy["capital"]["authority_max_age_days"]),
        # beta policy 的 fx_max_age_hours 是給資本換匯用的獨立設定（與決策鮮度 gate
        # 不同消費者），維持 hours 不改名；在呼叫點換算成交易日即可。
        max_fx_age_sessions=max(
            1, int(resolved_policy["capital"]["fx_max_age_hours"]) // 24
        ),
        fx_fetcher=fx_fetcher,
    )
    risk_snapshot = compose_risk_snapshot(
        portfolio,
        capital_view,
        resolved_policy,
        as_of=evaluation_at,
    )
    self_funded_cash = capital_view["self_funded_cash"]
    capital_available = (
        portfolio["status"] == "available"
        and self_funded_cash["status"] == "available"
        and not risk_snapshot["hard_blocks"]
    )
    # 自有現金可投入區間＝Portfolio CASH − cash floor，不再乘任何 pace。
    # 只有真正的硬擋（槓桿 cap／總曝險 cap／資本 authority 失效）會讓它歸零。
    deployable = float(self_funded_cash["deployable_cash_base"])
    self_funded_range = [0.0, max(deployable, 0.0)] if capital_available else [0.0, 0.0]

    allocation_gap = build_allocation_gap(
        portfolio=portfolio,
        policy=resolved_policy,
        target_policy=resolved_target,
    )

    price_statuses = {str(item["price_status"]) for item in items}
    base_status = (
        "degraded"
        if portfolio["status"] != "available"
        or not price_statuses <= {"observed", "insufficient_history"}
        else "partial"
        if "insufficient_history" in price_statuses
        else "ok"
    )
    report_status = (
        base_status
        if base_status == "degraded"
        else "partial"
        if base_status == "partial" or capital_view["status"] != "available"
        else "ok"
    )
    return {
        "schema_version": "engine-d-beta-monitor-v7",
        "as_of": evaluation_at,
        "policy_version": resolved_policy["policy_version"],
        "policy_mode": resolved_policy["mode"],
        "capital_scope": resolved_policy["capital_scope"],
        "status": report_status,
        "portfolio": {
            "status": portfolio["status"],
            "nav_base": nav if nav > 0 else None,
            "base_currency": portfolio["base_currency"],
            "cash_base": portfolio["cash_base"],
            "cash_floor_base": self_funded_cash["cash_floor_base"],
            "deployable_cash_base": self_funded_cash["deployable_cash_base"],
            "invested_non_cash_base": allocation_gap["invested_non_cash_base"],
            "leveraged_nominal_weight": portfolio["leveraged_nominal_base"] / nav if nav > 0 else None,
            "leveraged_effective_weight": portfolio["leveraged_effective_base"] / nav if nav > 0 else None,
            "alpha_total_weight": risk_snapshot["alpha_total_weight"],
            "known_issuer_exposures": risk_snapshot["issuer_exposures"],
        },
        "capital_view": {
            key: capital_view[key]
            for key in (
                "schema_version",
                "status",
                "as_of",
                "authority_as_of",
                "digest",
                "base_currency",
                "self_funded_cash",
                "fx",
                "blockers",
                "warnings",
                "drawn_debt_base",
            )
        },
        "self_funded_supported_range": self_funded_range,
        "contingent_credit_available": capital_view["contingent_credit_available"],
        "loan_funded_supported_range": capital_view["loan_funded_supported_range"],
        "allocation_gap": allocation_gap,
        "risk_snapshot": risk_snapshot,
        "risk_changes": risk_changes(risk_snapshot, previous_risk_snapshot, resolved_policy),
        "event_search_requests": event_search_requests(
            risk_snapshot,
            observations_by_benchmark=observations_by_benchmark,
            history_by_benchmark=history_by_benchmark,
            policy=resolved_policy,
        ),
        "blockers": sorted(
            set(portfolio["blockers"] + capital_view["blockers"] + risk_snapshot["hard_blocks"])
        ),
        "warnings": sorted(
            set(portfolio["warnings"] + risk_snapshot["warnings"] + capital_view["warnings"])
        ),
        "items": items,
    }


def _pct(value: Any) -> str:
    parsed = _finite(value)
    return "未知" if parsed is None else f"{parsed * 100:.1f}%"


def _signed_pct(value: Any) -> str:
    parsed = _finite(value)
    if parsed is None:
        return "未知"
    percentage = parsed * 100
    if abs(percentage) < 0.05:
        percentage = 0.0
    return f"{percentage:+.1f}%"


def _moves(heartbeat: Mapping[str, Any]) -> str:
    """每日心跳：最新完整交易日＋自身短期漲跌，任何情況都不省略。"""

    session = str(heartbeat.get("session_date") or "未知")
    return (
        f"最新完整交易日 {session}：1日 {_signed_pct(heartbeat.get('return_1d'))}｜"
        f"5日 {_signed_pct(heartbeat.get('return_5d'))}｜"
        f"20日 {_signed_pct(heartbeat.get('return_20d'))}"
    )


def _twse_snapshot(heartbeat: Mapping[str, Any]) -> str:
    session = heartbeat.get("twse_session_date")
    change_pct = _finite(heartbeat.get("twse_change_pct"))
    if not session or change_pct is None:
        return ""
    return f"TWSE 官方 {session} {_signed_pct(change_pct)}｜"


def _water_level_label(item: Mapping[str, Any]) -> str:
    """相對水位純呈現：不排序、不建議、不換算金額。"""

    level = item.get("water_level") or {}
    percentile = _finite(level.get("range_percentile_52w"))
    percentile_text = "n/a" if percentile is None else f"{percentile * 100:.0f}%"
    return (
        f"52週區間位置 {percentile_text}（0%=低點／100%=高點）｜"
        f"距52週高點 {_pct(level.get('pct_from_52w_high'))}｜"
        f"距200日均線 {_signed_pct(level.get('pct_from_sma200'))}"
    )


def _price_status_label(item: Mapping[str, Any]) -> str:
    if str(item.get("price_status")) == "observed":
        return "🟢 行情正常"
    if str(item.get("price_status")) == "insufficient_history":
        return "⚪ 歷史不足"
    return "🔴 資料不足"


def _sleeve_label(value: Any) -> str:
    return {
        "beta_core": "全球廣度錨",
        "beta_tilt": "科技／區域傾斜",
        "beta_tilt_active": "主動型 beta",
        "beta_leverage": "槓桿 ETF",
        "large_cap_tilt": "單一大型股",
        "alpha": "瓶頸研究衛星",
    }.get(str(value), str(value))


def _gap_state_label(value: Any) -> str:
    return {
        "below_band": "低於目標區間",
        "on_target": "到位（區間內、無偏好）",
        "above_band": "高於目標區間",
        "unknown": "算不到",
    }.get(str(value), str(value))


def _gap_reason_label(value: Any) -> str:
    return {
        "holdings_unavailable": "持股資料不可用",
        "invested_non_cash_zero": "沒有已投入的非現金部位",
        "residual_sleeve_ambiguous": "殘量無法歸屬到單一 sleeve",
        "sleeve_value_unavailable": "此 sleeve 的部位金額不可得",
    }.get(str(value), str(value).replace("_", " "))


def _constraint_label(value: Any) -> str:
    raw = str(value)
    labels = {
        "technical_history_insufficient_252_sessions": "歷史不足 252 個交易日",
        "technical_observation_missing": "缺少行情資料",
        "technical_observation_stale": "行情資料過期",
        "technical_fetched_at_missing": "行情時戳缺失",
        "technical_fetched_at_invalid": "行情時戳無效",
        "technical_fetched_at_future": "行情時戳在未來",
        "technical_session_stale_vs_twse": "TWSE 官方行情較新，本列暫時隔離",
        "technical_twse_freshness_unavailable": "TWSE freshness 校驗不可用",
        "technical_refresh_failed": "本輪行情更新失敗",
    }
    return labels.get(raw, raw.replace("_", " "))


def _warning_label(value: Any) -> str:
    raw = str(value)
    if raw.startswith("issuer_concentration_warning:"):
        return f"{raw.partition(':')[2]} 集中曝險已進警戒"
    return {
        "issuer_lookthrough_partial": "ETF 成分穿透僅涵蓋已登記部分",
        "leveraged_effective_warning": "換算槓桿曝險已進警戒",
        "leveraged_nominal_warning": "槓桿 ETF 資金占比已進警戒",
        "unclassified_holdings_assumed_unlevered_direct_issuer": (
            "未分類持股暫按非槓桿直接曝險計算"
        ),
        "drawn_debt_present": "已有提款貸款",
        "credit_terms_incomplete": "貸款條件資料不完整",
        "twse_freshness_unavailable": "TWSE freshness 校驗不可用",
        "twse_reference_older_than_provider": "TWSE 參考列落後供應商列",
    }.get(raw, raw.replace("_", " "))


def _status_label(value: Any) -> str:
    return {
        "available": "可用",
        "incomplete": "資料不完整",
        "unavailable": "不可用",
        "complete": "完整",
        "unknown": "未知",
    }.get(str(value), str(value).replace("_", " "))


def _compact_monitor_item(item: Mapping[str, Any]) -> str:
    twse = _twse_snapshot(item["heartbeat"]).rstrip("｜")
    return (
        f"{item['ticker']} {_price_status_label(item)}"
        f"（{_moves(item['heartbeat'])}，{_water_level_label(item)}"
        + (f"，{twse}" if twse else "")
        + (
            "，" + "、".join(_constraint_label(value) for value in item.get("blockers") or [])
            if item.get("blockers")
            else ""
        )
        + "）"
    )


def _risk_hint_summary(report: Mapping[str, Any]) -> str:
    changes = report.get("risk_changes") or []
    if not changes:
        return "今日沒有顯示門檻跨越或狀態翻轉"
    if any(item.get("kind") == "baseline_initialized" for item in changes):
        return "已建立第一筆風險 baseline；後續只回報門檻跨越或狀態翻轉"
    labels: list[str] = []
    for item in changes:
        metric = str(item.get("metric") or "")
        if metric.startswith("issuer_exposure:"):
            labels.append(f"{metric.partition(':')[2]} 集中曝險變動")
        elif metric == "alpha_total_weight":
            labels.append("alpha 總量變動")
        elif "leverage" in metric:
            labels.append("槓桿狀態變動")
        elif metric == "policy_version":
            labels.append("風控 policy 已換版")
    return "、".join(dict.fromkeys(labels)) or "風險狀態有變"


def _money(value: Any, currency: str | None) -> str:
    parsed = _finite(value, non_negative=True)
    return "未知" if parsed is None else f"{currency or ''} {parsed:,.0f}".strip()


def _issuer_exposure_label(value: Any, coverage_status: Any) -> str:
    exposure = _pct(value)
    return f"已知至少 {exposure}" if str(coverage_status) == "partial" else exposure


def _risk_snapshot_lines(report: Mapping[str, Any], *, full: bool) -> list[str]:
    snapshot = report["risk_snapshot"]
    changes = report.get("risk_changes") or []
    if not full and not changes:
        return []
    etf = snapshot["etf_leverage"]
    lines = ["", "## 投組風險變化" if not full else "## 投組風險完整快照"]
    # 總曝險永遠顯示：它是唯一同時涵蓋持股、槓桿 ETF 與借款的口徑，
    # 而借款在 2026-08-01 之前完全不受任何硬擋約束。歸零門檻與它並列，
    # 因為「1.5x」對人沒有感覺，「指數跌 67% 自有資本歸零」才有。
    total = _finite(snapshot.get("total_exposure_weight"), non_negative=True)
    if total is not None:
        wipeout = _finite(snapshot.get("wipeout_index_drawdown"), non_negative=True)
        cap = _finite(snapshot.get("total_exposure_cap"), non_negative=True)
        lines.append(
            f"- **總曝險 {total:.2f}x**"
            + (f"（上限 {cap:.2f}x）" if cap else "")
            + (f"；自有資本歸零門檻：指數跌 {wipeout:.0%}" if wipeout else "")
        )
    if full or any("leverage" in str(item.get("metric")) for item in changes):
        lines.append(
            f"- 槓桿 ETF 資金占比：{_pct(etf.get('nominal_weight'))}；"
            f"換算槓桿曝險：{_pct(etf.get('effective_weight'))}；"
            f"已提款貸款占 NAV：{_pct(snapshot.get('loan_leverage_weight'))}；"
            f"合計換算曝險：{_pct(snapshot.get('combined_leverage_weight'))}"
        )
    if full or any(item.get("metric") == "alpha_total_weight" for item in changes):
        lines.append(f"- Alpha 總量：{_pct(snapshot.get('alpha_total_weight'))}（警告、不阻擋）")
    changed_issuers = {
        str(item.get("metric")).partition(":")[2]
        for item in changes
        if str(item.get("metric") or "").startswith("issuer_exposure:")
    }
    coverage = snapshot["issuer_coverage"]
    for issuer, exposure in snapshot.get("issuer_exposures", {}).items():
        if full or issuer in changed_issuers:
            lines.append(
                f"- {issuer}：總曝險 "
                f"{_issuer_exposure_label(exposure.get('total_weight'), coverage.get('status'))}"
                f"（直接 {_pct(exposure.get('direct_weight'))}／間接 {_pct(exposure.get('indirect_weight'))}）"
            )
    if full:
        lines.append(
            f"- Issuer look-through coverage：{coverage['status']}；method={coverage['method']}；"
            f"未建模={','.join(coverage['unmodeled_lookthrough_instruments']) or 'none'}"
        )
    if changes:
        lines.append(
            "- 較前次："
            + "；".join(
                f"{item.get('metric')} {item.get('previous_state', '')}→{item.get('current_state', '')}"
                for item in changes
            )
        )
    return lines


def _allocation_gap_lines(report: Mapping[str, Any], currency: str | None) -> list[str]:
    gap = report["allocation_gap"]
    lines = [
        "",
        "## 目標配置差距（決定「這次投哪一檔」的錨點）",
        "",
        f"- 分母：已投入的非現金部位 {_money(gap.get('invested_non_cash_base'), currency)}"
        "（不含現金；cash floor 是另一個 authority，不佔本表比例）",
        "- 再平衡只用新投入的錢往低於目標的格子補，不賣出；落在容忍區間內視為到位、沒有偏好。",
        "- 本表只給差距，不給金額、不排名——要投多少由你決定。",
        "- 貸款 tranche 不適用本表，仍走 Capital Authority 的逐次人工核准。",
    ]
    if gap.get("status") != "available":
        lines.append(
            f"- ⚠ 目前算不出實際佔比：{_gap_reason_label(gap.get('unavailable_reason'))}"
        )
    lines += [
        "",
        "| Sleeve | 角色 | 目標 | 容忍區間 | 實際 | 差距 | 狀態 |",
        "|---|---|---|---|---|---|---|",
    ]
    for entry in gap["sleeves"]:
        actual = entry.get("actual")
        state = _gap_state_label(entry.get("state"))
        if actual is None:
            state = f"{state}（{_gap_reason_label(entry.get('unavailable_reason'))}）"
        lines.append(
            f"| {entry['sleeve']}（{_sleeve_label(entry['sleeve'])}） | {entry['role']} | "
            f"{_pct(entry['target'])} | ±{_pct(entry['band'])} | "
            f"{'算不到' if actual is None else _pct(actual)} | "
            f"{'算不到' if entry.get('gap') is None else _signed_pct(entry.get('gap'))} | "
            f"{state} |"
        )
    below = [
        entry["sleeve"] for entry in gap["sleeves"] if entry.get("state") == "below_band"
    ]
    above = [
        entry["sleeve"] for entry in gap["sleeves"] if entry.get("state") == "above_band"
    ]
    unknown = [
        entry["sleeve"] for entry in gap["sleeves"] if entry.get("state") == "unknown"
    ]
    summary: list[str] = []
    if below:
        summary.append("低於目標、新資金可優先補：" + "、".join(below))
    if above:
        summary.append("高於目標、新資金避開：" + "、".join(above))
    if unknown:
        summary.append("算不到（不得當成 0）：" + "、".join(unknown))
    if not summary:
        summary.append("全部落在容忍區間內，沒有偏好——這次投哪一檔由你自己決定即可")
    lines.append("")
    lines.append("- **" + "；".join(summary) + "。**")

    lines += ["", "### 相關性警告（每天都要講一次，不因每天一樣而省略）", ""]
    for warning in gap.get("correlation_warnings") or []:
        lines.append(f"- **{warning['name']}**：{warning['detail']}")
    return lines


def render_beta_monitor_markdown(
    report: Mapping[str, Any],
    *,
    risk_view: str = "changes",
) -> str:
    """輸出配置錨點與行情心跳；不含任何時點判斷、節奏或系統動作。"""

    portfolio = report["portfolio"]
    currency = portfolio.get("base_currency")
    capital_view = report["capital_view"]
    self_funded_cash = capital_view["self_funded_cash"]
    contingent = report["contingent_credit_available"]
    deployable_cash = self_funded_cash.get("deployable_cash_base")
    supported_ceiling = report["self_funded_supported_range"][1]

    lines = [
        "# Beta Allocation Monitor",
        "",
        "## TL;DR",
        "",
        "- 目標：最大化約 30 年後的退休淨終值；Beta 維持只累積、不因一般回檔自動賣出。",
        "- **本報告不判斷「今天該不該投」，也不給任何投入金額或時間表。** 它只回答兩件事："
        "各 sleeve 距目標配置多遠、每檔現在在什麼水位。",
        "- **相對水位純屬脈絡，不參與排序。** 長期上漲的標的多數時間會落在 52 週區間的高位，"
        "那是正確資訊，不是「該等回檔」的訊號——等回檔才投入對 30 年終值是負貢獻。",
        f"- 自有現金可部署：{_money(deployable_cash, currency)}；cash floor 以上為 Alpha／Beta 共用。",
        f"- 風控：{_risk_hint_summary(report)}；未動用貸款額度 "
        f"{_money(contingent.get('undrawn_amount_base'), currency)} 不算自有現金。",
    ]

    lines += _allocation_gap_lines(report, currency)

    lines += [
        "",
        "## 資本與風控明細",
        "",
        f"- 自有現金可部署：{_money(deployable_cash, currency)}",
        f"- 自有現金可投入區間上限：{_money(supported_ceiling, currency)}"
        "（＝可部署現金；只有槓桿／總曝險硬擋或資本 authority 失效會歸零）",
        f"- 未動用貸款額度：{_money(contingent.get('undrawn_amount_base'), currency)}"
        f"（狀態：{_status_label(contingent.get('status', 'unknown'))}；"
        f"條件資料：{_status_label(contingent.get('terms_status', 'unknown'))}；"
        "不算自有現金）",
        f"- 已借款：{_money(contingent.get('drawn_amount_base'), currency)}；"
        f"估計月息：{_money(contingent.get('estimated_monthly_interest_base'), currency)}",
        "- 貸款投入：尚未核准；提款時間表、金額、標的與批次留待另案人工核准，且月息不得依賴被迫賣出 beta",
        f"- 共同現金池計算：Portfolio CASH {_money(portfolio.get('cash_base'), currency)} − "
        f"cash floor {_money(self_funded_cash.get('cash_floor_base'), currency)}；"
        "cash floor 以上全部可供 Alpha 與 Beta 共用",
        "- Alpha／Beta 分配：由目標配置比例、Decision sizing、單筆上限與風控另外決定；不預扣 alpha reserve。",
    ]
    blockers = report.get("blockers") or []
    warnings = list(report.get("warnings") or [])
    if risk_view != "full":
        warnings = [
            item
            for item in warnings
            if item not in set(report["risk_snapshot"].get("warnings") or [])
        ]
    if blockers:
        lines.append(f"- Portfolio blockers：{'、'.join(str(item) for item in blockers)}")
    if warnings:
        lines.append(f"- 風險提醒：{'、'.join(_warning_label(item) for item in warnings)}")
    twse_freshness = report.get("twse_freshness") or {}
    if twse_freshness.get("status") not in {None, "not_required", "not_available"}:
        lines.append(
            f"- 台股行情 freshness：{twse_freshness.get('status')}；"
            "TWSE 官方列只作最新交易日校驗，不混入 adjusted-close 指標"
        )

    lines += _risk_snapshot_lines(report, full=risk_view == "full")
    requests = report.get("event_search_requests") or []
    if requests:
        lines += ["", "## 集中曝險事件搜尋請求（未經查證、不寫入 authority）"]
        coverage_status = (report["risk_snapshot"].get("issuer_coverage") or {}).get(
            "status"
        )
        for request in requests:
            lines.append(
                f"- {request['issuer']}｜1日 {_signed_pct(request['return_1d'])}｜"
                f"曝險 {_issuer_exposure_label(request['exposure_weight'], coverage_status)}"
                f"（直接 {_pct(request['direct_weight'])}／"
                f"間接 {_pct(request['indirect_weight'])}）｜WebSearch：{request['search_query']}"
            )

    gap_state_by_sleeve = {
        str(entry["sleeve"]): entry for entry in report["allocation_gap"]["sleeves"]
    }
    primary_rank = {ticker: index for index, ticker in enumerate(_PRIMARY_DISPLAY_ORDER)}
    primary_items = sorted(
        (item for item in report["items"] if item["ticker"] in primary_rank),
        key=lambda item: primary_rank[item["ticker"]],
    )
    secondary_items = [
        item for item in report["items"] if item["ticker"] not in primary_rank
    ]
    # 行情表是每日心跳：即使今天不投入、或全部落在配置區間內，逐檔表都不得省略。
    lines += ["", "## 主力 ETF／權值（每日心跳，不受今日是否投入影響）"]
    if primary_items:
        lines += [
            "| 標的 | 行情狀態 | 行情心跳（自身價格） | 相對水位（自身價格） | 所屬 sleeve 配置狀態 |",
            "|---|---|---|---|---|",
        ]
        for item in primary_items:
            heartbeat = item["heartbeat"]
            twse = _twse_snapshot(heartbeat).rstrip("｜")
            moves = _moves(heartbeat) + (f"；{twse}" if twse else "")
            entry = gap_state_by_sleeve.get(str(item["sleeve"])) or {}
            note = (
                "、".join(_constraint_label(value) for value in item.get("blockers") or [])
            )
            lines.append(
                f"| {item['ticker']} | {_price_status_label(item)}"
                + (f"（{note}）" if note else "")
                + f" | {moves} | {_water_level_label(item)} | "
                f"{item['sleeve']}：{_gap_state_label(entry.get('state'))} |"
            )
    else:
        lines.append("- 無")
    lines += ["", "## 個股與其他（摘要）"]
    if secondary_items:
        other_etfs = [item for item in secondary_items if item["ticker"] in {"0050.TW", "006208.TW"}]
        individual_names = [item for item in secondary_items if item not in other_etfs]
        if other_etfs:
            lines.append(
                "- 其他 ETF：" + "；".join(_compact_monitor_item(item) for item in other_etfs)
            )
        if individual_names:
            lines.append(
                "- 個股：" + "；".join(_compact_monitor_item(item) for item in individual_names)
            )
    else:
        lines.append("- 無")
    lines += [
        "",
        "> 本報告不產生部位尺寸、不代表已核准、已提款、已下單或已寫回 Google Sheet。"
        "未動用貸款額度不計入投資資產或自有現金。",
    ]
    return "\n".join(lines)


__all__ = [
    "build_allocation_gap",
    "build_beta_monitor",
    "render_beta_monitor_markdown",
    "water_level",
]
