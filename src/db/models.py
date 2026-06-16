"""SQLAlchemy ORM models for the Personal AI Investment Advisor.

PostgreSQL in production, SQLite for local development.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, JSON, DateTime, Text, ForeignKey, Boolean, Integer, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.db.connection import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _uuid_column():
    """Use PostgreSQL UUID on pg, String on sqlite for cross-compat."""
    return Column(String(36), primary_key=True, default=_uuid)


def _timestamp():
    return datetime.utcnow()


# ── User & Profile ────────────────────────────────────────────

class UserORM(Base):
    __tablename__ = "users"

    id = _uuid_column()
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_timestamp)
    updated_at = Column(DateTime, default=_timestamp, onupdate=_timestamp)

    profile = relationship("UserProfileORM", uselist=False, back_populates="user", cascade="all, delete-orphan")
    holdings = relationship("PortfolioORM", back_populates="user", cascade="all, delete-orphan")
    watchlists = relationship("WatchlistORM", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("RecommendationLogORM", back_populates="user", cascade="all, delete-orphan")


class UserProfileORM(Base):
    __tablename__ = "user_profiles"

    id = _uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    risk_appetite = Column(String(50), default="moderate")          # conservative | moderate | aggressive
    investment_goal = Column(String(50), default="growth")          # growth | income | preservation
    investment_horizon = Column(String(50), default="medium")       # short | medium | long
    preferred_sectors = Column(JSON, default=list)
    excluded_sectors = Column(JSON, default=list)
    preferred_analysts = Column(JSON, default=list)
    initial_capital = Column(Float, default=100000.0)
    margin_requirement = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_timestamp)
    updated_at = Column(DateTime, default=_timestamp, onupdate=_timestamp)

    user = relationship("UserORM", back_populates="profile")


# ── Portfolio ─────────────────────────────────────────────────

class PortfolioORM(Base):
    __tablename__ = "portfolio_holdings"

    id = _uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(10), nullable=False)
    shares = Column(Float, default=0.0)
    avg_cost = Column(Float, default=0.0)
    target_allocation = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=_timestamp, onupdate=_timestamp)

    user = relationship("UserORM", back_populates="holdings")


class HoldingORM(Base):
    """Alias for PortfolioORM – same table, different query context."""
    __tablename__ = "portfolio_holdings"
    __table_args__ = {"extend_existing": True}

    id = _uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(10), nullable=False)
    shares = Column(Float, default=0.0)
    avg_cost = Column(Float, default=0.0)
    target_allocation = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=_timestamp, onupdate=_timestamp)


# ── Watchlists ────────────────────────────────────────────────

class WatchlistORM(Base):
    __tablename__ = "watchlists"

    id = _uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    tickers = Column(JSON, default=list)
    created_at = Column(DateTime, default=_timestamp)
    updated_at = Column(DateTime, default=_timestamp, onupdate=_timestamp)

    user = relationship("UserORM", back_populates="watchlists")


# ── Recommendation Logs ───────────────────────────────────────

class RecommendationLogORM(Base):
    __tablename__ = "recommendation_logs"

    id = _uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(10), nullable=False)
    signal = Column(String(20), nullable=False)        # buy | sell | hold
    confidence = Column(Float, default=0.0)
    reasoning = Column(Text, default="")
    agent_signals = Column(JSON, default=dict)
    user_action = Column(String(20), nullable=True)     # followed | ignored | null
    created_at = Column(DateTime, default=_timestamp)

    user = relationship("UserORM", back_populates="recommendations")


# ── Alerts ─────────────────────────────────────────────────────

class AlertORM(Base):
    """User-configured alerts for price targets, volume spikes, etc."""
    __tablename__ = "alerts"

    id = _uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(10), nullable=False)
    alert_type = Column(String(50), nullable=False)        # price_above | price_below | volume_spike | news
    threshold = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    triggered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_timestamp)
    updated_at = Column(DateTime, default=_timestamp, onupdate=_timestamp)


# ── Transactions ───────────────────────────────────────────────

class TransactionORM(Base):
    """Executed trade history for audit trail + P&L tracking."""
    __tablename__ = "transactions"

    id = _uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(10), nullable=False)
    action = Column(String(10), nullable=False)            # buy | sell
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=_timestamp)


# ── Agent Analysis History ────────────────────────────────────

class AgentAnalysisORM(Base):
    """Per-agent signal per ticker per recommendation run."""
    __tablename__ = "agent_analysis_logs"

    id = _uuid_column()
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_id = Column(String(36), ForeignKey("recommendation_logs.id", ondelete="SET NULL"), nullable=True)
    ticker = Column(String(10), nullable=False)
    agent_name = Column(String(100), nullable=False)
    signal = Column(String(20), nullable=False)            # bullish | bearish | neutral | buy | sell | hold
    confidence = Column(Float, default=0.0)
    reasoning = Column(Text, default="")
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_timestamp)
