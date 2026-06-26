"""
extract.py — LLM-based extraction of supply-chain knowledge graph from raw documents.

Reads prompts/extract_system.md as the system prompt at startup.
Injects the known-entity list from samples/cpo_external_laser_source.json so the LLM
reuses canonical IDs (e.g. co:broadcom) instead of inventing duplicates.

Usage:
    python extract.py --input library/raw/<doc>.txt \\
                      --source-type transcript \\
                      --evidence-tier 1 \\
                      --out extractions/<doc>.json

On JSON parse error: writes raw LLM response to extractions/<doc>_raw.txt and exits 1.
Run loader/validate.py on the output before loading into Neo4j.

Env vars:
    ANTHROPIC_API_KEY  — required
    NEO4J_*            — not used by this script; consumed by loader/load_to_neo4j.py
    EXTRACT_MODEL      — optional; defaults to claude-sonnet-4-6
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

def extract(
    input_path: str,
    source_type: str,
    evidence_tier: int,
    out_path: str,
    title: str | None = None,
    model: str | None = None,
) -> int:
    try:
        from anthropic import Anthropic
    except ImportError:
        print("需要 anthropic 套件: pip install anthropic", file=sys.stderr)
        return 1

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("請設 ANTHROPIC_API_KEY 環境變數", file=sys.stderr)
        return 1

    model = model or os.environ.get("EXTRACT_MODEL", "claude-sonnet-4-6")

    # Load and patch system prompt
    system_prompt = _load_system_prompt()
    system_prompt = system_prompt.replace("{{KNOWN_ENTITIES}}", _known_entities_block())

    # Read document
    doc_path = Path(input_path)
    if not doc_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 1
    doc_text = doc_path.read_text(encoding="utf-8")

    doc_id = doc_path.stem
    doc_title = title or doc_id

    # Build user message
    user_message = f"""\
Document to extract:

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

    # Call API
    print(f"[extract] model={model}  input={input_path}", file=sys.stderr)
    client = Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text

    # Parse JSON
    cleaned = _strip_code_fences(raw_text)
    try:
        doc = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        out = Path(out_path)
        raw_file = out.parent / (out.stem + "_raw.txt")
        raw_file.parent.mkdir(parents=True, exist_ok=True)
        raw_file.write_text(raw_text, encoding="utf-8")
        print(f"ERROR: LLM response is not valid JSON: {exc}", file=sys.stderr)
        print(f"  Raw response saved to {raw_file}", file=sys.stderr)
        print("  Fix the system prompt and retry.", file=sys.stderr)
        return 1

    # Ensure schema_version is set
    doc.setdefault("schema_version", "0.1")

    # Write output
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[extract] Wrote {out_path}", file=sys.stderr)
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract supply-chain knowledge graph from a raw document via Claude."
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
        "--out", required=True,
        help="Output path for the intermediate JSON (e.g. extractions/coherent_q3.json).",
    )
    ap.add_argument(
        "--title",
        help="Human-readable document title. Defaults to the input filename stem.",
    )
    ap.add_argument(
        "--model",
        help="Claude model override (env: EXTRACT_MODEL; default: claude-sonnet-4-6).",
    )
    args = ap.parse_args()

    return extract(
        input_path=args.input,
        source_type=args.source_type,
        evidence_tier=args.evidence_tier,
        out_path=args.out,
        title=args.title,
        model=args.model,
    )


if __name__ == "__main__":
    raise SystemExit(main())
