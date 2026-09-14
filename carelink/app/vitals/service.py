from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.audit.service import create_audit_log
from app.users.models import User
from app.vitals.models import VitalSign


def create_vital_sign(db: Session, vital_data):
    admission = db.get(Admission, vital_data.admission_id)

    if admission is None:
        raise ValueError("Admission not found")

    user = db.get(User, vital_data.recorded_by)

    if user is None:
        raise ValueError("Recording healthcare worker not found")

    if not user.is_active:
        raise ValueError("Recording healthcare worker is inactive")

    recorded_at = vital_data.recorded_at

    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc)

    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)

    recorded_at = recorded_at.astimezone(timezone.utc)

    measurements = [
        vital_data.systolic_bp,
        vital_data.diastolic_bp,
        vital_data.pulse,
        vital_data.temperature,
        vital_data.respiratory_rate,
        vital_data.spo2,
    ]

    measured_count = sum(
        value is not None for value in measurements
    )

    if (vital_data.systolic_bp is None) != (
        vital_data.diastolic_bp is None
    ):
        raise ValueError(
            "Systolic and diastolic blood pressure must be recorded together"
        )

    if vital_data.measurement_status == "COMPLETE":
        if measured_count != 6:
            raise ValueError(
                "COMPLETE measurements require all vital-sign values"
            )

        if vital_data.not_measured_reason:
            raise ValueError(
                "not_measured_reason must be empty for COMPLETE measurements"
            )

    elif vital_data.measurement_status == "PARTIAL":
        if measured_count == 0:
            raise ValueError(
                "PARTIAL measurements require at least one vital-sign value"
            )

        if measured_count == 6:
            raise ValueError(
                "PARTIAL measurements must have at least one missing vital-sign value"
            )

        if not vital_data.not_measured_reason:
            raise ValueError(
                "not_measured_reason is required for PARTIAL measurements"
            )

    elif vital_data.measurement_status == "NOT_MEASURED":
        if measured_count != 0:
            raise ValueError(
                "NOT_MEASURED records cannot contain vital-sign values"
            )

        if not vital_data.not_measured_reason:
            raise ValueError(
                "not_measured_reason is required for NOT_MEASURED measurements"
            )

    vital_sign = VitalSign(
        admission_id=vital_data.admission_id,
        recorded_by=vital_data.recorded_by,
        recorded_at=recorded_at,
        systolic_bp=vital_data.systolic_bp,
        diastolic_bp=vital_data.diastolic_bp,
        pulse=vital_data.pulse,
        temperature=vital_data.temperature,
        respiratory_rate=vital_data.respiratory_rate,
        spo2=vital_data.spo2,
        measurement_status=vital_data.measurement_status,
        not_measured_reason=vital_data.not_measured_reason,
        notes=vital_data.notes,
    )

    try:
        db.add(vital_sign)
        db.flush()

        create_audit_log(
            db,
            user_id=vital_sign.recorded_by,
            action="CREATE",
            entity_type="VITAL_SIGN",
            entity_id=vital_sign.id,
            details=(
                f"Vital-sign record created for admission "
                f"{vital_sign.admission_id}"
            ),
        )

        db.commit()
        db.refresh(vital_sign)

        return vital_sign

    except Exception:
        db.rollback()
        raise


def get_vital_signs_by_admission(
    db: Session,
    admission_id: int,
):
    admission = db.get(Admission, admission_id)

    if admission is None:
        raise ValueError("Admission not found")

    result = db.execute(
        select(VitalSign)
        .where(VitalSign.admission_id == admission_id)
        .order_by(VitalSign.recorded_at)
    )

    return result.scalars().all()


def get_vital_sign_by_id(
    db: Session,
    vital_sign_id: int,
):
    result = db.execute(
        select(VitalSign)
        .where(VitalSign.id == vital_sign_id)
    )

    return result.scalar_one_or_none()