from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ..events import _atomic_append_line, _canonical_event_json, load_events, make_event
from .model import DependencyTemplate, NodeTemplate, Scaffold
from ..model import EdgeType, Kind


KNOWLEDGE_EVENTS_FILENAME = "knowledge_events.jsonl"

KNOWLEDGE_SCAFFOLD_CONFIRMED = "KNOWLEDGE_SCAFFOLD_CONFIRMED"

APPLY_SCAFFOLD_PROPOSAL = "APPLY_SCAFFOLD_PROPOSAL"

def _scaffold_application_payload(
    *,
    goal_id: str,
    scaffold_id: str,
    source_domain: str,
    evidence_strength: str,
    proposed_nodes: list[Node],
    proposed_edges: list[Edge],
) -> dict:
    return {
        "goal_id": goal_id,
        "scaffold_id": scaffold_id,
        "source_domain": source_domain,
        "evidence_strength": evidence_strength,
        "proposed_nodes": [_node_to_obj(n) for n in proposed_nodes],
        "proposed_edges": [_edge_to_obj(e) for e in proposed_edges],
    }



def _scaffold_to_payload(scaffold: Scaffold) -> dict:
    return {
        "scaffold_id": scaffold.scaffold_id,
        "domain": scaffold.domain,
        "match_terms": list(scaffold.match_terms),
        "entrypoint_template_indices": list(scaffold.entrypoint_template_indices),
        "node_templates": [
            {
                "kind": nt.kind.value,
                "text_template": nt.text_template,
                "default_domain": nt.default_domain,
                "default_est_minutes": nt.default_est_minutes,
                "slots": dict(nt.slots),
            }
            for nt in scaffold.node_templates
        ],
        "dependency_templates": [
            {
                "src_index": dt.src_index,
                "edge_type": dt.edge_type.value,
                "dst_index": dt.dst_index,
            }
            for dt in scaffold.dependency_templates
        ],
        "evidence_strength": scaffold.evidence_strength,
        "priority": scaffold.priority,
    }


def scaffold_from_payload(payload: dict) -> Scaffold:
    return Scaffold(
        scaffold_id=payload["scaffold_id"],
        domain=payload["domain"],
        match_terms=tuple(payload.get("match_terms", [])),
        entrypoint_template_indices=tuple(payload.get("entrypoint_template_indices", [])),
        node_templates=tuple(
            NodeTemplate(
                kind=Kind(obj["kind"]),
                text_template=obj["text_template"],
                default_domain=obj.get("default_domain"),
                default_est_minutes=obj.get("default_est_minutes"),
                slots=dict(obj.get("slots", {})),
            )
            for obj in payload.get("node_templates", [])
        ),
        dependency_templates=tuple(
            DependencyTemplate(
                src_index=obj["src_index"],
                edge_type=EdgeType(obj["edge_type"]),
                dst_index=obj["dst_index"],
            )
            for obj in payload.get("dependency_templates", [])
        ),
        evidence_strength=payload.get("evidence_strength", "authoritative"),
        priority=payload.get("priority", 100),
    )

def append_apply_scaffold_proposal_event(
    data_dir: Path,
    *,
    goal_id: str,
    scaffold_id: str,
    source_domain: str,
    evidence_strength: str,
    proposed_nodes: list[Node],
    proposed_edges: list[Edge],
    ts: int | None = None,
) -> Path:
    payload = _scaffold_application_payload(
        goal_id=goal_id,
        scaffold_id=scaffold_id,
        source_domain=source_domain,
        evidence_strength=evidence_strength,
        proposed_nodes=proposed_nodes,
        proposed_edges=proposed_edges,
    )
    event = make_event(APPLY_SCAFFOLD_PROPOSAL, payload, ts=ts)
    path = Path(data_dir) / EVENTS_FILENAME
    _atomic_append_line(path, _canonical_event_json(event))
    return path

def append_scaffold_confirmed_event(
    data_dir: Path,
    scaffold: Scaffold,
    *,
    ts: int | None = None,
) -> Path:
    event = make_event(
        KNOWLEDGE_SCAFFOLD_CONFIRMED,
        _scaffold_to_payload(scaffold),
        ts=ts,
    )
    path = Path(data_dir) / KNOWLEDGE_EVENTS_FILENAME
    _atomic_append_line(path, _canonical_event_json(event))
    return path


def load_knowledge_events(data_dir: Path):
    path = Path(data_dir) / KNOWLEDGE_EVENTS_FILENAME
    if not path.is_file():
        return []
    return load_events(path)

