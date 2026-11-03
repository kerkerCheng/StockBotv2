"""入圖包的「庫內已有幾份」由機器數（盲點修法 plan 2026-11-02-001 §1 第 20a 條；failure log #58）。

[750] Freiberger 的報告寫「自家庫先 grep：0」，實際 8 份，使用者據此 go。守的事：①名冊名稱與別名在 library/raw 命中幾份、
附例子；②英數字詞以前後非英數字為界（AXT 不比對 AXTI）、短字大小寫要一致、中日文名照子字串；③名冊或目錄讀不到是
「沒數到」，不是 0；④收據進紀錄、不進 digest；決策區塊印、公開入圖報告不印（例子是檔名）。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from intake import library_mentions as lm

FREIBERGER = SimpleNamespace(display_name="Freiberger Compound Materials GmbH",
                             name_aliases=("Freiberger Compound Materials", "Freiberger"), research_ticker=None)
AXT = SimpleNamespace(display_name="AXT, Inc.", name_aliases=("AXT", "北京通美"), research_ticker="AXTI")


class _Registry:
    def __init__(self, **companies):
        self.companies = companies

    def company(self, company_id):
        return self.companies.get(company_id)


def _raw(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "raw"
    root.mkdir()
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    return root


def test_counts_files_that_name_the_company_and_lists_examples(tmp_path: Path) -> None:
    raw = _raw(tmp_path, {"axti_10_k.txt": "Competitors include Sumitomo and Freiberger.",
                          "mops_2455.txt": "基板供應商：FREIBERGER COMPOUND MATERIALS",   # 長名不分大小寫
                          "other.txt": "nothing here", "scan.pdf": "Freiberger"})          # pdf 不掃
    check = lm.receipt("co:freiberger", raw_dir=raw, registry=_Registry(**{"co:freiberger": FREIBERGER}))
    assert check["status"] == "checked" and check["files"] == 2 and check["scanned"] == 3
    assert check["examples"] == ["axti_10_k.txt", "mops_2455.txt"]
    assert lm.valid(check)


def test_word_boundaries_case_and_cjk(tmp_path: Path) -> None:
    raw = _raw(tmp_path, {"a.txt": "AXTI filed its 10-Q",          # 代號整字
                          "b.txt": "the AXTX index",                # 不是 AXT 也不是 AXTI
                          "c.txt": "taxt axt",                      # 短字大小寫要一致、前後要是界
                          "d.txt": "子公司北京通美晶體"})            # 中文名照子字串
    check = lm.receipt("co:axt", raw_dir=raw, registry=_Registry(**{"co:axt": AXT}))
    assert check["examples"] == ["a.txt", "d.txt"]
    assert "AXTI" in check["terms"] and "北京通美" in check["terms"]


def test_numeric_tickers_are_not_terms() -> None:
    who = SimpleNamespace(display_name="全新光電", name_aliases=(), research_ticker="2455.TW")
    assert lm.mention_terms(who) == ["全新光電"]


def test_unreadable_is_not_zero(tmp_path: Path) -> None:
    class Broken:
        def company(self, _company_id):
            raise OSError("registry gone")

    assert lm.receipt("co:x", raw_dir=tmp_path, registry=Broken())["status"] == "upstream_unavailable"
    missing = lm.receipt("co:x", raw_dir=tmp_path, registry=_Registry())
    assert missing["status"] == "upstream_unavailable" and "名冊沒有" in missing["reason"]
    empty = lm.receipt("co:freiberger", raw_dir=_raw(tmp_path, {}), registry=_Registry(**{"co:freiberger": FREIBERGER}))
    assert empty["status"] == "upstream_unavailable" and lm.valid(empty)
    text = "\n".join(lm.render_lines(missing))
    assert "沒數到" in text and "這不是 0" in text and "命中" not in text


def test_render_names_the_count_and_the_rest() -> None:
    check = {"status": "checked", "company_id": "co:freiberger", "terms": ["Freiberger"], "scanned": 1215, "files": 10,
             "examples": [f"f{i}.txt" for i in range(lm.MAX_EXAMPLES)]}
    text = "\n".join(lm.render_lines(check))
    assert "**命中 10 份**" in text and "f0.txt" in text and "…另 2 份" in text and "以這裡為準" in text
    assert lm.render_lines(None) == []


def test_valid_rejects_malformed_receipts() -> None:
    assert not lm.valid({"status": "checked", "files": -1, "scanned": 1, "terms": [], "examples": []})
    assert not lm.valid({"status": "maybe"}) and not lm.valid({"status": "upstream_unavailable"}) and not lm.valid([])


def test_prepare_records_it_and_only_the_decision_packet_prints_it(tmp_path: Path, monkeypatch) -> None:
    from intake import actions as research_actions
    from intake import application

    from test_research_actions import _request_for_docs

    def _down():
        raise OSError("connection refused")

    monkeypatch.setattr(application, "_driver", _down)
    receipt = {"status": "checked", "company_id": "co:axt", "terms": ["AXTI"], "scanned": 3, "files": 1,
               "examples": ["axti_10_k.txt"]}
    monkeypatch.setattr(lm, "receipt", lambda company_id, **_kw: dict(receipt, company_id=company_id))
    prepared = application._prepare_research_action_impl(_request_for_docs("first_doc"), root=tmp_path)
    assert prepared["status"] == "ready"
    record = research_actions.read_action(prepared["action_id"], root=tmp_path)
    assert record["library_mention_check"]["files"] == 1 and record["library_mention_check"]["company_id"] == "co:axt"
    assert "庫內已有幾份" in prepared["review_packet"] and "axti_10_k.txt" in prepared["review_packet"]
    assert "庫內已有幾份" not in research_actions._full_report(record)          # 公開入圖報告不印檔名
    dry = application._prepare_research_action_impl(_request_for_docs("first_doc"), root=tmp_path, dry_run=True)
    assert "**命中 1 份**" in dry["library_mentions"]
