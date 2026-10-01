"""company-onboard 與 research-drain 的可執行行（Phase 4 Step 4.5c）。

守三件事：
1. onboard 沒有任何一步直接寫 Neo4j——入圖只經 prepare → pq2 `ra_admission` → apply 固定入口（四個人工 gate 之一）。
2. skill 裡寫的每一行指令，拿真的 argparse 解析得過——旗標改名或拿掉時這裡紅，不是等下一個 session 照著跑才撞牆。
3. onboard 先答「坐哪一層」、不留份數門檻（份數是讀了多少文件，不是證據強度）。
"""
from __future__ import annotations

import importlib.util
import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ONBOARD = ROOT / "skills" / "company-onboard" / "SKILL.md"
DRAIN = ROOT / "skills" / "research-drain" / "SKILL.md"


def _code_lines(path: Path) -> list[str]:
    """fenced code block 裡的每一行（skill 的「可執行行」；註解行不算）。"""
    lines, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside and line.strip() and not line.strip().startswith("#"):
            lines.append(line.strip())
    return lines


def _argv(line: str, prefix: str) -> list[str]:
    """去掉指令前綴、把 `<佔位>` 換成形狀正確的值，切成 argv（行尾的 `# 註解` 不算）。"""
    body = re.sub(r"\s+#\s.*$", "", line)
    body = body[body.index(prefix) + len(prefix):]
    for placeholder, value in {"<1-4>": "2", "<type>": "news", "<編號>": "663", "<action_digest>": "a" * 64}.items():
        body = body.replace(placeholder, value)
    return shlex.split(re.sub(r"<[^<>]+>", "x", body), posix=True)


def test_onboard_never_loads_the_graph_directly_and_goes_through_the_admission_entry() -> None:
    lines = _code_lines(ONBOARD)
    assert not any("load_to_neo4j" in line for line in lines)
    assert any("prepare_research_action" in line for line in lines)
    assert any("apply_ra_admission.py" in line for line in lines)
    text = ONBOARD.read_text(encoding="utf-8")
    assert "TICKER_MAP" not in text and "config/company_identity.json" in text


def test_onboard_asks_for_the_layer_first_and_keeps_no_document_count_threshold() -> None:
    text = ONBOARD.read_text(encoding="utf-8")
    step1 = text[text.index("## Step 1"):text.index("## Step 2")]
    assert "坐在圖上的哪一層" in step1 and "system-decompose" in step1
    assert not re.search(r"<N>/3|N/3|≥ ?3 才能", text), "份數門檻已退役——說缺哪一類，不是數份數"
    assert "layer_enumerations" in text


def test_every_extract_and_entry_line_in_the_onboard_skill_parses() -> None:
    import extract

    extract_lines = [l for l in _code_lines(ONBOARD) if l.startswith("python extract.py")]
    assert len(extract_lines) == 2
    parsed = [extract.build_parser().parse_args(_argv(l, "python extract.py")) for l in extract_lines]
    assert parsed[0].scaffold and parsed[1].response and parsed[1].out

    spec = importlib.util.spec_from_file_location("apply_ra_admission_skillcheck",
                                                  ROOT / "scripts" / "apply_ra_admission.py")
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    apply_line = next(l for l in _code_lines(ONBOARD) if "apply_ra_admission.py" in l)
    args = entry.build_parser().parse_args(_argv(apply_line, "scripts/apply_ra_admission.py"))
    assert args.pq2 == 663 and args.digest == "a" * 64

    from engine_b.todo import main as todo_main  # noqa: F401 —— 指令存在即可（sync 不在這裡真的跑）
    assert any(l.startswith("python -m engine_b.todo sync") for l in _code_lines(ONBOARD))


def test_research_drain_graph_walk_lines_parse_with_the_real_cli() -> None:
    """research-drain 段 4 ② 的鑄號三行（register／annotate／triage）拿 `engine_b.cli.build_parser()` 解析。"""
    from engine_b.cli import build_parser

    commands = {}
    for line in (l for l in _code_lines(DRAIN) if "-m engine_b.cli " in l):
        args = build_parser().parse_args(_argv(line, "-m engine_b.cli"))
        commands[args.command] = args
    assert {"register", "annotate", "triage"} <= set(commands)
    assert commands["register"].source == "graph_walk:sole_supplier_self_reported"
    assert any(r.startswith("graph_walk_subject=") for r in commands["annotate"].ref)
    assert commands["triage"].classified_by == "interactive:graph_walk"
