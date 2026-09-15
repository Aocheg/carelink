from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.audit.service import create_audit_log
from app.medications.models import MedicationOrder
from app.users.models import User


def create_medication_order(
    db: Session,
    medication_data,
):
    admission = db.get(
        Admission,
        medication_data.admission_id,
    )

    if admission is None:
        raise ValueError("Admission not found")

    user = db.get(
        User,
        medication_data.prescribed_by,
    )

    if user is None:
        raise ValueError(
            "Prescribing healthcare worker not found"
        )

    if not user.is_active:
        raise ValueError(
            "Prescribing healthcare worker is inactive"
        )

    medication_order = MedicationOrder(
        admission_id=medication_data.admission_id,
        medication_name=medication_data.medication_name,
        dose=medication_data.dose,
        route=medication_data.route,
        frequency=medication_data.frequency,
        start_date=medication_data.start_date,
        end_date=medication_data.end_date,
        prescribed_by=medication_data.prescribed_by,
        status=medication_data.status,
        instructions=medication_data.instructions,
    )

    try:
        db.add(medication_order)

        db.flush()

        create_audit_log(
            db,
            user_id=medication_order.prescribed_by,
            action="CREATE",
            entity_type="MEDICATION_ORDER",
            entity_id=medication_order.id,
            details=(
                f"Medication order "
                f"{medication_order.medication_name} "
                f"created for admission "
                f"{medication_order.admission_id}"
            ),
        )

        db.commit()

        db.refresh(medication_order)

        return medication_order

    except Exception:
        db.rollback()
        raise


def get_medication_orders_by_admission(
    db: Session,
    admission_id: int,
):
    admission = db.get(
        Admission,
        admission_id,
    )

    if admission is None:
        raise ValueError("Admission not found")

    result = db.execute(
        select(MedicationOrder)
        .where(
            MedicationOrder.admission_id == admission_id
        )
        .order_by(MedicationOrder.id)
    )

    return result.scalars().all()


def get_medication_order_by_id(
    db: Session,
    medication_order_id: int,
):
    result = db.execute(
        select(MedicationOrder)
        .where(
            MedicationOrder.id == medication_order_id
        )
    )

    return result.scalar_one_or_none()