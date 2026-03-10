from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .events import (
    KNOWLEDGE_SCAFFOLD_CONFIRMED,
    load_knowledge_events,
    scaffold_from_payload,
)
from .model import Scaffold


@dataclass(frozen=True)
class KnowledgeRegistry:
    scaffolds_by_id: dict[str, Scaffold]
    scaffolds_by_domain: dict[str, tuple[Scaffold, ...]]

    def scaffolds_for_domain(self, domain: str | None) -> tuple[Scaffold, ...]:
        if domain is None:
            return ()
        return self.scaffolds_by_domain.get(domain, ())


def registry_from_scaffolds(scaffolds: list[Scaffold]) -> KnowledgeRegistry:
    scaffolds_by_id = {s.scaffold_id: s for s in sorted(scaffolds, key=lambda x: x.scaffold_id)}
    domains: dict[str, list[Scaffold]] = {}
    for s in sorted(scaffolds, key=lambda x: (x.domain, x.priority, x.scaffold_id)):
        domains.setdefault(s.domain, []).append(s)
    scaffolds_by_domain = {
        domain: tuple(items)
        for domain, items in sorted(domains.items(), key=lambda kv: kv[0])
    }
    return KnowledgeRegistry(
        scaffolds_by_id=scaffolds_by_id,
        scaffolds_by_domain=scaffolds_by_domain,
    )


def load_knowledge_registry(data_dir: Path) -> KnowledgeRegistry:
    events = load_knowledge_events(data_dir)
    scaffolds: dict[str, Scaffold] = {}

    for ev in events:
        if ev.type == KNOWLEDGE_SCAFFOLD_CONFIRMED:
            scaffold = scaffold_from_payload(ev.payload)
            scaffolds[scaffold.scaffold_id] = scaffold
            continue
        raise ValueError(f"Unknown knowledge event type: {ev.type!r}")

    return registry_from_scaffolds(list(scaffolds.values()))
