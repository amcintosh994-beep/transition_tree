# Magic Transition ToDo Tree (MTTT)
A deterministic, schema-governed task graph system with invariant enforcement, controlled natural language linting, and reproducible CLI gates.

MTTT models tasks as typed nodes and edges, computes derived state, enforces structural invariants, and produces stable, normalized JSON outputs suitable for version control and CI enforcement.

## Design principles
* **Determinism first** - stable sorting, canonical JSON, no nondeterministic outputs
* **Schema authority** - internal types define the graph contract
* **Invariant enforcement** - structural failures are hard errors
* **CLI as gate** - <mttt check> and <mttt normalize> are CI-validating commands
* **Install-clean packaging** - no reliance on <PYTHONPATH> or root shims

## Installation (editable development mode)

	python -m pip install -e .

Verify:

	mttt -
	mttt check --data-dir fixtures/valid_minimal

## CLI commands
<mttt check>

Validate invariants and lint rules.

	mttt check --data-dir <directory>

Performs:

* Graph invariant checks
* CNL lint validation
* Deterministic ordering checks

Returns nonzero exit code on structural failure (CI-safe)

<mttt normalize>

Normalize JSON files into canonical, stable form.

	mttt normalize --data-dir <directory>

Guarantees:

* Stable key ordering
* Stable list ordering
* LF-only line endings
* UTF-8 (no BOM)

Safe to run in CI to prevent drift.

## Project Layout
	src/
		mttt/
			cli.py
			model.py
			loader_json.py
			normalize_json.py
			invariants.py
			derived_status.py
			resume_ranking.py
			cnl_lint.py

* Internal imports are **package-relative only**
* Root-level shims (if present) exist only for compatibility

## Development workflow
### Run local gate

	python -m pip install -e .
	python -m unittest -q
	mttt check --data-dir fixtures/valid_minimal
	mttt normalize --data-dir fixtures/valid_minimal

After cloning, run:
.\scripts\install-hooks.ps1