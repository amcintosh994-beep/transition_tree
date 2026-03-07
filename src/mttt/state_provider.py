from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Protocol

from .loader_json import load_nodes_edges_from_dir
from .model import Edge, Node


StateRegime = Literal["snapshot", "events"]


@dataclass(frozen=True)
class LoadedState:
    nodes: List[Node]
    edges: List[Edge]
    provenance: str


class StateProvider(Protocol):
    def load(self, data_dir: Path) -> LoadedState:
        ...


class SnapshotStateProvider:
    """
    Authoritative state comes directly from canonical nodes.json / edges.json.
    """

    def load(self, data_dir: Path) -> LoadedState:
        nodes, edges = load_nodes_edges_from_dir(data_dir)
        return LoadedState(
            nodes=nodes,
            edges=edges,
            provenance="snapshot:nodes.json+edges.json",
        )


class EventReplayStateProvider:
    """
    Authoritative state comes from replaying events.jsonl.
    """

    def load(self, data_dir: Path) -> LoadedState:
        from .events import load_and_replay_events

        materialized = load_and_replay_events(data_dir)
        return LoadedState(
            nodes=materialized.nodes,
            edges=materialized.edges,
            provenance="events:events.jsonl",
        )


def get_state_provider(regime: StateRegime) -> StateProvider:
    if regime == "snapshot":
        return SnapshotStateProvider()
    if regime == "events":
        return EventReplayStateProvider()
    raise ValueError(f"Unknown state regime: {regime!r}")


def load_state(data_dir: Path, regime: StateRegime = "snapshot") -> LoadedState:
    provider = get_state_provider(regime)
    return provider.load(data_dir)
