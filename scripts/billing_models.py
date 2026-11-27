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
    referral_code = Column(String(64), nullable=True)
    referral_locked_at = Column(DateTime(timezone=True), nullable=True)
    auth_sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    entitlements = relationship("Entitlement", back_populates="user", cascade="all, delete-orphan")
    admin_audit_logs = relationship("AdminAuditLog", back_populates="admin_user")


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


class PhoneVerification(Base):
    __tablename__ = "phone_verifications"
    __table_args__ = (
        Index("idx_phone_verification_phone", "phone", "purpose", "created_at"),
        Index("idx_phone_verification_ip_created", "request_ip", "created_at"),
        UniqueConstraint("challenge_id", name="uq_phone_verification_challenge"),
    )
    id = Column(BigInteger, primary_key=True)
    challenge_id = Column(String(128), nullable=False, unique=True)
    phone = Column(String(32), nullable=False)
    purpose = Column(String(32), nullable=False, default="register", server_default="register")
    name = Column(String(200), nullable=False)
    password_hash = Column(Text, nullable=False)
    code_hash = Column(String(128), nullable=False)
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    request_ip = Column(String(45), nullable=True)
    referral_code_input = Column(String(64), nullable=True)
    referral_rejected_reason = Column(String(64), nullable=True)
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
    currency = Column(String(8), nullable=False, default="IRR")
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
    marketer_id_snapshot = Column(Integer, nullable=True)
    commission_bps_snapshot = Column(Integer, nullable=True)
    referral_code_snapshot = Column(String(64), nullable=True)
    referral_label_snapshot = Column(String(200), nullable=True)
    referral_snapshot_at = Column(DateTime(timezone=True), nullable=True)
    user = relationship("User", back_populates="orders")
    plan = relationship("PremiumPlan", back_populates="orders")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    entitlements = relationship("Entitlement", back_populates="order")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("idx_payments_provider_authority", "provider", "provider_authority"),
        Index("idx_payments_status", "status"),
        UniqueConstraint("provider", "provider_transaction_id", name="uq_payment_provider_transaction"),
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
    __table_args__ = (
        Index("idx_admin_audit_created", "created_at"),
        Index(
            "uq_admin_audit_referral_code",
            "target_id",
            unique=True,
            postgresql_where=text("target_type = 'referral_code' AND action = 'create_referral_code'"),
            sqlite_where=text("target_type = 'referral_code' AND action = 'create_referral_code'"),
        ),
    )
    id = Column(BigInteger, primary_key=True)
    admin_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(100), nullable=False)
    metadata_json = Column("metadata", JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    admin_user = relationship("User", back_populates="admin_audit_logs")


class JourneyCreditConsumption(Base):
    """Independent billing ledger: one authenticated journey UUID => one charge."""
    __tablename__ = "journey_credit_consumptions"
    __table_args__ = (
        UniqueConstraint("session_uuid", name="uq_journey_credit_consumption_session"),
        Index("idx_journey_credit_consumption_user", "user_id"),
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_uuid = Column(String(64), nullable=False)
    entitlement_id = Column(BigInteger, ForeignKey("entitlements.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User")
    entitlement = relationship("Entitlement")

class ReferralMarketer(Base):
    """Owner of one or more referral codes.

    May be an existing account (``user_id`` set) or an outside person with no
    account. Commission is expressed in basis points so all money math stays
    integer-only.
    """

    __tablename__ = "referral_marketers"
    __table_args__ = (
        Index("idx_referral_marketer_user", "user_id"),
        Index("idx_referral_marketer_active", "is_active"),
    )
    id = Column(Integer, primary_key=True)
    public_id = Column(String(40), nullable=False, unique=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(32), nullable=True)
    commission_bps = Column(Integer, nullable=False, default=0, server_default="0")
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    note = Column(String(500), nullable=True)
    # True when the owner minted this themselves rather than being onboarded.
    self_service = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ReferralCode(Base):
    """Registry row binding a public code to its marketer."""

    __tablename__ = "referral_codes"
    __table_args__ = (Index("idx_referral_codes_marketer", "marketer_id"),)
    id = Column(Integer, primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    marketer_id = Column(Integer, ForeignKey("referral_marketers.id", ondelete="RESTRICT"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_by_user_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReferralCommission(Base):
    """Accrued commission for exactly one paid order (never a payment)."""

    __tablename__ = "referral_commissions"
    __table_args__ = (
        Index("idx_referral_commission_marketer", "marketer_id"),
        Index("idx_referral_commission_status", "status"),
    )
    id = Column(Integer, primary_key=True)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    marketer_id = Column(Integer, ForeignKey("referral_marketers.id", ondelete="RESTRICT"), nullable=False)
    referral_code = Column(String(64), nullable=False)
    gross_amount_minor = Column(BigInteger, nullable=False)
    commission_bps = Column(Integer, nullable=False)
    commission_amount_minor = Column(BigInteger, nullable=False)
    currency = Column(String(8), nullable=False)
    status = Column(String(16), nullable=False, default="accrued", server_default="accrued")
    settled_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReferralSignup(Base):
    """One immutable attribution row per account, written at signup.

    Independent of purchases: this is the "how many people did this marketer
    bring" counter. ``user_id`` is unique, so it can never double count.
    """

    __tablename__ = "referral_signups"
    __table_args__ = (
        Index("idx_referral_signups_marketer", "marketer_id"),
        Index("idx_referral_signups_code", "code"),
        Index("idx_referral_signups_created", "created_at"),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    code = Column(String(64), nullable=False)
    marketer_id = Column(Integer, ForeignKey("referral_marketers.id", ondelete="RESTRICT"), nullable=True)
    source = Column(String(32), nullable=False, default="register", server_default="register")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
