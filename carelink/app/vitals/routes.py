from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.vitals.schemas import VitalSignCreate, VitalSignResponse
from app.vitals.service import (
    create_vital_sign,
    get_vital_sign_by_id,
    get_vital_signs_by_admission,
)


router = APIRouter(
    prefix="/vitals",
    tags=["Vital Signs"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=VitalSignResponse,
    status_code=201,
)
def create_vital_sign_endpoint(
    vital: VitalSignCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_vital_sign(db, vital)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get(
    "/admission/{admission_id}",
    response_model=list[VitalSignResponse],
)
def get_vital_signs_by_admission_endpoint(
    admission_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_vital_signs_by_admission(
            db,
            admission_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@router.get(
    "/{vital_sign_id}",
    response_model=VitalSignResponse,
)
def get_vital_sign_endpoint(
    vital_sign_id: int,
    db: Session = Depends(get_db),
):
    vital_sign = get_vital_sign_by_id(
        db,
        vital_sign_id,
    )

    if vital_sign is None:
        raise HTTPException(
            status_code=404,
            detail="Vital-sign record not found",
        )

    return vital_sign