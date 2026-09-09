from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.patients.schemas import PatientCreate, PatientResponse
from app.patients.service import (
    create_patient,
    get_patients,
    get_patient_by_id,
    search_patients,
    find_duplicate_patient,
)

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
    existing_patient = find_duplicate_patient(
        db,
        patient.full_name,
        patient.date_of_birth,
    )

    if existing_patient:
        raise HTTPException(
            status_code=409,
            detail="A patient with the same name and date of birth already exists"
        )

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

@router.get("/", response_model=list[PatientResponse])
def get_patients_endpoint(
    db: Session = Depends(get_db)
):
    patients = get_patients(db)

    return patients


@router.get("/search", response_model=list[PatientResponse])
def search_patients_endpoint(
    name: str | None = None,
    phone_number: str | None = None,
    patient_number: str | None = None,
    db: Session = Depends(get_db)
):
    patients = search_patients(
        db,
        name=name,
        phone_number=phone_number,
        patient_number=patient_number,
    )

    return patients
    

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_endpoint(
    patient_id: int,
    db: Session = Depends(get_db)
):
    patient = get_patient_by_id(db, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient


