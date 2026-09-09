"""decompose 提案自動鑄號（研究閉環 P∥；2026-09-09 使用者定案「分散度優先於主線」）。

## 這一層做什麼、不做什麼

`system-decompose` 是系統裡唯一能長出「圖裡根本沒這個節點」的機制，但選題今天全靠使用者想起來。
本模組把**提案**變成機械流程，**核准仍逐題**（decompose 選題不在常規授權清單，見
`config/standing_authorization.json` 的 never／`AGENTS.md`「常規授權類別」）：

- **提名**（系統名、需求錨、為什麼是新錨、哪條 lead 點名）由 research-drain／weekly／使用者貼入的 lead
  產生——那是語意工作，LLM 可以解析與提議；本模組只驗兩件機械的事，然後鑄一個 `manual` 型 pq2 編號。
- **廣度判準是機械的**：需求錨不在 `config/sector_anchors.json` 既有各組、**且**頂層節點不在圖裡
  （用 coverage state artifact 的節點清單當圖的快照，不連 Neo4j）。兩者都不成立就是深度題，
  該走 `coverage_gaps`，不鑄 decompose 提案。
- **防噪音**（「建議只由 pool ground truth 導出」）：同時 open 的提案 ≤ `MAX_OPEN`；使用者 `drop`
  過的系統，除非有**新的** lead 點名，否則不重生。

`go` 只授權跑 `system-decompose`（研究地圖，不入圖、不 onboard、不提高 tier）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
SECTOR_ANCHORS_PATH = ROOT / "config" / "sector_anchors.json"
REF_PREFIX = "decompose:"
MAX_OPEN = 2
SOURCE = "decompose_proposal"


class DecomposeProposalError(ValueError):
    """提案被機械判準擋下（不是新錨、已 drop 過、open 已滿）。"""


def slugify(system: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", system.strip().lower()).strip("_")
    if not slug:
        raise DecomposeProposalError("系統名稱不能為空")
    return slug[:60]


# ---------------------------------------------------------------------------
# 廣度判準（機械）
# ---------------------------------------------------------------------------

def load_known_anchors(path: Path | None = None) -> dict[str, str]:
    """需求錨 id → 產業組名（`config/sector_anchors.json` 是唯一 SSOT）。"""
    payload = json.loads((path or SECTOR_ANCHORS_PATH).read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for sector, anchors in (payload.get("sectors") or {}).items():
        for anchor in anchors or ():
            out[str(anchor)] = str(sector)
    return out


def graph_nodes_from_coverage(payload: Mapping[str, Any]) -> frozenset[str]:
    """coverage state artifact 裡出現過的節點 id（covered／modelling_gaps／research_gaps／concept）。"""
    nodes: set[str] = set()
    for key in ("covered", "modelling_gaps", "research_gaps", "concept"):
        for row in payload.get(key) or ():
            node = row.get("node") if isinstance(row, Mapping) else row
            if node:
                nodes.add(str(node))
    return frozenset(nodes)


@dataclass(frozen=True)
class BreadthCheck:
    adds_breadth: bool
    anchor_known_in_sector: str | None
    node_in_graph: bool | None       # None＝圖快照讀不到
    reason: str


def breadth_check(anchor: str, *, known_anchors: Mapping[str, str],
                  graph_nodes: frozenset[str] | None) -> BreadthCheck:
    sector = known_anchors.get(anchor)
    in_graph = None if graph_nodes is None else (anchor in graph_nodes)
    if sector is not None:
        return BreadthCheck(False, sector, in_graph,
                            f"需求錨 {anchor} 已屬產業組「{sector}」——這是深度題，走 coverage_gaps，不是新錨")
    if in_graph:
        return BreadthCheck(False, None, True,
                            f"頂層節點 {anchor} 已在圖裡（coverage 快照）——請改 decompose 一台以它為錨的實體，或走 coverage_gaps")
    note = "（圖快照讀不到，只驗了產業組）" if in_graph is None else ""
    return BreadthCheck(True, None, in_graph, f"需求錨 {anchor} 不在任何產業組、不在圖裡——是新錨{note}")


# ---------------------------------------------------------------------------
# pool ground truth：open 幾個、drop 過沒有
# ---------------------------------------------------------------------------

def open_proposals(pool: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [it for it in pool.get("items", ())
            if it.get("type") == "manual" and str(it.get("ref_id", "")).startswith(REF_PREFIX)
            and not it.get("resolved_at")]


def dropped_before(pool: Mapping[str, Any], slug: str) -> dict[str, Any] | None:
    ref = REF_PREFIX + slug
    hits = [it for it in pool.get("items", ())
            if it.get("ref_id") == ref and it.get("resolved_at") and it.get("resolution") == "drop"]
    return hits[-1] if hits else None


def _lead_ids_in(item: Mapping[str, Any]) -> set[str]:
    return set(re.findall(r"lead_[0-9a-f]{8,}", str(item.get("hint") or "")))


def build_hint(*, system: str, anchor: str, why_new_anchor: str, lead_ids: Sequence[str],
               layers_estimate: int | None, check: BreadthCheck) -> str:
    leads_text = "、".join(lead_ids) if lead_ids else "（無 lead；由 weekly／使用者提名）"
    layers = f"預估拆出 {layers_estimate} 層" if layers_estimate else "層數未估"
    return (
        f"decompose 提案（自動鑄號，核准逐題）｜系統：{system}｜需求錨：{anchor}｜為什麼是新錨：{why_new_anchor}"
        f"｜廣度判準：{check.reason}｜點名來源：{leads_text}｜{layers}"
        "｜go＝跑 skills/system-decompose 產出研究地圖（選題理由＝本提案），不含入圖、不含 onboard、不含提高 evidence tier、不含 live"
        "｜drop＝本系統不再重提，除非新 lead 再點名"
    )


def propose(
    pool: dict[str, Any],
    *,
    system: str,
    anchor: str,
    why_new_anchor: str,
    lead_ids: Iterable[str] = (),
    layers_estimate: int | None = None,
    known_anchors: Mapping[str, str] | None = None,
    graph_nodes: frozenset[str] | None = None,
    at: str | None = None,
) -> dict[str, Any]:
    """通過三道機械判準後鑄一個 `manual` 型 pq2 編號；任何一道不過就 raise，不鑄。"""
    from engine_b import todo

    slug = slugify(system)
    lead_ids = [str(x) for x in lead_ids if str(x).strip()]
    if not why_new_anchor.strip():
        raise DecomposeProposalError("必須寫『為什麼是新錨』——選題理由要留在輸出裡（system-decompose 的誠實限制）")
    check = breadth_check(anchor, known_anchors=known_anchors if known_anchors is not None else load_known_anchors(),
                          graph_nodes=graph_nodes)
    if not check.adds_breadth:
        raise DecomposeProposalError(check.reason)
    prior = dropped_before(pool, slug)
    if prior is not None:
        new_leads = set(lead_ids) - _lead_ids_in(prior)
        if not new_leads:
            raise DecomposeProposalError(
                f"系統「{system}」使用者已 drop（[{prior.get('n')}]），且沒有新的 lead 點名——不重生（pool ground truth）")
    opened = open_proposals(pool)
    if any(it.get("ref_id") == REF_PREFIX + slug for it in opened):
        return next(it for it in opened if it.get("ref_id") == REF_PREFIX + slug)     # 冪等：同題已 open
    if len(opened) >= MAX_OPEN:
        raise DecomposeProposalError(
            f"同時 open 的 decompose 提案已達 {MAX_OPEN}（{[it.get('n') for it in opened]}）——先讓使用者決定那幾題")
    hint = build_hint(system=system, anchor=anchor, why_new_anchor=why_new_anchor, lead_ids=lead_ids,
                      layers_estimate=layers_estimate, check=check)
    return todo.upsert(pool, item_type="manual", ref_id=REF_PREFIX + slug,
                       title=f"decompose 提案：{system}（新需求錨 {anchor}）", hint=hint, source=SOURCE, at=at)


__all__ = [
    "MAX_OPEN", "REF_PREFIX", "SOURCE", "BreadthCheck", "DecomposeProposalError", "breadth_check",
    "build_hint", "dropped_before", "graph_nodes_from_coverage", "load_known_anchors", "open_proposals",
    "propose", "slugify",
]
