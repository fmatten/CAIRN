# Pull Request

## Summary

<!-- One sentence: what does this PR do? -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring (no functional change)
- [ ] Test improvement
- [ ] Adapter (new data source)
- [ ] Analysis module

## Changes

<!-- Describe the changes in detail -->

## FM-2 Invariants

If this PR touches `cairn/core/`:

- [ ] Allen algebra mutual exclusivity preserved
- [ ] TimeInterval positivity enforced (`start < end`)
- [ ] Type DAG edges run child → parent
- [ ] Z3 proofs updated / added where applicable

## Tests

- [ ] Unit tests added / updated
- [ ] Integration tests added / updated
- [ ] Property-based tests added / updated (Hypothesis)
- [ ] All 40 existing tests still pass

## Checklist

- [ ] Code follows project style (`ruff check`)
- [ ] Type annotations complete (`mypy cairn`)
- [ ] No real patient data included
- [ ] CHANGELOG.md updated
- [ ] NOTICE updated if new dependencies added

## EUPL-1.2 Confirmation

- [ ] I confirm this contribution is licensed under EUPL-1.2
- [ ] I confirm this contribution will be returned to the CAIRN reference system
