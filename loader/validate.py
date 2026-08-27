"""
validate.py — 驗證一份中介 JSON 是否合法且自洽。

檢查三層:
1. JSON Schema(schema/intermediate_format.schema.json)
2. 字彙(schema/vocab.json):type/relation/level/role/... 是否都在對照表
3. 參照完整性:edge/claim 指到的 id 是否都存在;source_ids 是否都在 sources

用法:
    pip install jsonschema
    python loader/validate.py samples/cpo_external_laser_source.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Windows consoles default to cp950; force utf-8 so ✓/✗ render correctly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "intermediate_format.schema.json"
VOCAB = ROOT / "schema" / "vocab.json"


def _load(p: Path) -> dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# 法人後綴不帶識別力：Coherent Corporation 與 Coherent Inc 是同一家。
_CORP_SUFFIX = re.compile(
    r"\b(corporation|corp|inc|incorporated|ltd|limited|llc|plc|nv|sa|ab|oyj|"
    r"company|holdings|holding|group)\b\.?",
    re.IGNORECASE,
)


def _core_tokens(name: str) -> set[str]:
    """取名稱的核心識別 token（小寫、去法人後綴與標點、濾掉過短詞）。"""
    s = _CORP_SUFFIX.sub(" ", name.casefold())
    s = re.sub(r"[^\w\s]", " ", s)
    return {t for t in s.split() if len(t) >= 3}


def validate(doc_path: str) -> list[str]:
    errors: list[str] = []
    doc = _load(Path(doc_path))
    vocab = _load(VOCAB)

    # ── 1. JSON Schema ──
    try:
        import jsonschema
        jsonschema.validate(doc, _load(SCHEMA))
    except ImportError:
        errors.append("WARN: 未裝 jsonschema,跳過結構驗證(pip install jsonschema)")
    except Exception as ex:  # jsonschema.ValidationError
        errors.append(f"SCHEMA: {getattr(ex, 'message', ex)}")

    node_ids = {n["id"] for n in doc.get("nodes", [])}
    source_ids = {s["id"] for s in doc.get("sources", [])}

    # ── 2. 字彙 ──
    for n in doc.get("nodes", []):
        if n["type"] not in vocab["node_type"]:
            errors.append(f"VOCAB: node {n['id']} type={n['type']} 不在對照表")
        if n["abstraction_level"] not in vocab["abstraction_level"]:
            errors.append(f"VOCAB: node {n['id']} level={n['abstraction_level']} 不在對照表")
        if n.get("role") and n["role"] not in vocab["role"]:
            errors.append(f"VOCAB: node {n['id']} role={n['role']} 不在對照表")
    for e in doc.get("edges", []):
        if e["relation"] not in vocab["relation"]:
            errors.append(f"VOCAB: edge {e['id']} relation={e['relation']} 不在對照表")
        if "lead_time_weeks" in e.get("attributes", {}):
            errors.append(
                f"SCHEMA: edge {e['id']} 使用已停用的 lead_time_weeks；"
                "正常關係基準請用 structural_lead_time_weeks，內在物理週期請用 "
                "intrinsic_cycle_time_weeks，當期實際交期請存 dated Claim/Engine C observation"
            )
        qs = e.get("attributes", {}).get("qualification_status")
        if qs and qs not in vocab["qualification_status"]:
            errors.append(f"VOCAB: edge {e['id']} qualification_status={qs} 不在對照表")
    for i, c in enumerate(doc.get("claims", [])):
        cid = c.get("id", f"claims[{i}]")
        if "id" not in c:
            errors.append(f"REF: {cid} 缺 id 欄位（慣例 cl1、cl2…；跨文件重載的 MERGE 依賴穩定 id）")
        if c["demand_proof_level"] not in vocab["demand_proof_level"]:
            errors.append(f"VOCAB: claim {cid} demand_proof_level={c['demand_proof_level']} 不在對照表")
    sd = doc["source_doc"]
    if sd["source_type"] not in vocab["source_type"]:
        errors.append(f"VOCAB: source_doc source_type={sd['source_type']} 不在對照表")
    if sd["evidence_tier"] not in vocab["evidence_tier"]:
        errors.append(f"VOCAB: source_doc evidence_tier={sd['evidence_tier']} 不在對照表")

    # ── 4. 來源獨立性 (L8) ──
    origin = doc["source_doc"].get("origin_entity")
    if not origin:
        errors.append(
            "WARN: source_doc.origin_entity 未填 — "
            "無法做 L8 來源獨立性檢查（Lane Memo 生成時會被計為零獨立來源）"
        )
    else:
        # G5 同質性：sole_source 只有客戶端或第三方能確認；供應商自報最高只算
        # verified_by_absence（weak），入圖前先在文件層警告。
        #
        # 兩個曾經漏抓的形狀（2026-08-27 由 NVDA EX-99.2 實例發現）：
        # (a) 只認 type=="Company" — 把 issuer 包裝成 TechNode（tech:nvidia_ai_infrastructure）
        #     就能靜默通過。issuer 是誰跟節點型別無關，所以改為不限型別。
        # (b) 只查 src — 但 sole_source 替誰背書要看 relation 方向。issuer 自承
        #     「我依賴 B」是不利益陳述、反而可信；issuer 自稱「沒人能取代我」才需要警告。
        # (c) 名稱比對原本用雙向子字串，對 Company 節點碰巧有效（"nvidia" 是
        #     "nvidia corporation" 的子字串），但 issuer 一旦被包裝成描述性名稱就失效：
        #     "NVIDIA AI Data Center Infrastructure" 與 "NVIDIA Corporation" 互相都不是
        #     對方的子字串。改比對核心 token 的包含關係（去掉法人後綴與過短詞）。
        origin_tokens = _core_tokens(origin)

        def _is_origin_entity(node: dict) -> bool:
            if not origin_tokens:
                return False
            for name in [node.get("name") or "", *node.get("aliases", [])]:
                tokens = _core_tokens(name)
                if not tokens:
                    continue
                if origin_tokens <= tokens or tokens <= origin_tokens:
                    return True
            return False

        origin_node_ids = {
            n["id"] for n in doc.get("nodes", []) if _is_origin_entity(n)
        }
        beneficiary_end = vocab.get("sole_source_beneficiary_end", {})
        for e in doc.get("edges", []):
            if not e.get("attributes", {}).get("sole_source"):
                continue
            # 未登記受益端的 relation 兩端都查（fail safe）。
            end = beneficiary_end.get(e["relation"])
            ends = {"src": ["src_id"], "dst": ["dst_id"]}.get(end, ["src_id", "dst_id"])
            for key in ends:
                if e[key] not in origin_node_ids:
                    continue
                errors.append(
                    f"WARN: edge {e['id']} 的 sole_source=true 由受益方自報"
                    f"（origin_entity={origin} 即 {key[:3]} {e[key]}）— "
                    "L8 只能算 verified_by_absence（weak），需客戶端或第三方來源印證"
                )
                break

    # ── 4b. co:* 身分解析（registry 是唯一權威）──
    # 類別詞被實體化成公司節點（co:nvidia_direct_customers_csp）與未具名實體
    # （co:unnamed_ai_research_deployment_co）都會在這裡現形。實測 106 份既有抽取、
    # 202 個 co:* 節點只有 5 個未命中，且那 5 個都是真公司待 onboard —— 訊噪比夠高才留這道檢查。
    # 這是 WARN 不是 ERROR：未命中有兩種正當結局（幻覺→刪除、真公司→onboard），
    # 都需要人判斷，不能由 validate 代決。
    try:
        registry = _load(ROOT / "config" / "company_identity.json")
        known = {c["company_id"] for c in registry.get("companies", [])}
    except (OSError, ValueError, KeyError):
        known = None
        errors.append(
            "WARN: 無法讀取 config/company_identity.json — 跳過 co:* 身分解析檢查"
        )
    if known is not None:
        for n in doc.get("nodes", []):
            nid = n["id"]
            if not nid.startswith("co:") or nid in known:
                continue
            errors.append(
                f"WARN: node {nid}（{n.get('name')}）不在 config/company_identity.json — "
                "須明確分流：若是把類別詞或未具名實體當成公司則刪除該節點；"
                "若是真公司則先 onboard 進 registry 再入圖。不得靜默入圖。"
            )

    # ── 3. 參照完整性 ──
    def _check_sources(owner: str, sids: list[str]) -> None:
        for sid in sids:
            if sid not in source_ids:
                errors.append(f"REF: {owner} 的 source_id={sid} 不在 sources")

    for n in doc.get("nodes", []):
        _check_sources(f"node {n['id']}", n["source_ids"])
    for e in doc.get("edges", []):
        if e["src_id"] not in node_ids:
            errors.append(f"REF: edge {e['id']} src_id={e['src_id']} 無對應 node")
        if e["dst_id"] not in node_ids:
            errors.append(f"REF: edge {e['id']} dst_id={e['dst_id']} 無對應 node")
        _check_sources(f"edge {e['id']}", e["source_ids"])
    edge_ids = {e["id"] for e in doc.get("edges", [])}
    for i, c in enumerate(doc.get("claims", [])):
        cid = c.get("id", f"claims[{i}]")
        if c["subject_id"] not in node_ids and c["subject_id"] not in edge_ids:
            errors.append(f"REF: claim {cid} subject_id={c['subject_id']} 無對應 node 或 edge")
        _check_sources(f"claim {cid}", c["source_ids"])

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python loader/validate.py <doc.json>", file=sys.stderr)
        return 2
    errs = validate(sys.argv[1])
    hard = [e for e in errs if not e.startswith("WARN")]
    for e in errs:
        print(("  ✗ " if not e.startswith("WARN") else "  ! ") + e)
    if hard:
        print(f"\nFAIL: {len(hard)} 個錯誤")
        return 1
    print(f"\nOK: {Path(sys.argv[1]).name} 通過驗證"
          + (" (有 warning)" if errs else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
