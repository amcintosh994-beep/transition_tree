# normalize_json.py
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

from .model import Edge, Node


def _canonicalize_nodes_edges(nodes: List[Node], edges: List[Edge]) -> Tuple[List[Node], List[Edge]]:
    """
    Mirror loader_json.py sorting guarantees:
      nodes: by id
      edges: by (src, type.value, dst)
    """
    nodes_sorted = sorted(nodes, key=lambda n: n.id)
    edges_sorted = sorted(edges, key=lambda e: (e.src, e.type.value, e.dst))
    return nodes_sorted, edges_sorted


def _node_to_obj(n: Node) -> dict:
    """
    Stable, schema-ish projection of Node for JSON output.

    Important: we emit only fields the loader expects:
      id, kind, text, slots, facets
    """
    facets = n.facets
    facets_obj = {
        "status": facets.status.value,
        "commitment": (facets.commitment.value if facets.commitment else None),
        "recurring": bool(facets.recurring),
        "frequency": facets.frequency,
        "control_locus": (facets.control_locus.value if facets.control_locus else None),
        "domain": facets.domain,
        "est_minutes": facets.est_minutes,
    }

    # Drop None keys from facets for stable minimal output (optional but reduces churn).
    facets_obj = {k: v for k, v in facets_obj.items() if v is not None}

    return {
        "id": n.id,
        "kind": n.kind.value,
        "text": n.text,
        "slots": dict(sorted((n.slots or {}).items(), key=lambda kv: kv[0])),
        "facets": facets_obj,
    }


def _edge_to_obj(e: Edge) -> dict:
    return {
        "src": e.src,
        "type": e.type.value,
        "dst": e.dst,
    }


def _write_json_lf(path: Path, obj) -> None:
    """
    Deterministic JSON:
      - UTF-8 (no BOM)
      - LF newlines
      - sort_keys=True to prevent key-order drift
      - indent=2 for human review
      - trailing newline
    """
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    # Enforce LF regardless of platform/editor settings
    text = text.replace("\r\n", "\n").replace("\r", "\n") + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def save_nodes_edges_to_dir(dir_path: str | Path, nodes: List[Node], edges: List[Edge]) -> None:
    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)

    nodes_sorted, edges_sorted = _canonicalize_nodes_edges(nodes, edges)

    nodes_out = [_node_to_obj(n) for n in nodes_sorted]
    edges_out = [_edge_to_obj(e) for e in edges_sorted]

    _write_json_lf(d / "nodes.json", nodes_out)
    _write_json_lf(d / "edges.json", edges_out)


def normalize_dir(dir_path: str | Path) -> None:
    """
    Load canon and rewrite canon deterministically.
    """
    from .loader_json import load_nodes_edges_from_dir  # local import to avoid cycles

    nodes, edges = load_nodes_edges_from_dir(dir_path)
    save_nodes_edges_to_dir(dir_path, nodes, edges)




