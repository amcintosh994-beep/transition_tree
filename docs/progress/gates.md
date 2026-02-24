# MTTT v1 Gates (Compiler-Grade Progress)

**Scope.** This file defines a *gate sequence* for MTTT v1. Each gate has a concrete pass condition and a command/test that proves it.

**Rule.** A gate is only considered **PASS** if the referenced command(s) pass in CI *and* locally on Windows (PowerShell).

---

## Gate 0 — Repo hygiene (anti-drift preflight)

**Goal:** remove structural hazards that cause silent divergence across editors, OS, or duplicate implementations.

**Pass conditions**

- [ ] No Python source files include a UTF-8 BOM.
- [ ] No duplicate entrypoints exist (single CLI entry; no “shadow scripts”).
- [ ] `backup/` fork files removed or relocated into a clearly non-imported archive.
- [ ] `__pycache__/` is not tracked; `.gitignore` covers it.
- [ ] Imports are consistent (package import path works from repo root).

**Proof commands**

- `python -m compileall -q src` (or package dir)
- `python -m pytest -q`
- `python -m transition_tree.cli doctor` (to be implemented)

**Status:** ☐ PASS / ☐ FAIL

---

## Gate 1 — Canonical state + schema authority

**Goal:** one canonical state model validated by a versioned schema.

**Pass conditions**

- [ ] Canonical storage model selected and documented (`docs/architecture/canonical_state.md`).
- [ ] Schemas exist under `schema/v1/` and validate datasets.
- [ ] Loader refuses unknown fields and rejects invalid graphs.

**Proof commands**

- `python -m transition_tree.cli validate ./data/demo` (or fixture directory)
- `python -m pytest -q tests/test_schema_validation.py`

**Status:** ☐ PASS / ☐ FAIL

---

## Gate 2 — Deterministic normalization (no-diff policy)

**Goal:** canonical data files and render outputs are stable under repeated runs.

**Pass conditions**

- [ ] `normalize --check` passes when no changes are needed.
- [ ] `normalize` followed by `normalize --check` yields no diff.
- [ ] Canonical ordering rules are documented.

**Proof commands**

- `python -m transition_tree.cli normalize ./data/demo --check`
- `python -m pytest -q tests/test_determinism.py`

**Status:** ☐ PASS / ☐ FAIL

---

## Gate 3 — Compiler gate correctness (invariants + lint + derived)

**Goal:** your pipeline boundary is explicit and exhaustive.

**Pass conditions**

- [ ] Gate is implemented as a single stable function (e.g., `pipeline.compute_ui_state`).
- [ ] Invariants are comprehensive and fail fast.
- [ ] CNL lint produces stable enumerated codes.
- [ ] Derived status is deterministic.

**Proof commands**

- `python -m pytest -q tests/test_invariants_and_lint.py`
- `python -m pytest -q tests/test_derived_status.py`

**Status:** ☐ PASS / ☐ FAIL

---

## Gate 4 — Resume loop (usable daily)

**Goal:** “what should I do next?” works end-to-end.

**Pass conditions**

- [ ] `resume` command prints the chosen node + blockers + rationale.
- [ ] Deterministic tie-breakers produce stable selection.

**Proof commands**

- `python -m transition_tree.cli resume ./data/demo`
- `python -m pytest -q tests/test_resume_ranking.py`

**Status:** ☐ PASS / ☐ FAIL

---

## Gate 5 — Render loop (stable human-readable audit output)

**Goal:** generate an inspectable artifact that is stable and reviewable.

**Pass conditions**

- [ ] `render` produces deterministic output for the same canon.
- [ ] Golden render snapshots match.

**Proof commands**

- `python -m transition_tree.cli render ./data/demo --out artifacts/render.md`
- `python -m pytest -q tests/test_render_golden.py`

**Status:** ☐ PASS / ☐ FAIL

---

## Gate 6 — Patch-based edits (UI-ready commit protocol)

**Goal:** all edits flow through an untrusted patch protocol with atomic writes.

**Pass conditions**

- [ ] Patch format is defined and documented.
- [ ] `apply-patch` writes canon atomically.
- [ ] Any invalid patch fails before write.

**Proof commands**

- `python -m transition_tree.cli apply-patch ./data/demo ./patches/example_patch.json --dry-run`
- `python -m pytest -q tests/test_apply_patch.py`

**Status:** ☐ PASS / ☐ FAIL

---

## Gate 7 — Audit manifest (version-locked provenance)

**Goal:** make builds and runs reproducible and attributable.

**Pass conditions**

- [ ] A deterministic build manifest is produced.
- [ ] Manifest includes python version, dependency freeze hash, schema hash(es), git commit.

**Proof commands**

- `python -m transition_tree.cli manifest --out artifacts/build_manifest.json`
- `python -m pytest -q tests/test_manifest.py`

**Status:** ☐ PASS / ☐ FAIL

---

## Gate 8 — Sprout proposals (optional for v1, required for v1.1)

**Goal:** model integration cannot mutate canon without passing the gate.

**Pass conditions**

- [ ] Proposals are parsed into patches.
- [ ] Candidate patch is gate-checked and shown as a diff.
- [ ] User acceptance is required to commit.

**Proof commands**

- `python -m transition_tree.cli sprout ./data/demo --dry-run`
- `python -m pytest -q tests/test_sprout_pipeline.py`

**Status:** ☐ PASS / ☐ FAIL

