"""
extract.py — 從原始文件抽出供應鏈知識圖譜的中介 JSON。**session-in-the-loop，不接 API。**

## 為什麼不再呼叫 anthropic（2026-09-04）

使用者已定案不再使用 LLM API；實際流程早就是 session-in-the-loop——
`decision_lab assessment-scaffold` → session 寫判斷 → `reassess --assessment`
（268 筆紀錄佐證）。這支是最後兩個 legacy API 呼叫點之一，改成同一個形狀。

⚠ **拆成兩段，而且中間那段刻意留給 session：**

1. `--scaffold OUT.md` — 產生**完整的抽取提示**（system prompt ＋ 已知實體清單 ＋
   文件全文 ＋ 欄位指示）。deterministic，零外部相依。
2. `--response RESP.json --out OUT.json` — 吃 session 寫好的 JSON，跑**原封不動的
   後處理**：schema_version 預設、source id 加 doc_id 前綴（L6：局部 ID 跨文件
   MERGE 會命名空間衝突）、寫檔。

⚠ **後處理是這支的價值所在，不能省。** 從前它藏在 API 呼叫後面，看起來像是
「LLM 做完就好」；拆開之後才看得出來：真正不可替代的是 id 前綴與 schema 驗證，
而那兩件事跟哪個模型產出 JSON 完全無關（L3：抽取層輸出 DB 無關 JSON）。

用法：
    # ① 產提示
    python extract.py --input library/raw/<doc>.txt --source-type transcript \
        --evidence-tier 1 --scaffold extractions/<doc>.prompt.md
    # ② session 依提示產出 JSON，存成 <doc>.response.json
    # ③ 後處理
    python extract.py --input library/raw/<doc>.txt --source-type transcript \
        --evidence-tier 1 --response extractions/<doc>.response.json \
        --out extractions/<doc>.json

抽完跑 `loader/validate.py` 再進 Neo4j。

Env vars:
    NEO4J_*  — 本支不用；由 loader/load_to_neo4j.py 消費
    ⚠ **不再需要 ANTHROPIC_API_KEY。**
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent
SYSTEM_PROMPT_FILE = ROOT / "prompts" / "extract_system.md"
SAMPLE_FILE = ROOT / "samples" / "cpo_external_laser_source.json"


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_system_prompt() -> str:
    if not SYSTEM_PROMPT_FILE.exists():
        print(f"ERROR: System prompt not found at {SYSTEM_PROMPT_FILE}", file=sys.stderr)
        sys.exit(1)
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


def _known_entities_block() -> str:
    """Build the known-entity list from the hand-authored sample for the system prompt."""
    if not SAMPLE_FILE.exists():
        return "(no sample file found — entity list unavailable)"
    with open(SAMPLE_FILE, encoding="utf-8") as f:
        sample = json.load(f)
    lines = []
    for n in sample.get("nodes", []):
        role_note = f", role: {n['role']}" if n.get("role") else ""
        lines.append(
            f'  - id: "{n["id"]}", name: "{n["name"]}"'
            f', type: {n["type"]}, level: {n["abstraction_level"]}{role_note}'
        )
    return "\n".join(lines)


def _prefix_source_ids(doc: dict, doc_id: str) -> dict:
    """Rewrite all source IDs from local s{N} to {doc_id}_s{N} format.

    Pure function — returns a new dict, does not mutate the input.
    Idempotent: skips IDs that already contain an underscore-s pattern (already prefixed).
    """
    import copy
    doc = copy.deepcopy(doc)

    mapping: dict[str, str] = {}
    for s in doc.get("sources", []):
        old_id = s["id"]
        # Already prefixed if it contains '_s' followed by digits
        if "_s" in old_id and old_id.split("_s")[-1].isdigit():
            mapping[old_id] = old_id
        else:
            new_id = f"{doc_id}_{old_id}"
            mapping[old_id] = new_id
            s["id"] = new_id

    def _rewrite(ids: list) -> list:
        return [mapping.get(sid, sid) for sid in ids]

    for n in doc.get("nodes", []):
        n["source_ids"] = _rewrite(n.get("source_ids", []))
    for e in doc.get("edges", []):
        e["source_ids"] = _rewrite(e.get("source_ids", []))
    for c in doc.get("claims", []):
        c["source_ids"] = _rewrite(c.get("source_ids", []))

    return doc


def _strip_code_fences(text: str) -> str:
    """Remove leading ```json or ``` and trailing ``` from LLM responses."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop the opening fence line (```json or ```)
        lines = lines[1:]
        # Drop the closing fence if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


# ── core extraction ────────────────────────────────────────────────────────────

def build_prompt(
    input_path: str,
    source_type: str,
    evidence_tier: int,
    title: str | None = None,
) -> tuple[str, str]:
    """組出 (system_prompt, user_message)。**純函式，零外部相依。**

    這一段從前埋在 API 呼叫裡，拆出來之後才測得到——提示本身就是契約
    （`prompts/extract_system.md` 的逐字規則，例如「具體型號／公司名必須在 quote 裡
    逐字出現」是 L6 Gap 4 的唯一防線）。
    """
    doc_path = Path(input_path)
    if not doc_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    doc_text = doc_path.read_text(encoding="utf-8")
    doc_id = doc_path.stem
    doc_title = title or doc_id

    system_prompt = _load_system_prompt().replace(
        "{{KNOWN_ENTITIES}}", _known_entities_block()
    )
    user_message = f"""Document to extract:

Title: {doc_title}
Source type: {source_type}
Evidence tier: {evidence_tier}

---

{doc_text}

---

Set these fields in source_doc:
  doc_id: "{doc_id}"
  title: "{doc_title}"
  source_type: "{source_type}"
  evidence_tier: {evidence_tier}

Output ONLY the JSON object."""
    return system_prompt, user_message


def write_scaffold(
    input_path: str,
    source_type: str,
    evidence_tier: int,
    scaffold_path: str,
    title: str | None = None,
) -> int:
    """把提示寫成一份 Markdown，交給 session 產出 JSON。"""
    system_prompt, user_message = build_prompt(
        input_path, source_type, evidence_tier, title
    )
    out = Path(scaffold_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# 抽取提示（session-in-the-loop）\n\n"
        "⚠ 依下列 system prompt 的規則產出**單一 JSON 物件**，存成檔案後用\n"
        "`python extract.py --input ... --response <該檔> --out <輸出>` 完成後處理。\n"
        "**不要自己補 source id 前綴或 schema_version**——那是後處理的事。\n\n"
    )
    out.write_text(
        header
        + "## System prompt\n\n" + system_prompt
        + "\n\n## Document\n\n" + user_message + "\n",
        encoding="utf-8",
    )
    print(f"[extract] 提示已寫入 {scaffold_path}；產出 JSON 後用 --response 完成後處理",
          file=sys.stderr)
    return 0


def ingest_response(
    input_path: str,
    response_path: str,
    out_path: str,
) -> int:
    """吃 session 產出的 JSON，跑 deterministic 後處理並寫檔。

    ⚠ 後處理**與從前一字不差**：`schema_version` 預設、source id 加 doc_id 前綴。
    前綴那一步是 L6 的教訓——局部 ID 在單文件內沒問題，跨文件 MERGE 後會命名空間衝突。
    """
    raw_text = Path(response_path).read_text(encoding="utf-8")
    cleaned = _strip_code_fences(raw_text)
    try:
        doc = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"ERROR: {response_path} 不是合法 JSON：{exc}", file=sys.stderr)
        print("  ⚠ 這是 session 產出的內容有問題，不是抽取失敗——修 JSON 後重跑即可。",
              file=sys.stderr)
        return 1

    doc.setdefault("schema_version", "0.1")
    doc = _prefix_source_ids(doc, Path(input_path).stem)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[extract] Wrote {out_path}", file=sys.stderr)
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="從原始文件抽出供應鏈知識圖譜的中介 JSON（session-in-the-loop，不接 API）"
    )
    ap.add_argument(
        "--input", required=True,
        help="Path to the raw document text file (pre-trimmed to the relevant section).",
    )
    ap.add_argument(
        "--source-type", required=True,
        choices=["filing", "transcript", "ir_deck", "industry_report", "paper", "news", "social"],
        help="Document source type (must match schema/vocab.json source_type).",
    )
    ap.add_argument(
        "--evidence-tier", required=True, type=int, choices=[1, 2, 3, 4],
        help="Evidence tier: 1=filing/transcript (strongest) … 4=social (weakest).",
    )
    ap.add_argument(
        "--scaffold",
        help="產生抽取提示到這個路徑（第一段）。與 --response 互斥。",
    )
    ap.add_argument(
        "--response",
        help="session 產出的 JSON 檔（第二段）。需搭配 --out。",
    )
    ap.add_argument(
        "--out",
        help="中介 JSON 的輸出路徑（例：extractions/coherent_q3.json）。搭配 --response。",
    )
    ap.add_argument(
        "--title",
        help="Human-readable document title. Defaults to the input filename stem.",
    )
    args = ap.parse_args()

    # ⚠ 兩段互斥且各自必要——不給任何一段時**明確報錯，不預設走某一段**。
    # 這支從前是一個命令做完全部；沉默地挑一段會讓使用者以為抽取完成了。
    if bool(args.scaffold) == bool(args.response):
        ap.error("--scaffold 與 --response 必須且只能擇一"
                 "（先 --scaffold 產提示，session 產出 JSON 後再 --response）")
    if args.scaffold:
        return write_scaffold(
            input_path=args.input,
            source_type=args.source_type,
            evidence_tier=args.evidence_tier,
            scaffold_path=args.scaffold,
            title=args.title,
        )
    if not args.out:
        ap.error("--response 必須搭配 --out")
    return ingest_response(
        input_path=args.input,
        response_path=args.response,
        out_path=args.out,
    )


if __name__ == "__main__":
    raise SystemExit(main())
