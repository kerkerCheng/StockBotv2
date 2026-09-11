"""一手取得路徑的唯一 loader（`config/source_routes.json`）。

## 為什麼是程式不是一張表

2026-09-11 一個 session 內三次把「我沒試」講成「拿不到」（深交所 API、pypdf、MOPS
fetcher 都早就可用）。第一版的修法是「park 前填一張 checklist」——但那張表要我自己勾，
我可以勾「試過 SZSE」而沒真的試，等於回到原點。使用者當場點出這是自律不是機制。

所以規則落在這裡：**哪些路存在由 config 回答，park 時要附的是這支程式產生的 receipt，
不是執行者的自陳。**（修法層級：根除——自律版本擋不住沒試就宣稱試過。）

## 不做的事

不下載、不解析、不判斷證據強度。它只回答「有哪些路、各自怎麼走、試了沒」。
真正抓檔的是 `fetchers/*`；tier 與獨立性判準仍在 L8／`lead_trace_status`，本模組不碰。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "config" / "source_routes.json"


class SourceRouteError(ValueError):
    """config 缺漏、違反封閉性，或 receipt 不合格。"""


@dataclass(frozen=True, slots=True)
class Route:
    key: str
    label: str
    rung: int
    applies_to: str
    tier_cap: int
    verified: bool
    how: str
    why: str
    venues: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()
    foreign_suffixes: tuple[str, ...] = ()

    def applies(self, *, ticker: str | None, venue: str | None) -> bool:
        if self.applies_to == "always":
            return True
        if self.applies_to == "venue":
            return bool(venue) and venue.upper() in self.venues
        if self.applies_to == "ticker_suffix":
            return bool(ticker) and any(ticker.upper().endswith(s) for s in self.suffixes)
        if self.applies_to == "ticker_no_foreign_suffix":
            # 離線近似，方向刻意偏向多列：漏一條的代價遠大於多跑一次 probe。
            return bool(ticker) and not any(
                ticker.upper().endswith(s) for s in self.foreign_suffixes)
        raise SourceRouteError(f"未登記的 applies_to：{self.applies_to!r}")


@dataclass(frozen=True, slots=True)
class RouteRegistry:
    routes: tuple[Route, ...]
    file_formats: Mapping[str, Mapping[str, Any]]
    park_requires_receipt_when: frozenset[str]
    path: Path = DEFAULT_PATH

    def applicable(self, *, ticker: str | None = None, venue: str | None = None) -> tuple[Route, ...]:
        """這個標的可以走哪幾條，依 rung 由淺到深排序。"""
        hit = [r for r in self.routes if r.applies(ticker=ticker, venue=venue)]
        return tuple(sorted(hit, key=lambda r: (r.rung, r.key)))

    def requires_receipt(self, trace_status: str | None) -> bool:
        """這個 trace_status 是「我沒拿到」型嗎？是 → park 必須附 receipt。"""
        return str(trace_status or "") in self.park_requires_receipt_when

    def missing_rungs(self, attempted: Iterable[str], *, ticker: str | None = None,
                      venue: str | None = None) -> tuple[Route, ...]:
        """可以走、但這次沒走的那幾條——**這就是「你還沒試」的清單**。"""
        tried = {str(a).strip() for a in attempted}
        return tuple(r for r in self.applicable(ticker=ticker, venue=venue) if r.key not in tried)


def load(path: Path | str | None = None) -> RouteRegistry:
    target = Path(path) if path else DEFAULT_PATH
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SourceRouteError(f"{target} 不存在——路徑表缺席時不得放行任何 park") from exc
    except json.JSONDecodeError as exc:
        raise SourceRouteError(f"{target} 不是合法 JSON：{exc}") from exc
    if payload.get("schema_version") != 1:
        raise SourceRouteError("source_routes schema_version 必須是 1")
    raw = payload.get("routes")
    if not isinstance(raw, list) or not raw:
        raise SourceRouteError("routes 必須是非空 list——空表等於「沒有路可走」，那是假的")
    routes: list[Route] = []
    seen: set[str] = set()
    for item in raw:
        key = str(item.get("key") or "").strip()
        if not key:
            raise SourceRouteError("route 缺 key")
        if key in seen:
            raise SourceRouteError(f"route key 重複：{key}")
        seen.add(key)
        for required in ("label", "rung", "applies_to", "tier_cap", "verified", "how", "why"):
            if required not in item:
                raise SourceRouteError(f"route {key} 缺 {required!r}")
        routes.append(Route(
            key=key, label=str(item["label"]), rung=int(item["rung"]),
            applies_to=str(item["applies_to"]), tier_cap=int(item["tier_cap"]),
            verified=bool(item["verified"]), how=str(item["how"]), why=str(item["why"]),
            venues=tuple(str(v).upper() for v in item.get("venues") or ()),
            suffixes=tuple(str(s).upper() for s in item.get("suffixes") or ()),
            foreign_suffixes=tuple(
                str(s).upper() for s in item.get("foreign_suffixes") or ()),
        ))
    # 至少要有一條 always 路徑，否則某些標的會「一條路都沒有」而靜默通過檢查。
    if not any(r.applies_to == "always" for r in routes):
        raise SourceRouteError("至少要有一條 applies_to=always 的路徑")
    gate = payload.get("park_requires_receipt_when_trace_status_in")
    if not isinstance(gate, list) or not gate:
        raise SourceRouteError(
            "park_requires_receipt_when_trace_status_in 不得為空——空集合代表「park 永遠不必交代」")
    from engine_b.lead_refs import get_trace_status_registry

    known = get_trace_status_registry()
    for name in gate:
        known.resolve(str(name), allow_alias=False)   # 未登記的 trace_status 直接拒絕載入
    return RouteRegistry(
        routes=tuple(routes),
        file_formats=dict(payload.get("file_formats") or {}),
        park_requires_receipt_when=frozenset(str(g) for g in gate),
        path=target,
    )


def venue_for(ticker: str) -> str | None:
    """從 registry 取 execution_venue（INV-1：走 registry，不從 ticker 猜）。"""
    from identity.registry import get_registry

    reg = get_registry()
    company_id = reg.company_id_for_ticker(ticker.strip().upper())
    if not company_id:
        return None
    entry = reg.company(company_id)
    return getattr(entry, "execution_venue", None) if entry else None


def render(routes: Sequence[Route], *, attempted: Iterable[str] = ()) -> list[str]:
    """人看的清單：試過的打勾，沒試的留白——**留白就是「你還沒試」**。"""
    tried = {str(a).strip() for a in attempted}
    out = []
    for r in routes:
        mark = "✓" if r.key in tried else "·"
        note = "" if r.verified else "（未驗證，跑之前先確認它還通）"
        out.append(f"{mark} rung{r.rung} {r.key}｜{r.label}｜tier≤{r.tier_cap}{note}")
        if r.key not in tried:
            out.append(f"    怎麼走：{r.how}")
    return out


def build_receipt(ticker: str, attempted: Iterable[str], *, outcome: str = "") -> str:
    """把「這個標的有哪些路、我走了哪幾條」壓成一行可存進 lead ref 的收據。

    ⚠ 它**不驗證你真的跑了**——沒有任何程式能驗證那件事。它做的是把「還沒走的那幾條」
    逐條寫進收據，讓漏掉的路在 park 紀錄裡**具名**。自陳「我試過了」可以造假，
    但「rung2 szse 未走」這行留在 receipt 裡，下一個 session 一眼就看得到。
    """
    registry = load()
    venue = venue_for(ticker)
    applicable = registry.applicable(ticker=ticker, venue=venue)
    missing = registry.missing_rungs(attempted, ticker=ticker, venue=venue)
    tried = ",".join(sorted({str(a).strip() for a in attempted if str(a).strip()})) or "無"
    gap = ",".join(f"{r.key}(rung{r.rung}{'/未驗證' if not r.verified else ''})" for r in missing) or "無"
    tail = f"；結果={outcome}" if outcome else ""
    return (f"ticker={ticker};適用={len(applicable)}條;已走={tried};未走={gap}{tail}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="這個標的有哪些一手取得路徑、哪幾條還沒走")
    ap.add_argument("ticker")
    ap.add_argument("--attempted", default="", help="逗號分隔的已走路徑 key")
    ap.add_argument("--outcome", default="", help="一句話結果，寫進收據")
    ap.add_argument("--receipt", action="store_true", help="只印收據字串（給 --ref 用）")
    args = ap.parse_args(argv)
    attempted = [a for a in args.attempted.split(",") if a.strip()]
    if args.receipt:
        print(build_receipt(args.ticker, attempted, outcome=args.outcome))
        return 0
    registry = load()
    venue = venue_for(args.ticker)
    rows = registry.applicable(ticker=args.ticker, venue=venue)
    print(f"# {args.ticker}（venue={venue}）可走 {len(rows)} 條，✓＝本次已走")
    for line in render(rows, attempted=attempted):
        print(line)
    fmt = registry.file_formats.get("pdf") or {}
    if fmt:
        print()
        print(f"# 檔案格式：PDF {'可解' if fmt.get('verified') else '未驗證'}——{fmt.get('how')}")
    print()
    print(f"收據：{build_receipt(args.ticker, attempted, outcome=args.outcome)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Route", "RouteRegistry", "SourceRouteError", "build_receipt",
           "load", "main", "render", "venue_for"]
