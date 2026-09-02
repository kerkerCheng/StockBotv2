"""同一 working tree 的 session 級 advisory writer lock（2026-09-02 ROADMAP #2）。

`AGENTS.md`：「排程與互動 session 也算兩個 writer，不能重疊。」2026-08-31 的
`writer_guard` 只做到**單向避讓**——互動側查排程的時間窗讓開；排程側 0 檢查，
且時間窗對「延遲開跑」失明（實測 2026-08-29 排程 08:21 才跑完 publisher，
06:15–07:45 的避讓窗整個落空）。

本模組把避讓升級為**雙向 advisory lock**：

- 鎖檔 `library/leads/.writer_lock.json`（gitignored；與被保護的共用檔同目錄）。
- **排程側**嵌在既有入口內：`crons/harvest_leads.py` 開跑 acquire(`scheduled`)、
  `scripts/publish_daily_state.py` 收尾 release——**不新增 CLI 命令、不動
  `.codex/rules` 的 16 條 allowlist**（sandbox impact review 結論：鎖檔是 repo 內
  一般檔案，workspace-write 已涵蓋，無 identity／ACL／網路／credential 副作用）。
- **互動側**走 `scripts/writer_guard.py acquire／release`；`check` 同時看時間窗
  與本鎖——鎖補上時間窗防不了的延遲開跑，時間窗補上「排程要跑但還沒 acquire」
  的前置幾分鐘。
- **stale-tolerant**：鎖帶 TTL（`expires_at`）；過期或檔案損毀視同 stale，
  下一個 acquire 直接接手並在新鎖上記下 `superseded`——崩潰的 session 最多
  卡住別人一個 TTL，不會永久鎖死。

⚠ 這是 advisory 不是 mandatory：同 owner 的多個 CLI 行程（daily 的十幾個命令、
互動 session 的多次工具呼叫）無法逐行程歸屬，enforcement 落在 session 邊界
（acquire 撞到未過期的外人鎖＝fail closed），不落在每次 save()。
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = _ROOT / "library" / "leads" / ".writer_lock.json"

# 量測依據（2026-09-02，23 個正常日的 git publisher commit）：daily 全程中位數
# 約 19 分、p90 約 30 分、最長 43 分。TTL 取 90 分＝最長實測的兩倍餘裕——
# 夠寬到正常 run 絕不會被接手，夠窄到崩潰後不會把互動 session 卡掉半天。
DEFAULT_TTL_MINUTES = 90.0

SCHEDULED_OWNER = "scheduled"
INTERACTIVE_OWNER = "interactive"


class WriterLockHeld(RuntimeError):
    """另一個 owner 持有未過期的鎖。attribute `holder` 是對方的鎖內容。"""

    def __init__(self, holder: dict[str, Any]):
        self.holder = holder
        super().__init__(
            f"writer lock 由 {holder.get('owner')!r} 持有中"
            f"（purpose={holder.get('purpose')!r}，expires_at={holder.get('expires_at')}）"
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def holder(path: Path | None = None) -> dict[str, Any] | None:
    """目前鎖內容；None＝沒有鎖。損毀的鎖檔回 `{"invalid": True}` 現形（L12：
    「沒有鎖」與「鎖檔壞掉」不是同一件事），但兩者對 acquire 都算可接手。"""
    p = path or LOCK_PATH
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not data.get("owner"):
            raise ValueError("lock 格式非法")
        return data
    except (OSError, ValueError):
        return {"invalid": True}


def is_stale(lock: dict[str, Any] | None, *, now: datetime | None = None) -> bool:
    """過期或損毀＝stale。expires_at 解析不了也算 stale——一個讀不出到期日的鎖
    等於永久鎖，而永久鎖正是本模組要防的形狀。"""
    if lock is None:
        return True
    if lock.get("invalid"):
        return True
    try:
        expires = datetime.fromisoformat(str(lock["expires_at"]))
    except (KeyError, ValueError, TypeError):
        return True
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return (now or _now()) >= expires


def _write_lock(payload: dict[str, Any], path: Path) -> None:
    """atomic 寫檔（tempfile + os.replace），沿用 repo 慣例。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        prefix=f".{path.name}.", suffix=".tmp", delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def acquire(
    owner: str,
    *,
    ttl_minutes: float = DEFAULT_TTL_MINUTES,
    purpose: str = "",
    path: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """取得（或續期）advisory lock。

    - 無鎖／stale 鎖 → 接手，stale 的舊 owner 記進 `superseded`；
    - 同 owner 的未過期鎖 → 續期（renew），同 session 重複 acquire 是正常操作；
    - 異 owner 的未過期鎖 → raise WriterLockHeld（fail closed，呼叫端決定
      是等待、放棄還是回報結構化 failure）。
    """
    if not owner:
        raise ValueError("owner 不可為空")
    p = path or LOCK_PATH
    current = holder(p)
    moment = now or _now()
    superseded = None
    if current is not None and not is_stale(current, now=moment):
        if current.get("owner") != owner:
            raise WriterLockHeld(current)
    elif current is not None:
        superseded = {
            "owner": current.get("owner"),
            "expires_at": current.get("expires_at"),
            "invalid": bool(current.get("invalid")),
        }
    payload: dict[str, Any] = {
        "owner": owner,
        "purpose": purpose,
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "acquired_at": moment.isoformat(),
        "expires_at": (moment + timedelta(minutes=float(ttl_minutes))).isoformat(),
    }
    if superseded:
        payload["superseded"] = superseded
    _write_lock(payload, p)
    return payload


def release(owner: str, *, path: Path | None = None) -> bool:
    """釋放自己的鎖。回傳 True＝有釋放；無鎖／已是別人的鎖 → False（不搶拆——
    拆別人的鎖等於把 mutual exclusion 靜默關掉）。stale／損毀鎖任何人可清。"""
    p = path or LOCK_PATH
    current = holder(p)
    if current is None:
        return False
    if current.get("owner") != owner and not is_stale(current):
        return False
    p.unlink(missing_ok=True)
    return True
