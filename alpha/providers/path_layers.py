"""路徑上各層的取數（個股頁 S3c，2026-10-09）：結構表的鏈、層代表公司宣告、名冊、Engine C 的營收與匯率 →
`alpha.path_layers` 的純函式。**一輪 materialize 只算一次**：每一層、每一家公司各算一次，所有頁共用（119 頁）。

營收與換匯沿用「吃到多少」的同一套（`alpha.providers.capture.company_quarters`／`fx_tables`、`alpha.capture.usd_quarter`；
L16：取數路與換算規則只有一個 owner）。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

from alpha.capture import usd_quarter
from alpha.demand_anchor import series_keys_for
from alpha.layer_rep.contracts import SCOPE_LABELS
from alpha.path_layers import (
    COMPANY_PROXY, KIND_LABELS, absent, calendar_yoy, company_paths, fiscal_yoy, layer_yoy, node_kind,
)

from .capture import company_quarters, fx_tables

_SHOWN_POINTS = 8          # 每一節帶最近幾季（呈現用；全部的缺口照留在 gaps）


def _company_label(registry: Any, company_id: str) -> tuple[str | None, str]:
    company = registry.company(company_id) if registry is not None else None
    if company is None:
        return None, company_id
    return company.research_ticker, (company.display_name or company.research_ticker or company_id)


class _RevenueCache:
    """同一輪裡每家公司的曆季營收、每個幣別的季均價各取一次。"""

    def __init__(self, conn: Any, as_of: date) -> None:
        self.conn, self.as_of = conn, as_of
        self.quarters: dict[str, dict[str, Any]] = {}
        self.fx: dict[str, Any] = {}

    def company(self, ticker: str) -> dict[str, Any]:
        if ticker not in self.quarters:
            self.quarters[ticker] = company_quarters(self.conn, ticker, as_of=self.as_of)
        return self.quarters[ticker]

    def usd(self, ticker: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        got = self.company(ticker)
        currencies = {str(q.get("currency")) for q in got["quarters"].values()} - {"USD"}
        for currency in currencies - set(self.fx):
            table, _gaps = fx_tables(self.conn, {currency}, as_of=self.as_of)
            self.fx[currency] = table.get(currency)
        fx = {c: t for c, t in self.fx.items() if t is not None}
        out, gaps = {}, []
        for label, q in got["quarters"].items():
            converted = usd_quarter(q, label, fx)
            if converted.get("reason"):
                gaps.append({"period": label, "reason": converted["reason"]})
            else:
                out[label] = {"usd": converted["usd"], "known_on": converted["known_on"]}
        return out, gaps


def _layer_line(node: str, kind: str, declaration: Any, sitters: int, cache: _RevenueCache, registry: Any,
                *, as_of: date, declarations_read: bool) -> dict[str, Any]:
    line: dict[str, Any] = {"basis_label": "代表公司同一曆季營收加總（換美元）的年增", "sitters": sitters,
                            "representatives": [], "declaration": None}
    if not declarations_read:
        return {**line, "absence": absent("declarations_unread")}
    if declaration is None:
        code = "nobody_sits" if sitters == 0 else "no_representatives_declared"
        reason = None if sitters == 0 else f"還沒宣告代表公司（圖上坐這一層的有 {sitters} 家）"
        if kind == "product":
            reason = "還沒宣告代表公司（產品節點：公司財報不拆產品營收）"
        return {**line, "absence": absent(code, reason=reason)}
    line["declaration"] = {"rep_id": declaration.rep_id, "declared_on": declaration.created_at.date().isoformat(),
                           "expires": declaration.expires.isoformat() if declaration.expires else None,
                           "overdue": bool(declaration.expires and declaration.expires < as_of)}
    usd: dict[str, dict[str, dict[str, Any]]] = {}
    unavailable: dict[str, str] = {}
    declared = []
    for rep in declaration.representatives:
        ticker, name = _company_label(registry, rep.company_id)
        line["representatives"].append({"company_id": rep.company_id, "ticker": ticker, "name": name,
                                        "scope": rep.scope, "scope_label": SCOPE_LABELS.get(rep.scope, rep.scope),
                                        "segment": rep.segment, "why": rep.why,
                                        "citations": [c.as_dict() for c in rep.citations]})
        declared.append(rep.company_id)
        if rep.scope != "whole_company":
            unavailable[rep.company_id] = f"分部「{rep.segment}」還沒有季營收序列"
        elif not ticker:
            unavailable[rep.company_id] = "未上市或名冊沒有代號"
        elif cache.company(ticker)["source"] is None:
            unavailable[rep.company_id] = "季營收還沒接（海外財報）"
        else:
            usd[rep.company_id], _gaps = cache.usd(ticker)
    result = layer_yoy(usd, declared, unavailable, as_of=as_of)
    names = {r["company_id"]: r["name"] for r in line["representatives"]}
    points = result["points"]
    for point in points:                     # 給人讀的地方印公司名，不印 co:* id（id 照留在 company）
        for m in point["missing"]:
            m["name"] = names.get(m["company"], m["company"])
    out = {**line, "points": points[-_SHOWN_POINTS:], "gaps": result["gaps"][-6:],
           "latest": points[-1] if points else None, "absence": None}
    if not points:
        out["absence"] = absent("no_complete_quarter",
                                reason="還算不出年增——" + "；".join(f"{names.get(c, c)}：{r}" for c, r in sorted(unavailable.items()))
                                if unavailable else None)
    return out


def _company_line(node: str, cache: _RevenueCache, registry: Any, *, as_of: date) -> dict[str, Any]:
    from engine_c.history import first_filed_by_period, fundamental_series

    line: dict[str, Any] = {"basis_label": COMPANY_PROXY, "proxy": COMPANY_PROXY}
    if registry is None or registry.company(node) is None:
        return {**line, "absence": absent("company_not_in_registry")}
    ticker, name = _company_label(registry, node)
    line.update(ticker=ticker, company_name=name)
    if not ticker:
        return {**line, "absence": absent("company_unlisted")}
    got = cache.company(ticker)
    if got["source"] is None:
        from alpha.providers.capture import SEMIANNUAL_ONLY

        return {**line, "absence": absent("company_semiannual_only" if got.get("absence_reason") == SEMIANNUAL_ONLY
                                          else "company_no_revenue")}
    if got["source"].startswith("台股"):
        result = calendar_yoy(got["quarters"], as_of=as_of)
    else:
        rows = fundamental_series(cache.conn, ticker, "revenue_quarter", as_of=as_of)
        result = fiscal_yoy(rows, first_filed_by_period(cache.conn, ticker, "revenue_quarter", as_of=as_of), as_of=as_of)
    points = result["points"]
    out = {**line, "revenue_source": got["source"], "points": points[-_SHOWN_POINTS:], "gaps": result["gaps"][-6:],
           "latest": points[-1] if points else None, "absence": None}
    if not points:
        out["absence"] = absent("company_no_yoy")
    return out


def _anchor_line(node: str, anchor_ctx: Mapping[str, Any] | None) -> dict[str, Any]:
    """錨那一節：照抄 B2「錨的變化」那幾條序列的最新年增（不另算）。"""
    ctx = anchor_ctx or {}
    if ctx.get("absence"):
        return {"series": [], "absence": dict(ctx["absence"])}
    keys = series_keys_for([node], ctx.get("config") or {})
    series = []
    for key in keys:
        s = (ctx.get("series") or {}).get(key) or {}
        last = next((p for p in reversed(s.get("points") or ()) if p.get("yoy") is not None), None)
        series.append({"key": key, "label": s.get("label") or key, "period": (last or {}).get("period"),
                       "yoy": (last or {}).get("yoy"), "known_on": (last or {}).get("known_on")})
    return {"series": series, "absence": None if keys else absent("anchor_no_series")}


def path_context(conn: Any, *, structure_rows: Iterable[Mapping[str, Any]], seats: Mapping[str, Iterable[str]],
                 declarations: Mapping[str, Any] | None, registry: Any, anchor_ctx: Mapping[str, Any] | None,
                 as_of: date) -> dict[str, Any]:
    """一輪的路徑輸入：`{paths_by_company: {co: (paths, dropped)}, hops: {node: line}, companies}`。
    `declarations` 是 None＝這一輪沒讀到宣告 ledger（每一層照寫讀不到，不是「沒宣告」）。"""
    rows = list(structure_rows)
    names: dict[str, str] = {}
    for row in rows:
        for node, name in zip(row.get("chain") or (), row.get("chain_names") or ()):
            names.setdefault(str(node), str(name))
    companies = sorted({str(r.get("company_id")) for r in rows if r.get("company_id")})
    paths_by_company = {co: company_paths(rows, co) for co in companies}
    sitters: dict[str, int] = {}
    for _co, nodes in (seats or {}).items():
        for node in nodes or ():
            sitters[str(node)] = sitters.get(str(node), 0) + 1
    cache = _RevenueCache(conn, as_of)
    hops: dict[str, dict[str, Any]] = {}
    for co, (paths, _dropped) in paths_by_company.items():
        for path in paths:
            for index, node in enumerate(path):
                if node in hops:
                    continue
                kind = "anchor" if index == 0 else node_kind(node)
                base = {"node": node, "name": names.get(node, node), "kind": kind,
                        "kind_label": KIND_LABELS.get(kind or "", "不認得")}
                if kind == "anchor":
                    hops[node] = {**base, **_anchor_line(node, anchor_ctx)}
                elif kind in ("layer", "product"):
                    hops[node] = {**base, **_layer_line(
                        node, kind, (declarations or {}).get(node), sitters.get(node, 0), cache, registry,
                        as_of=as_of, declarations_read=declarations is not None)}
                elif kind == "company":
                    hops[node] = {**base, **_company_line(node, cache, registry, as_of=as_of)}
                else:
                    hops[node] = {**base, "absence": absent("unknown_node_kind")}
    return {"paths_by_company": paths_by_company, "hops": hops, "companies": companies, "as_of": as_of.isoformat()}


__all__ = ["path_context"]
