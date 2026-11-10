"""私有文件索引（failure log #141；ROADMAP「私有券商報告建索引、讀某檔時列出點名它的報告」）。

兩個事發形狀要列得出來：AXTI ← 凱基 08-18 光通產業報告第 5、7 頁寫「AXT」（名冊名稱是「AXT, Inc.」、沒有別名——
靠去法律尾綴的核心名）；1519.TW ← 元大 09-11 產業報告第 25 頁「華城(1519 TT)」。守的事：名字比對走
`query.bottleneck.quote_names_company`（單字分大小寫、兩家共用的寫法不算）；台股另認券商的代號寫法、裸數字不算；
抽不出字的是「沒核」不是「沒點名」；增量重建；同一份檔放兩處只列一次；索引不抄內容。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sourcing import private_docs as pd

AXT = SimpleNamespace(company_id="co:axt", display_name="AXT, Inc.", name_aliases=(), research_ticker="AXTI")
COHERENT = SimpleNamespace(company_id="co:coherent", display_name="Coherent Corp.", name_aliases=(),
                           research_ticker="COHR")
FORTUNE = SimpleNamespace(company_id="co:fortune_electric", display_name="Fortune Electric Co., Ltd.",
                          name_aliases=("華城", "華城電機"), research_ticker="1519.TW")
VPEC = SimpleNamespace(company_id="co:visual_photonics", display_name="Visual Photonics Epitaxy",
                       name_aliases=("VPEC", "全新光電"), research_ticker="2455.TW")


class _Registry:
    def __init__(self, *companies):
        self.companies = tuple(companies)

    def has_company(self, company_id):
        return any(c.company_id == company_id for c in self.companies)

    def company_id_for_ticker(self, ticker):
        return next((c.company_id for c in self.companies if c.research_ticker == ticker), None)


REGISTRY = _Registry(AXT, COHERENT, FORTUNE, VPEC)


def _pages(*bodies: str) -> str:
    return "".join(f"=== PAGE {n} ===\n{body}\n" for n, body in enumerate(bodies, 1))


def _root(tmp_path: Path, files: dict[str, str | bytes]) -> Path:
    root = tmp_path / "broker_reports"
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            path.write_bytes(body)
        else:
            path.write_text(body, encoding="utf-8")
    return root


@pytest.fixture
def no_pdf(monkeypatch):
    """測試環境不產 PDF：PDF 那一支一律當讀不到，逼它退回同名文字檔（另有一條測 PDF 優先）。"""
    def broken(_path):
        raise ValueError("not a pdf")

    monkeypatch.setattr(pd, "_pdf_pages", broken)


# ---------------------------------------------------------------------------
# 找檔、分頁、檔名
# ---------------------------------------------------------------------------

def test_discover_pairs_pdf_and_txt_and_skips_other_files(tmp_path):
    root = _root(tmp_path, {"a/r1.pdf": b"%PDF", "a/r1.txt": "x", "a/r2.txt": "y", "a/list.csv": "c", "a/idx.md": "m"})
    found = [(doc.name, text.name if text else None) for doc, text, _r in pd.discover([root])]
    assert found == [("r1.pdf", "r1.txt"), ("r2.txt", "r2.txt")]


def test_pages_prefer_pdf_then_fall_back_to_the_sibling_text(tmp_path, monkeypatch):
    root = _root(tmp_path, {"r.pdf": b"%PDF", "r.txt": _pages("一", "二 AXT"), "plain.txt": "沒有分頁記號"})
    monkeypatch.setattr(pd, "_pdf_pages", lambda _p: [(1, "pdf 一"), (2, "pdf 二")])
    pages, why, source = pd.pages_of(root / "r.pdf", root / "r.txt")
    assert source == "pdf" and why is None and [n for n, _ in pages] == [1, 2]
    monkeypatch.setattr(pd, "_pdf_pages", lambda _p: [(1, "  "), (2, "")])       # 掃描檔：每頁都是空的
    pages, why, source = pd.pages_of(root / "r.pdf", root / "r.txt")
    assert source == "txt" and [n for n, _ in pages] == [1, 2] and "AXT" in pages[1][1]
    pages, why, source = pd.pages_of(root / "plain.txt", None)
    assert source == "txt" and pages == [(1, "沒有分頁記號")]


def test_unreadable_pdf_without_text_is_named_not_dropped(tmp_path, no_pdf):
    root = _root(tmp_path, {"scan.pdf": b"%PDF"})
    pages, why, source = pd.pages_of(root / "scan.pdf", None)
    assert pages is None and source is None and "PDF 讀不到" in why


def test_describe_reads_the_naming_convention_and_folder_dates():
    named = pd.describe(Path("x/2026-09-11_元大投顧_組裝及零組件產業_產業概況更新_中文.pdf"))
    assert named == {"date": "2026-09-11", "broker": "元大投顧", "title": "組裝及零組件產業_產業概況更新_中文",
                     "subject_code": None}
    company = pd.describe(Path("x/2026-06-18_凱基_高力-8996_動態更新_最後登機廣播_中文.pdf"))
    assert company["subject_code"] == "8996" and company["broker"] == "凱基"
    folder = pd.describe(Path("broker_reports/2026-08-18_kgi/kgi_20260818.pdf"))
    assert folder["date"] == "2026-08-18" and folder["broker"] == "kgi"
    loose = pd.describe(Path("inbox/memo_20261019.txt"))
    assert loose["date"] == "2026-10-19" and loose["broker"] is None


# ---------------------------------------------------------------------------
# 點名比對
# ---------------------------------------------------------------------------

def test_mentions_use_the_single_name_owner_and_broker_ticker_style():
    pages = [(1, "coherent optics demand"),                 # 普通名詞，不是 Coherent
             (2, "Coherent and AXT supply InP"),           # 單字名分大小寫；AXT 靠核心名（名冊名稱 AXT, Inc.）
             (3, "TAXT axt AXTX"),                         # 不是整字或大小寫不同
             (4, "全新(2455 TT)與華城(1519 TT)"),          # 券商的代號寫法；華城是別名
             (5, "2026 年營收 2455 億元")]                  # 裸數字不算
    hits = pd.mentions(pages, REGISTRY)
    assert hits == {"co:coherent": [2], "co:axt": [2], "co:visual_photonics": [4], "co:fortune_electric": [4]}


def test_a_form_shared_by_two_companies_names_neither():
    twin = SimpleNamespace(company_id="co:axt_dup", display_name="AXT Ltd.", name_aliases=(), research_ticker=None)
    hits = pd.mentions([(1, "AXT ships substrates")], _Registry(AXT, twin))
    assert hits == {}                                       # 不猜（L15）：核心名 AXT 兩家共用


def test_code_pattern_forms():
    pattern = pd.code_pattern("2455")
    for text in ("(2455 TT)", "（2455）", "(2455.TW)", "2455 TT", "2455.TW"):
        assert pattern.search(text), text
    for text in ("2455", "12455 TT", "2455 億元", "x2455.TWX"):
        assert not pattern.search(text), text


# ---------------------------------------------------------------------------
# 索引：增量、版本、讀不到、去重
# ---------------------------------------------------------------------------

def test_refresh_reuses_unchanged_docs_and_rescans_when_names_change(tmp_path, no_pdf, monkeypatch):
    root = _root(tmp_path, {"2026-08-18_kgi/kgi_20260818.pdf": b"%PDF",
                            "2026-08-18_kgi/kgi_20260818.txt": _pages("Coherent", "x", "y", "z", "AXT 基板", "w", "AXT")})
    index_path = tmp_path / "index.json"
    first = pd.refresh(roots=[root], index_path=index_path, registry=REGISTRY)
    doc = first["docs"][0]
    assert doc["mentions"] == {"co:coherent": [1], "co:axt": [5, 7]} and doc["text_from"] == "txt"
    assert doc["date"] == "2026-08-18" and doc["broker"] == "kgi" and doc["pages"] == 7
    calls = []
    real = pd.pages_of
    monkeypatch.setattr(pd, "pages_of", lambda *a: calls.append(a) or real(*a))
    pd.refresh(roots=[root], index_path=index_path, registry=REGISTRY)
    assert calls == []                                      # 指紋沒變、名冊沒變：沿用
    newcomer = SimpleNamespace(company_id="co:w", display_name="Widget Holdings", name_aliases=(), research_ticker=None)
    pd.refresh(roots=[root], index_path=index_path, registry=_Registry(AXT, COHERENT, newcomer))
    assert len(calls) == 1                                  # 名冊多了一家：回頭重掃舊報告
    stale = json.loads(index_path.read_text(encoding="utf-8"))
    stale["version"] = pd.INDEX_VERSION - 1
    index_path.write_text(json.dumps(stale), encoding="utf-8")
    pd.refresh(roots=[root], index_path=index_path, registry=_Registry(AXT, COHERENT, newcomer))
    assert len(calls) == 2                                  # 規則改了（版本號）：整份重掃


def test_index_keeps_no_content(tmp_path, no_pdf):
    root = _root(tmp_path, {"2026-09-11_元大投顧_產業_中文.txt": _pages("華城(1519 TT) 的客戶是 某某電力 交期 2027")})
    index_path = tmp_path / "index.json"
    pd.refresh(roots=[root], index_path=index_path, registry=REGISTRY)
    raw = index_path.read_text(encoding="utf-8")
    assert "某某電力" not in raw and "交期" not in raw      # 只有頁碼與指紋
    assert json.loads(raw)["docs"][0]["mentions"] == {"co:fortune_electric": [1]}


def test_docs_for_lists_once_per_file_newest_first_and_counts_unreadable(tmp_path, no_pdf):
    same = _pages("x", "AXT")
    root = _root(tmp_path, {"2026-08-18_kgi/kgi_20260818.txt": same,
                            "inbox_copy/2026-08-18_凱基_光通產業_中文.txt": same,
                            "2026-09-21_元大投顧_光通訊產業_中文.txt": _pages("AXT"),
                            "2026-06-18_凱基_高力-8996_動態更新_中文.txt": _pages("沒提到別家"),
                            "scan.pdf": b"%PDF"})
    index = pd.refresh(roots=[root], index_path=tmp_path / "i.json", registry=REGISTRY)
    docs = pd.docs_for(index, "co:axt")
    assert [d["date"] for d in docs] == ["2026-09-21", "2026-08-18"]
    assert len(docs[1]["also"]) == 1 and docs[1]["hit_pages"] == [2]
    text = "\n".join(pd.render("co:axt", "AXTI（co:axt）", docs, index))
    assert "第 2 頁（共 2 頁）" in text and "同一份另在" in text
    assert "抽不出字 1 份沒核（不是沒點名）" in text and "scan.pdf" in text


def test_subject_from_the_file_name_is_listed_even_without_a_text_hit(tmp_path, no_pdf):
    gcs = SimpleNamespace(company_id="co:kaori", display_name="Kaori Heat Treatment Co., Ltd.", name_aliases=(),
                          research_ticker="8996.TW")
    root = _root(tmp_path, {"2026-06-18_凱基_高力-8996_動態更新_中文.txt": _pages("最後登機廣播")})
    index = pd.refresh(roots=[root], index_path=tmp_path / "i.json", registry=_Registry(gcs))
    docs = pd.docs_for(index, "co:kaori")
    assert len(docs) == 1 and docs[0]["is_subject"] and docs[0]["hit_pages"] == []
    assert "內文沒點名（檔名主題）" in "\n".join(pd.render("co:kaori", "8996.TW", docs, index))


# ---------------------------------------------------------------------------
# 命令列
# ---------------------------------------------------------------------------

def test_cli_resolves_through_the_registry_and_refuses_unknown(tmp_path, no_pdf, monkeypatch, capsys):
    root = _root(tmp_path, {"2026-09-11_元大投顧_組裝及零組件產業_中文.txt": _pages(*(["x"] * 24), "華城(1519 TT)", "y")})
    monkeypatch.setattr(pd, "ROOTS", (root,))
    monkeypatch.setattr(pd, "INDEX_PATH", tmp_path / "i.json")
    monkeypatch.setattr("identity.registry.get_registry", lambda: REGISTRY)
    real_refresh = pd.refresh
    monkeypatch.setattr(pd, "refresh", lambda **kw: real_refresh(roots=(root,), index_path=tmp_path / "i.json", **kw))
    assert pd.main(["1519.TW"]) == 0
    out = capsys.readouterr().out
    assert "1519.TW（co:fortune_electric）：私有文件裡點名它的 1 份" in out and "第 25 頁（共 26 頁）" in out
    assert pd.main(["NOPE.TW", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert "名冊沒有" in captured.err and json.loads(captured.out)["_index"]["docs"] == 1
