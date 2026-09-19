"""Daily 本機 state 收尾：驗證四份 authority、釋放 writer lock、留下收工標記。

本腳本刻意沒有 Git、subprocess 或網路能力。Engine B state 留在固定本機路徑，
由 ``scripts/backup_private.py`` 納入 private backup；Daily Brief 的對外投遞另走既有
``publish_daily_brief.py``，兩者不混用。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine_b.state_files import StateFileError, validate_state_files  # noqa: E402
from engine_b.writer_lock import (  # noqa: E402
    LOCK_PATH,
    RUN_MARKER_PATH,
    SCHEDULED_OWNER,
    mark_run_finished,
    release,
)


def finalize_daily_state(
    root: Path | str = ROOT,
    *,
    owner: str = SCHEDULED_OWNER,
    lock_path: Path | None = None,
    marker_path: Path | None = None,
) -> dict[str, Any]:
    """完成本機 state lifecycle；驗證失敗也必須釋放自己的鎖。"""
    result: dict[str, Any]
    try:
        snapshots = validate_state_files(root)
        result = {"status": "finalized", "state_files": snapshots}
    except (StateFileError, OSError) as exc:
        result = {"status": "state_invalid", "error": str(exc), "state_files": []}
    finally:
        released = release(owner, path=lock_path or LOCK_PATH)
        marker = mark_run_finished(
            status=result["status"], owner=owner, path=marker_path or RUN_MARKER_PATH
        )
        result["writer_lock_released"] = released
        result["run_marker"] = marker
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args()
    owner = os.environ.get("STOCKBOT_WRITER_OWNER") or SCHEDULED_OWNER
    result = finalize_daily_state(owner=owner)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "finalized" else 1


if __name__ == "__main__":
    raise SystemExit(main())
