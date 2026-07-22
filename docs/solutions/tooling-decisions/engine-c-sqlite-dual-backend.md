---
title: "Engine C Dual-Backend DB Abstraction: SQLite for Local Dev, Postgres for Production"
date: 2026-07-08
last_updated: 2026-07-22
category: docs/solutions/tooling-decisions/
module: engine-c-financial-db
problem_type: tooling_decision
component: database
severity: medium
applies_when:
  - Engine C financial data engine needs a zero-install local dev backend
  - Docker/Postgres is not available on the developer machine
  - Single-user local development of a financial data pipeline
  - Non-US stocks (e.g. Nasdaq Stockholm) require a manual IR doc download path instead of EDGAR
tags:
  - sqlite
  - postgres
  - dual-backend
  - engine-c
  - financial-data
  - non-us-stocks
  - yfinance
  - edgar
  - local-dev
---

# Dual-Backend DB Abstraction for Zero-Install Local Development

## Context

Engine C (financial data engine) was designed for Postgres. When implementation began, the development environment had no Docker installed. Installing Docker just to run a local Postgres instance adds significant friction to a single-user, local-only tool — and it blocks development entirely while the environment is being set up.

Rather than halt progress or require infrastructure changes as a prerequisite, a dual-backend abstraction layer was introduced. SQLite becomes the default zero-install path; Postgres is activated by environment variable for production-grade deployments. The same application code works on both without branching at the call site. SQLite 後來再移入 ignored private runtime，避免把個人財務 observation 與 manual ledger 當成可由 Git 回復的 source code。

This pattern also emerged from a second discovery: non-US stocks (e.g., Sivers Semiconductors, traded on Nasdaq Stockholm) have a separate onboarding path that EDGAR cannot service. That path — manual PDF extraction via pdfplumber, yfinance with exchange suffixes — was established alongside the DB abstraction work.

---

## Guidance

### The dual-backend abstraction in `engine_c/db.py`

The entire backend-selection logic lives in one module. Every other file imports from `engine_c.db` and never calls `psycopg2` or `sqlite3` directly.

**Backend detection — environment variables as the switch:**

```python
_PG_ENVS = ("POSTGRES_DSN", "POSTGRES_HOST")

def _use_postgres() -> bool:
    return any(os.environ.get(k) for k in _PG_ENVS)

DB_TYPE = "postgres" if _use_postgres() else "sqlite"
```

No config file, no flag. If `POSTGRES_DSN` or `POSTGRES_HOST` is set in the environment, the module uses Postgres; otherwise SQLite. `DB_TYPE` is exported as a module-level string so other modules can check it once if they need backend-specific branching.

**Connection factory — returns native connections, not an ORM:**

```python
def sqlite_path(*, repo_root: Path | None = None,
                private_root: Path | None = None) -> Path:
    """Resolve the active ignored Engine C authority."""
    repo = (repo_root or _ROOT).resolve()
    private = initialize_private_root(
        (private_root or repo / "library" / "private").resolve(),
        repo_root=repo,
    )
    pointer = private / "runtime_pointer.json"
    if pointer.is_file():
        # Parse a relative target, validate containment and run SQLite quick_check.
        ...
        if not destination.is_file():
            raise RuntimeError("Engine C runtime pointer target is missing")
        return destination

    legacy = repo / "engine_c" / "stockbot.db"
    if legacy.is_file():
        return legacy.resolve()
    if list((private / "engine_c").glob("stockbot-engine-c-private-v*.db")):
        raise RuntimeError("Engine C versioned runtime exists without an authority pointer")
    return validate_private_destination(
        private / "engine_c" / "stockbot.db",
        private_root=private,
        repo_root=repo,
    )

def get_conn():
    """Return a native SQLite or psycopg2 connection."""
    if _use_postgres():
        # Build a psycopg2 connection with a bounded connect timeout.
        ...

    path = sqlite_path()
    legacy = (_ROOT / "engine_c" / "stockbot.db").resolve()
    if path.resolve() == legacy:
        return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn = connect_sqlite(path, create=not path.exists())
    _ensure_sqlite_schema(conn)
    return conn
```

以上是 contract-level 摘要；完整驗證與連線細節以 `engine_c/db.py` 為準。Fresh clone 尚無 authority 時可在 `library/private/engine_c/` bootstrap SQLite schema；但已有 runtime pointer、versioned runtime 或 legacy authority 時會驗證並 fail closed，不會把遺失／損毀的 authority 靜默替換成空 DB。Postgres 變更仍使用 `engine_c/migrations/` 的 versioned migrations，並由 `python -m engine_c.migrate` 顯式套用與驗證 required schema。

`manual_observations` 是 append-only private input authority，`manual_fields` 才是可重建 projection。兩者目前同庫，因此「ETL projection 可重建」不代表整個 Engine C DB 可以無備份刪除；任何整庫 relocation／restore 前都必須把 manual ledger 納入 recovery backup。

```sql
CREATE TABLE IF NOT EXISTS financial_snapshots (
    ticker TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    price REAL,
    pe_trailing REAL,
    pe_forward REAL,
    ev_revenue REAL,
    gross_margin REAL,
    shares_outstanding REAL,
    analyst_target_mean REAL,
    analyst_target_count INTEGER,
    fetched_at TEXT,
    UNIQUE(ticker, snapshot_date)
);

CREATE TABLE IF NOT EXISTS manual_fields (
    ticker TEXT NOT NULL,
    field_name TEXT NOT NULL,
    value TEXT,
    updated_at TEXT,
    UNIQUE(ticker, field_name)
);
```

**Upsert — the one place where SQL dialects diverge:**

SQLite and Postgres have different upsert syntax. This is isolated to a single function:

```python
def upsert_snapshot(conn, snap: dict) -> None:
    if _use_postgres():
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO financial_snapshots (ticker, snapshot_date, price, ...)
            VALUES (%s, %s, %s, ...)
            ON CONFLICT (ticker, snapshot_date) DO UPDATE SET
                price = EXCLUDED.price, ...
        """, (snap["ticker"], snap["snapshot_date"], snap.get("price"), ...))
        conn.commit()
    else:
        conn.execute("""
            INSERT OR REPLACE INTO financial_snapshots (ticker, snapshot_date, price, ...)
            VALUES (?, ?, ?, ...)
        """, (snap["ticker"], snap["snapshot_date"], snap.get("price"), ...))
        conn.commit()
```

Key difference: SQLite uses `?` for parameter placeholders and `INSERT OR REPLACE`; Postgres uses `%s` and `ON CONFLICT ... DO UPDATE`. These are the two things that cannot be unified without an ORM. Keep them in one function each.

**Checklist queries — branching via `DB_TYPE`:**

`checklist.py` queries the DB to pull financial fields for the five-item watchlist gate. It checks `DB_TYPE` once at query time:

```python
from engine_c.db import get_conn, DB_TYPE

conn = get_conn()
placeholder = "%s" if DB_TYPE == "postgres" else "?"
cur = conn.execute(
    f"SELECT * FROM financial_snapshots WHERE ticker = {placeholder}",
    (ticker,)
)
```

### Non-US stock onboarding path

EDGAR is US-only. For stocks listed outside the US, the onboarding path is:

1. **yfinance ticker suffix**: Use the exchange-specific suffix, not the bare ticker. Nasdaq Stockholm requires `.ST`:
   - Wrong: `SIVE`
   - Correct: `SIVE.ST`

2. **TICKER_MAP in `loader/load_to_neo4j.py`**: Map the graph node ID to the yfinance ticker:
   ```python
   TICKER_MAP = {
       "co:coherent": "COHR",
       "co:sivers_semiconductors": "SIVE.ST",
       "co:some_private_company": None,   # None = private, not unmapped
   }
   ```
   `None` is explicit: it means "this company is private and has no public ticker." Do not leave private companies out of the map; an absent key is ambiguous (not yet mapped vs. intentionally no ticker).

3. **Annual reports via pdfplumber**: IR sites often have PDF annual reports. For an 86-page report, extract only the relevant pages:
   ```python
   import pdfplumber

   PAGES_OF_INTEREST = list(range(3, 7)) + list(range(9, 13)) + list(range(13, 18))

   with pdfplumber.open("sivers_annual_report_2024.pdf") as pdf:
       text = "\n\n".join(
           pdf.pages[i].extract_text() or ""
           for i in PAGES_OF_INTEREST
           if i < len(pdf.pages)
       )
   # ~47,673 chars / ~11,918 tokens for the relevant sections
   ```
   Pass the extracted text into the standard extract pipeline (`prompts/extract_system.md`).

### EDGAR token guard

Large SEC filings (10-K, 10-Q) can exceed 500,000 characters. Add a default truncation guard to `fetchers/edgar.py` to prevent accidental LLM token overflows:

```python
_DEFAULT_MAX_CHARS = 50_000

def fetch_ticker(ticker, forms, n, max_chars=_DEFAULT_MAX_CHARS):
    # ... fetch and clean text ...
    if max_chars and len(text) > max_chars:
        import sys
        print(
            f"WARNING: truncating {len(text)} -> {max_chars} chars",
            file=sys.stderr
        )
        meta["truncated"] = True
        meta["original_chars"] = len(text)
        text = text[:max_chars]
    return text, meta
```

CLI exposes `--max-chars` (pass `0` to disable truncation). The `meta` dict carries `truncated: true` and `original_chars` so downstream code can log or flag the truncation.

---

## Why This Matters

**Zero-install is a real constraint for single-user local tools.** Requiring Docker as a prerequisite for a personal research system raises the barrier to entry on any new machine and blocks development entirely while the environment is being set up. SQLite ships with Python and needs no server process — it is genuinely the right default for a tool that runs on one machine with one user.

**Without the abstraction layer, every future Postgres migration touches every file.** If `checklist.py`, `etl_yfinance.py`, and any future Engine C script all import `psycopg2` directly, switching to Postgres (or back to SQLite for a new machine) requires hunting down every DB call. The abstraction confines the divergence to `engine_c/db.py` and the two parameter-placeholder checks in `checklist.py`.

**EDGAR silently returns nothing for non-US stocks.** There is no error — the CIK lookup just finds no results. If you do not know this, you can spend time debugging the fetcher or the pipeline before realizing the stock is not registered with the SEC. Lesson: verify that the registry the fetcher depends on covers your target universe before onboarding a new stock.

**Unguarded EDGAR fetches can silently overflow LLM context.** A 10-K can be 300,000–800,000 characters. Without a truncation guard, the text passes through to the extract prompt and either gets silently truncated by the LLM API, hits a token limit error, or produces degraded extraction quality from the middle/end of the document. The `--max-chars` guard makes truncation explicit and logged.

---

## When to Apply

Apply the dual-backend pattern when:

- The tool is primarily single-user and local-first, but you want a clear upgrade path to a production database without rewriting.
- You want to develop without running a database server (no Docker, no Postgres install, no network).
- The SQL used is simple enough that the only meaningful dialect differences are parameter placeholders (`?` vs `%s`) and upsert syntax. If you need window functions, CTEs, or Postgres-specific types (JSONB, arrays), the abstraction becomes much more complex — evaluate whether SQLite is actually sufficient at that point.
- You are in early-stage development and schema changes are frequent；fresh private SQLite 可由 tracked schema bootstrap，但已有 authority 必須經 explicit migration／cutover／backup contract，不可把 `CREATE TABLE IF NOT EXISTS` 當成遺失資料的 recovery。

Apply the non-US onboarding path when:

- The stock is listed outside the US (not NYSE, NASDAQ, or OTC).
- EDGAR returns no results for a ticker you expected to find.
- The IR site provides PDF documents rather than structured filings.

Apply the EDGAR token guard when:

- Fetching 10-K, 10-Q, or proxy filings that may run to hundreds of pages.
- The extract prompt receives the full document text (not pre-chunked).
- You need the truncation to be auditable (visible in logs and stored in metadata).

---

## Examples

**Starting the ETL with SQLite (default, no config needed):**

```bash
python engine_c/etl_yfinance.py COHR SIVE.ST
```

Fresh clone 尚未有 Engine C authority 時，SQLite 會建立在 ignored `library/private/engine_c/`；cutover 後由 `library/private/runtime_pointer.json` 指向 active DB。舊 `engine_c/stockbot.db` 只保留 read-only compatibility fallback，不再是新 runtime 的寫入位置。No environment variables required.

**Switching to Postgres:**

```bash
export POSTGRES_DSN="postgresql://stockbot:secret@localhost:5432/stockbot"
python engine_c/etl_yfinance.py COHR SIVE.ST
```

The same script, zero code changes. Bootstrap a new Postgres database with `engine_c/schema.sql`; for an existing database, run `python -m engine_c.migrate` before the ETL. Connections default to a bounded five-second timeout, configurable with `POSTGRES_CONNECT_TIMEOUT`.

**Checking which backend is active:**

```python
from engine_c.db import DB_TYPE, get_conn

conn = get_conn()
print(f"Using backend: {DB_TYPE}")  # "sqlite" or "postgres"
```

**Fetching financial data for a Stockholm-listed stock:**

```python
import yfinance as yf

# Must use .ST suffix for Nasdaq Stockholm
ticker = yf.Ticker("SIVE.ST")
info = ticker.info
print(info.get("marketCap"), info.get("trailingPE"))
```

**Extracting pages from a large PDF annual report:**

```python
import pdfplumber

PAGES_OF_INTEREST = list(range(3, 7)) + list(range(9, 13)) + list(range(13, 18))

with pdfplumber.open("sivers_annual_report_2024.pdf") as pdf:
    text = "\n\n".join(
        pdf.pages[i].extract_text() or ""
        for i in PAGES_OF_INTEREST
        if i < len(pdf.pages)
    )
# Pass `text` to the standard extract pipeline
```

**EDGAR fetch with explicit token guard:**

```bash
# Default: truncate at 50,000 chars
python fetchers/edgar.py --ticker COHR --forms 10-K --n 1

# No truncation (careful with LLM context windows)
python fetchers/edgar.py --ticker COHR --forms 10-K --n 1 --max-chars 0
```

---

## Related

- `engine_c/db.py` — the dual-backend abstraction (canonical source of truth for this pattern)
- `engine_c/etl_yfinance.py` — ETL that writes snapshots via `upsert_snapshot()`
- `engine_c/checklist.py` — financial checklist queries; uses `DB_TYPE` for placeholder branching
- `fetchers/edgar.py` — EDGAR fetcher with `--max-chars` guard
- `loader/load_to_neo4j.py` — contains `TICKER_MAP`; `None` values mark private companies explicitly
- `docs/onboarding-sop.md` — step-by-step onboarding SOP that uses this non-US path
- `docs/solutions/architecture-patterns/knowledge-graph-data-quality-and-engine-c-join-key.md` — graph-side TICKER_MAP: how Neo4j Company nodes get ticker attributes as the A→C join key
- `docs/solutions/architecture-patterns/engine-d-content-addressed-decision-context.md` — Engine D 只凍結本次使用的 Engine C values，不取代 current observation authority
- `AGENTS.md`「上游三引擎匯流至 Engine D 的前置條件」— Engine C / Engine A join key design: `TICKER_MAP` is the A→C bridge
