"""
preconditions.py — L9 前置條件 Gate（三大條件全部滿足才能開放投資建議標籤）。

CLAUDE.md L9 規定，投資諮詢開放前必須滿足三個前置條件：
  1. 第二條垂直切片完成（非 AI / 非 CPO 主題，跑通同一 pipeline）
  2. 最小投資規則已定義（進場/出場/sizing/thesis 失效）
  3. 財務核驗清單 5 項可一鍵查出

若任一條件未滿足，輸出標記為 [Research Note] 而非 [Investment Candidate]。

用法:
    from thesis.preconditions import check_all, format_gate
    result = check_all()
    print(format_gate(result))
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── 1. 第二條垂直切片 ─────────────────────────────────────────────────────────

_SECOND_SLICE_PLAN = ROOT / "docs" / "plans" / "2026-07-08-005-feat-second-vertical-slice-plan.md"

def _check_second_slice() -> dict:
    """
    第二條切片的前置條件：計畫存在且包含 done/complete 標記，
    或 thesis/ 目錄有對應的 lane memo 產出。
    目前 v1：計畫存在 = 條件成立（計畫執行由人工啟動）。
    """
    if not _SECOND_SLICE_PLAN.exists():
        return {
            "ok": False,
            "label": "second_slice",
            "detail": f"計畫文件不存在：{_SECOND_SLICE_PLAN.relative_to(ROOT)}",
            "action": "確認 docs/plans/2026-07-08-005-feat-second-vertical-slice-plan.md 已建立",
        }

    # 進一步確認計畫是否已「執行完成」：thesis/ 有 non-CPO slice memo
    thesis_dir = ROOT / "thesis"
    non_cpo_memos = [
        f for f in thesis_dir.glob("*.md")
        if "amat" in f.name or "lrcx" in f.name or "semi_equip" in f.name
           or "mature_node" in f.name
    ]
    if non_cpo_memos:
        return {
            "ok": True,
            "label": "second_slice",
            "detail": f"第二條切片已完成 ({non_cpo_memos[0].name})",
            "action": None,
        }

    return {
        "ok": False,
        "label": "second_slice",
        "detail": "計畫已建立，但尚未執行（thesis/ 中未找到非 CPO 的 Lane Memo）",
        "action": "依 2026-07-08-005 計畫執行工業半導體設備切片（手選 5-8 篇文件 → extract → thesis）",
    }


# ── 2. 最小投資規則已定義 ─────────────────────────────────────────────────────

_INVESTMENT_SOP = ROOT / "docs" / "investment-sop.md"
_REQUIRED_SOP_SECTIONS = ["進場條件", "單檔上限", "持有期", "出場條件"]

def _check_investment_rules() -> dict:
    if not _INVESTMENT_SOP.exists():
        return {
            "ok": False,
            "label": "investment_rules",
            "detail": f"投資 SOP 不存在：{_INVESTMENT_SOP.relative_to(ROOT)}",
            "action": "建立 docs/investment-sop.md（包含進場條件/sizing/出場觸發）",
        }

    content = _INVESTMENT_SOP.read_text(encoding="utf-8", errors="ignore")
    missing = [s for s in _REQUIRED_SOP_SECTIONS if s not in content]
    if missing:
        return {
            "ok": False,
            "label": "investment_rules",
            "detail": f"investment-sop.md 存在但缺少段落：{missing}",
            "action": f"在 docs/investment-sop.md 補齊：{missing}",
        }

    return {
        "ok": True,
        "label": "investment_rules",
        "detail": "investment-sop.md 已定義所有必要規則",
        "action": None,
    }


# ── 3. 財務核驗清單 5 項可一鍵查出 ───────────────────────────────────────────

def _check_financial_checklist(ticker: str | None = None) -> dict:
    """
    嘗試呼叫 engine_c.checklist.get_checklist()。
    - 若 engine_c 不可用 → 條件未滿足
    - 若可用但 Postgres 未啟動 → 條件未滿足（但 graceful）
    - 若可用且 Postgres 在線 → 條件滿足
    ticker 選填：若提供則用該 ticker 測試；否則用 COHR 作預設 smoke test。
    """
    test_ticker = ticker or "COHR"
    try:
        from engine_c.checklist import get_checklist
        result = get_checklist(test_ticker)
    except ImportError as e:
        return {
            "ok": False,
            "label": "financial_checklist",
            "detail": f"engine_c.checklist 無法匯入：{e}",
            "action": "確認 engine_c/ 目錄與 requirements.txt 安裝（psycopg2-binary）",
        }
    except Exception as e:
        return {
            "ok": False,
            "label": "financial_checklist",
            "detail": f"checklist 呼叫失敗：{e}",
            "action": "確認 Postgres 已啟動（docker compose up postgres -d）",
        }

    if not result.get("engine_c_available", True):
        return {
            "ok": False,
            "label": "financial_checklist",
            "detail": "Postgres 未連線（engine_c_available=False）",
            "action": (
                "啟動 Postgres：docker compose up postgres -d\n"
                "    初始化 schema：engine_c/schema.sql\n"
                "    跑 ETL：python engine_c/etl_yfinance.py"
            ),
        }

    return {
        "ok": True,
        "label": "financial_checklist",
        "detail": f"財務核驗清單可用（smoke test ticker: {test_ticker}）",
        "action": None,
    }


# ── public API ─────────────────────────────────────────────────────────────────

def check_all(ticker: str | None = None) -> dict:
    """
    執行三大前置條件檢查，回傳結果 dict。

    結構:
    {
      "gate_pass": bool,          # 全部滿足才 True
      "investment_label_ok": bool, # 同 gate_pass（提供語意明確的別名）
      "checks": [
        {"label": "second_slice", "ok": bool, "detail": str, "action": str | None},
        {"label": "investment_rules", ...},
        {"label": "financial_checklist", ...},
      ]
    }
    """
    checks = [
        _check_second_slice(),
        _check_investment_rules(),
        _check_financial_checklist(ticker),
    ]
    gate_pass = all(c["ok"] for c in checks)
    return {
        "gate_pass": gate_pass,
        "investment_label_ok": gate_pass,
        "checks": checks,
    }


def format_gate(result: dict) -> str:
    """格式化成 Lane Memo 可注入的 Markdown 片段。"""
    lines = ["## L9 前置條件 Gate（投資諮詢開放條件）"]

    all_pass = result.get("gate_pass", False)
    label = "✅ 全部通過 → 可標記 [Investment Note]" if all_pass else "⚠ 未全通過 → 輸出維持 [Research Note]"
    lines.append(label)
    lines.append("")

    for c in result.get("checks", []):
        icon = "✅" if c["ok"] else "❌"
        lines.append(f"{icon} **{c['label']}**: {c['detail']}")
        if not c["ok"] and c.get("action"):
            for line in c["action"].split("\n"):
                lines.append(f"   → {line.strip()}")

    return "\n".join(lines)


def main() -> int:
    import sys
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else None
    result = check_all(ticker)
    print(format_gate(result))
    return 0 if result["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
