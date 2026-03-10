from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from ..model import EdgeType, Kind


@dataclass(frozen=True)
class NodeTemplate:
    kind: Kind
    text_template: str
    default_domain: Optional[str] = None
    default_est_minutes: Optional[int] = None
    slots: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DependencyTemplate:
    src_index: int
    edge_type: EdgeType
    dst_index: int


@dataclass(frozen=True)
class Scaffold:
    scaffold_id: str
    domain: str
    match_terms: Tuple[str, ...] = ()
    entrypoint_template_indices: Tuple[int, ...] = ()
    node_templates: Tuple[NodeTemplate, ...] = ()
    dependency_templates: Tuple[DependencyTemplate, ...] = ()
    evidence_strength: str = "authoritative"
    priority: int = 100

