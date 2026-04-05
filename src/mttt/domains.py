from __future__ import annotations

from typing import Iterable


VALID_PLANNING_DOMAINS: frozenset[str] = frozenset(
    {
        "care",
        "voice",
        "integration",
        "administrative",
        "legal",
        "logistics",
        "medical",
        "social",
    }
)


def normalize_domain(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("domain must be a string")
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        raise ValueError("domain must be a non-empty string")
    return normalized


def validate_domain(
    value: str,
    *,
    allowed: Iterable[str] | None = None,
    field_name: str = "domain",
) -> str:
    normalized = normalize_domain(value)
    allowed_set = frozenset(
        normalize_domain(x) for x in (allowed if allowed is not None else VALID_PLANNING_DOMAINS)
    )

    if normalized not in allowed_set:
        allowed_str = ", ".join(sorted(allowed_set))
        raise ValueError(f"invalid {field_name} {value!r}; expected one of: {allowed_str}")

    return normalized
