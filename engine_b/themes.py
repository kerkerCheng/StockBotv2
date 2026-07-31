"""主題字彙比對：lead 之間的第二層確定性關聯。

第一層是 `engine_b/entities.py` 的具名標的（cashtag、結構化 source、registry 反查），
精準但召回有限——主題相關卻沒有共同 ticker 的關聯抓不到，例如「FCC 禁中國 humanoid
進口」對上「Agility 透過 CCXI 上市」。

這一層用 `config/themes.txt` 已註冊的主題字彙做關鍵字比對。仍然是**確定性**的：
關鍵字逐字出現才算，不呼叫模型、不做模糊比對，因此可預測、可測試、規模成長不退化。

**反證關鍵字同樣會標記該主題。** themes.txt 每個主題都帶「替代/反證關鍵字」
（cpo 的反證是 LPO、copper interconnect 等）。一則講 LPO 的貼文對 CPO thesis
高度相關——它是反面證據。把它標成同一主題但註明 `counter`，正是 L7（可證偽是
一等公民）要的：反證要能被找到，不是被過濾掉。

比對結果只是注意力線索，與 lead status 同性質，永不影響 evidence tier。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PATH = _ROOT / "config" / "themes.txt"

# themes.txt 每行格式：
#   <slug>: <描述> | 核心公司: <t1>, <t2> | 關鍵字: <k1>, <k2> | 替代/反證關鍵字: <c1>, <c2>
_FIELD_LABELS = {
    "核心公司": "tickers",
    "關鍵字": "keywords",
    "替代/反證關鍵字": "counter_keywords",
}


class ThemeRegistryError(ValueError):
    """themes.txt 格式不合法。"""


@dataclass(frozen=True)
class Theme:
    slug: str
    description: str
    tickers: tuple[str, ...]
    keywords: tuple[str, ...]
    counter_keywords: tuple[str, ...]


def _compile(term: str) -> re.Pattern[str]:
    """逐字比對；ASCII 詞彙要求詞邊界，避免 InP 命中 input 這類子字串。"""

    escaped = re.escape(term.strip())
    if re.fullmatch(r"[\x00-\x7F]+", term.strip()):
        return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(escaped)


@lru_cache(maxsize=1)
def _patterns() -> Mapping[str, tuple[tuple[str, re.Pattern[str], bool], ...]]:
    """每個 theme 的 (term, pattern, is_counter) 清單。"""

    compiled: dict[str, tuple] = {}
    for slug, theme in load_themes().items():
        items = [(t, _compile(t), False) for t in theme.keywords + theme.tickers]
        items += [(t, _compile(t), True) for t in theme.counter_keywords]
        compiled[slug] = tuple(items)
    return compiled


@lru_cache(maxsize=1)
def load_themes(path: str | None = None) -> Mapping[str, Theme]:
    """讀 config/themes.txt；`#` 開頭與空行忽略。"""

    target = Path(path) if path else _DEFAULT_PATH
    if not target.exists():
        return {}
    themes: dict[str, Theme] = {}
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ThemeRegistryError(f"themes.txt 行缺少 slug 分隔：{line[:40]}")
        slug, rest = line.split(":", 1)
        slug = slug.strip()
        segments = [s.strip() for s in rest.split("|")]
        description = segments[0] if segments else ""
        fields: dict[str, tuple[str, ...]] = {
            "tickers": (),
            "keywords": (),
            "counter_keywords": (),
        }
        for segment in segments[1:]:
            if ":" not in segment:
                continue
            label, values = segment.split(":", 1)
            key = _FIELD_LABELS.get(label.strip())
            if key:
                fields[key] = tuple(
                    v.strip() for v in values.split(",") if v.strip()
                )
        themes[slug] = Theme(
            slug=slug,
            description=description,
            tickers=fields["tickers"],
            keywords=fields["keywords"],
            counter_keywords=fields["counter_keywords"],
        )
    return themes


def match_themes(*texts: str | None) -> dict[str, dict]:
    """回傳文字命中的主題與命中詞。

    每個主題記 `terms`（命中的正向詞）與 `counter_terms`（命中的反證詞）；
    只命中反證詞仍然算命中該主題，並標 `counter_only=True`。
    """

    blob = "\n".join(str(t) for t in texts if t)
    if not blob.strip():
        return {}
    result: dict[str, dict] = {}
    for slug, items in _patterns().items():
        hits: list[str] = []
        counter_hits: list[str] = []
        for term, pattern, is_counter in items:
            if pattern.search(blob):
                (counter_hits if is_counter else hits).append(term)
        if hits or counter_hits:
            result[slug] = {
                "terms": sorted(set(hits)),
                "counter_terms": sorted(set(counter_hits)),
                "counter_only": not hits and bool(counter_hits),
            }
    return result


def lead_themes(lead: Mapping) -> dict[str, dict]:
    """取一筆 lead 已存的主題命中；未標記過的即時推導。"""

    stored = lead.get("themes")
    if isinstance(stored, dict):
        return stored
    return match_themes(lead.get("title"), lead.get("raw_text"))


def related_by_theme(
    store: Mapping, lead_id: str, *, statuses: Iterable[str] = ("parked",)
) -> list[dict]:
    """找出與指定 lead 共用主題的其他 lead。

    與 `entities.related_leads` 互補：那一層要求共用具名標的，這一層只要求
    落在同一個已註冊主題，因此能接上「同主題但沒提到同一家公司」的關聯。
    """

    leads = store.get("leads") or {}
    target = leads.get(lead_id)
    if target is None:
        raise KeyError(f"未知 lead：{lead_id}")
    wanted = set(lead_themes(target))
    if not wanted:
        return []
    allowed = set(statuses)
    matches: list[dict] = []
    for other_id, other in leads.items():
        if other_id == lead_id or other.get("status") not in allowed:
            continue
        other_themes = lead_themes(other)
        shared = wanted & set(other_themes)
        if not shared:
            continue
        matches.append(
            {
                "lead_id": other_id,
                "status": other.get("status"),
                "shared_themes": sorted(shared),
                # 對方是否只以反證詞命中——那是最值得看的一類關聯
                "counter_only_themes": sorted(
                    s for s in shared if other_themes[s].get("counter_only")
                ),
                "title": str(other.get("title") or "")[:120],
                "url": other.get("url"),
            }
        )
    matches.sort(key=lambda m: (-len(m["shared_themes"]), m["lead_id"]))
    return matches


def backfill_themes(store: dict) -> int:
    """替尚未標記主題的既有 lead 補上；回傳更新筆數。"""

    updated = 0
    for lead in (store.get("leads") or {}).values():
        if isinstance(lead.get("themes"), dict):
            continue
        lead["themes"] = match_themes(lead.get("title"), lead.get("raw_text"))
        updated += 1
    return updated
