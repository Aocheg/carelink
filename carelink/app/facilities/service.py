from sqlalchemy import select
from sqlalchemy.orm import Session

from app.facilities.models import Facility


def create_facility(db: Session, facility_data):
    facility = Facility(
        name=facility_data.name,
        description=facility_data.description,
    )

    db.add(facility)
    db.commit()
    db.refresh(facility)

    return facility


def get_facilities(db: Session):
    result = db.execute(
        select(Facility).order_by(Facility.id)
    )

    return result.scalars().all()


def get_facility_by_id(db: Session, facility_id: int):
    result = db.execute(
        select(Facility).where(Facility.id == facility_id)
    )

    return result.scalar_one_or_none()