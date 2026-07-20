"""
preconditions.py — L9 前置條件 Gate（三大條件全部滿足才能開放投資建議標籤）。

CLAUDE.md L9 規定，投資諮詢開放前必須滿足三個前置條件：
  1. 第二條垂直切片完成（非 AI / 非 CPO 主題，跑通同一 pipeline）
  2. 最小投資規則已定義（進場/出場/sizing/thesis 失效）
  3. 財務核驗清單 5 項可一鍵查出

若任一條件未滿足，輸出標記為 [Research Note] 而非 [Investment Candidate]。

除了三大 L9 前置條件，本 gate 另加一個**每公司**的升格 hold：來源可信度
（`source_credibility`）。事實 `source_under_audit` 住 Engine A 的 SourceDoc；此處與
memo 的 evidence gate 共用 `query.audit_hold` 讀同一真相，避免兩個閘門面漂移。
若被建議公司的證據基底有審查中來源，credibility hold 觸發、gate 不亮綠。

用法:
    from thesis.preconditions import check_all, format_gate
    result = check_all()
    print(format_gate(result))
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── 1. 第二條垂直切片 ─────────────────────────────────────────────────────────

# 第二切片的「規格」住文件（AGENTS.md 開發優先序第 1 項；詳細歷史規格見 005 plan）。
# 此 gate 只認 runtime 交付物（memo + scoring），刻意不綁任何 plan 檔存在性——
# plan 是意圖不是完成訊號，且 docs/plans 已定為純歷史，gate 不該硬依賴其檔名。
_SECOND_SLICE_SPEC_REF = (
    "AGENTS.md 開發優先序第 1 項"
    "（詳細規格：docs/plans/2026-07-08-005-feat-second-vertical-slice-plan.md）"
)
_SECOND_SLICE_MEMO_TOKENS = ("amat", "lrcx", "semi_equip", "mature_node")


def _extract_score(content: str, label: str) -> int | None:
    match = re.search(
        rf"\|\s*(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*\|\s*(?:\*\*)?(\d+)\s*/",
        content,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def _check_second_slice(*, root: Path = ROOT) -> dict:
    """
    L9 前置條件 #1：第二條非 AI／非 CPO 垂直切片是否「做完且通過」。

    判定完全依 runtime 交付物——thesis/ 下檔名含 amat/lrcx/semi_equip/mature_node
    的 Lane Memo，且有非空 Variant Perception 段落 + 同 stem scoring 過失敗閾值。
    刻意不檢查任何 plan 檔存在性：plan 是意圖不是完成訊號，規格住文件（見
    `_SECOND_SLICE_SPEC_REF`），gate 只認交付物。
    """
    thesis_dir = root / "thesis"
    non_cpo_memos = [
        f for f in thesis_dir.glob("*.md")
        if any(token in f.name for token in _SECOND_SLICE_MEMO_TOKENS)
    ]
    if not non_cpo_memos:
        return {
            "ok": False,
            "label": "second_slice",
            "detail": "尚未找到第二切片 Lane Memo（thesis/ 無 amat/lrcx/semi_equip/mature_node memo）",
            "action": f"依 {_SECOND_SLICE_SPEC_REF} 執行工業半導體設備切片（手選 5-8 篇文件 → extract → thesis → scoring）",
        }

    memo = non_cpo_memos[0]
    content = memo.read_text(encoding="utf-8", errors="ignore")
    variant_match = re.search(
        r"(?ims)^#{1,6}\s*Variant Perception\s*$\s*(.+?)(?=^#{1,6}\s|\Z)",
        content,
    )
    if not variant_match or not variant_match.group(1).strip():
        return {
            "ok": False,
            "label": "second_slice",
            "detail": f"{memo.name} 缺少非空 Variant Perception 段落",
            "action": "補上市場隱含假設 X、thesis Y 與催化劑 Z",
        }

    stem = memo.stem
    scoring_candidates = [
        memo.with_name(stem.replace("_lane_memo", "_scoring") + ".md"),
        memo.with_name(stem + ".scoring.md"),
    ]
    scoring = next((path for path in scoring_candidates if path.exists()), None)
    if scoring is None:
        return {
            "ok": False,
            "label": "second_slice",
            "detail": f"{memo.name} 有 Variant Perception，但缺對應 scoring 檔",
            "action": "建立同 stem 的 _scoring.md 並完成失敗閾值評分",
        }

    scoring_text = scoring.read_text(encoding="utf-8", errors="ignore")
    scores = {
        "可信度": _extract_score(scoring_text, "可信度"),
        "可證偽性": _extract_score(scoring_text, "可證偽性"),
        "市場差異度": _extract_score(scoring_text, "市場差異度"),
        "總分": _extract_score(scoring_text, "總分"),
    }
    missing_scores = [label for label, score in scores.items() if score is None]
    if missing_scores:
        return {
            "ok": False,
            "label": "second_slice",
            "detail": f"{scoring.name} 缺少 scoring 欄位：{missing_scores}",
            "action": "補齊可信度、可證偽性、市場差異度與總分",
        }
    thresholds = {"可信度": 3, "可證偽性": 3, "市場差異度": 2, "總分": 20}
    failed = [
        f"{label} {scores[label]} < {minimum}"
        for label, minimum in thresholds.items()
        if scores[label] < minimum
    ]
    if failed:
        return {
            "ok": False,
            "label": "second_slice",
            "detail": "second-slice scoring 未通過：" + "；".join(failed),
            "action": "補強研究後重新評分；不可只靠檔名解鎖 L9",
        }
    return {
        "ok": True,
        "label": "second_slice",
        "detail": f"第二條切片內容與 scoring 皆通過 ({memo.name})",
        "action": None,
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
            "detail": "Engine C 未連線（engine_c_available=False）",
            "action": (
                "啟動 Postgres：docker compose up postgres -d\n"
                "    初始化 schema：engine_c/schema.sql\n"
                "    跑 ETL：python engine_c/etl_yfinance.py"
            ),
        }

    if not result.get("gate_pass", False):
        incomplete = [
            f"{item.get('label', key)}={item.get('status', 'missing')}"
            for key, item in result.get("items", {}).items()
            if item.get("status") not in ("ok", "manual_reviewed")
        ]
        detail = "；".join(incomplete) or result.get("note", "清單狀態不完整")
        return {
            "ok": False,
            "label": "financial_checklist",
            "detail": f"{test_ticker} 財務核驗清單未完成：{detail}",
            "action": "補齊被建議標的的 missing/manual_required 項目後再提供倉位數字",
        }

    return {
        "ok": True,
        "label": "financial_checklist",
        "detail": f"{test_ticker} 財務核驗清單五項皆完成",
        "action": None,
    }


# ── 4. 來源可信度 hold（audit）— 跨引擎閘門，事實住 Engine A ─────────────────────

def _resolve_company_id(ticker: str | None, company_id: str | None) -> str | None:
    """company_id 優先；否則用 TICKER_MAP 反查（靜態 lookup，不猜）。"""
    if company_id:
        return company_id
    if not ticker:
        return None
    try:
        from loader.load_to_neo4j import TICKER_MAP
    except ImportError:
        return None
    reverse = {tk: cid for cid, tk in TICKER_MAP.items() if tk}
    return reverse.get(ticker.upper())


def _check_source_credibility(
    ticker: str | None = None, company_id: str | None = None
) -> dict:
    """升格 hold：公司證據基底若有 `source_under_audit` 來源，不得升格。

    與 memo 的 evidence gate 共用 `query.audit_hold`（事實住 Engine A 的 SourceDoc）。
    無法查證（Neo4j 未連線／ticker 未對映）→ 出 warning 但不擋——memo 的 evidence
    gate 是真正的 promotion backstop，這裡的軟降級只避免圖暫時不可用時 brick 整個 gate。
    """
    cid = _resolve_company_id(ticker, company_id)
    if not cid:
        return {
            "ok": True,
            "label": "source_credibility",
            "detail": f"未能由 ticker={ticker} 對映 company_id，跳過來源審查檢查",
            "action": None,
        }
    try:
        from neo4j import GraphDatabase
        from query.audit_hold import audit_hold_for_company
    except ImportError as e:
        return {"ok": True, "label": "source_credibility",
                "detail": f"⚠ 無法檢查來源審查狀態（套件不可用：{e}）", "action": None}
    pw = os.environ.get("NEO4J_PASSWORD")
    if not pw:
        return {"ok": True, "label": "source_credibility",
                "detail": "⚠ 無法檢查來源審查狀態（NEO4J_PASSWORD 未設）", "action": None}
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), pw),
    )
    try:
        hold = audit_hold_for_company(driver, cid)
    except Exception as e:
        return {"ok": True, "label": "source_credibility",
                "detail": f"⚠ 無法檢查來源審查狀態（Neo4j 查詢失敗：{e}）", "action": None}
    finally:
        driver.close()

    if not hold["held"]:
        return {"ok": True, "label": "source_credibility",
                "detail": f"{cid} 證據基底無審查中來源", "action": None}
    docs = hold["docs"]
    review_bys = sorted({str(d.get("review_by")) for d in docs if d.get("review_by")})
    doc_ids = "、".join(d["doc_id"] for d in docs)
    return {
        "ok": False,
        "label": "source_credibility",
        "detail": (
            f"{cid} 有審查中來源（credibility hold）：{doc_ids}"
            + (f"；review_by={', '.join(review_bys)}" if review_bys else "")
        ),
        "action": "審查解除前不得升格 [Investment Note]；走 source-trace 追指控原文、盯 review_by 結果",
    }


# ── public API ─────────────────────────────────────────────────────────────────

def check_all(ticker: str | None = None, company_id: str | None = None) -> dict:
    """
    執行三大前置條件檢查，回傳結果 dict。

    三大 L9 前置條件 + 每公司的來源可信度 hold（audit）。company_id 選填：
    generate_lane_memo 直接傳入；命令列只給 ticker 時由 TICKER_MAP 反查。

    結構:
    {
      "gate_pass": bool,          # 全部滿足才 True
      "investment_label_ok": bool, # 同 gate_pass（提供語意明確的別名）
      "checks": [
        {"label": "second_slice", "ok": bool, "detail": str, "action": str | None},
        {"label": "investment_rules", ...},
        {"label": "financial_checklist", ...},
        {"label": "source_credibility", ...},  # audit hold，事實住 Engine A
      ]
    }
    """
    checks = [
        _check_second_slice(),
        _check_investment_rules(),
        _check_financial_checklist(ticker),
        _check_source_credibility(ticker, company_id),
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
