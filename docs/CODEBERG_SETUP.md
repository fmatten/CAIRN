# CAIRN — Codeberg Repository Setup Guide

## Repository Settings

After creating the repository at https://codeberg.org/iscad/cairn,
configure the following settings in the Codeberg web interface:

### Basic Settings

| Field | Value |
|---|---|
| Repository name | `cairn` |
| Description | `Clinical interoperability reference architecture. Built on FM-2.` |
| Website | `https://codeberg.org/iscad/cairn` |
| Visibility | Public |
| Default branch | `main` |

### Topics (Tags)

Add these topics in Settings → Repository → Topics:

```
fhir  hl7  interoperability  formal-verification  allen-algebra
clinical-informatics  information-loss  python  openehr  sild  fm2
```

### Branch Protection (Settings → Branches)

Protect `main`:
- [x] Require pull request before merging
- [x] Require status checks to pass (Woodpecker CI)
- [x] Dismiss stale pull request approvals
- [ ] Allow force push: NO

### Woodpecker CI Activation

1. Go to https://ci.codeberg.org
2. Log in with your Codeberg account
3. Search for `iscad/cairn`
4. Click "Enable"
5. The `.woodpecker.yml` pipeline will run automatically on push

### Labels

Create these labels in Issues → Labels:

| Label | Colour | Description |
|---|---|---|
| `bug` | #d73a4a | Something isn't working |
| `enhancement` | #a2eeef | New feature or request |
| `fm2-core` | #e4e669 | Touches FM-2 mathematical core |
| `adapter` | #0075ca | New or improved data adapter |
| `documentation` | #0075ca | Documentation improvements |
| `eupl-compliance` | #cfd3d7 | Licence / copyleft related |
| `not-a-medical-device` | #b60205 | Scope boundary enforcement |

## Initial Push

```bash
# Clone and initialise
git clone https://codeberg.org/iscad/cairn.git
cd cairn

# Copy CAIRN source files into the cloned repo
# (copy contents of this package here)

# Initial commit
git add .
git commit -m "feat: CAIRN v1.0.0 initial release

Clinical interoperability reference architecture built on FM-2.

- FM-2 core: type DAG, Allen algebra (13 relations), 6-tuple event model
- Formal verification: Z3 SMT proofs, SILD information loss detector
- Adapters: FHIR R4, HL7 v2 (ORU/ADT/RXA), CSV/DataFrame
- Analysis: cohort queries φA–φD, terminology drift, variance analyzer
- API: FastAPI REST, Click CLI
- Tests: 40 passing (unit + integration + Hypothesis property tests)

Licence: EUPL-1.2
NOT a medical device (EU MDR 2017/745 / MPDG)"

git push origin main

# Tag the release
git tag -a v1.0.0 -m "CAIRN v1.0.0"
git push origin v1.0.0
```

## Codeberg Release

After push, create a release at:
https://codeberg.org/iscad/cairn/releases/new

| Field | Value |
|---|---|
| Tag | `v1.0.0` |
| Title | `CAIRN v1.0.0 — Initial Release` |
| Description | (copy from CHANGELOG.md) |

## PyPI Publication (v1.1.0+)

```bash
pip install build twine
python -m build
twine upload dist/*
```

Package will be available at: https://pypi.org/project/cairn/
