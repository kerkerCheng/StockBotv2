"""今日 brief 的 Markdown：串各 pane 的 renderer ＋ Engine D 自己的決策段落。

由同一份 public DTO 產生，不接觸 private payload。每個 item 帶穩定編號 [N] 供
對話式批次核准引用（plan R5）；顯示自追蹤變化%與 evidence_delta，不使用顏色維度
（plan R15）。

⚠ 段落順序本身是契約（`tests/test_today_first_screen.py`／`test_decision_brief.py`
／`test_daily_brief_skill.py` 斷言首屏出現哪些 token）。要改就換 token，
**刪掉等於失去剎車**。
"""
from __future__ import annotations

from typing import Any, Mapping

from alpha.brief import (
    render_outcome_aggregate,
    render_position_events,
    render_ranking,
    render_ready_not_ranked,
)
from decision_lab.action_card import assert_safe_payload
from portfolio.brief import render_nav_exposure
from shared.markdown import markdown_text, pct

__all__ = ["render_today_markdown"]


def _render_capital_expression(counters: Mapping[str, Any]) -> list[str]:
    """研究進展常駐計數器（廣度、量測）。"""
    lines: list[str] = []
    measured = int(counters.get("measured_outcomes") or 0)
    outcomes = int(counters.get("outcomes") or 0)
    measurable = int(counters.get("shadow_measurable_cohorts") or 0)
    anchored = int(counters.get("shadow_anchored_cohorts") or 0)
    # 量測以 Shadow 錨點為準，不以 outcome_envelopes 為準：後者要人工 close 才有列，
    # 且 2026-08-15 實測 8 筆有 6 筆來自無 ticker 的廢棄 cohort，永遠算不出報酬。
    # 拿它當分母會每天喊「已量測 0/8」，而事實是 9 個有錨點的 cohort 全部可量測。
    eligible = int(counters.get("eligible_cohorts") or 0)
    total_cohorts = int(counters.get("total_cohorts") or 0)
    # 首屏只放使用者實際在盯的三條（ROADMAP 新 workstream）：廣度、量測。
    # 舊的「非零 live 區間 N/決策數」已移除：尺寸不再對人呈現（Alpha 呈現契約），
    # 且它的分母數的是歷來 decision，同一標的每 reassess 一次就 +1。
    # 單位是「有 identity 的公司」不是 cohort：無 company_id 的殘骸與同公司的
    # 重複 cohort 都不計，否則分母會謊報「還有救得回來的標的」。
    legacy_eligible = int(counters.get("legacy_eligible_cohorts") or 0)
    line = (
        f"- 研究進展：上線標的 {eligible}/{total_cohorts} 檔"
        f"｜可量測 {measurable}/{anchored} 檔"
    )
    # 舊判準的殘量分開講，不加進上面那個數字——合起來會讓「換判準」看起來像「有進展」。
    if legacy_eligible:
        line += f"（另有 {legacy_eligible} 檔仍為 U7 前判準，reassess 後才會重算）"
    if eligible == 0 and total_cohorts and not legacy_eligible:
        line += "　⚠ 目前沒有任何可評估標的"
    lines.append(line)
    # 提醒各自一行：主行是狀態、子行是待處理項。串在同一行會長到手機讀不完，
    # 而且會讓「數字」與「要做的事」混在一起。exception-first，沒問題就不出現。
    #
    # 公司已上線但底下有重複 cohort：不影響上線比率，但要有人去合併／結案，
    # 否則 Decision Store 會長出兩條互不知道的軌跡（ROADMAP backlog）。
    # 以公司為單位計數是對的，但不能因此把它藏起來——那是把缺陷掃到地毯下。
    dupes = tuple(counters.get("duplicate_cohort_companies") or ())
    if dupes:
        names = "、".join(markdown_text(name) for name in dupes[:3])
        more = f" 等 {len(dupes)} 檔" if len(dupes) > 3 else ""
        lines.append(f"  - ⚠ {names}{more} 有重複 cohort，待合併")
    orphans = int(counters.get("orphan_cohorts") or 0)
    if orphans:
        lines.append(
            f"  - ℹ {orphans} 個無 identity 的 cohort 殘骸；不計入分母，"
            "但仍在 outcome_envelopes 裡（Decision Store append-only，不刪除）"
        )
    if measurable == 0:
        lines.append("  - ⚠ 判斷準不準仍無法用證據回答（無 Shadow 錨點）")
    elif measured == 0 and outcomes:
        # 有錨點就算得出報酬，但尚未有任何 probe 正式結案歸因。
        lines.append(
            f"  - ℹ 報酬可量測但尚無結案歸因（outcome_envelopes {measured}/{outcomes}）；"
            "跑 `scripts/outcome_if_settled_today.py` 看目前表現"
        )
    return lines


def _render_identity_alignment(alignment: Mapping[str, Any]) -> list[str]:
    """公司對齊常駐計數器（2026-09-02）。

    洩漏（圖∖registry）應恆 0——非 0 逐一列出並附修法；registry∖圖 只計數現形。
    """
    leaked = list(alignment.get("graph_not_in_registry") or ())
    unresearched = int(alignment.get("registry_not_in_graph_count") or 0)
    if leaked:
        names = "、".join(markdown_text(x) for x in leaked[:5])
        more = f" 等 {len(leaked)} 個" if len(leaked) > 5 else ""
        return [
            f"- 🔴 公司對齊：圖中 {names}{more} 不在 registry——join-key 契約破口，"
            "補 `config/company_identity.json` 條目（private 也要 null 條目）"
        ]
    return [
        f"- 公司對齊：圖∖registry 0（✓）｜registry 已登記未入圖 {unresearched} 家"
        f"（圖 {alignment.get('graph_companies')}／registry "
        f"{alignment.get('registry_companies')}）"
    ]


def _render_backup_status(backup: Mapping[str, Any]) -> list[str]:
    """備份計數器：「從未備份」與「狀態檔壞掉」都必須現形，不得靜默（L12／L14）。"""
    backup_state = str(backup.get("status") or "")
    if backup_state == "never":
        return ["- 🔴 最後一次備份：從未備份——跑 `python scripts/backup_private.py run`"]
    if backup_state == "invalid":
        return [
            "- 🔴 最後一次備份：狀態檔無法解讀（library/private/backups/"
            "last_backup.json），視同沒有備份處理"
        ]
    age = int(backup.get("age_days") or 0)
    drive_status = str(backup.get("drive_status") or "unknown")
    notes = [
        "Drive ✓" if drive_status == "uploaded" else f"Drive 🔴 {markdown_text(drive_status)}",
        "restore 已驗證" if backup.get("restore_verified") else "restore 🔴 未驗證",
    ]
    marker = "🔴 " if age > 7 or drive_status != "uploaded" else ""
    return [f"- {marker}最後一次備份：{age} 天前（{'，'.join(notes)}）"]


def _render_items(items: list[Any]) -> list[str]:
    """帶穩定編號的待辦清單——使用者回覆 `1 3 7 go` 引用的就是這裡的 [N]。"""
    if not items:
        return []
    lines = ["", "## 項目（回覆用編號）"]
    for item in items:
        idx = item.get("index")
        # Sheet-only 持股常無 registry 對應，company_id 會是 unresolved；
        # 顯示 ticker 才看得出是哪一檔。
        label = item.get("company_id") or ""
        if str(label) in {"", "unresolved"} and item.get("ticker"):
            label = item["ticker"]
        company = markdown_text(label)
        attention = "需要複查" if item.get("attention") == "REVIEW" else "監控中"
        perf = pct(item.get("performance_since_tracked"))
        since_decision = pct(item.get("performance_since_decision"))
        delta = markdown_text(item.get("evidence_delta") or "none")
        lines.append(
            f"- [{idx}] {attention} — {company}｜自追蹤 {perf}"
            f"（決策後 {since_decision}）｜證據 {delta}"
        )
        resp = markdown_text(item.get("user_response_needed") or "")
        if resp:
            lines.append(f"      → {resp}")
        # variant perception（2026-09-02）：REVIEW 項第一眼要看到「市場隱含 vs
        # 本 thesis」；沒寫就顯示（未寫）現形——那是待辦，不是可以省略的欄。
        vp = item.get("variant_perception")
        if "variant_perception" in item:
            if vp:
                lines.append(f"      → 差異點：{markdown_text(str(vp))}")
            elif item.get("attention") == "REVIEW":
                lines.append(
                    "      → 差異點：（未寫 variant perception——"
                    f"`decision_lab variant-perception {item.get('cohort_id')} --text …`）"
                )
        disproof = markdown_text(item.get("disproof_condition") or "")
        if disproof:
            lines.append(f"      → Disproof：{disproof}")
    return lines


def _render_live_entry(items: list[Any], capital: Mapping[str, Any]) -> list[str]:
    """live 入口。

    2026-08-18 紅隊審查 B8：`record-choice --user-sized` 蓋好了，但**沒有任何入口**
    ——brief 不提、todo pool 不提、Action Card 不提，它是一個使用者必須自己記得的
    CLI。這一段把「要記得」變成「看得到」。

    ⚠ 這**不是**行動指引，不違反 Alpha 呈現契約：指令裡的 `--selected-weight` 刻意
    留空給使用者填，brief 不提供任何建議尺寸；系統也不判斷現在該不該買。
    它只解決一件事：真的決定要買的時候，有地方可以記錄，記分板才可能有資料。

    ⚠ live 筆數必須動態取（2026-09-02 修正）：原版把 08-18 當時的實測值「0 筆」
    寫死在字串裡，使用者走完第一筆 choice→fill 後 footer 仍喊 0，與 outcome
    surface 直接矛盾——「現況數字會過期，判準不會」的程式版。
    """
    actionable = [
        item
        for item in items
        if item.get("decision_id")
        and str(item.get("company_id") or "") not in {"", "unresolved"}
    ]
    if not actionable:
        return []
    n_choices = capital.get("live_choices")
    n_fills = capital.get("live_fills")
    scoreboard = (
        f"——目前 `live_choices` {n_choices} 筆／fill {n_fills} 筆"
        if isinstance(n_choices, int) and isinstance(n_fills, int)
        else ""
    )
    lines = [
        "",
        "## 若你今天決定進場／加碼（指令，不是建議）",
        "",
        "尺寸由你決定；系統不建議金額，也不判斷時點。記錄下來只為了讓「判斷準不準」"
        f"日後能用證據回答{scoreboard}。",
        "",
    ]
    for item in actionable[:8]:
        label = markdown_text(item.get("ticker") or item.get("company_id"))
        lines.append(
            f"- **{label}**：`python -m decision_lab record-choice "
            f"{item['decision_id']} --selected-weight <你的NAV占比> "
            f"--explicit --user-sized --reason \"<為什麼是這個尺寸>\" "
            f"--confirmation-ref \"<你的紀錄編號>\"`"
        )
    lines.append(
        "\n成交後再回報：`python -m decision_lab record-fill <decision_id> "
        "--execution-ref <券商成交編號> --shares <股數> --price <成交價> "
        "--currency <幣別> --explicit`"
    )
    lines.append(
        "⚠ decision 凍結超過 7 天會被拒絕（資本上限讀的是凍結當時的持股快照）；"
        "先跑 `decision_lab reassess` 重新凍結。"
    )
    return lines


def render_today_markdown(brief: Mapping[str, Any]) -> str:
    """由同一 public DTO 產生 Markdown；不接觸 private payload。"""

    assert_safe_payload(brief)
    blockers = "、".join(markdown_text(item) for item in brief.get("blockers") or []) or "無"
    # 首屏是瓶頸排序——系統的終點是「哪些標的值得看」，不是「今天要不要動作」。
    lines = render_ranking(brief.get("ranking"))
    lines += render_ready_not_ranked(brief.get("ready_not_ranked"))
    lines += render_nav_exposure(brief.get("nav_exposure"))
    lines += [
        f"# 今天需要動作嗎？{'是' if brief['action_needed'] else '否'}",
        "",
        f"- 注意力：{'需要複查' if brief['attention'] == 'REVIEW' else '監控中'}",
        f"- 原因：{markdown_text(brief['reason'])}",
        f"- Blockers：{blockers}",
        f"- 下一個 review：{markdown_text(brief.get('next_review_at') or '尚未排定')}",
    ]
    lines += render_position_events(brief.get("alpha_position_events"))
    counters = brief.get("capital_expression") or {}
    if counters:
        lines += _render_capital_expression(counters)
    alignment = brief.get("identity_alignment")
    if alignment:
        lines += _render_identity_alignment(alignment)
    lines += render_outcome_aggregate(
        brief.get("outcome_aggregate"),
        measured_key_present="outcome_aggregate" in brief,
    )
    backup = brief.get("backup_status")
    if backup:
        lines += _render_backup_status(backup)
    items = brief.get("items") or []
    lines += _render_items(items)
    lines += _render_live_entry(items, counters)

    pending_identity = brief.get("identity_registration_pending") or []
    if pending_identity:
        lines += [
            "",
            "## 結構性阻塞：等 registry 補可交易 ticker（研究無法解決）",
        ]
        for row in pending_identity:
            company = markdown_text(row.get("company_id") or "")
            action = markdown_text(row.get("blocking_action") or "")
            state = "已登記但無 ticker" if row.get("registered") else "尚未登記"
            lines.append(f"- {company}（{state}）→ {action}")
    lines += [
        "",
        "## 需要你回答或回報",
        "\n".join(
            f"- {markdown_text(item)}" for item in brief.get("user_response_needed") or []
        ) or "- 無",
    ]
    return "\n".join(lines)
