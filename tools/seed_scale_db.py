"""Seed a disposable PostgreSQL database for multi-replica scale regression.

Reference/scoring data remains JSON-backed in the application. This helper only
copies the minimal major metadata required by operational result persistence into
the benchmark database. It is never used by production deployment.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from sqlalchemy import delete

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import engine
# Register every ORM table in the shared Base metadata before create_all(),
# including the users table referenced by UserSession.
import billing_models  # noqa: F401,E402
import feedback_models  # noqa: F401,E402
from models import Base, Major

def load_majors() -> list[dict]:
    with (ROOT / "majors_database_v2.json").open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise RuntimeError("majors_database_v2.json must contain a list")
    return data


def main() -> None:
    if engine is None:
        raise RuntimeError("DATABASE_URL must be configured")

    Base.metadata.create_all(bind=engine)
    majors = load_majors()
    with engine.begin() as conn:
        conn.execute(delete(Major))

    rows = []
    for item in majors:
        rows.append(
            Major(
                id=int(item["id"]),
                name=str(item["name"]),
                group=str(item["group"]),
                cluster=item.get("cluster"),
                subgroup=item.get("subgroup"),
                exam_group=item.get("exam_group"),
                high_school_branch=item.get("high_school_branch"),
                strategy_weights=item.get("strategy_weights", []),
                value_weights=item.get("value_weights", []),
                archetype=item.get("archetype"),
                fulfillment_source=item.get("fulfillment_source"),
                prestige_level=item.get("prestige_level"),
                handcrafted=bool(item.get("handcrafted", True)),
                motive_driven=bool(item.get("motive_driven", True)),
                weights_version=item.get("weights_version"),
            )
        )

    with engine.begin() as conn:
        conn.execute(
            Major.__table__.insert(),
            [
                {
                    "id": row.id,
                    "name": row.name,
                    "group": row.group,
                    "cluster": row.cluster,
                    "subgroup": row.subgroup,
                    "exam_group": row.exam_group,
                    "high_school_branch": row.high_school_branch,
                    "strategy_weights": row.strategy_weights,
                    "value_weights": row.value_weights,
                    "archetype": row.archetype,
                    "fulfillment_source": row.fulfillment_source,
                    "prestige_level": row.prestige_level,
                    "handcrafted": row.handcrafted,
                    "motive_driven": row.motive_driven,
                    "weights_version": row.weights_version,
                }
                for row in rows
            ],
        )

    print(f"Seeded {len(rows)} majors into benchmark PostgreSQL")


if __name__ == "__main__":
    main()
