"""把跨幣別標的的 `fx_rate` 觀測同步到最新一天（2026-09-19）。

## 它要消掉的失敗模式

`alpha/fx.py` 的消費端只接受與現價 `bar_date` 相差 **±3 天以內**的匯率觀測
（`FX_AS_OF_TOLERANCE_DAYS`）。2026-09-13 手抄的那四筆，每一筆的 `_note` 自己就逐字寫著
「**現價 bar_date 換了就要補新的一筆**」——而**沒有任何東西在補它**。

實測代價（2026-09-19）：四筆觀測停在 09-11、過期 8 天，於是 6680.HK／HEXA-B.ST／
XFAB.PA／XPEV 四檔的 `headline` 與 `why` 全部退回 `inputs_incompatible`，隱含報酬印不出來。
**它不會壞、不會報錯、測試不會紅**（L17-1）——只是每隔幾天安靜地把四檔的結論拿掉。

## 為什麼自動化不牴觸 `alpha/fx.py` 的契約決定 1

那條決定逐字是「匯率從 Engine C 的 `mechanical` 人工觀測來……**不用 provider 快照**」，
理由列了三個：帶 `as_of`、帶 `source_ref`、append-only、任何人重查都得到同一個數。
**被反駁的是「provider 快照」那個實作形式**（當時指的是往 `financial_snapshots` 加一個
每天被覆寫、沒有日期的欄位——「當時用的是哪個匯率」只能靠排序猜），**不是自動化本身**。
本腳本每天 append 一筆**帶 `as_of`、帶 `source_ref`、永不覆寫**的觀測，三個理由一條不少；
而且它抓的來源就是手抄那四筆用的同一個 `yfinance {base}{quote}=X` 日線收盤。

⚠ **這不需要 pq2。** `fx_rate` 在 `engine_c/observation_fields.py` 的 registry 裡
`verifiability='mechanical'`，而 2026-09-04 定案：mechanical 欄位不再需要人工核准
（`AGENTS.md`「gate 攔的是新的知識主張」）。補償控制也已經在：`value` 必須是可 diff 的
JSON 數值物件，散文會被寫入端拒收。

## 三個刻意的邊界

1. **幣別對不手寫清單，從既有觀測導出**（L16）。今天資料支持的就是已經有人建立過的那幾組；
   **新標的的第一筆仍然是人工**——那時心跳段 1 會說「FX 觀測 N 檔」而那一檔不在裡面。
   刻意不去猜「哪些標的可能需要匯率」（那要跑整條 view，而且會猜錯）。
2. **`author` 用 `fx_sync` 不是 `session`**：人抄的與機器抓的必須分得開，否則追源時
   「誰決定用這個數字」答不出來。
3. **只 append，不 supersede、不覆寫**。同一天重跑是冪等的（observation id 是內容雜湊）；
   同一天但數字變了（盤中重跑）會被寫入端的 duplicate guard 擋下——**那是對的**，
   一天一筆收盤價，不是一天多筆。

用法：
    python scripts/sync_fx_observations.py            # 同步
    python scripts/sync_fx_observations.py --dry-run  # 只印會寫什麼
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIELD = "fx_rate"
AUTHOR = "fx_sync"


def _require_field_is_still_mechanical() -> None:
    """啟動時查 registry：`fx_rate` 不再是 `mechanical` 就直接退出（exit 3）。

    ⚠ **這道閘門是這支腳本能進無人值守的唯一理由**，照 `scripts/backfill_fiscal_year_results.py`
    2026-09-10 的先例：`append_manual_observation` 本身**不擋** judgment 欄位
    （它只在 mechanical 時多驗數值可否機械比對），所以「只寫 mechanical」不能靠
    `FIELD` 這個常數沒被改過——常數會被改，而改的人不會知道他同時改掉了一道人工 gate。
    **沒有任何 CLI 參數可以換掉 `FIELD`**，這是刻意的。放行與收緊必須同時發生（L15）。
    """
    from engine_c.observation_fields import get_observation_field_registry

    spec = get_observation_field_registry().get(FIELD)
    if spec is None:
        raise SystemExit(f"✗ {FIELD} 不在 observation_fields registry 裡——拒跑")
    if getattr(spec, "verifiability", None) != "mechanical":
        raise SystemExit(
            f"✗ {FIELD} 的 verifiability 是 {getattr(spec, 'verifiability', None)!r} 不是 mechanical"
            "——它已經變成需要人工核准的判讀欄位，無人值守不得寫它")
    if getattr(spec, "requires_user_approval", False):
        raise SystemExit(f"✗ {FIELD} 現在 requires_user_approval——無人值守不得寫它")


def known_pairs(conn: Any) -> list[tuple[str, str, str]]:
    """從既有觀測導出 `(ticker, base, quote)`——**不手寫清單**（L16）。

    同一檔可能有多組（理論上），所以用 set 去重後排序，讓輸出穩定。
    """
    rows = conn.execute(
        "SELECT ticker, value FROM manual_observations WHERE field_name = ?", (FIELD,)
    ).fetchall()
    out: set[tuple[str, str, str]] = set()
    for ticker, value in rows:
        try:
            payload = json.loads(value)
        except (TypeError, ValueError):
            continue          # 壞掉的一筆不讓整批停擺，但也不靜默——由呼叫端計數
        base, quote = payload.get("base"), payload.get("quote")
        if isinstance(base, str) and isinstance(quote, str):
            out.add((str(ticker), base.upper(), quote.upper()))
    return sorted(out)


def existing_as_of(conn: Any, ticker: str) -> set[str]:
    rows = conn.execute(
        "SELECT as_of FROM manual_observations WHERE field_name = ? AND ticker = ?",
        (FIELD, ticker),
    ).fetchall()
    return {str(r[0])[:10] for r in rows}


def _as_of_date(raw: Any) -> date | None:
    """yfinance 回的是帶時區的時戳（例 `2026-09-18T00:00:00+01:00`）。

    ⚠ **取它自己那一天，不做時區轉換**：那個時戳代表「這是哪一根日線」，
    轉成本機時區會讓它前後跳一天，而 ±3 天的容忍窗是拿它跟 `bar_date` 比的。
    """
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(str(raw)).date()
    except ValueError:
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None


def sync(*, dry_run: bool = False) -> dict[str, Any]:
    from engine_c.db import get_conn
    from engine_c.manual_observations import append_manual_observation
    from engine_c.market_data import get_fx_snapshot

    conn = get_conn()
    report: dict[str, Any] = {"input": 0, "written": 0, "skipped": 0, "failed": 0,
                              "reasons": {}, "rows": []}

    def _reason(key: str) -> None:
        report["reasons"][key] = report["reasons"].get(key, 0) + 1

    try:
        pairs = known_pairs(conn)
        report["input"] = len(pairs)
        for ticker, base, quote in pairs:
            snapshot = get_fx_snapshot(f"{base}/{quote}", evaluation_at="")
            if snapshot.get("status") != "observed" or snapshot.get("rate") is None:
                report["failed"] += 1
                _reason(f"fetch_{snapshot.get('status') or 'unknown'}")
                report["rows"].append({"ticker": ticker, "pair": f"{base}/{quote}",
                                       "state": "failed", "detail": snapshot.get("blockers")})
                continue
            when = _as_of_date(snapshot.get("as_of"))
            if when is None:
                report["failed"] += 1
                _reason("as_of_unparseable")
                continue
            if when.isoformat() in existing_as_of(conn, ticker):
                report["skipped"] += 1
                _reason("already_have_that_day")
                report["rows"].append({"ticker": ticker, "pair": f"{base}/{quote}",
                                       "state": "skipped", "as_of": when.isoformat()})
                continue
            rate = float(snapshot["rate"])
            symbol = f"{base}{quote}=X"
            value = json.dumps({
                "base": base, "quote": quote, "rate": rate,
                "source": f"yfinance {symbol} 日線收盤（{when.isoformat()}）",
                "_note": (
                    f"⚠ **方向**：1 {base} ＝ {rate:g} {quote}。反了會差一個倒數，而那種錯不會報錯。"
                    f"⚠ **本筆由 `scripts/sync_fx_observations.py` 自動同步**（author=`{AUTHOR}`），"
                    "不是人工判讀：它只把已經有人建立過的幣別對更新到最新一根日線，"
                    "不新增幣別對、不做倒數、不換來源。"
                    f"⚠ 本筆只涵蓋 {when.isoformat()} 這一天；消費端只接受與現價 bar_date "
                    "相差 ±3 天內的觀測（`alpha/fx.py::FX_AS_OF_TOLERANCE_DAYS`）。"
                ),
            }, ensure_ascii=False)
            source_ref = (f"yfinance 外匯日線：{symbol}，{when.isoformat()} 收盤 {rate:.6g}"
                          "（Yahoo Finance 匯率序列，任何人重抓都得到同一個數）")
            if dry_run:
                report["rows"].append({"ticker": ticker, "pair": f"{base}/{quote}",
                                       "state": "would_write", "as_of": when.isoformat(), "rate": rate})
                continue
            try:
                observation_id = append_manual_observation(
                    conn, ticker=ticker, field_name=FIELD, value=value,
                    source_ref=source_ref, as_of=when.isoformat(), author=AUTHOR)
            except ValueError as exc:
                # 寫入端拒收（例：同一天已有一筆但數字不同）——**降級要說話**（INV-3）
                report["failed"] += 1
                _reason("rejected_by_writer")
                report["rows"].append({"ticker": ticker, "pair": f"{base}/{quote}",
                                       "state": "rejected", "detail": str(exc)[:160]})
                continue
            report["written"] += 1
            report["rows"].append({"ticker": ticker, "pair": f"{base}/{quote}", "state": "written",
                                   "as_of": when.isoformat(), "rate": rate, "id": observation_id})
    finally:
        conn.close()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="只印會寫什麼，不寫入")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()

    _require_field_is_still_mechanical()
    report = sync(dry_run=args.dry_run)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    head = "FX 觀測同步" + ("（dry-run）" if args.dry_run else "")
    print(f"# {head}")
    print(f"- 幣別對 {report['input']} 組｜寫入 {report['written']}｜"
          f"已有那一天 {report['skipped']}｜失敗 {report['failed']}")
    if report["reasons"]:
        print("- 理由：" + "、".join(f"{k} {v}" for k, v in sorted(report["reasons"].items())))
    for row in report["rows"]:
        detail = f"　{row.get('detail')}" if row.get("detail") else ""
        rate = f"　{row['rate']:.6g}" if row.get("rate") is not None else ""
        print(f"  - {row['ticker']:<10} {row['pair']:<9} {row['state']:<12}"
              f"{row.get('as_of') or '':<12}{rate}{detail}")
    # 失敗不讓整批變成非零退出：它是 best-effort 同步，心跳那行才是常駐的真相來源
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
