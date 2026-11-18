"""偵探第一版（`skills/detective/SKILL.md`）：純邏輯的角色、日期、清理、問句、派工提示、核引文，與 provider 的選檔計數。

驗收句住 ROADMAP「偵探：計畫外線索組裝」；M0 的設計與結果在 `docs/reports/phase7/detective-m0-2026-11-18.md`。
"""
from __future__ import annotations

from datetime import date

from alpha.cli import build_parser
from alpha.detective import (
    DRAWERS, DocInfo, Neighbor, build_questions, doc_date, has_our_header, neighbors_from_rows, render_prompt,
    role_of, sanitize_excerpt, verify_report,
)
from alpha.providers.detective import SECOND_HOP_PER_COMPANY, _select, listed_files


# ---- 角色 ---------------------------------------------------------------------------------------
def test_role_of_one_hop_layer_and_second_hop() -> None:
    assert role_of("SUPPLIES_TO", True, None) == "customer"
    assert role_of("SUPPLIES_TO", False, None) == "supplier"
    assert role_of("COMPETES_WITH", False, None) == "competitor"
    assert role_of("INVESTS_IN", True, None) == "other"
    assert role_of("SUPPLIES_TO", True, "mat:inp_substrate") == "layer_peer"
    assert role_of("DEPENDS_ON", True, "mat:inp_substrate") == "layer_buyer"
    # M0：價格線索的 AOI 是同層對手雲南鍺業的客戶——第二跳
    assert role_of("SUPPLIES_TO", True, "co:yunnan_germanium", hop=2) == "rival_customer"


def test_neighbors_merge_roles_and_skip_target() -> None:
    rows = [
        {"rel": "SUPPLIES_TO", "out": True, "nid": "co:lumentum", "name": "Lumentum", "via": None},
        {"rel": "DEPENDS_ON", "out": True, "nid": "co:lumentum", "name": "Lumentum", "via": "mat:inp_substrate"},
        {"rel": "SUPPLIES_TO", "out": True, "nid": "co:lumentum", "name": "Lumentum", "via": "co:sumitomo_electric",
         "hop": 2},
        {"rel": "SUPPLIES_TO", "out": True, "nid": "co:aoi", "name": "AOI", "via": "co:yunnan_germanium", "hop": 2},
        {"rel": "SUPPLIES_TO", "out": True, "nid": "co:axt", "name": "AXT", "via": None},     # 目標自己
    ]
    nbs = neighbors_from_rows("co:axt", rows)
    assert [n.company_id for n in nbs] == ["co:lumentum", "co:aoi"]       # 客戶先、只是對手的客戶的後
    lite = nbs[0]
    assert lite.roles == {"customer", "layer_buyer", "rival_customer"}
    assert lite.role_text() == "客戶、同層買方、對手的客戶"
    assert lite.vias == {"mat:inp_substrate", "co:sumitomo_electric"}


# ---- 日期（INV-6）-------------------------------------------------------------------------------
def test_doc_date_precedence_meta_header_filename_top_lines() -> None:
    head = "SOURCE: x\nPUBLISHED: 2026-07-02\n"
    assert doc_date("a_20260801.txt", head, {"published_at": "2026-05-08", "retrieved_at": "2026-10-06"}) \
        == date(2026, 5, 8)
    assert doc_date("a_20260801.txt", head, {"filed_date": "2026-08-11"}) == date(2026, 8, 11)
    assert doc_date("a_20260801.txt", head) == date(2026, 7, 2)
    assert doc_date("a_20260801.txt", "") == date(2026, 8, 1)
    # 不拿 retrieved_at 冒充發布日
    assert doc_date("a.txt", "", {"retrieved_at": "2026-10-06"}) is None


def test_doc_date_skips_invalid_filename_date() -> None:
    # 「fy2026_20260817」先撞到「2026_20…」（20 月不合法）——跳過找下一個
    assert doc_date("vpec_fy2026_20260817.txt", "") == date(2026, 8, 17)


def test_doc_date_top_lines_take_latest_never_earliest() -> None:
    head = "來源：AAOI Form 10-Q，季度截至 2026-09-30，2026-11-05 申報，節錄（2026-11-06 取得）。\n正文\n2027-01-01 起"
    # 取第一個（季度截止日）會讓回溯包收進回溯日之後才申報的檔；取最晚只會偏晚
    assert doc_date("aaoi_10q_q3_2026_excerpt.txt", head) == date(2026, 11, 6)
    assert doc_date("annual_report_2025.txt", "沒有日期\n") is None


# ---- 回溯包的清理 -------------------------------------------------------------------------------
def test_has_our_header_recognizes_all_excerpt_shapes() -> None:
    assert has_our_header("SOURCE: x\n")
    assert has_our_header("Source URL: https://x\n\nExcerpt:\n")
    assert has_our_header("來源：Applied Optoelectronics 10-Q\n")
    assert has_our_header("Published: 2026-08-27 | Origin: IREN Ltd | Retrieved: 2026-10-04\n")
    assert not has_our_header("aaoi20251231_10k.htm\n0001158114\nAPPLIED OPTOELECTRONICS, INC.\n")


def test_sanitize_drops_our_notes_and_later_dates() -> None:
    text = "\n".join([
        "SOURCE: AXT 8-K",
        "NOTE: 我們 2026-10-30 補的註",
        "RETRIEVED: 2026-10-06",
        "原文：the agreement runs through 2026-08-31.",
        "原文：shipments begin 2026-10-01.",            # 回溯日之後的日期（分不出原文或我們補的，保守拿掉）
        "推一步：這代表漲價",
        "2026年11月 的事",
        "11-12 法說會",
        "[2026-10-04 追加——更正走廊]",
        "(re-verified against the live page 2026-10-03)",
        "保留這一行",
    ])
    out, dropped = sanitize_excerpt(text, date(2026, 9, 7))
    assert out.splitlines() == ["SOURCE: AXT 8-K", "原文：the agreement runs through 2026-08-31.", "保留這一行"]
    assert dropped == 8


# ---- 選檔：每一步丟掉的都數出來（INV-3）-------------------------------------------------------
def _doc(name: str, day: date | None, *named: str) -> DocInfo:
    return DocInfo(name=name, published=day, named=tuple(named))


def test_select_counts_exclusions_and_orders_target_first() -> None:
    docs = [
        _doc("old_peer.txt", date(2026, 3, 1), "co:peer"),
        _doc("target.txt", date(2026, 1, 1), "co:axt"),
        _doc("undated.txt", None, "co:axt"),
        _doc("late.txt", date(2026, 10, 1), "co:axt"),
        _doc("both.txt", date(2026, 2, 1), "co:peer", "co:lumentum"),
    ]
    keep, counts = _select(docs, "co:axt", date(2026, 9, 7))
    assert [d.name for d in keep] == ["target.txt", "both.txt", "old_peer.txt"]
    assert counts == {"named": 5, "undated": 1, "after_as_of": 1, "second_hop_capped": 0, "truncated": 0}
    # 現況（沒有回溯日）不排除日期不明與晚的
    keep_now, counts_now = _select(docs, "co:axt", None)
    assert len(keep_now) == 5 and counts_now["undated"] == counts_now["after_as_of"] == 0


def test_select_caps_second_hop_only_docs_per_company_and_sorts_them_last() -> None:
    hub = [_doc(f"nvda_{i:02d}.txt", date(2026, 1, 1 + i), "co:nvidia") for i in range(SECOND_HOP_PER_COMPANY + 3)]
    shared = _doc("nvda_and_axt.txt", date(2025, 1, 1), "co:nvidia", "co:axt")    # 也點名目標：不受上限
    peer = _doc("peer.txt", date(2025, 6, 1), "co:peer")
    keep, counts = _select([*hub, shared, peer], "co:axt", None, frozenset({"co:nvidia"}))
    assert counts["second_hop_capped"] == 3
    names = [d.name for d in keep]
    assert names[:2] == ["nvda_and_axt.txt", "peer.txt"]
    assert "nvda_00.txt" not in names and f"nvda_{SECOND_HOP_PER_COMPANY + 2:02d}.txt" in names   # 留最新的


# ---- 問句 ---------------------------------------------------------------------------------------
def test_questions_per_role_holes_and_fixed_three() -> None:
    nbs = [
        Neighbor("co:lumentum", "Lumentum", {"customer"}),
        Neighbor("co:jx", "JX", {"layer_peer"}),
        Neighbor("co:aixtron", "AIXTRON", {"supplier"}),
        Neighbor("co:aoi", "AOI", {"rival_customer"}, {"co:yunnan_germanium"}),
        Neighbor("co:fund", "Fund", {"other"}),
    ]
    docs = {"co:lumentum": [_doc("lite.txt", date(2026, 8, 11), "co:lumentum")]}
    qs = build_questions("AXT", nbs, docs, ["會計期末 2027-12-31 營收共識 5.10 億"], with_narrative=True)
    assert qs[0].startswith("共識：會計期末 2027-12-31") and "量級②" in qs[0]
    assert len(qs) == 1 + 5 + 3
    joined = "\n".join(qs)
    assert "庫裡 1 份點名它的文件，最新 2026-08-11" in joined
    assert joined.count("庫裡 0 份點名它的文件——這個洞本身就是線索") == 4      # 沒有文件也問（INV-3）
    assert "單價" in qs[2] and "對手的客戶 AOI" in qs[4]
    no_cons = build_questions("AXT", [], {}, [], with_narrative=False)
    assert no_cons[0].startswith("共識：沒有資料") and len(no_cons) == 4


# ---- 派工提示：鐵則都在 -------------------------------------------------------------------------
def test_prompt_carries_the_iron_rules() -> None:
    prompt = render_prompt(company="AXT", ticker="AXTI", read_scope="MANIFEST 列的檔", materials="- 材料",
                           questions=["q1", "q2"], as_of=date(2026, 9, 7))
    for must in ("只能讀這個線索包列出的檔案", "不得帶 email", "不看價格與市場資料", "library/private/engine_c",
                 "檔名:行號", "推一步", "不給目標價", "2026-09-07", "不要用你自己對 2026-09-07 之後的任何記憶",
                 "Q1 q1", "Q2 q2", "窗口提早關至少 1 條"):
        assert must in prompt, must
    assert all(d in prompt for d in DRAWERS)
    now = render_prompt(company="AXT", ticker="AXTI", read_scope="x", materials="", questions=[], as_of=None)
    assert "之後的任何記憶" not in now


# ---- 核引文 -------------------------------------------------------------------------------------
def test_verify_report_statuses() -> None:
    files = {"a.txt": ["line one", "the price was raised", "line three"], "b.txt": ["其他"]}
    report = "\n".join([
        "- 觀察：「the price was raised」（a.txt:2）",
        "- 觀察：「the price was raised」（a.txt:40）",
        "- 觀察：「the price was cut today」（a.txt:2）",
        "- 觀察：「anything at all here」（missing.txt:1）",
        "- 推論：沒有引號的 a.txt:3 不核",
    ])
    checks = verify_report(report, lambda name: files.get(name))
    assert [c.status for c in checks] == ["ok", "line_off", "missing", "no_file"]


def test_verify_report_flags_files_outside_the_pack(tmp_path) -> None:
    (tmp_path / "MANIFEST.md").write_text(
        "# 線索包\n\n- 鄰居 1 家\n\n## 文件\n- library/raw/a.txt（2026-01-01｜X）\n", encoding="utf-8")
    (tmp_path / "PROMPT.md").write_text(
        "- 讀圖：library/private/alpha/structure_readings/mat_x.jsonl 裡 reading_id = r 那一列\n", encoding="utf-8")
    allowed = listed_files(tmp_path)
    assert allowed is not None and {"a.txt", "mat_x.jsonl"} <= allowed and "nikkei.txt" not in allowed
    files = {"a.txt": ["the price was raised"], "nikkei.txt": ["住友電工が増産する計画"]}
    report = "「the price was raised」（a.txt:1）\n「住友電工が増産する計画」（nikkei.txt:1）"
    checks = verify_report(report, lambda n: files.get(n), allowed)
    assert [(c.status, c.in_manifest) for c in checks] == [("ok", True), ("ok", False)]
    assert listed_files(tmp_path / "nope") is None
    assert verify_report(report, lambda n: files.get(n))[0].in_manifest is None     # 沒給清單不判


def test_verify_report_ellipsis_parts_and_whitespace() -> None:
    files = {"c.txt": ["We are currently in", "discussions with other customers", "to form similar agreements"]}
    report = "「We are currently in discussions…to form similar agreements」（c.txt:2）"
    assert [c.status for c in verify_report(report, lambda n: files.get(n))] == ["ok"]


# ---- CLI 接上了 ---------------------------------------------------------------------------------
def test_cli_has_detective_pack_and_verify() -> None:
    parser = build_parser()
    args = parser.parse_args(["detective", "pack", "AXTI", "--as-of", "2026-09-07"])
    assert args.action == "pack" and args.ticker == "AXTI" and args.as_of == "2026-09-07"
    args = parser.parse_args(["detective", "verify", "REPORT.md", "--pack", "p"])
    assert args.action == "verify" and args.report == "REPORT.md" and args.pack == "p"
