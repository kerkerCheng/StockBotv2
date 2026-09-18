"""`python -m query.structure <node>` — 把一個節點的五個結構角度一次查出來。

## 為什麼需要它

**瓶頸性不是一條邊。** 2026-09-17 實測：「CW DFB laser 是不是瓶頸」的答案是由四個不同角度的邊
湊出來的，沒有任何一條邊自己說得出來——

| 角度 | 實際的邊 | 值 | 單獨看會誤導成 |
|---|---|---|---|
| 需求側 | `tech:pluggable_transceiver` depends_on 它 | sub 4 | 「這是個大瓶頸」 |
| 供給側 | 六家 supplies_to 它 | 4–5／3／3／2／2／2 | 「沒人卡住，不重要」 |
| 下一層 | 它 depends_on `mat:inp_substrate` | sub 5 | — |
| 反向 | `prod:blazar` competes_with 它 | — | — |

四條放在一起才是答案：**技術繞不掉、但供應層競爭、而且更卡的在它下游**
——那是「量的賭注」的形狀，不是「護城河」的形狀。

而這件事今天**沒有任何 owner**：`rank_bottlenecks()` 一次只看一條邊（而且只看 `src` 為 `co:` 的
向下邊，所以技術層那條 sub=4 結構上讀不到）。把四條邊讀在一起只在互動 session 裡臨時發生，
做完就散。本模組把「來回查圖」從十幾次手打查詢變成一條命令。

## 它明確不做的事

- **零 LLM、零推理、零判斷。** 它只把五個角度的邊查出來排好——**A 還是 B 由人（或互動 session
  的 LLM）讀完之後判斷**，不由本模組決定。
- **不過濾、不排序、不給分數。** `rank_bottlenecks()` 仍是唯一排序權威；本模組不產生第二套排序。
- **不寫任何 authority。** 純讀。

## 維護：存輸入，不存結論

`--json` 的輸出帶一個 `result_digest`，它是**五個角度的查詢結果**的指紋，不是「我讀過哪幾條邊」
的清單。這個分別是刻意的：**最危險的變化是「多了一條我當初沒讀到的邊」**——
例如有人替 CW laser 補上第七家供應商，供給側分布就變了、A/B 判讀可能翻轉。
存「我讀過這四條」偵測不到它；存「這五條查詢當時回這個集合」偵測得到。

所以 staleness 偵測是**零 LLM 的**：重跑一次、比 digest。只有真的變了才需要重新推理。

⚠ **界線要講清楚**：這套機制維護的是「**讀圖結論跟圖還一不一致**」，
**不是「讀圖結論對不對」**。對不對要靠 outcome 量測。一份跟圖完全一致但判斷錯誤的讀圖，
這套機制永遠不會叫——那是設計如此，不是漏洞。

用法：

    python -m query.structure tech:cw_dfb_laser
    python -m query.structure tech:cw_dfb_laser --json      # 給讀圖紀錄用，帶 result_digest
    python -m query.structure tech:cw_dfb_laser --digest     # 只印 digest（給 staleness 比對）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from query.bottleneck import (  # noqa: E402
    DEMAND_PULL_RELATIONS, DEPENDENCY_RELATIONS, CanonicalEdge, build_upward_index,
    collapse_assertions, demand_chain, fetch_assertions,
)

#: 五個角度是**封閉清單**，而且不是憑空設計的——前四個直接來自 2026-09-17 那次
#: 真的問出答案的四次查詢，第五個是排序本來就有的可達性檢查。
#: ⚠ 要加第六個角度前先問：它在哪一個實際案例裡改變過結論？答不出來就不要加（L17-4）。
ANGLES: tuple[tuple[str, str], ...] = (
    ("demand_side", "需求側：誰需要它、繞不繞得過"),
    ("supply_side", "供給側：誰供它、有沒有人獨佔"),
    ("next_layer", "下一層：它自己卡在誰身上"),
    ("counter_path", "反向路徑：有沒有東西在取代它"),
    ("anchor", "需求錨：走不走得到有人花錢的地方"),
)

#: 哪些 relation 算「需求側」——與 `build_upward_index` 同一組語意，但這裡是**看向這個節點**：
#: `A depends_on N` ⇒ A 需要 N；`N is_component_of B` ⇒ B 需要 N。
#:
#: ⚠ inbound 那一族**直接消費 `DEPENDENCY_RELATIONS`，不自己列**。2026-09-18 之前
#: 這裡硬編 `("depends_on",)`，與 `build_upward_index` 的分支各一份，於是
#: `constrained_by` 在兩處同時缺席——同一個分類有 SSOT 卻沒跟著資料走到需要它的地方（L16）。
#: 實測影響：`tech:inp_dfb_laser` 的需求側原本看不到 `co:coherent`，而那條邊一直都在圖裡。
#: ⚠ `enables` 於 2026-09-18 由 outbound 改成 inbound：`X enables N` 逐字是
#: 「X 的採用帶動對 N 的需求」⇒ **X 需要 N**，所以它看向 N 時是需求側的 inbound；
#: 先前放在 outbound（`N enables X`）方向剛好相反。與 `query/bottleneck.py` 的
#: `DEMAND_PULL_RELATIONS` 是同一個決定，兩邊都從那裡讀，不各寫一份（L16）。
_DEMAND_INBOUND = tuple(DEPENDENCY_RELATIONS) + tuple(DEMAND_PULL_RELATIONS)
_DEMAND_OUTBOUND = ("is_component_of",)
_COUNTER = ("competes_with", "constrained_by")


@dataclass
class EdgeView:
    src: str
    relation: str
    dst: str
    substitutability: int | None
    sole_source: bool | None
    qualification_status: str | None
    evidence: str | None
    documents: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "src": self.src, "relation": self.relation, "dst": self.dst,
            "substitutability": self.substitutability, "sole_source": self.sole_source,
            "qualification_status": self.qualification_status,
            "evidence": self.evidence, "documents": self.documents,
        }

    def key(self) -> tuple:
        """進 digest 的欄位——**值變了就算變**，不只是邊在不在。"""
        return (self.src, self.relation, self.dst, self.substitutability,
                self.sole_source, self.qualification_status, self.evidence)


@dataclass
class StructureView:
    node: str
    angles: dict[str, list[EdgeView]] = field(default_factory=dict)
    anchor_chain: list[str] | None = None

    def result_digest(self) -> str:
        """五個角度**查詢結果**的指紋。

        ⚠ 排序過才 hash——邊的回傳順序不保證穩定，不排序會讓 digest 每次都不同，
        那會讓 staleness 偵測恆亮（L14-4「恆亮＝零鑑別力」）。
        """
        payload = {
            name: sorted(str(e.key()) for e in self.angles.get(name, ()))
            for name, _ in ANGLES if name != "anchor"
        }
        payload["anchor"] = list(self.anchor_chain or [])
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "node": self.node,
            "angles": {
                name: [e.as_dict() for e in self.angles.get(name, ())]
                for name, _ in ANGLES if name != "anchor"
            },
            "anchor_chain": self.anchor_chain,
            "result_digest": self.result_digest(),
            "this_is_not": (
                "這是五個角度的邊，不是判斷。A（護城河）還是 B（量）由讀的人決定；"
                "本模組不過濾、不排序、不給分數、不寫任何 authority。"
            ),
        }


def _view(edge: CanonicalEdge) -> EdgeView:
    return EdgeView(
        src=edge.src, relation=edge.relation, dst=edge.dst,
        substitutability=edge.substitutability, sole_source=edge.sole_source,
        qualification_status=edge.qualification_status,
        evidence=edge.evidence, documents=edge.documents,
    )


def build_structure(node: str, edges: Iterable[CanonicalEdge]) -> StructureView:
    """把一個節點的五個角度查出來。**不判斷、不排序、不過濾。**"""
    edges = list(edges)
    view = StructureView(node=node)

    view.angles["demand_side"] = [
        _view(e) for e in edges
        if (e.dst == node and e.relation in _DEMAND_INBOUND)
        or (e.src == node and e.relation in _DEMAND_OUTBOUND)
    ]
    view.angles["supply_side"] = [
        _view(e) for e in edges
        if e.dst == node and e.relation == "supplies_to"
    ]
    # 「它自己卡在誰身上」有兩種寫法，兩種都要收：
    #   ① `N depends_on／constrained_by X` ⇒ N 卡在 X（`DEPENDENCY_RELATIONS`）
    #   ② `A is_component_of N`           ⇒ A 是 N 的零件 ⇒ N 卡在 A
    # ⚠ 2026-09-18 之前只收①，於是**全圖 68 條 `is_component_of` 在 dst 側 100% 看不見**
    # ——`tech:isolator` 的五個角度全空、`tech:cpo` 的下一層只有 4 條（實際 21 條）。
    # 這與同日修掉的 `constrained_by` 是同一族：一個角度的成員資格漏了一半，
    # 而漏掉的那一半不會讓任何東西變紅（L17-3 的對稱面）。
    # 放閘前量過：digest 會變的節點 **35／282**，`tech:cw_dfb_laser` 的讀圖因此轉 stale
    # ——那是 staleness 偵測正常運作，不是壞掉。
    view.angles["next_layer"] = [
        _view(e) for e in edges
        if (e.src == node and e.relation in DEPENDENCY_RELATIONS)
        or (e.dst == node and e.relation == "is_component_of")
    ]
    view.angles["counter_path"] = [
        _view(e) for e in edges
        if (e.dst == node or e.src == node) and e.relation in _COUNTER
    ]
    view.anchor_chain = demand_chain(node, build_upward_index(edges))
    return view


def _sub_distribution(rows: Iterable[EdgeView]) -> str:
    """供給側的**分布**——單一最大值不是答案，分布才是。"""
    values = [e.substitutability for e in rows]
    filled = sorted((v for v in values if v is not None), reverse=True)
    unfilled = sum(1 for v in values if v is None)
    if not filled and not unfilled:
        return "（無）"
    parts = ["／".join(str(v) for v in filled) or "（都沒填）"]
    if unfilled:
        parts.append(f"另有 {unfilled} 條未填")
    return "｜".join(parts)


def render_markdown(view: StructureView,
                    quotes: dict | None = None) -> str:
    out = [
        f"# 結構讀圖：`{view.node}`",
        "",
        "> **零 LLM、零判斷。** 這是五個角度的邊，不是結論——"
        "A（護城河）還是 B（量）由讀的人決定。",
        "> ⚠ **單看任何一個角度都會誤導**：需求側高會讓你以為有護城河，"
        "供給側分散會讓你以為不重要。要一起讀。",
        "",
        f"`result_digest`：`{view.result_digest()[:16]}…`"
        "（五個角度的**查詢結果**指紋；重跑比對即可偵測 stale，零 LLM）",
        "",
    ]
    for name, label in ANGLES:
        if name == "anchor":
            out.append(f"\n## {label}\n")
            if view.anchor_chain:
                out.append(f"✅ {' → '.join(view.anchor_chain)}"
                           f"　（距需求端 {len(view.anchor_chain) - 1} 跳）")
            else:
                out.append("🔴 **走不到任何已登記的需求錨**"
                           "——可能是鏈真的斷了，也可能是走訪清單沒收那個 relation。")
            continue
        rows = view.angles.get(name, [])
        out.append(f"\n## {label}（{len(rows)} 條）\n")
        if not rows:
            out.append("（無）")
            continue
        if name == "supply_side":
            out.append(f"**sub 分布：{_sub_distribution(rows)}**"
                       "　← 有人明顯高於其他＝可能是 A；大家都低＝可能是 B\n")
        out.append("| 邊 | sub | sole | 合格狀態 | 證據 | 文件 |")
        out.append("|---|---|---|---|---|---|")
        for e in sorted(rows, key=lambda r: -(r.substitutability or 0)):
            out.append(
                f"| `{e.src}` {e.relation} `{e.dst}` | {e.substitutability if e.substitutability is not None else '—'} "
                f"| {'✓' if e.sole_source else ('✗' if e.sole_source is False else '—')} "
                f"| {e.qualification_status or '—'} | {e.evidence or '—'} | {e.documents} |"
            )
            if quotes is None:
                continue
            found = quotes.get((e.src, e.relation, e.dst)) or []
            if not found:
                # ⚠ 「沒有逐字」與「沒印逐字」不得同形（L13-2）。
                out.append("|  |  |  |  |  | ⚠ **這條邊在圖裡沒有任何逐字** |")
                continue
            for q in found[:3]:
                out.append(
                    f"|  |  |  |  |  | «{q['quote'][:200]}»"
                    f"<br>　`{q['doc']}`（tier {q['tier']}｜{q['origin']}）"
                    f"{'｜' + q['locator'] if q['locator'] else ''} |"
                )
    out.append(
        "\n---\n\n⚠ **本工具維護的是「讀圖結論跟圖還一不一致」，不是「結論對不對」。**"
        "\n對不對要靠 outcome 量測——一份跟圖完全一致但判斷錯誤的讀圖，digest 永遠不會變。"
    )
    return "\n".join(out)


_Q_QUOTES = """
MATCH (ea:EdgeAssertion)-[:QUOTES]->(s:Source)
WHERE ea.src_id = $node OR ea.dst_id = $node
OPTIONAL MATCH (ea)-[:CITES]->(d:SourceDoc)
RETURN ea.src_id AS src, ea.relation AS relation, ea.dst_id AS dst,
       s.quote AS quote, s.locator AS locator,
       d.id AS doc, d.evidence_tier AS tier, d.origin_entity AS origin
"""


def fetch_quotes(session, node: str) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    """一條邊 →（它的逐字, 出處）。

    ⚠ **這是本模組存在意義的補完，不是裝飾。** 2026-09-18 之前這個工具的輸出裡
    **一個字都不是「當初那份文件實際寫的」**——於是用它讀圖的人，結構上不可能發現
    `tech:external_laser_source is_component_of tech:isolator` 這種錯（那條邊的逐字
    只是列舉 Coherent 做的兩樣東西，完全沒說哪個是哪個的元件）。
    那天所有發現都是**繞過這個工具**、直接 `grep extractions/` 找到的——
    而深挖若需要繞過自己的工具，它就不會例行發生（L18）。
    """
    out: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for r in session.run(_Q_QUOTES, node=node):
        if not r["quote"]:
            continue
        out.setdefault((r["src"], r["relation"], r["dst"]), []).append({
            "quote": " ".join(str(r["quote"]).split()),
            "locator": r["locator"],
            "doc": r["doc"],
            "tier": r["tier"],
            "origin": r["origin"],
        })
    return out


def _load_quotes(node: str) -> dict:
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv()
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    try:
        with driver.session() as session:
            return fetch_quotes(session, node)
    finally:
        driver.close()


def _load_edges() -> list[CanonicalEdge]:
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise SystemExit("請設 NEO4J_PASSWORD")
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
    try:
        with driver.session() as session:
            rows = fetch_assertions(session)
    finally:
        driver.close()
    # ⚠ 共用 `collapse_assertions`，不自己收斂——否則結構讀圖與排序會對同一條邊
    # 給出不同的值，而那是 L16 說的「每個消費端重造一份，重造品立刻開始偏離」。
    return list(collapse_assertions(rows).values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把一個節點的五個結構角度一次查出來（零 LLM、零判斷）")
    parser.add_argument("node", help="節點 id，如 tech:cw_dfb_laser 或 co:coherent")
    parser.add_argument("--json", action="store_true", help="機器可讀，帶 result_digest")
    parser.add_argument("--digest", action="store_true", help="只印 result_digest（staleness 比對用）")
    parser.add_argument("--quotes", action="store_true",
                        help="每條邊附上它自己的逐字（V1/L18：不看逐字就只能相信 label）")
    args = parser.parse_args(argv)

    edges = _load_edges()
    known = {e.src for e in edges} | {e.dst for e in edges}
    if args.node not in known:
        # ⚠ 「圖裡沒這個節點」與「這個節點沒有邊」是兩件事，要分得開（INV-3／L12）。
        print(f"⚠ `{args.node}` 在圖的邊裡沒有出現過。"
              f"\n  這可能是 ①節點 id 打錯（不要憑名字猜，唯一權威是 config/company_identity.json）"
              f"\n  ②它真的還沒有任何邊——那是研究缺口，不是查詢失敗。", file=sys.stderr)
        return 2

    view = build_structure(args.node, edges)
    quotes = None
    if args.quotes:
        quotes = _load_quotes(args.node)
    if args.digest:
        print(view.result_digest())
    elif args.json:
        print(json.dumps(view.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_markdown(view, quotes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
