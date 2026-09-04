"""Staged authentication service for Dark Horse V2.

Authentication is operational-only and does not participate in scoring.
Passwords are hashed with PBKDF2-HMAC-SHA256; bearer tokens are never stored
raw, only as SHA-256 hashes in the database.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from billing_models import AuthSession, User

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
TOKEN_BYTES = 32
DEFAULT_SESSION_DAYS = 30
IRAN_MOBILE_RE = re.compile(r"^09\d{9}$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_phone(phone: str) -> str:
    value = "".join((phone or "").split())
    if not value:
        raise ValueError("phone is required")
    translation = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "0123456789" + "0123456789",
    )
    value = value.translate(translation)
    if not IRAN_MOBILE_RE.fullmatch(value):
        raise ValueError("phone must be a valid Iranian mobile number")
    return value


def hash_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("password must contain at least 8 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "$".join(
        [
            PASSWORD_ALGORITHM,
            str(PASSWORD_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_s, salt_b64, digest_b64 = encoded.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_s)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session(db: Session, user: User, days: int = DEFAULT_SESSION_DAYS) -> tuple[str, AuthSession]:
    if days <= 0:
        raise ValueError("session lifetime must be positive")
    raw_token = secrets.token_urlsafe(TOKEN_BYTES)
    session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utcnow() + timedelta(days=days),
    )
    db.add(session)
    db.flush()
    return raw_token, session


def register_user(db: Session, *, name: str, phone: str, password: str) -> tuple[User, str]:
    phone = normalize_phone(phone)
    if db.scalar(select(User).where(User.phone == phone)) is not None:
        raise ValueError("phone already registered")
    user = User(public_id=str(uuid4()), name=name.strip(), phone=phone, password_hash=hash_password(password))
    if not user.name:
        raise ValueError("name is required")
    db.add(user)
    db.flush()
    token, _ = issue_session(db, user)
    return user, token


def create_verified_user(db: Session, *, name: str, phone: str, password_hash: str) -> tuple[User, str]:
    """Create an already-verified user from a persisted password hash."""
    phone = normalize_phone(phone)
    if db.scalar(select(User).where(User.phone == phone)) is not None:
        raise ValueError("phone already registered")
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("name is required")
    if not password_hash:
        raise ValueError("password hash is required")
    user = User(public_id=str(uuid4()), name=clean_name, phone=phone, password_hash=password_hash)
    db.add(user)
    db.flush()
    token, _ = issue_session(db, user)
    return user, token


def authenticate_user(db: Session, *, phone: str, password: str) -> tuple[User, str]:
    phone = normalize_phone(phone)
    user = db.scalar(select(User).where(User.phone == phone, User.status == "active"))
    if user is None or not user.password_hash or not verify_password(password, user.password_hash):
        raise ValueError("invalid credentials")
    user.last_login_at = utcnow()
    token, _ = issue_session(db, user)
    return user, token


def resolve_session(db: Session, raw_token: str) -> User:
    if not raw_token:
        raise ValueError("token is required")
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
    now = utcnow()
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise ValueError("invalid or expired session")
    user = db.get(User, session.user_id)
    if user is None or user.status != "active":
        raise ValueError("user is not active")
    return user


def revoke_session(db: Session, raw_token: str) -> None:
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
    if session is None:
        return
    session.revoked_at = utcnow()
    db.flush()
