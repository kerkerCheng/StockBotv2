---
name: detective
description: >
  偵探：一家公司的蒐證、拼線索與落帳。兩種叫法——「偵探 <代號>」只拼我們已經讀過的文件，找「公告計畫與分析師共識以外」的線索
  （量超前、漲價、撐更久、窗口提早關）；「做深 <代號>」先對外蒐證（公司、買方、對手、技術文件、媒體）、再拼線索、
  把新讀的存節錄、圖的洞登記成線索、敘事換版、等待登記，最後出一份蒐證包交給故事頁（skills/stock-story）。
  線索包是機械組的（圖上的鄰居＋點名它們的自家庫文件＋共識軌跡＋由鄰居角色產生的問句）→ 強模型唯讀子代理照 PROMPT.md 回報 →
  主 session 核引文。只在互動 session；不入圖、不鑄 pq2、不改候選狀態、不給目標價與排序、全程不看價格。
  當使用者說「偵探」「做深」「找破口」「計畫外的線索」「拼一下線索」「detective」，或研究 session 要回答「市場還沒寫進去的是什麼」時使用。
  觸發詞：偵探、做深、找破口、計畫外、拼線索、detective。
---

# Generated cross-agent adapter

Read `../../../skills/detective/SKILL.md` completely, then follow it as the authoritative skill.
Resolve its relative references from the canonical skill directory.
Do not add workflow rules here; edit the canonical skill and rerun
`python scripts/sync_agent_skills.py`.
