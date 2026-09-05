"""把 Engine D 的決策摘要與各 domain 的 pane 組成一份今日 brief。

輸出 DTO 的形狀與 B6 之前一字未改——`decision_lab today`、MCP 的
`get_decision_brief`、`engine_b todo sync` 讀的都是同一份 payload。改的只是
**誰算出每一塊**。
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from alpha.brief import build_ready_not_ranked
from decision_lab.brief import build_decision_brief, cohort_company_ids
from decision_lab.store import DecisionStore
from decision_lab.workflow_ports import WorkflowDataProvider
from identity.registry import IdentityRegistry, get_registry
from portfolio.brief import build_sheet_only_items

from .sources import (
    fetch_alpha_position_events,
    load_backup_status,
    load_outcome_aggregate,
)

__all__ = ["build_today_brief"]


def build_today_brief(
    store: DecisionStore,
    *,
    as_of: str,
    current_holdings: Mapping[str, Any] | None = None,
    change_context_by_cohort: Mapping[str, Mapping[str, Any]] | None = None,
    portfolio_context_by_cohort: Mapping[str, Mapping[str, Any]] | None = None,
    current_authority_by_cohort: Mapping[str, Mapping[str, Any]] | None = None,
    provider: WorkflowDataProvider | None = None,
    registry: IdentityRegistry | None = None,
    alpha_series_by_ticker: Mapping[str, Any] | None = None,
    ranking: Mapping[str, Any] | None = None,
    nav_exposure: Mapping[str, Any] | None = None,
    identity_alignment: Mapping[str, Any] | None = None,
    alpha_cards: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """掃描 cohorts／decisions 與當前 Sheet snapshot；不寫入任何 authority。

    `ranking`（`alpha.ranking.build_ranking_view` 的輸出）與 `nav_exposure`
    （`portfolio.exposure.build_nav_exposure` 的輸出）由呼叫端注入——前者需要
    Neo4j、後者需要 Google Sheet，取數住 `engine_d_runtime.adapters`。兩者缺席時
    首屏照常渲染，只是那兩區明說「未提供」；**不得因此讓整份 brief 失敗，也不得
    讓「沒注入」與「沒有東西」同形**（L12）。
    """

    registry = registry or get_registry()
    if provider is not None and current_holdings is None:
        try:
            current_holdings = provider.current_holdings(evaluation_at=as_of)
        except Exception:
            current_holdings = {"status": "unavailable"}

    # ⚠ 順序有意義：先問 Engine D「哪些公司已經有人負責」，再由 Portfolio 判斷
    # 剩下的 Sheet 持股誰沒人看。這條鏈漏一環，持股就會從 pq2 待辦池消失
    #（`engine_b todo sync → public_view → 這裡`），所以
    # `build_decision_brief` 把 `sheet_only_items` 設成必填而非可選。
    sheet_only_items = build_sheet_only_items(
        current_holdings,
        cohort_company_ids=cohort_company_ids(store, as_of=as_of),
        registry=registry,
    )

    brief = build_decision_brief(
        store,
        as_of=as_of,
        sheet_only_items=sheet_only_items,
        current_holdings=current_holdings,
        change_context_by_cohort=change_context_by_cohort,
        portfolio_context_by_cohort=portfolio_context_by_cohort,
        current_authority_by_cohort=current_authority_by_cohort,
        provider=provider,
    )

    # 系統終點：瓶頸排序在前、NAV 比例在後。兩者都是注入的（見 docstring）。
    panes: dict[str, Any] = {
        "ranking": dict(ranking) if ranking else None,
        "ready_not_ranked": build_ready_not_ranked(brief["items"], ranking),
        # Alpha Card 精簡摘要（2026-09-05）：由 `briefing.alpha_view` 的 canonical view 經
        # `compact_card` 選取而來，呼叫端注入（取數要 Neo4j＋Engine C＋Decision Store）。
        # None＝未注入／整批讀取失敗，不與「排序內沒有候選」的空 list 混用（L12）。
        "alpha_cards": [dict(card) for card in alpha_cards] if alpha_cards is not None else None,
        "nav_exposure": dict(nav_exposure) if nav_exposure else None,
        # 公司三集合對齊常駐計數器（2026-09-02 使用者稽核定案）：圖∖registry 是
        # join-key 契約破口（應恆 0），registry∖圖 是登記未研究。None＝呼叫端未注入
        #（如遠端受限 surface），不與「對齊為 0」混用。
        "identity_alignment": (
            dict(identity_alignment) if identity_alignment is not None else None
        ),
        # Alpha live 部位的事件監控。與 `capital_expression` 同一個窄 duck-type
        # 契約：surface 不提供就是 None，不與「有部位但沒事」的空 list 混用。
        "alpha_position_events": fetch_alpha_position_events(
            store, series_by_ticker=alpha_series_by_ticker
        ),
        # 備份計數器：private authority「最後一次備份 N 天前」必須自己出現在首屏
        # （L14——靠人記得跑 scripts/backup_private.py 的段落就是會被忘記的段落）。
        # None 只代表這個 surface 沒有 private root，不與「從未備份」混用（L12）。
        "backup_status": load_backup_status(),
        # 排序品質計數器（2026-09-02）：讀 outcome_if_settled_today 落的狀態檔，
        # 不在 brief 生成時重打行情 API。None＝從未量測（檔不存在），現形於缺席。
        "outcome_aggregate": load_outcome_aggregate(),
    }

    # 鍵序維持 B6 之前的 `decision_lab today --format json` 輸出：排序／NAV 在
    # 決策欄位之前，items 永遠在最後。
    assembled: dict[str, Any] = {}
    for key in ("schema_version", "as_of"):
        assembled[key] = brief[key]
    for key in ("ranking", "ready_not_ranked", "alpha_cards", "nav_exposure"):
        assembled[key] = panes[key]
    for key in (
        "action_needed", "attention", "reason", "alpha_thesis_changes",
        "beta_portfolio_risk", "blockers", "next_review_at",
        "identity_registration_pending", "user_response_needed",
        "capital_expression",
    ):
        assembled[key] = brief[key]
    for key in (
        "identity_alignment", "alpha_position_events", "backup_status",
        "outcome_aggregate",
    ):
        assembled[key] = panes[key]
    assembled["items"] = brief["items"]
    return assembled
