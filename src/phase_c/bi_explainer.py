"""
Phase C — BI Tool Integration
Explains Tableau calculated fields and Power BI DAX measures in plain English,
and converts them to equivalent SQL expressions.
"""

from __future__ import annotations
import json
from anthropic import Anthropic
from config import settings

_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_TABLEAU_SYSTEM = """You are a Senior BI Architect at Optum. You have deep expertise in:
- Tableau calculated fields and LOD expressions
- Power BI DAX measures
- Converting BI formulas to equivalent SQL (T-SQL and Snowflake)

Respond ONLY with a valid JSON object — no markdown fences, no preamble:
{
  "plain_english": "What this formula does, in 1-2 plain sentences a non-technical stakeholder could understand",
  "formula_breakdown": [
    {"part": "exact sub-expression", "meaning": "what it does"}
  ],
  "sql_equivalent": "The equivalent SQL expression or subquery",
  "optimization_tip": "One concrete suggestion to make this more efficient or readable"
}"""

_DAX_SYSTEM = """You are a Senior BI Architect at Optum with deep expertise in Power BI DAX.

Respond ONLY with a valid JSON object — no markdown fences, no preamble:
{
  "plain_english": "What this DAX measure does, in 1-2 plain sentences",
  "formula_breakdown": [
    {"part": "exact sub-expression", "meaning": "what it does"}
  ],
  "sql_equivalent": "The equivalent SQL expression or subquery",
  "optimization_tip": "One concrete suggestion to make this more efficient"
}"""


def explain_tableau_calc(formula: str) -> dict:
    """
    Explains a Tableau calculated field and returns its SQL equivalent.

    Args:
        formula: Tableau calculated field expression, e.g.:
                 "ZN(SUM([Paid_Amount])) / NULLIF(ZN(COUNT([ClaimKey])), 0)"

    Returns:
        {
            "plain_english":      str,
            "formula_breakdown":  list[{"part": str, "meaning": str}],
            "sql_equivalent":     str,
            "optimization_tip":   str
        }

    Example:
        >>> result = explain_tableau_calc("ZN(SUM([Paid_Amount])) / NULLIF(ZN(COUNT([ClaimKey])), 0)")
        >>> print(result["plain_english"])
        "Calculates the average paid amount per claim, safely handling nulls and division by zero."
    """
    response = _client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=_TABLEAU_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Explain and convert this Tableau calculated field:\n\n{formula}"
        }],
    )
    return _parse(response.content[0].text)


def explain_dax_measure(measure: str) -> dict:
    """
    Explains a Power BI DAX measure and returns its SQL equivalent.

    Args:
        measure: DAX measure expression, e.g.:
                 "CALCULATE(SUM(Claims[Paid_Amount]), Claims[ClaimStatus] = \"PAID\")"

    Returns:
        Same structure as explain_tableau_calc().
    """
    response = _client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=_DAX_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Explain and convert this Power BI DAX measure:\n\n{measure}"
        }],
    )
    return _parse(response.content[0].text)


def _parse(raw: str) -> dict:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM did not return valid JSON. Raw response:\n{raw}"
        ) from exc
