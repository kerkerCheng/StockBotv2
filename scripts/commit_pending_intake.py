"""Publish applied Research Actions from a trusted local session."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp_server.action_publisher import publication_status, publish_pending_actions
from mcp_server.research_actions import cleanup_expired_actions


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Commit each applied Research Action with exact pathspecs, then push the "
            "fully explained batch once. This command is local-only."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root (defaults to this checkout)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--status", action="store_true", help="show pending action publication state"
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="run Git preflight and show the intended commits without mutation",
    )
    mode.add_argument(
        "--cleanup-expired",
        action="store_true",
        help="compact expired, never-applied action payloads without touching Git",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    if args.status:
        result = publication_status(root=root)
    elif args.cleanup_expired:
        result = cleanup_expired_actions(root=root)
    else:
        result = publish_pending_actions(root=root, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("status") in {
        "ok",
        "dry_run",
        "pushed",
        "nothing_to_push",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
