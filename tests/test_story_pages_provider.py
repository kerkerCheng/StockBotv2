"""故事頁的帳（Phase 8 plan 2026-11-26-001 Step 8.1；`alpha.providers.story_pages`）。

守四件事：
1. 跨帳核對：名冊、現行敘事、等待 registry、圖上節點、冷讀回報——各自對不上就 E5／E6；
   圖連不上是 W10（沒核，**不是通過**）。
2. 寫入只有一個入口：有 ERROR 就什麼都不寫；收了才把片段複製進私有區、帳追加一列；一模一樣的不再寫。
3. 現行頁＝帳上最後一列；壞行回報不靜默丟（INV-3）；片段被改過或不見了就 raise，不回半份。
4. 對版（rebind）：要有現行敘事、要真的換了版、要寫一句、片段要還在。
全部在 tmp 目錄：假名冊、假敘事、假等待、假圖——不讀真實的帳。
"""
from __future__ import annotations

import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.providers import story_pages as spp
from identity.registry import CompanyIdentity, IdentityRegistry

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "story_page" / "ZZZZ"
RELATIVE = Path("tests") / "fixtures" / "story_page" / "ZZZZ"
TODAY = date(2026, 11, 26)
NOW = datetime(2026, 11, 26, 14, 0, tzinfo=timezone.utc)
WATCH = "ew_9001_2026-11-26"


#: 用真的名冊類別建一份小名冊（不自己仿介面——仿的會跟真的長不一樣：`companies` 是屬性不是方法）
REGISTRY = IdentityRegistry(version=1, companies=(
    CompanyIdentity(company_id="co:zzzz_example", research_ticker="ZZZZ", display_name="範例精密"),
    CompanyIdentity(company_id="co:pkg_a", research_ticker=None, display_name="封裝廠甲"),
    CompanyIdentity(company_id="co:pkg_b", research_ticker=None, display_name="封裝廠乙", name_aliases=("甲乙封裝",)),
))


def _slots() -> dict:
    """敘事的依據（形狀照 `tests/test_stories.py::_slots`：v2 寫入規則要的 placeholder 都在）。"""
    ev = ["graph://x"]
    return {"demand": {"text": "買方擴產。", "evidence_refs": ev},
            "position": {"text": "坐在檢測層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": "卡的是高階機台的量。", "evidence_refs": ev},
            "priced_in": {"text": "自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。", "evidence_refs": ev},
            "our_bet": {"text": "賭高階機台。", "evidence_refs": ev},
            "what_must_be_true": {"text": "買方照計畫擴產。", "evidence_refs": ev},
            "when": {"text": "{next_checkpoint_date} 檢核點。", "evidence_refs": ev}}


def _brief(created: datetime = datetime(2026, 11, 25, tzinfo=timezone.utc)):
    rec = brief_record(company_id="co:zzzz_example", ticker="ZZZZ", slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:zzzz_inspection", "unit": "layer", "reading_id": "sr_" + "a" * 16}],
                       answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": "pass", "watch_id": None, "reason": "理由的依據"},
                       created_at=created)
    return parse_brief_record(rec)


BRIEF = _brief()
NEWER = _brief(datetime(2026, 11, 26, 1, 0, tzinfo=timezone.utc))


def _layout(tmp_path: Path, brief_id: str = BRIEF.brief_id) -> Path:
    """範例頁複製到 tmp 根目錄下同一個相對位置（`quote_sources` 的 glob 對根目錄解析）。"""
    folder = tmp_path / RELATIVE
    shutil.copytree(FIXTURE, folder)
    _edit_decl(folder, brief_id=brief_id)
    return folder


def _edit_decl(folder: Path, **over) -> None:
    target = folder / spp.DECLARATION_FILE
    decl = json.loads(target.read_text(encoding="utf-8"))
    decl.update(over)
    target.write_text(json.dumps(decl, ensure_ascii=False, indent=2), encoding="utf-8")


def _kw(tmp_path: Path, *, briefs=(BRIEF,), watches=(WATCH,), graph=lambda ids: set(ids),
        registry=None) -> dict:
    return {"registry": registry or REGISTRY,
            "brief_loader": lambda t: (list(briefs), []) if t == "ZZZZ" else ([], []),
            "watch_loader": lambda: {"watches": [{"watch_id": w} for w in watches]},
            "graph_checker": graph, "root": tmp_path, "today": TODAY}


def _ledger(tmp_path: Path) -> Path:
    return tmp_path / "library" / "private" / "alpha" / "story_pages.jsonl"


def _page_dir(tmp_path: Path) -> Path:
    return tmp_path / "library" / "private" / "story_pages"


def _add(tmp_path: Path, folder: Path, **over):
    kw = _kw(tmp_path, **{k: over.pop(k) for k in ("briefs", "watches", "graph", "registry") if k in over})
    return spp.add_page(folder, path=_ledger(tmp_path), page_dir=_page_dir(tmp_path), now=NOW, **kw, **over)


def _codes(findings) -> list[str]:
    return [f.code for f in findings]


def _text(findings, code: str) -> str:
    return "\n".join(f.message for f in findings if f.code == code)

# ---------------------------------------------------------------- 跨帳核對

def test_example_folder_passes_when_every_ledger_agrees(tmp_path) -> None:
    report = spp.check_folder(_layout(tmp_path), **_kw(tmp_path))
    assert report.errors == [], [f.line() for f in report.errors]
    assert _codes(report.warnings) == ["W1"]
    assert report.company_id == "co:zzzz_example"
    assert report.current_brief_id == BRIEF.brief_id
    assert report.quote_files == [(RELATIVE / "source_excerpt.txt").as_posix()]
    assert report.as_dict()["visible_chars"] == report.check.visible_chars


def test_brief_id_must_be_the_current_version(tmp_path) -> None:
    report = spp.check_folder(_layout(tmp_path), **_kw(tmp_path, briefs=(BRIEF, NEWER)))
    assert f"現行那一版敘事 {NEWER.brief_id}" in _text(report.errors, "E5")


def test_no_current_v2_brief_is_an_error(tmp_path) -> None:
    folder = _layout(tmp_path)
    assert "沒有現行的 v2 敘事" in _text(spp.check_folder(folder, **_kw(tmp_path, briefs=())).errors, "E5")
    kw = _kw(tmp_path)
    kw["brief_loader"] = lambda t: ([], ["stories.jsonl:3: 壞行"])
    assert "1 行解析失敗" in _text(spp.check_folder(folder, **kw).errors, "E5")


def test_unknown_ticker_is_an_error_not_a_guess(tmp_path) -> None:
    folder = _layout(tmp_path)
    _edit_decl(folder, ticker="YYYY")
    assert "YYYY 不在名冊" in _text(spp.check_folder(folder, **_kw(tmp_path)).errors, "E5")


def test_watch_ids_must_exist_in_the_waiting_registry(tmp_path) -> None:
    report = spp.check_folder(_layout(tmp_path), **_kw(tmp_path, watches=("ew_0001_2026-08-31",)))
    assert f"等待 registry 找不到：{WATCH}" in _text(report.errors, "E5")


def test_unreachable_graph_is_a_warning_not_a_pass(tmp_path) -> None:
    report = spp.check_folder(_layout(tmp_path), **_kw(tmp_path, graph=lambda ids: None))
    assert report.errors == []
    assert "W10" in _codes(report.warnings) and "沒核" in _text(report.warnings, "W10")


def test_ride_nodes_must_exist_on_the_graph(tmp_path) -> None:
    report = spp.check_folder(_layout(tmp_path), **_kw(tmp_path, graph=lambda ids: set()))
    assert "圖上找不到：tech:zzzz_inspection" in _text(report.errors, "E5")


def test_cold_read_report_must_be_in_the_folder(tmp_path) -> None:
    folder = _layout(tmp_path)
    (folder / "coldread" / "REPORT.md").unlink()
    assert "coldread/REPORT.md 不在這個資料夾裡" in _text(spp.check_folder(folder, **_kw(tmp_path)).errors, "E6")


def test_missing_files_are_findings_not_exceptions(tmp_path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    report = spp.check_folder(empty, **_kw(tmp_path))
    assert "沒有 page.html" in _text(report.errors, "E2")
    assert "沒有 page.json" in _text(report.errors, "E5")


def test_quote_sources_that_match_nothing_say_so(tmp_path) -> None:
    folder = _layout(tmp_path)
    _edit_decl(folder, quote_sources=["nowhere/*.txt"])
    report = spp.check_folder(folder, **_kw(tmp_path))
    assert "一個檔都沒對到" in _text(report.warnings, "W6")
    assert report.quote_files == []

# ---------------------------------------------------------------- 寫入

def test_add_copies_the_fragment_and_appends_one_row(tmp_path) -> None:
    folder = _layout(tmp_path)
    record, report = _add(tmp_path, folder)
    pid = spp.page_id("co:zzzz_example", BRIEF.brief_id, report.html_sha256)
    assert record["page_id"] == pid and pid.startswith("sp_") and len(pid) == 19
    assert record["kind"] == "page" and record["supersedes_id"] is None and record["rebind_note"] is None
    assert record["html_path"] == f"library/private/story_pages/ZZZZ/{pid}.html"
    assert record["created_at"] == NOW.isoformat()
    assert record["warnings"] and record["warnings"][0].startswith("W1 ")
    assert record["declaration"]["brief_id"] == BRIEF.brief_id
    assert spp.read_html(record, root=tmp_path) == (folder / spp.PAGE_FILE).read_text(encoding="utf-8")
    lines = _ledger(tmp_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 and json.loads(lines[0]) == record


def test_the_same_page_twice_is_refused(tmp_path) -> None:
    folder = _layout(tmp_path)
    _add(tmp_path, folder)
    with pytest.raises(ContractViolation, match="跟現行那一頁"):
        _add(tmp_path, folder)
    assert len(_ledger(tmp_path).read_text(encoding="utf-8").splitlines()) == 1


def test_a_refused_page_writes_nothing(tmp_path) -> None:
    folder = _layout(tmp_path)
    page = folder / spp.PAGE_FILE
    page.write_text(page.read_text(encoding="utf-8").replace("</header>", "<script>alert(1)</script>\n</header>"),
                    encoding="utf-8")
    with pytest.raises(ContractViolation, match="拒收"):
        _add(tmp_path, folder)
    assert not _ledger(tmp_path).exists()
    assert not _page_dir(tmp_path).exists()


def test_a_secret_looking_declaration_is_refused_before_writing(tmp_path) -> None:
    folder = _layout(tmp_path)
    _edit_decl(folder, evidence_pack="Authorization: Bearer abcdef0123456789")
    with pytest.raises(ContractViolation, match="密鑰"):
        _add(tmp_path, folder)
    assert not _ledger(tmp_path).exists() and not _page_dir(tmp_path).exists()


def test_a_new_version_supersedes_and_the_last_row_is_current(tmp_path) -> None:
    folder = _layout(tmp_path)
    first, _ = _add(tmp_path, folder)
    page = folder / spp.PAGE_FILE
    page.write_text(page.read_text(encoding="utf-8").replace("量在低階，錢在高階", "量在低階，利潤在高階"),
                    encoding="utf-8")
    second, _ = _add(tmp_path, folder)
    assert second["supersedes_id"] == first["page_id"] and second["page_id"] != first["page_id"]
    current, errors = spp.current_pages(path=_ledger(tmp_path))
    assert errors == [] and current["co:zzzz_example"]["page_id"] == second["page_id"]
    assert [r["page_id"] for r in spp.history("co:zzzz_example", path=_ledger(tmp_path))] == [
        first["page_id"], second["page_id"]]
    assert spp.read_html(first, root=tmp_path) != spp.read_html(second, root=tmp_path)   # 舊版片段還在、沒被蓋


def test_bad_ledger_lines_are_reported_not_dropped(tmp_path) -> None:
    folder = _layout(tmp_path)
    record, _ = _add(tmp_path, folder)
    with _ledger(tmp_path).open("a", encoding="utf-8") as handle:
        handle.write("不是 JSON\n")
        handle.write(json.dumps({**record, "kind": "draft"}, ensure_ascii=False) + "\n")
        handle.write(json.dumps({k: v for k, v in record.items() if k != "declaration"}, ensure_ascii=False) + "\n")
    records, errors = spp.read_records(path=_ledger(tmp_path))
    assert [r["page_id"] for r in records] == [record["page_id"]]
    assert len(errors) == 3
    assert errors[0].startswith("story_pages.jsonl:2:")
    assert "kind 不認得" in errors[1] and "缺 declaration" in errors[2]


def test_a_tampered_or_missing_fragment_raises(tmp_path) -> None:
    record, _ = _add(tmp_path, _layout(tmp_path))
    stored = spp.html_file(record, root=tmp_path)
    stored.write_text(stored.read_text(encoding="utf-8") + "<p>偷加的</p>", encoding="utf-8")
    with pytest.raises(ContractViolation, match="被改過"):
        spp.read_html(record, root=tmp_path)
    stored.unlink()
    with pytest.raises(ContractViolation, match="不見了"):
        spp.read_html(record, root=tmp_path)


@pytest.mark.parametrize("ticker", ["../x", "..", ".", "..\\x", "a/../../b"])
def test_slug_keeps_the_fragment_inside_the_page_dir(tmp_path, ticker: str) -> None:
    slug = spp._safe_slug(ticker)
    assert "/" not in slug and "\\" not in slug and not slug.startswith(".")
    assert (tmp_path / slug / "a.html").resolve().parent.parent == tmp_path.resolve()
    assert spp._safe_slug("6727.TWO") == "6727.TWO"

# ---------------------------------------------------------------- 對版

NOTE = "新版只把檢核日從十二月改到一月，夢與反證都沒變，這一頁照樣站得住"


def _rebind(tmp_path: Path, note: str = NOTE, **over):
    kw = _kw(tmp_path, **{k: over.pop(k) for k in ("briefs", "registry") if k in over})
    for key in ("watch_loader", "graph_checker"):
        kw.pop(key)
    return spp.rebind_page("ZZZZ", note, path=_ledger(tmp_path), now=NOW, **kw, **over)


def test_rebind_needs_a_page_first(tmp_path) -> None:
    with pytest.raises(ContractViolation, match="還沒有故事頁"):
        _rebind(tmp_path, briefs=(BRIEF, NEWER))


def test_rebind_binds_the_same_fragment_to_the_new_brief(tmp_path) -> None:
    first, _ = _add(tmp_path, _layout(tmp_path))
    with pytest.raises(ContractViolation, match="不必對版"):
        _rebind(tmp_path)                                         # 敘事沒換版
    with pytest.raises(ContractViolation, match="12 字以上"):
        _rebind(tmp_path, "沒變", briefs=(BRIEF, NEWER))
    record = _rebind(tmp_path, briefs=(BRIEF, NEWER))
    assert record["kind"] == "rebind" and record["brief_id"] == NEWER.brief_id
    assert record["supersedes_id"] == first["page_id"] and record["page_id"] != first["page_id"]
    assert record["html_path"] == first["html_path"] and record["html_sha256"] == first["html_sha256"]
    assert record["rebind_note"] == NOTE
    current, _errors = spp.current_pages(path=_ledger(tmp_path))
    assert current["co:zzzz_example"]["page_id"] == record["page_id"]
    assert spp.read_html(record, root=tmp_path) == spp.read_html(first, root=tmp_path)
    with pytest.raises(ContractViolation, match="不必對版"):
        _rebind(tmp_path, briefs=(BRIEF, NEWER))


def test_rebind_refuses_unknown_tickers_missing_briefs_and_tampered_fragments(tmp_path) -> None:
    first, _ = _add(tmp_path, _layout(tmp_path))
    with pytest.raises(ContractViolation, match="不在名冊"):
        spp.rebind_page("YYYY", NOTE, path=_ledger(tmp_path), registry=REGISTRY, root=tmp_path, today=TODAY)
    with pytest.raises(ContractViolation, match="沒有現行的 v2 敘事"):
        _rebind(tmp_path, briefs=())
    stored = spp.html_file(first, root=tmp_path)
    stored.write_text("<p>換掉</p>", encoding="utf-8")
    with pytest.raises(ContractViolation, match="被改過"):
        _rebind(tmp_path, briefs=(BRIEF, NEWER))
    assert len(_ledger(tmp_path).read_text(encoding="utf-8").splitlines()) == 1


def test_page_status_against_the_current_brief(tmp_path) -> None:
    record = {"brief_id": BRIEF.brief_id}
    assert spp.page_status(record, BRIEF.brief_id) == "current"
    assert spp.page_status(record, NEWER.brief_id) == "stale"
    assert spp.page_status(record, None) == "no_brief"
    ids = spp.current_brief_ids(["ZZZZ", "YYYY"], brief_loader=lambda t: ([BRIEF, NEWER], []) if t == "ZZZZ"
                                else ([], []), today=TODAY)
    assert ids == {"ZZZZ": NEWER.brief_id, "YYYY": None}


def test_company_names_come_from_the_registry() -> None:
    assert spp.company_names(REGISTRY) == {"co:zzzz_example": ["範例精密"], "co:pkg_a": ["封裝廠甲"],
                                              "co:pkg_b": ["封裝廠乙", "甲乙封裝"]}
