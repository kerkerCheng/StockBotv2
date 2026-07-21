"""Decision Lab 本機 CLI；公開 surface 只突出 assess 與 card。"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, TextIO

from .action_card import (
    RedactionError,
    assert_safe_payload,
    build_action_card,
    render_markdown,
)
from .execution import ExecutionError, assess_probe
from .store import DecisionStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m decision_lab",
        description="評估已凍結的 Signal context，或讀取 action-first Decision Card。",
    )
    parser.add_argument("--store", required=True, type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--private-root", required=True, type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--repo-root", required=True, type=Path, help=argparse.SUPPRESS)
    subcommands = parser.add_subparsers(dest="command", required=True)

    assess = subcommands.add_parser(
        "assess",
        help="依凍結 context 與 Coverage 產生決策，eligible 時原子建立 system paper。",
    )
    assess.add_argument("--input", default="-", help="JSON 檔；- 代表 stdin。")

    card = subcommands.add_parser(
        "card",
        help="純讀既有 decision 的 NO ACTION / REVIEW / TRADE / HEDGE 卡片。",
    )
    card.add_argument("decision_id")
    card.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser


def _read_json(source: str, stdin: TextIO) -> dict[str, Any]:
    text = stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    assert_safe_payload(value)
    return value


def _write_json(value: Any, stdout: TextIO) -> None:
    json.dump(
        value,
        stdout,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    stdout.write("\n")


def run(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    args = build_parser().parse_args(argv)
    store: DecisionStore | None = None
    try:
        store = DecisionStore.open(
            args.store,
            private_root=args.private_root,
            repo_root=args.repo_root,
        )
        if args.command == "assess":
            request = _read_json(args.input, stdin)
            required = {
                "context_digest",
                "coverage_assessment_id",
                "assessment",
                "idempotency_key",
                "effective_at",
            }
            if set(request) != required:
                raise ValueError("assess input fields do not match the public contract")
            bundle = store.get_context_bundle(str(request["context_digest"]))
            coverage = store.get_coverage_result(
                str(request["coverage_assessment_id"])
            )
            result = assess_probe(
                store,
                bundle,
                coverage,
                request["assessment"],
                idempotency_key=str(request["idempotency_key"]),
                effective_at=str(request["effective_at"]),
            )
            _write_json(asdict(result), stdout)
        else:
            card = build_action_card(store, args.decision_id)
            if args.format == "markdown":
                stdout.write(render_markdown(card) + "\n")
            else:
                _write_json(card, stdout)
        return 0
    except (
        ExecutionError,
        RedactionError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        code = (
            "SENSITIVE_INPUT_REJECTED"
            if isinstance(exc, RedactionError)
            else "NOT_FOUND"
            if isinstance(exc, KeyError)
            else "INVALID_REQUEST"
        )
        _write_json({"status": "error", "code": code}, stdout)
        return 2
    finally:
        if store is not None:
            store.close()


def main(argv: list[str] | None = None) -> int:
    return run(argv)
