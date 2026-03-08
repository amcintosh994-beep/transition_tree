# Event State Pipeline

## Purpose

This document defines the event-authoritative state model for `transition_tree`.

The repository now supports two explicit state authority regimes:

- **snapshot regime**: authoritative state is loaded from canonical `nodes.json` / `edges.json`
- **events regime**: authoritative state is loaded by replaying `events.jsonl`

This document specifies the invariants, file formats, command behavior, and intended semantics of the event pipeline.

---

## Design Goal

The event system is designed to preserve the repository’s compiler-style guarantees:

- deterministic behavior
- explicit authority
- auditability
- drift resistance
- canonical serialization
- no silent fallback across authority regimes

The event system is intentionally minimal in its current form. It exists to provide a deterministic event backbone before introducing finer-grained mutation events.

---

## Authority Model

### Snapshot Regime

In snapshot regime, authoritative state is read directly from:

```text
nodes.json
edges.json
