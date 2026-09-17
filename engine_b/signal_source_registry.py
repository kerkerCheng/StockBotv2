"""訊號來源登記表的唯一 loader（`config/signal_sources.json`）——D5，ROADMAP Phase 3。

哪些帳號會被 harvest、各自處在哪一級信任，由 config 決定；本模組只負責**載入、驗證封閉性、
回答 tier 是什麼**。它不 harvest 任何東西，也不改任何 tier。

## 封閉性

`tier` 必在 `TIERS` 內，`status` 必在 `STATUSES` 內；違反就在載入時失敗。
字彙一旦有行為後果就必須被強制——自由字串卻決定去留，打錯不報錯、只會安靜沉底（L16-3）。

## ⚠ 三條不得

1. **tier 升降是一季一次的 pq2 manual（D5）。** 本模組刻意**沒有**寫入函式：
   要改 tier 就去改 config，而改 config 要先有 pq2 receipt。
2. **tier 不參與投資標的排序、不給尺寸。** 它只動 pq1 研究佇列的優先序（`priority_bonus`），
   而那是注意力不是資本（AGENTS.md「技術訊號的地位」通則：未量測的指標可以被提出、被測，
   但不得參與任何排序或尺寸決定）。
3. **來源 tier ≠ evidence tier。** 推文永遠是 tier-4 lead；`trusted` 帳號的推文也是 tier-4。
   兩者不得互相換算——這是 L15-2（語意歸語言處理，權限永遠 deterministic）的直接應用。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "config" / "signal_sources.json"

#: 信任級別的封閉字彙。順序即高低，`pq1_priority_bonus` 靠它。
#: ⚠ 刻意**沒有** `blocked`／`retired`——那是 `status` 的職責，兩個欄位不得混用
#: （一個表示承載兩種語意就是 L12 的形狀）。
TIERS: tuple[str, ...] = ("probation", "measured", "trusted")

#: 帳號在 harvest 管線裡的狀態。與 tier **正交**：`active` 的 `probation` 帳號照抓，只是不加分。
#:
#: ⚠⚠ **`probation` 在這份 config 裡出現兩次，意思不同**，寫的時候務必看清楚是哪一欄：
#:   - `status = "probation"` → decision_lab 的 **attention policy**：這個來源要不要自動 capture。
#:   - `tier   = "probation"` → D5 的 **信任級別**：這個來源的點名有沒有被量測過。
#: 一個帳號可以 `status=active` 且 `tier=probation`（照抓，但信任為零）——那正是今天的實況。
#:
#: 這個字彙的 SSOT 是 `decision_lab.intake._SOURCE_STATUSES`（早於本模組存在）。
#: 這裡**借它而不是自己抄一份**：抄一份就會在某天悄悄分岔，而分岔的那天不會有東西壞掉
#: （L16：分類已經有 SSOT 時，要讓它跟著資料走到需要它的地方）。
def _load_statuses() -> tuple[str, ...]:
    from decision_lab.intake import _SOURCE_STATUSES

    return tuple(sorted(_SOURCE_STATUSES))


STATUSES: tuple[str, ...] = _load_statuses()

#: tier → pq1 優先序加分。**只影響研究佇列的順序，不影響入池、不影響 evidence tier。**
#: probation 是 0 而不是負數：新帳號不該被懲罰，只是還沒有理由被優先看。
PQ1_PRIORITY_BONUS: Mapping[str, int] = {"probation": 0, "measured": 10, "trusted": 25}

#: 升 `measured` 的最低樣本（§6 的 stop rule）。本模組只**陳述**它，不執行升等。
MEASURED_MIN_NAMED_CALLS = 20
MEASURED_MIN_DISTINCT_TICKERS = 5


class SignalSourceRegistryError(ValueError):
    """config 缺漏或違反封閉性。"""


@dataclass(frozen=True)
class SignalSource:
    source_id: str
    platform: str
    handle: str
    status: str
    tier: str
    research_priority: int
    auto_capture: bool
    tier_since: str | None = None
    tier_rationale: str = ""

    @property
    def pq1_priority_bonus(self) -> int:
        return PQ1_PRIORITY_BONUS[self.tier]

    @property
    def harvest_key(self) -> str:
        """harvest_log／lead 的 `source` 欄位長什麼樣（例：`x:aleabitoreddit`）。"""
        return f"{self.platform}:{self.handle}"


@dataclass(frozen=True)
class SignalSourceRegistry:
    sources: Mapping[str, SignalSource]
    path: Path = DEFAULT_PATH
    schema_version: int = 2

    def get(self, source_id: str) -> SignalSource | None:
        return self.sources.get(source_id)

    def by_harvest_key(self, harvest_key: str) -> SignalSource | None:
        """`x:aleabitoreddit` → 該帳號。找不到回 None——**不猜**（INV-1 的同一條紀律）。"""
        for source in self.sources.values():
            if source.harvest_key == harvest_key:
                return source
        return None

    def active(self) -> tuple[SignalSource, ...]:
        return tuple(s for s in self.sources.values() if s.status == "active")

    def by_tier(self, tier: str) -> tuple[SignalSource, ...]:
        if tier not in TIERS:
            raise SignalSourceRegistryError(f"tier 未登記：{tier!r}；已知 {TIERS}")
        return tuple(s for s in self.sources.values() if s.tier == tier)

    def tier_counts(self) -> Mapping[str, int]:
        """**每一級都出現，包含 0**——缺席不得被壓成「沒有這一級」。"""
        return {tier: len(self.by_tier(tier)) for tier in TIERS}


def load(path: Path | str | None = None) -> SignalSourceRegistry:
    target = Path(path) if path else DEFAULT_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SignalSourceRegistryError(f"找不到登記表：{target}") from exc
    except json.JSONDecodeError as exc:
        raise SignalSourceRegistryError(f"登記表不是合法 JSON：{target}（{exc}）") from exc

    entries = raw.get("sources")
    if not isinstance(entries, list):
        raise SignalSourceRegistryError(f"{target}: `sources` 必須是 list")

    sources: dict[str, SignalSource] = {}
    for item in entries:
        if not isinstance(item, Mapping):
            raise SignalSourceRegistryError(f"{target}: sources 的每一項必須是 object")
        source_id = str(item.get("source_id") or "").strip()
        if not source_id:
            raise SignalSourceRegistryError(f"{target}: 有一項缺 source_id")
        if source_id in sources:
            raise SignalSourceRegistryError(f"{target}: source_id 重複：{source_id!r}")
        tier = str(item.get("tier") or "").strip()
        if tier not in TIERS:
            raise SignalSourceRegistryError(
                f"{target}: {source_id} 的 tier 未登記：{tier!r}；已知 {TIERS}——"
                "未宣告不得預設放行（tier 有行為後果，L16-3）")
        status = str(item.get("status") or "").strip()
        if status not in STATUSES:
            raise SignalSourceRegistryError(
                f"{target}: {source_id} 的 status 未登記：{status!r}；已知 {STATUSES}")
        sources[source_id] = SignalSource(
            source_id=source_id,
            platform=str(item.get("platform") or "x"),
            handle=str(item.get("handle") or source_id),
            status=status,
            tier=tier,
            research_priority=int(item.get("research_priority") or 0),
            auto_capture=bool(item.get("auto_capture")),
            tier_since=(str(item["tier_since"]) if item.get("tier_since") else None),
            tier_rationale=str(item.get("tier_rationale") or ""),
        )
    if not sources:
        raise SignalSourceRegistryError(f"{target}: 登記表是空的")
    return SignalSourceRegistry(
        sources=sources, path=target, schema_version=int(raw.get("schema_version") or 1))


def _describe(registry: SignalSourceRegistry) -> str:
    lines = [f"# 訊號來源登記表（{registry.path.name}，schema v{registry.schema_version}）"]
    counts = registry.tier_counts()
    lines.append("  ".join(f"{tier}：{counts[tier]}" for tier in TIERS))
    for source in sorted(registry.sources.values(), key=lambda s: (s.tier, s.source_id)):
        lines.append(
            f"- {source.harvest_key:28s} tier={source.tier:10s} status={source.status:7s} "
            f"pq1 加分 +{source.pq1_priority_bonus}"
            + (f"｜tier 自 {source.tier_since}" if source.tier_since else ""))
        if source.tier_rationale:
            lines.append(f"    {source.tier_rationale}")
    lines.append(
        f"⚠ tier 升降是一季一次的 pq2 manual（D5）；"
        f"升 measured 的最低樣本：{MEASURED_MIN_NAMED_CALLS} 則具名點名、"
        f"跨 {MEASURED_MIN_DISTINCT_TICKERS} 檔。")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    parser.add_argument("--path", default=None)
    args = parser.parse_args(argv)
    try:
        registry = load(args.path)
    except SignalSourceRegistryError as exc:
        print(f"✗ {exc}")
        return 2
    print(_describe(registry))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
