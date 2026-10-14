"""
migrate_manual_relations_20261014.py — 取代鏈 A 的一次性遷移：14 組同期多筆生效的處置（2026-10-14，使用者選 A）。

**manifest（逐組寫死、可稽核）**：
- mechanical 的 10 組直接寫取代關係（`engine_c.manual_observations.append_relation`）——不需 pq2；
- 判斷欄位的 4 組只建**提案**（`engine_c.pending_observations.propose_relation`）——`python -m engine_b.todo sync` 鑄號、
  使用者 go 之後 `todo complete-observation` 才寫（Engine C 判讀寫入 gate）。

**前置**：本機備份＋還原驗證（`python scripts/backup_private.py run --no-drive` → `verify-restore`；本次 20261014T072251Z）。
**對帳**：寫之前、之後各 dump 一次 `manual_observations`（逐列內容雜湊）——**一列都不得變、不得多、不得少**；印每一組
寫之前／之後的生效筆數、`manual_fields` 投影勝出者有變的 (ticker, 欄位)；manifest 與對帳結果寫到
`library/private/migrations/20261014_manual_relations/`（私有、不進 git）。

預設只驗證、不寫（每一組先過 `check_relation`，任何一組不過就整批不寫）；`--apply` 才寫。重跑冪等（關係與提案都是內容定址）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "library" / "private" / "migrations" / "20261014_manual_relations"
BACKUP = ROOT / "library" / "private" / "backups" / "20261014T072251Z"
AUTHOR = "session（取代鏈 A 遷移 2026-10-14）"

#: (ticker, 欄位, 期間, 留下的那一筆, [被它取代的], 理由)
MECHANICAL = [
    ("000660.KS", "fiscal_year_results", "2025-12-31", "mo_a637d7e549ce9dc7805486a4192679a1",
     ["mo_108f3394c3fd41bd24f95cc64a3668c9"],
     "DART 2025 사업보고서（審計後，2026-03-17 申報）取代 2026-01-28 業績新聞稿的四捨五入數；同一年度同一口徑"),
    ("AVGO", "fiscal_year_results", "2025-11-02", "mo_eb59c56c8212f493767748bb7d5ba380",
     ["mo_dc75285e003142778b7fc8cf50b5eecc"],
     "完整版（FY2025 業績新聞稿，多稅前、EPS 等欄位）取代 xbrl_backfill 只有營收與營業利益的最小組合；兩筆數字相同"),
    ("AXTI", "fiscal_year_results", "2025-12-31", "mo_4f6f6c632fceb02cdd000835a8e38cb9",
     ["mo_965211d8d53580a8dd8e002a87cad371"],
     "完整版（FY2025 業績新聞稿）取代 xbrl_backfill 的最小組合；兩筆數字相同"),
    ("AXTI", "runway_inputs", "2026-06-30", "mo_eb08f615f2d2b433771fd0c988a8cb46",
     ["mo_45b3924521bf252b59a592635227e7dd"],
     "被取代的那筆是閘門端到端驗證用的重複列（它自己的 note：內容同 mo_eb08f615，僅測試提案路徑），不是觀測"),
    ("CRWV", "fiscal_year_results", "2025-12-31", "mo_d1954c6c2ba7439bd33ee11644f2754e",
     ["mo_cd2f00f4b00e571e9a52427e9f9a3fcb"],
     "留下的那筆出處自己寫「更正版（補上 supersedes 連結）」——更正的意圖在，連結沒接上"),
    ("GFS", "fiscal_year_results", "2025-12-31", "mo_aa58866cf2cf302b8afbd37c9402acda",
     ["mo_1ac638f78cb80e749f01bc7e3e6cdf83"],
     "完整版（FY2025 業績新聞稿）取代 xbrl_backfill 的最小組合；兩筆數字相同"),
    ("LITE", "fiscal_year_results", "2026-06-27", "mo_72b0cdf703f205898643e632b1b4a9cd",
     ["mo_b1318cb0f4b79e838a5e8d8b2392b048", "mo_151f12aeac37f77cba64446195df710d"],
     "同一個 session 12 分鐘內連寫三版（15:13 → 15:22 補 non-GAAP 與 operating_income → 15:25 再補鍵名說明）；最後一版是前兩版的超集"),
    ("SOI.PA", "segment_revenue_share", "2026-03-31", "mo_cef1e3246a04256490a324cfaf0c170b",
     ["mo_9e7d365382f29b842a52103db7e69442"],
     "留下的那筆出處自己寫「CORRECTION（supersedes mo_9e7d…）：前一筆把 Automotive & Industrial 寫成 0.1165」——連結沒接上"),
    ("TSEM", "fiscal_year_results", "2025-12-31", "mo_1b42ee5ebf1c51d8ded1bae816cd4579",
     ["mo_d4d1994f9acc37a82e898812e419303a"],
     "完整版（FY2025 業績新聞稿）取代 xbrl_backfill 的最小組合；兩筆數字相同"),
    ("TSM", "fiscal_year_results", "2025-12-31", "mo_93e4d882cbf14968268e3360bf48ca8b",
     ["mo_70d1fdd458fb22776e6a0047c3a5b4d7"],
     "留下的那筆 coverage_note 自己寫「本筆 supersede mo_70d1…（同日先以 TWD 記錄），改記 USD 的理由是單位一致性」"
     "（共識 EPS 是每 ADS 美元、價格是 ADR 美元價）——連結沒接上。ROADMAP 原寫「記並存」，查原文後改照原文記取代"),
]

#: 判斷欄位：(ticker, 欄位, 期間, 建議留下的, [建議被取代的], 關係理由, 給使用者的建議)
JUDGMENT = [
    ("LYC.AX", "backlog", "2026-03-10", "mo_648002a09f0afabc83becc5ae356ee69", ["mo_e2014c1e4de771c672ab8856e9c27fa4"],
     "逐字引文版取代摘要版：摘要把「上限 7,200 噸」寫得像確定承諾，原文那一段是視供給而定（no opportunity loss），不是 firm",
     "go：留逐字版——它分得清 firm 承諾（每年 5,000 噸）與視供給而定的上限（7,200 噸），摘要版寫成「上限 7,200t」會被讀成確定量；"
     "反方向（留摘要版）也合理的話是它短、是 9/1 核准的那一版"),
    ("LYC.AX", "customer_concentration", "2026-06-30", "mo_dba7cb80a2af28c45e570b2ca6a45a81", ["mo_8e64e174c7e22f63ff3ee3b118c348d4"],
     "較完整的版本取代簡版：用銷量算日本承諾占 68%（簡版用產量），加了重稀土 50% 承諾與年報 p.115 的優先供應條款",
     "go：留較完整的版本；⚠ 它裡面「美國國防部 LOI 約占營收 2.5%／年」等於美元金額直接除以澳幣營收（US$24M÷A$977.9M＝2.45%），"
     "看起來沒換匯——本機沒有澳幣匯率可核對，要更正請另外寫一筆觀測（研究動作，不在這個號裡）"),
    ("META", "backlog", "2026-07-01", "mo_aedf9e488b3a212d8a44e05718cfda23", ["mo_5cc20c1aba2ede09f7a14fcd3bc16b8f"],
     "錯字更正：前一筆把 US$349.31B 寫成 US-349.31B，其餘一字不差",
     "go：兩筆只差一個錯字（US- → US$），留更正後的那筆"),
    ("MP", "customer_concentration", "2025-12-31", "mo_eab62d81412844210a05548f5c365ccb", ["mo_ca7ad8b4bd9c6caa23ee23bb2059bcaa"],
     "文字版取代 JSON 版：文字版涵蓋 JSON 的每一個數（30%、23%、31%、合計 84%），另有 FY2023–24 的趨勢與成因，"
     "也已寫明三家未具名、Shenghe 那一句是推論",
     "go：留文字版——它多了 FY2023 單一客戶 96% → FY2024 98% → FY2025 84% 的趨勢與停止對中國銷售的成因；"
     "JSON 版只多一條「Customer C 的 31% 分母是公司總營收」的註記，文字版的「占總營收」已說清楚"),
]


def _dump(conn) -> dict[str, str]:
    rows = conn.execute("SELECT observation_id, ticker, field_name, value, source_ref, as_of, author, supersedes_id, "
                        "recorded_at, payload_digest FROM manual_observations ORDER BY observation_id").fetchall()
    return {str(r[0]): hashlib.sha256(json.dumps([str(x) for x in r], ensure_ascii=False).encode()).hexdigest() for r in rows}


def _projection(conn) -> dict[str, list[str]]:
    return {f"{t}|{f}": [str(v)[:60], str(s)[:60], str(u)] for t, f, v, s, u in conn.execute(
        "SELECT ticker, field_name, value, source_note, updated_at FROM manual_fields").fetchall()}


def _check_groups(conn) -> list[str]:
    """每一組的 id 都要真的在那個 (ticker, 欄位, 期間)、現在都生效——對不上就整批不寫。"""
    from engine_c.manual_observations import live_observation_ids

    problems = []
    for ticker, field, day, keep, closes, *_rest in MECHANICAL + JUDGMENT:
        live = set(live_observation_ids(conn, ticker, field, day))
        missing = [i for i in [keep, *closes] if i not in live]
        if missing:
            problems.append(f"{ticker}／{field}／{day}：{missing} 不是這一組現在生效的列（生效的是 {sorted(live)}）")
    return problems


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="取代鏈 A 的一次性遷移（14 組）")
    parser.add_argument("--apply", action="store_true", help="真的寫（預設只驗證、印 manifest）")
    args = parser.parse_args(argv)
    from engine_c import pending_observations
    from engine_c.db import get_conn
    from engine_c.manual_observations import append_relation, check_relation, duplicate_live_groups, is_judgment_field

    if not (BACKUP / "engine_c.db").exists() and not any(BACKUP.glob("*engine_c*")):
        print(f"✗ 找不到備份 {BACKUP}——先跑 backup_private.py run --no-drive 與 verify-restore", file=sys.stderr)
        return 2
    conn = get_conn()
    try:
        problems = _check_groups(conn)
        for ticker, field, _day, keep, closes, reason, *_rest in MECHANICAL:
            if is_judgment_field(field):
                problems.append(f"{ticker}／{field} 被放在 mechanical 清單，但它是判斷欄位")
            try:
                check_relation(conn, observation_id=keep, target_ids=closes, relation="supersedes", reason=reason,
                               author=AUTHOR)
            except Exception as exc:  # noqa: BLE001 — 逐條列出，一條不過就整批不寫
                problems.append(f"{ticker}／{field}：{exc}")
        for ticker, field, *_rest in JUDGMENT:
            if not is_judgment_field(field):
                problems.append(f"{ticker}／{field} 被放在判斷清單，但它是 mechanical 欄位")
        print(f"manifest：mechanical {len(MECHANICAL)} 組直接寫取代關係、判斷 {len(JUDGMENT)} 組只建提案；備份 {BACKUP.name}")
        before_dupes = duplicate_live_groups(conn)
        print(f"寫之前：同一期間多筆生效 {len(before_dupes)} 組")
        if problems:
            print("✗ 驗證沒過，一筆都不寫：\n- " + "\n- ".join(problems), file=sys.stderr)
            return 2
        if not args.apply:
            for ticker, field, day, keep, closes, reason, *_rest in MECHANICAL:
                print(f"  寫｜{ticker}／{field}／{day}：{keep} 取代 {'、'.join(closes)}｜{reason[:60]}")
            for ticker, field, day, keep, closes, reason, *_rest in JUDGMENT:
                print(f"  提案｜{ticker}／{field}／{day}：{keep} 取代 {'、'.join(closes)}｜{reason[:60]}")
            print("（只驗證，沒有寫；加 --apply 才寫）")
            return 0
        rows_before, proj_before = _dump(conn), _projection(conn)
        written, proposed = [], []
        for ticker, field, day, keep, closes, reason, *_rest in MECHANICAL:
            ids = append_relation(conn, observation_id=keep, target_ids=closes, relation="supersedes", reason=reason,
                                  author=AUTHOR)
            written.append({"ticker": ticker, "field": field, "as_of": day, "keep": keep, "closes": closes, "reason": reason,
                            "relation_ids": ids})
        for ticker, field, day, keep, closes, reason, advice in JUDGMENT:
            record = pending_observations.propose_relation(conn, observation_id=keep, target_ids=closes,
                                                           relation="supersedes", reason=reason, author=AUTHOR)
            proposed.append({"ticker": ticker, "field": field, "as_of": day, "keep": keep, "closes": closes,
                             "reason": reason, "advice": advice, "proposal_id": record["proposal_id"]})
        rows_after, proj_after = _dump(conn), _projection(conn)
        after_dupes = duplicate_live_groups(conn)
    finally:
        conn.close()
    changed_rows = sorted(set(rows_before.items()) ^ set(rows_after.items()))
    projection_changes = {k: {"before": proj_before.get(k), "after": proj_after.get(k)}
                          for k in sorted(set(proj_before) | set(proj_after)) if proj_before.get(k) != proj_after.get(k)}
    reconciliation = {
        "at": datetime.now(timezone.utc).isoformat(), "backup": BACKUP.name,
        "rows_before": len(rows_before), "rows_after": len(rows_after), "rows_changed": len(changed_rows),
        "duplicate_groups_before": len(before_dupes), "duplicate_groups_after": len(after_dupes),
        "duplicate_groups_left": [list(k) for k in sorted(after_dupes)],
        "projection_changes": projection_changes,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps({"written": written, "proposed": proposed}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    (OUT / "reconciliation.json").write_text(json.dumps(reconciliation, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = len(rows_before) == len(rows_after) and not changed_rows
    print(f"{'✓' if ok else '✗'} ledger 列：寫之前 {len(rows_before)}、之後 {len(rows_after)}、內容有變 {len(changed_rows)}")
    print(f"同一期間多筆生效：{len(before_dupes)} → {len(after_dupes)} 組（剩下的：{', '.join('/'.join(k) for k in sorted(after_dupes))}）")
    print(f"投影勝出者有變：{len(projection_changes)} 個 (ticker, 欄位)：{', '.join(projection_changes)}")
    print(f"取代關係寫了 {sum(len(w['relation_ids']) for w in written)} 筆；提案 {len(proposed)} 份："
          + "、".join(p["proposal_id"] for p in proposed))
    print(f"manifest 與對帳 → {OUT}")
    print("下一步：python -m engine_b.todo sync（提案鑄號）")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
