"""讀圖反證寫「新進」、圖上 develops 這一層的公司卻不在 entities（2026-11-10，failure log #143；使用者「#143 … 照推薦做」）。

CW DFB 層讀圖 `sr_790f15cdae054ce3` 反證①「不在現有 14 家之內的新進者首次量產」，entities 只列 11 家既有廠——環宇（co:gcs_holdings，
4991.TWO；圖上 develops 這一層）不在其中：它自己公告量產，①不會醒。

守的事：①寫「新進」的那一條，develops 這一層、不在 entities 的公司列出來（n＝disproof[] 的順序）；②is_variant_of 的來源、
已列進 entities 的、沒寫「新進」的（「第二家」「新廠」）不算；③收據附 research ticker；④只印不擋——提示算不成照樣寫入、照樣登記 watch。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from alpha.structure_reading import structure_reading_record
from alpha.structure_reading.entrants import developers, entrant_gaps

NODE = "tech:cw_dfb_laser"
GCS = "co:gcs_holdings"
NOW = datetime(2026, 11, 7, 3, 0, tzinfo=timezone.utc)
CONDITION = "①新增產能或新進者的一手（不是圖上第 N 家）：不在現有 14 家之內的新進者首次量產"


def _structure() -> dict:
    def edge(src: str, relation: str) -> dict:
        return {"src": src, "relation": relation, "dst": NODE, "substitutability": None, "sole_source": None,
                "qualification_status": None, "evidence": "needs_review", "documents": 1}
    return {"node": NODE, "result_digest": "e" * 64, "anchor_chain": None,
            "angles": {"demand_side": [], "supply_side": [edge("co:lumentum", "supplies_to")], "next_layer": [],
                       "counter_path": [],
                       "developers": [edge(GCS, "develops"), edge("co:lumentum", "develops"),
                                      edge("tech:cw_dfb_400mw", "is_variant_of")]}}


def _disproof(condition: str = CONDITION, entities=("co:lumentum", "co:coherent")) -> dict:
    return {"condition": condition, "entities": list(entities), "check_frequency": "每季",
            "action_48h": "重讀這一層", "source": "self"}


def _record(*disproof: dict) -> dict:
    return structure_reading_record(node=NODE, structure=_structure(), unit="layer", kind="undecided",
                                    reading="判不出：需求側在等 CW 光源，供給側缺新進者的量產時點與產能數字。", expires=date(2027, 2, 7), created_at=NOW,
                                    author="test", disproof=list(disproof), citations=[])


def test_cw_dfb_replay_names_the_developer_missing_from_an_entrant_condition() -> None:
    record = _record(_disproof())
    assert developers(record) == [GCS, "co:lumentum"]                     # is_variant_of 的來源是節點、不算
    assert entrant_gaps(record) == [{"n": 1, "missing": [GCS]}]


def test_listed_developers_and_conditions_without_the_word_are_quiet() -> None:
    assert entrant_gaps(_record(_disproof(entities=("co:lumentum", GCS)))) == []
    second = _disproof("買方的一手點名第二家供應商；或 Coherent 寫出新廠進入量產")
    assert entrant_gaps(_record(second)) == []
    both = _record(second, _disproof("不在現有供應商之內的新進入者首次量產出貨並寫出產能"))
    assert entrant_gaps(both) == [{"n": 2, "missing": [GCS]}]              # 編號照 disproof[] 的順序


def test_the_receipt_names_the_company_with_its_ticker() -> None:
    from alpha.providers.structure_readings import entrant_notices

    lines = entrant_notices(_record(_disproof()))
    assert len(lines) == 1 and "反證第 1 條" in lines[0] and f"{GCS}（4991.TWO）" in lines[0]
    assert entrant_notices(_record(_disproof(entities=("co:lumentum", GCS)))) == []


def _run_add(tmp_path: Path, monkeypatch, capsys, *, notices=None) -> tuple[int, str, list]:
    from alpha import cli
    from alpha.providers import structure_readings as provider

    registered: list = []
    monkeypatch.setattr(provider, "fetch_structure_snapshot_with_quotes", lambda node: (_structure(), {}, None))
    monkeypatch.setattr(provider, "read_reading_records", lambda node, **kw: ([], []))
    monkeypatch.setattr(provider, "append_reading_record", lambda record, **kw: tmp_path / "ledger.jsonl")

    def register(record, **kw):
        registered.append(record["reading_id"])
        return {k: [] for k in ("registered", "consumed", "reread_registered", "reread_consumed", "touched_handled")}

    monkeypatch.setattr(provider, "register_reading_watches", register)
    if notices is not None:
        monkeypatch.setattr(provider, "entrant_notices", notices)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"unit": "layer", "kind": "undecided", "reading": "判不出：需求側在等 CW 光源，供給側缺新進者的量產時點與產能數字。",
                                "expires": "2027-02-07", "disproof": [_disproof()], "citations": []},
                               ensure_ascii=False), encoding="utf-8")
    rc = cli.main(["structure-reading", NODE, "--add", str(spec)])
    return rc, capsys.readouterr().out, registered


def test_the_add_receipt_prints_the_notice_after_the_write(tmp_path, monkeypatch, capsys) -> None:
    rc, out, registered = _run_add(tmp_path, monkeypatch, capsys)
    assert rc == 0 and len(registered) == 1
    assert out.index("✓ sr_") < out.index("⚠ 反證第 1 條寫「新進」") and GCS in out


def test_a_notice_that_fails_does_not_stop_the_write_or_the_watches(tmp_path, monkeypatch, capsys) -> None:
    def boom(record):
        raise OSError("名冊讀不到")

    rc, out, registered = _run_add(tmp_path, monkeypatch, capsys, notices=boom)
    assert rc == 0 and len(registered) == 1, "提示算不成，寫入與等待登記照常"
    assert "新進者那一項這次沒核成（OSError" in out
