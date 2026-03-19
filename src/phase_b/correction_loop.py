"""
Phase B — Correction Loop
Core LLM-powered query fixer. Takes a broken query and its error message,
retrieves relevant schema context, and returns a diagnosis + corrected SQL.
"""

from __future__ import annotations
import json
from anthropic import Anthropic
from src.phase_a.vector_store import find_relevant_tables
from src.shared.safety_guard import assert_safe
from config import settings

_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_SYSTEM_PROMPT = """You are a Senior Data Architect at Optum with expert knowledge of:
- SQL Server (T-SQL) and Snowflake SQL syntax
- Healthcare data schemas:
    Claims        (dbo.Claims, dbo.ClaimLines)
    Members       (dbo.Members, dbo.MemberEligibility)
    Providers     (dbo.Providers, dbo.ProviderSpecialties)
    Fraud         (dbo.FraudAlerts, dbo.SuspiciousPatterns)

Hard rules you MUST follow:
1. NEVER generate DROP, DELETE, TRUNCATE, UPDATE, INSERT, ALTER, CREATE, EXEC, EXECUTE, or MERGE.
2. Only produce SELECT statements.
3. Always include at least one concrete performance optimization.
4. Use exact column and table names from the schema context provided — do not invent names.
5. For SQL Server: prefer range filters over function-wrapped column filters (sargable predicates).
6. For Snowflake: use QUALIFY instead of nested subqueries for window-function filtering.

Respond ONLY with a valid JSON object in this exact format — no markdown fences, no preamble:
{
  "diagnosis": "Plain English explanation of why the query failed (1-3 sentences)",
  "corrected_sql": "The full corrected SELECT query as a string",
  "optimizations": ["Optimization 1", "Optimization 2"]
}"""


def heal_query(
    broken_sql: str,
    error_message: str,
    analyst_question: str = "",
) -> dict:
    """
    Diagnoses a failing SQL query and returns a corrected version.

    Args:
        broken_sql:        The SQL that produced the error.
        error_message:     The database error message (e.g. from pyodbc or snowflake).
        analyst_question:  Optional plain-English description of what the analyst wanted.
                           Improves schema retrieval accuracy when provided.

    Returns:
        {
            "diagnosis":      str,
            "corrected_sql":  str,
            "optimizations":  list[str],
            "safe":           bool   (always True — UnsafeSQLError raised otherwise)
        }

    Raises:
        UnsafeSQLError:  If the LLM produces a non-SELECT statement.
        ValueError:      If the LLM response is not valid JSON.
    """
    search_text = analyst_question if analyst_question else broken_sql
    relevant_schemas = find_relevant_tables(search_text)
    schema_context = "\n\n".join(relevant_schemas)

    user_prompt = f"""The following SQL query failed:

```sql
{broken_sql}
```

Error message from the database:
{error_message}

Relevant schema context (use these exact column and table names):
{schema_context}

Diagnose the error and provide the corrected query."""

    response = _client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM did not return valid JSON. Raw response:\n{raw}"
        ) from exc

    # Hard safety check — raises UnsafeSQLError if any write keyword is present
    assert_safe(result["corrected_sql"])
    result["safe"] = True

    return result
