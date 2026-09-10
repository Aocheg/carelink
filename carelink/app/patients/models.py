from datetime import date, datetime
from sqlalchemy import String, DateTime, ForeignKey
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

    date_of_birth: Mapped[date | None] = mapped_column(
        nullable=True
    ) 

    sex: Mapped[str | None] = mapped_column(
        String(20), 
        nullable=True
    )

    marital_status: Mapped[str | None] = mapped_column(
        String(30), 
        nullable=True
    )

    religion: Mapped[str | None] = mapped_column(
        String(30), 
        nullable=True
    )

    occupation: Mapped[str | None] = mapped_column(
        String(100), 
        nullable=True
    )

    address: Mapped[str | None] = mapped_column(
        String(250), 
        nullable=True
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(30), 
        nullable=True
    )

    blood_group: Mapped[str | None] = mapped_column(
        String(5), 
        nullable=True
    )

    genotype: Mapped[str | None] = mapped_column(
        String(5), 
        nullable=True
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
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

class NextOfKin(Base):
    __tablename__ = "next_of_kins"

    id: Mapped[int] = mapped_column(primary_key=True)

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    relationship: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    phone_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    address: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True
    )

    is_primary: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )