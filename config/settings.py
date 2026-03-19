import os
from dotenv import load_dotenv

load_dotenv()

# ── AI APIs ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]
ANTHROPIC_MODEL: str = "claude-opus-4-5"
EMBEDDING_MODEL: str = "text-embedding-3-small"

# ── Pinecone ──────────────────────────────────────────────────────────────────
PINECONE_API_KEY: str = os.environ["PINECONE_API_KEY"]
PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "optum-schema")
VECTOR_TOP_K: int = 5

# ── SQL Server ────────────────────────────────────────────────────────────────
SQLSERVER_CONN_STR: str = os.getenv("SQLSERVER_CONN_STR", "")

# ── Snowflake ─────────────────────────────────────────────────────────────────
SNOWFLAKE_ACCOUNT: str = os.getenv("SNOWFLAKE_ACCOUNT", "")
SNOWFLAKE_USER: str = os.getenv("SNOWFLAKE_USER", "")
SNOWFLAKE_PASSWORD: str = os.getenv("SNOWFLAKE_PASSWORD", "")
SNOWFLAKE_DATABASE: str = os.getenv("SNOWFLAKE_DATABASE", "")
SNOWFLAKE_WAREHOUSE: str = os.getenv("SNOWFLAKE_WAREHOUSE", "")
SNOWFLAKE_SCHEMA: str = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")

# ── App config ────────────────────────────────────────────────────────────────
DB_DIALECT: str = os.getenv("DB_DIALECT", "sqlserver")  # "sqlserver" | "snowflake"
MAX_HEAL_RETRIES: int = 2
