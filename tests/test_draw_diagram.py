"""示意圖畫圖器（scripts/draw_diagram.py）：斷行不拆英文字、避頭避尾、最後一行不只剩兩個字；
框中框下面那一行不壓框線（2026-10-08 截圖抓到、量測工具當時沒量這一項）；畫出來的 SVG 過得了載入檢查。
這裡用估計字寬檢查幾何；實際字框由 scripts/check_diagrams.py 用瀏覽器量。"""
from __future__ import annotations

import re
from xml.etree import ElementTree

from scripts.draw_diagram import ASC, DSC, X1, layout_problems, render, text_width, wrap
from webapp.diagrams import svg_problems

LPT = "圖上：HD 現代電氣、曉星重工、日立、Prolec GE、Delta Star、Virginia Transformer、Niagara、PTT（列舉不完整）"
MODULE = "發：DSP 把電訊號整理乾淨 → 驅動 → 雷射＋調變器把資料寫進光 → 光纖。收：光偵測器 → TIA 放大 → DSP。"
COLD_PLATE = "貼在晶片上的金屬板，冷卻液流過裡面的流道把熱帶走。"
EML = "Coherent、聯亞、Lumentum、華星光、Sivers、全新、穩懋（CW DFB）、Coherent、Lumentum、穩懋（EML）（列舉不完整）"


def test_wrapping_keeps_every_character_and_never_splits_a_latin_word() -> None:
    for text, size, width in ((LPT, 11, 312), (MODULE, 12.5, 312), (EML, 11, 200), ("快接頭：Stäubli、Parker", 11, 60)):
        lines = wrap(text, size, width)
        assert "".join(lines).replace(" ", "") == text.replace(" ", ""), text
        for word in re.findall(r"[A-Za-zÀ-ɏ]+", text):
            assert any(word in line for line in lines), (word, lines)
        assert all(text_width(line, size) <= width for line in lines if len(line) > 1), lines


def test_no_line_starts_with_closing_punctuation_or_ends_with_an_opening_one() -> None:
    for text, size, width in ((LPT, 11, 312), (MODULE, 12.5, 312), (EML, 11, 200), (EML, 11, 150), (LPT, 11, 120)):
        lines = wrap(text, size, width)
        assert not any(line[0] in "）」』、。，；：" for line in lines[1:]), lines
        assert not any(line[-1] in "（「『→" for line in lines[:-1]), lines


def test_an_arrow_moved_to_the_next_line_keeps_its_space() -> None:
    lines = wrap(MODULE, 12.5, 312)
    assert any(line.startswith("→ ") or " → " in line for line in lines)
    assert not any("→D" in line or "→T" in line for line in lines), lines


def test_the_last_line_is_not_left_with_one_or_two_characters() -> None:
    lines = wrap(COLD_PLATE, 12.5, 312)
    assert len(lines) == 2 and text_width(lines[-1], 12.5) >= 2.5 * 12.5, lines


def _estimated_boxes(svg: str):
    root = ElementTree.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    rects = [tuple(float(r.get(k)) for k in ("x", "y", "width", "height")) for r in root.iter(f"{ns}rect")]
    texts = []
    for t in root.iter(f"{ns}text"):
        size, x, base = float(t.get("font-size")), float(t.get("x")), float(t.get("y"))
        width = text_width(t.text or "", size)
        x = x - width if t.get("text-anchor") == "end" else x
        texts.append((t.text, (x, base - ASC * size, width, (ASC + DSC) * size)))
    return root, rects, texts


def test_text_under_a_box_inside_a_box_does_not_sit_on_its_border() -> None:
    layout = {"steps": [
        {"box": "heat", "title": "CDU（冷卻液分配單元）", "desc": "泵推動機櫃這一側的迴路；裡面的熱交換器把熱交給設施水。",
         "suppliers": ["AAON、奇鋐、雙鴻、CoolIT、台達、高力、Munters"],
         "inner": [{"title": "板式熱交換器", "desc": "兩種液體隔著一疊薄金屬板交換熱量。", "suppliers": ["Alfa Laval、Danfoss"]},
                   {"title": "套管", "desc": "絕緣管。", "suppliers": []}]},
        {"arrow": "熱交給設施水"},
        {"box": "gray", "title": "設施水", "desc": "熱最後由設施端排到室外。"},
    ]}
    svg = render(layout)
    assert svg_problems(svg) == []
    root, rects, texts = _estimated_boxes(svg)
    width, height = (float(v) for v in root.get("viewBox").split()[2:])
    frames = [r for r in rects if (r[2], r[3]) != (width, height)]
    assert len(frames) == 4
    meet = lambda a, b: a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]  # noqa: E731
    within = lambda a, b: a[0] >= b[0] and a[1] >= b[1] and a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3]  # noqa: E731
    for text, box in texts:
        assert box[0] + box[2] <= X1 + 8 and box[1] >= 0 and box[1] + box[3] <= height, text
        for frame in frames:
            assert not (meet(box, frame) and not within(box, frame)), (text, frame)
    for a, (ta, ba) in enumerate(texts):
        for tb, bb in texts[a + 1:]:
            assert not meet(ba, bb), (ta, tb)


def test_a_layout_that_cannot_be_drawn_says_what_is_wrong() -> None:
    assert layout_problems(None) and layout_problems({"steps": []})
    problems = layout_problems({"steps": [{"box": "neon", "title": "x"}, {"box": "heat"}, {"box": "heat", "title": "y",
                                                                                         "arrow": "z"},
                                          {"box": "gray", "title": "w", "inner": [{"desc": "沒有名字"}]}]})
    text = " ".join(problems)
    assert "neon" in text and "沒有名字" in text and "要嘛是 box" in text and "框中框" in text
    assert layout_problems({"steps": [{"box": "heat", "title": "冷板"}, {"arrow": ""}]}) == []
