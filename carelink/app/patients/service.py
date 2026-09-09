from datetime import date
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.patients.models import Patient


def generate_patient_number(db: Session) -> str:
    result = db.execute(
        select(func.max(Patient.id))
    )

    max_id = result.scalar_one()

    next_number = (max_id or 0) + 1

    return f"CL-{next_number:06d}"


def create_patient(db: Session, patient_data):
    patient_number = generate_patient_number(db)

    patient = Patient(
        patient_number=patient_number,
        full_name=patient_data.full_name,
        date_of_birth=patient_data.date_of_birth,
        sex=patient_data.sex,
        marital_status=patient_data.marital_status,
        religion=patient_data.religion,
        occupation=patient_data.occupation,
        address=patient_data.address,
        phone_number=patient_data.phone_number,
        blood_group=patient_data.blood_group,
        genotype=patient_data.genotype,
        allergy_status=patient_data.allergy_status,
        allergy_details=patient_data.allergy_details,
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    return patient


def get_patients(db: Session):
    result = db.execute(
        select(Patient).order_by(Patient.id)
    )

    return result.scalars().all()

def get_patient_by_id(db: Session, patient_id: int):
    result = db.execute(
        select(Patient).where(Patient.id == patient_id)
    )

    return result.scalar_one_or_none()


def search_patients(
    db: Session,
    name: str | None = None,
    phone_number: str | None = None,
    patient_number: str | None = None,
):
    query = select(Patient)

    if name:
        query = query.where(
            Patient.full_name.ilike(f"%{name}%")
        )

    if phone_number:
        query = query.where(
            Patient.phone_number == phone_number
        )

    if patient_number:
        query = query.where(
            Patient.patient_number == patient_number
        )

    result = db.execute(query)

    return result.scalars().all()

def find_duplicate_patient(
    db: Session,
    full_name: str,
    date_of_birth: date | None,
):
    query = select(Patient).where(
        Patient.full_name.ilike(full_name)
    )

    if date_of_birth is not None:
        query = query.where(
            Patient.date_of_birth == date_of_birth
        )

    result = db.execute(query)

    return result.scalar_one_or_none()