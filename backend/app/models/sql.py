"""
SQLAlchemy ORM model for the trades table.
Must match the schema defined in infra/mysql/init.sql.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    action: Mapped[str] = mapped_column(Enum("BUY", "SELL"), nullable=False)
    order_type: Mapped[str] = mapped_column(
        Enum("MARKET", "LIMIT", "STOP"), default="MARKET"
    )
    status: Mapped[str] = mapped_column(
        Enum("PENDING", "FILLED", "CANCELLED", "REJECTED"), default="PENDING"
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    exec_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    # total_value is a generated column in MySQL — read-only here
    total_value: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 4), server_default=None, insert_default=None
    )
    fees: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    paper_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_workflow: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[int | None] = mapped_column(nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_user_ticker", "user_id", "ticker"),
        Index("idx_ticker_time", "ticker", "created_at"),
        Index("idx_status", "status"),
        Index("idx_paper", "paper_flag"),
        Index("idx_external", "external_order_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Trade(id={self.id}, ticker={self.ticker}, "
            f"action={self.action}, status={self.status}, "
            f"qty={self.quantity}, price={self.exec_price})>"
        )
