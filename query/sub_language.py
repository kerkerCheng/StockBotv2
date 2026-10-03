"""sub 引文含不含可替代性語言——`sub_language_in_quote` 旗標的唯一 owner（2026-10-01 Phase 4 Step 4.4b）。

為什麼（ROADMAP Phase 4 A3）：抽取提示要求 `substitutability` 等屬性**只在文件真的談到可替代性、替代品認證或
排他性時**才填（`prompts/extract_system.md` 的 Unsupported-attribute rule）；猜出來的值會讓目標看起來**更像**瓶頸，
而那正是人工覆核不會覺得怪的方向。這個旗標回答一個機械問題：撐住這個 sub 的引文裡，有沒有一個字在談可替代性。

- 字表住 `config/substitutability_language.json`（版本化；寬窄兩版都存、只用 `active` 那一版並記名）。
- **只印、不放閘**：旗標不改任何 sub、不進 `candidates`、不寫投影 meta、不改 `collapse_assertions`——量到的是
  「引文措辭」，不是「sub 對不對」（L14：先量測後放閘；準確率抽樣見 Step 4.4 的八欄）。
- 消費端：結構表每條邊的 `assertions_without_sub_language`（`query.bottleneck.structure_table`）、層計數器 ③
  （`query.layer_stats`）、RA packet 的警告（`intake.actions.check_sub_language`）——都問這裡，不各寫一份（L16）。
  Phase 6 Step 6.5 起旗標**跟著值**走到消費端（`canonical_sub_language`：贏得 sub 值的那一筆）：結構表的
  `sub_language_in_quote` 一格、`query.structure` 五個角度的邊、走圖第 1 型的「需求側 sub≥4 其中引文撐得住 N」、
  個股讀取模型「替代難度」的旁註。⚠ 旗標與字表版本都**不進**讀圖的 `result_digest` 與 staleness 快照列——
  字表升版不能讓讀圖變 stale（量到的會是我們的程式改版，不是圖）。
- ⚠ L19：字表**不得**出現在 `prompts/`、`skills/`——抽取端讀得到字表，就會挑含這些字的引文，旗標就恆亮
  （`tests/test_sub_language.py` 守著）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parent.parent
LANGUAGE_PATH = ROOT / "config" / "substitutability_language.json"

#: 中日韓字元：沒有空白分詞，整串出現即算（與 `query.bottleneck._CJK` 同一個範圍）。
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯]")


class LanguageConfigError(ValueError):
    """字表設定檔形狀不合規——fail closed，不帶著壞字表算旗標。"""


@dataclass(frozen=True)
class SubLanguage:
    version: int
    variant: str
    terms: tuple[str, ...]

    @property
    def label(self) -> str:
        """印在每個計數器旁邊的字表版本（「這個數是用哪一版字表量的」）。"""
        return f"v{self.version}·{self.variant}"


def _term_pattern(term: str) -> re.Pattern[str]:
    if _CJK.search(term):
        return re.compile(re.escape(term))
    # ASCII 整詞、不分大小寫；不用 `\b`——Python 把中文字算 word 字元，「是唯一的second source」會漏抓。
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(term) + r"(?![A-Za-z0-9_])", re.IGNORECASE)


@lru_cache(maxsize=4096)
def _compiled(term: str) -> re.Pattern[str]:
    return _term_pattern(term)


def _variant_terms(variants: Mapping[str, Any], name: str, *, seen: tuple[str, ...] = ()) -> list[str]:
    if name in seen:
        raise LanguageConfigError(f"variants 的 extends 成環：{' → '.join(seen + (name,))}")
    body = variants.get(name)
    if not isinstance(body, Mapping):
        raise LanguageConfigError(f"variants 沒有 {name!r}")
    terms: list[str] = []
    base = body.get("extends")
    if base:
        terms.extend(_variant_terms(variants, str(base), seen=seen + (name,)))
    for category, values in body.items():
        if category == "extends":
            continue
        if not isinstance(values, list) or not all(isinstance(v, str) and v.strip() for v in values):
            raise LanguageConfigError(f"variants.{name}.{category} 必須是非空字串的 list")
        terms.extend(v.strip() for v in values)
    return terms


def load_language(path: Path | None = None, *, variant: str | None = None) -> SubLanguage:
    """讀字表。`variant` 不給就用設定檔的 `active`（寬窄兩版都存，只用一版——記名就是 `label`）。"""
    source = path or LANGUAGE_PATH
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LanguageConfigError(f"{source}：讀不到或不是 JSON（{exc}）") from exc
    if not isinstance(data, Mapping) or data.get("schema_version") != 1:
        raise LanguageConfigError(f"{source}：schema_version 必須是 1")
    version = data.get("version")
    if not isinstance(version, int) or version < 1:
        raise LanguageConfigError(f"{source}：version 必須是正整數")
    history = data.get("_history")
    if not isinstance(history, list) or not any(isinstance(h, Mapping) and h.get("version") == version
                                                for h in history):
        raise LanguageConfigError(f"{source}：_history 沒有 version {version} 的那一行——改字表要記一筆")
    variants = data.get("variants")
    if not isinstance(variants, Mapping):
        raise LanguageConfigError(f"{source}：variants 必須是物件")
    name = variant or str(data.get("active") or "")
    terms = _variant_terms(variants, name)
    folded = [t.casefold() for t in terms]
    duplicates = sorted({t for t in folded if folded.count(t) > 1})
    if duplicates:
        raise LanguageConfigError(f"{source}：{name} 有重複的詞 {duplicates}")
    return SubLanguage(version=version, variant=name, terms=tuple(terms))


@lru_cache(maxsize=1)
def get_language() -> SubLanguage:
    """正式字表（每個行程讀一次）。測試要換字表請把 `language=` 傳進消費端。"""
    return load_language()


def matched_terms(text: str | None, *, language: SubLanguage | None = None) -> list[str]:
    """這段文字命中的詞（給抽樣與稽核看「憑哪個字」——L18：標籤要指得回原文）。"""
    lang = language or get_language()
    body = str(text or "")
    if not body:
        return []
    return [term for term in lang.terms if _compiled(term).search(body)]


def quote_has_sub_language(quotes: Iterable[str | None] | str | None, *,
                           language: SubLanguage | None = None) -> bool:
    """這組引文（或一段引文）有沒有任何一個字在談可替代性／替代品認證／排他性。沒有引文＝False。"""
    if quotes is None:
        return False
    items = [quotes] if isinstance(quotes, str) else list(quotes)
    return any(matched_terms(q, language=language) for q in items)


def fetch_all_quotes(session) -> dict[str, list[str]]:
    """每一筆 EdgeAssertion 的逐字（`QUOTES`）——按 assertion id 收。

    ⚠ **不得**把這個 QUOTES join 塞進 `query.bottleneck.fetch_assertions`：一筆 assertion 掛幾段逐字就會多出幾列，
    `collapse_assertions` 的 `documents` 計數會被灌大（plan §5 b）。所以另開一條查詢、在 Python 端對 id。
    """
    out: dict[str, list[str]] = {}
    for record in session.run("MATCH (ea:EdgeAssertion)-[:QUOTES]->(s:Source) "
                              "RETURN ea.id AS id, collect(DISTINCT s.quote) AS quotes"):
        out[str(record["id"])] = [str(q) for q in record["quotes"] or () if q]
    return out


def sub_value(row: Mapping[str, Any]) -> Any:
    """一筆 assertion 的 substitutability（`attributes` 可能是 JSON 字串）；沒有就 None。"""
    from query.bottleneck import parse_attributes

    value = parse_attributes(row.get("attributes")).get("substitutability")
    if isinstance(value, bool):          # bool 是 int 的子類；sub 從來不是布林
        return None
    return value


def canonical_sub_language(edge: Any, flags: Mapping[str, bool] | None) -> bool | None:
    """一條 canonical 邊的 sub 旗標＝**贏得 sub 值的那筆 assertion**（`CanonicalEdge.sub_assertion_id`）的旗標
    （Phase 6 Step 6.5：旗標跟著值走——印的 sub 是哪一筆給的，就印那一筆的引文撐不撐得住）。

    同一條邊另一筆引文撐得住、但 confidence 較低（沒贏得值）→ 仍印贏家那筆的旗標，不挑好看的那一筆。
    回 None 而不是 False 的三種情況：這條邊沒有 sub、這次沒核對（`flags` 是 None）、贏家那筆沒有 id（對不到引文）——
    「沒有旗標」與「引文不撐」不得同形（L12）。**只印、不改值、不進讀圖 digest**（plan §0 第 6 條）。
    """
    if flags is None or getattr(edge, "substitutability", None) is None:
        return None
    aid = getattr(edge, "sub_assertion_id", None)
    return flags.get(str(aid)) if aid else None


def sub_language_flags(rows: Iterable[Mapping[str, Any]], quotes_by_assertion: Mapping[str, Iterable[str]], *,
                       language: SubLanguage | None = None) -> dict[str, bool]:
    """每一筆**帶 sub 的** assertion → 它的引文有沒有可替代性語言（`sub_language_in_quote`）。

    沒有 `assertion_id` 的列無從對引文——不靜默當成 False，直接略過（呼叫端看 `len()` 對得上帶 sub 的列數）。
    沒有任何逐字的帶 sub assertion＝False（沒有引文就沒有措辭撐住它）。
    """
    lang = language or get_language()
    flags: dict[str, bool] = {}
    for row in rows:
        if sub_value(row) is None:
            continue
        aid = row.get("assertion_id")
        if not aid:
            continue
        flags[str(aid)] = quote_has_sub_language(quotes_by_assertion.get(str(aid)) or (), language=lang)
    return flags


__all__ = [
    "LANGUAGE_PATH", "LanguageConfigError", "SubLanguage", "canonical_sub_language", "fetch_all_quotes",
    "get_language", "load_language", "matched_terms", "quote_has_sub_language", "sub_language_flags", "sub_value",
]
