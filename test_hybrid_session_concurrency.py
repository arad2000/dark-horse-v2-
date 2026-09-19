from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import select

from billing_models import User
from database import SessionLocal, engine
from main_v2 import _persist_discovery_session
from models import UserSession


def request_stub() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v2/darkhorse/discover",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "query_string": b"",
        }
    )


class JourneySessionConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if SessionLocal is None or engine is None or engine.dialect.name != "postgresql":
            raise unittest.SkipTest("PostgreSQL DATABASE_URL is required")

        with SessionLocal() as db:
            user = User(
                public_id=str(uuid4()),
                name="Concurrent Journey Session Test",
                phone="09" + str(uuid4().int % 1_000_000_000).zfill(9),
                password_hash=None,
                role="user",
                status="active",
            )
            db.add(user)
            db.commit()
            cls.user_id = user.id


    def test_unowned_session_cannot_be_claimed_by_two_users(self) -> None:
        with SessionLocal() as db:
            second_user = User(
                public_id=str(uuid4()),
                name="Second Session Owner Test",
                phone="09" + str(uuid4().int % 1_000_000_000).zfill(9),
                password_hash=None,
                role="user",
                status="active",
            )
            session_uuid = str(uuid4())
            db.add(second_user)
            db.add(
                UserSession(
                    user_id=None,
                    session_uuid=session_uuid,
                    micro_motives=[],
                    sjt_answers={},
                    conjoint_choices={},
                )
            )
            db.commit()
            second_user_id = second_user.id

        def claim(user_id: int) -> tuple[str, int | None, int | None]:
            try:
                value = _persist_discovery_session(
                    request_stub(),
                    type(
                        "Payload",
                        (),
                        {
                            "micro_motives": [],
                            "sjt_answers": {},
                            "conjoint_choices": {},
                            "session_id": session_uuid,
                        },
                    )(),
                    user_id=user_id,
                )
                return value[0], value[1], None
            except HTTPException as exc:
                return "", None, exc.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, [self.user_id, second_user_id]))

        successful = [row for row in results if row[2] is None]
        rejected = [row for row in results if row[2] == 403]
        self.assertEqual(len(successful), 1)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(successful[0][0], session_uuid)

        with SessionLocal() as db:
            row = db.scalar(
                select(UserSession).where(UserSession.session_uuid == session_uuid)
            )
            self.assertIsNotNone(row)
            self.assertIn(row.user_id, {self.user_id, second_user_id})


    def test_same_authenticated_journey_uuid_resolves_to_one_session(self) -> None:
        session_uuid = str(uuid4())

        def create_once() -> tuple[str, int | None]:
            request = request_stub()
            return _persist_discovery_session(
                request,
                type(
                    "Payload",
                    (),
                    {
                        "micro_motives": [],
                        "sjt_answers": {},
                        "conjoint_choices": {},
                        "session_id": session_uuid,
                    },
                )(),
                user_id=self.user_id,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(lambda _: create_once(), range(2)))

        self.assertEqual({uuid for uuid, _ in rows}, {session_uuid})
        self.assertEqual(rows[0][1], rows[1][1])

        with SessionLocal() as db:
            sessions = list(
                db.scalars(
                    select(UserSession).where(UserSession.session_uuid == session_uuid)
                )
            )
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].user_id, self.user_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
