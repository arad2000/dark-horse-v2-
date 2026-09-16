"""Billing/auth models for staged Hybrid mode.

The product is credit-based, not a time subscription:
- free_1_test => exactly 1 test credit
- pack_3_tests => exactly 3 additional test credits after verified payment
- expiration is optional and normally NULL
"""
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("idx_users_status", "status"),)
    id = Column(BigInteger, primary_key=True)
    public_id = Column(String(36), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(32), nullable=False, unique=True)
    password_hash = Column(Text, nullable=True)
    role = Column(String(20), nullable=False, default="user", server_default="user")
    status = Column(String(20), nullable=False, default="active", server_default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    auth_sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    entitlements = relationship("Entitlement", back_populates="user", cascade="all, delete-orphan")
    admin_audit_logs = relationship("AdminAuditLog", back_populates="admin_user")
    saved_results = relationship("SavedResult", back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (Index("idx_auth_session_expiry", "expires_at"),)
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(128), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="auth_sessions")


class RegistrationChallenge(Base):
    __tablename__ = "registration_challenges"
    __table_args__ = (
        UniqueConstraint("challenge_id", name="uq_registration_challenge_id"),
        Index("idx_registration_challenge_phone", "phone"),
        Index("idx_registration_challenge_expiry", "expires_at"),
    )
    id = Column(BigInteger, primary_key=True)
    challenge_id = Column(String(36), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(32), nullable=False)
    password_hash = Column(Text, nullable=False)
    code_hash = Column(String(128), nullable=False)
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    max_attempts = Column(Integer, nullable=False, default=5, server_default="5")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PremiumPlan(Base):
    __tablename__ = "premium_plans"
    __table_args__ = (UniqueConstraint("code", name="uq_premium_plan_code"),)
    id = Column(BigInteger, primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    name_fa = Column(String(200), nullable=False)
    plan_type = Column(String(20), nullable=False, default="credits", server_default="credits")
    duration_days = Column(Integer, nullable=True)
    credits_granted = Column(Integer, nullable=False, default=0, server_default="0")
    price_minor = Column(BigInteger, nullable=False)
    currency = Column(String(8), nullable=False, default="IRR", server_default="IRR")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    features = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    orders = relationship("Order", back_populates="plan")
    entitlements = relationship("Entitlement", back_populates="plan")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("idx_orders_status", "status"),)
    id = Column(BigInteger, primary_key=True)
    public_id = Column(String(36), nullable=False, unique=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    plan_id = Column(BigInteger, ForeignKey("premium_plans.id", ondelete="RESTRICT"), nullable=False)
    amount_minor = Column(BigInteger, nullable=False)
    currency = Column(String(8), nullable=False)
    status = Column(String(20), nullable=False, default="pending", server_default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user = relationship("User", back_populates="orders")
    plan = relationship("PremiumPlan", back_populates="orders")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    entitlements = relationship("Entitlement", back_populates="order")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("idx_payments_provider_authority", "provider", "provider_authority"),
        Index("idx_payments_status", "status"),
        Index(
            "uq_payment_provider_transaction",
            "provider",
            "provider_transaction_id",
            unique=True,
            postgresql_where=text("provider_transaction_id IS NOT NULL"),
        ),
    )
    id = Column(BigInteger, primary_key=True)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(32), nullable=False)
    provider_request_id = Column(String(128), nullable=True)
    provider_authority = Column(String(128), nullable=True)
    provider_transaction_id = Column(String(128), nullable=True)
    amount_minor = Column(BigInteger, nullable=False)
    currency = Column(String(8), nullable=False)
    status = Column(String(20), nullable=False, default="initiated", server_default="initiated")
    raw_callback = Column(JSON, nullable=True)
    verification_response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    order = relationship("Order", back_populates="payments")
    events = relationship("PaymentEvent", back_populates="payment", cascade="all, delete-orphan")


class Entitlement(Base):
    __tablename__ = "entitlements"
    __table_args__ = (
        Index("idx_entitlement_user_status", "user_id", "status"),
        Index("idx_entitlement_user_credits", "user_id", "credits_remaining"),
    )
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(BigInteger, ForeignKey("premium_plans.id", ondelete="RESTRICT"), nullable=False)
    source = Column(String(20), nullable=False)
    credits_granted = Column(Integer, nullable=False, default=0, server_default="0")
    credits_remaining = Column(Integer, nullable=False, default=0, server_default="0")
    starts_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="active", server_default="active")
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user = relationship("User", back_populates="entitlements")
    plan = relationship("PremiumPlan", back_populates="entitlements")
    order = relationship("Order", back_populates="entitlements")


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (Index("idx_payment_event_payment", "payment_id"), UniqueConstraint("event_key", name="uq_payment_event_key"))
    id = Column(BigInteger, primary_key=True)
    payment_id = Column(BigInteger, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_key = Column(String(200), nullable=False, unique=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    payment = relationship("Payment", back_populates="events")


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    __table_args__ = (Index("idx_admin_audit_created", "created_at"),)
    id = Column(BigInteger, primary_key=True)
    admin_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(100), nullable=False)
    metadata_json = Column("metadata", JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    admin_user = relationship("User", back_populates="admin_audit_logs")


class SavedResult(Base):
    __tablename__ = "saved_results"
    __table_args__ = (
        Index("idx_saved_results_user_created", "user_id", "created_at"),
        Index("idx_saved_results_session", "session_uuid"),
    )
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_uuid = Column(String(36), nullable=True)
    result_summary = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user = relationship("User", back_populates="saved_results")
