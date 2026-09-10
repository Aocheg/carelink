from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.facilities.service import get_facility_by_id
from app.wards.schemas import (
    WardCreate,
    WardResponse,
    BedCreate,
    BedResponse,
)
from app.wards.service import (
    create_ward,
    get_wards,
    get_ward_by_id,
    create_bed,
    get_beds,
    get_beds_by_ward,
)


router = APIRouter(
    prefix="/wards",
    tags=["Wards"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=WardResponse,
    status_code=201
)
def create_ward_endpoint(
    ward: WardCreate,
    db: Session = Depends(get_db)
):
    facility = get_facility_by_id(
        db,
        ward.facility_id
    )

    if facility is None:
        raise HTTPException(
            status_code=404,
            detail="Facility not found"
        )

    return create_ward(db, ward)


@router.get(
    "/",
    response_model=list[WardResponse]
)
def get_wards_endpoint(
    db: Session = Depends(get_db)
):
    return get_wards(db)


@router.get(
    "/{ward_id}",
    response_model=WardResponse
)
def get_ward_endpoint(
    ward_id: int,
    db: Session = Depends(get_db)
):
    ward = get_ward_by_id(db, ward_id)

    if ward is None:
        raise HTTPException(
            status_code=404,
            detail="Ward not found"
        )

    return ward


@router.post(
    "/beds",
    response_model=BedResponse,
    status_code=201
)
def create_bed_endpoint(
    bed: BedCreate,
    db: Session = Depends(get_db)
):
    ward = get_ward_by_id(
        db,
        bed.ward_id
    )

    if ward is None:
        raise HTTPException(
            status_code=404,
            detail="Ward not found"
        )

    return create_bed(db, bed)


@router.get(
    "/beds/all",
    response_model=list[BedResponse]
)
def get_beds_endpoint(
    db: Session = Depends(get_db)
):
    return get_beds(db)


@router.get(
    "/{ward_id}/beds",
    response_model=list[BedResponse]
)
def get_ward_beds_endpoint(
    ward_id: int,
    db: Session = Depends(get_db)
):
    ward = get_ward_by_id(db, ward_id)

    if ward is None:
        raise HTTPException(
            status_code=404,
            detail="Ward not found"
        )

    return get_beds_by_ward(db, ward_id)