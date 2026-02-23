# tests/fixtures.py
from __future__ import annotations

from typing import List, Tuple

from mttt_model import Commitment, Edge, EdgeType, Facets, Kind, Node, Status


def fixture_valid_minimal() -> Tuple[List[Node], List[Edge]]:
    nodes = [
        Node(
            id="G1",
            kind=Kind.GOAL,
            text="Achieve a stable daily routine.",
            slots={"is_root": "true"},
            facets=Facets(status=Status.ACTIVE, commitment=Commitment.DECIDED, domain="integration"),
        ),
        Node(
            id="T1",
            kind=Kind.TASK,
            text="Do plan tomorrow morning routine.",
            slots={},
            facets=Facets(status=Status.ACTIVE, est_minutes=20, domain="integration"),
        ),
    ]
    edges = [
        Edge(src="G1", type=EdgeType.DECOMPOSES_INTO, dst="T1"),
    ]
    return nodes, edges


def fixture_invalid_goal_no_decomp() -> Tuple[List[Node], List[Edge]]:
    nodes = [
        Node(
            id="G2",
            kind=Kind.GOAL,
            text="Achieve a consistent skincare routine.",
            slots={},  # not root
            facets=Facets(status=Status.ACTIVE, commitment=Commitment.DECIDED, domain="care"),
        )
    ]
    edges = []
    return nodes, edges


def fixture_invalid_task_missing_estimate() -> Tuple[List[Node], List[Edge]]:
    nodes = [
        Node(
            id="G3",
            kind=Kind.GOAL,
            text="Achieve more consistent voice practice.",
            slots={"is_root": "true"},
            facets=Facets(status=Status.ACTIVE, commitment=Commitment.DECIDED, domain="voice"),
        ),
        Node(
            id="T2",
            kind=Kind.TASK,
            text="Do practice voice for 30 minutes.",
            slots={},
            facets=Facets(status=Status.ACTIVE, domain="voice"),  # missing est_minutes
        ),
    ]
    edges = [Edge(src="G3", type=EdgeType.DECOMPOSES_INTO, dst="T2")]
    return nodes, edges


def fixture_invalid_requires_task_cycle() -> Tuple[List[Node], List[Edge]]:
    nodes = [
        Node(id="T3", kind=Kind.TASK, text="Do draft email to clinic.", facets=Facets(est_minutes=10)),
        Node(id="T4", kind=Kind.TASK, text="Do call clinic to confirm details.", facets=Facets(est_minutes=10)),
        Node(id="G4", kind=Kind.GOAL, text="Achieve scheduling a consultation.", slots={"is_root": "true"}),
    ]
    edges = [
        Edge(src="G4", type=EdgeType.DECOMPOSES_INTO, dst="T3"),
        Edge(src="G4", type=EdgeType.DECOMPOSES_INTO, dst="T4"),
        Edge(src="T3", type=EdgeType.REQUIRES_TASK, dst="T4"),
        Edge(src="T4", type=EdgeType.REQUIRES_TASK, dst="T3"),
    ]
    return nodes, edges


def fixture_invalid_cnl_template() -> Tuple[List[Node], List[Edge]]:
    nodes = [
        Node(
            id="T5",
            kind=Kind.TASK,
            text="Execute book appointment.",  # wrong template (v0.2 expects "Do ... .")
            facets=Facets(est_minutes=5),
        ),
        Node(
            id="G5",
            kind=Kind.GOAL,
            text="Achieve booking appointment.",
            slots={"is_root": "true"},
        ),
    ]
    edges = [Edge(src="G5", type=EdgeType.DECOMPOSES_INTO, dst="T5")]
    return nodes, edges


def fixture_invalid_conjunction_split_needed() -> Tuple[List[Node], List[Edge]]:
    nodes = [
        Node(
            id="T6",
            kind=Kind.TASK,
            text="Do call clinic and ask about pricing.",
            facets=Facets(est_minutes=15),
        ),
        Node(
            id="G6",
            kind=Kind.GOAL,
            text="Achieve understanding clinic pricing.",
            slots={"is_root": "true"},
        ),
    ]
    edges = [Edge(src="G6", type=EdgeType.DECOMPOSES_INTO, dst="T6")]
    return nodes, edges
