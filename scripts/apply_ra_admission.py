"""`python scripts/apply_ra_admission.py --pq2 N --digest <sha256>`——套用一個**已在對話中明確核准**的 pq2 `ra_admission`。

## 為什麼需要它（2026-10-01 Phase 4 Step 4.2d；ROADMAP 旁支「本機 Research Action apply 入口」）

遠端入口退役後，graph admission gate 的最後一步只剩「在對話裡呼叫私有函式
`intake.application._apply_research_action_impl`」——prepare（`scripts/prepare_research_action.py`）與 publish
（`scripts/commit_pending_intake.py`）都有固定入口，唯獨 apply 沒有，所以沒有地方掛檢查與收據。

## 它檢查什麼、不做什麼

**授權載體仍是對話中的明確核准**（AGENTS「授權介面唯一：pq2 編號＋go」；使用者主動指示＝已授權）。本入口
**不授權任何東西**，只在套用前做四道 fail closed，通過才蓋戳記、再 apply：

1. pq2 編號存在、型別是 `ra_admission`、**尚未結案**（drop 的編號永久拒絕——要重提請重跑 prepare 取新編號）；
2. 那個編號的 `ref_id` 就是一筆存在的 Research Action；
3. `--digest` 等於那筆紀錄凍結的 `action_digest`（使用者核准的就是這一份）；
4. 紀錄 `ready` 且未過期——或同一個編號、同一個 digest 先前已蓋過戳記、apply 中斷在 `partial`／`applying`（重試）。

通過後先把 `approval={pq2_n, digest, at}` 寫進紀錄的 `execution`，再呼叫 apply。**不 publish、不 resolve**：
publish 走 `scripts/commit_pending_intake.py`，結案走 `python -m engine_b.todo complete-ra <N> --digest …`
（它會比對 `approval.pq2_n`——沒經過本入口的 apply 結不了案）。

⚠ **互動專用，不進任何無人值守 allowlist**（sandbox impact review 見 `docs/OPERATIONS.md`「Research Action apply 入口」）。

結束碼：0＝已 apply；2＝四道檢查沒過（**沒有任何寫入**）；3＝已蓋戳記但 apply 沒有完成（看輸出的 next_action）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXIT_OK, EXIT_REFUSED, EXIT_NOT_APPLIED = 0, 2, 3
_RETRY_STATES = frozenset({"partial", "applying"})


class ApplyRefused(RuntimeError):
    """四道檢查沒過——沒有任何寫入。"""


def check_and_stamp(n: int, digest: str, *, pool_path: Path, root: Path, now: datetime | None = None) -> dict:
    """四道檢查＋蓋核准戳記。回 `{action_id, record, retry}`；不過就 raise ApplyRefused（此時沒有任何寫入）。"""

    from engine_b import todo
    from intake import actions as research_actions

    current = now or datetime.now(timezone.utc)
    digest = str(digest or "").strip().lower()
    try:
        research_actions.validate_action_digest(digest)
    except ValueError as exc:
        raise ApplyRefused(f"--digest 必須是完整 64 位小寫 sha256：{exc}") from exc
    pool = todo.load(pool_path)
    try:
        item = todo.get(pool, n)
    except todo.TodoError as exc:
        raise ApplyRefused(f"[{n}] 不存在或已結案（drop 的編號永久拒絕；要重提請重跑 prepare 取新編號）") from exc
    if item.get("type") != "ra_admission":
        raise ApplyRefused(f"[{n}] 的型別是 {item.get('type')}，不是 ra_admission——本入口只套用入圖核准")
    action_id = str(item.get("ref_id") or "")
    try:
        research_actions.validate_action_id(action_id)
        record = research_actions.read_action(action_id, root=root)
    except FileNotFoundError as exc:
        raise ApplyRefused(f"[{n}] 指的 Research Action {action_id} 不存在") from exc
    except (OSError, ValueError) as exc:
        raise ApplyRefused(f"[{n}] 指的 Research Action {action_id} 讀不出來或不合法：{exc}") from exc
    if record["action_digest"] != digest:
        raise ApplyRefused(f"[{n}] 的 digest 不符凍結內容（你核准的不是這一份）——沒有任何寫入")

    approval = (record.get("execution") or {}).get("approval")
    if approval and (approval.get("pq2_n") != n or approval.get("digest") != digest):
        raise ApplyRefused(f"{action_id} 已由 [{approval.get('pq2_n')}] 蓋過核准戳記——同一筆紀錄不能被兩個編號核准")
    expired = record["state"] == "ready" and current >= research_actions._parse_time(record["expires_at"])
    if record["state"] == "expired" or expired:
        raise ApplyRefused(f"{action_id} 已過期——重提請重跑 prepare（新 digest、新編號）")
    retry = record["state"] in _RETRY_STATES and bool(approval)
    if record["state"] in _RETRY_STATES and not approval:
        # 舊紀錄（入口上線前中斷的 apply）沒有任何戳記——沒有哪個編號能「沿用原核准重試」（R2-a N5）。
        raise ApplyRefused(f"{action_id} 的狀態是 {record['state']}，但沒有核准戳記（入口上線前中斷的 apply）——"
                           "沒有任何編號能重試它；重提請重跑 prepare（新 digest、新編號）")
    if record["state"] != "ready" and not retry:
        raise ApplyRefused(f"{action_id} 的狀態是 {record['state']}，不是 ready——已 apply 的請走 "
                           "commit_pending_intake.py／todo complete-ra；中斷的 apply 只能由原核准編號重試")

    if not approval:
        with research_actions.action_lock(action_id, root=root):
            record = research_actions.read_action(action_id, root=root)    # 鎖內重讀，避免蓋到別人剛改的版本
            if record["action_digest"] != digest or record["state"] != "ready":
                raise ApplyRefused(f"{action_id} 在檢查與蓋章之間被改動了——沒有任何寫入，請重跑")
            # 鎖內也要重查戳記（R2-a N2）：兩個未結的編號指向同一筆紀錄、同時執行時，後到的不得覆蓋先到的戳記。
            stamped_by = (record.get("execution") or {}).get("approval")
            if stamped_by:
                raise ApplyRefused(f"{action_id} 在檢查與蓋章之間已由 [{stamped_by.get('pq2_n')}] 蓋過核准戳記——"
                                   "同一筆紀錄不能被兩個編號核准；沒有任何寫入")
            record["execution"]["approval"] = {"pq2_n": int(n), "digest": digest, "at": current.isoformat()}
            record = research_actions.save_action(record, root=root, now=current)
    return {"action_id": action_id, "record": record, "retry": retry}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="套用一個已在對話中明確核准的 pq2 ra_admission（四道檢查、先蓋戳記再 apply；不 publish、不結案）")
    parser.add_argument("--pq2", type=int, required=True, help="pq2 編號（型別必須是 ra_admission、尚未結案）")
    parser.add_argument("--digest", required=True, help="使用者核准的那一份的完整 action_digest")
    parser.add_argument("--pool", default=None, help="（測試用）待辦池路徑；預設 library/leads/todo_pool.json")
    parser.add_argument("--root", default=None, help="（測試用）repo 根目錄；預設本 repo")
    args = parser.parse_args(argv)

    from engine_b.todo import DEFAULT_POOL_PATH
    from intake.application import _apply_research_action_impl

    root = Path(args.root) if args.root else ROOT
    pool_path = Path(args.pool) if args.pool else DEFAULT_POOL_PATH
    try:
        stamped = check_and_stamp(args.pq2, args.digest, pool_path=pool_path, root=root)
    except ApplyRefused as exc:
        print(f"✗ 拒絕：{exc}", file=sys.stderr)
        return EXIT_REFUSED
    print(f"✓ [{args.pq2}] → {stamped['action_id']}：四道檢查通過，核准戳記已寫入"
          f"{'（重試：沿用原戳記）' if stamped['retry'] else ''}；開始 apply", file=sys.stderr)
    result = _apply_research_action_impl(stamped["action_id"], args.digest.strip().lower(), root=root)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if result.get("status") == "applied" or result.get("state") == "applied":
        print("下一步：python scripts/commit_pending_intake.py（publish）→ "
              f"python -m engine_b.todo complete-ra {args.pq2} --digest <同一個 digest>（結案）", file=sys.stderr)
        return EXIT_OK
    return EXIT_NOT_APPLIED


if __name__ == "__main__":
    raise SystemExit(main())
