"""Generate thin Claude Code and Codex adapters for canonical repo skills."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = REPO_ROOT / "skills"
ADAPTER_ROOTS = (
    REPO_ROOT / ".agents" / "skills",
    REPO_ROOT / ".claude" / "skills",
)


def _metadata_lines(skill_text: str, source: Path) -> list[str]:
    """Return only the cross-platform name/description YAML lines."""
    lines = skill_text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{source}: missing opening YAML delimiter")

    try:
        closing = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError(f"{source}: missing closing YAML delimiter") from exc

    frontmatter = lines[1:closing]
    try:
        name_index = next(i for i, line in enumerate(frontmatter) if line.startswith("name:"))
        description_index = next(
            i for i, line in enumerate(frontmatter) if line.startswith("description:")
        )
    except StopIteration as exc:
        raise ValueError(f"{source}: frontmatter requires name and description") from exc

    description_end = len(frontmatter)
    for index in range(description_index + 1, len(frontmatter)):
        line = frontmatter[index]
        if line and not line[0].isspace() and ":" in line:
            description_end = index
            break

    return [
        frontmatter[name_index],
        *frontmatter[description_index:description_end],
    ]


def _adapter_text(skill_dir: Path) -> str:
    canonical = skill_dir / "SKILL.md"
    metadata = _metadata_lines(canonical.read_text(encoding="utf-8"), canonical)
    relative = f"../../../skills/{skill_dir.name}/SKILL.md"
    return "\n".join(
        [
            "---",
            *metadata,
            "---",
            "",
            "# Generated cross-agent adapter",
            "",
            f"Read `{relative}` completely, then follow it as the authoritative skill.",
            "Resolve its relative references from the canonical skill directory.",
            "Do not add workflow rules here; edit the canonical skill and rerun",
            "`python scripts/sync_agent_skills.py`.",
            "",
        ]
    )


def expected_adapters() -> dict[Path, str]:
    canonical_dirs = sorted(
        path for path in CANONICAL_ROOT.iterdir() if (path / "SKILL.md").is_file()
    )
    return {
        root / skill_dir.name / "SKILL.md": _adapter_text(skill_dir)
        for root in ADAPTER_ROOTS
        for skill_dir in canonical_dirs
    }


def check() -> int:
    stale = [
        path
        for path, expected in expected_adapters().items()
        if not path.is_file() or path.read_text(encoding="utf-8") != expected
    ]
    if stale:
        print("Agent skill adapters are missing or stale:")
        for path in stale:
            print(f"- {path.relative_to(REPO_ROOT)}")
        print("Run: python scripts/sync_agent_skills.py")
        return 1
    print("Agent skill adapters are in sync.")
    return 0


def sync() -> int:
    updated = []
    for path, expected in expected_adapters().items():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == expected:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8", newline="\n")
        updated.append(path.relative_to(REPO_ROOT))

    if updated:
        print("Updated agent skill adapters:")
        for path in updated:
            print(f"- {path}")
    else:
        print("Agent skill adapters already in sync.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when a generated adapter is missing or stale.",
    )
    args = parser.parse_args()
    try:
        return check() if args.check else sync()
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
