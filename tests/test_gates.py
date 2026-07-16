"""Quality gates beyond file-existence checks."""

from __future__ import annotations

from pathlib import Path

from thesis.preconditions import _check_financial_checklist, _check_second_slice


def _root(tmp_path: Path) -> Path:
    (tmp_path / "thesis").mkdir()
    plan = tmp_path / "docs" / "plans" / "2026-07-08-005-feat-second-vertical-slice-plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# Second slice plan\n", encoding="utf-8")
    return tmp_path


def _write_memo(root: Path, content: str) -> Path:
    path = root / "thesis" / "amat_draft_lane_memo.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_scoring(root: Path, *, total: int = 24, credibility: int = 4,
                   falsifiability: int = 4, variant: int = 3) -> Path:
    path = root / "thesis" / "amat_draft_scoring.md"
    path.write_text(
        "\n".join(
            [
                "| 維度 | 分數 |",
                "|---|---|",
                f"| 可信度 | {credibility}/5 |",
                f"| 可證偽性 | {falsifiability}/5 |",
                f"| 市場差異度 | {variant}/5 |",
                f"| **總分** | **{total}/30** |",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_filename_only_draft_does_not_complete_second_slice(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write_memo(root, "# AMAT draft\n")

    result = _check_second_slice(root=root)

    assert result["ok"] is False
    assert "Variant Perception" in result["detail"]


def test_variant_without_corresponding_scoring_still_fails(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write_memo(
        root,
        "# AMAT memo\n## Variant Perception\n市場信成熟製程低成長，本 thesis 認為服務收入更穩定，催化劑是訂單回升。\n",
    )

    result = _check_second_slice(root=root)

    assert result["ok"] is False
    assert "scoring" in result["detail"].lower()


def test_second_slice_requires_scoring_above_every_failure_threshold(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write_memo(
        root,
        "# AMAT memo\n## Variant Perception\n市場信成熟製程低成長，本 thesis 認為服務收入更穩定，催化劑是訂單回升。\n",
    )
    _write_scoring(root, total=24, credibility=4, falsifiability=4, variant=3)

    assert _check_second_slice(root=root)["ok"] is True

    _write_scoring(root, total=24, credibility=2, falsifiability=4, variant=3)
    failed = _check_second_slice(root=root)
    assert failed["ok"] is False
    assert "可信度" in failed["detail"]


def test_financial_gate_rejects_manual_required_for_requested_ticker(monkeypatch) -> None:
    def fake_checklist(ticker: str) -> dict:
        return {
            "ticker": ticker,
            "engine_c_available": True,
            "gate_pass": False,
            "items": {
                "gross_margin_trend": {"status": "ok", "label": "毛利率趨勢"},
                "customer_concentration": {
                    "status": "manual_required",
                    "label": "客戶集中度",
                },
                "backlog": {"status": "manual_reviewed", "label": "Backlog"},
                "dilution": {"status": "ok", "label": "稀釋"},
                "valuation_pressure": {"status": "ok", "label": "估值壓力"},
            },
        }

    monkeypatch.setattr("engine_c.checklist.get_checklist", fake_checklist)

    result = _check_financial_checklist("SIVE.ST")

    assert result["ok"] is False
    assert "SIVE.ST" in result["detail"]
    assert "manual_required" in result["detail"]
    assert "倉位數字" in result["action"]


def test_financial_gate_passes_only_when_all_five_items_complete(monkeypatch) -> None:
    items = {
        key: {"status": "ok", "label": key}
        for key in ("gross_margin", "customer", "backlog", "dilution", "valuation")
    }
    monkeypatch.setattr(
        "engine_c.checklist.get_checklist",
        lambda ticker: {
            "ticker": ticker,
            "engine_c_available": True,
            "gate_pass": True,
            "items": items,
        },
    )

    result = _check_financial_checklist("SIVE.ST")

    assert result["ok"] is True
    assert "SIVE.ST" in result["detail"]
