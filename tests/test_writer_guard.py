"""互動 session 對本機排程的單向避讓。

事發（2026-08-31）：`AGENTS.md` 早就寫著「排程與互動 session 也算兩個 writer，
不能重疊」，但 06:30 只存在於散文與 OS 排程器設定裡——程式看不到，所以程式不可能
自己避開。repo 內 `filelock`／`flock`／pidfile 全部 0 命中。兩側寫同一組 authority 檔，
重疊時最危險的是**靜默的 lost update**，不是報錯。

驗收條件寫成「時間窗算得對、且跨窗的長 run 會被擋下」，不是「函式回得出一個 bool」——
後者在修好之前就已經成立。
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts import writer_guard

TPE = ZoneInfo("Asia/Taipei")
SCHEDULE = {
    "timezone": "Asia/Taipei",
    "daily_local_time": "06:30",
    "expected_duration_minutes": 60,
    "guard_margin_minutes": 15,
}


def test_window_covers_margin_before_and_duration_after() -> None:
    now = datetime(2026, 8, 31, 12, 0, tzinfo=TPE)
    start, end = writer_guard._window(SCHEDULE, now)

    assert (start.hour, start.minute) == (6, 15), "起點＝觸發時間減 margin"
    assert (end.hour, end.minute) == (7, 45), "終點＝觸發＋預期時長＋margin"


def test_real_config_declares_a_schedule_window() -> None:
    """時間窗必須留在 config，不得回到只寫在散文裡的狀態。"""
    schedule = writer_guard._load_schedule()

    for key in (
        "timezone",
        "daily_local_time",
        "expected_duration_minutes",
        "guard_margin_minutes",
    ):
        assert key in schedule, key
    start, end = writer_guard._window(schedule, datetime.now(ZoneInfo(schedule["timezone"])))
    assert start < end


def test_shared_paths_cover_every_file_both_writers_touch() -> None:
    """漏一個檔就等於那個檔沒有保護——而漏掉不會有任何東西叫。"""
    assert set(writer_guard.SHARED_PATHS) == {
        "library/leads/pending_leads.json",
        "library/leads/todo_pool.json",
        "library/leads/event_watches.json",
    }


def test_check_reports_unsafe_when_the_run_would_cross_the_window(capsys, monkeypatch) -> None:
    """起跑時安全不代表跑到一半安全——跑到一半撞上最難收拾，所以要先算。"""

    # 22:00 起跑、跑 600 分鐘 → 隔天 08:00，會穿過 06:15 的窗。
    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return datetime(2026, 8, 31, 22, 0, tzinfo=TPE)

    monkeypatch.setattr(writer_guard, "datetime", _FixedDatetime)
    monkeypatch.setattr(writer_guard, "_git", lambda *a: "")  # 乾淨的 tree，隔離變因

    code = writer_guard.main(["check", "--minutes", "600"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["safe"] is False
    assert any("跨進" in reason for reason in payload["reasons"])


def test_check_is_safe_for_a_short_run_far_from_the_window(capsys, monkeypatch) -> None:
    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return datetime(2026, 8, 31, 14, 0, tzinfo=TPE)

    monkeypatch.setattr(writer_guard, "datetime", _FixedDatetime)
    monkeypatch.setattr(writer_guard, "_git", lambda *a: "")
    # ⚠ 也要隔離**真實鎖檔**。第一版只 monkeypatch 了 `_git`，於是這條測試會在
    # 「排程正在跑（或留下孤兒鎖）」時失敗——2026-09-04 實測踩到：daily 06:32
    # 取鎖後中途結束，鎖未釋放，測試就紅了。
    # 那是環境狀態，不是被測邏輯；讀真實狀態的測試會在最不該紅的時候紅。
    monkeypatch.setattr(writer_guard, "_lock_holder", lambda: None)

    code = writer_guard.main(["check", "--minutes", "60"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["safe"] is True
    assert payload["reasons"] == []


def test_check_refuses_when_the_working_tree_is_dirty(capsys, monkeypatch) -> None:
    """不乾淨的 tree 代表可能有另一個 writer 在跑，或上一輪沒收乾淨——兩者都不該疊上去。"""

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return datetime(2026, 8, 31, 14, 0, tzinfo=TPE)

    monkeypatch.setattr(writer_guard, "datetime", _FixedDatetime)
    monkeypatch.setattr(
        writer_guard, "_git", lambda *a: " M library/leads/todo_pool.json"
    )

    code = writer_guard.main(["check", "--minutes", "60"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert any("working tree" in reason for reason in payload["reasons"])


def test_verify_flags_scheduled_publisher_commits(capsys, monkeypatch) -> None:
    """期間出現排程側的 state commit＝我手上的狀態已過期，必須重讀而不是續寫。"""

    def fake_git(*args: str) -> str:
        if args[:2] == ("rev-parse", "HEAD"):
            return "newhead"
        if args[0] == "log":
            return "abc1234\x1fchore(daily): sync local approval state"
        return ""

    monkeypatch.setattr(writer_guard, "_git", fake_git)

    code = writer_guard.main(["verify", "--since", "oldhead"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["clean"] is False
    assert payload["foreign_commits"] == ["abc1234 chore(daily): sync local approval state"]


def test_verify_ignores_our_own_commits(capsys, monkeypatch) -> None:
    """HEAD 前進不等於別人動過——互動 session 自己的 commit 不算 foreign。"""

    def fake_git(*args: str) -> str:
        if args[:2] == ("rev-parse", "HEAD"):
            return "newhead"
        if args[0] == "log":
            return "def5678\x1fresearch(pq1): 產出入圖包"
        return ""

    monkeypatch.setattr(writer_guard, "_git", fake_git)

    code = writer_guard.main(["verify", "--since", "oldhead"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["clean"] is True
    assert payload["head_moved"] is True


def test_verify_does_not_flag_interactive_commits_using_the_house_convention(
    capsys, monkeypatch
) -> None:
    """互動 session 也用 `chore(daily):` 寫 pool sync——只比 prefix 會把自己判成排程。

    事發（2026-08-31，guard 上線當天）：互動 session 提交
    "chore(daily): sync pool after [230] 結案；…"，`verify` 立刻回報偵測到排程 writer。
    這是 L12 的形狀——一個訊號（commit subject 前綴）承載兩種語意（排程 publisher／
    互動 session 沿用房規慣例）。**會誤報的 guard 一週內就會被忽略，那比沒有 guard 更糟。**

    修法是比對 publisher 的完整 subject 常數，而且從 publisher 匯入而非各寫一份。
    """
    from scripts.publish_daily_state import COMMIT_SUBJECT

    def fake_git(*args: str) -> str:
        if args[:2] == ("rev-parse", "HEAD"):
            return "newhead"
        if args[0] == "log":
            return (
                "cb3788b\x1fchore(daily): sync pool after [230] 結案；[342] 為 [230] 留下的缺口"
            )
        return ""

    monkeypatch.setattr(writer_guard, "_git", fake_git)

    code = writer_guard.main(["verify", "--since", "oldhead"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0, "互動 session 自己的 pool sync 不得被判成排程"
    assert payload["foreign_commits"] == []
    # 而真正的 publisher subject 仍必須被抓到——否則就是把 guard 關掉了
    assert writer_guard._PUBLISHER_SUBJECT == COMMIT_SUBJECT


def test_verify_still_catches_the_exact_publisher_subject(capsys, monkeypatch) -> None:
    from scripts.publish_daily_state import COMMIT_SUBJECT

    def fake_git(*args: str) -> str:
        if args[:2] == ("rev-parse", "HEAD"):
            return "newhead"
        if args[0] == "log":
            return f"abc1234\x1f{COMMIT_SUBJECT}"
        return ""

    monkeypatch.setattr(writer_guard, "_git", fake_git)

    code = writer_guard.main(["verify", "--since", "oldhead"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["foreign_commits"] == [f"abc1234 {COMMIT_SUBJECT}"]


# ---------------------------------------------------------------------------
# 「今天那輪 daily 已經收工」（2026-09-12）
#
# 事發：使用者把 daily 改到 05:30，但 config 還是 06:30，於是窗避讓 06:15–07:45——
# **兩個方向都錯**：05:15–06:15 daily 真的在跑卻回 safe，06:45–07:45 daily 早就收工
# 卻擋住互動 session 約 1.5 小時。時間改掉只解決當下這一次；窗是純時鐘算術，
# 它結構上回答不了「跑完了沒」，所以延遲開跑或手動重跑時同樣的錯會再來一次。
#
# 這四條是**放寬一道 gate 時的收緊面**（`AGENTS.md`：放行與收緊必須同時發生）。
# 驗收寫成「窗內的判定真的翻轉了，而三個不該翻的情境沒有翻」，不是「函式回得出 bool」。


def _at(moment: datetime, monkeypatch, *, marker: datetime | None) -> None:
    """把時點、標記與環境固定下來；呼叫端接著自己跑 `main(["check", ...])`。

    ⚠ 真實鎖檔與 working tree 都要隔離——讀真實狀態的測試會在最不該紅的時候紅
    （2026-09-04 已踩過一次）。"""

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return moment

    monkeypatch.setattr(writer_guard, "datetime", _FixedDatetime)
    monkeypatch.setattr(writer_guard, "_git", lambda *a: "")
    monkeypatch.setattr(writer_guard, "_lock_holder", lambda: None)
    monkeypatch.setattr(writer_guard, "_load_schedule", lambda: dict(SCHEDULE))
    monkeypatch.setattr(writer_guard, "_daily_run_finished_at", lambda: marker)


def test_window_still_blocks_when_today_has_no_finish_marker(capsys, monkeypatch) -> None:
    """沒有標記＝fail closed。讀不到就當成還沒跑完，窗照常成立。"""
    _at(datetime(2026, 9, 12, 7, 0, tzinfo=TPE), monkeypatch, marker=None)
    code = writer_guard.main(["check", "--minutes", "10"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["daily_done_today"] is False
    assert any("避讓窗" in reason for reason in payload["reasons"])


def test_window_clears_once_today_s_daily_has_finished(capsys, monkeypatch) -> None:
    """這一條就是修好的證據：同一個時點、同一個窗，判定從擋下翻成放行。"""
    _at(
        datetime(2026, 9, 12, 7, 0, tzinfo=TPE),
        monkeypatch,
        marker=datetime(2026, 9, 12, 6, 52, tzinfo=TPE),
    )
    code = writer_guard.main(["check", "--minutes", "10"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0, payload["reasons"]
    assert payload["daily_done_today"] is True
    assert payload["reasons"] == []


def test_yesterday_s_marker_does_not_open_today_s_window(capsys, monkeypatch) -> None:
    """昨天的標記開不了今天的門——否則它只需要被寫對一次，就永遠開著。"""
    _at(
        datetime(2026, 9, 12, 7, 0, tzinfo=TPE),
        monkeypatch,
        marker=datetime(2026, 9, 11, 6, 52, tzinfo=TPE),
    )
    code = writer_guard.main(["check", "--minutes", "10"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["daily_done_today"] is False
    assert any("不算今天這輪" in reason for reason in payload["reasons"])


def test_marker_from_before_the_window_does_not_open_it(capsys, monkeypatch) -> None:
    """凌晨手動跑一次留下的標記，不能拿來開 06:15 才開始的窗——那時 daily 還沒跑。"""
    _at(
        datetime(2026, 9, 12, 7, 0, tzinfo=TPE),
        monkeypatch,
        marker=datetime(2026, 9, 12, 3, 10, tzinfo=TPE),
    )
    code = writer_guard.main(["check", "--minutes", "10"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["daily_done_today"] is False


def test_scheduled_lock_still_blocks_even_with_a_valid_marker(capsys, monkeypatch) -> None:
    """補償控制：標記只放行時間窗那一條理由。daily 延遲重跑時由鎖擋下，標記不得介入。"""

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return datetime(2026, 9, 12, 7, 0, tzinfo=TPE)

    monkeypatch.setattr(writer_guard, "datetime", _FixedDatetime)
    monkeypatch.setattr(writer_guard, "_git", lambda *a: "")
    monkeypatch.setattr(writer_guard, "_load_schedule", lambda: dict(SCHEDULE))
    monkeypatch.setattr(
        writer_guard,
        "_daily_run_finished_at",
        lambda: datetime(2026, 9, 12, 6, 52, tzinfo=TPE),
    )
    monkeypatch.setattr(
        writer_guard,
        "_lock_holder",
        lambda: {"owner": "scheduled", "purpose": "daily", "expires_at": "2999-01-01T00:00:00+00:00"},
    )

    code = writer_guard.main(["check", "--minutes", "10"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["daily_done_today"] is True, "標記本身有效"
    assert any("writer lock" in reason for reason in payload["reasons"]), "但鎖仍然獨立擋下"
