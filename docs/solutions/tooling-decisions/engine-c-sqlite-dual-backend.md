---
title: "Engine C Dual-Backend DB Abstraction: SQLite for Local Dev, Postgres for Production"
date: 2026-07-08
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

Rather than halt progress or require infrastructure changes as a prerequisite, a dual-backend abstraction layer was introduced. SQLite becomes the default zero-install path; Postgres is activated by environment variable for production-grade deployments. The same application code works on both without branching at the call site.

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
_SQLITE_PATH = _ROOT / "engine_c" / "stockbot.db"

def get_conn():
    """Returns sqlite3.Connection or psycopg2 connection.
    Auto-creates SQLite schema on first connect."""
    if _use_postgres():
        import psycopg2
        dsn = os.environ.get("POSTGRES_DSN") or (
            f"host={os.environ['POSTGRES_HOST']} "
            f"dbname={os.environ.get('POSTGRES_DB', 'stockbot')} "
            f"user={os.environ.get('POSTGRES_USER', 'stockbot')} "
            f"password={os.environ.get('POSTGRES_PASSWORD', '')}"
        )
        return psycopg2.connect(dsn)
    else:
        import sqlite3
        conn = sqlite3.connect(_SQLITE_PATH)
        _ensure_schema(conn)
        return conn
```

SQLite schema is created inline on the first `get_conn()` call — no migration runner, no setup script needed:

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
- You are in early-stage development and schema changes are frequent; SQLite's `_ensure_schema()` approach (`CREATE TABLE IF NOT EXISTS` inline) is faster to iterate than maintaining migration files.

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

`engine_c/stockbot.db` is created automatically on first run. No environment variables required.

**Switching to Postgres:**

```bash
export POSTGRES_DSN="postgresql://stockbot:secret@localhost:5432/stockbot"
python engine_c/etl_yfinance.py COHR SIVE.ST
```

The same script, zero code changes. The schema must exist in Postgres already (run the DDL manually or via a migration).

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
- `CLAUDE.md §L9` — Engine C / Engine A join key design: `TICKER_MAP` is the A→C bridge
