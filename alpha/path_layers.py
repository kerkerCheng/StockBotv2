"""路徑上各層（個股頁 S3c，2026-10-09；B2「需求傳導」）——**純函式**。取數住 `alpha/providers/path_layers.py`。

**問的是：** AI 的錢從需求錨一路往下，經過的每一層有沒有在長？每一頁的路徑＝結構表裡這家公司從需求錨走到它坐的層的鏈
（`query.bottleneck` 的 `chain`：錨 → … → 瓶頸節點）。

**路徑怎麼取（`company_paths`）：**
- 鏈裡有本頁公司（「退回公司才走到錨」的列、或經過本公司的依賴邊）：只取公司之前那一段——那是錢流到它之前經過的層。
- 鏈裡沒有本頁公司、關係是供貨：整條都收，終點就是它供貨進去的那一層（或客戶）。
- 鏈不經過本頁公司的依賴或受限邊：不收（那答的是「它的上游接到哪」，不是它坐的層），計數照報（INV-3）。

**每一節怎麼算（`hop_line`）：**
- 錨：照抄 B2「錨的變化」那一條序列的最新年增（不另算）。
- 層（tech:／mat:／comp:）與產品（prod:）：研究宣告的代表公司（`alpha/layer_rep`）同一曆季的營收換美元、加總、算年增；
  **年增只算這一季與去年同季都有值的那幾家**（固定成分），其餘逐家寫缺什麼；成員是空的那一季沒有值。沒宣告＝具名缺席，
  不拿坐這一層的全部公司或只坐這一層的公司頂替（使用者 2026-10-09 ②A；被否決的 B、C 見個股頁 plan Amendment G）。
- 公司節點（co:）：它自己的整家營收、它自己的季，不用宣告；年增比的是去年同一季（期末差一年 ±10 天），兩期長度差超過
  5 天（14 週的季）不算（與「吃到多少」同一條長度規則）。必印「整家公司營收（含不走這條路的業務）」。

只照抄、不排序、不打分、沒有門檻；缺席由這裡宣告種類與原因（L16），頁面照印。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable, Mapping, Sequence

from alpha.demand_anchor import CALENDAR_SLACK_DAYS, PERIOD_LENGTH_SLACK_DAYS

#: 節點前綴 → 種類（封閉字彙；未登記的前綴不猜）。
NODE_KINDS: Mapping[str, str] = {"tech": "layer", "mat": "layer", "comp": "layer", "prod": "product", "co": "company"}
KIND_LABELS: Mapping[str, str] = {"anchor": "需求錨", "layer": "層", "product": "產品", "company": "公司"}

#: 一節沒有年增時的原因（封閉字彙：code → (缺席種類, 給人讀的一句)）。
HOP_ABSENCES: Mapping[str, tuple[str, str]] = {
    "no_representatives_declared": ("not_yet_recorded", "還沒宣告代表公司"),
    "nobody_sits": ("not_yet_recorded", "還沒宣告代表公司（圖上也沒有公司坐這一層）"),
    "declarations_unread": ("upstream_unavailable", "這一輪沒讀到代表公司宣告"),
    "no_complete_quarter": ("not_yet_recorded", "代表公司沒有一季是今年與去年同季都有營收的"),
    "company_no_revenue": ("provider_missing", "這家公司的季營收還沒接（不是台股月營收、也沒有 EDGAR 季營收）"),
    # 日韓財報來源 S2（2026-10-21）：日本有營收、只是沒有季——「還沒接」是錯的那句（L11-5）
    "company_semiannual_only": ("inputs_incompatible", "這家公司只有半年營收（日本 2024-04 起沒有季報）——對不上曆季，不估年增"),
    "company_unlisted": ("provider_missing", "未上市或名冊沒有代號"),
    "company_not_in_registry": ("not_yet_recorded", "名冊沒有這家公司"),
    "company_no_yoy": ("not_yet_recorded", "這家公司沒有一季找得到可比的去年同季"),
    "anchor_no_series": ("not_yet_recorded", "這個錨沒有宣告序列"),
    "unknown_node_kind": ("capability_absent", "不認得的節點種類"),
}
#: 整頁沒有路徑時的原因。
PAGE_ABSENCES: Mapping[str, tuple[str, str]] = {
    "structure_unread": ("upstream_unavailable", "這一輪沒讀到結構表"),
    "point_in_time": ("point_in_time_unavailable", "回看的那天沒有當時的結構表與代表公司宣告——不拿今天的冒充（INV-6）"),
    "not_in_structure": ("not_yet_recorded", "結構表裡沒有這家公司的邊"),
    "no_path": ("not_yet_recorded", "從它坐的層走不到需求錨（只有依賴邊，或圖上走不上去）"),
    "sits_on_anchor": ("method_not_applicable", "它直接坐在需求錨上——中間沒有別的層"),
}
COMPANY_PROXY = "整家公司營收（含不走這條路的業務）"


def node_kind(node: str) -> str | None:
    return NODE_KINDS.get(str(node).split(":", 1)[0])


def company_paths(rows: Iterable[Mapping[str, Any]], company_id: str) -> tuple[list[tuple[str, ...]], dict[str, int]]:
    """這家公司的路徑（錨在前、去重、依首次出現的順序）與丟掉的列數 `{no_chain, input_side}`。"""
    paths: list[tuple[str, ...]] = []
    dropped = {"no_chain": 0, "input_side": 0}
    for row in rows:
        if str(row.get("company_id")) != company_id:
            continue
        chain = [str(n) for n in row.get("chain") or ()]
        if not chain:
            dropped["no_chain"] += 1
            continue
        if company_id in chain:
            path = tuple(chain[:chain.index(company_id)])
        elif row.get("relation") == "supplies_to":
            path = tuple(chain)
        else:
            dropped["input_side"] += 1
            continue
        if path and path not in paths:
            paths.append(path)
    return paths, dropped


def layer_yoy(quarters_usd: Mapping[str, Mapping[str, Mapping[str, Any]]], declared: Sequence[str],
              unavailable: Mapping[str, str], *, as_of: date) -> dict[str, Any]:
    """一層的曆季年增：代表公司美元營收加總，**每一季只算那一季與去年同季都有值、可知日 ≤ as_of 的那幾家**。

    `quarters_usd`：co → {季: {usd, known_on}}；`unavailable`：整家算不出來的原因（分部還沒有序列、沒有季營收…）。
    回 `{points: [{period, yoy, members, missing: [{company, reason}], coverage, known_on}], gaps}`（期別升序）。"""
    labels = sorted({label for table in quarters_usd.values() for label in table})
    points: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for label in labels:
        year, q = int(label[:4]), label[-1]
        prior = f"{year - 1}Q{q}"
        members, missing = [], []
        known: list[str] = []
        for co in declared:
            if co in unavailable:
                missing.append({"company": co, "reason": unavailable[co]})
                continue
            table = quarters_usd.get(co) or {}
            now, then = table.get(label), table.get(prior)
            if now is None or then is None:
                missing.append({"company": co, "reason": f"缺 {label if now is None else prior}"})
                continue
            stamp = max(str(now["known_on"]), str(then["known_on"]))
            if stamp > as_of.isoformat():
                missing.append({"company": co, "reason": f"as-of {as_of.isoformat()} 時還不可知（{stamp} 才齊）"})
                continue
            members.append(co)
            known.append(stamp)
        if not members:
            gaps.append({"period": label, "reason": "；".join(f"{m['company']} {m['reason']}" for m in missing)})
            continue
        now_sum = sum(float(quarters_usd[co][label]["usd"]) for co in members)
        prior_sum = sum(float(quarters_usd[co][prior]["usd"]) for co in members)
        if not prior_sum:
            gaps.append({"period": label, "reason": "去年同季合計是 0——年增沒有定義"})
            continue
        points.append({"period": label, "yoy": now_sum / prior_sum - 1, "members": members, "missing": missing,
                       "coverage": f"{len(members)}/{len(declared)}", "known_on": max(known)})
    return {"points": points, "gaps": gaps}


def fiscal_yoy(rows: Sequence[Mapping[str, Any]], first: Mapping[str, str], *, as_of: date) -> dict[str, Any]:
    """一家公司自己的季（`fundamental_series` 每期最新版本）的年增：比去年同一季（期末差 365 天 ±10 天）；兩期長度差超過
    5 天不算（14 週的季多一週——與「吃到多少」同一條長度規則的單一公司面）。回 `{points: [{period, yoy, known_on}], gaps}`。"""
    def length(row: Mapping[str, Any]) -> int | None:
        if not row.get("period_start"):
            return None
        return (date.fromisoformat(str(row["period_end"])[:10]) - date.fromisoformat(str(row["period_start"])[:10])).days + 1

    by_end = {date.fromisoformat(str(r["period_end"])[:10]): r for r in rows}
    points: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for end, row in sorted(by_end.items()):
        target = end - timedelta(days=365)
        near = [e for e in by_end if abs((e - target).days) <= CALENDAR_SLACK_DAYS]
        prior = by_end[min(near, key=lambda e: (abs((e - target).days), e))] if near else None   # 取最近的那一期（R2 非阻擋）
        if prior is None:
            continue
        if str(row.get("currency")) != str(prior.get("currency")):
            gaps.append({"period": end.isoformat(), "reason": "兩期幣別不同——不比"})
            continue
        a, b = length(row), length(prior)
        if a is None or b is None or abs(a - b) > PERIOD_LENGTH_SLACK_DAYS:
            gaps.append({"period": end.isoformat(), "reason": f"兩期長度不同（{a} 天 vs {b} 天）——多一週的季不比"})
            continue
        known_on = max(first.get(end.isoformat(), str(row["filed"])[:10]),
                       first.get(str(prior["period_end"])[:10], str(prior["filed"])[:10]))
        if known_on > as_of.isoformat() or not float(prior["value"]):
            continue
        points.append({"period": end.isoformat(), "yoy": float(row["value"]) / float(prior["value"]) - 1,
                       "known_on": known_on, "currency": str(row.get("currency"))})
    return {"points": points, "gaps": gaps}


def calendar_yoy(quarters: Mapping[str, Mapping[str, Any]], *, as_of: date) -> dict[str, Any]:
    """一家公司自己的曆季（台股月營收三個月成季）的年增，本幣計（單一公司不需要換匯）。"""
    points, gaps = [], []
    for label, q in sorted(quarters.items()):
        prior = quarters.get(f"{int(label[:4]) - 1}Q{label[-1]}")
        if prior is None:
            continue
        known_on = max(str(q["known_on"]), str(prior["known_on"]))
        if known_on > as_of.isoformat() or not float(prior["value"]):
            continue
        points.append({"period": label, "yoy": float(q["value"]) / float(prior["value"]) - 1, "known_on": known_on,
                       "currency": str(q.get("currency"))})
    return {"points": points, "gaps": gaps}


def absent(code: str, table: Mapping[str, tuple[str, str]] = HOP_ABSENCES, reason: str | None = None) -> dict[str, str]:
    kind, text = table[code]
    return {"kind": kind, "code": code, "reason": reason or text}


def page_path(paths: Sequence[tuple[str, ...]], dropped: Mapping[str, int], hops: Mapping[str, Mapping[str, Any]],
              *, page_company: str, focus: Iterable[str] = (), in_structure: bool = True) -> dict[str, Any]:
    """一頁的路徑上各層：`{paths: [{nodes, focus}], hops: {node: line}, counts, absence}`。押的格（`focus`）那幾條排前面，
    其餘照首次出現的順序——索引不是名次。`hops` 只帶這一頁路徑上的節點（各層一輪只算一次，頁與頁共用）。"""
    want = set(focus)
    if not in_structure:
        return {"paths": [], "hops": {}, "counts": {"paths": 0, **dropped}, "absence": absent("not_in_structure", PAGE_ABSENCES)}
    if not paths:
        return {"paths": [], "hops": {}, "counts": {"paths": 0, **dropped}, "absence": absent("no_path", PAGE_ABSENCES)}
    ordered = sorted(paths, key=lambda p: (not (want & set(p)), paths.index(p)))
    nodes = [n for p in ordered for n in p[1:]]
    if not nodes:
        return {"paths": [{"nodes": list(p), "focus": bool(want & set(p))} for p in ordered], "hops": {},
                "counts": {"paths": len(paths), **dropped}, "absence": absent("sits_on_anchor", PAGE_ABSENCES)}
    page_hops = {n: dict(hops[n]) for p in ordered for n in p if n in hops}
    for line in page_hops.values():          # 代表公司裡有本頁公司：那一層的成長含它自己（照標，不拿掉）
        line["includes_page_company"] = any(r.get("company_id") == page_company
                                            for r in line.get("representatives") or ())
    valued = sorted({n for n in nodes if (page_hops.get(n) or {}).get("latest")})
    return {"paths": [{"nodes": list(p), "focus": bool(want & set(p))} for p in ordered], "hops": page_hops,
            "counts": {"paths": len(paths), "hops": len(set(nodes)), "valued": len(valued), **dropped},
            "valued_nodes": valued, "absence": None}


__all__ = ["COMPANY_PROXY", "HOP_ABSENCES", "KIND_LABELS", "NODE_KINDS", "PAGE_ABSENCES", "absent", "calendar_yoy",
           "company_paths", "fiscal_yoy", "layer_yoy", "node_kind", "page_path"]
