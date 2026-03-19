"""
Tests for the safety guard — the most critical module in the project.
Every destructive keyword must be caught. Every valid SELECT must pass.
"""

import pytest
from src.shared.safety_guard import assert_safe, is_safe, UnsafeSQLError


# ── Queries that must be BLOCKED ──────────────────────────────────────────────

UNSAFE_CASES = [
    ("DELETE FROM Claims WHERE 1=1",           "DELETE"),
    ("DROP TABLE Members",                     "DROP"),
    ("TRUNCATE TABLE ClaimLines",              "TRUNCATE"),
    ("UPDATE Claims SET Paid_Amount = 0",      "UPDATE"),
    ("INSERT INTO Fraud VALUES (1, 'x')",      "INSERT"),
    ("ALTER TABLE Claims ADD col INT",         "ALTER"),
    ("CREATE TABLE Hack (id INT)",             "CREATE"),
    ("EXEC sp_executesql N'SELECT 1'",        "EXEC"),
    ("EXECUTE xp_cmdshell 'dir'",             "EXECUTE"),
    ("MERGE Claims USING src ON ...",          "MERGE"),
    # Case-insensitive check
    ("delete from claims",                     "delete"),
    ("DeLeTe FrOm ClAiMs",                    "DELETE mixed case"),
    # Inline in a comment — should still catch it
    ("SELECT * FROM Claims -- DROP TABLE x",   "DROP in comment"),
]

@pytest.mark.parametrize("sql,label", UNSAFE_CASES)
def test_blocked(sql, label):
    assert not is_safe(sql), f"Expected '{label}' to be blocked"
    with pytest.raises(UnsafeSQLError):
        assert_safe(sql)


# ── Queries that must PASS ─────────────────────────────────────────────────────

SAFE_CASES = [
    "SELECT * FROM Claims WHERE ClaimStatus = 'PAID'",
    "SELECT COUNT(*) FROM Members",
    "SELECT c.ClaimKey, m.MemberKey FROM Claims c JOIN Members m ON c.MemberKey = m.MemberKey",
    "SELECT TOP 10 ProviderNPI, SUM(Paid_Amount) FROM Claims GROUP BY ProviderNPI ORDER BY 2 DESC",
    "WITH cte AS (SELECT * FROM Claims) SELECT * FROM cte",
    # The word "created" should not trigger CREATE
    "SELECT created_at FROM Members WHERE created_at > '2024-01-01'",
    # The word "deleted_flag" should not trigger DELETE
    "SELECT deleted_flag FROM Claims",
    # "execution" should not trigger EXECUTE/EXEC
    "SELECT execution_time FROM QueryLog",
]

@pytest.mark.parametrize("sql", SAFE_CASES)
def test_allowed(sql):
    assert is_safe(sql), f"Expected safe but was blocked: {sql[:60]}"
    assert_safe(sql)  # Should not raise
