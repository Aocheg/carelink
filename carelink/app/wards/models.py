from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Ward(Base):
    __tablename__ = "wards"

    __table_args__ = (
        UniqueConstraint(
            "facility_id",
            "name",
            name="uq_ward_facility_name"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    facility_id: Mapped[int] = mapped_column(
        ForeignKey("facilities.id"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class Bed(Base):
    __tablename__ = "beds"

    __table_args__ = (
        UniqueConstraint(
            "ward_id",
            "bed_number",
            name="uq_bed_ward_number"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    ward_id: Mapped[int] = mapped_column(
        ForeignKey("wards.id"),
        nullable=False
    )

    bed_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="AVAILABLE"
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(datetime.UTC)
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(datetime.UTC),
        onupdate=lambda: datetime.now(datetime.UTC)
    )