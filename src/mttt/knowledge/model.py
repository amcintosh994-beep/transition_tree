from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from ..domains import validate_domain
from ..model import EdgeType, Kind

MAX_SCAFFOLD_NODES = 8


@dataclass(frozen=True)
class NodeTemplate:
    kind: Kind
    text_template: str
    default_domain: Optional[str] = None
    default_est_minutes: Optional[int] = None
    slots: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_domain(self.default_domain, field_name="NodeTemplate.default_domain")


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

    def __post_init__(self) -> None:
        validate_domain(self.domain, field_name="Scaffold.domain")
        if len(self.node_templates) > MAX_SCAFFOLD_NODES:
            raise ValueError(
                f"Scaffold {self.scaffold_id!r} exceeds node ceiling "
                f"({len(self.node_templates)} > {MAX_SCAFFOLD_NODES})"
            )
