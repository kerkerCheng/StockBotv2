"""候選狀態每日序列（Phase 5 Step 5.6；plan §7）：`materialize --candidates` 寫完 artifact 後 append 一行。

守的是：同日重跑只留最後一筆、跨日各一行、壞行不吞掉整檔（而且原樣留著）、試跑碰不到真實序列、
寫失敗不讓候選板消失、計數照抄 artifact（`held` 讀不到是 null 不是 0）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from webapp import materialize as mat
from webapp.store import DEFAULT_STATE_DIR, StateArtifactStore

from test_webapp_candidates import fake_candidates_payload


def _payload(today: str, *, hour: int = 5, held=0, open_n: int = 0):
    payload = fake_candidates_payload()
    payload = dict(payload, today=today, generated_at=datetime(2026, 10, 2, hour, tzinfo=timezone.utc).isoformat())
    payload["counts"] = dict(payload["counts"], held=held, open=open_n)
    return payload


def _lines(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_same_day_reruns_keep_only_the_last_row(tmp_path) -> None:
    path = tmp_path / "series.jsonl"
    mat.append_candidate_series(_payload("2026-10-02", hour=5, open_n=0), path=path)
    report = mat.append_candidate_series(_payload("2026-10-02", hour=9, open_n=1), path=path)
    rows = [json.loads(line) for line in _lines(path)]
    assert len(rows) == 1 and report["replaced_same_day"] == 1
    assert rows[0]["counts"]["open"] == 1 and rows[0]["generated_at"].startswith("2026-10-02T09")


def test_each_day_gets_its_own_row(tmp_path) -> None:
    path = tmp_path / "series.jsonl"
    mat.append_candidate_series(_payload("2026-10-02"), path=path)
    mat.append_candidate_series(_payload("2026-10-03"), path=path)
    assert [json.loads(line)["date"] for line in _lines(path)] == ["2026-10-02", "2026-10-03"]


def test_a_bad_line_is_kept_verbatim_and_does_not_swallow_the_file(tmp_path) -> None:
    """壞行原樣留著（這份序列拿不回來，L10）；它前後的好行也都在。"""
    path = tmp_path / "series.jsonl"
    mat.append_candidate_series(_payload("2026-10-01"), path=path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"date": "2026-10-0\n')                          # 寫到一半的殘骸
    report = mat.append_candidate_series(_payload("2026-10-02"), path=path)
    lines = _lines(path)
    assert report["bad_lines_kept"] == 1 and len(lines) == 3
    assert lines[1] == '{"date": "2026-10-0'
    assert [json.loads(lines[i])["date"] for i in (0, 2)] == ["2026-10-01", "2026-10-02"]


def test_row_copies_the_artifact_counts_and_keeps_an_absent_held_as_null(tmp_path) -> None:
    """照抄 artifact 的 `counts`：五組＋四附組＋無敘事；持股讀不到時 `held` 是 None——序列裡是 null，不是 0。"""
    row = mat.candidate_series_row(_payload("2026-10-02", held=None))
    # 2026-11-03（第 18＋16 條）起四組：等回落併回可開，序列不再有 priced_wait 那一格
    assert row["counts"] == {"open": 0, "missing": 0, "pass": 0, "held": None}
    assert row["side"] == {"not_multiple": 0, "edge_unmeasurable": 0, "legacy": 0, "precondition_failed": 0}
    assert row["no_narrative"] == 2 and row["oldest_stall_days"] == {"open": 0, "missing": None}
    # 遲滯與在門檻上（2026-11-01）：舊板沒有這兩格＝null，不是 0
    assert row["edge"] == {"on_threshold": None, "not_edge_pending": None}
    assert set(row) == {"date", "counts", "side", "no_narrative", "oldest_stall_days", "edge", "addon_unchecked",
                        "generated_at"}


def test_row_copies_the_addon_unchecked_count_including_zero() -> None:
    """加碼條件還沒查（第 18＋16 條）：有算的板照抄、0 就是 0；舊板或持股讀不到（板上是 None／沒有這格）＝null，不是 0。"""
    payload = _payload("2026-11-03")
    assert mat.candidate_series_row(payload)["addon_unchecked"] == 1
    payload["counts"] = dict(payload["counts"], addon_unchecked=0)
    assert mat.candidate_series_row(payload)["addon_unchecked"] == 0
    payload["counts"] = dict(payload["counts"], addon_unchecked=None)
    assert mat.candidate_series_row(payload)["addon_unchecked"] is None
    payload["counts"] = {k: v for k, v in payload["counts"].items() if k != "addon_unchecked"}
    assert mat.candidate_series_row(payload)["addon_unchecked"] is None


def test_only_the_default_state_dir_writes_the_real_series(tmp_path) -> None:
    """預設 state 目錄 → `library/private/measurement/`；其他目錄（測試、`--dir`）→ 那個目錄裡的 `measurement/`。"""
    assert mat.candidate_series_path(StateArtifactStore(DEFAULT_STATE_DIR)) == \
        mat.DEFAULT_MEASUREMENT_DIR / "candidate_state_series.jsonl"
    assert mat.DEFAULT_MEASUREMENT_DIR.parts[-3:] == ("library", "private", "measurement")
    other = mat.candidate_series_path(StateArtifactStore(tmp_path / "state"))
    assert other == tmp_path / "state" / "measurement" / "candidate_state_series.jsonl"


@pytest.fixture()
def fake_board(monkeypatch):
    import alpha.providers.candidates as cand

    def fake_load(universe, context=None, structure=None):
        payload = fake_candidates_payload()
        return {k: payload[k] for k in ("groups", "side_groups", "counts", "oldest_stall_days", "holdings",
                                        "narrative_rewrite", "ledger", "rollup", "universe", "today", "no_narrative")}

    monkeypatch.setattr(cand, "load_board", fake_load)
    monkeypatch.setattr(mat, "_graph_node_names", lambda ids: {})          # 測試不連真的圖


def test_materialize_appends_after_writing_the_artifact(fake_board, tmp_path) -> None:
    """真的走 `materialize_candidates`：artifact 寫完，序列多一行，`counts` 與 artifact 的 `counts` 相同。"""
    store = StateArtifactStore(tmp_path / "state")
    path, payload = mat.materialize_candidates(tickers=["AXTI"], store=store)
    series = tmp_path / "state" / "measurement" / "candidate_state_series.jsonl"
    rows = [json.loads(line) for line in _lines(series)]
    assert path.is_file() and len(rows) == 1
    merged = {**rows[0]["counts"], **rows[0]["side"], "no_narrative": rows[0]["no_narrative"],
              "addon_unchecked": rows[0]["addon_unchecked"]}
    assert merged == payload["counts"] and rows[0]["date"] == payload["today"]
    mat.materialize_candidates(tickers=["AXTI"], store=store)                # 同日重跑
    assert len(_lines(series)) == 1


def test_a_series_write_failure_does_not_fail_materialize(fake_board, tmp_path, monkeypatch, capsys) -> None:
    def broken(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(mat, "append_candidate_series", broken)
    path, _payload = mat.materialize_candidates(tickers=["AXTI"], store=StateArtifactStore(tmp_path / "state"))
    assert path.is_file()                                                    # 候選板照樣有
    assert "候選狀態序列沒寫進去" in capsys.readouterr().err
