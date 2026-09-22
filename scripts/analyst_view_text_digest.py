"""個股頁**文字** digest：讓「只拿掉面板、不改文字」變成可機械比對的一句話。

用途只有一個：Phase 0（`docs/plans/2026-09-22-001-refactor-phase0-retire-plan.md`）的
結案 gate 3 與 R2 檢查 7 要求「materialize 前後，73 檔的 brief／argument／research 面板**文字**不變」
（2026-09-23 起： 退役、 升核心）。
沒有一個固定配方的話，前後兩次比對會各自寫一段 snippet，於是「不變」永遠證不出來。

**只 hash 敘事文字**，不 hash 數字、時戳、digest、依賴 payload——因為那些本來就會隨資料刷新而動，
把它們算進去會讓比對永遠紅、於是永遠被忽略（那就等於沒有 gate）。

唯讀：不寫任何檔案、不碰 authority。

    python scripts/analyst_view_text_digest.py              # 每檔一行 ＋ 總 digest
    python scripts/analyst_view_text_digest.py --per-panel  # 逐面板展開
    python scripts/analyst_view_text_digest.py --dir <路徑>  # 指定 artifact 目錄
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

#: 要比對的面板。Phase 0 只承諾這三個面板的文字不動（其餘面板本來就會被拿掉）。
#: ⚠ 2026-09-23（Phase 0 Step 0b.1，使用者定案 A）：`why` 退役、`argument` 升核心，所以比對的
#: 第二格由 `why` 換成 `argument`。gate 3 的措辭同步改成「argument 少掉的只能是估值來源的段」。
PANELS = ("brief", "argument", "research")

#: `datum` 底下唯一算文字的鍵。其餘（as_of、authority、dependencies、basis…）是 metadata，
#: 會隨刷新而變，不屬於「文字」。
_TEXT_KEYS = ("value", "text", "label", "note", "reason")


def _texts_from_datum(datum: object) -> list[str]:
    """從一條 line 的 datum 裡取出敘事字串（不遞迴進 dependencies 之類的 payload）。"""
    out: list[str] = []
    if isinstance(datum, str):
        out.append(datum)
    elif isinstance(datum, dict):
        for key in _TEXT_KEYS:
            val = datum.get(key)
            if isinstance(val, str) and val.strip():
                out.append(val)
            elif isinstance(val, list):
                out.extend(v for v in val if isinstance(v, str) and v.strip())
    return out


def panel_texts(panel: object) -> list[str]:
    """一個面板的敘事文字，順序固定（title → 逐 line 的 label＋文字 → notes → questions）。"""
    if not isinstance(panel, dict):
        return []
    out: list[str] = []
    title = panel.get("title")
    if isinstance(title, str) and title.strip():
        out.append(f"title::{title}")
    for line in panel.get("lines") or []:
        if not isinstance(line, dict):
            continue
        key = line.get("key")
        label = line.get("display_label")
        if isinstance(label, str) and label.strip():
            out.append(f"label::{key}::{label}")
        for text in _texts_from_datum(line.get("datum")):
            out.append(f"text::{key}::{text}")
    for field in ("notes", "questions"):
        for item in panel.get(field) or []:
            if isinstance(item, str) and item.strip():
                out.append(f"{field}::{item}")
    return out


def _digest(texts: list[str]) -> str:
    return hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()[:16]


def artifact_texts(doc: dict) -> dict[str, list[str]]:
    """一份 analyst view 的文字，分面板回傳；`our_bet` 單獨一格（首屏短評的主詞）。"""
    view = doc.get("view") or {}
    result = {name: panel_texts(view.get(name)) for name in PANELS}
    our_bet = ((doc.get("overview") or {}).get("brief") or {}).get("our_bet") or {}
    value = our_bet.get("value")
    result["our_bet"] = [f"our_bet::{value}"] if isinstance(value, str) and value.strip() else []
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="個股頁 brief／argument／research 的文字 digest（唯讀）")
    parser.add_argument("--dir", type=Path, default=None, help="analyst view artifact 目錄")
    parser.add_argument("--per-panel", action="store_true", help="逐面板一行")
    args = parser.parse_args(argv)

    if args.dir is not None:
        directory = args.dir
    else:
        from webapp.store import artifact_dir

        directory = artifact_dir()

    # `.meta.json`（字彙表）與寫入中的 `.<name>.tmp` 以點開頭，不是股票——與 `webapp.store.tickers()` 同一條規則。
    paths = sorted(p for p in directory.glob("*.json")
                   if p.is_file() and not p.name.startswith("."))
    if not paths:
        print(f"# 沒有 artifact：{directory}")
        return 1

    print(f"# analyst view 文字 digest（{len(paths)} 檔；目錄 {directory}）")
    print("# 只 hash 敘事文字：title／display_label／datum 的 value・text・label・note・reason／notes／questions")
    overall: list[str] = []
    for path in paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        texts = artifact_texts(doc)
        flat: list[str] = []
        for name in ("our_bet", *PANELS):
            flat.append(f"[{name}]")
            flat.extend(texts[name])
        ticker = doc.get("ticker") or path.stem
        line_counts = "／".join(f"{name}={len(texts[name])}" for name in ("our_bet", *PANELS))
        print(f"{ticker}\t{_digest(flat)}\t{line_counts}")
        if args.per_panel:
            for name in ("our_bet", *PANELS):
                print(f"    {ticker}.{name}\t{_digest(texts[name])}\t{len(texts[name])} 段")
        overall.append(f"{ticker}\t{_digest(flat)}")
    print(f"# TOTAL\t{_digest(overall)}\t{len(paths)} 檔")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
