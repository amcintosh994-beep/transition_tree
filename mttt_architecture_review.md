# MTTT — Architectural Review and Event-Sourced Redesign Proposal

**Date:** 2026-03-04  
**Scope:** Full systems-level review of `src/mttt/` package; migration to append-only event-sourced architecture.  
**Codebase state:** post-refactor to `src/mttt` layout; Gates 0–3 partially complete; legacy SQLite branch (`scripts/ttree.py`, `tree.db`) coexists in repository but is not imported by the package.

---

## 1. Current Architecture Diagnosis

### 1.1 State storage model

The current system is **file-authoritative, mutable-snapshot**. Canonical state lives in two JSON files per dataset directory:

```
<data_dir>/nodes.json    # list of node objects
<data_dir>/edges.json    # list of edge objects
```

These files are the only persistent artifact. There is no write-ahead log, no history, no event record. A call to `normalize_dir()` reads these files, sorts and re-serializes them, and overwrites them in place. After any mutation the prior state is gone.

The `tree.db` / `tree.db.bak` SQLite files in the repo root represent an entirely separate, older architecture (`scripts/ttree.py`) that used SQLite as the canonical store. That branch is architecturally disconnected from `src/mttt/` — the package never imports from `scripts/`. However, the presence of `tree.db` in the working tree creates ambiguity about what is authoritative. This is the most significant hygiene hazard in the current repo.

### 1.2 Normalization

Normalization is performed by `normalize_json.py:normalize_dir()`, which:

1. calls `loader_json.load_nodes_edges_from_dir()` to parse JSON → typed `Node`/`Edge` dataclasses,
2. sorts nodes by `id` and edges by `(src, type.value, dst)`,
3. re-serializes with `sort_keys=True`, `indent=2`, LF-only, UTF-8 no-BOM, trailing newline.

This is idempotent and byte-stable (verified by `test_determinism.py`). The normalization contract is well-specified and the implementation matches. The only gap is that `normalize_dir` is a read-modify-write on the same files — there is no atomic write (no temp-file rename). On a crash mid-write, the files could be partially overwritten. This is a correctness risk even before the event-sourcing pivot.

### 1.3 Invariant enforcement

`invariants.py:check_invariants()` receives `(nodes, edges)` — pure in-memory objects — and returns an `InvariantReport`. It is stateless: no file I/O, no side effects. The invariants cover:

- duplicate node IDs
- referential integrity of edges
- kind/edge compatibility (lattice enforcement)
- orphan BLOCKER and ASSET nodes
- GOAL decomposition requirement
- recurrence facet correctness
- `requires_task` cycle detection (DFS, deterministic by sorted adjacency)
- QUESTION discharge on completion
- TASK estimate presence and magnitude
- TASK verb blacklist

The cycle detection (`_has_cycle_requires_task`) uses a standard iterative DFS. The implementation is correct but uses Python recursion rather than an explicit stack — a `RecursionError` is possible on pathologically deep graphs. This is low risk at current scale but worth noting.

`fast_fail=True` (default in `pipeline.py`) means the first error causes early return. `cmd_check` in `cli.py` passes `fast_fail=False` to accumulate all errors. These two modes are not consistently documented, which is a minor API hazard.

### 1.4 Pipeline

`pipeline.py:compute_ui_state()` is a pure function over `(nodes, edges)`. It sequences: invariant check → CNL lint → derived state → resume ranking. All four stages are stateless and take typed dataclasses. This is the cleanest module in the package — it is effectively a pure projection function and maps directly onto what the replay engine needs to become.

### 1.5 CLI

`cli.py` implements two commands: `normalize` (read-normalize-overwrite) and `check` (load-invariants-exit-code). The CLI loads state by calling `load_nodes_edges_from_dir` directly; there is no intermediate abstraction between the CLI and the file loader. This means the CLI is tightly coupled to the file-authoritative storage model. Introducing an event log requires routing CLI state acquisition through a replay layer rather than a direct file load — a clean seam that already needs to exist.

### 1.6 Determinism guarantees (current)

The following are currently guaranteed:

- Byte-stable normalization (verified by SHA-256 idempotence test).
- Deterministic invariant output (sorted node/edge traversal order in all loops).
- Deterministic CNL lint output (sorted by `node_id` then code).
- Deterministic derived state (sorted adjacency construction throughout).
- Deterministic resume ranking (explicit composite sort key with `node.id` as tiebreaker).

The snapshot test (`test_semantic_snapshot.py`) computes `compute_ui_state` output and diffs against a stored `.snapshot.json`. This is a solid regression guard for the projection.

### 1.7 Architectural coupling and technical debt

**Coupling 1: CLI ↔ file loader.** `cmd_check` and `cmd_normalize` both call `load_nodes_edges_from_dir` directly. There is no "get current state" abstraction. Adding event sourcing requires inserting a `replay → snapshot → load` path between the CLI and the graph objects.

**Coupling 2: normalize overwrites source.** `normalize_dir` mutates its input directory. In an event-sourced system, normalization of the persisted log should never occur; normalization applies only to the projection. The current `normalize` CLI command will need to be re-scoped or removed.

**Coupling 3: no write path at all.** The current package has no mutation interface: no `add_node`, no `update_edge`, no `delete_node`. Mutations are assumed to happen externally (by editing `nodes.json` / `edges.json` directly). The event log introduces the first formal write path, which means the CLI will need new commands before any of the existing ones can be deprecated.

**Debt 1: legacy SQLite branch.** `scripts/ttree.py` is a 600+ line standalone script with a completely different node model (domain-based tree, `prerequisite`/`capability`/`resource` type vocabulary, OpenAI integration). It uses `tree.db` as its canonical store. This branch is not imported by `src/mttt/` and poses no runtime hazard, but its presence in the repo creates conceptual noise. It should be quarantined to `tools/legacy/` and explicitly excluded from CI.

**Debt 2: no atomic writes.** `_write_json_lf` calls `path.write_text(...)` directly, which is not atomic. A crash during write corrupts the file. This needs a temp-file rename pattern: write to `<path>.tmp`, then `Path.rename()`.

**Debt 3: `__pycache__/` tracked.** The zip contains compiled bytecode. This is a hygiene issue (tracked artifacts that drift from source) but does not affect correctness.

**Debt 4: `run_from_json_dir.py` duplication.** The file exists both at repo root and under `scripts/`. The root version uses bare imports (`from loader_json import ...`) that work only when run from the repo root. This will silently break under `pip install -e .`.

---

## 2. Compatibility with Event Sourcing

### 2.1 Modules that can remain intact

**`model.py`** — pure dataclasses, no I/O. Fully reusable. The `Node`, `Edge`, `Facets` types become the output types of the projection builder.

**`invariants.py`** — pure function `(List[Node], List[Edge]) → InvariantReport`. Ideal projection validator. No changes required.

**`cnl_lint.py`** — pure function `(List[Node]) → List[CnlLintIssue]`. Reusable without modification.

**`derived_status.py`** — pure function `(List[Node], List[Edge]) → Dict[str, DerivedState]`. The derived state layer sits naturally at the end of the replay pipeline.

**`resume_ranking.py`** — pure function over derived state. No changes required.

**`pipeline.py`** — `compute_ui_state()` becomes the projection validator. It should be renamed (e.g., `gate.validate_projection()`) but its logic is already correct for its new role.

### 2.2 Modules that become part of the replay engine

**`loader_json.py`** — currently loads `nodes.json` / `edges.json`. Its deserialization logic (JSON → typed dataclasses, enum parsing, BOM-safe read) should be extracted into a shared `deserialize.py` utility and reused by both the legacy snapshot loader (for migration) and the event deserializer. The directory-based `load_nodes_edges_from_dir` function itself becomes a compatibility shim used only during migration.

**`normalize_json.py`** — the serialization side (`_node_to_obj`, `_edge_to_obj`, `_write_json_lf`, `_canonicalize_nodes_edges`) becomes the snapshot serializer used by `mttt compact` and `mttt replay --write-snapshot`. The `normalize_dir` entry point becomes irrelevant once the event log is authoritative — the "normalize" operation has no meaning against an append-only log.

### 2.3 Modules that must be redesigned

**`cli.py`** — must be substantially rewritten. The two existing commands (`normalize`, `check`) need replacement or re-scoping. New commands (`event add`, `replay`, `compact`) require a write path that the current system entirely lacks.

**No event layer exists.** The entire `events/`, `replay/`, and `projections/` subsystems are absent. These must be built from scratch.

---

## 3. Target Architecture

### 3.1 Proposed package structure

```
src/mttt/
    __init__.py
    cli.py                   # CLI entrypoint; thin dispatch layer only

    events/
        __init__.py
        schema.py            # Event schema version, Pydantic or dataclass models
        types.py             # EventType enum; typed event dataclasses
        store.py             # append_event(), read_events(), hash_chain verification
        ids.py               # ULID generation; deterministic test IDs

    replay/
        __init__.py
        engine.py            # replay(events) -> (List[Node], List[Edge], ReplayMeta)
        checkpoint.py        # read/write checkpoint.snapshot.json

    projections/
        __init__.py
        builder.py           # build_projection(nodes, edges) -> ProjectionState
        sqlite_index.py      # write_sqlite_index(ProjectionState, path)
        snapshot.py          # write_state_snapshot(ProjectionState, path)

    graph/
        __init__.py
        model.py             # (current model.py, unchanged)
        serialize.py         # node/edge ↔ dict; extracted from normalize_json.py
        deserialize.py       # dict → node/edge; extracted from loader_json.py

    invariants/
        __init__.py
        check.py             # (current invariants.py, unchanged)
        cnl_lint.py          # (current cnl_lint.py, unchanged)
        gate.py              # (current pipeline.py, renamed; wraps check + lint + derived)

    derived/
        __init__.py
        status.py            # (current derived_status.py, unchanged)
        resume.py            # (current resume_ranking.py, unchanged)
```

### 3.2 Subsystem responsibilities

**`events/`** — owns the event log. `store.py` manages reads and writes to `data/events_v1.jsonl`: appending new events, reading the full sequence, and verifying the SHA-256 hash chain. The hash chain links each event record to its predecessor: `event.prev_hash = sha256(serialize(prev_event))`. `ids.py` generates ULIDs (monotonic, sortable, collision-resistant) for event IDs. `schema.py` defines the versioned event schema: a sealed union of typed event dataclasses (`NodeCreate`, `NodeUpdate`, `NodeDelete`, `EdgeCreate`, `EdgeDelete`, `CheckpointSnapshot`), validated on read and on write.

**`replay/`** — consumes `events/` output, produces `(List[Node], List[Edge])`. `engine.py` folds over the event sequence, applying each event to an accumulator (a mutable working set during replay, converted to frozen dataclasses at end). Replay is a pure function of the event sequence — given the same `events_v1.jsonl`, it always produces the same graph. `checkpoint.py` handles optional checkpoint events that embed a full snapshot, enabling replay to start from the most recent checkpoint rather than from genesis.

**`projections/`** — takes the replayed `(nodes, edges)` and materializes derived artifacts. `builder.py` calls the invariants gate and derived state pipeline, producing a `ProjectionState` that bundles the raw graph, invariant report, derived states, and resume pick. `sqlite_index.py` writes `build/index_v1.sqlite` (read-optimized; not authoritative). `snapshot.py` writes `build/state_v1.json` (deterministic serialization of the full projection).

**`graph/`** — pure data layer. `model.py` is unchanged. `serialize.py` and `deserialize.py` extract the conversion logic currently scattered across `loader_json.py` and `normalize_json.py`, making them importable by both the event layer and any compatibility shims.

**`invariants/`** — unchanged logic; reorganized into a subpackage for explicitness. `gate.py` replaces `pipeline.py` as the validated projection builder.

**`derived/`** — unchanged logic; reorganized.

### 3.3 Data flow

```
[mttt event add node.create ...]
    → events/store.append_event(event)
    → data/events_v1.jsonl (append-only)

[mttt replay]
    → events/store.read_events()
    → replay/engine.replay(events) → (nodes, edges)
    → invariants/gate.validate_projection(nodes, edges) → ProjectionState
    → projections/snapshot.write(ProjectionState) → build/state_v1.json
    → projections/sqlite_index.write(ProjectionState) → build/index_v1.sqlite

[mttt check]
    → replay() → validate_projection() → print InvariantReport

[mttt resume]
    → replay() → validate_projection() → print ResumePick

[mttt compact]
    → replay() → events/store.write_checkpoint(snapshot)
    → prunes events before checkpoint from active log (or archives to events_v1.jsonl.bak)
```

---

## 4. Migration Plan

### Phase 0 — Pre-migration hygiene (prerequisite; no behavior change)

Fix the two correctness hazards that will cause problems during migration regardless:

- Replace `path.write_text(...)` in `_write_json_lf` with an atomic temp-file rename. This is a one-line fix: write to `path.with_suffix('.tmp')`, then `Path.rename(path)`.
- Fix `run_from_json_dir.py` bare imports; delete the root-level duplicate, keep only `scripts/run_from_json_dir.py`, update to package-relative imports.
- Move `scripts/ttree.py`, `tree.db`, `tree.db.bak` to `tools/legacy/`. Add a `.gitignore` entry for `tools/legacy/tree.db`. Confirm no test file imports from `scripts/`.

These changes are non-breaking and can be committed independently.

### Phase 1 — Introduce the event layer (additive; no CLI changes yet)

Create `src/mttt/events/` with `types.py`, `schema.py`, `store.py`, `ids.py`.

Define the minimal event schema:

```python
@dataclass(frozen=True)
class EventRecord:
    event_id: str         # ULID
    event_type: str       # "node.create" | "node.update" | "node.delete" | "edge.create" | "edge.delete"
    schema_version: str   # "v1"
    timestamp_utc: str    # ISO-8601
    prev_hash: str        # SHA-256 of previous serialized event; "0"*64 for first
    payload: dict         # event-type-specific fields
```

Implement `append_event()` and `read_events()` with hash chain construction and verification. Write unit tests: append three events, read them back, verify hash chain, assert byte-stable JSONL serialization.

At this point, nothing in the existing CLI changes. The event layer is an isolated new module.

**Dependency:** Phase 0 complete.

### Phase 2 — Replay engine

Create `src/mttt/replay/engine.py`. Implement `replay(events: List[EventRecord]) -> Tuple[List[Node], List[Edge]]`.

The replay fold applies events in order:

- `node.create`: construct `Node` from payload, add to working set (reject duplicate ID as a replay invariant violation).
- `node.update`: patch facets/slots on existing node (reject if node not present).
- `node.delete`: remove node and all edges referencing it.
- `edge.create` / `edge.delete`: straightforward set operations.
- `checkpoint.snapshot`: replace working set with embedded snapshot (skip event processing before this point if fast replay is desired).

Write a golden test: a fixed `events_v1.jsonl` with known content → assert deterministic replay output matches expected `(nodes, edges)`. This golden test is the replay contract.

**Dependency:** Phase 1 complete; `graph/model.py` available (unchanged from current `model.py`).

### Phase 3 — Convert normalization into projection builder

Extract `serialize.py` and `deserialize.py` from `loader_json.py` and `normalize_json.py`. Move to `graph/`. Update imports.

Create `projections/builder.py` that calls the existing `gate.validate_projection` (renamed from `pipeline.compute_ui_state`). Wire: `replay(events) → builder.build_projection(nodes, edges) → ProjectionState`.

Write a round-trip test: construct events programmatically → replay → project → assert `InvariantReport.ok == True` and `ResumePick.node_id` matches expected.

The existing `test_semantic_snapshot.py` should continue to pass because `compute_ui_state` logic is unchanged — only its call site moves.

**Dependency:** Phase 2 complete.

### Phase 4 — Refactor CLI

Add `mttt event add` command. This is the first write path: it parses user-supplied arguments into an `EventRecord`, appends to `data/events_v1.jsonl`, then calls replay → project to validate the resulting graph. If validation fails, the event is not persisted (validate-before-append pattern).

Add `mttt replay` command: reads events, runs replay + projection, writes `build/state_v1.json` and `build/index_v1.sqlite`.

Re-scope `mttt check` to call `replay() → validate_projection()` rather than `load_nodes_edges_from_dir()`.

Re-scope or remove `mttt normalize`. In the event-sourced model, the serialization format of the event log is fixed at write time (events are never re-sorted or re-serialized). The `normalize` command is only meaningful for migrating legacy `nodes.json` / `edges.json` into the event log (see Phase 5).

Add `mttt compact`: replay → write `checkpoint.snapshot` event → truncate pre-checkpoint events to an archive file.

**Dependency:** Phase 3 complete.

### Phase 5 — Migration of legacy state and removal of legacy loaders

Write a one-time migration script (`tools/migrate_json_to_events.py`) that:

1. calls `load_nodes_edges_from_dir(legacy_dir)` on an existing `nodes.json` / `edges.json`,
2. emits one `node.create` event per node and one `edge.create` event per edge (with stable synthetic ULIDs derived from node/edge content hashes for reproducibility),
3. writes `data/events_v1.jsonl`.

After migration, verify: `mttt replay` produces `build/state_v1.json` whose `nodes` and `edges` match the original JSON files byte-for-byte (modulo sort order, which normalization already guaranteed).

Once migration is verified, `load_nodes_edges_from_dir` can be removed from the production import path and moved to `tools/` alongside the migration script. The `normalize_dir` entry point is retired. The existing `fixtures/` directory retains its `nodes.json` / `edges.json` files for use as test fixtures only — they are not read by the production CLI.

**Dependency:** Phase 4 complete; manual verification of migration output.

---

## 5. Determinism Guarantees in the Event-Sourced Architecture

### 5.1 Event log determinism

Each event record is serialized as a single-line JSON object with `sort_keys=True`, `ensure_ascii=False`, no trailing whitespace, LF terminator. Event IDs are ULIDs: 48-bit millisecond timestamp + 80-bit cryptographically random suffix. ULIDs are monotonically increasing within the same millisecond; they do not depend on process state beyond the current time. For test environments, a seeded deterministic ULID generator should be provided (`ids.py:make_test_id(seed: int)`).

The hash chain enforces append-only semantics: `event.prev_hash = sha256(event[i-1].serialized)`. Any insertion, deletion, or reordering of events in the log is detectable by re-verifying the chain. This is not encryption; it is tamper-evidence.

### 5.2 Replay determinism

Replay is a pure left-fold over the event sequence. Given the same JSONL file, byte-for-byte identical replay output is guaranteed because:

- event deserialization is deterministic (same schema, same enum parsing),
- the fold accumulator uses sorted sets (nodes sorted by `id`; edges sorted by `(src, type.value, dst)`) at materialization time,
- no external state (timestamps, random values, environment variables) is read during replay.

The replay engine must not call `datetime.now()` or `uuid4()`. Any time-dependent logic (e.g., "is this task due today?") must receive its clock value as an explicit parameter.

### 5.3 Projection determinism

The projection pipeline (`invariants`, `cnl_lint`, `derived_status`, `resume_ranking`) is already deterministic. The only requirement is that it receives a deterministically ordered `(nodes, edges)` list — which replay guarantees.

The `build/state_v1.json` snapshot is produced by the same `_write_json_lf` serializer used by the legacy normalizer. SHA-256 fingerprinting of `build/state_v1.json` provides a stable artifact identity for audit purposes.

### 5.4 Auditability

The `build/state_v1.json` should include a `_meta` block:

```json
{
  "_meta": {
    "schema_version": "v1",
    "event_count": 42,
    "log_sha256": "<sha256 of events_v1.jsonl>",
    "replay_timestamp_utc": "2026-03-04T12:00:00Z",
    "mttt_version": "0.2.0",
    "python_version": "3.11.x"
  },
  "nodes": [...],
  "edges": [...],
  ...
}
```

This makes every snapshot traceable to its source log and the tool version that produced it.

---

## 6. Major Architectural Risks

### Risk 1: Projection divergence after schema evolution

**Description.** Event schema changes (adding a field, changing an enum value, renaming an event type) are applied retroactively during replay if the deserializer is updated without a migration path. The result is that the same `events_v1.jsonl` produces different `(nodes, edges)` under different versions of `replay/engine.py`. This is the event-sourcing equivalent of a silent data migration bug.

**Mitigation.** Each event record must carry a `schema_version` field. The replay engine must be version-dispatched: `replay_v1_event(record)` handles `schema_version == "v1"` events; future versions get their own handler. Old events are never rewritten. When a new schema version is introduced, a migration event type (`schema.migrate`) can be appended to the log, after which subsequent events use the new schema. The version dispatch table is the authoritative migration record. Test this with a fixture that contains events from multiple schema versions.

### Risk 2: Nondeterministic ULID generation in tests

**Description.** If tests use real ULID generation (wall-clock time + randomness), replay golden tests will fail intermittently when event IDs differ across runs, or when two events within the same millisecond produce different orderings on different platforms.

**Mitigation.** `ids.py` must expose two interfaces: `make_ulid()` for production (real randomness) and `make_test_ulid(seed: int)` for tests (deterministic). All test fixtures that construct `EventRecord` objects must use `make_test_ulid`. The `replay/engine.py` golden test must use a fixed, checked-in `events_v1.jsonl` file rather than constructing events at test time — this ensures the test is a replay test, not a construction test.

### Risk 3: CLI/state coupling during the migration window

**Description.** Phases 1–4 involve a period where the CLI still calls `load_nodes_edges_from_dir` directly (current behavior) while the event layer is being built alongside it. If any CLI command is updated to use replay before the replay engine is complete, the system will have two incompatible state acquisition paths simultaneously. Any test that exercises both will be fragile during this window.

**Mitigation.** Introduce a single `state_provider` abstraction at the start of Phase 4 — a callable `() -> Tuple[List[Node], List[Edge]]` — that can be backed by either the legacy file loader or the replay engine. Both `cmd_check` and `cmd_normalize` (and all future commands) take this abstraction as a dependency-injected parameter, never importing a loader directly. During Phase 4, the default implementation switches from `load_nodes_edges_from_dir` to `replay`. This provides a clean, testable seam and prevents the dual-path fragility.

---

## 7. Minimal Viability Milestone

**Milestone: deterministic event append + replay producing `build/state_v1.json`**

Scope: Phases 1 and 2 only (plus Phase 0 hygiene). No CLI changes beyond adding `mttt event add` and `mttt replay`. Legacy `check` and `normalize` commands remain unchanged.

**Success criteria:**

1. `mttt event add node.create --id G1 --kind GOAL --text "Achieve a stable daily routine." --slot is_root=true` appends a valid, hash-chained event to `data/events_v1.jsonl`.

2. `mttt event add node.create --id T1 --kind TASK --text "Do plan tomorrow morning routine." --facet est_minutes=20` appends a second event; its `prev_hash` matches `sha256(line_1)`.

3. `mttt event add edge.create --src G1 --type decomposes_into --dst T1` appends a third event.

4. `mttt replay` reads the three events, replays them to `(nodes=[G1, T1], edges=[G1→T1])`, runs the full projection pipeline, writes `build/state_v1.json`.

5. `sha256(build/state_v1.json)` is identical across three independent runs of `mttt replay` on the same `data/events_v1.jsonl`.

6. The existing `test_determinism.py` and `test_semantic_snapshot.py` still pass (legacy path not yet removed).

7. A new `tests/test_replay_golden.py` asserts that a checked-in `fixtures/events_golden_v1.jsonl` replays to a checked-in `fixtures/events_golden_v1.snapshot.json`, byte-for-byte.

This milestone proves the core invariant of the new architecture — that the event log is the authoritative source and that its projection is deterministic — without requiring any destruction of existing functionality.
