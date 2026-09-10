from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.facilities.schemas import (
    FacilityCreate,
    FacilityResponse,
)
from app.facilities.service import (
    create_facility,
    get_facilities,
    get_facility_by_id,
)


router = APIRouter(
    prefix="/facilities",
    tags=["Facilities"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=FacilityResponse,
    status_code=201
)
def create_facility_endpoint(
    facility: FacilityCreate,
    db: Session = Depends(get_db)
):
    return create_facility(db, facility)


@router.get(
    "/",
    response_model=list[FacilityResponse]
)
def get_facilities_endpoint(
    db: Session = Depends(get_db)
):
    return get_facilities(db)


@router.get(
    "/{facility_id}",
    response_model=FacilityResponse
)
def get_facility_endpoint(
    facility_id: int,
    db: Session = Depends(get_db)
):
    facility = get_facility_by_id(db, facility_id)

    if facility is None:
        raise HTTPException(
            status_code=404,
            detail="Facility not found"
        )

    return facility