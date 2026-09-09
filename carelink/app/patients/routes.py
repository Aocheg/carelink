from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.patients.schemas import PatientCreate
from app.patients.service import create_patient


router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/")
def create_patient_endpoint(
    patient: PatientCreate,
    db: Session = Depends(get_db)
):
    saved_patient = create_patient(db, patient)

    return {
        "message": "Patient created successfully",
        "patient": {
            "id": saved_patient.id,
            "patient_number": saved_patient.patient_number,
            "full_name": saved_patient.full_name,
            "date_of_birth": saved_patient.date_of_birth,
            "sex": saved_patient.sex,
            "marital_status": saved_patient.marital_status,
            "religion": saved_patient.religion,
            "occupation": saved_patient.occupation,
            "address": saved_patient.address,
            "phone_number": saved_patient.phone_number,
            "blood_group": saved_patient.blood_group,
            "genotype": saved_patient.genotype,
            "allergy_status": saved_patient.allergy_status,
            "allergy_details": saved_patient.allergy_details,
        }
    }
