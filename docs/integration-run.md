# Integration Run — Step-by-Step (人工執行)

> 本檔是 U4 的執行檢查單。照順序做,每個 ✓ 打勾後再往下。

---

## 前置條件
- [ ] Docker Desktop 已啟動且 WSL2 整合已啟用(Windows 設定 → Docker → Resources → WSL Integration)
- [ ] `.env` 已建立(複製 `.env.example`,填入真實 `ANTHROPIC_API_KEY` 與 `NEO4J_PASSWORD`)
- [ ] `pip install neo4j jsonschema anthropic` 已完成

---

## Step 1 — 啟動 Neo4j + 載入樣本 (U1 驗收)

```powershell
# 在 repo 根目錄執行
docker compose up -d
# 等約 30 秒讓 Neo4j + APOC 完整起動
```

套 schema:
```powershell
Get-Content schema\neo4j_setup.cypher | docker exec -i stockbot-neo4j cypher-shell -u neo4j -p stockbot_dev_pw
```

載入手工樣本:
```powershell
python loader\load_to_neo4j.py samples\cpo_external_laser_source.json --apoc
```

### U1 驗收 (在 Neo4j Browser http://localhost:7474 跑)
```cypher
SHOW INDEXES;
-- 應看到 ≥4 個索引 (entity_id_unique, entity_type, entity_level, entity_role + fulltext + vector)

MATCH (n) RETURN count(n);
-- 應為 10 (9 Entity + 1 Claim)

MATCH ()-[r:SUPPLIES_TO]->() RETURN r.attributes;
-- 應看到 2 筆,各有 substitutability / lead_time_weeks / qualification_status

-- 冪等性測試:重跑 loader,節點數不增加
python loader\load_to_neo4j.py samples\cpo_external_laser_source.json --apoc
MATCH (n) RETURN count(n);
-- 仍為 10
```

---

## Step 2 — 準備一手資料 (U2 前置)

從以下來源選一篇,下載 CPO / external laser source 相關段落:

**優先(Tier 1 — 法說會逐字稿):**
- Coherent Corp 最近一季法說會 → 搜尋 CPO / co-packaged optics / external laser / ELS 段落
  IR: https://www.coherent.com/company/investor-relations
- Lumentum 最近一季法說會 → 同上
  IR: https://investor.lumentum.com
- Broadcom 最近一季法說會 → 搜尋 CPO / Tomahawk / AI ASIC 段落
  IR: https://investors.broadcom.com

**備選(Tier 2 — OFC/ECOC 論文):**
- OFC 2025 CPO session 論文(搜尋 "co-packaged optics OFC 2025")

**存檔方式:**
1. 只擷取 CPO/ELS 相關段落(手動剪貼),避免整份逐字稿塞爆 context window
2. 存到 `library/raw/<公司>_<季度>_cpo_section.txt`
   例: `library/raw/coherent_q3fy26_cpo.txt`
3. 在檔案最前面加一行原始來源注記:
   ```
   # Source: Coherent Corp Q3 FY2026 Earnings Call Transcript
   # URL: https://...
   # Retrieved: 2026-06-07
   ```

---

## Step 3 — 跑 extract.py (U3 驗收)

```powershell
python extract.py `
    --input "library/raw/coherent_q3fy26_cpo.txt" `
    --source-type transcript `
    --evidence-tier 1 `
    --title "Coherent Q3 FY2026 Earnings Call — CPO section" `
    --out "extractions/coherent_q3fy26_cpo.json"
```

驗證輸出:
```powershell
python loader\validate.py extractions\coherent_q3fy26_cpo.json
# 必須印出 OK,沒有 FAIL
```

若 validate 失敗:
- 先看錯誤訊息(SCHEMA / VOCAB / REF 哪層出問題)
- 若是 LLM 輸出問題:開 `extractions/coherent_q3fy26_cpo_raw.txt` 看原始回應
- 調整 `prompts/extract_system.md` 後重跑

---

## Step 4 — 載入圖 + 人工 review

```powershell
python loader\load_to_neo4j.py extractions\coherent_q3fy26_cpo.json --apoc
```

在 Neo4j Browser 跑:
```cypher
MATCH (n:Entity)-[r]->(m:Entity) RETURN n, r, m LIMIT 100;
```

**人工 review 清單:**
- [ ] 新節點數量合理?(不應有暴增的幻覺節點)
- [ ] `co:coherent` / `co:lumentum` / `co:broadcom` 有正確 MERGE 到既有節點?(不應出現 `co:coherent2` 等重複)
- [ ] 抽查 ≥3 條邊:找到 edge 的 `source_ids`,回去查 JSON 裡 sources 的 quote,確認 quote 支持這條關係
- [ ] 有沒有明顯幻覺(文件裡根本沒提到的關係)?

---

## Step 5 — 記錄 schema gap (U4 驗收)

把 review 發現的問題記進 `CLAUDE.md` 的 Lessons 區塊(下一個 L 編號):

```markdown
### L6 — [本次抽取發現的問題]
**事發:** [描述]
**通用判準:**
1. [如何避免]
```

例子可能包含:
- 需要新的 `relation` 字彙(例如 `co_develops_with`)
- `abstraction_level` 指定模糊(某技術歸哪層不明確)
- LLM 傾向把時變數字(季度 revenue guidance)誤放進 node attributes
- entity ID naming 衝突(同一公司出現兩種拼法)

---

## 完成標準

全部 ✓ 後,第一條垂直切片 v0 完成:
- [ ] Step 1 四項 U1 驗收全過
- [ ] extract.py 輸出通過 validate.py (無 FAIL)
- [ ] 載入後與樣本節點正確 MERGE(無重複)
- [ ] ≥3 條邊的 quote 審核通過
- [ ] CLAUDE.md 已補 L6(或更高編號)schema gap 記錄
