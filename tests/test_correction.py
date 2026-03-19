"""
Tests for the correction loop and BI explainer.
These tests mock the Anthropic API and Pinecone to avoid live calls.
"""

from unittest.mock import patch, MagicMock
import json
import pytest
from src.phase_b.correction_loop import heal_query
from src.phase_c.bi_explainer import explain_tableau_calc
from src.shared.safety_guard import UnsafeSQLError


# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_CORRECTION = {
    "diagnosis": "Column 'Member_ID' should be 'MemberKey', 'Paid_Amt' should be 'Paid_Amount'.",
    "corrected_sql": "SELECT MemberKey, Paid_Amount FROM dbo.Claims WHERE ClaimStatus = 'PAID'",
    "optimizations": ["Add index on ClaimStatus", "Use date range instead of YEAR() function"],
}

VALID_TABLEAU_RESULT = {
    "plain_english": "Average paid amount per claim, null-safe.",
    "formula_breakdown": [
        {"part": "ZN(SUM([Paid_Amount]))", "meaning": "Sum of paid amounts, nulls as 0"},
    ],
    "sql_equivalent": "CASE WHEN COUNT(ClaimKey) = 0 THEN NULL ELSE SUM(Paid_Amount) / COUNT(ClaimKey) END",
    "optimization_tip": "Use a single CASE expression instead of nested ZN/NULLIF calls.",
}


def _mock_anthropic_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=json.dumps(payload))]
    return response


# ── heal_query tests ──────────────────────────────────────────────────────────

@patch("src.phase_b.correction_loop.find_relevant_tables", return_value=["MemberKey INT NOT NULL"])
@patch("src.phase_b.correction_loop._client")
def test_heal_query_returns_valid_structure(mock_client, mock_tables):
    mock_client.messages.create.return_value = _mock_anthropic_response(VALID_CORRECTION)

    result = heal_query(
        broken_sql="SELECT Member_ID FROM Claims",
        error_message="Invalid column name 'Member_ID'",
    )

    assert "diagnosis" in result
    assert "corrected_sql" in result
    assert "optimizations" in result
    assert result["safe"] is True
    assert isinstance(result["optimizations"], list)


@patch("src.phase_b.correction_loop.find_relevant_tables", return_value=["MemberKey INT NOT NULL"])
@patch("src.phase_b.correction_loop._client")
def test_heal_query_blocks_unsafe_llm_output(mock_client, mock_tables):
    """If the LLM somehow returns a DELETE, it must be blocked."""
    bad_payload = {**VALID_CORRECTION, "corrected_sql": "DELETE FROM Claims WHERE 1=1"}
    mock_client.messages.create.return_value = _mock_anthropic_response(bad_payload)

    with pytest.raises(UnsafeSQLError):
        heal_query(
            broken_sql="SELECT Member_ID FROM Claims",
            error_message="Invalid column name 'Member_ID'",
        )


@patch("src.phase_b.correction_loop.find_relevant_tables", return_value=[])
@patch("src.phase_b.correction_loop._client")
def test_heal_query_raises_on_invalid_json(mock_client, mock_tables):
    """LLM returning non-JSON should raise ValueError, not crash silently."""
    response = MagicMock()
    response.content = [MagicMock(text="Here is the fix: SELECT * FROM Claims")]
    mock_client.messages.create.return_value = response

    with pytest.raises(ValueError, match="valid JSON"):
        heal_query(
            broken_sql="SELECT bad_col FROM Claims",
            error_message="Invalid column name 'bad_col'",
        )


# ── explain_tableau_calc tests ────────────────────────────────────────────────

@patch("src.phase_c.bi_explainer._client")
def test_tableau_explainer_returns_valid_structure(mock_client):
    mock_client.messages.create.return_value = _mock_anthropic_response(VALID_TABLEAU_RESULT)

    result = explain_tableau_calc("ZN(SUM([Paid_Amount])) / NULLIF(ZN(COUNT([ClaimKey])), 0)")

    assert "plain_english" in result
    assert "formula_breakdown" in result
    assert "sql_equivalent" in result
    assert "optimization_tip" in result
    assert isinstance(result["formula_breakdown"], list)


@patch("src.phase_c.bi_explainer._client")
def test_tableau_explainer_raises_on_invalid_json(mock_client):
    response = MagicMock()
    response.content = [MagicMock(text="This formula calculates the average.")]
    mock_client.messages.create.return_value = response

    with pytest.raises(ValueError, match="valid JSON"):
        explain_tableau_calc("ZN(SUM([Paid_Amount]))")
