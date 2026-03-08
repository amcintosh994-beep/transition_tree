# State authority
## Purpose

This document defines how authoritative state is selected in `transition tree`.

The repository supports two explicit state authority regimes:

- **snapshot regime**
- **events regime**

The central rule is simple:

> Authority must always be explicit.

No comand or internal module should infer authority implicitly from whichever files happen to be present in a directory.

---

## Snapshot regime

In snapshot regime, authoritative state is loaded from:

```text
nodes.json
edges.json