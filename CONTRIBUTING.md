# Contributing to CAIRN

Thank you for your interest in contributing to CAIRN.

## Licence and Copyleft

CAIRN is licensed under **EUPL-1.2**. By contributing, you agree that:

- Your contributions are licensed under the same EUPL-1.2 licence
- **Modifications must be returned** to the reference system (copyleft clause)
- You have the right to contribute the code you submit

This ensures CAIRN remains a true open reference architecture — not a fork base for proprietary derivates.

## How to Contribute

### Bug Reports and Feature Requests
Open an issue at: https://codeberg.org/fm2-project/cairn/issues

Please include:
- CAIRN version (`cairn version`)
- Python version
- Minimal reproducible example
- Expected vs. actual behaviour

### Pull Requests

1. Fork the repository on Codeberg
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Write tests for your change (unit + integration)
4. Run the test suite: `pytest`
5. Run the linter: `ruff check cairn tests`
6. Run type checks: `mypy cairn`
7. Submit a pull request with a clear description

### Code Standards

- Python 3.11+, strict typing
- All public functions must have docstrings
- Tests required for all new modules
- Property-based tests (Hypothesis) for FM-2 mathematical invariants
- No patient data in tests — use synthetic examples only

### FM-2 Mathematical Correctness

Changes to `cairn/core/` must:
- Preserve the Allen algebra mutual exclusivity invariant
- Maintain strictly positive interval durations (`start < end`)
- Preserve DAG edge direction (child → parent)
- Be accompanied by Z3 proofs where applicable

### NOT a Medical Device

CAIRN must never be modified to:
- Process real patient data in production
- Provide clinical decision support
- Claim CE marking or MDR compliance

Any PR that would move CAIRN toward medical device territory will be rejected.

## Development Setup

```bash
git clone https://codeberg.org/fm2-project/cairn.git
cd cairn
pip install -e ".[dev]"
pytest
```

## Questions

Open a discussion at: https://codeberg.org/fm2-project/cairn/issues
