from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.patients.models import Patient


def generate_patient_number(db: Session) -> str:
    result = db.execute(
        select(func.count(Patient.id))
    )

    count = result.scalar_one()

    next_number = count + 1

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
