# loader_json.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, List, Tuple
from .model import (
    Commitment,
    ControlLocus,
    Edge,
    EdgeType,
    Facets,
    Kind,
    Node,
    Status,
)
class LoadError(Exception):
    pass
def _parse_enum(enum_cls, val: Any, field: str) -> Any:
    if val is None:
        return None
    try:
        return enum_cls(val)
    except Exception as e:
        raise LoadError(f"Invalid enum value for {field}: {val}") from e
def load_nodes_edges_from_dir(dir_path: str | Path) -> Tuple[List[Node], List[Edge]]:
    d = Path(dir_path)
    nodes_path = d / "nodes.json"
    edges_path = d / "edges.json"
    if not nodes_path.exists():
        raise LoadError(f"Missing {nodes_path}")
    if not edges_path.exists():
        raise LoadError(f"Missing {edges_path}")
    # BOM-safe reads for Windows tooling
    nodes_raw = json.loads(nodes_path.read_text(encoding="utf-8-sig"))
    edges_raw = json.loads(edges_path.read_text(encoding="utf-8-sig"))
    if not isinstance(nodes_raw, list):
        raise LoadError("nodes.json must be a JSON list.")
    if not isinstance(edges_raw, list):
        raise LoadError("edges.json must be a JSON list.")
    nodes: List[Node] = []
    for obj in nodes_raw:
        if not isinstance(obj, dict):
            raise LoadError("Each node must be an object.")
        nid = obj.get("id")
        kind = obj.get("kind")
        text = obj.get("text")
        if not nid or not kind or not text:
            raise LoadError(f"Node missing required fields (id/kind/text): {obj}")
        facets_obj = obj.get("facets", {}) or {}
        slots_obj = obj.get("slots", {}) or {}
        facets = Facets(
            status=_parse_enum(Status, facets_obj.get("status", Status.ACTIVE.value), "facets.status"),
            commitment=_parse_enum(Commitment, facets_obj.get("commitment"), "facets.commitment"),
            recurring=bool(facets_obj.get("recurring", False)),
            frequency=facets_obj.get("frequency"),
            control_locus=_parse_enum(ControlLocus, facets_obj.get("control_locus"), "facets.control_locus"),
            domain=facets_obj.get("domain"),
            est_minutes=facets_obj.get("est_minutes"),
        )
        nodes.append(
            Node(
                id=str(nid),
                kind=_parse_enum(Kind, kind, "kind"),
                text=str(text),
                slots={str(k): str(v) for k, v in dict(slots_obj).items()},
                facets=facets,
            )
        )
    edges: List[Edge] = []
    for obj in edges_raw:
        if not isinstance(obj, dict):
            raise LoadError("Each edge must be an object.")
        src = obj.get("src")
        et = obj.get("type")
        dst = obj.get("dst")
        if not src or not et or not dst:
            raise LoadError(f"Edge missing required fields (src/type/dst): {obj}")
        edges.append(
            Edge(
                src=str(src),
                type=_parse_enum(EdgeType, et, "edge.type"),
                dst=str(dst),
            )
        )
    nodes.sort(key=lambda n: n.id)
    edges.sort(key=lambda e: (e.src, e.type.value, e.dst))
    return nodes, edges



