"""
observation_relations.py — Engine C 人工觀測的取代／並存關係入口（2026-10-14 取代鏈 A；ROADMAP「人工觀測的取代鏈收多值」）。

`supersedes_id` 是單值欄位（帶 FK），一筆新紀錄只能關掉一條鏈；同一期間長出兩條互不相干的鏈之後就合併不了
（2026-09-13 實測 14 組）。這裡寫的是另一本 append-only 的關係表：一筆可以關掉多筆，也能記「刻意並存」。
既有的觀測列一個欄位都不改。

- **mechanical 欄位**：直接寫（與 `scripts/record_mechanical_observation.py` 同一個判準：任何人重讀同一份文件得到同一個數）。
- **判斷欄位**：同一個命令只建**提案**（`engine_c.pending_observations.propose_relation`）——`python -m engine_b.todo sync`
  鑄 pq2、使用者 go 之後 `python -m engine_b.todo complete-observation <編號>` 才寫（Engine C 判讀寫入 gate 只有一道門）。

用法::

    python -m engine_c.observation_relations list                      # 同一期間多筆生效的組（含逐筆內容摘要）與已寫的關係
    python -m engine_c.observation_relations add mo_新 --supersedes mo_舊1 mo_舊2 --reason "…"
    python -m engine_c.observation_relations add mo_甲 --parallel mo_乙 --reason "…"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _summary(value: str, width: int = 110) -> str:
    return " ".join(str(value).split())[:width]


def cmd_list(conn) -> int:
    from engine_c.manual_observations import duplicate_live_groups, is_judgment_field, live_groups

    duplicates = duplicate_live_groups(conn)
    multi = {k: v for k, v in live_groups(conn).items() if len(v) > 1}
    print(f"同一期間多筆生效：{len(duplicates)} 組（另有 {len(multi) - len(duplicates)} 組登記過的刻意並存）")
    for (ticker, field, day), ids in sorted(duplicates.items()):
        kind = "判斷（取代關係要 pq2）" if is_judgment_field(field) else "mechanical（可直接寫）"
        print(f"\n== {ticker}｜{field}｜{day}｜{kind}｜{len(ids)} 筆")
        marks = ",".join("?" for _ in ids)
        for oid, recorded, author, value in conn.execute(
                f"SELECT observation_id, recorded_at, author, value FROM manual_observations WHERE observation_id IN ({marks}) "
                "ORDER BY recorded_at", ids).fetchall():
            print(f"   {oid}｜記錄 {str(recorded)[:16]}｜{author}｜{_summary(value)}")
    try:
        rows = conn.execute("SELECT observation_id, relation, target_id, recorded_at, author, approval_ref, reason "
                            "FROM manual_observation_relations ORDER BY recorded_at").fetchall()
    except Exception:  # noqa: BLE001 — 表還沒建
        rows = []
    print(f"\n已寫的關係：{len(rows)} 筆")
    for oid, relation, target, recorded, author, approval, reason in rows:
        print(f"   {oid} {relation} {target}｜{str(recorded)[:16]}｜{author}"
              f"{'｜核准 ' + str(approval) if approval else ''}｜{_summary(reason, 80)}")
    return 0


def cmd_add(conn, args: argparse.Namespace) -> int:
    from engine_c import pending_observations
    from engine_c.manual_observations import RelationError, append_relation, check_relation, is_judgment_field

    relation, targets = ("supersedes", args.supersedes) if args.supersedes else ("parallel", args.parallel)
    try:
        _ticker, field_name, _targets = check_relation(
            conn, observation_id=args.observation_id, target_ids=targets, relation=relation, reason=args.reason,
            author=args.author, require_approval=False)
        if is_judgment_field(field_name):
            record = pending_observations.propose_relation(
                conn, observation_id=args.observation_id, target_ids=targets, relation=relation, reason=args.reason,
                author=args.author)
            print(f"✓ {field_name} 是判斷欄位：只建了提案 {record['proposal_id']}（state={record['state']}），沒有寫入")
            print("  下一步：python -m engine_b.todo sync 取得 pq2 編號；使用者 go 之後 "
                  "python -m engine_b.todo complete-observation <編號> 才寫")
            return 0
        ids = append_relation(conn, observation_id=args.observation_id, target_ids=targets, relation=relation,
                              reason=args.reason, author=args.author)
    except (RelationError, pending_observations.ProposalError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    print(f"✓ 已寫 {len(ids)} 筆關係：{'、'.join(ids)}（{field_name} 是 mechanical 欄位，不需 pq2）")
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Engine C 人工觀測的取代／並存關係（append-only）")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="同一期間多筆生效的組與已寫的關係")
    add = sub.add_parser("add", help="寫一筆關係（判斷欄位只建提案）")
    add.add_argument("observation_id", help="留下來的那一筆（取代）／並存的其中一筆")
    group = add.add_mutually_exclusive_group(required=True)
    group.add_argument("--supersedes", nargs="+", help="它關掉的那幾筆（不再生效）")
    group.add_argument("--parallel", nargs="+", help="與它刻意並存的那幾筆（都算數）")
    add.add_argument("--reason", required=True, help="為什麼（寫進關係表，跟著那一筆走）")
    add.add_argument("--author", default="session")
    args = parser.parse_args(argv)
    from engine_c.db import get_conn

    conn = get_conn()
    try:
        return cmd_list(conn) if args.command == "list" else cmd_add(conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
