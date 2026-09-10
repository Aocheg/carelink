from sqlalchemy import select
from sqlalchemy.orm import Session

from app.wards.models import Ward, Bed


def create_ward(db: Session, ward_data):
    ward = Ward(
        facility_id=ward_data.facility_id,
        name=ward_data.name,
        description=ward_data.description,
    )

    db.add(ward)
    db.commit()
    db.refresh(ward)

    return ward


def get_wards(db: Session):
    result = db.execute(
        select(Ward).order_by(Ward.id)
    )

    return result.scalars().all()


def get_ward_by_id(db: Session, ward_id: int):
    result = db.execute(
        select(Ward).where(Ward.id == ward_id)
    )

    return result.scalar_one_or_none()


def create_bed(db: Session, bed_data):
    bed = Bed(
        ward_id=bed_data.ward_id,
        bed_number=bed_data.bed_number,
        status="AVAILABLE",
    )

    db.add(bed)
    db.commit()
    db.refresh(bed)

    return bed


def get_beds(db: Session):
    result = db.execute(
        select(Bed).order_by(Bed.id)
    )

    return result.scalars().all()


def get_beds_by_ward(db: Session, ward_id: int):
    result = db.execute(
        select(Bed)
        .where(Bed.ward_id == ward_id)
        .order_by(Bed.id)
    )

    return result.scalars().all()