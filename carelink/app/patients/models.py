from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)

    patient_number: Mapped[str] = mapped_column(
        String(20),
        unique=True, 
        nullable=False
    )