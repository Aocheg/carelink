from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.medications.schemas import (
    MedicationOrderCreate,
    MedicationOrderResponse,
)
from app.medications.service import (
    create_medication_order,
    get_medication_order_by_id,
    get_medication_orders_by_admission,
)


router = APIRouter(
    prefix="/medications",
    tags=["Medications"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=MedicationOrderResponse,
    status_code=201,
)
def create_medication_order_endpoint(
    medication: MedicationOrderCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_medication_order(
            db,
            medication,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get(
    "/admission/{admission_id}",
    response_model=list[MedicationOrderResponse],
)
def get_medication_orders_by_admission_endpoint(
    admission_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_medication_orders_by_admission(
            db,
            admission_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@router.get(
    "/{medication_order_id}",
    response_model=MedicationOrderResponse,
)
def get_medication_order_endpoint(
    medication_order_id: int,
    db: Session = Depends(get_db),
):
    medication_order = get_medication_order_by_id(
        db,
        medication_order_id,
    )

    if medication_order is None:
        raise HTTPException(
            status_code=404,
            detail="Medication order not found",
        )

    return medication_order