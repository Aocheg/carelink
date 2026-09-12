from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Admission(Base):
    __tablename__ = "admissions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    admission_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False
    )

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False
    )

    ward_id: Mapped[int] = mapped_column(
        ForeignKey("wards.id"),
        nullable=False
    )

    bed_id: Mapped[int] = mapped_column(
        ForeignKey("beds.id"),
        nullable=False
    )

    admitted_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    reason_for_admission: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    presenting_complaint: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    patient_account: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    doctor_assessment: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True
    )

    nursing_assessment: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True
    )

    nursing_diagnosis: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True
    )

    admitted_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="ACTIVE"
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )