# mttt_model.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Kind(str, Enum):
    TASK = "TASK"
    GOAL = "GOAL"
    QUESTION = "QUESTION"
    ASSET = "ASSET"
    BLOCKER = "BLOCKER"


class EdgeType(str, Enum):
    REQUIRES_TASK = "requires_task"
    REQUIRES_ASSET = "requires_asset"
    BLOCKED_BY = "blocked_by"
    ANSWERS = "answers"
    DECOMPOSES_INTO = "decomposes_into"


class Status(str, Enum):
    ACTIVE = "active"
    PARKED = "parked"
    COMPLETED = "completed"
    MAINTENANCE_MODE = "maintenance_mode"


class Commitment(str, Enum):
    TENTATIVE = "tentative"
    DECIDED = "decided"


class ControlLocus(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


@dataclass(frozen=True)
class Facets:
    status: Status = Status.ACTIVE
    commitment: Optional[Commitment] = None
    # Temporal facet: recurrence must NOT be in canonical text.
    recurring: bool = False
    # If recurring, a simple canonical frequency string; refine later (RRULE).
    frequency: Optional[str] = None
    control_locus: Optional[ControlLocus] = None
    domain: Optional[str] = None
    # Optional deterministic UI hints
    est_minutes: Optional[int] = None


@dataclass(frozen=True)
class Node:
    id: str
    kind: Kind
    text: str  # canonical CNL sentence
    slots: Dict[str, str] = field(default_factory=dict)
    facets: Facets = field(default_factory=Facets)


@dataclass(frozen=True)
class Edge:
    src: str
    type: EdgeType
    dst: str
