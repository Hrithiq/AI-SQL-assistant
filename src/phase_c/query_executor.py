"""
Shared — Query Executor
Thin connection factory for SQL Server and Snowflake.
Always opens read-only connections. Use run_with_healing() from
phase_b/error_catcher.py to execute with auto-correction.
"""

from __future__ import annotations
import pyodbc
import snowflake.connector
from config import settings


def get_sqlserver_connection() -> pyodbc.Connection:
    """
    Returns an open SQL Server connection using the configured ODBC string.
    The connection string should point to a read-only login — enforce this
    at the database level, not just in code.
    """
    if not settings.SQLSERVER_CONN_STR:
        raise EnvironmentError(
            "SQLSERVER_CONN_STR is not set. Check your .env file."
        )
    return pyodbc.connect(settings.SQLSERVER_CONN_STR)


def get_snowflake_connection() -> snowflake.connector.SnowflakeConnection:
    """
    Returns an open Snowflake connection using configured credentials.
    Connect with a role that has SELECT-only privileges on analytics schemas.
    """
    required = [
        settings.SNOWFLAKE_ACCOUNT,
        settings.SNOWFLAKE_USER,
        settings.SNOWFLAKE_PASSWORD,
        settings.SNOWFLAKE_DATABASE,
        settings.SNOWFLAKE_WAREHOUSE,
    ]
    if not all(required):
        raise EnvironmentError(
            "One or more Snowflake settings are missing. Check your .env file."
        )
    return snowflake.connector.connect(
        account=settings.SNOWFLAKE_ACCOUNT,
        user=settings.SNOWFLAKE_USER,
        password=settings.SNOWFLAKE_PASSWORD,
        database=settings.SNOWFLAKE_DATABASE,
        warehouse=settings.SNOWFLAKE_WAREHOUSE,
        schema=settings.SNOWFLAKE_SCHEMA,
    )


def get_connection():
    """
    Returns the appropriate connection based on DB_DIALECT setting.
    Use this in scripts that need to be dialect-agnostic.
    """
    if settings.DB_DIALECT == "snowflake":
        return get_snowflake_connection()
    return get_sqlserver_connection()
