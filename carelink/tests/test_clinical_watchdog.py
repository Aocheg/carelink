from datetime import date, datetime, timedelta, timezone
import pytest

from app.admissions.models import Admission
from app.audit.service import verify_audit_trail
from app.clinical.models import ClinicalNote
from app.clinical.watchdog import watchdog
from app.facilities.models import Facility
from app.investigations.models import InvestigationOrder
from app.patients.models import Patient
from app.users.models import User
from app.users.service import hash_password
from app.users.tokens import create_access_token
from app.vitals.models import VitalSign
from app.wards.models import Bed, Ward


@pytest.fixture(autouse=True)
def clean_watchdog_cache():
    watchdog.clear_cooldown_cache()
    yield
    watchdog.clear_cooldown_cache()


@pytest.fixture
def watchdog_fixture(db):
    facility = Facility(name="Abuja National Hospital", is_active=True)
    db.add(facility)
    db.commit()

    ward = Ward(facility_id=facility.id, name="Acute Medical Unit (AMU)", description="High Dependency Inpatient Bay")
    db.add(ward)
    db.commit()

    bed1 = Bed(ward_id=ward.id, bed_number="AMU-BED-01", status="OCCUPIED")
    bed2 = Bed(ward_id=ward.id, bed_number="AMU-BED-02", status="OCCUPIED")
    db.add_all([bed1, bed2])
    db.commit()

    doctor = User(
        username="dr.tunde",
        password_hash=hash_password("DoctorPass123!"),
        full_name="Dr. Tunde Bakare",
        role="DOCTOR",
        is_active=True,
    )
    nurse = User(
        username="nurse.chioma",
        password_hash=hash_password("NursePass123!"),
        full_name="Nurse Chioma Okon",
        role="NURSE",
        is_active=True,
    )
    lab_tech = User(
        username="lab.sani",
        password_hash=hash_password("LabPass123!"),
        full_name="MLS Sani Bello",
        role="LAB_TECHNICIAN",
        is_active=True,
    )
    db.add_all([doctor, nurse, lab_tech])
    db.commit()

    # Patient 1: Deteriorating vitals
    patient1 = Patient(
        patient_number="PAT-WD-001",
        full_name="Musa Danjuma",
        allergy_status="NO_KNOWN_ALLERGIES",
        date_of_birth=date(1975, 4, 12),
        sex="MALE",
    )
    # Patient 2: Overdue STAT lab
    patient2 = Patient(
        patient_number="PAT-WD-002",
        full_name="Amina Garba",
        allergy_status="NO_KNOWN_ALLERGIES",
        date_of_birth=date(1989, 9, 21),
        sex="FEMALE",
    )
    db.add_all([patient1, patient2])
    db.commit()

    now = datetime.now(timezone.utc)

    adm1 = Admission(
        admission_number="ADM-WD-001",
        patient_id=patient1.id,
        ward_id=ward.id,
        bed_id=bed1.id,
        admitted_by=doctor.id,
        admitted_at=now - timedelta(hours=3),
        source="EMERGENCY",
        reason_for_admission="Severe Dyspnea & Sepsis Evaluation",
        status="ACTIVE",
    )
    adm2 = Admission(
        admission_number="ADM-WD-002",
        patient_id=patient2.id,
        ward_id=ward.id,
        bed_id=bed2.id,
        admitted_by=doctor.id,
        admitted_at=now - timedelta(hours=14),  # Admitted > 12h ago
        source="EMERGENCY",
        reason_for_admission="Suspected Pulmonary Embolism",
        status="ACTIVE",
    )
    db.add_all([adm1, adm2])
    db.commit()

    return {
        "facility": facility,
        "ward": ward,
        "doctor": doctor,
        "nurse": nurse,
        "lab_tech": lab_tech,
        "patient1": patient1,
        "patient2": patient2,
        "adm1": adm1,
        "adm2": adm2,
    }


def test_watchdog_detects_news2_deterioration_and_chains_audit(watchdog_fixture, db):
    adm1 = watchdog_fixture["adm1"]
    doctor = watchdog_fixture["doctor"]

    # Critical vital sign: SpO2 88% (+3), Resp Rate 28 (+3), Pulse 135 (+3), Temp 39.5 (+2) -> Total NEWS2 = 11
    crit_vital = VitalSign(
        admission_id=adm1.id,
        recorded_by=doctor.id,
        recorded_at=datetime.now(timezone.utc),
        systolic_bp=88,  # +3
        diastolic_bp=55,
        pulse=135,       # +3
        respiratory_rate=28,  # +3
        temperature=39.5,     # +2
        spo2=88.0,            # +3
        measurement_status="COMPLETE",
    )
    db.add(crit_vital)
    db.commit()

    alerts = watchdog.scan_facility_safety(db, actor_id=doctor.id)
    news2_alerts = [a for a in alerts if a["alert_type"] == "CRITICAL_PHYSIOLOGICAL_DETERIORATION"]

    assert len(news2_alerts) >= 1
    alert = news2_alerts[0]
    assert alert["admission_id"] == adm1.id
    assert alert["severity"] == "CRITICAL"
    assert alert["news2_score"] >= 7
    assert len(alert["red_flags"]) >= 1

    # Verify SHA-256 chained audit trail integrity
    verification = verify_audit_trail(db)
    assert verification["status"] == "VALID"
    assert verification["tamper_detected"] is False
    assert verification["records_verified"] >= 1


def test_watchdog_anti_fatigue_debounce_cooldown(watchdog_fixture, db):
    adm1 = watchdog_fixture["adm1"]
    doctor = watchdog_fixture["doctor"]

    vital = VitalSign(
        admission_id=adm1.id,
        recorded_by=doctor.id,
        recorded_at=datetime.now(timezone.utc),
        systolic_bp=85,
        pulse=120,
        respiratory_rate=26,
        temperature=38.5,
        spo2=91.0,
        measurement_status="COMPLETE",
    )
    db.add(vital)
    db.commit()

    # First scan: alert triggered
    first_scan = watchdog.scan_facility_safety(db, actor_id=doctor.id)
    n1 = [a for a in first_scan if a["alert_type"] == "CRITICAL_PHYSIOLOGICAL_DETERIORATION"]
    assert len(n1) == 1

    # Second scan immediately: debounce suppresses alert
    second_scan = watchdog.scan_facility_safety(db, actor_id=doctor.id)
    n2 = [a for a in second_scan if a["alert_type"] == "CRITICAL_PHYSIOLOGICAL_DETERIORATION"]
    assert len(n2) == 0

    # Third scan with force_ignore_cooldown=True: alert re-triggers
    third_scan = watchdog.scan_facility_safety(db, actor_id=doctor.id, force_ignore_cooldown=True)
    n3 = [a for a in third_scan if a["alert_type"] == "CRITICAL_PHYSIOLOGICAL_DETERIORATION"]
    assert len(n3) == 1


def test_watchdog_detects_overdue_stat_lab_and_overdue_shift_review(watchdog_fixture, db):
    adm2 = watchdog_fixture["adm2"]
    doctor = watchdog_fixture["doctor"]

    # Overdue STAT order: ordered 90 minutes ago (> 60m SLA)
    order = InvestigationOrder(
        admission_id=adm2.id,
        test_name="D-Dimer Quantitative Assay",
        category="LABORATORY",
        ordered_by=doctor.id,
        ordered_at=datetime.now(timezone.utc) - timedelta(minutes=90),
        urgency="STAT",
        status="ORDERED",
    )
    db.add(order)
    db.commit()

    # adm2 has been admitted for 14 hours with no clinical notes or vitals
    alerts = watchdog.scan_facility_safety(db, actor_id=doctor.id)

    overdue_labs = [a for a in alerts if a["alert_type"] == "OVERDUE_DIAGNOSTIC_INVESTIGATION"]
    assert len(overdue_labs) == 1
    assert overdue_labs[0]["urgency"] == "STAT"
    assert overdue_labs[0]["severity"] == "CRITICAL"
    assert overdue_labs[0]["elapsed_minutes"] >= 89

    overdue_handovers = [a for a in alerts if a["alert_type"] == "OVERDUE_SHIFT_HANDOVER_REVIEW"]
    assert len(overdue_handovers) == 1
    assert overdue_handovers[0]["admission_id"] == adm2.id
    assert overdue_handovers[0]["severity"] == "WARNING"


def test_watchdog_endpoints_rbac(client, watchdog_fixture, db):
    doctor = watchdog_fixture["doctor"]
    nurse = watchdog_fixture["nurse"]
    lab_tech = watchdog_fixture["lab_tech"]

    doctor_token = create_access_token(user_id=doctor.id, username=doctor.username, role=doctor.role)
    doc_headers = {"Authorization": f"Bearer {doctor_token}"}

    nurse_token = create_access_token(user_id=nurse.id, username=nurse.username, role=nurse.role)
    nurse_headers = {"Authorization": f"Bearer {nurse_token}"}

    lab_token = create_access_token(user_id=lab_tech.id, username=lab_tech.username, role=lab_tech.role)
    lab_headers = {"Authorization": f"Bearer {lab_token}"}

    # 1. Doctor can scan
    res = client.post("/clinical/watchdog/scan", headers=doc_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED"

    # 2. Nurse can view alerts & status
    status_res = client.get("/clinical/watchdog/status", headers=nurse_headers)
    assert status_res.status_code == 200
    assert status_res.json()["service"] == "ClinicalSafetyWatchdog"
    assert status_res.json()["status"] == "RUNNING"

    alerts_res = client.get("/clinical/watchdog/alerts", headers=nurse_headers)
    assert alerts_res.status_code == 200
    assert isinstance(alerts_res.json(), list)

    # 3. Lab technician forbidden from clinical watchdog scan
    forbidden_res = client.post("/clinical/watchdog/scan", headers=lab_headers)
    assert forbidden_res.status_code == 403
