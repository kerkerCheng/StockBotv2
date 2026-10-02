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
                     *, registry: Any = None, publishers: Any = None) -> list[str]:
    """v3 引用的寫入端核對（plan A2）：回傳問題清單，空＝全部核對得到。**不查圖**——`quotes` 必須與
    紀錄的快照出自同一次查詢（`fetch_structure_snapshot_with_quotes`）。

    每一條引用：①邊在紀錄快照的那個角度裡；②片段（去空白正規化）是那條邊某段逐字的子字串，且那段逐字
    出自 `source_id` 那份文件；③標 `independent` 的，那份文件的 `origin_entity` 經
    `query.origin_resolution.resolve_origin`（唯一 owner，與邊的證據等級同一個；Step 4.3）解析成：
    名冊公司且不是那條邊的主詞（供應商自己），或**算印證的發布者**（`publisher_lifts`：自產資料的類別、
    或宣告 `origin_linkage=independent` 的媒體文；宣告 same_origin 的一律不算）。解析不到的不算。
    """
    parsed = parse_structure_reading_record(record)
    problems: list[str] = []
    if not parsed.citations:
        return problems
    if registry is None:
        from identity.registry import get_registry

        registry = get_registry()
    from query.origin_resolution import publisher_lifts, resolve_origin

    # 插槽的「不是供應商自己」＝不是**這個插槽的任何一家供應商**（與插槽視角的「客戶端原文」同一個定義；
    # plan 待決 #12，Step 2.5 定案）。實測：`prod:els_8ch_module` 用同插槽另一家供應商 Enablence 發的聯合新聞稿
    # 標 independent，舊規則（只排除那條邊的主詞）放行了一份 Sivers 的插槽護城河——聯合公告方與它利益一致，不是客戶。
    # 層讀圖不變：一層的其他供應商是競爭者，不是聯合公告方。
    # ⚠ 扣掉**製造者**（對這個產品有 `develops` 的公司；plan 待決 #22）：製造者是插槽那一格的客戶，它的一手
    # 就是客戶端原文。製造者從**同一次查詢的逐字鍵**取（`develops` 不在五個角度、快照裡沒有）——
    # 一條 develops 邊若沒有逐字，那家會被當成供應商而被排除：方向是更嚴，不會放寬。
    makers = {str(k[0]) for k in quotes if len(k) == 3 and k[1] == "develops" and k[2] == parsed.node}
    socket_suppliers = ({str(row[0]) for row in parsed.angles.get("supply_side", ())} - makers
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
            problems.extend(_independence_problems(label, citation.source_id, edge[0], hits, socket_suppliers,
                                                   registry=registry, publishers=publishers,
                                                   resolve_origin=resolve_origin, publisher_lifts=publisher_lifts))
    return problems


def _independence_problems(label: str, source_id: str, subject: str, hits: Sequence[Mapping[str, Any]],
                           socket_suppliers: set[str], *, registry: Any, publishers: Any,
                           resolve_origin: Any, publisher_lifts: Any) -> list[str]:
    """一條標 `independent` 的引用，它那份文件的 origin 撐不撐得住「不是供應商自己」。

    `hits` 都出自同一份文件（`source_id`），所以通常只有一個 origin；逐個 origin 判，任何一個撐不住就說出來。
    """
    problems: list[str] = []
    by_origin: dict[str, set] = {}
    for q in hits:
        by_origin.setdefault(str(q.get("origin") or ""), set()).add(q.get("origin_linkage") or None)
    for origin, linkages in sorted(by_origin.items()):
        resolution = resolve_origin(origin, registry, publishers=publishers)
        if resolution.kind == "company":
            if resolution.id == subject:
                problems.append(f"{label}：標了 independent，但來源 {source_id} 就是 {subject} 自己——"
                                "供應商自稱是弱主張（L8）")
            elif resolution.id in socket_suppliers:
                problems.append(f"{label}：標了 independent，但來源 {source_id} 是這個插槽的另一家供應商 "
                                f"{resolution.id}——同插槽的聯合公告方不是客戶端（L8；plan 待決 #12）")
        elif resolution.kind == "publisher":
            if not publisher_lifts(resolution, linkages):
                problems.append(
                    f"{label}：標了 independent，但來源 {source_id} 的 origin_entity {origin!r} 是"
                    f"{'宣告為轉述（same_origin）的' if 'same_origin' in linkages else '沒宣告 independent 的媒體'}文件"
                    "——轉述不是第三方印證（L11-3）；要追它轉述的那份一手")
        else:
            problems.append(f"{label}：標了 independent，但來源 {source_id} 的 origin_entity "
                            f"{origin!r} 解析不到任何 co:* 或登記的發布者——解析不到的不算外部印證（L8、INV-1）")
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


def evidence_rank() -> Mapping[str, int]:
    """證據等級的 rank——唯一 owner 是 `query.bottleneck.EVIDENCE_RANK`，這裡只是把它遞給不能 import `query` 的
    讀圖 staleness（`alpha.structure_reading.staleness.reading_status` 的 `evidence_rank=`；Phase 6 Step 6.1）。
    回傳的就是那一份物件，不是副本。"""
    from query.bottleneck import EVIDENCE_RANK

    return EVIDENCE_RANK


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

    rank = evidence_rank()
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
            status = reading_status(reading, view.as_dict(), today=today, evidence_rank=rank)
            by_graph = needs_reread(status)
            # 讀圖頁要印得出「判讀憑哪一段原文」與「每條反證登記成哪一筆 watch」（Step 2.7；L18：標籤指得回原始證據）。
            # watch 以 `reading:<id>#<序>` 指回（`register_reading_watches` 的鍵）；沒登記到就是 None，照實印。
            by_ref = {str(w.get("source_ref")): w for w in watches if str(w.get("source_ref") or "").startswith("reading:")}
            disproof = []
            for index, entry in enumerate(reading.disproof, 1):
                watch = by_ref.get(f"reading:{reading.reading_id}#{index}") or {}
                disproof.append({"condition": entry.condition, "entities": list(entry.entities),
                                 "check_frequency": entry.check_frequency, "action_48h": entry.action_48h,
                                 "source": entry.source, "watch_id": watch.get("watch_id"),
                                 "watch_status": watch.get("status")})
            citations = [{"angle": c.angle, "edge": list(c.edge), "quote": c.quote, "source_id": c.source_id,
                          "independent": c.independent} for c in reading.citations]
            # 需求側客戶（Phase 3 Step 3.7）：個股頁 argument 鏈段的需求端改讀**這份讀圖當時查到的需求側**，
            # 不再經 `get_bottlenecks` 的 sub≥4 需求錨（filter 殘留，G1）。沿用登記 watch 的同一個函式（L16）。
            customers = demand_side_customers({"node": node, "angles": reading.angles})
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
                "citations": citations,
                "disproof": disproof,
                "demand_customers": customers,
            })
    return rows, parse_errors


#: 公司「坐在」哪些節點：它對那個節點有這兩種邊之一（由**圖**推，INV-1——不靠讀圖紀錄裡的 ticker）。
SEAT_RELATIONS: tuple[str, ...] = ("supplies_to", "develops")


def seat_readings_context(*, today: Any = None, as_of: Any = None) -> dict[str, Any]:
    """讀圖面板與 argument 鏈段的輸入：**一次**載入圖的邊與讀圖 ledger，給每一檔切用（`seat_readings_for`）。

    - `seats`：`co:*` → 它 `supplies_to`／`develops` 到的非公司節點（讀圖只寫在層與插槽上）。
    - `by_node`：節點 → 現行讀圖（每個單位一份）＋ 由讀圖字彙附上的中文標籤——消費端（compose、builder）
      不碰讀圖字彙，標籤在這裡附上，那一端只照抄（L16：字彙只有一份）。每列帶 `demand_customers`（Step 3.7）。
    讀不到就整份回 `upstream_unavailable`，不回空集合——空集合會讓每一檔都印「還沒讀」（INV-3）。
    ⚠ Step 3.7 由 `webapp/materialize.py::readings_context` 原樣搬來（briefing 的 CLI 也要用，briefing 不得 import webapp）。
    ⚠ **as-of 視角明確拒絕**（INV-6；3.7 R1）：坐在哪些節點讀的是現在的圖（`_load_edges` 沒有時點投影），讀圖對圖的
    staleness 也拿現在的圖與今天比——拿它回答「T 時刻這一層變了沒」就是用當前值冒充。讀圖面板升核心後這會進 readiness。
    """
    from datetime import date

    if as_of is not None:
        return {"absence": {"kind": "point_in_time_unavailable",
                            "reason": "as-of 視角沒有讀圖對圖的時點投影——坐在哪一層、那一層變了沒都只有現在的圖（INV-6）"}}
    try:
        from query.structure import _load_edges

        from ..structure_reading import READING_KINDS, READING_UNITS
        from ..structure_reading.staleness import READING_STATUSES

        edges = _load_edges()
        rows, _errors = reading_status_rows(edges, today=today or date.today(), as_of=as_of)
    except Exception as exc:  # noqa: BLE001 — 讀不到圖只讓讀圖面板與鏈段需求端說讀不到，其餘照走
        return {"absence": {"kind": "upstream_unavailable",
                            "reason": f"這次沒讀到圖或讀圖 ledger（{type(exc).__name__}）——不是「沒有讀圖」"}}
    seats: dict[str, set[str]] = {}
    for edge in edges:
        if edge.src.startswith("co:") and edge.relation in SEAT_RELATIONS and not edge.dst.startswith("co:"):
            seats.setdefault(edge.src, set()).add(edge.dst)
    by_node: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not row.get("reading_id"):
            continue
        reasons = list(row.get("reread_reasons") or ())
        status_label = READING_STATUSES.get(str(row.get("status")), "這次沒比對到圖（不是現行）")
        if reasons:
            status_label += "；另有重讀理由：" + "；".join(reasons[:2])
        by_node.setdefault(str(row["node"]), []).append({
            "node": row["node"], "unit": row.get("unit"),
            "unit_label": str(READING_UNITS.get(str(row.get("unit")), row.get("unit"))).split("讀圖")[0],
            "kind": row.get("kind"),
            "kind_label": str(READING_KINDS.get(str(row.get("kind")), row.get("kind"))).split("——")[0],
            "status": row.get("status"), "status_label": status_label, "reason": row.get("reason"),
            "reading_id": row.get("reading_id"), "read_on": row.get("read_on"), "expires": row.get("expires"),
            "reading": row.get("reading"), "needs_reread": row.get("needs_reread"),
            "demand_customers": list(row.get("demand_customers") or ()),
        })
    return {"seats": {co: sorted(nodes) for co, nodes in seats.items()}, "by_node": by_node}


def demand_side_abstention(ticker: str, *, today: Any = None, directory: Path | None = None) -> Any:
    """這檔現行的 `readings/demand_side` abstention（刻意不主張：它在需求側、不坐任何層）；沒有或讀不到回 `None`。

    讀不到 ledger 時回 `None`（＝沒有宣告），面板照舊印原本的缺席——不因為讀不到而把 blocker 變 settled。"""
    from datetime import date as _date

    from alpha.abstention.contracts import select_abstention

    from .abstentions import read_abstention_records

    try:
        records, _errors = read_abstention_records(ticker, directory=directory)
    except OSError:
        return None
    return select_abstention(records, layer="readings", subject="demand_side", period_end=None, as_of=None,
                             today=today or _date.today())


def seat_readings_for(context: Mapping[str, Any], company_id: str | None, *,
                      demand_side: Any = None) -> dict[str, Any]:
    """一家公司坐的節點與那些節點的現行讀圖（Phase 2 Step 2.7 的組法；3.7 起讀圖面板與 argument 鏈段共用）。

    `context`：`webapp.materialize.readings_context()` 的輸出（`{"seats", "by_node"}` 或 `{"absence"}`）。
    缺席分型由這裡宣告（L16）：讀不到圖／沒有 co: id＝`upstream_unavailable`；坐的節點都沒有讀圖＝交給消費端寫
    `not_yet_recorded`。⚠ 由 `co:*` 推（INV-1），不靠讀圖紀錄裡的 ticker。

    `demand_side`：這檔現行的 `readings/demand_side` abstention（`demand_side_abstention()`；2026-09-30 使用者核准）。
    **只在圖上沒有它坐的層時採用**——宣告 `deliberate_abstention`（settled），理由照抄那筆紀錄；
    圖上有它坐的層時不採用（宣告和圖矛盾），照舊 `not_yet_recorded` 並在理由裡寫明。"""
    if context.get("absence"):
        return {"absence": dict(context["absence"])}
    if not company_id:
        return {"absence": {"kind": "upstream_unavailable",
                            "reason": "這檔沒有 co: id（registry 解析不到），推不出它坐在哪些節點（INV-1）"}}
    seats = list((context.get("seats") or {}).get(company_id) or ())
    by_node = context.get("by_node") or {}
    readings = [r for node in seats for r in by_node.get(node, ())]
    # 沒有讀圖時是哪一種沒有——由這裡宣告，面板照抄（L12：「還沒讀」與「圖上沒有可讀的層」下一步不同）。
    empty = ({"kind": "not_yet_recorded",
              "reason": "這家公司坐的層與插槽都還沒有讀圖（圖上它供貨或開發的節點：" + "、".join(seats) + "）"}
             if seats else
             {"kind": "upstream_unavailable",
              "reason": "圖上沒有它供貨或開發的層或插槽——讀圖寫在層與插槽上，要先補圖的供貨／開發邊，或判定它在需求側"})
    if demand_side is not None:
        declared = (f"刻意不主張：它在需求側、不坐任何層——{demand_side.reason}｜什麼會改寫：{demand_side.revisit_when}"
                    f"｜宣告於 {demand_side.created_on.isoformat()}（{demand_side.abstention_id}）")
        if not seats:
            empty = {"kind": "deliberate_abstention", "reason": declared, "settled_by": demand_side.abstention_id}
        else:
            empty = {**empty, "reason": empty["reason"] + "｜⚠ 有一筆需求側宣告（" + demand_side.abstention_id
                     + "）但圖上有它坐的層，和圖矛盾，不採用"}
    return {"seats": seats, "readings": readings, "empty": empty}


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


__all__ = ["STRUCTURE_READING_DIR", "append_reading_record", "demand_side_customers", "evidence_rank",
           "fetch_structure_snapshot_with_quotes", "fetch_structure_snapshot", "known_nodes", "ledger_path",
           "read_reading_records",
           "register_reading_watches", "reread_reasons", "seat_readings_context", "seat_readings_for",
           "verify_citations",
           "verify_disproof_sources"]
