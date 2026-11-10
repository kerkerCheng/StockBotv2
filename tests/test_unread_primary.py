"""換版收據：上一版之後進池、這一版沒指到的一手（failure log #32；plan 2026-11-10-001 G，使用者 11-10 選 A）。

守的事：①窗＝（上一版寫入，這一版寫入〕，用**進池**時間不用發布日（回補進來的舊文件要列）；撤回的那一版不算上一版；第一版不列但說出來；
②lead 只算一手、非持股申報、實體有這家；③「指到」認 id／網址／refs 的一手位置，EDGAR 另認自家庫檔名（節錄讀過算指到）；
④自家庫認點名這家（或 meta 是這家）、主檔名出現在紀錄裡算指到、非文字檔照數「沒核」；⑤最多 5 則、非例行的先、新到舊、截斷要說話；
⑥寫入端真的印它。"""
from __future__ import annotations

import inspect
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from alpha import cli
from alpha.providers import unread_primary as up

T0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 11, 9, tzinfo=timezone.utc)


def _brief(brief_id, day, *, retracted=False, supersedes=None):
    return SimpleNamespace(brief_id=brief_id, created_at=datetime(2026, 11, day, tzinfo=timezone.utc),
                           retracted=retracted, supersedes_id=supersedes)


def _lead(lead_id, *, seen, title="X 8-K filed 2026-11-05 [1]", company="co:x", klass="primary", form=None,
          url="https://example.com/a", published="2026-11-05", refs=None, entities=()):
    return {"lead_id": lead_id, "first_seen": seen, "title": title, "company_id": company, "source_class": klass,
            "form_type": form, "url": url, "published_at": published, "refs": refs or {}, "_entities": set(entities)}


def _unread(leads, blob="{}", company="co:x"):
    return up.unread_leads(company, T0, T1, blob, leads, ownership_forms=("4", "144"),
                           entities_of=lambda lead: lead["_entities"],
                           category_of=lambda lead: {"category": lead.get("_category")} if lead.get("_category") else None,
                           routine=frozenset({"attention_trading"}))


# ---- ① 上一版是哪一版 -----------------------------------------------------------------------------------------------

def test_previous_version_skips_retractions_and_the_retracted_one() -> None:
    records = [_brief("ib_a", 1), _brief("ib_b", 3), _brief("ib_r", 4, retracted=True, supersedes="ib_b"), _brief("ib_c", 5)]
    assert up.previous_written_at(records, "ib_c") == datetime(2026, 11, 1, tzinfo=timezone.utc)   # ib_b 被撤回了
    assert up.previous_written_at(records, "ib_a") is None                                         # 第一版
    assert up.previous_written_at(records, "ib_missing") is None


# ---- ② lead：一手、非持股申報、實體有這家、進池時間在窗內 ------------------------------------------------------------

def test_leads_in_window_are_by_entry_time_not_publication() -> None:
    leads = {
        "keep": _lead("keep", seen="2026-11-07T00:00:00+00:00"),
        "old_but_new_in_pool": _lead("old_but_new_in_pool", seen="2026-11-08T00:00:00+00:00", published="2026-07-01"),
        "before": _lead("before", seen="2026-10-31T23:59:00+00:00"),
        "after": _lead("after", seen="2026-11-09T00:00:01+00:00"),
        "secondary": _lead("secondary", seen="2026-11-07T00:00:00+00:00", klass="secondary"),
        "form4": _lead("form4", seen="2026-11-07T00:00:00+00:00", form="4"),
        "other": _lead("other", seen="2026-11-07T00:00:00+00:00", company="co:y"),
        "named": _lead("named", seen="2026-11-07T00:00:00+00:00", company="co:y", entities=("co:x",)),
    }
    items, counts = _unread(leads)
    assert sorted(item.pointer for item in items) == ["keep", "named", "old_but_new_in_pool"]
    assert counts == {"window": 3, "pointed": 0}


# ---- ③ 指到 ---------------------------------------------------------------------------------------------------------

def test_pointed_by_id_url_refs_or_the_excerpt_file_name() -> None:
    seen = "2026-11-07T00:00:00+00:00"
    leads = {
        "by_url": _lead("by_url", seen=seen, url="https://www.sec.gov/x/8k.htm"),
        "by_ref": _lead("by_ref", seen=seen, refs={"mops_history_query": "ajax_t05st01（POST step=2&seq_no=1）"}),
        "by_excerpt": _lead("by_excerpt", seen=seen, title="PSIX 8-K filed 2026-08-06 [054346]"),
        "by_quarter": _lead("by_quarter", seen=seen, title="BW 10-Q filed 2026-08-10 [000068]"),
        "by_fiscal_year": _lead("by_fiscal_year", seen=seen, title="CECO 10-K filed 2026-03-02 [1]"),
        "not_pointed": _lead("not_pointed", seen=seen, title="PSIX 8-K filed 2026-09-30 [408371]"),
    }
    blob = ('{"refs": ["https://www.sec.gov/x/8k.htm", "ajax_t05st01（POST step=2&seq_no=1）", '
            '"library/raw/psix_8k_20260806_q2_release_excerpt.txt", "library/raw/bw_10q_2026q2_backlog.txt", '
            '"library/raw/ceco_10k_fy2025_products.txt"]}')
    items, counts = _unread(leads, blob)
    assert [item.pointer for item in items] == ["not_pointed"]
    assert counts == {"window": 6, "pointed": 5}


# ---- ④ 自家庫 --------------------------------------------------------------------------------------------------------

def _touch(path: Path, text: str, when: datetime) -> None:
    path.write_text(text, encoding="utf-8")
    os.utime(path, (when.timestamp(), when.timestamp()))


def test_raw_files_naming_the_company_in_window(tmp_path: Path) -> None:
    inside = T0 + timedelta(days=3)
    _touch(tmp_path / "gxo_expansion_names_it.txt", "GXO signed with Acme for ...", inside)
    _touch(tmp_path / "acme_8k_20261105_excerpt.txt", "Acme 8-K excerpt", inside)          # 這一版引用了 → 指到
    _touch(tmp_path / "unrelated.txt", "nothing here", inside)
    _touch(tmp_path / "old_names_it.txt", "Acme older", T0 - timedelta(days=1))
    _touch(tmp_path / "acme_filing.txt", "no name in text", inside)
    (tmp_path / "acme_filing.meta.json").write_text('{"ticker": "ACME"}', encoding="utf-8")   # meta 說是這家
    _touch(tmp_path / "deck.pdf", "%PDF", inside)
    items, counts = up.unread_raw("ACME", T0, T1, '"library/raw/acme_8k_20261105_excerpt.txt"', raw_dir=tmp_path,
                                  names=lambda text: "Acme" in text)
    assert sorted(item.pointer for item in items) == ["library/raw/acme_filing.txt", "library/raw/gxo_expansion_names_it.txt"]
    assert counts == {"window": 3, "pointed": 1, "unchecked": 1}


# ---- ⑤ 排序、截斷、收據行 ---------------------------------------------------------------------------------------------

def test_real_registry_names_and_receipt_order_and_truncation(tmp_path: Path) -> None:
    seen = "2026-11-07T00:00:00+00:00"
    leads = {f"l{i}": _lead(f"l{i}", seen=seen, company="co:co_tech", published=f"2026-11-0{i}",
                            title=f"8358.TWO 金居 重訊 2026-11-0{i}：第 {i} 則") for i in range(1, 7)}
    for lead in leads.values():
        lead["source"] = "mops:8358.TWO"                       # 例行類別只認重訊（engine_b.announcement_category）
    leads["l6"]["title"] = "8358.TWO 金居 重訊 2026-11-06：本公司有價證券達公布注意交易資訊標準"   # 例行 → 排最後
    _touch(tmp_path / "customer_names_co_tech.txt", "供應商金居開發的 HVLP 銅箔", T0 + timedelta(days=2))
    record = {"brief_id": "ib_new", "company_id": "co:co_tech", "ticker": "8358.TWO", "created_at": T1.isoformat(),
              "slots": []}
    result = up.unread_primary(record, T0, leads=leads, raw_dir=tmp_path)
    assert [item.pointer for item in result["items"]] == ["l5", "l4", "l3", "customer_names_co_tech.txt".join(
        ["library/raw/", ""]), "l2"]
    assert result["more"] == 2 and result["routine_more"] == 1
    lines = up.receipt_lines(result)
    assert lines[0].startswith("  一手：上一版（2026-11-01）之後進池、這一版沒指到的 7 則（窗內 lead 6、指到 0；自家庫點名它的 1、指到 0）")
    assert lines[-1] == "    另有 2 則沒列（其中例行重訊 1）"
    assert "（點名這家公司）" in lines[4]
    assert up.receipt_lines(up.unread_primary(record, None, leads=leads, raw_dir=tmp_path)) == [
        "  一手（上一版之後進池）：這是第一版，沒有上一版可比——不列"]
    quiet = up.unread_primary(record, T0, leads={}, raw_dir=tmp_path / "missing")
    assert up.receipt_lines(quiet) == [
        "  一手：上一版（2026-11-01）之後進池、這一版沒指到的 0 則（窗內 lead 0、指到 0；自家庫點名它的 0、指到 0）"]


# ---- ⑥ 寫入端真的印 --------------------------------------------------------------------------------------------------

def test_the_write_path_prints_the_receipt() -> None:
    source = inspect.getsource(cli.cmd_brief)
    assert "receipt_lines(unread_primary(record, previous))" in source
    assert "previous_written_at(read_brief_records(ticker)[0]" in source
