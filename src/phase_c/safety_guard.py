"""
Shared — Safety Guard
Hard regex block for destructive SQL keywords.
This runs on EVERY query before execution, regardless of source.
Does not rely on the LLM respecting its system prompt.
"""

from __future__ import annotations
import re


class UnsafeSQLError(Exception):
    """Raised when a query contains a destructive SQL keyword."""


# All keywords that must never appear in analyst or AI-generated queries.
_DANGEROUS_PATTERN = re.compile(
    r"""
    \b(
        DROP     | DELETE   | TRUNCATE |
        UPDATE   | INSERT   | ALTER    |
        CREATE   | EXEC     | EXECUTE  |
        MERGE    | GRANT    | REVOKE   |
        DENY     | SHUTDOWN | RESTORE  |
        BACKUP   | BULK
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def is_safe(sql: str) -> bool:
    """Returns True if the query contains no destructive keywords."""
    return not bool(_DANGEROUS_PATTERN.search(sql))


def assert_safe(sql: str) -> None:
    """
    Raises UnsafeSQLError if the query is not safe.
    Use this as a gate before any query execution.

    Args:
        sql: The SQL string to check.

    Raises:
        UnsafeSQLError: With the offending keyword identified.

    Example:
        >>> assert_safe("SELECT * FROM Claims")          # passes silently
        >>> assert_safe("DELETE FROM Claims WHERE 1=1")  # raises UnsafeSQLError
    """
    match = _DANGEROUS_PATTERN.search(sql)
    if match:
        raise UnsafeSQLError(
            f"Blocked: query contains forbidden keyword '{match.group().upper()}'. "
            "Only SELECT statements are permitted."
        )
