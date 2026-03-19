"""
End-to-end demo of the SQL AI Assistant.
Runs all three phases without a live database connection
so you can verify your API keys and vector store work correctly.
"""

from src.phase_a.vector_store import find_relevant_tables
from src.phase_b.correction_loop import heal_query
from src.phase_c.bi_explainer import explain_tableau_calc, explain_dax_measure
from src.shared.safety_guard import assert_safe, UnsafeSQLError
import json


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


# ── Phase A: Schema lookup ─────────────────────────────────────────────────────

section("Phase A — Schema Lookup")
print("Question: 'Where is the fraud data?'\n")

results = find_relevant_tables("Where is the fraud data?")
print(f"Found {len(results)} relevant tables:")
for i, ddl in enumerate(results, 1):
    preview = ddl[:120].replace("\n", " | ")
    print(f"  {i}. {preview}...")


# ── Phase B: Query correction ──────────────────────────────────────────────────

section("Phase B — Query Correction")

broken_sql = """
SELECT Member_ID, Paid_Amt, ClaimYear
FROM Claims
WHERE ClaimYear = 2024
  AND Status = 'paid'
"""

error_msg = (
    "Invalid column name 'Member_ID'. "
    "Invalid column name 'Paid_Amt'. "
    "Invalid column name 'ClaimYear'. "
    "Invalid column name 'Status'."
)

print("Broken SQL:")
print(broken_sql.strip())
print(f"\nError: {error_msg}\n")

fix = heal_query(
    broken_sql=broken_sql,
    error_message=error_msg,
    analyst_question="paid claims by member for 2024",
)

print(f"Diagnosis:\n  {fix['diagnosis']}\n")
print("Corrected SQL:")
print(fix["corrected_sql"])
print("\nOptimizations:")
for opt in fix["optimizations"]:
    print(f"  - {opt}")


# ── Phase C: Tableau explainer ─────────────────────────────────────────────────

section("Phase C — Tableau Formula Explainer")

formula = "ZN(SUM([Paid_Amount])) / NULLIF(ZN(COUNT([ClaimKey])), 0)"
print(f"Formula: {formula}\n")

result = explain_tableau_calc(formula)
print(f"Plain English:\n  {result['plain_english']}\n")
print("Breakdown:")
for part in result["formula_breakdown"]:
    print(f"  {part['part']}")
    print(f"    → {part['meaning']}")
print(f"\nSQL equivalent:\n  {result['sql_equivalent']}")
print(f"\nOptimization tip:\n  {result['optimization_tip']}")


# ── Safety guard demo ──────────────────────────────────────────────────────────

section("Safety Guard")

safe_queries = [
    "SELECT * FROM Claims WHERE ClaimStatus = 'PAID'",
    "SELECT COUNT(*) FROM Members",
]
unsafe_queries = [
    "DELETE FROM Claims WHERE 1=1",
    "DROP TABLE Members",
    "EXEC sp_executesql N'SELECT 1'",
]

for q in safe_queries:
    try:
        assert_safe(q)
        print(f"  PASS  {q[:60]}")
    except UnsafeSQLError as e:
        print(f"  FAIL  {e}")

for q in unsafe_queries:
    try:
        assert_safe(q)
        print(f"  MISSED  {q[:60]}")
    except UnsafeSQLError:
        print(f"  BLOCKED  {q[:60]}")

print("\nDemo complete.")
