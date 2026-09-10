from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.patients.schemas import (
    PatientCreate,
    PatientResponse,
    NextOfKinCreate,
    NextOfKinResponse,
)
from app.patients.service import (
    create_patient,
    get_patients,
    get_patient_by_id,
    search_patients,
    find_duplicate_patient,
    create_next_of_kin,
    get_next_of_kins,
)
from app.audit.service import create_audit_log

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


@router.post("/", response_model=PatientResponse, status_code=201)
def create_patient_endpoint(patient: PatientCreate, db: Session = Depends(get_db)):
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
    
    create_audit_log(
        db,
        user_id=None,
        action="CREATE",
        entity_type="PATIENT",
        entity_id=saved_patient.id,
        details=f"Patient {saved_patient.patient_number} registered"
    )

    return saved_patient


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

@router.post(
    "/{patient_id}/next-of-kin",
    response_model=NextOfKinResponse
)
def create_next_of_kin_endpoint(
    patient_id: int,
    kin: NextOfKinCreate,
    db: Session = Depends(get_db)
):
    patient = get_patient_by_id(db, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return create_next_of_kin(
        db,
        patient_id,
        kin
    )


@router.get(
    "/{patient_id}/next-of-kin",
    response_model=list[NextOfKinResponse]
)
def get_next_of_kins_endpoint(
    patient_id: int,
    db: Session = Depends(get_db)
):
    patient = get_patient_by_id(db, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return get_next_of_kins(
        db,
        patient_id
    )
    

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


