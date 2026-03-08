from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .events import load_and_replay_events
from .loader_json import load_nodes_edges_from_dir
from .model import Edge, Node


StateRegime = Literal["snapshot", "events"]


@dataclass(frozen=True)
class LoadedState:
    nodes: list[Node]
    edges: list[Edge]
    regime: StateRegime


def load_state(
    data_dir: Path,
    regime: StateRegime = "snapshot",
    *,
    until_ts: int | None = None,
) -> LoadedState:
    data_dir = Path(data_dir)

    if regime == "snapshot":
        nodes, edges = load_nodes_edges_from_dir(data_dir)
        return LoadedState(nodes=nodes, edges=edges, regime="snapshot")

    if regime == "events":
        materialized = load_and_replay_events(data_dir, until_ts=until_ts)
        return LoadedState(
            nodes=materialized.nodes,
            edges=materialized.edges,
            regime="events",
        )

    raise ValueError(f"Unknown state regime: {regime!r}")
