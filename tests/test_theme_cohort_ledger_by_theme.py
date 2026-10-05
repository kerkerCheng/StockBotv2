"""主題等權組 ledger 以題材認組、不以檔名認組（多主題等權組 S1，plan 2026-10-05-002，使用者 2026-10-06 選 A）。

事發（2026-10-05 盤點）：`slug()` 把非英數字一律換成 `_`——「電力」「散熱」都是 `__.jsonl`；先前 `current_cohorts` 以**檔案**為單位
挑現行組，兩組一建就寫進同一個檔、其中一組被安靜蓋掉（INV-3）。這裡斷言的是「兩組都還在」，不是函式會動（L13）。
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from alpha.providers.theme_cohorts import append_cohort_record, current_cohorts, ledger_path, read_cohort_records, slug
from alpha.theme_cohort import cohort_record


class _Registry:
    """嚴格解析的最小替身：組員的 ticker 都解析得到自己的 company_id。"""

    def has_company(self, company_id: str) -> bool:
        return company_id.startswith("co:")

    def company_id_for_ticker(self, ticker: str) -> str:
        return {"6501.T": "co:hitachi", "267260.KS": "co:hd_hyundai_electric", "3017.TW": "co:avc",
                "3653.TW": "co:jentech", "AXTI": "co:axt", "AAOI": "co:aaoi"}[ticker]


def _record(theme: str, members: list[tuple[str, str]], *, day: str = "2026-10-06") -> dict:
    spec = {"theme": theme, "reason": "測試", "excluded": [],
            "members": [{"ticker": t, "company_id": c, "reason": "組員"} for t, c in members]}
    return cohort_record(spec, pq2_ref=1, decided_on=date.fromisoformat(day),
                         created_at=datetime.fromisoformat(f"{day}T01:00:00+00:00").astimezone(timezone.utc))


POWER = [("6501.T", "co:hitachi"), ("267260.KS", "co:hd_hyundai_electric")]
COOLING = [("3017.TW", "co:avc"), ("3653.TW", "co:jentech")]


def test_two_themes_with_the_same_slug_get_their_own_files_and_both_stay_current(tmp_path: Path) -> None:
    """「電力」「散熱」的 slug 相同；照新規則各寫各的檔（slug＋題材雜湊），兩組都是現行組。

    變異：`ledger_path` 改回 `slug(theme).jsonl` → 兩筆寫進同一個檔；再配合以檔挑現行組 → 只剩一組，這條紅。"""
    assert slug("電力") == slug("散熱") == "__"
    power = append_cohort_record(_record("電力", POWER), directory=tmp_path, registry=_Registry())
    cooling = append_cohort_record(_record("散熱", COOLING), directory=tmp_path, registry=_Registry())
    assert power != cooling
    assert power.name == f"___{hashlib.sha1('電力'.encode('utf-8')).hexdigest()[:8]}.jsonl"
    cohorts, errors = current_cohorts(directory=tmp_path)
    assert errors == [] and sorted(c.theme for c in cohorts) == ["散熱", "電力"]
    assert [m.ticker for m in read_cohort_records("散熱", directory=tmp_path)[0][0].members] == ["3017.TW", "3653.TW"]


def test_an_old_collided_file_still_yields_one_current_cohort_per_theme(tmp_path: Path) -> None:
    """舊規則留下的碰撞檔（兩個題材擠在 `__.jsonl`）：以紀錄的 theme 分組，兩組都讀得到，不會有一組被蓋掉。

    變異：`current_cohorts` 改回「每個檔挑一份」→ 只回一組，這條紅。"""
    collided = tmp_path / "__.jsonl"
    collided.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                for r in (_record("電力", POWER), _record("散熱", COOLING))), encoding="utf-8")
    cohorts, errors = current_cohorts(directory=tmp_path)
    assert errors == [] and sorted(c.theme for c in cohorts) == ["散熱", "電力"]
    # 已經在碰撞檔裡的題材，之後的紀錄沿用那個檔（既有檔不搬）
    assert ledger_path("電力", directory=tmp_path) == collided


def test_an_existing_theme_keeps_its_file_and_a_supersede_stays_in_it(tmp_path: Path) -> None:
    """既有的光通訊 ledger（`AI_____CPO.jsonl`）不搬、不改名：同題材的新紀錄寫回同一個檔，現行組由最新那份勝出。"""
    existing = tmp_path / "AI_____CPO.jsonl"
    first = _record("AI 光互連／CPO", [("AXTI", "co:axt"), ("AAOI", "co:aaoi")], day="2026-10-04")
    existing.write_text(json.dumps(first, ensure_ascii=False) + "\n", encoding="utf-8")
    assert ledger_path("AI 光互連／CPO", directory=tmp_path) == existing
    second = _record("AI 光互連／CPO", [("AXTI", "co:axt"), ("AAOI", "co:aaoi")], day="2026-10-06")
    second = {**second, "supersedes_id": first["cohort_id"]}
    second = cohort_record({k: second[k] for k in ("theme", "members", "excluded", "reason", "supersedes_id")},
                           pq2_ref=2, decided_on=date(2026, 10, 6),
                           created_at=datetime(2026, 10, 6, 2, tzinfo=timezone.utc))
    assert append_cohort_record(second, directory=tmp_path, registry=_Registry()) == existing
    cohorts, _ = current_cohorts(directory=tmp_path)
    assert [c.cohort_id for c in cohorts] == [second["cohort_id"]]
    assert sorted(p.name for p in tmp_path.glob("*.jsonl")) == ["AI_____CPO.jsonl"]
