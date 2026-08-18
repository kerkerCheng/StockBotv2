"""L8 來源獨立性稽核：供應商自報的 `sole_source` 必須降級。

`schema/graph_schema.md` §7 的鐵律：

> 供應商自己的法說會說「我們是唯一供應商」不算 `verified_by_search`；需要**客戶端或
> 第三方**來源印證。若某條 `sole_source=true` 的邊，其所有 source_ids 的 `origin_entity`
> 全是同一家供應商 → 自動標 `sole_source_evidence_quality: weak`（L8），
> 且 `confidence` 不得超過 0.5。

**這條規則從 2026-07-17 就寫在 schema 裡，但從未對圖執行過**（2026-08-18 實測：
`sole_source_evidence_quality` 全圖 0 筆，而 4 筆 `sole_source=true` 全部 confidence=0.9）。
判定所需資料一直都在——`origin_entity` 100% 填滿——缺的只是有人去比對。

判定單位是**canonical edge（`edge_key`）**，不是單一 EdgeAssertion：規則講的是
「某條邊的**所有** source_ids」，所以必須跨 assertion 聚合 origin。同一家公司在兩份
自家文件裡各講一次，仍然只有一個 origin。

⚠ 本腳本預設 dry-run。`--apply` 會修改 Engine A（依 L10 允許：圖可由 extraction 重建），
但仍輸出 manifest 供比對。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

from dotenv import load_dotenv  # noqa: E402
from neo4j import GraphDatabase  # noqa: E402

from identity.registry import get_registry  # noqa: E402

WEAK = "weak"
WEAK_CONFIDENCE_CAP = 0.5
MANIFEST_DIR = ROOT / "library" / "private" / "graph_migrations"


def _attrs(raw) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return {}
    return raw if isinstance(raw, dict) else {}


def _company_id_for(origin: str | None, registry) -> str | None:
    """把 SourceDoc 的 `origin_entity`（人類公司名，如 "Lumentum"）解析成 `co:*`。

    ⚠ 解析失敗一律回 None 並讓該筆進 `unresolved_origins`，**不得當成「不同源」**。
    那會讓供應商自報的邊悄悄通過檢查——正是 L8／L11 要防的 laundering
    （L15：先解析身分、再查權限；解析時不得偏好「能通過的答案」）。

    解析順序刻意由嚴到寬，且**兩個以上候選就不猜**（L15 的無歧義原則）。
    """
    if not origin:
        return None
    text = str(origin).strip()
    if not text:
        return None

    by_ticker = registry.company_id_for_ticker(text)
    if by_ticker:
        return by_ticker

    slug = "co:" + text.lower().replace(" ", "_").replace(".", "").replace(",", "")
    if registry.has_company(slug):
        return slug

    # 正式名稱／別名比對；大小寫不敏感，但必須唯一命中。
    needle = text.casefold()
    hits = {
        c.company_id
        for c in registry.companies
        if needle == str(getattr(c, "name", "") or "").casefold()
        or needle in {str(a).casefold() for a in (getattr(c, "aliases", None) or ())}
    }
    return hits.pop() if len(hits) == 1 else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="實際寫回 Neo4j；預設只報告")
    ap.add_argument("--all-bottleneck", action="store_true",
                    help="除 sole_source 外，一併統計所有帶瓶頸屬性的邊的 origin 同質性")
    args = ap.parse_args()

    load_dotenv()
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    registry = get_registry()

    with driver.session() as session:
        assertions = session.run(
            """
            MATCH (e:EdgeAssertion)
            OPTIONAL MATCH (d:SourceDoc {id: e.source_doc_id})
            RETURN e.id AS aid, e.edge_key AS edge_key, e.src_id AS src,
                   e.relation AS rel, e.dst_id AS dst, e.attributes AS attrs,
                   e.confidence AS conf, e.source_doc_id AS doc,
                   d.origin_entity AS origin, d.evidence_tier AS tier
            """
        ).data()

    rows = [{**a, "attrs": _attrs(a["attrs"])} for a in assertions]
    by_edge: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_edge[r["edge_key"]].append(r)

    findings = []
    for edge_key, group in by_edge.items():
        if not any(g["attrs"].get("sole_source") is True for g in group):
            continue
        subject = group[0]["src"]
        origins = {g["origin"] for g in group if g["origin"]}
        resolved = {o: _company_id_for(o, registry) for o in origins}
        unresolved = sorted(o for o, cid in resolved.items() if cid is None)
        external_companies = sorted(
            {cid for cid in resolved.values() if cid and cid != subject}
        )

        # ⚠ 三分，不是二分。`None` 同時可能是「真的第三方媒體」與「沒解析出來的
        # 子公司／別名」——兩者對本檢查的意義相反（L12）。首版用
        # `resolved == {subject}` 判定，於是任何無法解析的 origin 都會讓集合不等於
        # {subject}，**自動被當成外部佐證通過**。那正是本檔 docstring 說不得發生的事。
        # 現在改成：只有解析到「不同公司」才算已印證；只剩無法解析者一律 needs_review，
        # 由人決定它是第三方（schema §7 接受）還是同源別名（不接受）。
        if external_companies:
            verdict = "externally_corroborated"
        elif unresolved:
            verdict = "needs_review"
        else:
            verdict = "self_reported"

        findings.append({
            "edge_key": edge_key,
            "edge": f"{subject} -[{group[0]['rel']}]-> {group[0]['dst']}",
            "assertions": [g["aid"] for g in group],
            "origins": sorted(origins),
            "external_companies": external_companies,
            "unresolved_origins": unresolved,
            "verdict": verdict,
            "self_reported": verdict == "self_reported",
            "max_confidence": max(float(g["conf"] or 0) for g in group),
            "current_quality": sorted(
                {str(g["attrs"].get("sole_source_evidence_quality")) for g in group}
            ),
        })

    print(f"# L8 來源獨立性稽核（{datetime.now(timezone.utc).date()}）\n")
    print(f"EdgeAssertion {len(rows)} 筆｜canonical edge {len(by_edge)} 條"
          f"｜含 sole_source=true 的邊 {len(findings)} 條\n")

    to_fix = [f for f in findings if f["self_reported"]]
    needs_review = [f for f in findings if f["verdict"] == "needs_review"]
    marks = {
        "externally_corroborated": "✅ 已有外部公司印證",
        "needs_review": "🟡 待人工判定",
        "self_reported": "🔴 供應商自報",
    }
    for f in findings:
        print(f"{marks[f['verdict']]}  {f['edge']}")
        print(f"    edge_key={f['edge_key'][:24]}…  assertions={len(f['assertions'])}")
        print(f"    origin_entity={f['origins']}  現有 quality={f['current_quality']}")
        print(f"    confidence={f['max_confidence']}"
              f"{'  → 應降至 ≤0.5' if f['self_reported'] else ''}")
        if f["external_companies"]:
            print(f"    外部佐證公司：{f['external_companies']}")
        if f["unresolved_origins"]:
            print(f"    ⚠ 無法解析成 co:* 的 origin：{f['unresolved_origins']}")
            if f["verdict"] == "needs_review":
                print("       → 這是**唯一**的非本人 origin。它可能是 schema §7 接受的"
                      "第三方媒體，也可能是沒解析出來的子公司／別名——兩者結論相反，"
                      "不得自動放行。請人工判定後，或登記進 registry、或標為第三方。")
        print()

    print(f"需降級：{len(to_fix)} 條｜待人工判定：{len(needs_review)} 條｜"
          f"已印證：{len(findings) - len(to_fix) - len(needs_review)} 條")

    if args.all_bottleneck:
        print("\n## 擴大統計：所有帶 substitutability 的邊（A3 lens）\n")
        stats = {"self": 0, "external": 0, "no_origin": 0}
        for edge_key, group in by_edge.items():
            if not any(g["attrs"].get("substitutability") is not None for g in group):
                continue
            subject = group[0]["src"]
            origins = {g["origin"] for g in group if g["origin"]}
            if not origins:
                stats["no_origin"] += 1
            elif {_company_id_for(o, registry) for o in origins} == {subject}:
                stats["self"] += 1
            else:
                stats["external"] += 1
        total = sum(stats.values())
        print(f"  帶 substitutability 的 canonical edge：{total} 條")
        for k, label in (("self", "僅供應商自報"), ("external", "有外部 origin"),
                         ("no_origin", "無 origin 可判定")):
            pct = stats[k] / total if total else 0
            print(f"    {label}：{stats[k]} ({pct:.0%})")
        print("\n  ⚠ 這批目前**不會**被本腳本降級——schema §7 的規則只寫給 sole_source。"
              "\n     但排名若採用 substitutability，自報比例就是排名的證據上限。")

    if not args.apply:
        print("\n(dry-run) 加 --apply 才會寫回 Neo4j")
        driver.close()
        return 0

    if not to_fix:
        print("\n無需修改")
        driver.close()
        return 0

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    manifest = MANIFEST_DIR / f"l8_sole_source_{stamp}.json"
    manifest.write_text(
        json.dumps({"applied_at": stamp, "findings": findings}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n✓ manifest：{manifest}")

    # attributes 是 JSON 字串欄位，在 Python 端組好再整份寫回；不依賴 APOC。
    with driver.session() as session:
        updated = 0
        for f in to_fix:
            for r in rows:
                if r["aid"] not in f["assertions"]:
                    continue
                attrs = dict(r["attrs"])
                attrs["sole_source_evidence_quality"] = WEAK
                new_conf = min(float(r["conf"] or 0), WEAK_CONFIDENCE_CAP)
                session.run(
                    "MATCH (e:EdgeAssertion {id: $aid}) "
                    "SET e.attributes = $attrs, e.confidence = $conf",
                    aid=r["aid"],
                    attrs=json.dumps(attrs, ensure_ascii=False, sort_keys=True),
                    conf=new_conf,
                )
                updated += 1
                print(f"  ✓ {r['aid']}: quality=weak, confidence {r['conf']} → {new_conf}")
    print(f"\n✓ 已更新 {updated} 筆 EdgeAssertion")
    driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
