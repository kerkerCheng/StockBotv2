"""`python -m alpha` 的入口。Phase 1 只有 audit 子命令；`research` 在 Phase 2。"""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:2] == ["audit", "invariants"]:
        from .audit import main as audit_main
        return audit_main(args[2:])
    print(
        "用法：\n"
        "  python -m alpha audit invariants     # runtime invariant audit\n"
        "  python -m alpha research <TICKER>    # Phase 2 才有",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
