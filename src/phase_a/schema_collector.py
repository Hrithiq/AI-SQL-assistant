"""
Phase A — Schema Collector
Harvests table and column metadata from SQL Server or Snowflake,
then embeds and upserts into the Pinecone vector store.

Run once after setup, then re-run whenever your schema changes:
    python -m src.phase_a.schema_collector
"""

from __future__ import annotations
import pyodbc
import snowflake.connector
from config import settings
from src.phase_a.vector_store import embed_and_store


# ── SQL Server harvester ───────────────────────────────────────────────────────

def collect_sqlserver_metadata() -> list[dict]:
    """
    Reads all base tables from INFORMATION_SCHEMA, including any MS_Description
    extended properties set by your team (great for enriching embeddings).
    Returns a list of {"table": "schema.table", "ddl": "column definitions"}.
    """
    conn = pyodbc.connect(settings.SQLSERVER_CONN_STR)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t.TABLE_SCHEMA,
            t.TABLE_NAME,
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.IS_NULLABLE,
            ep.value AS column_description
        FROM INFORMATION_SCHEMA.TABLES   t
        JOIN INFORMATION_SCHEMA.COLUMNS  c
            ON c.TABLE_NAME   = t.TABLE_NAME
           AND c.TABLE_SCHEMA = t.TABLE_SCHEMA
        LEFT JOIN sys.extended_properties ep
            ON ep.major_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
           AND ep.minor_id  = COLUMNPROPERTY(
                                OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME),
                                c.COLUMN_NAME, 'ColumnId')
           AND ep.name = 'MS_Description'
        WHERE t.TABLE_TYPE = 'BASE TABLE'
        ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
    """)
    rows = cursor.fetchall()
    conn.close()
    return _group_by_table(rows)


# ── Snowflake harvester ────────────────────────────────────────────────────────

def collect_snowflake_metadata() -> list[dict]:
    """
    Reads table and column metadata from Snowflake INFORMATION_SCHEMA.
    Uses the configured database and schema from settings.
    """
    conn = snowflake.connector.connect(
        account=settings.SNOWFLAKE_ACCOUNT,
        user=settings.SNOWFLAKE_USER,
        password=settings.SNOWFLAKE_PASSWORD,
        database=settings.SNOWFLAKE_DATABASE,
        warehouse=settings.SNOWFLAKE_WAREHOUSE,
        schema=settings.SNOWFLAKE_SCHEMA,
    )
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            t.TABLE_SCHEMA,
            t.TABLE_NAME,
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.IS_NULLABLE,
            c.COMMENT AS column_description
        FROM INFORMATION_SCHEMA.TABLES   t
        JOIN INFORMATION_SCHEMA.COLUMNS  c
            ON c.TABLE_NAME   = t.TABLE_NAME
           AND c.TABLE_SCHEMA = t.TABLE_SCHEMA
        WHERE t.TABLE_TYPE = 'BASE TABLE'
          AND t.TABLE_SCHEMA = '{settings.SNOWFLAKE_SCHEMA}'
        ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
    """)
    rows = cursor.fetchall()
    conn.close()
    return _group_by_table(rows)


# ── Shared grouping logic ──────────────────────────────────────────────────────

def _group_by_table(rows: list) -> list[dict]:
    """
    Groups flat column rows into one text blob per table.
    Embedding at table granularity gives better semantic retrieval
    than embedding each column individually.
    """
    tables: dict[str, list[str]] = {}
    for schema, table, col, dtype, nullable, desc in rows:
        key = f"{schema}.{table}"
        nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
        col_line = f"  {col} {dtype} {nullable_str}"
        if desc:
            col_line += f"  -- {desc}"
        tables.setdefault(key, []).append(col_line)
    return [{"table": k, "ddl": "\n".join(v)} for k, v in tables.items()]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Collecting metadata from {settings.DB_DIALECT}...")
    if settings.DB_DIALECT == "snowflake":
        metadata = collect_snowflake_metadata()
    else:
        metadata = collect_sqlserver_metadata()

    print(f"Found {len(metadata)} tables. Embedding and uploading to Pinecone...")
    embed_and_store(metadata)
    print("Done. Schema index is ready.")
