from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

ContextCategory = Literal["current_state", "constraint", "priority"]
ContextStatus = Literal["active", "superseded"]
ContextValue = str | int | float | bool

ALLOWED_CURRENT_STATE_KEYS = frozenset({
    "hrt_active",
    "estradiol_mg_per_day",
    "has_provider",
    "legal_name_change_done",
    "gender_marker_change_done",
    "social_transition_stage",
})

ALLOWED_CONSTRAINT_KEYS = frozenset({
    "low_income",
    "no_insurance",
    "privacy_sensitive",
    "geographically_limited",
    "low_energy_capacity",
    "time_budget_hours_per_week",
})

ALLOWED_PRIORITY_KEYS = frozenset({
    "prioritize_hrt_access",
    "prioritize_voice",
    "prioritize_legal_change",
    "minimize_cost",
    "avoid_visibility",
})

_ALLOWED_KEYS_BY_CATEGORY = {
    "current_state": ALLOWED_CURRENT_STATE_KEYS,
    "constraint": ALLOWED_CONSTRAINT_KEYS,
    "priority": ALLOWED_PRIORITY_KEYS,
}


def validate_context_key(category: ContextCategory, key: str) -> None:
    allowed = _ALLOWED_KEYS_BY_CATEGORY[category]
    if key not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"invalid context key {key!r} for category {category!r}; "
            f"expected one of: {allowed_str}"
        )


@dataclass(frozen=True)
class ContextItem:
    item_id: str
    category: ContextCategory
    key: str
    value: ContextValue
    status: ContextStatus = "active"
    jurisdiction: Optional[str] = None
    confidence: Optional[Literal["self_reported", "confirmed"]] = None
    source: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        validate_context_key(self.category, self.key)


@dataclass(frozen=True)
class ReplayedContext:
    current_state: dict[str, ContextItem]
    constraints: dict[str, ContextItem]
    priorities: dict[str, ContextItem]

    def get(self, category: ContextCategory, key: str) -> Optional[ContextItem]:
        if category == "current_state":
            return self.current_state.get(key)
        if category == "constraint":
            return self.constraints.get(key)
        return self.priorities.get(key)