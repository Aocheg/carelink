from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.patients.models import Patient
from app.wards.models import Ward, Bed
from app.users.models import User
from app.audit.service import create_audit_log


def generate_admission_number(db: Session) -> str:
    result = db.execute(
        select(Admission.id)
        .order_by(Admission.id.desc())
    )

    last_id = result.scalars().first()

    next_id = (last_id or 0) + 1

    year = datetime.now(datetime.UTC).year

    return f"ADM-{year}-{next_id:06d}"


def create_admission(
    db: Session,
    admission_data,
):
    patient = db.get(
        Patient,
        admission_data.patient_id
    )

    if patient is None:
        raise ValueError("Patient not found")

    ward = db.get(
        Ward,
        admission_data.ward_id
    )

    if ward is None:
        raise ValueError("Ward not found")

    bed = db.get(
        Bed,
        admission_data.bed_id
    )

    if bed is None:
        raise ValueError("Bed not found")

    user = db.get(
        User,
        admission_data.admitted_by
    )

    if user is None:
        raise ValueError("Admitting healthcare worker not found")

    if not user.is_active:
        raise ValueError(
            "Admitting healthcare worker is inactive"
        )

    if bed.ward_id != ward.id:
        raise ValueError(
            "Selected bed does not belong to selected ward"
        )

    if bed.status != "AVAILABLE":
        raise ValueError(
            "Selected bed is not available"
        )

    admission_number = generate_admission_number(db)

    admission = Admission(
        admission_number=admission_number,
        patient_id=admission_data.patient_id,
        ward_id=admission_data.ward_id,
        bed_id=admission_data.bed_id,
        source=admission_data.source,
        reason_for_admission=(
            admission_data.reason_for_admission
        ),
        presenting_complaint=(
            admission_data.presenting_complaint
        ),
        patient_account=(
            admission_data.patient_account
        ),
        doctor_assessment=(
            admission_data.doctor_assessment
        ),
        nursing_assessment=(
            admission_data.nursing_assessment
        ),
        nursing_diagnosis=(
            admission_data.nursing_diagnosis
        ),
        admitted_by=admission_data.admitted_by,
        status="ACTIVE",
    )

    bed.status = "OCCUPIED"

    db.add(admission)
    db.commit()
    db.refresh(admission)

    create_audit_log(
        db,
        user_id=admission.admitted_by,
        action="CREATE",
        entity_type="ADMISSION",
        entity_id=admission.id,
        details=f"Admission {admission.admission_number} created"
    )

    return admission

def get_admissions(db: Session):
    result = db.execute(
        select(Admission)
        .order_by(Admission.id)
    )

    return result.scalars().all()


def get_admission_by_id(
    db: Session,
    admission_id: int
):
    result = db.execute(
        select(Admission).where(
            Admission.id == admission_id
        )
    )

    return result.scalar_one_or_none()