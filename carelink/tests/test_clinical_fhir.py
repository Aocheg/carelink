from datetime import date, datetime, timezone
import pytest

from app.admissions.models import Admission
from app.audit.service import verify_audit_trail
from app.clinical.fhir import export_patient_fhir_bundle
from app.facilities.models import Facility
from app.patients.models import Patient
from app.users.models import User
from app.users.service import hash_password
from app.users.tokens import create_access_token
from app.vitals.models import VitalSign
from app.wards.models import Bed, Ward


@pytest.fixture
def fhir_fixture(db):
    facility = Facility(name="Federal Teaching Hospital", is_active=True)
    db.add(facility)
    db.commit()

    ward = Ward(facility_id=facility.id, name="Cardiology CCU", description="ICU High Dependency Bay")
    db.add(ward)
    db.commit()

    bed = Bed(ward_id=ward.id, bed_number="CCU-BED-01", status="OCCUPIED")
    db.add(bed)
    db.commit()

    doctor = User(
        username="dr.emeka",
        password_hash=hash_password("DoctorPass123!"),
        full_name="Dr. Emeka Eze",
        role="DOCTOR",
        is_active=True,
    )
    pharmacist = User(
        username="pharm.funke",
        password_hash=hash_password("PharmPass123!"),
        full_name="Pharm. Funke Ade",
        role="PHARMACIST",
        is_active=True,
    )
    db.add_all([doctor, pharmacist])
    db.commit()

    patient = Patient(
        patient_number="PAT-2026-099",
        full_name="Ibrahim Danladi",
        allergy_status="NO_KNOWN_ALLERGIES",
        date_of_birth=date(1982, 5, 14),
        sex="MALE",
        phone_number="+2348031234567",
        address="Plot 44, Garki II, Abuja",
    )
    db.add(patient)
    db.commit()

    admission = Admission(
        admission_number="ADM-2026-001",
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        admitted_by=doctor.id,
        admitted_at=datetime(2026, 10, 15, 8, 30, tzinfo=timezone.utc),
        source="EMERGENCY",
        reason_for_admission="Acute Coronary Syndrome with Dyspnea",
        status="ACTIVE",
    )
    db.add(admission)
    db.commit()

    vital = VitalSign(
        admission_id=admission.id,
        recorded_by=doctor.id,
        recorded_at=datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc),
        temperature=38.6,
        systolic_bp=145,
        diastolic_bp=92,
        pulse=105,
        respiratory_rate=22,
        spo2=94.0,
        measurement_status="COMPLETE",
    )
    db.add(vital)
    db.commit()

    return {
        "facility": facility,
        "ward": ward,
        "bed": bed,
        "doctor": doctor,
        "pharmacist": pharmacist,
        "patient": patient,
        "admission": admission,
        "vital": vital,
    }


def test_export_patient_fhir_bundle_structure(db, fhir_fixture):
    patient = fhir_fixture["patient"]
    doctor = fhir_fixture["doctor"]

    bundle = export_patient_fhir_bundle(db, patient.id, requesting_user_id=doctor.id)

    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["total"] >= 3  # Patient + Encounter + Vital Observation
    assert len(bundle["entry"]) == bundle["total"]

    # Check Patient Resource
    patient_entry = bundle["entry"][0]["resource"]
    assert patient_entry["resourceType"] == "Patient"
    assert patient_entry["id"] == str(patient.id)
    assert patient_entry["identifier"][0]["value"] == "PAT-2026-099"
    assert patient_entry["name"][0]["family"] == "Danladi"
    assert patient_entry["name"][0]["given"] == ["Ibrahim"]
    assert patient_entry["gender"] == "male"
    assert patient_entry["birthDate"] == "1982-05-14"
    assert patient_entry["telecom"][0]["value"] == "+2348031234567"
    assert "Plot 44, Garki II, Abuja" in patient_entry["address"][0]["text"]

    # Check Encounter Resource
    encounter_entry = bundle["entry"][1]["resource"]
    assert encounter_entry["resourceType"] == "Encounter"
    assert encounter_entry["status"] == "in-progress"
    assert encounter_entry["class"]["code"] == "IMP"
    assert encounter_entry["subject"]["reference"] == f"Patient/{patient.id}"
    assert "Acute Coronary Syndrome" in encounter_entry["reasonCode"][0]["text"]

    # Check Observation Resource (Vital Signs)
    obs_entry = bundle["entry"][2]["resource"]
    assert obs_entry["resourceType"] == "Observation"
    assert obs_entry["status"] == "final"
    assert obs_entry["category"][0]["coding"][0]["code"] == "vital-signs"
    assert obs_entry["code"]["coding"][0]["code"] == "85354-9"

    # Verify LOINC components
    components = {comp["code"]["coding"][0]["code"]: comp["valueQuantity"] for comp in obs_entry["component"]}
    assert components["8480-6"]["value"] == 145.0  # Systolic BP
    assert components["8480-6"]["unit"] == "mm[Hg]"
    assert components["8462-4"]["value"] == 92.0   # Diastolic BP
    assert components["8867-4"]["value"] == 105.0  # Heart rate
    assert components["8867-4"]["unit"] == "{beats}/min"
    assert components["9279-1"]["value"] == 22.0   # Resp rate
    assert components["8310-5"]["value"] == 38.6   # Temp
    assert components["2708-6"]["value"] == 94.0   # SpO2
    assert components["86488-8"]["value"] == 5.0   # NEWS2 Score

    # Verify audit verification is still intact
    audit_verification = verify_audit_trail(db)
    assert audit_verification["status"] == "VALID"
    assert audit_verification["tamper_detected"] is False


def test_export_patient_fhir_bundle_empty_admissions(db):
    patient = Patient(
        patient_number="PAT-EMPTY-001",
        full_name="Fatima Aliyu",
        allergy_status="NO_KNOWN_ALLERGIES",
        sex="FEMALE",
    )
    db.add(patient)
    db.commit()

    bundle = export_patient_fhir_bundle(db, patient.id)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
    assert bundle["entry"][0]["resource"]["gender"] == "female"


def test_export_patient_fhir_not_found(db):
    with pytest.raises(ValueError, match="not found"):
        export_patient_fhir_bundle(db, 999999)


def test_fhir_endpoint_success_for_doctor(client, fhir_fixture, db):
    doctor = fhir_fixture["doctor"]
    patient = fhir_fixture["patient"]

    token = create_access_token(user_id=doctor.id, username=doctor.username, role=doctor.role)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/clinical/fhir/{patient.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["resourceType"] == "Bundle"
    assert data["type"] == "collection"
    assert data["total"] >= 3


def test_fhir_endpoint_forbidden_for_pharmacist(client, fhir_fixture):
    pharmacist = fhir_fixture["pharmacist"]
    patient = fhir_fixture["patient"]

    token = create_access_token(user_id=pharmacist.id, username=pharmacist.username, role=pharmacist.role)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/clinical/fhir/{patient.id}", headers=headers)
    assert response.status_code == 403
