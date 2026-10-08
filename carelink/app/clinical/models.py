from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id: Mapped[int] = mapped_column(primary_key=True)

    admission_id: Mapped[int] = mapped_column(
        ForeignKey("admissions.id"),
        nullable=False,
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    note_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # DOCTOR_REVIEW, NURSING_ASSESSMENT, NURSING_DIAGNOSIS, NURSING_NOTE, HANDOVER_NOTE

    content: Mapped[str] = mapped_column(
        String(3000),
        nullable=False,
    )

    plan: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
