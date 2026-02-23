# invariants.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

from mttt_model import Edge, EdgeType, Kind, Node, Status


@dataclass(frozen=True)
class InvariantError:
    code: str
    severity: str  # "ERROR" | "WARN"
    node_id: Optional[str]
    edge: Optional[Tuple[str, str, str]]  # (src, type, dst)
    message: str


@dataclass(frozen=True)
class InvariantReport:
    ok: bool
    errors: List[InvariantError]
    warnings: List[InvariantError]

    def to_text(self) -> str:
        lines: List[str] = []
        if self.ok:
            lines.append("OK: invariants satisfied.")
        else:
            lines.append("FAIL: invariants violated.")
        if self.errors:
            lines.append("")
            lines.append("Errors:")
            for e in self.errors:
                where = f" node={e.node_id}" if e.node_id else ""
                if e.edge:
                    where += f" edge={e.edge}"
                lines.append(f"- [{e.code}] {e.message}{where}")
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self.warnings:
                where = f" node={w.node_id}" if w.node_id else ""
                if w.edge:
                    where += f" edge={w.edge}"
                lines.append(f"- [{w.code}] {w.message}{where}")
        return "\n".join(lines)


class InvariantCodes:
    TASK_MISSING_ESTIMATE = "E070"
    TASK_ESTIMATE_TOO_LARGE = "E071"
    TASK_VERB_BLACKLIST = "E072"
    # Referential integrity
    UNKNOWN_NODE_REFERENCE = "E001"
    DUPLICATE_NODE_ID = "E002"
    # Kind/edge compatibility
    INVALID_EDGE_ENDPOINT = "E010"
    # Orphans / required linkage
    ORPHAN_BLOCKER = "E020"
    ORPHAN_ASSET = "E021"
    GOAL_WITHOUT_DECOMPOSITION = "E022"
    # Requires-task cycle
    REQUIRES_TASK_CYCLE = "E030"
    # QUESTION discharge and completion behavior
    COMPLETED_QUESTION_NO_DISCHARGE = "E040"
    # Recurrence facet correctness
    RECURRING_TASK_NO_FREQUENCY = "E050"
    NON_TASK_HAS_RECURRENCE = "E051"
    # Completed node blocking others
    COMPLETED_BLOCKER = "W060"  # weird but possible: blocker completed is odd; treat as warn.


def build_index(nodes: Iterable[Node]) -> Dict[str, Node]:
    idx: Dict[str, Node] = {}
    for n in nodes:
        if n.id in idx:
            # keep first; report duplicates later
            continue
        idx[n.id] = n
    return idx


def _find_duplicate_ids(nodes: Iterable[Node]) -> Set[str]:
    seen: Set[str] = set()
    dup: Set[str] = set()
    for n in nodes:
        if n.id in seen:
            dup.add(n.id)
        else:
            seen.add(n.id)
    return dup


def _adjacency(edges: List[Edge], et: EdgeType) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for e in edges:
        if e.type != et:
            continue
        out.setdefault(e.src, []).append(e.dst)
    # deterministic ordering
    for k in out:
        out[k] = sorted(out[k])
    return out


def _has_cycle_requires_task(nodes_by_id: Dict[str, Node], edges: List[Edge]) -> List[List[str]]:
    """
    Returns list of cycles (each as list of node ids) for requires_task graph.
    Deterministic: sorts adjacency, and DFS order by node id.
    """
    adj = _adjacency(edges, EdgeType.REQUIRES_TASK)
    visited: Set[str] = set()
    stack: Set[str] = set()
    parent: Dict[str, str] = {}
    cycles: List[List[str]] = []

    def dfs(u: str):
        visited.add(u)
        stack.add(u)
        for v in adj.get(u, []):
            if v not in nodes_by_id:
                continue
            if v not in visited:
                parent[v] = u
                dfs(v)
            elif v in stack:
                # found back-edge u -> v; reconstruct cycle deterministically
                cyc = [v]
                cur = u
                while cur != v and cur in parent:
                    cyc.append(cur)
                    cur = parent[cur]
                cyc.append(v)
                cyc = list(reversed(cyc))
                cycles.append(cyc)
        stack.remove(u)

    for nid in sorted(nodes_by_id.keys()):
        if nid not in visited:
            dfs(nid)

    # de-duplicate cycles by canonical string
    uniq: Dict[str, List[str]] = {}
    for c in cycles:
        key = "->".join(c)
        uniq[key] = c
    return [uniq[k] for k in sorted(uniq.keys())]


def check_invariants(
    nodes: List[Node],
    edges: List[Edge],
    *,
    fast_fail: bool = True,
) -> InvariantReport:
    errors: List[InvariantError] = []
    warns: List[InvariantError] = []
    nodes_by_id = {n.id: n for n in nodes}
    
    # TASK must be session-sized (heuristic)
    # Policy:
    # - est_minutes is REQUIRED for TASK unless explicitly exempted (slots["no_estimate"] == "true")
    # - est_minutes must be <= 180 by default (3 hours). Tune later.
    # - blacklist verbs that reliably signal multi-session scope.
    import re

    verb_blacklist = re.compile(
        r"\b(organize|overhaul|revamp|learn|master|become|improve|transition|stabilize|research)\b",
        re.IGNORECASE,
    )
    max_minutes = 180

    for n in sorted(nodes_by_id.values(), key=lambda x: x.id):
        if n.kind != Kind.TASK:
            continue

        if verb_blacklist.search(n.text):
            errors.append(
                InvariantError(
                    code=InvariantCodes.TASK_VERB_BLACKLIST,
                    severity="ERROR",
                    node_id=n.id,
                    edge=None,
                    message="TASK appears multi-session/abstract by verb heuristic; convert to GOAL or split into smaller TASKs.",
                )
            )
            if fast_fail:
                return InvariantReport(ok=False, errors=errors, warnings=warns)

        exempt = (n.slots.get("no_estimate", "").lower() == "true")
        if not exempt and n.facets.est_minutes is None:
            errors.append(
                InvariantError(
                    code=InvariantCodes.TASK_MISSING_ESTIMATE,
                    severity="ERROR",
                    node_id=n.id,
                    edge=None,
                    message="TASK must provide est_minutes (or set slots.no_estimate=true).",
                )
            )
            if fast_fail:
                return InvariantReport(ok=False, errors=errors, warnings=warns)

        if n.facets.est_minutes is not None and n.facets.est_minutes > max_minutes:
            errors.append(
                InvariantError(
                    code=InvariantCodes.TASK_ESTIMATE_TOO_LARGE,
                    severity="ERROR",
                    node_id=n.id,
                    edge=None,
                    message=f"TASK est_minutes exceeds {max_minutes}; split into multiple TASKs.",
                )
            )
            if fast_fail:
                return InvariantReport(ok=False, errors=errors, warnings=warns)


    dup_ids = sorted(_find_duplicate_ids(nodes))
    if dup_ids:
        for did in dup_ids:
            errors.append(
                InvariantError(
                    code=InvariantCodes.DUPLICATE_NODE_ID,
                    severity="ERROR",
                    node_id=did,
                    edge=None,
                    message="Duplicate node id.",
                )
            )
        if fast_fail:
            return InvariantReport(ok=False, errors=errors, warnings=warns)

    # Referential integrity for edges
    for e in sorted(edges, key=lambda x: (x.src, x.type.value, x.dst)):
        if e.src not in nodes_by_id or e.dst not in nodes_by_id:
            errors.append(
                InvariantError(
                    code=InvariantCodes.UNKNOWN_NODE_REFERENCE,
                    severity="ERROR",
                    node_id=None,
                    edge=(e.src, e.type.value, e.dst),
                    message="Edge references unknown node id.",
                )
            )
            if fast_fail:
                return InvariantReport(ok=False, errors=errors, warnings=warns)

    # Edge endpoint compatibility (non-leaky lattice enforcement)
    for e in sorted(edges, key=lambda x: (x.src, x.type.value, x.dst)):
        src = nodes_by_id[e.src]
        dst = nodes_by_id[e.dst]

        def bad(msg: str):
            errors.append(
                InvariantError(
                    code=InvariantCodes.INVALID_EDGE_ENDPOINT,
                    severity="ERROR",
                    node_id=None,
                    edge=(e.src, e.type.value, e.dst),
                    message=msg,
                )
            )

        if e.type == EdgeType.REQUIRES_TASK:
            if dst.kind != Kind.TASK:
                bad("requires_task dst must be TASK.")
        elif e.type == EdgeType.REQUIRES_ASSET:
            if dst.kind != Kind.ASSET:
                bad("requires_asset dst must be ASSET.")
        elif e.type == EdgeType.BLOCKED_BY:
            if dst.kind != Kind.BLOCKER:
                bad("blocked_by dst must be BLOCKER.")
        elif e.type == EdgeType.ANSWERS:
            if src.kind != Kind.TASK or dst.kind != Kind.QUESTION:
                bad("answers must be TASK -> QUESTION.")
        elif e.type == EdgeType.DECOMPOSES_INTO:
            if src.kind != Kind.GOAL:
                bad("decomposes_into src must be GOAL.")
        # else: unknown enum not possible

        if errors and fast_fail:
            return InvariantReport(ok=False, errors=errors, warnings=warns)

    # Orphan blockers/assets
    blocked_by_edges = [e for e in edges if e.type == EdgeType.BLOCKED_BY]
    blockers_referenced: Set[str] = {e.dst for e in blocked_by_edges}
    for n in sorted(nodes_by_id.values(), key=lambda x: x.id):
        if n.kind == Kind.BLOCKER and n.id not in blockers_referenced:
            errors.append(
                InvariantError(
                    code=InvariantCodes.ORPHAN_BLOCKER,
                    severity="ERROR",
                    node_id=n.id,
                    edge=None,
                    message="BLOCKER is not referenced by any blocked_by edge.",
                )
            )
            if fast_fail:
                return InvariantReport(ok=False, errors=errors, warnings=warns)
        if n.kind == Kind.ASSET:
            # must be referenced OR explicitly informational
            has_ref = any(e.type == EdgeType.REQUIRES_ASSET and e.dst == n.id for e in edges)
            informational = (n.slots.get("informational", "").lower() == "true")
            if not has_ref and not informational:
                errors.append(
                    InvariantError(
                        code=InvariantCodes.ORPHAN_ASSET,
                        severity="ERROR",
                        node_id=n.id,
                        edge=None,
                        message="ASSET is not referenced by requires_asset and not marked informational.",
                    )
                )
                if fast_fail:
                    return InvariantReport(ok=False, errors=errors, warnings=warns)

    # GOAL must decompose (except if explicitly root and allowed)
    goal_decomp = {e.src for e in edges if e.type == EdgeType.DECOMPOSES_INTO}
    for n in sorted(nodes_by_id.values(), key=lambda x: x.id):
        if n.kind == Kind.GOAL:
            is_root = (n.slots.get("is_root", "").lower() == "true")
            if n.id not in goal_decomp and not is_root:
                errors.append(
                    InvariantError(
                        code=InvariantCodes.GOAL_WITHOUT_DECOMPOSITION,
                        severity="ERROR",
                        node_id=n.id,
                        edge=None,
                        message="GOAL has no decomposes_into edges (and is not marked root).",
                    )
                )
                if fast_fail:
                    return InvariantReport(ok=False, errors=errors, warnings=warns)

    # Recurrence facet correctness
    for n in sorted(nodes_by_id.values(), key=lambda x: x.id):
        if n.facets.recurring:
            if n.kind != Kind.TASK:
                errors.append(
                    InvariantError(
                        code=InvariantCodes.NON_TASK_HAS_RECURRENCE,
                        severity="ERROR",
                        node_id=n.id,
                        edge=None,
                        message="Only TASK nodes may have recurring facet.",
                    )
                )
                if fast_fail:
                    return InvariantReport(ok=False, errors=errors, warnings=warns)
            if not n.facets.frequency:
                errors.append(
                    InvariantError(
                        code=InvariantCodes.RECURRING_TASK_NO_FREQUENCY,
                        severity="ERROR",
                        node_id=n.id,
                        edge=None,
                        message="Recurring TASK must provide a frequency.",
                    )
                )
                if fast_fail:
                    return InvariantReport(ok=False, errors=errors, warnings=warns)

    # requires_task cycles (deadlock prevention)
    cycles = _has_cycle_requires_task(nodes_by_id, edges)
    for cyc in cycles:
        errors.append(
            InvariantError(
                code=InvariantCodes.REQUIRES_TASK_CYCLE,
                severity="ERROR",
                node_id=None,
                edge=None,
                message=f"requires_task cycle detected: {' -> '.join(cyc)}",
            )
        )
        if fast_fail:
            return InvariantReport(ok=False, errors=errors, warnings=warns)

    # Completed QUESTION must discharge (enforced by edges)
    # Discharge defined as: QUESTION has at least one incoming answers edge OR outgoing decomposes_into/other linkage.
    answers_in: Dict[str, int] = {}
    for e in edges:
        if e.type == EdgeType.ANSWERS:
            answers_in[e.dst] = answers_in.get(e.dst, 0) + 1

    for n in sorted(nodes_by_id.values(), key=lambda x: x.id):
        if n.kind == Kind.QUESTION and n.facets.status == Status.COMPLETED:
            if answers_in.get(n.id, 0) == 0 and n.slots.get("discharged", "").lower() != "true":
                errors.append(
                    InvariantError(
                        code=InvariantCodes.COMPLETED_QUESTION_NO_DISCHARGE,
                        severity="ERROR",
                        node_id=n.id,
                        edge=None,
                        message="Completed QUESTION has no answers edge and is not marked discharged.",
                    )
                )
                if fast_fail:
                    return InvariantReport(ok=False, errors=errors, warnings=warns)

    # Minor warning: BLOCKER being marked completed is odd; allow but warn
    for n in sorted(nodes_by_id.values(), key=lambda x: x.id):
        if n.kind == Kind.BLOCKER and n.facets.status == Status.COMPLETED:
            warns.append(
                InvariantError(
                    code=InvariantCodes.COMPLETED_BLOCKER,
                    severity="WARN",
                    node_id=n.id,
                    edge=None,
                    message="BLOCKER marked completed; usually blockers clear via conditions rather than completion.",
                )
            )

    ok = len(errors) == 0
    return InvariantReport(ok=ok, errors=errors, warnings=warns)
