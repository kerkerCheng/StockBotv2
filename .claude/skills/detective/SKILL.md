---
name: detective
description: >
  偵探：把我們已經讀過的文件拼起來，找一家公司「公告計畫與分析師共識以外」的線索——量超前、漲價、撐更久、窗口提早關。
  機械組線索包（圖上的鄰居＋點名它們的自家庫文件＋共識軌跡＋由鄰居角色產生的問句）→ 強模型唯讀子代理照 PROMPT.md 回報 →
  主 session 核引文 → 核過的線索寫進敘事的量級段、每條登 watch。只在互動 session；不入圖、不鑄 pq2、不改候選狀態、
  不給目標價與排序、不看價格。當使用者說「偵探」「找破口」「計畫外的線索」「拼一下線索」「detective」，
  或研究 session 要回答「市場還沒寫進去的是什麼」時使用。觸發詞：偵探、找破口、計畫外、拼線索、detective。
---

# Generated cross-agent adapter

Read `../../../skills/detective/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
