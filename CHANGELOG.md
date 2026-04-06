# Changelog

## v0.1.4 - UTF-8 + LF hardening
- Enforce UTF-8 encoding without BOM via pre-commit gate (`reject-utf8-bom`).
- Enforce LF-only line endings via `.gitattributes` and renormalization.
- Add normalization drift gate to ensure canonical fixture stability.

## v0.1.2 - Install-clean CLI + deterministic normalization
- Installable console script (`mttt`).
- Deterministic JSON normalization pipeline.
- CI smoke tests + normalization diff assertion.

## Hook subsystem hardening (2026-04-05)

Introduced a versioned Git hook subsystem to prevent commits that omit critical files.

- Added `tools/hooks/pre-commit.ps1` as the authoritative hook source
- Added `scripts/install-hooks.ps1` for deterministic deployment into `.git/hooks/`
- Added `scripts/test-hooks.ps1` for cold-state smoke testing (installer + behavior)
- Hook enforces invariant: no untracked files under `src/`, `tests/`, or `schema/`
- Verified installer correctness via cold-state reinstall (no reliance on local hook residue)
- Cleaned `.gitattributes` (removed BOM) to eliminate parsing warnings

Result: repository now guards against partial commits that would break schema/authority layers.

## Scaffold flow completion

- Add end-to-end CLI test proving that a recoverable GOAL_WITHOUT_DECOMPOSITION -> scaffold application -> event replayed
- Enforce requirement for SET_STATE baseline before replay
- Align knowledge registry 