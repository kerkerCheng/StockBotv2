"""偵探第一版的 I/O：查圖上的鄰居、掃自家庫、讀共識與現行敘事、寫線索包、給核引文讀檔。唯讀，不寫任何 authority。

純邏輯（角色、日期、清理、問句、派工提示、核引文）在 `alpha/detective.py`。
⚠ 點名比對只用 `query.bottleneck.quote_names_company`（L16；同 `unread_primary`）——不另寫一套名字規則。
⚠ 回溯（`as_of`）只收「答得出 T 時刻知道什麼」的文件：發布日不明的不收、數出來（INV-6、INV-3）。
"""
from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..detective import (
    DocInfo, Neighbor, build_questions, doc_date, has_our_header, neighbors_from_rows, render_prompt,
    sanitize_excerpt,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "library" / "raw"
TEXT_SUFFIXES = frozenset({".txt", ".md"})
#: 一份包最多列幾份文件（超過的照「點名目標優先、點名鄰居多的優先、新的優先」截斷，截斷要說話——INV-3）。
MAX_DOCS = 250
#: 第二跳（對手的客戶）只點名它、沒點名目標與一跳鄰居的文件，每家只留最新幾份——NVIDIA 這種樞紐不能把包灌滿（截斷要說話）。
SECOND_HOP_PER_COMPANY = 12

#: 一跳：與目標公司直接相連的公司（供貨、競爭、投資、合作…）。
ONE_HOP_CYPHER = """
MATCH (c:Company {id: $cid})-[r]-(n:Company)
RETURN type(r) AS rel, startNode(r) = c AS out, n.id AS nid, coalesce(n.name, n.id) AS name, null AS via
"""
#: 經一層：目標供應的層節點上，其他供應商（同層）與吃這一層的公司（同層買方）。
LAYER_CYPHER = """
MATCH (c:Company {id: $cid})-[:SUPPLIES_TO]->(m)<-[r]-(n:Company)
WHERE NOT m:Company AND NOT m:Claim AND NOT m:Source AND n.id <> $cid
RETURN type(r) AS rel, true AS out, n.id AS nid, coalesce(n.name, n.id) AS name, m.id AS via
"""
#: 第二跳：同層供應商與直接對手的客戶（買賣兩方各寫一半的合約，要兩邊的文件才對得起來——M0 的 AOI×雲南鍺業）。
RIVAL_CUSTOMER_CYPHER = """
MATCH (c:Company {id: $cid})-[:SUPPLIES_TO]->(m)<-[:SUPPLIES_TO]-(p:Company)-[:SUPPLIES_TO]->(n:Company)
WHERE NOT m:Company AND NOT m:Claim AND NOT m:Source AND p.id <> $cid AND n.id <> $cid
RETURN DISTINCT 'SUPPLIES_TO' AS rel, true AS out, n.id AS nid, coalesce(n.name, n.id) AS name, p.id AS via, 2 AS hop
UNION
MATCH (c:Company {id: $cid})-[:COMPETES_WITH]-(p:Company)-[:SUPPLIES_TO]->(n:Company)
WHERE n.id <> $cid
RETURN DISTINCT 'SUPPLIES_TO' AS rel, true AS out, n.id AS nid, coalesce(n.name, n.id) AS name, p.id AS via, 2 AS hop
"""


def fetch_neighbor_rows(company_id: str) -> list[dict[str, Any]]:
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(ROOT / ".env")
    driver = GraphDatabase.driver(os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                                  auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]))
    try:
        with driver.session() as session:
            rows = [dict(r) for r in session.run(ONE_HOP_CYPHER, cid=company_id)]
            rows += [dict(r) for r in session.run(LAYER_CYPHER, cid=company_id)]
            rows += [dict(r) for r in session.run(RIVAL_CUSTOMER_CYPHER, cid=company_id)]
    finally:
        driver.close()
    return rows


@dataclass
class ScanResult:
    docs: list[DocInfo] = field(default_factory=list)
    scanned: int = 0
    unchecked: int = 0          # 非文字檔（PDF 等）：沒核，不是沒點名（INV-3）


def scan_raw(companies: Mapping[str, Any], *, raw_dir: Path = RAW_DIR) -> ScanResult:
    """掃自家庫一次：每份文字檔點名了哪些公司（目標＋鄰居）。`companies`＝company_id → 名冊物件。"""
    from identity.registry import get_registry
    from query.bottleneck import quote_names_company, shared_name_forms

    shared = shared_name_forms(get_registry())
    out = ScanResult()
    for path in sorted(raw_dir.iterdir()):
        if not path.is_file() or path.name.endswith(".meta.json"):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            out.unchecked += 1
            continue
        out.scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            out.unchecked += 1
            continue
        named = tuple(cid for cid, company in companies.items() if quote_names_company(text, company, shared=shared))
        if named:
            meta = None
            sidecar = path.with_suffix(".meta.json")
            if sidecar.is_file():
                try:
                    meta = json.loads(sidecar.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    meta = None         # 壞的 sidecar：退回檔頭與檔名，不中斷
            out.docs.append(DocInfo(name=path.name, published=doc_date(path.name, text[:3000], meta), named=named))
    return out


def consensus_lines(ticker: str, *, as_of: date | None = None) -> list[str]:
    """會計年度別營收共識：最新一次抓取的每一期＋那一期的修正軌跡（數字變了的點）。共識是預估，不是價格。"""
    from alpha.providers.fundamentals import EngineCFundamentalsProvider

    prov = EngineCFundamentalsProvider()
    rows, _why = prov.fiscal_consensus(ticker, as_of=as_of)
    lines: list[str] = []
    for est in rows:
        if est.metric != "revenue" or est.value is None:
            continue
        hist, _ = prov.fiscal_consensus_history(ticker, metric="revenue", period_end=est.period.end, as_of=as_of)
        points: list[str] = []
        last = None
        for day, value, _n in hist:
            if last is None or abs(value - last) / max(abs(last), 1) > 0.005:
                points.append(f"{day.isoformat()} {value / 1e8:,.2f} 億")
                last = value
        span = f"（區間 {est.low / 1e8:,.2f}–{est.high / 1e8:,.2f}）" if est.low and est.high else ""
        unit = f" {est.currency}" if est.currency else ""
        lines.append(f"會計期末 {est.period.end.isoformat()} 營收共識 {est.value / 1e8:,.2f} 億{unit}"
                     f"（{est.analyst_count or '?'} 位）{span}；軌跡 " + " → ".join(points[-6:]))
    return lines


def _select(docs: Sequence[DocInfo], target_id: str, as_of: date | None,
            second_hop: frozenset[str] = frozenset()) -> tuple[list[DocInfo], dict[str, int]]:
    """回溯排除（日期不明、晚於回溯日）→ 第二跳每家上限 → 排序（點名目標的先、點名鄰居多的先、新的先；只點名第二跳的排最後）→ 總上限。
    每一步丟掉的都數出來（INV-3）。`second_hop`＝只以「對手的客戶」身分進來的公司。"""
    counts = {"named": len(docs), "undated": 0, "after_as_of": 0, "second_hop_capped": 0, "truncated": 0}
    keep: list[DocInfo] = []
    for d in docs:
        if as_of is not None:
            if d.published is None:
                counts["undated"] += 1
                continue
            if d.published > as_of:
                counts["after_as_of"] += 1
                continue
        keep.append(d)
    newest_first = sorted(keep, key=lambda d: -(d.published or date.min).toordinal())
    per_company: dict[str, int] = {}
    capped: set[str] = set()
    for d in newest_first:
        if not second_hop or not set(d.named) <= second_hop:
            continue
        if all(per_company.get(c, 0) >= SECOND_HOP_PER_COMPANY for c in d.named):
            capped.add(d.name)
            continue
        for c in d.named:
            per_company[c] = per_company.get(c, 0) + 1
    counts["second_hop_capped"] = len(capped)
    keep = [d for d in keep if d.name not in capped]
    keep.sort(key=lambda d: (set(d.named) <= second_hop if second_hop else False, target_id not in d.named,
                             -len(d.named), -(d.published or date.min).toordinal()))
    counts["truncated"] = max(0, len(keep) - MAX_DOCS)
    return keep[:MAX_DOCS], counts


def build_pack(ticker: str, out_dir: Path, *, as_of: date | None = None,
               rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """組一份線索包：MANIFEST.md、PROMPT.md、（現況）narrative.json；回溯另把文件複製進 docs/ 並清掉我們後來寫的字。
    回傳摘要（鄰居數、文件數、截斷與排除的計數）。"""
    from identity.registry import get_registry

    from ..price_mask import mask_brief_record
    from .briefs import raw_record
    from .structure_readings import ledger_path

    registry = get_registry()
    company_id = registry.company_id_for_ticker(ticker)
    if not company_id:
        raise SystemExit(f"✗ 名冊沒有 {ticker}（INV-1：不猜）")
    target = registry.company(company_id)
    name = str(getattr(target, "display_name", None) or ticker)
    neighbors: list[Neighbor] = neighbors_from_rows(company_id, rows if rows is not None else fetch_neighbor_rows(company_id))
    companies = {company_id: target}
    missing_registry = []
    for nb in neighbors:
        obj = registry.company(nb.company_id)
        if obj is None:
            missing_registry.append(nb.company_id)     # 圖上有、名冊沒有：比不到名字，說出來（INV-3）
            continue
        companies[nb.company_id] = obj
    scan = scan_raw(companies)
    second_hop = frozenset(nb.company_id for nb in neighbors if nb.roles == {"rival_customer"})
    docs, counts = _select(scan.docs, company_id, as_of, second_hop)
    by_company: dict[str, list[DocInfo]] = {}
    for d in docs:
        for cid in d.named:
            by_company.setdefault(cid, []).append(d)

    out_dir.mkdir(parents=True, exist_ok=True)
    narrative_note = ""
    reading_lines: list[str] = []
    if as_of is None:
        raw = raw_record(ticker)
        if raw is not None:
            (out_dir / "narrative.json").write_text(json.dumps(mask_brief_record(raw), ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
            narrative_note = f"- 現行敘事：{(out_dir / 'narrative.json').as_posix()}（`{raw.get('brief_id')}`；價格欄已遮，不要去找價格）。"
            for ride in raw.get("rides") or []:
                reading_lines.append(f"- 讀圖：{ledger_path(str(ride.get('node'))).relative_to(ROOT).as_posix()} 裡 "
                                     f"reading_id = {ride.get('reading_id')} 那一列（只讀這一列）。")
    docs_dir = out_dir / "docs"
    if as_of is not None:
        if docs_dir.exists():
            shutil.rmtree(docs_dir)
        docs_dir.mkdir()
        for d in docs:
            src = RAW_DIR / d.name
            text = src.read_text(encoding="utf-8", errors="replace")
            if has_our_header(text[:3000]):
                text, _dropped = sanitize_excerpt(text, as_of)
            (docs_dir / d.name).write_text(text, encoding="utf-8")
        read_scope = f"{docs_dir.as_posix()}/ 裡的檔（MANIFEST.md 列的那些）"
        file_prefix = docs_dir.as_posix() + "/"
    else:
        read_scope = f"MANIFEST.md 列的 library/raw 檔{('、現行敘事與讀圖那一列' if narrative_note else '')}"
        file_prefix = "library/raw/"

    manifest = [f"# 線索包：{name}（{ticker}，{company_id}）", "",
                f"- 產生日：{date.today().isoformat()}｜回溯：{as_of.isoformat() if as_of else '否（現況）'}",
                f"- 鄰居 {len(neighbors)} 家；名冊沒有、比不到名字的 {len(missing_registry)} 家：{'、'.join(missing_registry) or '無'}",
                f"- 自家庫掃了 {scan.scanned} 份文字檔（非文字檔沒核 {scan.unchecked} 份）；點名目標或鄰居的 {counts['named']} 份；"
                f"回溯排除：日期不明 {counts['undated']}、晚於回溯日 {counts['after_as_of']}；"
                f"只點名對手的客戶、超過每家 {SECOND_HOP_PER_COMPANY} 份的 {counts['second_hop_capped']}；截斷 {counts['truncated']}（上限 {MAX_DOCS}）",
                "", "## 鄰居（圖上的邊）"]
    for nb in neighbors:
        via = f"（經 {'、'.join(sorted(nb.vias))}）" if nb.vias else ""
        manifest.append(f"- {nb.role_text()}：{nb.name}（{nb.company_id}）{via}——{len(by_company.get(nb.company_id) or ())} 份")
    manifest += ["", "## 文件（點名目標的先、只點名對手的客戶的排最後；括號是發布日與點名了誰）"]
    label = {cid: (registry.company(cid).display_name if registry.company(cid) else cid) for cid in companies}
    for d in docs:
        who = "、".join(label.get(c, c) for c in d.named)
        manifest.append(f"- {file_prefix}{d.name}（{d.published.isoformat() if d.published else '日期不明'}｜{who}）")
    (out_dir / "MANIFEST.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")

    cons = consensus_lines(ticker, as_of=as_of)
    questions = build_questions(name, neighbors, by_company, cons, with_narrative=bool(narrative_note))
    materials = "\n".join(filter(None, [
        f"- 今天：{(as_of or date.today()).isoformat()}；公司：{name}（{ticker}）。",
        narrative_note, *reading_lines,
        f"- 檔案清單：{(out_dir / 'MANIFEST.md').as_posix()}（{len(docs)} 份；鄰居與它們的角色也在裡面）。大檔用 Grep 找段落，不要整份讀。",
        "- 分析師共識（營收；Engine C）：" + ("；".join(cons) if cons else "沒有資料"),
        "- 公司自己說的計畫與我們算的路徑：" + ("見敘事的量級那一格（四段）。" if narrative_note else "從文件自己讀。"),
    ]))
    prompt = render_prompt(company=name, ticker=ticker, read_scope=read_scope, materials=materials,
                           questions=questions, as_of=as_of)
    (out_dir / "PROMPT.md").write_text(prompt, encoding="utf-8")
    return {"company_id": company_id, "neighbors": len(neighbors), "docs": len(docs), "counts": counts,
            "missing_registry": missing_registry, "scanned": scan.scanned, "unchecked": scan.unchecked,
            "questions": len(questions), "out_dir": out_dir.as_posix()}


_LISTED_FILE = re.compile(r"([A-Za-z0-9_\-.]+\.(?:txt|md|jsonl|json))")


def listed_files(pack_dir: Path) -> frozenset[str] | None:
    """線索包准讀的檔名（MANIFEST.md 列的文件、PROMPT.md 指的敘事與讀圖檔）；沒有 MANIFEST 回 None（不判清單外）。"""
    manifest = pack_dir / "MANIFEST.md"
    if not manifest.is_file():
        return None
    names: set[str] = set()
    for path in (manifest, pack_dir / "PROMPT.md"):
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("- "):
                    names.update(Path(m).name for m in _LISTED_FILE.findall(line))
    return frozenset(names)


def make_reader(pack_dir: Path | None):
    """核引文的讀檔：先找包裡的 docs/（回溯），再找自家庫；都沒有回 None。"""
    roots = [p for p in ((pack_dir / "docs") if pack_dir else None, RAW_DIR) if p is not None]

    def read_lines(name: str) -> list[str] | None:
        for root in roots:
            path = root / Path(name).name
            if path.is_file():
                return path.read_text(encoding="utf-8", errors="replace").splitlines()
        return None
    return read_lines
