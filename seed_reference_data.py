"""Deterministic JSON -> PostgreSQL seed utility for Dark Horse V2 Hybrid.

Safety contract:
- Reference JSON files remain the source of truth.
- The command only writes when --confirm-staging is supplied.
- It never enables production PostgreSQL runtime use.
- It preserves natural keys and many-to-many mappings from the JSON sources.
- Alembic owns schema lifecycle; this script does not create/drop schema.
- BIOTM-* motive references are intentionally deferred; non-BIOTM unresolved
  references remain hard failures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import billing_models  # noqa: F401  # register User/auth tables on shared Base metadata
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import engine
from models import (
    Major,
    MicroMotive,
    SchoolBranch,
    TraitOption,
    ValuePole,
    branch_micro_motives,
    major_micro_motives,
)

ROOT = Path(__file__).resolve().parent