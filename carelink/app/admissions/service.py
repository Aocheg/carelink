from datetime import datetime, timezone
from typing import Any

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

    year = datetime.now(timezone.utc).year

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

    if user.role not in ("NURSE", "DOCTOR", "ADMIN"):
        raise ValueError(
            f"User with role '{user.role}' cannot admit patients. Only NURSE, DOCTOR, or ADMIN can admit patients."
        )

    if bed.ward_id != ward.id:
        raise ValueError(
            "Selected bed does not belong to selected ward"
        )

    if bed.status != "AVAILABLE":
        raise ValueError(
            "Selected bed is not available"
        )

    active_stmt = select(Admission).where(
        Admission.patient_id == admission_data.patient_id,
        Admission.status == "ACTIVE",
    )
    existing_active = db.execute(active_stmt).scalars().first()
    if existing_active:
        raise ValueError(
            f"Patient already has an active admission ({existing_active.admission_number}). "
            "A patient cannot have multiple concurrent active admissions."
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

    try:
        bed.status = "OCCUPIED"
        db.add(admission)

        db.flush()

        create_audit_log(
            db,
            user_id=admission.admitted_by,
            action="CREATE",
            entity_type="ADMISSION",
            entity_id=admission.id,
            details=f"Admission {admission.admission_number} created"
        )

        db.commit()
        db.refresh(admission)

        return admission

    except Exception:
        db.rollback()
        raise

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


def discharge_admission(
    db: Session,
    admission_id: int,
    discharge_data: Any = None,
    discharged_by: int | None = None,
    discharge_summary: str | None = None,
):
    if discharge_data is not None:
        if hasattr(discharge_data, "discharged_by"):
            discharged_by = discharge_data.discharged_by
            discharge_summary = discharge_data.discharge_summary
        elif isinstance(discharge_data, int):
            discharged_by = discharge_data

    admission = db.get(Admission, admission_id)
    if admission is None:
        raise ValueError("Admission not found")

    if admission.status != "ACTIVE":
        raise ValueError(
            f"Admission is already discharged or inactive (status: {admission.status}) and cannot be discharged"
        )

    discharging_user = db.get(User, discharged_by)
    if discharging_user is None:
        raise ValueError("Discharging healthcare worker not found")

    if not discharging_user.is_active:
        raise ValueError("Discharging healthcare worker is inactive")

    if discharging_user.role not in ("DOCTOR", "ADMIN"):
        raise ValueError(
            f"User with role '{discharging_user.role}' cannot discharge patients. Only DOCTOR or ADMIN can discharge."
        )

    clean_summary = discharge_summary.strip() if discharge_summary else ""
    if not clean_summary:
        raise ValueError("Discharge summary cannot be empty")

    try:
        admission.status = "DISCHARGED"
        admission.discharged_at = datetime.now(timezone.utc)
        admission.discharge_summary = clean_summary
        admission.discharged_by = discharged_by

        # Free the allocated bed so it becomes available for new admissions
        bed = db.get(Bed, admission.bed_id)
        if bed:
            bed.status = "AVAILABLE"

        create_audit_log(
            db,
            user_id=discharged_by,
            action="DISCHARGE",
            entity_type="ADMISSION",
            entity_id=admission.id,
            details=f"Admission {admission.admission_number} discharged with summary",
        )
        db.commit()
        db.refresh(admission)
        return admission
    except Exception:
        db.rollback()
        raise


def get_admissions_by_patient(
    db: Session,
    patient_id: int,
):
    result = db.execute(
        select(Admission)
        .where(Admission.patient_id == patient_id)
        .order_by(Admission.admitted_at.desc())
    )
    return result.scalars().all()