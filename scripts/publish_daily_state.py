"""安全發布本機 daily routine 的四個 tracked state files。

排程只准提交 pending leads、穩定 pq2 編號池、event watch registry 與假設對照；
不吃外部 path 參數、不碰使用者已 staged 的內容，也不會把其他未推送的 master
commits 一併推上去。

2026-09-02 pathset 由二擴四（sandbox impact review 同 change 完成）：daily 會更新
watch 喚醒／mark-checked 與假設對照，但先前只能留本機未提交，等互動 session 順手
commit——兩個 writer 的變更混在同一份 diff，正是 writer lock 要防的形狀在 Git 層
的殘留。擴充不新增命令、不新增 OS／網路能力（同一條 `.codex/rules` exact entry、
同目錄 tracked 檔案、同一組 git 動作）；guard 全部沿用（pathset 白名單、branch、
private-tracked、ahead-commit 檢查自動涵蓋新路徑）。契約斷言見
`tests/test_daily_state_publisher.py`。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
STATE_PATHS = (
    "library/leads/pending_leads.json",
    "library/leads/todo_pool.json",
    "library/leads/event_watches.json",
    "library/leads/hypotheses.json",
)
#: 追源證據的所在目錄。**不是 pathset 的一部分**——只有「被本次要發布的 leads
#: state 指名引用、且確實存在」的檔案才會被帶上（見 `_referenced_evidence`）。
EVIDENCE_PREFIX = "library/raw/"
#: 一輪最多帶幾份證據。daily 一輪只做少量追源；數字爆掉代表**發生了別的事**，
#: 這時 fail closed 比「照單全收」安全（L12：兩個修法方向都會壞時先分開再各自定規則）。
MAX_EVIDENCE_PER_RUN = 20

COMMIT_PREFIX = "chore(daily):"
# 本 publisher 提交時的**完整** subject。`writer_guard` 靠它辨認「這筆共用檔變更
# 是排程做的」——必須是完整字串而不是 prefix：互動 session 也會用 `chore(daily):`
# 這個房規慣例寫 pool sync，只比對 prefix 會把自己的 commit 判成排程（2026-08-31 實測）。
COMMIT_SUBJECT = f"{COMMIT_PREFIX} sync local approval state"


def _git(root: Path, *args: str, timeout: int = 30) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    return proc.returncode, (proc.stdout or "")


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _result(status: str, *, committed: bool = False, pushed: bool = False) -> dict[str, Any]:
    return {"status": status, "committed": committed, "pushed": pushed}


def _referenced_evidence(repo: Path) -> list[str]:
    """本次要發布的 leads state 指名引用、且確實存在的 `library/raw/` 檔案。

    ## 為什麼需要這個（2026-09-04 `audit invariants` 抓到的第一筆真實問題）

    daily 的 pq1 追源把原文寫進 `library/raw/`、把路徑寫進 lead 的
    `trace_attempts_ref`，但 publisher 的 pathset 只有四個 leads JSON。
    結果是**引用推上 origin、被引用的檔案留在本機**——實測 3 筆有 2 筆
    （`mu_8_k_20260826.txt`／`mu_4_20260825.txt`）已經永久消失。
    指標活著、被指的東西死了，而沒有任何東西會叫（INV-3：no silent drop）。

    ## 為什麼不是直接把 `library/raw/` 加進 pathset

    那會讓無人值守排程能提交**任何**下載到該目錄的東西，surface 大得多。
    這裡的集合是**從即將發布的 state 推導出來的**：只有 state 自己指名、
    路徑合法、確實存在的檔案才進來。state 沒提到的檔案一律留在本機。

    ⚠ 這**不能**用「重新下載補檔」來取代——那會產生一個 `retrieved_at` 是
    今天的檔案去冒充當時的追源嘗試，等於偽造 provenance（INV-6）。
    """
    leads_path = repo / "library" / "leads" / "pending_leads.json"
    if not leads_path.exists():
        return []
    try:
        payload = json.loads(leads_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            ref = node.strip().replace("\\", "/")
            if not ref.startswith(EVIDENCE_PREFIX) or len(ref.split()) != 1:
                return
            if ".." in ref or ref.endswith("/"):
                return          # 路徑穿越／目錄一律不收
            if (repo / ref).is_file():
                found.add(ref)

    walk(payload.get("leads") or {})
    return sorted(found)


def publish_daily_state(root: Path | str = ROOT) -> dict[str, Any]:
    """Commit/push exact daily state paths，任何邊界不符都 fail closed。"""
    repo = Path(root)

    code, branch = _git(repo, "branch", "--show-current")
    if code != 0 or branch.strip() != "master":
        return _result("guard_wrong_branch")

    code, private_paths = _git(repo, "ls-files", "library/private")
    if code != 0 or _lines(private_paths):
        return _result("guard_private_tracked")

    code, staged = _git(repo, "diff", "--cached", "--name-only")
    if code != 0 or _lines(staged):
        return _result("guard_staged_changes")

    code, head = _git(repo, "rev-parse", "HEAD")
    if code != 0:
        return _result("guard_git_state")
    code, upstream = _git(repo, "rev-parse", "origin/master")
    if code != 0:
        return _result("guard_missing_upstream")

    # 不把使用者先前尚未 push 的工作一併送出。唯一例外是上一輪本腳本已 commit
    # 但 push 失敗；那種 commit 必須只碰 STATE_PATHS，且 subject 帶固定 prefix。
    if head.strip() != upstream.strip():
        code, ahead_paths = _git(repo, "diff", "--name-only", "origin/master..HEAD")
        ahead = set(_lines(ahead_paths))
        # 上一輪可能同時帶了被引用的追源證據；那些也只能在 `library/raw/` 底下。
        if code != 0 or not all(
            path in STATE_PATHS or path.startswith(EVIDENCE_PREFIX) for path in ahead
        ):
            return _result("guard_unpushed_commits")
        code, subjects = _git(repo, "log", "--format=%s", "origin/master..HEAD")
        if code != 0 or not _lines(subjects) or any(
            not subject.startswith(COMMIT_PREFIX) for subject in _lines(subjects)
        ):
            return _result("guard_unpushed_commits")

    code, changed = _git(repo, "status", "--porcelain", "--", *STATE_PATHS)
    if code != 0:
        return _result("status_failed")

    committed = False
    # porcelain 的第一欄可能是空白（例如 `` M path``），不可先 strip。
    status_lines = [line.rstrip() for line in changed.splitlines() if line.strip()]
    expected = {line[3:].strip().replace("\\", "/") for line in status_lines}

    # 被 state 指名、且本身有未提交變更的追源證據，與 state 同一筆提交。
    # 分開提交會讓兩者之間存在一個「引用已推、檔案未推」的窗口——正是要防的形狀。
    evidence: list[str] = []
    if expected:
        referenced = _referenced_evidence(repo)
        if len(referenced) > MAX_EVIDENCE_PER_RUN:
            return _result("guard_evidence_volume")
        if referenced:
            code, dirty = _git(repo, "status", "--porcelain", "--", *referenced)
            if code != 0:
                return _result("status_failed")
            evidence = sorted(
                line.rstrip()[3:].strip().replace("\\", "/")
                for line in dirty.splitlines() if line.strip()
            )
        if not all(path.startswith(EVIDENCE_PREFIX) for path in evidence):
            return _result("guard_pathset")

    if expected:
        if not expected.issubset(set(STATE_PATHS)):
            return _result("guard_pathset")
        # 證據多半是**新檔**，而 `git commit -- <path>` 只吃 tracked 路徑
        # （untracked 會 `pathspec did not match`）。所以先 add——此時 index
        # 已由 `guard_staged_changes` 確認為空，加進去的只有這幾個檔。
        if evidence:
            code, _ = _git(repo, "add", "--", *evidence)
            if code != 0:
                return _result("evidence_stage_failed")
        code, _ = _git(
            repo,
            "commit",
            "-m",
            COMMIT_SUBJECT,
            "--",
            *STATE_PATHS,
            *evidence,
        )
        if code != 0:
            # 別把髒 index 留給下一輪——那會讓它撞 `guard_staged_changes`，
            # 而失敗原因看起來會變成完全不相干的另一件事（L12）。
            if evidence:
                _git(repo, "reset", "-q", "--", *evidence)
            return _result("commit_failed")
        committed = True

        code, committed_paths = _git(
            repo, "show", "--name-only", "--pretty=format:", "HEAD"
        )
        if code != 0 or set(_lines(committed_paths)) != expected | set(evidence):
            return _result("guard_commit_pathset", committed=True)

    # 即使本輪沒新變更，仍可補推上一輪由本腳本留下的安全 commit。
    code, head = _git(repo, "rev-parse", "HEAD")
    code2, upstream = _git(repo, "rev-parse", "origin/master")
    if code != 0 or code2 != 0:
        return _result("guard_git_state", committed=committed)
    if head.strip() == upstream.strip():
        return _result("no_change", committed=committed, pushed=False)

    code, _ = _git(repo, "push", "origin", "master", timeout=60)
    if code != 0:
        return _result("push_failed", committed=committed)
    return _result("pushed", committed=committed, pushed=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="發布本機 daily routine 的窄 state pathset")
    parser.parse_args()
    result = publish_daily_state()
    # Writer lock 收尾（ROADMAP #2）：publisher 是 daily 的最後一個共用檔寫入者，
    # 無論 publish 成敗都釋放——失敗的輪次不該繼續佔鎖到 TTL。owner 不符時
    # release 是 no-op（不拆別人的鎖）。
    try:
        sys.path.insert(0, str(ROOT))
        from engine_b.writer_lock import SCHEDULED_OWNER, release

        result["writer_lock_released"] = release(
            os.environ.get("STOCKBOT_WRITER_OWNER") or SCHEDULED_OWNER
        )
    except Exception:
        result["writer_lock_released"] = None
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"no_change", "pushed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
