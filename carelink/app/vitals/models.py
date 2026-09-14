from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.database.connection import Base


class UTCDateTime(TypeDecorator):
    """
    Store timestamps in UTC and return them as timezone-aware datetimes.

    SQLite does not preserve timezone information in its normal DateTime
    column, so this type explicitly converts timestamps to UTC when saving
    and restores UTC timezone information when reading.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        value = value.astimezone(timezone.utc)

        # SQLite DateTime does not store timezone information.
        # Store the UTC clock time and restore the timezone when reading.
        return value.replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)


class VitalSign(Base):
    __tablename__ = "vital_signs"

    id: Mapped[int] = mapped_column(primary_key=True)

    admission_id: Mapped[int] = mapped_column(
        ForeignKey("admissions.id"),
        nullable=False,
        index=True,
    )

    recorded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    systolic_bp: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    diastolic_bp: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    pulse: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    temperature: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    respiratory_rate: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    spo2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    measurement_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="COMPLETE",
    )

    not_measured_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )