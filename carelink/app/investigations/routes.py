from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.investigations.schemas import (
    InvestigationOrderCreate,
    InvestigationOrderResponse,
    InvestigationResultCreate,
    InvestigationResultResponse,
)
from app.investigations.service import (
    create_investigation_order,
    get_investigations_by_admission,
    get_late_investigations,
    record_investigation_result,
)

router = APIRouter(
    prefix="/investigations",
    tags=["Investigations"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/orders",
    response_model=InvestigationOrderResponse,
    status_code=201,
)
def create_investigation_order_endpoint(
    order: InvestigationOrderCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_investigation_order(db, order)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get(
    "/admission/{admission_id}",
    response_model=list[InvestigationOrderResponse],
)
def get_investigations_by_admission_endpoint(
    admission_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_investigations_by_admission(db, admission_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.post(
    "/results",
    response_model=InvestigationResultResponse,
    status_code=201,
)
def record_investigation_result_endpoint(
    result: InvestigationResultCreate,
    db: Session = Depends(get_db),
):
    try:
        return record_investigation_result(db, result)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get(
    "/late",
)
def get_late_investigations_endpoint(
    routine_hours: int = 24,
    urgent_hours: int = 6,
    stat_hours: int = 2,
    db: Session = Depends(get_db),
):
    return get_late_investigations(
        db,
        routine_threshold_hours=routine_hours,
        urgent_threshold_hours=urgent_hours,
        stat_threshold_hours=stat_hours,
    )
