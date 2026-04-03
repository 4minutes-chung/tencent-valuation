# Version History (Git Lineage)

Last updated: 2026-04-03

This repository has one active development line: `main`.
Current package identity is V4 (`tencent-valuation-v4`) with source under `src/tencent_valuation_v4/`.

## 1) Timeline Summary

| Era | Commit | Date | Headline |
|---|---|---|---|
| V1 baseline | `f2cf350` | 2026-02-17 | Initial Tencent valuation framework |
| V2 expansion | `9fa837f` | 2026-02-19 | Added data snapshots and valuation artifacts |
| V3 package era | `0e0cc09` | 2026-03-19 | Expanded valuation stack and QA contracts |
| V4 merge milestone | `4d64af3` | 2026-03-24 | V4 branch merged into `main` |
| V4-only cleanup | `426f8fc` | 2026-03-29 | Removed legacy duplicate trees, kept single active layout |
| V4 namespace hard-cut (current baseline) | `284ac6b` | 2026-04-03 | Switched canonical module path to `src/tencent_valuation_v4/` |

## 2) Current Main Characteristics

- Branch: `main`
- Active package name: `tencent-valuation-v4`
- Active module path: `src/tencent_valuation_v4/`
- CLI entrypoint: `tencent_valuation_v4.cli:main`
- Build metadata file: `pyproject.toml`

## 3) Architecture Clarification

- `pyproject.toml` is not optional clutter; it defines build backend, dependencies, and CLI script mapping.
- `src/` is the standard Python source root for package discovery (`setuptools` with `package-dir = {"": "src"}`).
- The repository is operationally V4; references to older versions are historical records only.

## 4) Historical Inspection Commands

Inspect historical README content:

```bash
git show f2cf350:README.md
git show 9fa837f:README.md
git show 0e0cc09:README.md
git show 426f8fc:README.md
git show 284ac6b:README.md
```

Inspect files changed by a specific milestone:

```bash
git diff-tree --no-commit-id --name-status -r <commit>
```

List top-level tree at a historical commit:

```bash
git ls-tree --name-only <commit>
```

## 5) Working Rule

Treat `main` + V4 CLI as the only production path.
Historical commits are for audit/reproducibility, not for day-to-day model runs.
