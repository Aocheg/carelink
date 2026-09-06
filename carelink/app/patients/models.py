from datetime import date, datetime

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

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    date_of_birth: Mapped[date] = mapped_column(
        nullable=False
    ) 

    sex: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )

    marital_status: Mapped[str] = mapped_column(
        String(30), 
        nullable=False
    )

    religion: Mapped[str] = mapped_column(
        String(30), 
        nullable=False
    )

    occupation: Mapped[str] = mapped_column(
        String(100), 
        nullable=False
    )

    address: Mapped[str] = mapped_column(
        String(250), 
        nullable=False
    )

    phone_number: Mapped[str] = mapped_column(
        String(30), 
        nullable=False
    )

    blood_group: Mapped[str] = mapped_column(
        String(5), 
        nullable=False
    )

    genotype: Mapped[str] = mapped_column(
        String(5), 
        nullable=False
    )

    allergy_status: Mapped[str] = mapped_column(
        String(30), 
        nullable=False
    )

    allergy_details: Mapped[str | None] = mapped_column(
        String(250), 
        nullable=True
    )


    created_at: Mapped[datetime] = mapped_column(
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False
    )