from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.admissions.schemas import (
    AdmissionCreate,
    AdmissionResponse,
)
from app.admissions.service import (
    create_admission,
    get_admissions,
    get_admission_by_id,
)


router = APIRouter(
    prefix="/admissions",
    tags=["Admissions"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=AdmissionResponse,
    status_code=201
)
def create_admission_endpoint(
    admission: AdmissionCreate,
    db: Session = Depends(get_db)
):
    try:
        return create_admission(
            db,
            admission
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@router.get(
    "/",
    response_model=list[AdmissionResponse]
)
def get_admissions_endpoint(
    db: Session = Depends(get_db)
):
    return get_admissions(db)


@router.get(
    "/{admission_id}",
    response_model=AdmissionResponse
)
def get_admission_endpoint(
    admission_id: int,
    db: Session = Depends(get_db)
):
    admission = get_admission_by_id(
        db,
        admission_id
    )

    if admission is None:
        raise HTTPException(
            status_code=404,
            detail="Admission not found"
        )

    return admission