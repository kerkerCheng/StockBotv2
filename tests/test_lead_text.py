"""分類前的內文（failure log #105，2026-10-27）。

事發：分類器只看得到 `raw_text`；EDGAR／MFN／公司新聞頁的 lead 沒有原文（6-K 主文件又只是封面），雷達的事實句沒帶進
prompt——09-01 起 25 則因「原文為空」被判 no_go（GFS、POET 6-K、Samsung 基板擴產）。守的是：

1. 6-K／8-K 照索引頁的 **Type 欄**抓 EX-99.x 附件（GFS 的附件叫 `gfpressreleasefinal.htm`，檔名沒有 99），放在主文件前面；
   索引頁抓不到＝抓不到，**不得把只有封面的主文件存成全文**。
2. 看不到任何內文的 lead **到不了分類器**（不在批次、不佔上限），而且會說話（批次那一行、心跳、drain 段 0）。
3. 分類器看得到的內文（全文、雷達事實句）真的進了 prompt，且標明是哪一種（L12：輸入要出現在證據欄位）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

INDEX_HTML = """
<table class="tableFile" summary="Document Format Files">
 <tr><th scope="col">Seq</th><th scope="col">Description</th><th scope="col">Document</th><th scope="col">Type</th><th>Size</th></tr>
 <tr><td scope="row">1</td><td scope="row">6-K</td>
     <td scope="row"><a href="/Archives/edgar/data/1709048/000170904826000252/a2026-10form6xk.htm">a2026-10form6xk.htm</a></td>
     <td scope="row">6-K</td><td scope="row">10080</td></tr>
 <tr class="evenRow"><td scope="row">2</td><td scope="row">EX-99.1</td>
     <td scope="row"><a href="/Archives/edgar/data/1709048/000170904826000252/gfpressreleasefinal.htm">gfpressreleasefinal.htm</a></td>
     <td scope="row">EX-99.1</td><td scope="row">23741</td></tr>
 <tr><td scope="row">3</td><td scope="row">EX-99.2</td>
     <td scope="row"><a href="/ix?doc=/Archives/edgar/data/1709048/000170904826000252/slides.htm">slides.htm</a></td>
     <td scope="row">EX-99.2</td><td scope="row">5000</td></tr>
 <tr><td scope="row">4</td><td scope="row"></td>
     <td scope="row"><a href="/Archives/edgar/data/1709048/000170904826000252/image_0a.jpg">image_0a.jpg</a></td>
     <td scope="row">GRAPHIC</td><td scope="row">79641</td></tr>
 <tr class="evenRow"><td scope="row">&nbsp;</td><td scope="row">Complete submission text file</td>
     <td scope="row"><a href="/Archives/edgar/data/1709048/000170904826000252/0001709048-26-000252.txt">0001709048-26-000252.txt</a></td>
     <td scope="row">&nbsp;</td><td scope="row">143292</td></tr>
</table>
"""

GFS_URL = "https://www.sec.gov/Archives/edgar/data/1709048/000170904826000252/a2026-10form6xk.htm"


def test_exhibits_are_picked_by_type_column_not_file_name() -> None:
    from fetchers.edgar import parse_filing_index

    rows = parse_filing_index(INDEX_HTML)
    by_type = {r["type"]: r["document"] for r in rows}
    assert by_type["EX-99.1"] == "gfpressreleasefinal.htm"      # 檔名裡沒有 99
    assert by_type["EX-99.2"] == "slides.htm"                   # inline XBRL 的 /ix?doc= 連結
    assert by_type["6-K"] == "a2026-10form6xk.htm"
    assert "" in by_type and by_type[""].endswith(".txt")       # 完整 submission 沒有 Type，不會被當附件
    assert len(rows) == 5


def test_six_k_text_puts_exhibits_before_the_cover(monkeypatch: pytest.MonkeyPatch) -> None:
    import fetchers.edgar as edgar
    from engine_b import semantic_prescreen as sp

    monkeypatch.setattr(edgar, "fetch_filing_text", lambda cik, acc, doc: "UNITED STATES SECURITIES AND EXCHANGE COMMISSION FORM 6-K cover")
    monkeypatch.setattr(edgar, "fetch_filing_exhibits",
                        lambda cik, acc: [("EX-99.1", "gfpressreleasefinal.htm", "GlobalFoundries announces X")])
    fetch = sp.fetcher_for({"source": "edgar:GFS", "url": GFS_URL, "form_type": "6-K"})
    text = fetch()
    assert text.index("GlobalFoundries announces X") < text.index("FORM 6-K cover")
    assert "【附件 EX-99.1｜gfpressreleasefinal.htm】" in text


def test_ten_q_keeps_the_main_document_only(monkeypatch: pytest.MonkeyPatch) -> None:
    import fetchers.edgar as edgar
    from engine_b import semantic_prescreen as sp

    monkeypatch.setattr(edgar, "fetch_filing_text", lambda cik, acc, doc: "quarterly report body")

    def no_index(*_a, **_kw):
        raise AssertionError("10-Q 不該去抓附件")

    monkeypatch.setattr(edgar, "fetch_filing_exhibits", no_index)
    fetch = sp.fetcher_for({"source": "edgar:X", "url": GFS_URL, "form_type": "10-Q"})
    assert fetch() == "quarterly report body"


def test_an_unreachable_index_is_a_failed_fetch_not_a_cover_only_text(monkeypatch: pytest.MonkeyPatch,
                                                                     tmp_path: Path) -> None:
    """只有封面的主文件存進去的話，下一輪讀存檔、分類器又只看到封面——等於把 #105 存起來。"""
    import fetchers.edgar as edgar
    from engine_b import lead_text

    monkeypatch.setattr(edgar, "fetch_filing_text", lambda cik, acc, doc: "FORM 6-K cover")

    def index_down(*_a, **_kw):
        raise ConnectionError("index 503")

    monkeypatch.setattr(edgar, "fetch_filing_exhibits", index_down)
    lead = {"lead_id": "lead_gfs", "status": "pending", "source": "edgar:GFS", "source_class": "primary",
            "url": GFS_URL, "form_type": "6-K", "title": "GFS 6-K filed"}
    sendable, held, counts = lead_text.attach([lead], text_dir=tmp_path)
    assert sendable == [] and [r["body_status"] for r in held] == ["fetch_failed"]
    assert not list(tmp_path.iterdir()), "抓不到附件時不得留下只有封面的存檔"


def test_a_cover_only_cache_from_before_105_is_refetched(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """10-27 實測：GFS 6-K 的存檔只有封面（預篩 10-15 存的）。舊存檔不重抓的話，修好抓附件也讀不到。
    重抓的新版仍逐字含主文件——預篩當時驗過的引文仍是子字串。"""
    import fetchers.edgar as edgar
    from engine_b import semantic_prescreen as sp

    cover = "UNITED STATES SECURITIES AND EXCHANGE COMMISSION FORM 6-K Exhibit 99.1 Press release"
    (tmp_path / "lead_gfs.txt").write_text(cover, encoding="utf-8")
    (tmp_path / "lead_gfs.json").write_text(json.dumps({"lead_id": "lead_gfs", "chars": len(cover)}), encoding="utf-8")
    lead = {"lead_id": "lead_gfs", "url": GFS_URL, "form_type": "6-K", "source": "edgar:GFS"}
    assert sp.cached_text("lead_gfs", lead, text_dir=tmp_path) is None
    monkeypatch.setattr(edgar, "fetch_filing_text", lambda cik, acc, doc: cover)
    monkeypatch.setattr(edgar, "fetch_filing_exhibits", lambda cik, acc: [("EX-99.1", "gf.htm", "GF reports Q3")])
    text, reused = sp.load_or_fetch_text("lead_gfs", lead, text_dir=tmp_path, fetch=sp.fetcher_for(lead))
    assert not reused and text.startswith("【附件 EX-99.1") and cover in text
    assert sp.cached_text("lead_gfs", lead, text_dir=tmp_path) == text           # 新版標了 exhibits_checked
    ten_q = {**lead, "form_type": "10-Q"}
    (tmp_path / "lead_q.txt").write_text("10-Q body", encoding="utf-8")
    assert sp.cached_text("lead_q", ten_q, text_dir=tmp_path) == "10-Q body"      # 不需要附件的照舊重用


def _lead(lead_id: str, **fields) -> dict:
    return {"lead_id": lead_id, "status": "pending", "title": f"title {lead_id}", **fields}


def test_every_lead_gets_one_status_and_only_text_bearing_ones_are_sent(tmp_path: Path) -> None:
    from engine_b import lead_text

    (tmp_path / "lead_cached.txt").write_text("cached body " * 400, encoding="utf-8")
    (tmp_path / "lead_cached.json").write_text(json.dumps({"exhibits_checked": True}), encoding="utf-8")
    rows = [
        _lead("lead_x", source="x:a", source_class="secondary", raw_text="tweet body"),
        _lead("lead_radar", source="web_radar:new", source_class="secondary", refs={"radar_fact": "三星電機投資 50 億美元"}),
        _lead("lead_theme", source="theme_scan:robotics", url="https://www.fool.com/x"),
        _lead("lead_cached", source="edgar:GFS", source_class="primary", url=GFS_URL),
        _lead("lead_fetch", source="mfn:sivers", source_class="primary", url="https://mfn.se/a"),
        _lead("lead_fail", source="mfn:sivers", source_class="primary", url="https://mfn.se/b"),
        _lead("lead_nofetch", source="yahoo:iqe-l", source_class="secondary", url="https://uk.advfn.com/a"),
        _lead("lead_later", source="mfn:sivers", source_class="primary", url="https://mfn.se/c"),
    ]
    fetchers = {"lead_fetch": lambda: "fetched body", "lead_fail": lambda: None, "lead_later": lambda: "late"}

    def pick(row):
        if row["source"].startswith("yahoo:"):
            return None
        return fetchers.get(row["lead_id"], lambda: "unexpected")

    sendable, held, counts = lead_text.attach(rows, text_dir=tmp_path, fetcher=pick, fetch_limit=2)
    status = {r["lead_id"]: r["body_status"] for r in [*sendable, *held]}
    assert status == {"lead_x": "raw_text", "lead_radar": "radar_fact", "lead_theme": "self_described",
                      "lead_cached": "cached", "lead_fetch": "fetched", "lead_fail": "fetch_failed",
                      "lead_nofetch": "no_fetcher", "lead_later": "deferred"}
    assert [r["lead_id"] for r in sendable] == ["lead_x", "lead_radar", "lead_theme", "lead_cached", "lead_fetch"]
    assert set(status.values()) <= set(lead_text.STATUSES)
    cached = next(r for r in sendable if r["lead_id"] == "lead_cached")
    assert len(cached["body_text"]) <= lead_text.BODY_MAX_CHARS + len(lead_text.TRUNCATION_MARK)
    assert cached["body_text"].endswith(lead_text.TRUNCATION_MARK)
    assert (tmp_path / "lead_fetch.txt").read_text(encoding="utf-8") == "fetched body"   # 與預篩同一個存檔
    line = lead_text.summary_line(counts, held)
    assert "無內文、不送分類 3 則" in line and "lead_nofetch" in line


def test_no_fetch_never_calls_a_fetcher(tmp_path: Path) -> None:
    from engine_b import lead_text

    def boom():
        raise AssertionError("--no-fetch 不得連網")

    rows = [_lead("lead_e", source="edgar:X", source_class="primary", url=GFS_URL)]
    sendable, held, _ = lead_text.attach(rows, text_dir=tmp_path, fetch=False, fetcher=lambda row: boom)
    assert sendable == [] and held[0]["body_status"] == "deferred"


def test_held_pending_is_offline_and_only_counts_pending(tmp_path: Path) -> None:
    from engine_b import lead_text

    leads = {
        "lead_a": {"status": "pending", "source_class": "primary", "source": "edgar:X"},
        "lead_b": {"status": "triaged_no_go", "source_class": "primary", "source": "edgar:X"},
        "lead_c": {"status": "pending", "source_class": "primary", "source": "edgar:X"},
        "lead_d": {"status": "pending", "source": "theme_scan:power"},
    }
    (tmp_path / "lead_c.txt").write_text("body", encoding="utf-8")
    assert lead_text.held_pending(leads, text_dir=tmp_path) == ["lead_a"]


def test_the_prompt_carries_the_body_and_says_what_kind_it_is() -> None:
    from crons import llm_step

    row = {"lead_id": "lead_r", "source": "web_radar:new", "title": "Samsung secures customer backing",
           "raw_text": "", "body_status": "radar_fact",
           "refs": {"radar_fact": "三星電機投資約 50 億美元擴充 FCBGA 載板產能", "radar_publisher": "DIGITIMES",
                    "radar_why": "不該進 prompt"}}
    out = llm_step._prompt_lead(row)
    assert out["radar_fact"].startswith("三星電機") and out["radar_publisher"] == "DIGITIMES"
    assert out["body_status"] == "radar_fact"
    assert "radar_why" not in json.dumps(out, ensure_ascii=False), "雷達模型的理由不給分類器（它要自己判）"
    edgar = llm_step._prompt_lead({"lead_id": "lead_g", "raw_text": "", "body_status": "fetched",
                                   "body_text": "【附件 EX-99.1｜gf.htm】\n" + "x" * 5000})
    assert edgar["body_text"].startswith("【附件 EX-99.1") and len(edgar["body_text"]) < 3100
    prompt = (ROOT / "crons" / "triage_prompt.md").read_text(encoding="utf-8")
    assert "不要因為 `raw_text` 是空的就判「無可查核內容」" in prompt
    for status in ("raw_text", "body_text", "radar_fact", "self_described"):
        assert f"`{status}`" in prompt, status


def test_the_batch_command_keeps_textless_leads_out_and_says_so(tmp_path: Path) -> None:
    """端到端：`list --triage-batch --json` 的 stdout 是送給分類器的批次——無內文的不在裡面，stderr 說出來。"""
    from engine_b import leads

    store_path = tmp_path / "leads.json"
    store = leads.load(store_path)
    fake_6k = "https://www.sec.gov/Archives/edgar/data/1709048/000170904899999999/fake6k.htm"   # 不撞到真的存檔
    gfs, _ = leads.register(store, source="edgar:GFS", url=fake_6k, title="GFS 6-K filed 2026-10-14",
                            source_class="primary", form_type="6-K")
    tweet, _ = leads.register(store, source="x:someone", url="https://x.com/a/status/1", title="t",
                              raw_text="Coherent ships 6-inch InP", source_class="secondary")
    leads.save(store, store_path)
    result = subprocess.run(
        [sys.executable, "-m", "engine_b.cli", "--leads", str(store_path), "list", "--status", "pending",
         "--triage-batch", "--json", "--no-fetch"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert result.returncode == 0, result.stderr[-800:]
    batch = json.loads(result.stdout)
    assert [r["lead_id"] for r in batch] == [tweet]
    assert batch[0]["body_status"] == "raw_text"
    assert "無內文、不送分類 1 則" in result.stderr and gfs[:13] in result.stderr


def test_heartbeat_and_ledger_name_the_held_count() -> None:
    import crons.heartbeat as hb

    section = hb.build_queue(state_dir=None)
    line = next(l for l in section.lines if "未 triage" in l)
    assert "無內文" in line, line
    heartbeat = (ROOT / "crons" / "heartbeat.py").read_text(encoding="utf-8")
    assert "held_pending" in heartbeat and "lead_text.attach" not in heartbeat, "心跳只能用不連網的那一支"
