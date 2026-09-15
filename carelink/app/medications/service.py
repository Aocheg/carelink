from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.audit.service import create_audit_log
from app.medications.models import (
    MedicationAdministration,
    MedicationOrder,
)
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

    if medication_data.status != "ACTIVE":
        raise ValueError(
            "New medication orders must have status ACTIVE"
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
        status="ACTIVE",
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


def create_medication_administration(
    db: Session,
    administration_data,
):
    medication_order = db.get(
        MedicationOrder,
        administration_data.medication_order_id,
    )

    if medication_order is None:
        raise ValueError("Medication order not found")

    if medication_order.status != "ACTIVE":
        raise ValueError(
            "Medication order is not active"
        )

    user = db.get(
        User,
        administration_data.administered_by,
    )

    if user is None:
        raise ValueError(
            "Administering healthcare worker not found"
        )

    if not user.is_active:
        raise ValueError(
            "Administering healthcare worker is inactive"
        )

    administration = MedicationAdministration(
        medication_order_id=(
            administration_data.medication_order_id
        ),
        administered_by=(
            administration_data.administered_by
        ),
        administered_at=(
            administration_data.administered_at
        ),
        status=administration_data.status,
        not_administered_reason=(
            administration_data.not_administered_reason
        ),
        notes=administration_data.notes,
    )

    try:
        db.add(administration)
        db.flush()

        create_audit_log(
            db,
            user_id=administration.administered_by,
            action="CREATE",
            entity_type="MEDICATION_ADMINISTRATION",
            entity_id=administration.id,
            details=(
                f"Medication administration recorded "
                f"for medication order "
                f"{administration.medication_order_id} "
                f"with status "
                f"{administration.status}"
            ),
        )

        db.commit()
        db.refresh(administration)
        return administration

    except Exception:
        db.rollback()
        raise


def get_medication_administration_by_id(
    db: Session,
    administration_id: int,
):
    result = db.execute(
        select(MedicationAdministration)
        .where(
            MedicationAdministration.id == administration_id
        )
    )

    return result.scalar_one_or_none()


def get_medication_administrations_by_order(
    db: Session,
    medication_order_id: int,
):
    medication_order = db.get(
        MedicationOrder,
        medication_order_id,
    )

    if medication_order is None:
        raise ValueError("Medication order not found")

    result = db.execute(
        select(MedicationAdministration)
        .where(
            MedicationAdministration.medication_order_id
            == medication_order_id
        )
        .order_by(MedicationAdministration.id)
    )

    return result.scalars().all()