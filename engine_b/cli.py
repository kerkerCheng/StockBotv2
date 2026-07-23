"""engine_b.cli — pending leads 的 list／triage／advance 命令列入口。

給 `/daily-brief` skill 一條 deterministic 持久化路徑：research agent 做語意
triage 判斷，這支 CLI 負責寫入狀態機（不讓 agent 手寫 JSON 冒險汙染 store）。
狀態語意與不變式（lead 狀態不影響 evidence tier）全在 engine_b/leads.py。

用法:
    python -m engine_b.cli list [--status pending]
    python -m engine_b.cli triage <lead_id> --go|--no-go --tier 3 --reason "有新角度"
    python -m engine_b.cli advance <lead_id> researching
    python -m engine_b.cli counts
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine_b import leads  # noqa: E402


def _cmd_list(args: argparse.Namespace) -> int:
    store = leads.load(args.leads)
    rows = sorted(
        store["leads"].values(),
        key=lambda l: (l.get("published_at") or "", l["lead_id"]),
        reverse=True,
    )
    if args.status:
        rows = [l for l in rows if l["status"] == args.status]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("（無符合 leads）")
        return 0
    for l in rows:
        tri = l.get("triage") or {}
        tag = f" [{tri.get('decision')}·tier{tri.get('tier')}]" if tri else ""
        print(f"{l['lead_id']}  {l['status']:15}{tag}  {l['source']}")
        print(f"    {l.get('title') or '(無標題)'}  {l.get('url')}")
    return 0


def _cmd_triage(args: argparse.Namespace) -> int:
    store = leads.load(args.leads)
    try:
        leads.triage(
            store, args.lead_id,
            go=args.go, tier=args.tier, reason=args.reason,
        )
    except (leads.LeadStateError, ValueError) as exc:
        print(f"triage 失敗：{exc}", file=sys.stderr)
        return 1
    leads.save(store, args.leads)
    print(f"✓ {args.lead_id} → {'triaged_go' if args.go else 'triaged_no_go'}")
    return 0


def _cmd_advance(args: argparse.Namespace) -> int:
    store = leads.load(args.leads)
    ref = {}
    if args.ref:
        for pair in args.ref:
            key, _, value = pair.partition("=")
            if key:
                ref[key] = value
    try:
        leads.advance(store, args.lead_id, args.to_status, ref=ref or None)
    except leads.LeadStateError as exc:
        print(f"advance 失敗：{exc}", file=sys.stderr)
        return 1
    leads.save(store, args.leads)
    print(f"✓ {args.lead_id} → {args.to_status}")
    return 0


def _cmd_counts(args: argparse.Namespace) -> int:
    store = leads.load(args.leads)
    counts = leads.status_counts(store)
    print(json.dumps(counts, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="pending leads 狀態機命令列入口")
    ap.add_argument("--leads", default=str(leads.DEFAULT_LEADS_PATH),
                    help="pending_leads.json 路徑（預設本機 authority）")
    sub = ap.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="列出 leads")
    p_list.add_argument("--status", help="只列某狀態（pending／triaged_go…）")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cmd_list)

    p_tri = sub.add_parser("triage", help="對 pending lead 下 go／no-go")
    p_tri.add_argument("lead_id")
    grp = p_tri.add_mutually_exclusive_group(required=True)
    grp.add_argument("--go", dest="go", action="store_true")
    grp.add_argument("--no-go", dest="go", action="store_false")
    p_tri.add_argument("--tier", type=int, required=True, help="1–4（來源分級，非 evidence tier）")
    p_tri.add_argument("--reason", required=True)
    p_tri.set_defaults(func=_cmd_triage)

    p_adv = sub.add_parser("advance", help="一般狀態轉移")
    p_adv.add_argument("lead_id")
    p_adv.add_argument("to_status")
    p_adv.add_argument("--ref", action="append", help="key=value，記錄關聯（如 research_action_id=ra_x）")
    p_adv.set_defaults(func=_cmd_advance)

    p_cnt = sub.add_parser("counts", help="各狀態計數（JSON）")
    p_cnt.set_defaults(func=_cmd_counts)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
