from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.audit.service import create_audit_log
from app.investigations.models import InvestigationOrder, InvestigationResult
from app.investigations.schemas import InvestigationOrderCreate, InvestigationResultCreate
from app.users.models import User


def create_investigation_order(
    db: Session,
    order_data: InvestigationOrderCreate,
) -> InvestigationOrder:
    admission = db.get(Admission, order_data.admission_id)
    if admission is None:
        raise ValueError("Admission not found")

    if admission.status != "ACTIVE":
        raise ValueError("Cannot order investigations for an inactive admission")

    user = db.get(User, order_data.ordered_by)
    if user is None:
        raise ValueError("Ordering healthcare worker not found")

    if not user.is_active:
        raise ValueError("Ordering healthcare worker is inactive")

    if user.role not in ("DOCTOR", "ADMIN"):
        raise ValueError(
            f"User with role '{user.role}' cannot order investigations. Only DOCTOR or ADMIN can order investigations."
        )

    order = InvestigationOrder(
        admission_id=order_data.admission_id,
        test_name=order_data.test_name,
        category=order_data.category,
        ordered_by=order_data.ordered_by,
        ordered_at=datetime.now(timezone.utc),
        urgency=order_data.urgency,
        clinical_indication=order_data.clinical_indication,
        status="ORDERED",
    )

    try:
        db.add(order)
        db.flush()

        create_audit_log(
            db,
            user_id=order.ordered_by,
            action="ORDER",
            entity_type="INVESTIGATION",
            entity_id=order.id,
            details=f"Investigation order {order.test_name} ({order.urgency}) created for admission {order.admission_id}",
        )

        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def record_investigation_result(
    db: Session,
    result_data: InvestigationResultCreate,
) -> InvestigationResult:
    order = db.get(InvestigationOrder, result_data.investigation_order_id)
    if order is None:
        raise ValueError("Investigation order not found")

    if order.status == "CANCELLED":
        raise ValueError("Cannot record results for a cancelled investigation order")

    user = db.get(User, result_data.recorded_by)
    if user is None:
        raise ValueError("Recording healthcare worker not found")

    if not user.is_active:
        raise ValueError("Recording healthcare worker is inactive")

    allowed_roles = ("LABORATORY_STAFF", "LAB_TECH", "DOCTOR", "ADMIN")
    if user.role not in allowed_roles:
        raise ValueError(
            f"User with role '{user.role}' cannot record investigation results. Only laboratory staff or doctor can record results."
        )

    result = InvestigationResult(
        investigation_order_id=result_data.investigation_order_id,
        recorded_by=result_data.recorded_by,
        recorded_at=datetime.now(timezone.utc),
        result_value=result_data.result_value,
        reference_range=result_data.reference_range,
        is_abnormal=result_data.is_abnormal,
        critical_alert=result_data.critical_alert,
        notes=result_data.notes,
    )

    try:
        db.add(result)
        order.status = "COMPLETED"
        db.flush()

        alert_str = " [CRITICAL ALERT]" if result.critical_alert else ""
        create_audit_log(
            db,
            user_id=result.recorded_by,
            action="RESULT",
            entity_type="INVESTIGATION",
            entity_id=order.id,
            details=f"Result recorded for {order.test_name}: {result.result_value}{alert_str}",
        )

        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise


def get_investigations_by_admission(
    db: Session,
    admission_id: int,
) -> list[InvestigationOrder]:
    admission = db.get(Admission, admission_id)
    if admission is None:
        raise ValueError("Admission not found")

    stmt = (
        select(InvestigationOrder)
        .where(InvestigationOrder.admission_id == admission_id)
        .order_by(InvestigationOrder.ordered_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_late_investigations(
    db: Session,
    routine_threshold_hours: int = 24,
    urgent_threshold_hours: int = 6,
    stat_threshold_hours: int = 2,
) -> list[dict]:
    """
    Surfaces pending investigation orders that have exceeded turnaround thresholds.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(InvestigationOrder)
        .where(InvestigationOrder.status.not_in(["COMPLETED", "CANCELLED"]))
        .order_by(InvestigationOrder.ordered_at.asc())
    )
    orders = db.execute(stmt).scalars().all()

    late_orders = []
    for order in orders:
        ordered_time = order.ordered_at
        if ordered_time.tzinfo is None:
            ordered_time = ordered_time.replace(tzinfo=timezone.utc)
        elapsed_hours = (now - ordered_time).total_seconds() / 3600.0

        if order.urgency == "STAT":
            threshold = stat_threshold_hours
        elif order.urgency == "URGENT":
            threshold = urgent_threshold_hours
        else:
            threshold = routine_threshold_hours

        if elapsed_hours >= threshold:
            late_orders.append({
                "order_id": order.id,
                "admission_id": order.admission_id,
                "test_name": order.test_name,
                "urgency": order.urgency,
                "ordered_at": order.ordered_at,
                "elapsed_hours": round(elapsed_hours, 1),
                "threshold_hours": threshold,
                "status": order.status,
            })

    return late_orders
