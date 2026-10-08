from datetime import datetime, timezone
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class InvestigationOrder(Base):
    __tablename__ = "investigation_orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    admission_id: Mapped[int] = mapped_column(
        ForeignKey("admissions.id"),
        nullable=False,
    )

    test_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="GENERAL",
    )

    ordered_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    ordered_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    urgency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ROUTINE",
    )

    clinical_indication: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="ORDERED",
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    results = relationship(
        "InvestigationResult",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class InvestigationResult(Base):
    __tablename__ = "investigation_results"

    id: Mapped[int] = mapped_column(primary_key=True)

    investigation_order_id: Mapped[int] = mapped_column(
        ForeignKey("investigation_orders.id"),
        nullable=False,
    )

    recorded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    result_value: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    reference_range: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    is_abnormal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    critical_alert: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    order = relationship("InvestigationOrder", back_populates="results")
