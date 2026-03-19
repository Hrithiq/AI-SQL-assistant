# Contributing

## Branch naming
- `feature/short-description` for new features
- `fix/short-description` for bug fixes
- `docs/short-description` for documentation only

## Adding a new query pattern
1. Add the SQL to `sql/healthcare_patterns.sql` with a comment block explaining the optimization rationale.
2. If the pattern involves a new table, re-run `python -m src.phase_a.schema_collector` to refresh the vector index.

## Adding a new BI formula type
Add a new function to `src/phase_c/bi_explainer.py` following the same structure as `explain_tableau_calc()`. Add a corresponding mock test in `tests/test_correction.py`.

## Environment for local development
```bash
cp .env.example .env
# Fill in your API keys and connection strings
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

## PR checklist
- [ ] Tests pass (`pytest tests/ -v`)
- [ ] No `.env` or credentials committed
- [ ] New correction logic has at least one test
- [ ] SQL patterns include inline optimization notes
