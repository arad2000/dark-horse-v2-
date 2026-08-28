"""Billing and authentication domain models for the staged Hybrid architecture.

These models are operational-only. They do not participate in scoring or
reference-data selection, and they do not enable PostgreSQL runtime cutover.
"""
from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
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


class PremiumPlan(Base):
    __tablename__ = "premium_plans"
    id = Column(BigInteger, primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    name_fa = Column(String(200), nullable=False)
    duration_days = Column(Integer, nullable=False)
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
    __table_args__ = (Index("idx_payments_provider_authority", "provider", "provider_authority"), Index("idx_payments_status", "status"))
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
    __table_args__ = (Index("idx_entitlement_user_status", "user_id", "status"),)
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(BigInteger, ForeignKey("premium_plans.id", ondelete="RESTRICT"), nullable=False)
    source = Column(String(20), nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="active", server_default="active")
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user = relationship("User", back_populates="entitlements")
    plan = relationship("PremiumPlan", back_populates="entitlements")
    order = relationship("Order", back_populates="entitlements")


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (Index("idx_payment_event_payment", "payment_id"),)
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
