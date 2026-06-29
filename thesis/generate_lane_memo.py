"""
generate_lane_memo.py — 用 Claude API 生成 CPO/矽光子 Directional Lane Memo。

流程:
  1. 建立 Neo4j driver，呼叫 query.graph_context.build_context() 取得結構化 Markdown
  2. 讀 prompts/lane_memo_system.md 作為 system prompt
  3. 呼叫 anthropic.messages.create (claude-sonnet-4-6)
  4. 輸出寫入 --out 指定路徑（預設 thesis/cpo_v1_lane_memo.md）

用法:
    python thesis/generate_lane_memo.py
    python thesis/generate_lane_memo.py --out thesis/cpo_v1_lane_memo.md

Env vars:
    ANTHROPIC_API_KEY  — required
    NEO4J_URI          — default bolt://localhost:7687
    NEO4J_USER         — default neo4j
    NEO4J_PASSWORD     — required
    THESIS_MODEL       — optional; defaults to claude-sonnet-4-6
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_FILE = ROOT / "prompts" / "lane_memo_system.md"
DEFAULT_OUT = ROOT / "thesis" / "cpo_v1_lane_memo.md"


def _check_env() -> bool:
    ok = True
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY が未設定", file=sys.stderr)
        ok = False
    if not os.environ.get("NEO4J_PASSWORD"):
        print("ERROR: NEO4J_PASSWORD が未設定", file=sys.stderr)
        ok = False
    return ok


def generate(out_path: str | Path | None = None, model: str | None = None) -> int:
    if not _check_env():
        return 1

    # Imports
    try:
        from anthropic import Anthropic
    except ImportError:
        print("需要 anthropic 套件: pip install anthropic", file=sys.stderr)
        return 1
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("需要 neo4j 套件: pip install neo4j", file=sys.stderr)
        return 1

    sys.path.insert(0, str(ROOT))
    from query.graph_context import build_context

    # System prompt
    if not SYSTEM_PROMPT_FILE.exists():
        print(f"ERROR: System prompt not found: {SYSTEM_PROMPT_FILE}", file=sys.stderr)
        return 1
    system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")

    # Graph context
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pw = os.environ.get("NEO4J_PASSWORD")
    driver = GraphDatabase.driver(uri, auth=(user, pw))
    try:
        context = build_context(driver)
    finally:
        driver.close()

    if context.startswith("⚠"):
        print(f"ERROR: 圖資料不足，無法生成 thesis。\n{context}", file=sys.stderr)
        return 1

    # Claude API call
    model = model or os.environ.get("THESIS_MODEL", "claude-sonnet-4-6")
    user_message = f"""\
以下是 CPO/矽光子供應鏈知識圖譜的結構化上下文，請依照 system prompt 的格式撰寫 Directional Lane Memo。

{context}

輸出 Markdown 格式的 Lane Memo，直接開始寫，不要加前言或解釋。"""

    print(f"[generate_lane_memo] model={model}", file=sys.stderr)
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    memo_text = response.content[0].text

    # Write output
    out = Path(out_path) if out_path else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(memo_text, encoding="utf-8")
    print(f"[generate_lane_memo] wrote {out}", file=sys.stderr)
    print(f"\n--- Lane Memo preview (first 500 chars) ---\n{memo_text[:500]}\n---",
          file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate CPO/矽光子 Directional Lane Memo using Claude API."
    )
    ap.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Output path for the Lane Memo markdown file.",
    )
    ap.add_argument(
        "--model",
        help="Claude model override (env: THESIS_MODEL; default: claude-sonnet-4-6).",
    )
    args = ap.parse_args()
    return generate(out_path=args.out, model=args.model)


if __name__ == "__main__":
    raise SystemExit(main())
