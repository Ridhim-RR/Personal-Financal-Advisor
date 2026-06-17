from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func

from src.db.connection import Base

# ── Re-export all src.db.models for convenience ──────────────
from src.db.models import (
    UserORM,
    UserProfileORM,
    PortfolioORM,
    WatchlistORM,
    RecommendationLogORM,
    HoldingORM,
    AlertORM,
    TransactionORM,
    AgentAnalysisORM,
)


class HedgeFundFlow(Base):
    """Table to store React Flow configurations (nodes, edges, viewport)"""
    __tablename__ = "hedge_fund_flows"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    nodes = Column(JSON, nullable=False)
    edges = Column(JSON, nullable=False)
    viewport = Column(JSON, nullable=True)
    data = Column(JSON, nullable=True)

    is_template = Column(Boolean, default=False)
    tags = Column(JSON, nullable=True)


class HedgeFundFlowRun(Base):
    __tablename__ = "hedge_fund_flow_runs"

    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(Integer, ForeignKey("hedge_fund_flows.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    status = Column(String(50), nullable=False, default="IDLE")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    trading_mode = Column(String(50), nullable=False, default="one-time")
    schedule = Column(String(50), nullable=True)
    duration = Column(String(50), nullable=True)

    request_data = Column(JSON, nullable=True)
    initial_portfolio = Column(JSON, nullable=True)
    final_portfolio = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    run_number = Column(Integer, nullable=False, default=1)


class HedgeFundFlowRunCycle(Base):
    __tablename__ = "hedge_fund_flow_run_cycles"

    id = Column(Integer, primary_key=True, index=True)
    flow_run_id = Column(Integer, ForeignKey("hedge_fund_flow_runs.id"), nullable=False, index=True)
    cycle_number = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    analyst_signals = Column(JSON, nullable=True)
    trading_decisions = Column(JSON, nullable=True)
    executed_trades = Column(JSON, nullable=True)

    portfolio_snapshot = Column(JSON, nullable=True)
    performance_metrics = Column(JSON, nullable=True)

    status = Column(String(50), nullable=False, default="IN_PROGRESS")
    error_message = Column(Text, nullable=True)

    llm_calls_count = Column(Integer, nullable=True, default=0)
    api_calls_count = Column(Integer, nullable=True, default=0)
    estimated_cost = Column(String(20), nullable=True)

    trigger_reason = Column(String(100), nullable=True)
    market_conditions = Column(JSON, nullable=True)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    provider = Column(String(100), nullable=False, unique=True, index=True)
    key_value = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

    description = Column(Text, nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
