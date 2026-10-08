from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.audit.service import create_audit_log
from app.clinical.alerts import calculate_news2_score, evaluate_clinical_alerts
from app.clinical.models import ClinicalNote
from app.clinical.schemas import ClinicalNoteCreate
from app.investigations.models import InvestigationOrder, InvestigationResult
from app.medications.models import MedicationAdministration, MedicationOrder
from app.patients.models import Patient
from app.users.models import User
from app.vitals.models import VitalSign
from app.wards.models import Bed, Ward


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_clinical_note(
    db: Session,
    note_data: ClinicalNoteCreate,
) -> ClinicalNote:
    admission = db.get(Admission, note_data.admission_id)
    if admission is None:
        raise ValueError("Admission not found")

    if admission.status != "ACTIVE":
        raise ValueError("Cannot add clinical notes to an inactive admission")

    author = db.get(User, note_data.author_id)
    if author is None:
        raise ValueError("Author not found")

    if not author.is_active:
        raise ValueError("Author is inactive")

    # Role validation
    if note_data.note_type == "DOCTOR_REVIEW":
        if author.role not in ("DOCTOR", "ADMIN"):
            raise ValueError(
                f"User with role '{author.role}' cannot record doctor reviews. "
                "Only DOCTOR or ADMIN can record doctor reviews."
            )
    else:
        # NURSING_ASSESSMENT, NURSING_DIAGNOSIS, NURSING_NOTE, HANDOVER_NOTE
        if author.role not in ("NURSE", "DOCTOR", "ADMIN"):
            raise ValueError(
                f"User with role '{author.role}' cannot record {note_data.note_type.lower().replace('_', ' ')}. "
                "Only NURSE, DOCTOR, or ADMIN can record this note."
            )

    note = ClinicalNote(
        admission_id=note_data.admission_id,
        author_id=note_data.author_id,
        note_type=note_data.note_type,
        content=note_data.content,
        plan=note_data.plan,
        created_at=datetime.now(timezone.utc),
    )

    try:
        db.add(note)
        db.flush()

        create_audit_log(
            db,
            user_id=note.author_id,
            action="CREATE",
            entity_type="CLINICAL_NOTE",
            entity_id=note.id,
            details=f"Clinical note {note.note_type} created for admission {note.admission_id}",
        )

        db.commit()
        db.refresh(note)
        return note
    except Exception:
        db.rollback()
        raise


def get_clinical_notes_by_admission(
    db: Session,
    admission_id: int,
    note_type: str | None = None,
) -> list[ClinicalNote]:
    admission = db.get(Admission, admission_id)
    if admission is None:
        raise ValueError("Admission not found")

    stmt = select(ClinicalNote).where(ClinicalNote.admission_id == admission_id)
    if note_type:
        stmt = stmt.where(ClinicalNote.note_type == note_type.strip().upper())

    stmt = stmt.order_by(ClinicalNote.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def generate_handover_summary(
    db: Session,
    admission_id: int,
) -> dict[str, Any]:
    admission = db.get(Admission, admission_id)
    if admission is None:
        raise ValueError("Admission not found")

    patient = db.get(Patient, admission.patient_id)
    ward = db.get(Ward, admission.ward_id)
    bed = db.get(Bed, admission.bed_id)

    # Length of stay
    admitted_dt = _ensure_utc(admission.admitted_at)
    now_dt = datetime.now(timezone.utc)
    ref_dt = _ensure_utc(admission.discharged_at) if admission.discharged_at else now_dt
    length_of_stay_days = max(0, (ref_dt.date() - admitted_dt.date()).days)

    # Patient age
    age_years = None
    if patient and patient.date_of_birth:
        today = now_dt.date()
        dob = patient.date_of_birth
        age_years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    # Latest vitals
    vitals_stmt = (
        select(VitalSign)
        .where(VitalSign.admission_id == admission_id)
        .order_by(VitalSign.recorded_at.desc())
    )
    latest_vital = db.execute(vitals_stmt).scalars().first()

    latest_vitals_dict = None
    news2_score = None
    clinical_alerts: list[dict] = []

    if latest_vital:
        news2_score = calculate_news2_score(latest_vital)
        clinical_alerts = evaluate_clinical_alerts(latest_vital)
        latest_vitals_dict = {
            "recorded_at": latest_vital.recorded_at,
            "systolic_bp": latest_vital.systolic_bp,
            "diastolic_bp": latest_vital.diastolic_bp,
            "pulse": latest_vital.pulse,
            "temperature": latest_vital.temperature,
            "respiratory_rate": latest_vital.respiratory_rate,
            "spo2": latest_vital.spo2,
            "measurement_status": latest_vital.measurement_status,
        }

    # Active medications
    meds_stmt = select(MedicationOrder).where(
        MedicationOrder.admission_id == admission_id,
        MedicationOrder.status == "ACTIVE",
    )
    active_meds = db.execute(meds_stmt).scalars().all()
    active_meds_list = [
        {
            "id": m.id,
            "medication_name": m.medication_name,
            "dose": m.dose,
            "route": m.route,
            "frequency": m.frequency,
            "instructions": m.instructions,
            "start_date": m.start_date.isoformat() if m.start_date else None,
        }
        for m in active_meds
    ]

    # Latest doctor review
    doc_stmt = (
        select(ClinicalNote)
        .where(
            ClinicalNote.admission_id == admission_id,
            ClinicalNote.note_type == "DOCTOR_REVIEW",
        )
        .order_by(ClinicalNote.created_at.desc())
    )
    latest_doc = db.execute(doc_stmt).scalars().first()
    latest_doc_dict = None
    if latest_doc:
        latest_doc_dict = {
            "id": latest_doc.id,
            "created_at": latest_doc.created_at,
            "author_id": latest_doc.author_id,
            "content": latest_doc.content,
            "plan": latest_doc.plan,
        }

    # Latest nursing note
    nurse_stmt = (
        select(ClinicalNote)
        .where(
            ClinicalNote.admission_id == admission_id,
            ClinicalNote.note_type.in_([
                "NURSING_NOTE",
                "NURSING_ASSESSMENT",
                "NURSING_DIAGNOSIS",
            ]),
        )
        .order_by(ClinicalNote.created_at.desc())
    )
    latest_nurse = db.execute(nurse_stmt).scalars().first()
    latest_nurse_dict = None
    if latest_nurse:
        latest_nurse_dict = {
            "id": latest_nurse.id,
            "note_type": latest_nurse.note_type,
            "created_at": latest_nurse.created_at,
            "author_id": latest_nurse.author_id,
            "content": latest_nurse.content,
            "plan": latest_nurse.plan,
        }

    # Pending investigations
    inv_stmt = (
        select(InvestigationOrder)
        .where(
            InvestigationOrder.admission_id == admission_id,
            InvestigationOrder.status.not_in(["COMPLETED", "CANCELLED"]),
        )
        .order_by(InvestigationOrder.ordered_at.desc())
    )
    pending_inv = db.execute(inv_stmt).scalars().all()
    pending_inv_list = [
        {
            "id": inv.id,
            "test_name": inv.test_name,
            "urgency": inv.urgency,
            "status": inv.status,
            "ordered_at": inv.ordered_at,
        }
        for inv in pending_inv
    ]

    return {
        "admission_id": admission.id,
        "admission_number": admission.admission_number,
        "patient_id": patient.id if patient else admission.patient_id,
        "patient_name": patient.full_name if patient else "Unknown",
        "patient_number": patient.patient_number if patient else "Unknown",
        "sex": patient.sex if patient and patient.sex else "Unknown",
        "age_years": age_years,
        "allergy_status": patient.allergy_status if patient else "UNKNOWN",
        "allergy_details": patient.allergy_details if patient else None,
        "ward_name": ward.name if ward else "Unknown Ward",
        "bed_number": bed.bed_number if bed else "Unknown Bed",
        "admitted_at": admission.admitted_at,
        "length_of_stay_days": length_of_stay_days,
        "admitting_reason": admission.reason_for_admission,
        "latest_vitals": latest_vitals_dict,
        "news2_score": news2_score,
        "clinical_alerts": clinical_alerts,
        "active_medications": active_meds_list,
        "latest_doctor_review": latest_doc_dict,
        "latest_nursing_note": latest_nurse_dict,
        "pending_investigations": pending_inv_list,
    }


def get_unified_clinical_timeline(
    db: Session,
    admission_id: int,
) -> list[dict[str, Any]]:
    admission = db.get(Admission, admission_id)
    if admission is None:
        raise ValueError("Admission not found")

    timeline: list[dict[str, Any]] = []

    # 1. Admission Event
    timeline.append({
        "event_type": "ADMISSION",
        "timestamp": admission.admitted_at,
        "title": "Patient Admitted",
        "description": f"Admitted via {admission.source}. Reason: {admission.reason_for_admission}",
        "recorded_by": admission.admitted_by,
        "metadata": {
            "ward_id": admission.ward_id,
            "bed_id": admission.bed_id,
            "source": admission.source,
        },
    })

    # 2. Discharge Event (if discharged)
    if admission.discharged_at:
        timeline.append({
            "event_type": "DISCHARGE",
            "timestamp": admission.discharged_at,
            "title": "Patient Discharged",
            "description": admission.discharge_summary or "Discharged from inpatient admission",
            "recorded_by": admission.discharged_by,
            "metadata": {},
        })

    # 3. Vital Signs Observations
    vitals_stmt = select(VitalSign).where(VitalSign.admission_id == admission_id)
    vitals_records = db.execute(vitals_stmt).scalars().all()
    for v in vitals_records:
        news2 = calculate_news2_score(v)
        alerts = evaluate_clinical_alerts(v)
        bp_str = f"{v.systolic_bp}/{v.diastolic_bp} mmHg" if v.systolic_bp else "N/A"
        desc = (
            f"BP: {bp_str}, HR: {v.pulse or '-'} bpm, Temp: {v.temperature or '-'}°C, "
            f"SpO2: {v.spo2 or '-'}%, RR: {v.respiratory_rate or '-'} (NEWS2: {news2})"
        )
        timeline.append({
            "event_type": "VITAL_SIGNS",
            "timestamp": v.recorded_at,
            "title": "Vital Signs Observation",
            "description": desc,
            "recorded_by": v.recorded_by,
            "metadata": {
                "news2_score": news2,
                "alerts": alerts,
                "measurement_status": v.measurement_status,
            },
        })

    # 4. Medication Orders
    meds_stmt = select(MedicationOrder).where(MedicationOrder.admission_id == admission_id)
    med_orders = db.execute(meds_stmt).scalars().all()
    med_order_ids = [m.id for m in med_orders]

    for m in med_orders:
        timeline.append({
            "event_type": "MEDICATION_ORDER",
            "timestamp": m.created_at,
            "title": f"Medication Ordered: {m.medication_name}",
            "description": f"{m.dose} via {m.route}, {m.frequency} (Status: {m.status})",
            "recorded_by": m.prescribed_by,
            "metadata": {
                "order_id": m.id,
                "status": m.status,
                "instructions": m.instructions,
            },
        })

    # 5. Medication Administrations
    if med_order_ids:
        admin_stmt = (
            select(MedicationAdministration, MedicationOrder.medication_name)
            .join(MedicationOrder, MedicationAdministration.medication_order_id == MedicationOrder.id)
            .where(MedicationAdministration.medication_order_id.in_(med_order_ids))
        )
        admins = db.execute(admin_stmt).all()
        for admin_record, med_name in admins:
            desc = f"Status: {admin_record.status}"
            if admin_record.not_administered_reason:
                desc += f" (Reason: {admin_record.not_administered_reason})"
            timeline.append({
                "event_type": "MEDICATION_ADMINISTRATION",
                "timestamp": admin_record.administered_at,
                "title": f"Medication Administered: {med_name}",
                "description": desc,
                "recorded_by": admin_record.administered_by,
                "metadata": {
                    "order_id": admin_record.medication_order_id,
                    "status": admin_record.status,
                    "notes": admin_record.notes,
                },
            })

    # 6. Investigation Orders and Results
    inv_stmt = select(InvestigationOrder).where(InvestigationOrder.admission_id == admission_id)
    inv_orders = db.execute(inv_stmt).scalars().all()
    for inv in inv_orders:
        timeline.append({
            "event_type": "INVESTIGATION_ORDER",
            "timestamp": inv.ordered_at,
            "title": f"Investigation Ordered: {inv.test_name}",
            "description": f"Urgency: {inv.urgency}, Category: {inv.category}, Status: {inv.status}",
            "recorded_by": inv.ordered_by,
            "metadata": {
                "order_id": inv.id,
                "urgency": inv.urgency,
                "category": inv.category,
            },
        })

        for res in inv.results:
            crit = " [CRITICAL ALERT]" if res.critical_alert else ""
            abn = " [ABNORMAL]" if res.is_abnormal else ""
            timeline.append({
                "event_type": "INVESTIGATION_RESULT",
                "timestamp": res.recorded_at,
                "title": f"Investigation Result: {inv.test_name}",
                "description": f"Value: {res.result_value}{crit}{abn}",
                "recorded_by": res.recorded_by,
                "metadata": {
                    "order_id": inv.id,
                    "result_id": res.id,
                    "critical_alert": res.critical_alert,
                    "is_abnormal": res.is_abnormal,
                    "reference_range": res.reference_range,
                },
            })

    # 7. Clinical Notes
    notes_stmt = select(ClinicalNote).where(ClinicalNote.admission_id == admission_id)
    notes = db.execute(notes_stmt).scalars().all()
    for note in notes:
        plan_str = f" | Plan: {note.plan}" if note.plan else ""
        timeline.append({
            "event_type": note.note_type,
            "timestamp": note.created_at,
            "title": f"Clinical Note: {note.note_type.replace('_', ' ').title()}",
            "description": f"{note.content}{plan_str}",
            "recorded_by": note.author_id,
            "metadata": {
                "note_id": note.id,
                "plan": note.plan,
            },
        })

    # Sort strictly chronologically by timestamp
    timeline.sort(key=lambda event: _ensure_utc(event["timestamp"]))
    return timeline


def get_admission_alerts(
    db: Session,
    admission_id: int,
) -> dict[str, Any]:
    admission = db.get(Admission, admission_id)
    if admission is None:
        raise ValueError("Admission not found")

    # Latest vitals
    vitals_stmt = (
        select(VitalSign)
        .where(VitalSign.admission_id == admission_id)
        .order_by(VitalSign.recorded_at.desc())
    )
    latest_vital = db.execute(vitals_stmt).scalars().first()

    news2_score = None
    vital_alerts: list[dict] = []
    if latest_vital:
        news2_score = calculate_news2_score(latest_vital)
        vital_alerts = evaluate_clinical_alerts(latest_vital)

    # Critical investigations
    critical_stmt = (
        select(InvestigationResult, InvestigationOrder.test_name)
        .join(InvestigationOrder, InvestigationResult.investigation_order_id == InvestigationOrder.id)
        .where(
            InvestigationOrder.admission_id == admission_id,
            InvestigationResult.critical_alert == True,  # noqa: E712
        )
        .order_by(InvestigationResult.recorded_at.desc())
    )
    critical_rows = db.execute(critical_stmt).all()
    critical_labs = [
        {
            "order_id": res.investigation_order_id,
            "result_id": res.id,
            "test_name": test_name,
            "result_value": res.result_value,
            "reference_range": res.reference_range,
            "recorded_at": res.recorded_at,
        }
        for res, test_name in critical_rows
    ]

    return {
        "admission_id": admission.id,
        "admission_status": admission.status,
        "news2_score": news2_score,
        "vital_alerts": vital_alerts,
        "critical_lab_alerts": critical_labs,
    }
