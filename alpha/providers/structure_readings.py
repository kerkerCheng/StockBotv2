"""結構讀圖 ledger 的 I/O：`library/private/alpha/structure_readings/<node>.jsonl`。

與 `alpha/providers/abstentions.py`／`briefs.py` 同一個位置慣例與同一套規則：private、
append-only、content-addressed id 拒絕重複、secret 拒絕、`supersedes_id` 必須指到既有紀錄。
純邏輯（解析、選取、分級）在 `alpha/structure_reading/`；這裡只讀寫檔。

⚠ **主鍵是 node 不是 ticker**（`tech:cw_dfb_laser`、`mat:inp_substrate`）——結構讀圖問的是
「這個位置卡不卡」，一個節點會餵好幾檔股票的賭注。所以它另立一本，不塞進 `briefs/`：
那本的主鍵是 ticker、七格是封閉字彙，硬塞會讓兩邊的 contract 都變成「什麼都能放」（L16-3）。
node 會出現在檔名裡，所以 `:`／`/` 等路徑字元要正規化。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from shared.redaction import sensitive_payload_path

from ..errors import ContractViolation
from ..structure_reading.contracts import StructureReading, parse_structure_reading_record

_ROOT = Path(__file__).resolve().parents[2]
STRUCTURE_READING_DIR = _ROOT / "library" / "private" / "alpha" / "structure_readings"

#: node id 允許的字元；其餘一律換成 `_`。**不是為了美觀**——`tech:cw_dfb_laser` 直接當檔名
#: 在 Windows 上會被當成 NTFS 資料流（`檔名:資料流`）而靜默寫到別的地方。
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def _slug(node: str) -> str:
    text = _UNSAFE.sub("_", str(node).strip())
    if not text:
        raise ContractViolation("node 正規化後是空字串——檔名推不出來")
    return text


def ledger_path(node: str, *, directory: Path | None = None) -> Path:
    return (directory or STRUCTURE_READING_DIR) / f"{_slug(node)}.jsonl"


def read_reading_records(node: str, *, directory: Path | None = None,
                         ) -> tuple[list[StructureReading], list[str]]:
    """讀一個節點的全部紀錄。壞掉的行**不靜默丟棄**——回在第二個 list 裡，消費端計數（INV-3）。"""
    path = ledger_path(node, directory=directory)
    if not path.is_file():
        return [], []
    records: list[StructureReading] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(parse_structure_reading_record(json.loads(text)))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def _norm(text: Any) -> str:
    return " ".join(str(text or "").split())


def verify_citations(record: Mapping[str, Any], quotes: Mapping[tuple[str, str, str], Sequence[Mapping[str, Any]]],
                     *, registry: Any = None) -> list[str]:
    """v3 引用的寫入端核對（plan A2）：回傳問題清單，空＝全部核對得到。**不查圖**——`quotes` 必須與
    紀錄的快照出自同一次查詢（`fetch_structure_snapshot_with_quotes`）。

    每一條引用：①邊在紀錄快照的那個角度裡；②片段（去空白正規化）是那條邊某段逐字的子字串，且那段逐字
    出自 `source_id` 那份文件；③標 `independent` 的，那份文件的 `origin_entity` 經
    `query.bottleneck.company_id_for_origin`（唯一 owner，不重造）解析得到、且不是那條邊的主詞（供應商自己）。
    """
    parsed = parse_structure_reading_record(record)
    problems: list[str] = []
    if not parsed.citations:
        return problems
    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    from query.bottleneck import company_id_for_origin

    # 插槽的「不是供應商自己」＝不是**這個插槽的任何一家供應商**（與插槽視角的「客戶端原文」同一個定義；
    # plan 待決 #12，Step 2.5 定案）。實測：`prod:els_8ch_module` 用同插槽另一家供應商 Enablence 發的聯合新聞稿
    # 標 independent，舊規則（只排除那條邊的主詞）放行了一份 Sivers 的插槽護城河——聯合公告方與它利益一致，不是客戶。
    # 層讀圖不變：一層的其他供應商是競爭者，不是聯合公告方。
    socket_suppliers = ({str(row[0]) for row in parsed.angles.get("supply_side", ())}
                        if parsed.unit == "socket" else set())
    for index, citation in enumerate(parsed.citations, 1):
        edge = tuple(citation.edge)
        label = f"第 {index} 條引用（{citation.angle}：{edge[0]} {edge[1]} {edge[2]}）"
        rows = {tuple(str(x) for x in row[:3]) for row in parsed.angles.get(citation.angle, ())}
        if edge not in rows:
            problems.append(f"{label}：這條邊不在這次快照的 {citation.angle} 角度裡")
            continue
        needle = _norm(citation.quote)
        hits = [q for q in quotes.get(edge, ()) if str(q.get("doc") or "") == citation.source_id
                and needle in _norm(q.get("quote"))]
        if not hits:
            docs = sorted({str(q.get("doc")) for q in quotes.get(edge, ())})
            problems.append(f"{label}：片段不是這條邊出自 {citation.source_id} 的任何一段逐字"
                            f"（這條邊的逐字來自 {docs or '（沒有任何逐字）'}）")
            continue
        if citation.independent:
            origins = {str(q.get("origin") or "") for q in hits}
            resolved = {company_id_for_origin(o, registry) for o in origins}
            if None in resolved or not resolved:
                problems.append(f"{label}：標了 independent，但來源 {citation.source_id} 的 origin_entity "
                                f"{sorted(origins)} 解析不到任何 co:*——解析不到的不算外部印證（L8、INV-1）")
            elif edge[0] in resolved:
                problems.append(f"{label}：標了 independent，但來源 {citation.source_id} 就是 {edge[0]} 自己——"
                                "供應商自稱是弱主張（L8）")
            elif resolved & socket_suppliers:
                problems.append(f"{label}：標了 independent，但來源 {citation.source_id} 是這個插槽的另一家供應商 "
                                f"{sorted(resolved & socket_suppliers)}——同插槽的聯合公告方不是客戶端（L8；plan 待決 #12）")
    return problems


def verify_disproof_sources(record: Mapping[str, Any], existing: Sequence[StructureReading]) -> list[str]:
    """v3 反證出處的寫入端核對：`sr_*` 必須是同節點 ledger 裡既有的一份。"""
    parsed = parse_structure_reading_record(record)
    known = {r.reading_id for r in existing}
    return [f"第 {i} 條反證的 source={entry.source}：同節點 ledger 裡沒有這一份"
            for i, entry in enumerate(parsed.disproof, 1)
            if entry.source and entry.source.startswith("sr_") and entry.source not in known]


def append_reading_record(record: Mapping[str, Any], *, directory: Path | None = None,
                          quotes: Mapping[tuple[str, str, str], Sequence[Mapping[str, Any]]] | None = None,
                          registry: Any = None) -> Path:
    """append 一筆（已由 `structure_reading_record()` 驗證過的）紀錄；只 append，永不改寫既有行。

    v3 起多兩道寫入端核對（plan A2）：引用要對**同一份快照**的逐字核對（有引用卻沒給 `quotes` 就拒收，
    fail closed）；反證出處的 `sr_*` 要存在。任何一條不過就整筆拒收，並逐條說出是哪一條、為什麼。
    """
    parsed = parse_structure_reading_record(record)
    sensitive = sensitive_payload_path(dict(record), "structure_reading")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing structure reading rejected at {sensitive}")
    existing, _errors = read_reading_records(parsed.node, directory=directory)
    if any(r.reading_id == parsed.reading_id for r in existing):
        raise ContractViolation(f"reading {parsed.reading_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id and not any(r.reading_id == parsed.supersedes_id for r in existing):
        raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在 ledger 中")
    if not parsed.retracted:
        problems = verify_disproof_sources(record, existing)
        if parsed.citations:
            if quotes is None:
                problems.append("這筆有引用，但沒有給同一份快照的逐字（quotes）——核對不了就不寫")
            else:
                problems += verify_citations(record, quotes, registry=registry)
        if problems:
            raise ContractViolation("讀圖紀錄拒收：\n  - " + "\n  - ".join(problems))
    path = ledger_path(parsed.node, directory=directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def fetch_structure_snapshot(node: str) -> dict[str, Any]:
    """現在的圖對這個節點回什麼（`query.structure` 的輸出照抄）。

    ⚠ **這一支住在 providers 是刻意的**：`alpha/` 的契約與模型層不得依賴外部世界，
    providers 是唯一例外（`tests/test_layer_separation.py` 在守）。2026-09-17 實測：
    先前把 `from query.structure import ...` 寫進 `alpha/cli.py`，那條測試立刻紅。

    ⚠ 快照**只能**由這裡產生，不接受呼叫端遞來——手組的快照偵測不了
    「多了一條我當初沒讀到的邊」，而那正是這本 ledger 存在的理由。
    """
    from query.structure import _load_edges, build_structure

    return build_structure(str(node), _load_edges()).as_dict()


def fetch_structure_snapshot_with_quotes(node: str) -> tuple[dict[str, Any], dict[tuple[str, str, str], list[dict]]]:
    """快照＋這個節點每條邊的逐字，**出自同一次查詢**（v3 引用核對用；plan §13：不要另查一次圖）。"""
    from query.structure import load_snapshot_with_quotes

    view, quotes = load_snapshot_with_quotes(str(node))
    return view.as_dict(), quotes


def demand_side_customers(record: Mapping[str, Any]) -> list[str]:
    """快照 `demand_side` 那一角的公司端點（`co:*`，不含節點自己）——需求側客戶。"""
    node = str(record.get("node") or "")
    out: set[str] = set()
    for row in (record.get("angles") or {}).get("demand_side") or ():
        for endpoint in (row[0] if len(row) > 0 else None, row[2] if len(row) > 2 else None):
            if isinstance(endpoint, str) and endpoint.startswith("co:") and endpoint != node:
                out.add(endpoint)
    return sorted(out)


def register_reading_watches(record: Mapping[str, Any], *, watches_path: Path | None = None,
                             directory: Path | None = None) -> dict[str, list[str]]:
    """讀圖 append 成功後的等待登記（Phase 1 Step 1.5；冪等，可重跑）。

    1. 被取代（`supersedes_id`）或撤回的那一份：它還在盯的語意 watch → consume（note 寫明 superseded／retracted）。
    2. 這一份的 `disproof[]` → 每條一筆語意 watch（`source_ref=reading:<id>#<n>`，到期預設＝讀圖到期）。
    3. 需求側客戶 → `entity_filing_signal`＋`wake_reading=<node>`（到期＝讀圖到期）：客戶出了新一手文件，
       這個節點就列進 needs_reread——不自動重讀（重讀是研究）。已有同節點同客戶的 active 那一筆就不重登。
    4. 這一份本身就是「重讀完成」：這個節點 fired 的 `wake_reading` watch → consume；讀圖來源的反證被判觸及、
       還沒處置的 → `judgment.handled`（verb `reread`）。

    ⚠ 經 providers 呼叫 `engine_b`：`alpha/` 核心不得 import 它（`tests/test_layer_separation.py`）。
    """
    from datetime import datetime, timezone

    from engine_b import event_watch as ew

    parsed = parse_structure_reading_record(record)
    stamp = datetime.now(timezone.utc).isoformat()
    data = ew.load_watches(watches_path)
    summary: dict[str, list[str]] = {"registered": [], "consumed": [], "reread_registered": [],
                                     "reread_consumed": [], "touched_handled": []}
    # 收舊：撤回只收被撤回那一份的；新讀圖收**這個節點其他每一份**的（R2-b 第三輪 NB3-4：只認 supersedes_id 時，
    # 重讀忘了帶或帶錯，舊讀圖的條件永遠掛著，同一條件新舊兩筆）。節點的讀圖 id 從 ledger 讀，不只靠 watch 上的 node。
    # ⚠ 以（節點, 單位）為單位（v3，A1）：同一個 prod 節點的層讀圖與插槽讀圖各自是現行，
    # 新的插槽讀圖不得收掉層讀圖還在盯的條件，反之亦然。
    records, _errors = read_reading_records(parsed.node, directory=directory)
    same_unit_ids = {r.reading_id for r in records if r.unit == parsed.unit} | {parsed.reading_id}
    other_unit_ids = {r.reading_id for r in records if r.unit != parsed.unit}
    if parsed.retracted:
        stale_ids = {str(parsed.supersedes_id)} if parsed.supersedes_id else set()
    else:
        stale_ids = (same_unit_ids | ({str(parsed.supersedes_id)} if parsed.supersedes_id else set())) \
            - {parsed.reading_id}
    if stale_ids:
        note = "retracted" if parsed.retracted else f"superseded by {parsed.reading_id}"
        for watch in data["watches"]:
            ref = str(watch.get("source_ref") or "")
            if (watch.get("kind") != ew.SEMANTIC_KIND or not ref.startswith("reading:")
                    or ref[len("reading:"):].split("#", 1)[0] not in stale_ids):
                continue
            if watch.get("status") in ("active", "fired"):
                watch["status"] = "consumed"
                watch["closed"] = {"at": stamp, "note": note}
                summary["consumed"].append(watch["watch_id"])
            elif watch.get("status") == "expired" and not watch.get("expiry_resolution"):
                # 到期待決的也收（R2-b NB-4）：否則已被取代的讀圖條件還掛著 watch_decision，續等會復活一筆孤兒
                ew.resolve_expiry(data, watch["watch_id"], {"kind": "source_superseded", "note": note})
                summary["consumed"].append(watch["watch_id"])
    if not parsed.retracted:
        for index, entry in enumerate(parsed.disproof, 1):
            ref = f"reading:{parsed.reading_id}#{index}"
            if any(w.get("source_ref") == ref for w in data["watches"]):
                continue
            watch = ew.add_watch(
                data, kind=ew.SEMANTIC_KIND, disproof_ref=ref, source_ref=ref,
                expires=(entry.expires or parsed.expires).isoformat(), entities=list(entry.entities),
                condition=entry.condition, check_frequency=entry.check_frequency,
                action_48h=entry.action_48h, node=parsed.node, quote_locator="structure reading disproof[]",
                note=f"讀圖 {parsed.reading_id} 的第 {index} 條反證",
            )
            summary["registered"].append(watch["watch_id"])
        for customer in demand_side_customers(record):
            if any(w.get("wake_reading") == parsed.node and customer in (w.get("entities") or ())
                   and w.get("status") == "active" for w in data["watches"]):
                continue
            watch = ew.add_watch(
                data, kind="entity_filing_signal", wake_reading=parsed.node, expires=parsed.expires.isoformat(),
                entities=[customer], note=f"需求側客戶 {customer} 出了新一手文件 → {parsed.node} 該重讀",
            )
            summary["reread_registered"].append(watch["watch_id"])
    for watch in data["watches"]:
        if watch.get("wake_reading") == parsed.node and watch.get("status") == "fired":
            watch["status"] = "consumed"
            watch["closed"] = {"at": stamp, "note": f"已重讀：{parsed.reading_id}"}
            summary["reread_consumed"].append(watch["watch_id"])
        judgment = watch.get("judgment") or {}
        source_ref = str(watch.get("source_ref") or "")
        if (watch.get("kind") == ew.SEMANTIC_KIND and watch.get("node") == parsed.node
                and source_ref.startswith("reading:")
                and source_ref[len("reading:"):].split("#", 1)[0] not in other_unit_ids
                and judgment.get("touches") == "yes" and not judgment.get("handled")):
            judgment["handled"] = {"verb": "reread", "reading_id": parsed.reading_id, "at": stamp}
            summary["touched_handled"].append(watch["watch_id"])
    ew.save_watches(data, watches_path)
    return summary


def reread_reasons(node: str, watches: Sequence[Mapping[str, Any]]) -> list[str]:
    """這個節點為什麼該重讀（watch 那一側的理由）：需求側客戶出了新文件、讀圖的反證被判觸及未處置。"""
    reasons: list[str] = []
    for watch in watches:
        woken = watch.get("woken_by") or {}
        if watch.get("wake_reading") == node and watch.get("status") == "fired":
            reasons.append(f"客戶 {','.join(woken.get('shared_entities') or watch.get('entities') or [])}"
                           f" 出了新文件 {woken.get('lead_id')}")
        judgment = watch.get("judgment") or {}
        if watch.get("node") != node or not str(watch.get("source_ref") or "").startswith("reading:"):
            continue
        if judgment.get("touches") == "yes" and not judgment.get("handled"):
            reasons.append(f"反證被判觸及：{ew_label(watch.get('condition'))}")
        elif watch.get("status") == "expired" and not watch.get("expiry_resolution"):
            # 設計 B（Phase 1 Step 1.7）：讀圖來源的條件到期不鑄 pq2——重讀就是它的重問
            reasons.append(f"反證等滿一輪都沒發生：{ew_label(watch.get('condition'))}（重讀時換新一批）")
    return reasons


def ew_label(text: Any) -> str:
    from engine_b.event_watch import condition_label

    return condition_label(text)


def reading_status_rows(edges: Sequence[Any], *, today: Any, as_of: Any = None,
                        watches: Sequence[Mapping[str, Any]] = (),
                        directory: Path | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """每一份現行讀圖（節點, 單位）跟現在的圖還一不一致——**唯一算法**，讀圖 artifact 與走圖第 4 型共用。

    ⚠ 2026-09-26（Phase 2 Step 2.6）由 `webapp/materialize.py::materialize_structure_readings` 原樣搬出：
    走圖要問「哪份讀圖該重讀」，若在走圖裡再寫一份比對，兩份會立刻開始偏離（L16）。
    `edges` 由呼叫端一次載入（節點數會長，查詢次數不該跟著長）。回 `(rows, parse_errors)`。

    `needs_reread` ＝ 圖那一側（stale／expired）**或** watch 那一側（客戶出新文件、反證被判觸及）；
    `needs_reread_by_graph` 只看圖那一側——走圖第 4 型用它，watch 那一側由佇列段 `fired_reading_reread` 承載，
    不在兩處各算一次。
    """
    from query.structure import build_structure

    from ..structure_reading import needs_reread, reading_status, select_readings

    rows: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    for node in known_nodes(directory=directory):
        records, errors = read_reading_records(node, directory=directory)
        parse_errors.extend(errors)
        # 一列＝（節點, 單位）（v3，A1）：層讀圖與插槽讀圖各自現行、各自算 staleness。
        current = select_readings(records, as_of=as_of, today=today)
        if not current:
            # 有檔案但沒有現行紀錄（全部被撤回）——**不是「沒有這個節點」**，照實列出（INV-3）。
            rows.append({"node": node, "unit": None, "status": None, "reading_id": None,
                         "reason": "ledger 有紀錄但目前沒有現行的那一筆（已全部撤回）"})
            continue
        view = build_structure(node, edges)
        watch_reasons = reread_reasons(node, watches)
        for unit in sorted({r.unit for r in records} - set(current)):
            rows.append({"node": node, "unit": unit, "status": None, "reading_id": None,
                         "reason": f"這個節點的 {unit} 讀圖有紀錄但目前沒有現行的那一筆（已全部撤回）"})
        for unit, reading in current.items():
            status = reading_status(reading, view.as_dict(), today=today)
            by_graph = needs_reread(status)
            rows.append({
                "node": node,
                "unit": unit,
                "reading_id": reading.reading_id,
                "kind": reading.kind,
                "reading": reading.reading,
                "tickers": list(reading.tickers),
                "read_on": reading.created_on.isoformat(),
                "expires": reading.expires.isoformat(),
                **status,
                "needs_reread": by_graph or bool(watch_reasons),
                "needs_reread_by_graph": by_graph,
                "reread_reasons": watch_reasons,
            })
    return rows, parse_errors


def known_nodes(*, directory: Path | None = None) -> list[str]:
    """ledger 裡有紀錄的節點（由檔案內容回報真正的 node，不從檔名反推 slug）。"""
    root = directory or STRUCTURE_READING_DIR
    if not root.is_dir():
        return []
    nodes: list[str] = []
    for path in sorted(root.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                node = str(json.loads(text).get("node") or "")
            except ValueError:
                continue
            if node:
                nodes.append(node)
                break
    return nodes


__all__ = ["STRUCTURE_READING_DIR", "append_reading_record", "demand_side_customers", "fetch_structure_snapshot_with_quotes",
           "fetch_structure_snapshot", "known_nodes", "ledger_path", "read_reading_records",
           "register_reading_watches", "reread_reasons", "verify_citations", "verify_disproof_sources"]
