# cnl_lint.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .model import Kind, Node


@dataclass(frozen=True)
class CnlLintIssue:
    code: str
    severity: str  # "ERROR" | "WARN"
    node_id: str
    message: str


class CnlCodes:
    TEXT_TEMPLATE_MISMATCH = "L001"
    TEXT_TRAILING_WHITESPACE = "L002"
    TEXT_MISSING_PERIOD = "L003"
    TEXT_FORBIDDEN_CONJUNCTION = "L010"
    TEXT_TEMPORAL_CHAINING = "L011"
    TEXT_EMOTIVE_COMMENTARY = "L012"


# Canonical templates (strict)
# TASK:     "Do {action}."
# GOAL:     "Achieve {outcome}."
# QUESTION: "Determine {unknown}."
# ASSET:    "Have {resource}."
# BLOCKER:  "Blocked by {condition}."
_PATTERNS: Dict[Kind, re.Pattern[str]] = {
    Kind.TASK: re.compile(r"^Do\s+.+\.$"),
    Kind.GOAL: re.compile(r"^Achieve\s+.+\.$"),
    Kind.QUESTION: re.compile(r"^Determine\s+.+\.$"),
    Kind.ASSET: re.compile(r"^Have\s+.+\.$"),
    Kind.BLOCKER: re.compile(r"^Blocked by\s+.+\.$"),
}

# Global lexical bans (canonical text only)
# You can tune these later; treat as â€œguardrail lint,â€ not moral judgement.
_FORBIDDEN_CONJ = re.compile(r"\b(and|or)\b", re.IGNORECASE)
_TEMPORAL = re.compile(r"\b(after|before|when|once|then|until)\b", re.IGNORECASE)
_EMOTIVE = re.compile(r"\b(feel|feeling|ashamed|guilty|anxious|depressed|hopeless)\b", re.IGNORECASE)


def lint_cnl(nodes: List[Node]) -> List[CnlLintIssue]:
    """
    Controlled lint for canonical text.
    Deterministic ordering: by node id, then code.
    """
    issues: List[CnlLintIssue] = []

    for n in sorted(nodes, key=lambda x: x.id):
        txt = n.text

        # Trailing whitespace is a deterministic â€œdiff rotâ€ source
        if txt != txt.strip():
            issues.append(
                CnlLintIssue(
                    code=CnlCodes.TEXT_TRAILING_WHITESPACE,
                    severity="ERROR",
                    node_id=n.id,
                    message="Canonical text has leading/trailing whitespace.",
                )
            )

        # Enforce required final period, since patterns assume it
        if not txt.strip().endswith("."):
            issues.append(
                CnlLintIssue(
                    code=CnlCodes.TEXT_MISSING_PERIOD,
                    severity="ERROR",
                    node_id=n.id,
                    message="Canonical text must end with a period.",
                )
            )

        # Template match (strict)
        pat = _PATTERNS.get(n.kind)
        if pat and not pat.match(txt.strip()):
            issues.append(
                CnlLintIssue(
                    code=CnlCodes.TEXT_TEMPLATE_MISMATCH,
                    severity="ERROR",
                    node_id=n.id,
                    message=f"Canonical text does not match template for kind={n.kind.value}.",
                )
            )

        # Atomicity-ish bans on canonical text (you can soften to WARN later)
        if _FORBIDDEN_CONJ.search(txt):
            issues.append(
                CnlLintIssue(
                    code=CnlCodes.TEXT_FORBIDDEN_CONJUNCTION,
                    severity="ERROR",
                    node_id=n.id,
                    message="Canonical text contains forbidden conjunction (and/or). Use auto-split and edges instead.",
                )
            )

        if _TEMPORAL.search(txt):
            issues.append(
                CnlLintIssue(
                    code=CnlCodes.TEXT_TEMPORAL_CHAINING,
                    severity="ERROR",
                    node_id=n.id,
                    message="Canonical text contains temporal chaining. Represent ordering via requires_task or blocked_by edges.",
                )
            )

        if _EMOTIVE.search(txt):
            issues.append(
                CnlLintIssue(
                    code=CnlCodes.TEXT_EMOTIVE_COMMENTARY,
                    severity="WARN",
                    node_id=n.id,
                    message="Canonical text appears to contain affective commentary. Keep canonical text operational; store affect elsewhere if needed.",
                )
            )

    # Deterministic final ordering
    issues.sort(key=lambda i: (i.node_id, i.code))
    return issues

