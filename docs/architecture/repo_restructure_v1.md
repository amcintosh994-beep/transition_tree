# Proposed Repo Restructure for MTTT v1

This document proposes a concrete repository layout for a drift-resistant, compiler-gated MTTT v1.

## Objectives

- **Single canonical engine** and **single entrypoint**.
- **Schema-authoritative** canonical data model.
- Deterministic normalization + no-diff policy.
- Clear separation: `src/` (importable package) vs `scripts/` (tools) vs `docs/` (spec) vs `schema/`.

---

## Proposed layout

```
transition_tree/
  pyproject.toml
  README.md
  src/
    transition_tree/
      __init__.py
      cli.py                 # v1 CLI entrypoint (validate/normalize/resume/render/apply-patch/manifest/doctor)
      model.py               # (from mttt_model.py) core dataclasses/types
      schema.py              # schema loading + version selection
      load.py                # canonical loader (from loader_json.py) with strict validation
      normalize.py           # canonical normalization rules
      invariants.py          # (from invariants.py) structural invariants
      cnl_lint.py            # (from cnl_lint.py) CNL linting
      derived.py             # (from derived_status.py) derived UI state
      resume.py              # (from resume_ranking.py) resume selection
      render.py              # deterministic rendering
      patch.py               # patch format + apply_patch + atomic commit
      audit.py               # manifest + provenance
  schema/
    v1/
      node.schema.json
      edge.schema.json
      dataset.schema.json
    schema_hashes_v1.json    # hash lock
  data/
    demo/
      nodes.json
      edges.json
      meta.json
  artifacts/
    .gitkeep
  docs/
    architecture/
      canonical_state.md
      repo_restructure_v1.md
    progress/
      gates.md
      v1_capability_matrix.md
  tests/
    unit/
      test_invariants.py
      test_cnl_lint.py
      test_derived.py
      test_resume.py
    golden/
      scenario_01/
        nodes.json
        edges.json
        meta.json
        expected_render.md
        expected_resume.json
        expected_derived.json
      test_golden_scenarios.py
    test_determinism.py
  tools/
    doctor_checks.py         # optional: repo hygiene checks
    migrate_sqlite.py        # optional: legacy migration utility
```

Notes:

- `src/transition_tree/` is the only importable package.
- `scripts/` is replaced by `tools/` for non-package utilities.
- Canonical datasets live under `data/` (or user-specified paths), never inside Python modules.

---

## What should be deprecated (and why)

### Legacy SQLite + LLM CLI (deprecated for v1)

These files represent a different architecture (SQLite canonical state + model proposal schema). Keep them only as an archival reference or migrate them into `tools/legacy/`.

- `scripts/ttree.py`
- `scripts/ttree_guardrails.py`
- `scripts/get_ids.py` (if it only supports SQLite IDs)
- `tree.db`, `tree.db.bak`
- `tree_render.txt`, current `render.md` if generated from legacy pipeline

**v1 policy:** these must not be imported or executed by CI.

### Duplicate / shadow entrypoints

- `run_from_json_dir.py` at repo root **and** `scripts/run_from_json_dir.py`.

**Action:** keep one implementation only, and move it into `src/transition_tree/cli.py` (or wrap it).

### Backup forks

- `backup/invariants.py`, `backup/loader_json.py`, `backup/pipeline.py`

**Action:** remove from import path. Either delete or move into `docs/archive/`.

### Tracked build artifacts

- `__pycache__/` (tracked in zip) should never be versioned.

**Action:** remove from repo; ensure `.gitignore` covers `__pycache__/` and `*.pyc`.

---

## Migration plan (minimal-risk)

### Step 1 — Establish the package boundary

- Create `src/transition_tree/` and move:
  - `mttt_model.py` → `src/transition_tree/model.py`
  - `invariants.py` → `src/transition_tree/invariants.py`
  - `cnl_lint.py` → `src/transition_tree/cnl_lint.py`
  - `derived_status.py` → `src/transition_tree/derived.py`
  - `resume_ranking.py` → `src/transition_tree/resume.py`
  - `pipeline.py` → split into `cli.py` + `gate.py` (or keep `pipeline.py` inside package)
  - `loader_json.py` → `src/transition_tree/load.py`

Keep module names stable or provide thin re-export shims during the transition.

### Step 2 — Implement the v1 CLI

- `python -m transition_tree.cli ...` becomes the only supported entrypoint.
- Implement at least:
  - `validate`
  - `normalize` (+ `--check`)
  - `resume`
  - `render`
  - `apply-patch` (+ `--dry-run`)
  - `manifest`
  - `doctor`

### Step 3 — Introduce schemas and lock them

- Add `schema/v1/*.json`.
- Validate canonical data on load.
- Add schema hash lock file and CI check.

### Step 4 — Golden fixtures + determinism tests

- Add `tests/golden/` scenario(s).
- Add `test_determinism.py` enforcing idempotence.

### Step 5 — Quarantine legacy code

- Move legacy `scripts/ttree*.py` and `tree.db*` into `tools/legacy/` or `docs/archive/`.
- Remove them from CI paths.

---

## Immediate repo hygiene checklist

- Convert Python sources to `UTF-8 (no BOM)`.
- Enforce LF line endings.
- Remove tracked `__pycache__/`.
- Remove duplicate `run_from_json_dir.py`.
- Remove `backup/` forks from import path.

