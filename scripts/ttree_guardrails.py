#!/usr/bin/env python3
"""
Transition Tree — Day 1 setup (SQLite + LLM-assisted decomposition + deterministic linting)

Core guarantees:
- Canonical store is SQLite.
- Model only proposes candidates in strict JSON Schema.
- Deterministic linter gates acceptance (affect-free, non-blended, domain-consistent-ish).
- Optional repair loop for invalid children.
- Renderer outputs Tractatus-like numbering.

Usage:
  python ttree.py init --db tree.db
  python ttree.py add --db tree.db --parent "ROOT" --domain 1 --type prerequisite --text "Requires ... "
  python ttree.py expand --db tree.db --node <NODE_ID> --model "gpt-4.1-mini"
  python ttree.py render --db tree.db --out render.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ---- Cost estimation (USD per 1M tokens). Override via env if you want.
DEFAULT_PRICE_PER_1M_INPUT = float(os.getenv("OPENAI_PRICE_INPUT_PER_1M", "0.80"))
DEFAULT_PRICE_PER_1M_OUTPUT = float(os.getenv("OPENAI_PRICE_OUTPUT_PER_1M", "3.20"))


# ----------------------------
# Domain roots (fixed)
# ----------------------------

DOMAINS = [
    (1, "Social transition (name, pronouns, presentation)"),
    (2, "Mental health and support infrastructure"),
    (3, "Medical transition (HRT)"),
    (4, "Voice and communication"),
    (5, "Legal transition"),
    (6, "Surgical options"),
    (7, "Hair, skin, and ancillary care"),
    (8, "Social, occupational, and safety planning"),
    (9, "Long-term maintenance and integration"),
]

# ----------------------------
# Domain-specific guardrails (prompt-time only)
# ----------------------------
# These are *prompt guardrails*, not deterministic lint rules.
# Keep them lightweight and keyed by domain_id so they can be extended safely.
import re
from typing import Dict, List

# Deterministic domain-drift denylist (hard exclusions)
DOMAIN_DENYLIST: Dict[int, List[str]] = {
    9: [
        "workout",
        "training",
        "fitness",
        "injury",
        "wearable",
        "physiological",
        "intensity",
        "duration",
        "recovery",
        "baseline",
        "heart rate",
        "metrics",
    ],
    6: [
        # Domain 9 contaminants
        "budget", "cost", "costs", "price", "afford", "affordability", "save", "saving",
        "insurance", "coverage", "funding",

        # sequencing / roadmap language
        "timeline", "schedule", "sequencing", "sequence", "step", "steps", "next", "then", "first", "second",
        "roadmap", "plan", "planning",

        # desire / affect-adjacent outcome framing (non-affect but still disallowed per your spec)
        "want", "wish", "hope",
    ],
}


DOMAIN_GUARDRAILS: Dict[int, Dict[str, Any]] = {

    9: {
        "definition": (
            "sustainability, sequencing, emotional/financial load, risk management, "
            "disclosure cadence, recovery time, appointment cadence"
        ),
        "allowed_themes": [
            "sustainability",
            "sequencing",
            "capacity",
            "burnout",
            "budget",
            "appointments",
            "social disclosure",
            "maintenance routines",
            "documentation",
            "risk",
            "integration",
        ],
        "banned_themes": [
            "workout",
            "training",
            "fitness",
            "injury",
            "injury prevention",
            "baseline physical condition",
            "wearable",
            "wearable tech",
            "physiological",
            "physiological metrics",
            "recovery metrics",
            "intensity",
            "duration",
        ],
    },

    6: {
        "definition": (
            "Domain 6.1 is a requirements registry for surgical candidacy: eligibility, "
            "medical prerequisites, risk classifications, provider constraints, "
            "regulatory and documentation requirements, contraindications, "
            "and recovery dependencies as prerequisites (not plans)."
        ),
        "allowed_themes": [
            "eligibility conditions",
            "medical prerequisites",
            "risk classification",
            "provider criteria",
            "regulatory requirements",
            "documentation requirements",
            "contraindications",
            "preoperative testing",
            "postoperative discharge prerequisites",
        ],
        "banned_themes": [
            "budget", "cost", "affordability", "insurance", "coverage",
            "timeline", "schedule", "sequencing", "steps", "roadmap", "planning",
            "desire", "wanting", "hoping",
            "speculative outcomes",
        ],
    }

}



def domain_guardrails_block(domain_id: int) -> str:
    g = DOMAIN_GUARDRAILS.get(domain_id)
    if not g:
        return ""
    allowed = ", ".join(f"“{t}”" for t in g.get("allowed_themes", []))
    banned = ", ".join(f"“{t}”" for t in g.get("banned_themes", []))
    definition = g.get("definition", "")

    block = (
        "\nDOMAIN GUARDRAILS (hard):\n"
        f"- Domain definition: {definition}\n"
        f"- Positive anchors (allowed themes): {allowed}\n"
        f"- Hard exclusions (banned themes): {banned}\n"
        "- If you cannot propose children without using banned themes, return the minimum number of children.\n"
    )
    return block


NODE_TYPES = ("prerequisite", "capability", "resource", "decision", "maintenance", "constraint")
STATUSES = ("active", "deferred", "blocked", "complete")
BLOCKER_KINDS = ("money", "access", "energy", "safety", "time", "knowledge", "logistics")

# Affect is tracked outside the tree: we treat these as hard errors in atomic nodes.
AFFECT_WORDS = {
    "sad", "ashamed", "anxious", "scared", "afraid", "hopeless", "depressed",
    "dysphoric", "angry", "guilty", "embarrassed", "overwhelmed", "panicked",
    "lonely", "despair", "miserable", "worthless"
}

# Cue patterns for blend detection + gentle type sanity checks (deterministic, heuristic)
TYPE_CUES = {
    "prerequisite": [r"\brequires?\b", r"\bmust have\b", r"\bdepends on\b", r"\bnecessary\b", r"\bneed(s)? to have\b"],
    "capability":   [r"\b(i can|can do)\b", r"\bable to\b", r"\bcapable of\b", r"\bknow how\b"],
    "resource":     [r"\bcosts?\b", r"\bbudget\b", r"\bmoney\b", r"\btime\b", r"\baccess\b", r"\bappointment\b", r"\btransport\b", r"\binsurance\b"],
    "decision":     [r"\b(i have decided|i decide)\b", r"\bi choose\b", r"\bi'm choosing\b", r"\bi will\b"],
    "maintenance":  [r"\bdaily\b", r"\bweekly\b", r"\bmonthly\b", r"\bongoing\b", r"\broutine\b", r"\bmaintain\b", r"\bevery (day|week|month)\b"],
    "constraint":   [r"\bblocked\b", r"\b(can't|cannot)\b", r"\bunavailable\b", r"\bwaitlist\b", r"\bno coverage\b", r"\bnot possible\b"],
}

CONJUNCTION_RE = re.compile(r"\b(and|but|however|though)\b", re.I)

# ----------------------------
# JSON Schema for Structured Outputs
# ----------------------------

JSON_SCHEMA = {
    "name": "transition_tree_children_proposal",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "parent_id": {"type": "string"},
            "children": {
                "type": "array",
                "minItems": 4,
                "maxItems": 14,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {"type": "string", "enum": list(NODE_TYPES)},
                        "text": {"type": "string", "minLength": 6, "maxLength": 200},
                        "status": {"type": "string", "enum": list(STATUSES)},
                        "blocker_kind": {"type": ["string", "null"], "enum": list(BLOCKER_KINDS) + [None]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "notes": {"type": ["string", "null"], "maxLength": 160},
                    },
                    "required": ["type", "text", "status", "blocker_kind", "confidence", "notes"],
                },
            },
            "self_audit": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "affect_detected": {"type": "boolean"},
                    "blends_detected": {"type": "boolean"},
                    "domain_drift_detected": {"type": "boolean"},
                    "audit_notes": {"type": "string", "maxLength": 240},
                },
                "required": ["affect_detected", "blends_detected", "domain_drift_detected", "audit_notes"],
            },
        },
        "required": ["parent_id", "children", "self_audit"],
    },
}

# ----------------------------
# Linting
# ----------------------------

@dataclass
class LintIssue:
    severity: str  # "error" | "warning"
    code: str
    message: str

def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z']+", text.lower())

def contains_affect(text: str) -> Optional[str]:
    for t in tokenize(text):
        if t in AFFECT_WORDS:
            return t
    return None

def cue_hits(text: str) -> List[str]:
    hits: List[str] = []
    for typ, patterns in TYPE_CUES.items():
        for pat in patterns:
            if re.search(pat, text, flags=re.I):
                hits.append(typ)
                break
    return hits

def normalize_text(node_type: str, text: str) -> str:
    t = text.strip()
    # Gentle canonicalization so later editing is consistent
    if node_type == "prerequisite" and not re.match(r"^(Requires|Must have)\b", t, re.I):
        t = "Requires " + t[0].lower() + t[1:] if t else t
    if node_type == "constraint" and not re.match(r"^(Blocked by|Unavailable because)\b", t, re.I):
        # If the author already wrote "can't/cannot", rewrite to a constraint stem
        if re.search(r"\b(can't|cannot)\b", t, re.I):
            t = re.sub(r"\b(can't|cannot)\b", "Blocked by", t, flags=re.I)
        else:
            t = "Blocked by " + t[0].lower() + t[1:] if t else t
    if node_type == "decision" and not re.match(r"^I have decided\b", t, re.I):
        t = "I have decided " + t[0].lower() + t[1:] if t else t
    if node_type == "maintenance" and not re.search(r"\b(daily|weekly|monthly|ongoing|every)\b", t, re.I):
        t = t + " (ongoing)"
    return t

def lint_domain_drift(text: str, domain_id: int) -> List["LintIssue"]:
    """
    Deterministic domain-drift check.
    Any denylisted token for the given domain is a hard error.
    """
    issues: List[LintIssue] = []

    denylist = DOMAIN_DENYLIST.get(domain_id)
    if not denylist:
        return issues

    lowered = text.lower()

    for token in denylist:
        pattern = r"\b" + re.escape(token) + r"\b"
        if re.search(pattern, lowered):
            issues.append(
                LintIssue(
                    level="error",
                    code="domain_drift",
                    message=(
                        f"Domain {domain_id} denylisted token detected: '{token}'. "
                        "This content belongs to a prohibited adjacent domain."
                    ),
                )
            )

    return issues


def lint_child(child: Dict[str, Any], domain_id: int) -> List[LintIssue]:
    issues: List[LintIssue] = []

    # Aggregate all free text fields for deterministic scanning
    text_blob = " ".join(
        str(child.get(k, "")) for k in ("text", "notes")
    )

    issues.extend(lint_domain_drift(text_blob, domain_id))

    return issues


# ----------------------------
# SQLite
# ----------------------------

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS api_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  event TEXT NOT NULL,            -- "propose" | "repair"
  node_id TEXT NOT NULL,
  domain_id INTEGER NOT NULL,
  model TEXT NOT NULL,
  input_tokens INTEGER,
  output_tokens INTEGER,
  total_tokens INTEGER,
  estimated_cost_usd REAL,
  note TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_usage_created ON api_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_api_usage_node ON api_usage(node_id);


CREATE TABLE IF NOT EXISTS domains (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  domain_id INTEGER NOT NULL,
  parent_id TEXT NULL,
  type TEXT NOT NULL CHECK (type IN ('prerequisite','capability','resource','decision','maintenance','constraint')),
  text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','deferred','blocked','complete')),
  blocker_kind TEXT NULL CHECK (blocker_kind IN ('money','access','energy','safety','time','knowledge','logistics')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE,
  FOREIGN KEY(parent_id) REFERENCES nodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_domain ON nodes(domain_id);
"""

def now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str) -> None:
    conn = connect(db_path)
    with conn:
        conn.executescript(SCHEMA_SQL)
        conn.executemany("INSERT OR IGNORE INTO domains(id, name) VALUES(?,?)", DOMAINS)

        # Create root nodes for each domain (parent_id NULL)
        for domain_id, domain_name in DOMAINS:
            # deterministic root id for convenience
            root_id = f"ROOT-{domain_id}"
            conn.execute("""
                INSERT OR IGNORE INTO nodes(id, domain_id, parent_id, type, text, status, blocker_kind, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?, ?, ?)
            """, (root_id, domain_id, None, "decision", f"I have decided to work within domain: {domain_name}",
                  "active", None, now_iso(), now_iso()))
    conn.close()

def add_node(db_path: str, domain_id: int, parent_id: str, node_type: str, text: str,
             status: str, blocker_kind: Optional[str]) -> str:
    if parent_id == "ROOT":
        parent_id = f"ROOT-{domain_id}"

    node_id = str(uuid.uuid4())
    created = now_iso()

    # Normalize early to keep canonical style consistent
    text_norm = normalize_text(node_type, text)

    conn = connect(db_path)
    with conn:
        conn.execute("""
            INSERT INTO nodes(id, domain_id, parent_id, type, text, status, blocker_kind, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?, ?, ?)
        """, (node_id, domain_id, parent_id, node_type, text_norm, status, blocker_kind, created, created))
    conn.close()
    return node_id

def get_node(conn: sqlite3.Connection, node_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
    if not row:
        raise ValueError(f"Node not found: {node_id}")
    return row

def children_of(conn: sqlite3.Connection, node_id: str) -> List[sqlite3.Row]:
    return conn.execute("SELECT * FROM nodes WHERE parent_id = ? ORDER BY created_at ASC", (node_id,)).fetchall()
    
def _extract_usage(resp: Any) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Best-effort extraction across SDK versions.
    Returns (input_tokens, output_tokens, total_tokens).
    """
    u = getattr(resp, "usage", None)
    if not u:
        return None, None, None

    # Newer SDKs often expose attributes; sometimes it's a dict-like.
    def get(name: str) -> Optional[int]:
        if hasattr(u, name):
            return getattr(u, name)
        if isinstance(u, dict):
            return u.get(name)
        return None

    inp = get("input_tokens")
    out = get("output_tokens")
    tot = get("total_tokens")
    if tot is None and (inp is not None or out is not None):
        tot = (inp or 0) + (out or 0)
    return inp, out, tot

def _estimate_cost_usd(input_tokens: Optional[int], output_tokens: Optional[int]) -> Optional[float]:
    if input_tokens is None and output_tokens is None:
        return None
    inp = input_tokens or 0
    out = output_tokens or 0
    return (inp * DEFAULT_PRICE_PER_1M_INPUT + out * DEFAULT_PRICE_PER_1M_OUTPUT) / 1_000_000.0

def log_api_usage(
    conn: sqlite3.Connection,
    event: str,
    node_id: str,
    domain_id: int,
    model: str,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    total_tokens: Optional[int],
    estimated_cost_usd: Optional[float],
    note: Optional[str] = None
) -> None:
    conn.execute("""
        INSERT INTO api_usage(
            created_at,event,node_id,domain_id,model,
            input_tokens,output_tokens,total_tokens,
            estimated_cost_usd,note
        )
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        now_iso(), event, node_id, domain_id, model,
        input_tokens, output_tokens, total_tokens,
        estimated_cost_usd, note
    ))


# ----------------------------
# OpenAI call (Structured Outputs)
# ----------------------------

def openai_propose_children(db_path: str, parent: sqlite3.Row, domain_name: str, model: str) -> Dict[str, Any]:
    """
    Uses OpenAI Responses API with Structured Outputs (json_schema).
    Docs: Responses endpoint + json_schema via text.format. :contentReference[oaicite:1]{index=1}
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("Missing dependency. Run: pip install openai")

    client = OpenAI()

    parent_id = parent["id"]
    parent_type = parent["type"]
    parent_text = parent["text"]

    domain_id = int(parent["domain_id"])
    guard_block = domain_guardrails_block(domain_id)

    prompt = (
        "You are proposing CHILD NODES ONLY for a dependency tree.\n"
        "Rules (hard):\n"
        "- Each child must be atomic and must be exactly one of: prerequisite, capability, resource, decision, maintenance, constraint.\n"
        "- No affect terms or emotional content inside node text.\n"
        "- Children must be 'conditions for parent' (what must be true for the parent to hold), not general advice.\n"
        "- Stay within the same functional domain.\n"
        "- If status is 'blocked', set blocker_kind to one of: money/access/energy/safety/time/knowledge/logistics.\n"
        "- Keep node text under 200 chars, clear and rewriteable into canonical grammar.\n\n"
        f"PARENT_ID: {parent_id}\n"
        f"DOMAIN: {domain_name}\n"
        f"PARENT_TYPE: {parent_type}\n"
        f"PARENT_TEXT: {parent_text}\n"
    )

    if guard_block:
        prompt = prompt + guard_block

    # Responses API: text.format type json_schema with schema
    resp = client.responses.create(
        model=model,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": JSON_SCHEMA["name"],     # e.g., "transition_tree_children_proposal"
                "strict": True,
                "schema": JSON_SCHEMA["schema"],
                }
            }
        # If you prefer: set store=False to reduce retention; see docs. :contentReference[oaicite:2]{index=2}
        # store=False,
    )
    # SDK convenience: aggregated output text
    data = json.loads(resp.output_text)

    inp, out, tot = _extract_usage(resp)
    cost = _estimate_cost_usd(inp, out)

    conn = connect(db_path)
    with conn:
        log_api_usage(
            conn=conn,
            event="propose",
            node_id=parent["id"],
            domain_id=parent["domain_id"],
            model=model,
            input_tokens=inp,
            output_tokens=out,
            total_tokens=tot,
            estimated_cost_usd=cost,
            note=None
        )
    conn.close()

    return data

def openai_repair_children(bad_indices: Dict[int, List[str]],
                           proposal: Dict[str, Any],
                           domain_id: int,
                           domain_name: str,
                           model: str) -> Dict[str, Any]:
    """
    Ask the model to rewrite only the invalid children indices, keeping others identical.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("Missing dependency. Run: pip install openai")

    client = OpenAI()

    guard_block = domain_guardrails_block(domain_id)

    failure_report = {str(i): errs for i, errs in bad_indices.items()}
    prompt = (
        "Repair the JSON by rewriting ONLY the children at the specified indices.\n"
        "Do NOT change any other child objects.\n"
        "Rules (hard): six node types only; no affect; atomic; domain-consistent; blocked => blocker_kind set.\n"
        f"DOMAIN: {domain_name}\n"
        f"FAILURES: {json.dumps(failure_report)}\n"
    )

    if guard_block:
        prompt = prompt + guard_block

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "user", "content": prompt},
            {"role": "user", "content": json.dumps(proposal)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": JSON_SCHEMA["name"],
                "strict": True,
                "schema": JSON_SCHEMA["schema"],
            },
        },
    )
    return json.loads(resp.output_text)

# ----------------------------
# Expand workflow
# ----------------------------

def expand_node(db_path: str, node_id: str, model: str, max_repairs: int = 2) -> None:
    conn = connect(db_path)

    with conn:
        parent = get_node(conn, node_id)
        domain_id = int(parent["domain_id"])
        domain_name = conn.execute(
            "SELECT name FROM domains WHERE id = ?",
            (domain_id,)
        ).fetchone()["name"]

        proposal = openai_propose_children(db_path, parent, domain_name, model=model)

        # --- deterministic lint ---
        def lint_proposal(p: Dict[str, Any]) -> Tuple[Dict[int, List[str]], List[Dict[str, Any]]]:
            bad: Dict[int, List[str]] = {}
            normalized_children: List[Dict[str, Any]] = []

            for i, child in enumerate(p["children"]):
                issues = lint_child(child, domain_id)

                child2 = dict(child)
                child2["text"] = normalize_text(child2["type"], child2["text"])
                normalized_children.append(child2)

                hard = [iss for iss in issues if iss.severity == "error"]
                if hard:
                    bad[i] = [f"{iss.code}:{iss.message}" for iss in hard]

            return bad, normalized_children

        bad, normalized = lint_proposal(proposal)
        proposal["children"] = normalized

        repairs = 0
        while bad and repairs < max_repairs:
            proposal = openai_repair_children(
                bad,
                proposal,
                domain_id,
                domain_name,
                model=model
            )
            bad, normalized = lint_proposal(proposal)
            proposal["children"] = normalized
            repairs += 1

        if bad:
            print("Lint failed after repairs. Nothing inserted.")
            print(json.dumps(bad, indent=2))
            return

        # --- insertion ---
        created = now_iso()
        for child in proposal["children"]:
            child_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO nodes(
                    id, domain_id, parent_id,
                    type, text, status, blocker_kind,
                    created_at, updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                child_id,
                domain_id,
                parent["id"],
                child["type"],
                child["text"],
                child["status"],
                child["blocker_kind"],
                created,
                created
            ))

        print(f"Inserted {len(proposal['children'])} children under node {node_id}.")

    conn.close()


# ----------------------------
# Rendering (Tractatus-like numbering)
# ----------------------------

def render_markdown(db_path: str, out_path: str) -> None:
    conn = connect(db_path)
    with conn:
        rows = conn.execute("SELECT * FROM nodes ORDER BY domain_id ASC, created_at ASC").fetchall()
        # Build adjacency
        children_map: Dict[Optional[str], List[sqlite3.Row]] = {}
        node_map: Dict[str, sqlite3.Row] = {}
        for r in rows:
            node_map[r["id"]] = r
            children_map.setdefault(r["parent_id"], []).append(r)

        # Stable ordering: created_at already, but ensure deterministic within same timestamp
        for k in children_map:
            children_map[k].sort(key=lambda x: (x["created_at"], x["id"]))

        lines: List[str] = []
        for domain_id, domain_name in DOMAINS:
            lines.append(f"# {domain_id}. {domain_name}")
            root_id = f"ROOT-{domain_id}"

            def walk(nid: str, prefix: str) -> None:
                kids = children_map.get(nid, [])
                for idx, child in enumerate(kids, start=1):
                    this_num = f"{prefix}.{idx}" if prefix else str(idx)
                    status = child["status"]
                    blocker = child["blocker_kind"]
                    meta = f"[{status}" + (f":{blocker}" if blocker else "") + "]"
                    lines.append(f"{this_num} {meta} ({child['type']}) {child['text']}")
                    walk(child["id"], this_num)

            # We do not print the ROOT node itself (it’s just a container/anchor)
            walk(root_id, str(domain_id))

            lines.append("")  # spacing

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    conn.close()
    print(f"Wrote {out_path}")

# ----------------------------
# CLI
# ----------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_init = sub.add_parser("init")
    ap_init.add_argument("--db", required=True)

    ap_add = sub.add_parser("add")
    ap_add.add_argument("--db", required=True)
    ap_add.add_argument("--domain", type=int, choices=[d[0] for d in DOMAINS], required=True)
    ap_add.add_argument("--parent", required=True, help='Parent node id, or "ROOT" to attach under the domain root.')
    ap_add.add_argument("--type", choices=NODE_TYPES, required=True)
    ap_add.add_argument("--text", required=True)
    ap_add.add_argument("--status", choices=STATUSES, default="active")
    ap_add.add_argument("--blocker", choices=BLOCKER_KINDS, default=None)

    ap_expand = sub.add_parser("expand")
    ap_expand.add_argument("--db", required=True)
    ap_expand.add_argument("--node", required=True)
    ap_expand.add_argument("--model", default="gpt-4.1-mini")
    ap_expand.add_argument("--max-repairs", type=int, default=2)

    ap_render = sub.add_parser("render")
    ap_render.add_argument("--db", required=True)
    ap_render.add_argument("--out", required=True)

    args = ap.parse_args()

    if args.cmd == "init":
        init_db(args.db)
        print(f"Initialized {args.db} with domain roots.")
        return

    if args.cmd == "add":
        node_id = add_node(
            db_path=args.db,
            domain_id=args.domain,
            parent_id=args.parent,
            node_type=args.type,
            text=args.text,
            status=args.status,
            blocker_kind=args.blocker
        )
        print(node_id)
        return

    if args.cmd == "expand":
        expand_node(args.db, args.node, model=args.model, max_repairs=args.max_repairs)
        return

    if args.cmd == "render":
        render_markdown(args.db, args.out)
        return

if __name__ == "__main__":
    main()
