# MTTT v1 Capability Matrix (Tracking)

**Scope.** This file tracks the concrete capabilities required for a credible **v1** of the Magic Transition ToDo Tree (MTTT) system.

**Principle.** Progress is counted only when a capability meets its **Definition of Done (DoD)** and is backed by **executable evidence** (tests and/or deterministic commands).

**Canonical assumption for v1 (to be decided early):** 
- **Canonical state = JSON directory** (`nodes.json`, `edges.json`, `meta.json`) validated by a versioned JSON Schema.
- SQLite (`tree.db`) is treated as **legacy** and either migrated or removed from the v1 build path.

If you decide otherwise, update this header and adjust the matrix.

---

## How to use this matrix

- **Owner:** you (or a future collaborator) assigns a capability an owner.
- **Status:** `NOT STARTED | IN PROGRESS | BLOCKED | DONE`
- **Evidence:** must be a command, test name, and/or artifact path that proves DoD.
- **Drift resistance:** each DoD includes determinism or auditability requirements.

---

## Capability matrix

| ID | Capability | Why it matters | DoD (Definition of Done) | Evidence (tests / commands / artifacts) | Status |
|---:|---|---|---|---|---|
| C00 | **v1 canonical state decision** (JSON vs SQLite) | Eliminates split-brain and drifting invariants | `docs/architecture/canonical_state.md` merged; one canonical path is the only supported execution path; other path quarantined or migrated | Document + CI proof that only canonical path is exercised | NOT STARTED |
| C01 | **Versioned JSON Schemas** for node/edge/dataset | Makes structure authoritative and diff-reviewable | `schema/v1/` contains `node.schema.json`, `edge.schema.json`, `dataset.schema.json`; loader validates against them | `python -m transition_tree.cli validate <dataset>`; unit tests for schema validation | NOT STARTED |
| C02 | **Schema governance** (hash lock + bump-only rule) | Prevents silent schema drift | A lock file with schema hashes exists (e.g., `schema/schema_hashes_v1.json`); tooling enforces “never edit v1 in place” | CI check fails on schema drift; documented bump procedure | NOT STARTED |
| C03 | **Deterministic canon normalization** | Enables no-diff policy and reproducible builds | `normalize` command rewrites canon into canonical ordering/format; rerunning yields byte-identical output | `mttt normalize --check` returns success; determinism test | NOT STARTED |
| C04 | **Single compiler gate** (`load → invariants → lint → derived → resume → render`) | Creates one correctness boundary | A single function/module acts as the gate; all entrypoints call it; no side-path bypasses it | `tests/test_pipeline_gate.py` (or equivalent) | IN PROGRESS |
| C05 | **Patch-based commit protocol** (untrusted edits) | Required for UI, sprout, and safe automation | Implement `apply_patch` + atomic write; direct mutation forbidden | `mttt apply-patch` + tests demonstrating fast-fail on invalid patch | NOT STARTED |
| C06 | **CNL lint as first-class** (templates + errors) | Enforces “soft input / hard state” | Lint errors are stable, enumerated, and tested; templates match `Language and types spec v0.2` | `tests/test_cnl_lint.py` + documented error codes | IN PROGRESS |
| C07 | **Invariant suite** (type purity, edge validity, ID uniqueness, etc.) | Prevents structural corruption | `invariants.py` fully covers structural rules; all invariants have test coverage | `tests/test_invariants.py` | IN PROGRESS |
| C08 | **Derived status computation** is deterministic | Powers UI state, filtering, and resume ranking | Derived state is computed from canon; no hidden state; stable ordering | `tests/test_derived_status.py` + golden fixture | IN PROGRESS |
| C09 | **Resume ranking** is deterministic + explainable | Core “what next?” product loop | Resume output includes reasons and blockers; deterministic tie-breakers | `tests/test_resume_ranking.py` + golden fixture | IN PROGRESS |
| C10 | **Stable render** (tractatus numbering or equivalent) | Human-readable audit trail | `render` output stable across runs and machines | `tests/test_render_golden.py` comparing to `golden/expected_render.md` | NOT STARTED |
| C11 | **Golden scenarios** (2–4 fixtures) | Prevents “it works on my tree” illusions | Add `tests/golden/` scenarios with expected resume/render/derived outputs | CI runs golden tests; `mttt demo` prints outputs | NOT STARTED |
| C12 | **Determinism tests** (save/load idempotence) | Guarantees drift resistance | Repeated `load→normalize→save` yields byte-identical canon | `tests/test_determinism.py` | NOT STARTED |
| C13 | **Repo hygiene gate** (encoding, duplicates, imports) | Reduces Windows/editor hazards | No UTF-8 BOM in Python sources; no duplicate entrypoints; no `backup/` forks; `__pycache__` excluded | CI preflight check; `git status` clean after normalize/check | NOT STARTED |
| C14 | **CLI v1** implementing the UI contract loops (no GUI required for v1) | Makes system usable daily without UI | Commands: `validate`, `normalize`, `resume`, `render`, `apply-patch`, `doctor` | `python -m transition_tree.cli --help` + tests for commands | NOT STARTED |
| C15 | **Audit manifest** (build provenance) | “Computationally version-locked” traceability | `artifacts/build_manifest.json` contains python version, dependency hash, schema hashes, git commit | `mttt manifest` command; deterministic format | NOT STARTED |
| C16 | **Sprout pipeline** (optional for v1; required for v1.1) | Safe LLM integration | Proposals are parsed into patches; gate-run; diff shown; user accepts | `mttt sprout --dry-run` + tests for rejection on invalid proposals | NOT STARTED |

---

## Notes and immediate fixes

- **Test correctness:** ensure tests assert the intended error codes (e.g., a missing `TASK` estimate should assert `TASK_MISSING_ESTIMATE`, not a GOAL-related code).
- **Encoding:** remove UTF-8 BOM from Python sources and enforce `UTF-8 (no BOM)` + `LF` via tooling.
- **Duplicate scripts:** consolidate duplicate `run_from_json_dir.py` and remove/relocate legacy `ttree*.py`.

