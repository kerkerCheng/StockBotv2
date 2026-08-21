"""把 workspace 內的 research-action draft 凍結到 private staging。

這是 Daily pq1 的窄 CLI：只接受 ``library/leads/action_drafts/*.json``，
重跑既有 server-side validation 並建立待人工 graph admission 的 immutable action。
它不 apply、不寫 Neo4j、不建立 Decision 或 live permission。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parent.parent
MAX_ACTION_BYTES = 2 * 1024 * 1024
sys.path.insert(0, str(ROOT))


def _resolve_draft(action_file: Path, *, root: Path) -> Path:
    draft_root = (root / "library" / "leads" / "action_drafts").resolve()
    candidate = action_file if action_file.is_absolute() else root / action_file
    resolved = candidate.resolve()
    try:
        resolved.relative_to(draft_root)
    except ValueError as exc:
        raise ValueError(
            "action draft 必須位於 library/leads/action_drafts/"
        ) from exc
    if resolved.suffix.lower() != ".json":
        raise ValueError("action draft 必須是 .json")
    if not resolved.is_file():
        raise ValueError("action draft 不存在或不是檔案")
    if resolved.stat().st_size > MAX_ACTION_BYTES:
        raise ValueError("action draft 超過 2 MiB 上限")
    return resolved


def prepare_from_file(
    action_file: Path,
    *,
    root: Path = ROOT,
    prepare: Callable[..., dict] | None = None,
) -> dict:
    path = _resolve_draft(action_file, root=root)
    action_json = path.read_text(encoding="utf-8")
    payload = json.loads(action_json)
    if not isinstance(payload, dict):
        raise ValueError("action draft 頂層必須是 JSON object")
    if prepare is None:
        from mcp_server.graph_mcp import _prepare_research_action_impl

        prepare = _prepare_research_action_impl
    return prepare(action_json, root=root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action-file", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = prepare_from_file(args.action_file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"status": "rejected", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
    return 0 if result.get("status") == "ready" else 2


if __name__ == "__main__":
    sys.exit(main())
