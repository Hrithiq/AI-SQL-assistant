"""
Phase B — Error Catcher
Wraps query execution with an automatic heal-and-retry loop.
Logs every correction to the audit table via shared/audit_logger.py.
"""

from __future__ import annotations
import getpass
from src.phase_b.correction_loop import heal_query
from src.shared.audit_logger import log_correction
from src.shared.safety_guard import assert_safe
from config import settings


def run_with_healing(
    sql: str,
    db_conn,
    analyst_question: str = "",
    analyst_user: str | None = None,
    max_retries: int | None = None,
) -> tuple[list, list[dict]]:
    """
    Executes SQL against the provided database connection.
    On failure, calls the LLM correction loop and retries automatically.

    Args:
        sql:              The SQL query to run.
        db_conn:          An open pyodbc or snowflake connection.
        analyst_question: Plain-English intent (improves schema retrieval).
        analyst_user:     Username for the audit log (defaults to OS user).
        max_retries:      Override the default from settings (default: 2).

    Returns:
        (rows, corrections_log)
        - rows:             List of result rows from cursor.fetchall()
        - corrections_log:  List of correction dicts from each heal attempt

    Raises:
        Exception:  The original database error if all retries are exhausted.
    """
    retries = max_retries if max_retries is not None else settings.MAX_HEAL_RETRIES
    user = analyst_user or getpass.getuser()
    current_sql = sql
    corrections: list[dict] = []

    assert_safe(current_sql)  # Safety check before even trying

    for attempt in range(retries + 1):
        try:
            cursor = db_conn.cursor()
            cursor.execute(current_sql)
            rows = cursor.fetchall()
            return rows, corrections

        except Exception as db_error:
            if attempt == retries:
                raise  # All retries exhausted — bubble up the original error

            print(f"[heal] Attempt {attempt + 1} failed: {db_error}")
            print("[heal] Asking LLM to correct the query...")

            fix = heal_query(
                broken_sql=current_sql,
                error_message=str(db_error),
                analyst_question=analyst_question,
            )

            log_correction(
                original_sql=current_sql,
                error_message=str(db_error),
                diagnosis=fix["diagnosis"],
                corrected_sql=fix["corrected_sql"],
                analyst_user=user,
            )

            corrections.append(fix)
            current_sql = fix["corrected_sql"]
            print(f"[heal] Diagnosis: {fix['diagnosis']}")
            print(f"[heal] Retrying with corrected query...")
