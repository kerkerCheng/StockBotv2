"""Best-effort outbound Daily Brief publisher for Codex and Claude Code.

Usage (PowerShell):
    Get-Content <private-brief.md> | .venv\\Scripts\\python.exe \
        scripts\\publish_daily_brief.py --stdin --summary "..."

The command always returns zero unless ``--strict`` is supplied.  A transport
failure is printed as a redacted JSON result and must not block the Daily Brief.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - requirements.txt includes python-dotenv
    load_dotenv = None

from notifications.publisher import publish_daily_brief


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish one Daily Brief outbound notification")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--stdin", action="store_true", help="read the exact final Markdown from stdin")
    source.add_argument("--brief-file", type=Path, help="read the exact final Markdown from a private file")
    parser.add_argument("--summary", required=True, help="one-line or short action-first summary")
    parser.add_argument("--claude-share-url")
    parser.add_argument("--claude-session-id")
    parser.add_argument("--codex-thread-id")
    parser.add_argument("--strict", action="store_true", help="return non-zero when delivery fails")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env", override=False)
    if args.stdin:
        brief_text = sys.stdin.read()
    else:
        try:
            brief_text = args.brief_file.read_text(encoding="utf-8")
        except OSError as exc:
            result = {
                "status": "delivery_failed",
                "error_code": f"brief_file_{type(exc).__name__}",
            }
            print(json.dumps(result, ensure_ascii=False))
            return 1 if args.strict else 0
    result = publish_daily_brief(
        brief_text,
        summary=args.summary,
        repo_root=ROOT,
        claude_share_url=args.claude_share_url,
        claude_session_id=args.claude_session_id,
        codex_thread_id=args.codex_thread_id,
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False))
    if args.strict and result.status in {"delivery_failed", "not_configured"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
