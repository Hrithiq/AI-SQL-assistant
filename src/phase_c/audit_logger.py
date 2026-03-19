"""
Shared — Audit Logger
Writes every AI-generated SQL correction to dbo.AI_QueryCorrections.
Required for HIPAA audit trails and SOC 2 compliance.
Run sql/audit_table_setup.sql once before using this module.
"""

from __future__ import annotations
import datetime
import pyodbc
from config import settings


def log_correction(
    original_sql: str,
    error_message: str,
    diagnosis: str,
    corrected_sql: str,
    analyst_user: str,
) -> None:
    """
    Inserts one correction record into dbo.AI_QueryCorrections.
    Fails silently with a warning if the audit table is unreachable —
    the analyst's query still runs; audit loss is preferable to service loss.

    Args:
        original_sql:   The broken query before AI correction.
        error_message:  The database error that triggered the correction.
        diagnosis:      The LLM's plain-English diagnosis.
        corrected_sql:  The fixed query produced by the LLM.
        analyst_user:   OS or app username of the analyst.
    """
    if not settings.SQLSERVER_CONN_STR:
        print("[audit] No SQL Server connection string configured. Skipping audit log.")
        return

    try:
        conn = pyodbc.connect(settings.SQLSERVER_CONN_STR)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.AI_QueryCorrections
                (OriginalSQL, ErrorMessage, Diagnosis, CorrectedSQL, AnalystUser, CorrectedAt)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            original_sql,
            error_message[:2000],    # Truncate to column max
            diagnosis[:1000],
            corrected_sql,
            analyst_user,
            datetime.datetime.utcnow(),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[audit] Warning: failed to write audit log — {exc}")
