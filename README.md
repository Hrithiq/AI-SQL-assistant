#  SQL AI Assistant

An AI-powered SQL assistant for healthcare data analysts. Combines semantic schema search, self-healing query correction, and BI tool integration to help analysts write, debug, and optimize SQL queries against Claims, Members, Provider, and Fraud data warehouses.

---

## Features

- **Schema-aware query generation** — Ask in plain English ("Where is the fraud data?") and get back the correct table references from Snowflake or SQL Server
- **Self-healing query loop** — Paste a failing query and its error; the system diagnoses, fixes, and re-executes automatically
- **Safety guardrails** — Blocks all `DROP`, `DELETE`, `TRUNCATE`, `UPDATE`, `INSERT`, `ALTER` and `EXEC` statements at the code level, not just the prompt level
- **Tableau / Power BI explainer** — Converts Tableau calculated fields to plain English and equivalent SQL
- **Audit logging** — Every AI-generated correction is logged to `dbo.AI_QueryCorrections` for HIPAA and SOC 2 compliance
- **Dual database support** — SQL Server (T-SQL) and Snowflake dialects

---

## Architecture

```
sql-ai/
├── src/
│   ├── phase_a/            # Knowledge retrieval: schema harvesting + vector store
│   │   ├── schema_collector.py
│   │   └── vector_store.py
│   ├── phase_b/            # Self-healing: error catching + LLM correction loop
│   │   ├── error_catcher.py
│   │   └── correction_loop.py
│   ├── phase_c/            # BI integration: Tableau/Power BI formula explainer
│   │   └── bi_explainer.py
│   └── shared/             # Shared services across all phases
│       ├── safety_guard.py
│       ├── audit_logger.py
│       └── query_executor.py
├── config/
│   └── settings.py         # Centralised config (env-backed)
├── sql/
│   ├── healthcare_patterns.sql   # Production-grade query templates
│   └── audit_table_setup.sql     # DDL for the audit log table
├── examples/
│   └── demo.py             # End-to-end walkthrough
└── tests/
    ├── test_safety.py
    └── test_correction.py
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| Anthropic API key | claude-opus-4-5 access |
| OpenAI API key | text-embedding-3-small |
| Pinecone account | Serverless index |
| SQL Server or Snowflake | Read-only credentials |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_ORG/sql-ai.git
cd sql-ai
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys and connection strings
```

### 3. Run the schema harvester (one-time setup)

```bash
python -m src.phase_a.schema_collector
```

This connects to your database, reads all table/column metadata, embeds it, and upserts into Pinecone. Re-run whenever your schema changes.

### 4. Try the demo

```bash
python examples/demo.py
```

---

## Usage

### Heal a broken query

```python
from src.phase_b.correction_loop import heal_query

result = heal_query(
    broken_sql="SELECT Member_ID, Paid_Amt FROM Claims WHERE ClaimYear = 2024",
    error_message="Invalid column name 'Member_ID'. Invalid column name 'Paid_Amt'.",
    analyst_question="paid claims per member for 2024"
)

print(result["diagnosis"])       # "Column 'Member_ID' should be 'MemberKey'..."
print(result["corrected_sql"])   # Corrected SELECT using real column names
print(result["optimizations"])   # ["Use range filter on ClaimDate instead of YEAR()..."]
```

### Ask a schema question

```python
from src.phase_a.vector_store import find_relevant_tables

tables = find_relevant_tables("Where is the fraud data?")
# Returns DDL snippets for FraudAlerts, SuspiciousPatterns, etc.
```

### Explain a Tableau formula

```python
from src.phase_c.bi_explainer import explain_tableau_calc

result = explain_tableau_calc(
    "ZN(SUM([Paid_Amount])) / NULLIF(ZN(COUNT([ClaimKey])), 0)"
)

print(result["plain_english"])    # "Average paid amount per claim, null-safe"
print(result["sql_equivalent"])   # "CASE WHEN COUNT(ClaimKey) = 0 THEN NULL ..."
```

### Run with auto-healing

```python
from src.phase_b.error_catcher import run_with_healing
import pyodbc

conn = pyodbc.connect(os.getenv("SQLSERVER_CONN_STR"))
rows, corrections_log = run_with_healing(my_sql, conn)
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key (claude-opus-4-5) |
| `OPENAI_API_KEY` | OpenAI key for embeddings |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | Pinecone index name (default: ` -schema`) |
| `SQLSERVER_CONN_STR` | SQL Server ODBC connection string |
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PASSWORD` | Snowflake password |
| `SNOWFLAKE_DATABASE` | Snowflake database name |
| `SNOWFLAKE_WAREHOUSE` | Snowflake virtual warehouse |
| `SNOWFLAKE_SCHEMA` | Snowflake schema (default: `PUBLIC`) |
| `DB_DIALECT` | `sqlserver` or `snowflake` |

---

## Safety

All AI-generated SQL is passed through `src/shared/safety_guard.py` before execution. This is a regex-based hard block — it does not rely on the LLM respecting its system prompt.

Blocked keywords: `DROP`, `DELETE`, `TRUNCATE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `EXEC`, `EXECUTE`, `MERGE`

Any query containing these keywords raises a `UnsafeSQLError` and is never executed.

---

## Audit Logging

Run `sql/audit_table_setup.sql` once against your SQL Server instance to create the `dbo.AI_QueryCorrections` table. Every correction made by the AI is then logged automatically with:

- Original broken query
- Error message
- AI diagnosis
- Corrected query
- Analyst username
- Timestamp

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Contributing

1. Branch from `main`: `git checkout -b feature/your-feature`
2. Follow the existing module structure — one concern per file
3. Never commit `.env` or credentials
4. Add a test for any new correction logic
5. Open a PR with a description of what changed and why

---

## License

Internal use only
