// Neo4j v0.1 建模 — 約束 / 索引 / 向量索引
// 跑法: cypher-shell -u neo4j -p <pw> -f schema/neo4j_setup.cypher
// 對應 Neo4j 5.x(內建向量索引)。

// ── 建模約定 ──────────────────────────────────────────────
// 每個節點掛兩個 label:共用的 :Entity(給約束/索引用)+ 一個 type label(:Company / :TechNode / :Material / ...)。
// 關係 type 直接用 relation 字彙(:SUPPLIES_TO / :IS_COMPONENT_OF / ...),屬性掛在關係上。
// id 全域唯一,跨文件靠它 MERGE。

// ── 1. 唯一性約束(同時建立 id 索引) ──────────────────────
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (n:Entity) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT edge_assertion_id_unique IF NOT EXISTS
FOR (ea:EdgeAssertion) REQUIRE ea.id IS UNIQUE;

CREATE CONSTRAINT source_doc_id_unique IF NOT EXISTS
FOR (sd:SourceDoc) REQUIRE sd.id IS UNIQUE;

// ── 1b. 預註冊最小權限 writer 會用到的 property-name tokens ────────────
// Neo4j Enterprise 的 SET PROPERTY 權限不等於 CREATE NEW PROPERTY NAME。
// 由 admin 跑 setup 時先建立 token，再刪掉 sentinel；不要把建立任意
// property name 的權限授給 cloud_routine。
MERGE (prewarm:SourceDoc {id: '__schema_token_prewarm__'})
SET prewarm.storage_permission = 'local_only',
    prewarm.permission_basis = 'schema token pre-registration'
WITH prewarm
DETACH DELETE prewarm;

// ── 1c. 預註冊最小權限 writer 會用到的 relationship-type tokens ────────
// routine_writer 可建立白名單內的關係，但不能建立全新的 relationship
// type token。此清單必須與 schema/vocab.json 的 relation 完全同步；sentinel
// 關係刪除後 token 仍會留在資料庫，無須擴張 routine_writer 權限。
MERGE (rel_source:SchemaTokenSentinel {id: '__relation_token_source__'})
MERGE (rel_target:SchemaTokenSentinel {id: '__relation_token_target__'})
MERGE (rel_source)-[:SUPPLIES_TO]->(rel_target)
MERGE (rel_source)-[:IS_COMPONENT_OF]->(rel_target)
MERGE (rel_source)-[:DEVELOPS]->(rel_target)
MERGE (rel_source)-[:DEPLOYS]->(rel_target)
MERGE (rel_source)-[:OFFERED_UNDER]->(rel_target)
MERGE (rel_source)-[:COMPETES_WITH]->(rel_target)
MERGE (rel_source)-[:ENABLES]->(rel_target)
MERGE (rel_source)-[:DEPENDS_ON]->(rel_target)
MERGE (rel_source)-[:INVESTS_IN]->(rel_target)
MERGE (rel_source)-[:LICENSES_TO]->(rel_target)
MERGE (rel_source)-[:ABOUT]->(rel_target)
MERGE (rel_source)-[:ACQUIRED]->(rel_target)
MERGE (rel_source)-[:PARTNERSHIP_WITH]->(rel_target)
MERGE (rel_source)-[:CONSTRAINED_BY]->(rel_target)
WITH rel_source, rel_target
DETACH DELETE rel_source, rel_target;

// ── 2. 查詢用索引 ─────────────────────────────────────────
CREATE INDEX entity_type IF NOT EXISTS
FOR (n:Entity) ON (n.type);

CREATE INDEX entity_level IF NOT EXISTS
FOR (n:Entity) ON (n.abstraction_level);

CREATE INDEX entity_role IF NOT EXISTS
FOR (n:Entity) ON (n.role);

// ── 3. 全文索引(name + aliases,給實體解析/查找用) ───────
CREATE FULLTEXT INDEX entity_name_fulltext IF NOT EXISTS
FOR (n:Entity) ON EACH [n.name, n.aliases];

// ── 4. 向量索引(RAG;維度依 embedding model 調整) ────────
// bge-m3 = 1024;OpenAI text-embedding-3-large = 3072。先設 1024,換模型再改。
CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
FOR (n:Entity) ON (n.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1024,
  `vector.similarity_function`: 'cosine'
}};

// ── 5. (可選)文件 chunk 節點的向量索引 ──────────────────
// RAG 的 chunk 向量也可放圖裡,與實體向量分開索引。
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1024,
  `vector.similarity_function`: 'cosine'
}};

// ── 6. 寫入 readiness sentinel ────────────────────────────
// 只在本檔所有 schema DDL 成功後寫入。MCP 寫工具還會另外檢查 canonical
// projection、legacy edge 與 CITES reconciliation，避免未完成 migration 就收新資料。
MERGE (state:GraphSchemaState {id: 'stockbotv2'})
SET state.version = '2026-07-16-u3b';

// 驗證:列出已建索引
SHOW INDEXES;
