"""StockBot Web App（Phase 2 Step 5）——**LLM changes cognition; APP reads cognition.**

```
authority ──(materialize：唯一會跑模型的地方)──▶ artifact JSON ──(serve：純讀)──▶ HTTP ──▶ 瀏覽器
```

兩條責任鏈**刻意分開**：

- `python -m webapp materialize [TICKER ...]` 連 Neo4j／Engine C／private ledger，跑完整條鏈，
  atomic 寫下 artifact。約 4 秒／檔。
- `python -m webapp serve` 只讀那些 artifact。request path 沒有 LLM、沒有 authority write、
  沒有外部抓取、沒有任何模型執行——連 import 都沒有（`tests/test_webapp_request_path.py` 守著）。

外部認證邊界是 **Cloudflare Access**，不是本程式（`deploy/cloudflare/README.md`）。
本程式預設只綁 `127.0.0.1`，且沒有任何寫入端點。
"""
from .contracts import ARTIFACT_SCHEMA_VERSION, ArtifactUnavailable, freshness_of, validate_artifact
from .store import ArtifactStore

__all__ = ["ARTIFACT_SCHEMA_VERSION", "ArtifactStore", "ArtifactUnavailable", "freshness_of",
           "validate_artifact"]
