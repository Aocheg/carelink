from datetime import date, datetime, timedelta, timezone
import pytest

from app.admissions.models import Admission
from app.admissions.schemas import AdmissionCreate, AdmissionDischarge
from app.admissions.service import create_admission, discharge_admission
from app.clinical.alerts import calculate_news2_score, evaluate_clinical_alerts
from app.clinical.models import ClinicalNote
from app.clinical.schemas import ClinicalNoteCreate
from app.clinical.service import (
    create_clinical_note,
    generate_handover_summary,
    get_admission_alerts,
    get_clinical_notes_by_admission,
    get_unified_clinical_timeline,
)
from app.facilities.models import Facility
from app.facilities.schemas import FacilityCreate
from app.facilities.service import create_facility
from app.investigations.models import InvestigationOrder, InvestigationResult
from app.investigations.schemas import InvestigationOrderCreate, InvestigationResultCreate
from app.investigations.service import (
    create_investigation_order,
    get_late_investigations,
    record_investigation_result,
)
from app.medications.models import MedicationOrder
from app.medications.schemas import (
    MedicationAdministrationCreate,
    MedicationOrderCreate,
    MedicationOrderDiscontinue,
)
from app.medications.service import (
    create_medication_administration,
    create_medication_order,
    discontinue_medication_order,
)
from app.patients.models import Patient
from app.patients.schemas import PatientCreate
from app.patients.service import create_patient
from app.users.models import User
from app.users.service import create_user
from app.vitals.models import VitalSign
from app.vitals.schemas import VitalSignCreate
from app.vitals.service import create_vital_sign, get_vital_signs_by_admission
from app.wards.models import Bed, Ward
from app.wards.schemas import BedCreate, WardCreate
from app.wards.service import create_bed, create_ward


# Fixture helpers
def setup_clinical_environment(db):
    patient = create_patient(
        db,
        PatientCreate(
            full_name="Eleanor Vance",
            date_of_birth="1985-04-12",
            sex="Female",
            allergy_status="Penicillin",
            allergy_details="Anaphylaxis rash and bronchospasm",
        ),
    )

    facility = create_facility(
        db,
        FacilityCreate(name="St. Jude Regional Hospital"),
    )

    ward = create_ward(
        db,
        WardCreate(facility_id=facility.id, name="Acute Medical Unit"),
    )

    bed = create_bed(
        db,
        BedCreate(ward_id=ward.id, bed_number="AMU-01"),
    )

    doctor = create_user(
        db,
        username="dr.watson",
        full_name="Dr. John Watson",
        role="DOCTOR",
        password="SecurePassword123",
    )

    nurse = create_user(
        db,
        username="nurse.nightingale",
        full_name="Florence Nightingale",
        role="NURSE",
        password="SecurePassword123",
    )

    lab_tech = create_user(
        db,
        username="tech.curie",
        full_name="Marie Curie",
        role="LABORATORY_STAFF",
        password="SecurePassword123",
    )

    admission = create_admission(
        db,
        AdmissionCreate(
            patient_id=patient.id,
            ward_id=ward.id,
            bed_id=bed.id,
            source="Emergency Department",
            reason_for_admission="Severe community-acquired pneumonia with fever",
            presenting_complaint="Productive cough, chest pain, dyspnea for 3 days",
            admitted_by=doctor.id,
        ),
    )

    return {
        "patient": patient,
        "facility": facility,
        "ward": ward,
        "bed": bed,
        "doctor": doctor,
        "nurse": nurse,
        "lab_tech": lab_tech,
        "admission": admission,
    }


# ==========================================
# 1. Admissions & Bed Discharge Lifecycle
# ==========================================

def test_admission_discharge_frees_bed_and_preserves_history(db):
    env = setup_clinical_environment(db)
    bed = env["bed"]
    admission = env["admission"]
    doctor = env["doctor"]

    # Before discharge, bed is OCCUPIED
    db.refresh(bed)
    assert bed.status == "OCCUPIED"
    assert admission.status == "ACTIVE"

    # Execute discharge
    discharge_data = AdmissionDischarge(
        discharged_by=doctor.id,
        discharge_summary="Patient stabilized with oral amoxicillin course completed. Follow-up in 2 weeks.",
    )
    discharged_adm = discharge_admission(db, admission.id, discharge_data)

    assert discharged_adm.status == "DISCHARGED"
    assert discharged_adm.discharged_at is not None
    assert discharged_adm.discharge_summary == discharge_data.discharge_summary
    assert discharged_adm.discharged_by == doctor.id

    # Bed should now be AVAILABLE
    db.refresh(bed)
    assert bed.status == "AVAILABLE"

    # Historical admission data remains intact in DB
    reloaded = db.get(Admission, admission.id)
    assert reloaded.id == admission.id
    assert reloaded.reason_for_admission == "Severe community-acquired pneumonia with fever"


def test_cannot_discharge_already_discharged_admission(db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    doctor = env["doctor"]

    discharge_data = AdmissionDischarge(
        discharged_by=doctor.id,
        discharge_summary="Discharged home.",
    )
    discharge_admission(db, admission.id, discharge_data)

    # Attempt second discharge
    with pytest.raises(ValueError, match="already discharged"):
        discharge_admission(db, admission.id, discharge_data)


def test_non_doctor_cannot_discharge_admission(db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    nurse = env["nurse"]

    discharge_data = AdmissionDischarge(
        discharged_by=nurse.id,
        discharge_summary="Nurse trying to discharge.",
    )
    with pytest.raises(ValueError, match="Only DOCTOR or ADMIN can discharge"):
        discharge_admission(db, admission.id, discharge_data)


# ==========================================
# 2. Vital Signs Time-Series Immutability
# ==========================================

def test_vital_signs_preserves_history_without_overwriting(db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    nurse = env["nurse"]

    # Record reading 1 (Morning)
    v1 = create_vital_sign(
        db,
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=nurse.id,
            systolic_bp=120,
            diastolic_bp=80,
            pulse=72,
            temperature=37.0,
            respiratory_rate=16,
            spo2=98.0,
            measurement_status="COMPLETE",
        ),
    )

    # Record reading 2 (Afternoon - deteriorated)
    v2 = create_vital_sign(
        db,
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=nurse.id,
            systolic_bp=95,
            diastolic_bp=60,
            pulse=115,
            temperature=39.2,
            respiratory_rate=24,
            spo2=91.0,
            measurement_status="COMPLETE",
        ),
    )

    # Record reading 3 (Evening - stabilized)
    v3 = create_vital_sign(
        db,
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=nurse.id,
            systolic_bp=118,
            diastolic_bp=76,
            pulse=80,
            temperature=37.4,
            respiratory_rate=18,
            spo2=97.0,
            measurement_status="COMPLETE",
        ),
    )

    history = get_vital_signs_by_admission(db, admission.id)
    assert len(history) == 3
    # Both old and new readings are preserved with their distinct IDs and values
    ids = [v.id for v in history]
    assert v1.id in ids and v2.id in ids and v3.id in ids
    assert any(v.temperature == 39.2 for v in history)
    assert any(v.temperature == 37.0 for v in history)
    assert any(v.temperature == 37.4 for v in history)


# ==========================================
# 3. Medication Discontinuation & Administration
# ==========================================

def test_medication_order_administration_and_discontinuation(db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    doctor = env["doctor"]
    nurse = env["nurse"]

    order = create_medication_order(
        db,
        MedicationOrderCreate(
            admission_id=admission.id,
            medication_name="Ceftriaxone",
            dose="1g",
            route="IV",
            frequency="Once daily",
            start_date=date.today(),
            prescribed_by=doctor.id,
            instructions="Slow IV infusion over 30 mins",
        ),
    )
    assert order.status == "ACTIVE"

    # Administration: ADMINISTERED
    admin1 = create_medication_administration(
        db,
        MedicationAdministrationCreate(
            medication_order_id=order.id,
            administered_by=nurse.id,
            status="ADMINISTERED",
            notes="Dose given without complications.",
        ),
    )
    assert admin1.status == "ADMINISTERED"

    # Administration: REFUSED
    admin2 = create_medication_administration(
        db,
        MedicationAdministrationCreate(
            medication_order_id=order.id,
            administered_by=nurse.id,
            status="REFUSED",
            not_administered_reason="Patient felt nauseated and declined dose.",
        ),
    )
    assert admin2.status == "REFUSED"

    # Doctor discontinues medication order
    discontinued = discontinue_medication_order(
        db,
        order.id,
        MedicationOrderDiscontinue(
            discontinued_by=doctor.id,
            reason="Patient developed suspected allergic reaction; switched to oral azithromycin.",
        ),
    )
    assert discontinued.status == "DISCONTINUED"

    # Nurse cannot discontinue medication
    order2 = create_medication_order(
        db,
        MedicationOrderCreate(
            admission_id=admission.id,
            medication_name="Paracetamol",
            dose="1g",
            route="Oral",
            frequency="TDS PRN",
            start_date=date.today(),
            prescribed_by=doctor.id,
        ),
    )
    with pytest.raises(ValueError, match="Only DOCTOR or ADMIN"):
        discontinue_medication_order(
            db,
            order2.id,
            MedicationOrderDiscontinue(
                discontinued_by=nurse.id,
                reason="Nurse attempt to discontinue",
            ),
        )


# ==========================================
# 4. Investigations Orders & Results
# ==========================================

def test_investigation_order_and_result_workflow(db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    doctor = env["doctor"]
    lab_tech = env["lab_tech"]
    nurse = env["nurse"]

    # Doctor orders STAT lab
    order = create_investigation_order(
        db,
        InvestigationOrderCreate(
            admission_id=admission.id,
            test_name="Serum Potassium",
            category="BIOCHEMISTRY",
            ordered_by=doctor.id,
            urgency="STAT",
            clinical_indication="Suspected hypokalemia / cardiac arrhythmia risk",
        ),
    )
    assert order.status == "ORDERED"
    assert order.urgency == "STAT"

    # Non-doctor cannot order investigations
    with pytest.raises(ValueError, match="cannot order investigations"):
        create_investigation_order(
            db,
            InvestigationOrderCreate(
                admission_id=admission.id,
                test_name="Full Blood Count",
                category="HEMATOLOGY",
                ordered_by=nurse.id,
            ),
        )

    # Lab Tech records result with critical alert
    res = record_investigation_result(
        db,
        InvestigationResultCreate(
            investigation_order_id=order.id,
            recorded_by=lab_tech.id,
            result_value="2.4 mmol/L",
            reference_range="3.5 - 5.0 mmol/L",
            is_abnormal=True,
            critical_alert=True,
            notes="Phoned directly to primary ward nurse immediately.",
        ),
    )
    assert res.critical_alert is True
    assert res.is_abnormal is True

    # Order status transitions to COMPLETED
    db.refresh(order)
    assert order.status == "COMPLETED"


def test_late_investigations_surfacing(db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    doctor = env["doctor"]

    order = create_investigation_order(
        db,
        InvestigationOrderCreate(
            admission_id=admission.id,
            test_name="Blood Cultures",
            category="MICROBIOLOGY",
            ordered_by=doctor.id,
            urgency="URGENT",
        ),
    )

    # Artificially age the ordered_at timestamp to 8 hours ago
    order.ordered_at = datetime.now(timezone.utc) - timedelta(hours=8)
    db.commit()

    late_list = get_late_investigations(db, urgent_threshold_hours=6)
    order_ids = [item["order_id"] for item in late_list]
    assert order.id in order_ids
    found = next(item for item in late_list if item["order_id"] == order.id)
    assert found["urgency"] == "URGENT"
    assert found["elapsed_hours"] >= 8.0


# ==========================================
# 5. Clinical Documentation (Notes & Reviews)
# ==========================================

def test_doctor_review_and_nursing_notes_recording(db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    doctor = env["doctor"]
    nurse = env["nurse"]

    # Doctor records review
    doc_note = create_clinical_note(
        db,
        ClinicalNoteCreate(
            admission_id=admission.id,
            author_id=doctor.id,
            note_type="DOCTOR_REVIEW",
            content="Chest clear on right side, bibasilar crackles resolving on left. Alert and oriented.",
            plan="Step down oxygen to 2L via nasal cannula. Repeat CRP in 48h.",
        ),
    )
    assert doc_note.id is not None
    assert doc_note.note_type == "DOCTOR_REVIEW"

    # Nurse cannot record DOCTOR_REVIEW
    with pytest.raises(ValueError, match="Only DOCTOR or ADMIN can record doctor reviews"):
        create_clinical_note(
            db,
            ClinicalNoteCreate(
                admission_id=admission.id,
                author_id=nurse.id,
                note_type="DOCTOR_REVIEW",
                content="Nurse attempt to do doctor review",
            ),
        )

    # Nurse records nursing assessment and note
    nurse_note = create_clinical_note(
        db,
        ClinicalNoteCreate(
            admission_id=admission.id,
            author_id=nurse.id,
            note_type="NURSING_NOTE",
            content="Patient tolerated light lunch well. Mobilized with assist of 1 to chair.",
            plan="Monitor vital signs 4-hourly.",
        ),
    )
    assert nurse_note.id is not None

    notes = get_clinical_notes_by_admission(db, admission.id)
    assert len(notes) == 2

    doc_only = get_clinical_notes_by_admission(db, admission.id, note_type="DOCTOR_REVIEW")
    assert len(doc_only) == 1
    assert doc_only[0].author_id == doctor.id


# ==========================================
# 6. Handover Summary Generation
# ==========================================

def test_handover_summary_generation(db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    doctor = env["doctor"]
    nurse = env["nurse"]

    # Add vital sign
    create_vital_sign(
        db,
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=nurse.id,
            systolic_bp=110,
            diastolic_bp=70,
            pulse=88,
            temperature=37.2,
            respiratory_rate=18,
            spo2=96.0,
        ),
    )

    # Add active med
    create_medication_order(
        db,
        MedicationOrderCreate(
            admission_id=admission.id,
            medication_name="Amoxicillin-Clavulanate",
            dose="625mg",
            route="Oral",
            frequency="TDS",
            start_date=date.today(),
            prescribed_by=doctor.id,
        ),
    )

    # Add doctor review
    create_clinical_note(
        db,
        ClinicalNoteCreate(
            admission_id=admission.id,
            author_id=doctor.id,
            note_type="DOCTOR_REVIEW",
            content="Improving clinically. Continue current antibiotics.",
        ),
    )

    # Add pending investigation
    create_investigation_order(
        db,
        InvestigationOrderCreate(
            admission_id=admission.id,
            test_name="C-Reactive Protein (CRP)",
            category="BIOCHEMISTRY",
            ordered_by=doctor.id,
            urgency="ROUTINE",
        ),
    )

    summary = generate_handover_summary(db, admission.id)

    assert summary["admission_id"] == admission.id
    assert summary["patient_name"] == "Eleanor Vance"
    assert summary["allergy_status"] == "Penicillin"
    assert summary["ward_name"] == "Acute Medical Unit"
    assert summary["bed_number"] == "AMU-01"
    assert summary["news2_score"] is not None
    assert len(summary["active_medications"]) == 1
    assert summary["active_medications"][0]["medication_name"] == "Amoxicillin-Clavulanate"
    assert summary["latest_doctor_review"] is not None
    assert "Improving clinically" in summary["latest_doctor_review"]["content"]
    assert len(summary["pending_investigations"]) == 1
    assert summary["pending_investigations"][0]["test_name"] == "C-Reactive Protein (CRP)"


# ==========================================
# 7. Unified Clinical Chronological Timeline
# ==========================================

def test_unified_clinical_timeline_chronological_order(db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    doctor = env["doctor"]
    nurse = env["nurse"]

    # 1. Observation
    create_vital_sign(
        db,
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=nurse.id,
            systolic_bp=125,
            diastolic_bp=82,
            pulse=75,
            temperature=36.8,
            respiratory_rate=16,
            spo2=98.0,
        ),
    )

    # 2. Medication Order
    order = create_medication_order(
        db,
        MedicationOrderCreate(
            admission_id=admission.id,
            medication_name="Salbutamol Inhaler",
            dose="100mcg",
            route="Inhaled",
            frequency="PRN",
            start_date=date.today(),
            prescribed_by=doctor.id,
        ),
    )

    # 3. Clinical Note
    create_clinical_note(
        db,
        ClinicalNoteCreate(
            admission_id=admission.id,
            author_id=doctor.id,
            note_type="DOCTOR_REVIEW",
            content="Patient feels relief after bronchodilator.",
        ),
    )

    # 4. Discharge
    discharge_admission(
        db,
        admission.id,
        AdmissionDischarge(
            discharged_by=doctor.id,
            discharge_summary="Safe for discharge.",
        ),
    )

    timeline = get_unified_clinical_timeline(db, admission.id)

    assert len(timeline) >= 5
    event_types = [e["event_type"] for e in timeline]
    assert "ADMISSION" in event_types
    assert "VITAL_SIGNS" in event_types
    assert "MEDICATION_ORDER" in event_types
    assert "DOCTOR_REVIEW" in event_types
    assert "DISCHARGE" in event_types

    # Ensure strictly sorted chronologically
    timestamps = [e["timestamp"] for e in timeline]
    for i in range(len(timestamps) - 1):
        t1 = timestamps[i].replace(tzinfo=timezone.utc) if timestamps[i].tzinfo is None else timestamps[i]
        t2 = timestamps[i + 1].replace(tzinfo=timezone.utc) if timestamps[i + 1].tzinfo is None else timestamps[i + 1]
        assert t1 <= t2


# ==========================================
# 8. Deterministic NEWS2 & Safety Alerts
# ==========================================

class DummyVitals:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_deterministic_news2_score_calculations():
    # Completely normal vitals: score 0
    normal = DummyVitals(
        respiratory_rate=16,
        spo2=98.0,
        systolic_bp=120,
        pulse=70,
        temperature=37.0,
    )
    assert calculate_news2_score(normal) == 0

    # Severe deterioration:
    # RR=28 (+3), SpO2=88% (+3), Systolic BP=85 (+3), Pulse=135 (+3), Temp=34.5 (+3) -> total 15
    critical = DummyVitals(
        respiratory_rate=28,
        spo2=88.0,
        systolic_bp=85,
        pulse=135,
        temperature=34.5,
    )
    assert calculate_news2_score(critical) == 15

    # Moderate physiological derangement
    moderate = DummyVitals(
        respiratory_rate=22,  # +2
        spo2=93.0,            # +2
        systolic_bp=98,       # +2
        pulse=115,            # +2
        temperature=38.5,     # +1
    )
    assert calculate_news2_score(moderate) == 9


def test_deterministic_clinical_alerts_red_flags():
    # Hypotension alert
    hypo = DummyVitals(systolic_bp=82, diastolic_bp=50)
    alerts = evaluate_clinical_alerts(hypo)
    assert any(a["parameter"] == "BLOOD_PRESSURE" and a["severity"] == "CRITICAL" for a in alerts)

    # Hypertensive emergency alert
    hypert = DummyVitals(systolic_bp=195, diastolic_bp=125)
    alerts = evaluate_clinical_alerts(hypert)
    assert any(a["parameter"] == "BLOOD_PRESSURE" and a["severity"] == "CRITICAL" for a in alerts)

    # Hypoxia alert
    hypoxia = DummyVitals(spo2=86.0)
    alerts = evaluate_clinical_alerts(hypoxia)
    assert any(a["parameter"] == "SPO2" and a["severity"] == "CRITICAL" for a in alerts)

    # Severe bradycardia
    brady = DummyVitals(pulse=38)
    alerts = evaluate_clinical_alerts(brady)
    assert any(a["parameter"] == "PULSE" and a["severity"] == "CRITICAL" for a in alerts)

    # Fever
    fever = DummyVitals(temperature=39.5)
    alerts = evaluate_clinical_alerts(fever)
    assert any(a["parameter"] == "TEMPERATURE" and a["severity"] == "WARNING" for a in alerts)


# ==========================================
# 9. API HTTP Endpoints Integration
# ==========================================

def test_clinical_routes_via_client(client, db):
    env = setup_clinical_environment(db)
    admission = env["admission"]
    doctor = env["doctor"]

    # 1. Post clinical note
    note_resp = client.post(
        "/clinical/notes",
        json={
            "admission_id": admission.id,
            "author_id": doctor.id,
            "note_type": "DOCTOR_REVIEW",
            "content": "Patient improving on ward round.",
            "plan": "Discharge tomorrow morning.",
        },
    )
    assert note_resp.status_code == 201
    note_data = note_resp.json()
    assert note_data["note_type"] == "DOCTOR_REVIEW"

    # 2. Get handover summary
    handover_resp = client.get(f"/clinical/handover/{admission.id}")
    assert handover_resp.status_code == 200
    handover_data = handover_resp.json()
    assert handover_data["admission_id"] == admission.id
    assert handover_data["patient_name"] == "Eleanor Vance"

    # 3. Get timeline
    timeline_resp = client.get(f"/clinical/timeline/{admission.id}")
    assert timeline_resp.status_code == 200
    timeline_data = timeline_resp.json()
    assert len(timeline_data) >= 2  # Admission + Note

    # 4. Get alerts
    alerts_resp = client.get(f"/clinical/alerts/{admission.id}")
    assert alerts_resp.status_code == 200
    assert alerts_resp.json()["admission_id"] == admission.id

    # 5. Discharge via endpoint
    discharge_resp = client.post(
        f"/admissions/{admission.id}/discharge",
        json={
            "discharged_by": doctor.id,
            "discharge_summary": "Discharged home in stable condition.",
        },
    )
    assert discharge_resp.status_code == 200
    assert discharge_resp.json()["status"] == "DISCHARGED"
