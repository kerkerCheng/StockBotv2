"""2026-09-10 的三個「機制只夠用一次」修復（L17）。

三者共同形狀：機制在當初那個案例上完美運作，遇到第二種形狀時**不會壞、不會報錯、
測試不會紅**，只會安靜地偏掉。詳見
`docs/solutions/architecture-patterns/mechanism-built-for-one-case.md`。
"""
from __future__ import annotations

import json

from crons.harvest_leads import filings_to_leads
from loader import extraction_index


def _write(directory, filename: str, doc_id: str) -> None:
    (directory / filename).write_text(
        json.dumps({"source_doc": {"doc_id": doc_id}, "nodes": [], "edges": []}),
        encoding="utf-8",
    )


def test_doc_id_is_not_the_filename(tmp_path) -> None:
    """實測：`cpo_chip_package_paper.json` 的 doc_id 是
    `Electronic_Chip_Package_and_CPO_Technology_for_Modern_AI_Era`。

    206 個 doc_id 中有 11 個的同名檔不存在——拼檔名會把它們全部誤報成「無稽核依據」，
    但依據存在（L15：gate 攔下的不是它想攔的東西）。
    """

    extraction_index.invalidate()
    _write(tmp_path, "totally_different_name.json", "Some_Very_Long_Doc_Id")

    assert extraction_index.exists("Some_Very_Long_Doc_Id", tmp_path)
    assert not (tmp_path / "Some_Very_Long_Doc_Id.json").exists()
    assert not extraction_index.exists("totally_different_name", tmp_path)


def test_one_doc_id_can_have_many_extractions(tmp_path) -> None:
    """addendum 慣例：全庫 229 份檔案只有 206 個 doc_id，21 組共用。

    用 `dict[str, Path]` 存索引會讓後掃到的覆蓋先掃到的，重載時就少一份 provenance
    ——而**漏掉不會有任何東西壞掉**（2026-09-10 實測 `tech:eml` 少了兩個 source）。
    """

    extraction_index.invalidate()
    _write(tmp_path, "a_main.json", "Shared_Doc")
    _write(tmp_path, "b_addendum.json", "Shared_Doc")
    _write(tmp_path, "c_other.json", "Other_Doc")

    paths = extraction_index.paths_for("Shared_Doc", tmp_path)
    assert [p.name for p in paths] == ["a_main.json", "b_addendum.json"]
    assert len(extraction_index.paths_for("Other_Doc", tmp_path)) == 1
    assert extraction_index.paths_for("nope", tmp_path) == ()


def test_same_day_filings_get_distinguishable_titles() -> None:
    """同日多份同型 filing 的標題必須互不相同。

    ⚠ 原本被誤診成「去重壞了」：2026-09-09 的 TSM Form 4 有三筆，看起來一模一樣。
    實測 accession 各不相同（去重鍵是 url，完全正確）——**問題在標題不足以區分**。
    這條測試同時鎖住那個誤診：去重不該為了讓標題好看而被改動。
    """

    rows = filings_to_leads("TSM", "1046179", [
        {"accession": "000104617926000656", "primary_doc": "a.xml",
         "form_type": "4", "filed_date": "2026-09-09"},
        {"accession": "000104617926000644", "primary_doc": "b.xml",
         "form_type": "4", "filed_date": "2026-09-09"},
        {"accession": "000104617926000648", "primary_doc": "c.xml",
         "form_type": "4", "filed_date": "2026-09-09"},
    ])

    titles = [r["title"] for r in rows]
    assert len(set(titles)) == 3, f"同日三份 filing 的標題應互異：{titles}"
    assert all("2026-09-09" in t and "TSM 4" in t for t in titles)
    # url 仍然是唯一去重鍵，三筆各異
    assert len({r["url"] for r in rows}) == 3
