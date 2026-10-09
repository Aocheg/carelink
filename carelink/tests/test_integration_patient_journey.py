from datetime import date, datetime, timezone
import pytest

from app.audit.models import AuditLog
from app.audit.service import get_audit_logs
from app.users.service import create_user
from app.users.tokens import create_access_token


def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "CARELINK"
    assert data["version"] == "0.1.0"


def test_openapi_schema_generation(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "CARELINK"
    
    paths = schema["paths"]
    # Check that key endpoints across all modules are registered in the OpenAPI schema
    assert "/health" in paths
    assert "/patients/" in paths
    assert "/admissions/" in paths
    assert "/admissions/{admission_id}/discharge" in paths
    assert "/vitals/" in paths
    assert "/medications/" in paths
    assert "/medications/{medication_order_id}/discontinue" in paths
    assert "/investigations/orders" in paths
    assert "/investigations/results" in paths
    assert "/clinical/notes" in paths
    assert "/clinical/handover/{admission_id}" in paths
    assert "/clinical/timeline/{admission_id}" in paths
    assert "/audit/" in paths


def test_end_to_end_patient_journey_via_http_api(client, db):
    """
    Simulates a complete real-world inpatient hospital journey from presentation to discharge:
    1. Authenticate clinical staff (Admin, Doctor, Nurse, Lab Tech).
    2. Register patient and next of kin.
    3. Setup hospital facility, ward, and bed.
    4. Admit patient to bed (bed becomes OCCUPIED).
    5. Nurse records vital signs with NEWS2 & red-flag alert tracking.
    6. Doctor reviews patient and records clinical review note.
    7. Doctor prescribes IV antibiotic and nurse administers it.
    8. Doctor orders STAT diagnostic investigation and Lab Tech records critical result.
    9. Nursing shift handover summary and unified chronological timeline generated.
    10. Doctor discontinues medication with clinical rationale.
    11. Doctor discharges patient (bed freed back to AVAILABLE).
    12. Comprehensive audit trail verified.
    """

    # --- Step 1: Staff Creation & Authentication ---
    admin_user = create_user(
        db,
        username="journey.admin",
        full_name="Admin Director",
        role="ADMIN",
        password="AdminPassword123!",
    )
    doctor_user = create_user(
        db,
        username="journey.doctor",
        full_name="Dr. Gregory House",
        role="DOCTOR",
        password="DoctorPassword123!",
    )
    nurse_user = create_user(
        db,
        username="journey.nurse",
        full_name="Nurse Jackie",
        role="NURSE",
        password="NursePassword123!",
    )
    lab_user = create_user(
        db,
        username="journey.lab",
        full_name="Lab Tech Marcus",
        role="LABORATORY_STAFF",
        password="LabPassword123!",
    )

    # Obtain real JWT tokens via login endpoint
    login_admin = client.post("/users/login", json={"username": "journey.admin", "password": "AdminPassword123!"})
    assert login_admin.status_code == 200
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    login_doc = client.post("/users/login", json={"username": "journey.doctor", "password": "DoctorPassword123!"})
    assert login_doc.status_code == 200
    doc_token = login_doc.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Verify /users/me works for authenticated doctor
    me_resp = client.get("/users/me", headers=doc_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "journey.doctor"
    assert me_resp.json()["role"] == "DOCTOR"

    # --- Step 2: Patient Registration & Next of Kin ---
    patient_payload = {
        "full_name": "Clara Oswald",
        "date_of_birth": "1989-11-23",
        "sex": "Female",
        "marital_status": "Single",
        "religion": "None",
        "occupation": "High School Teacher",
        "address": "14 Totter's Lane, London",
        "phone_number": "08099887766",
        "blood_group": "B+",
        "genotype": "AA",
        "allergy_status": "Penicillin",
        "allergy_details": "Severe facial swelling and wheezing in 2018",
    }
    patient_resp = client.post("/patients/", json=patient_payload)
    assert patient_resp.status_code == 201
    patient_data = patient_resp.json()
    patient_id = patient_data["id"]
    assert patient_data["patient_number"].startswith("CL-")

    kin_payload = {
        "full_name": "Danny Pink",
        "relationship": "Partner",
        "phone_number": "08011223344",
        "address": "14 Totter's Lane, London",
        "is_primary": True,
    }
    kin_resp = client.post(f"/patients/{patient_id}/next-of-kin", json=kin_payload)
    assert kin_resp.status_code in (200, 201)

    # --- Step 3: Facility, Ward, and Bed Setup ---
    facility_resp = client.post("/facilities/", json={"name": "St. Jude Hospital", "description": "Acute General Hospital"})
    assert facility_resp.status_code == 201
    facility_id = facility_resp.json()["id"]

    ward_resp = client.post("/wards/", json={"facility_id": facility_id, "name": "Emergency Assessment Unit (EAU)"})
    assert ward_resp.status_code == 201
    ward_id = ward_resp.json()["id"]

    bed_resp = client.post("/wards/beds", json={"ward_id": ward_id, "bed_number": "EAU-01"})
    assert bed_resp.status_code == 201
    bed_id = bed_resp.json()["id"]

    # --- Step 4: Admission (Bed becomes OCCUPIED) ---
    adm_payload = {
        "patient_id": patient_id,
        "ward_id": ward_id,
        "bed_id": bed_id,
        "source": "Emergency Department",
        "reason_for_admission": "Severe acute asthma exacerbation",
        "presenting_complaint": "Acute onset dyspnea and wheeze unrelieved by salbutamol MDI",
        "admitted_by": doctor_user.id,
    }
    adm_resp = client.post("/admissions/", json=adm_payload)
    assert adm_resp.status_code == 201
    admission_data = adm_resp.json()
    admission_id = admission_data["id"]
    assert admission_data["status"] == "ACTIVE"
    assert admission_data["admission_number"].startswith("ADM-")

    # Confirm bed is now OCCUPIED
    bed_check = client.get(f"/wards/beds/{bed_id}")
    assert bed_check.status_code == 200
    assert bed_check.json()["status"] == "OCCUPIED"

    # --- Step 5: Vital Signs Observation & Alerts ---
    vitals_payload = {
        "admission_id": admission_id,
        "recorded_by": nurse_user.id,
        "systolic_bp": 135,
        "diastolic_bp": 88,
        "pulse": 118,           # Tachycardia (+2 NEWS2)
        "temperature": 37.4,    # Normal (0 NEWS2)
        "respiratory_rate": 26, # Severe tachypnea (+3 NEWS2)
        "spo2": 91.0,           # Hypoxia (+3 NEWS2)
        "measurement_status": "COMPLETE",
        "notes": "Patient in moderate respiratory distress with audible expiratory wheeze.",
    }
    vitals_resp = client.post("/vitals/", json=vitals_payload)
    assert vitals_resp.status_code == 201

    # Check NEWS2 score and clinical alerts via clinical API
    alerts_resp = client.get(f"/clinical/alerts/{admission_id}")
    assert alerts_resp.status_code == 200
    alerts_data = alerts_resp.json()
    assert alerts_data["news2_score"] >= 8  # High clinical risk
    vital_alert_params = [a["parameter"] for a in alerts_data["vital_alerts"]]
    assert "SPO2" in vital_alert_params
    assert "RESPIRATORY_RATE" in vital_alert_params

    # --- Step 6: Doctor Review & Clinical Note ---
    note_payload = {
        "admission_id": admission_id,
        "author_id": doctor_user.id,
        "note_type": "DOCTOR_REVIEW",
        "content": "Patient reviewed in EAU. Widespread polyphonic wheeze. Commencing back-to-back bronchodilator nebulizers and IV hydrocortisone.",
        "plan": "Nebulized salbutamol + ipratropium 20 minutely x 3. IV Hydrocortisone 100mg stat. Repeat vitals in 30 mins.",
    }
    note_resp = client.post("/clinical/notes", json=note_payload)
    assert note_resp.status_code == 201

    # --- Step 7: Medication Order & Administration ---
    med_payload = {
        "admission_id": admission_id,
        "medication_name": "Hydrocortisone Sodium Succinate",
        "dose": "100mg",
        "route": "IV",
        "frequency": "Stat",
        "start_date": str(date.today()),
        "prescribed_by": doctor_user.id,
        "instructions": "Slow IV bolus over 3 minutes",
    }
    med_resp = client.post("/medications/", json=med_payload)
    assert med_resp.status_code == 201
    med_order_id = med_resp.json()["id"]

    admin_payload = {
        "medication_order_id": med_order_id,
        "administered_by": nurse_user.id,
        "status": "ADMINISTERED",
        "notes": "Administered via peripheral venous catheter without incident.",
    }
    admin_resp = client.post("/medications/administrations", json=admin_payload)
    assert admin_resp.status_code == 201

    # --- Step 8: Diagnostic Investigation & Lab Result ---
    inv_payload = {
        "admission_id": admission_id,
        "test_name": "Arterial Blood Gas (ABG)",
        "category=":"BLOOD_GAS",
        "category": "BIOCHEMISTRY",
        "ordered_by": doctor_user.id,
        "urgency": "STAT",
        "clinical_indication": "Assess hypoxia and ventilatory compromise in severe acute asthma",
    }
    inv_resp = client.post("/investigations/orders", json=inv_payload)
    assert inv_resp.status_code == 201
    inv_order_id = inv_resp.json()["id"]

    res_payload = {
        "investigation_order_id": inv_order_id,
        "recorded_by": lab_user.id,
        "result_value": "pH 7.36, PaO2 8.2 kPa, PaCO2 4.1 kPa, HCO3 22 mmol/L",
        "reference_range": "pH 7.35-7.45, PaO2 > 10.6 kPa",
        "is_abnormal": True,
        "critical_alert": True,
        "notes": "Type 1 respiratory failure. Phoned to ward doctor immediately.",
    }
    res_resp = client.post("/investigations/results", json=res_payload)
    assert res_resp.status_code == 201

    # --- Step 9: Nursing Handover Summary & Unified Timeline ---
    handover_resp = client.get(f"/clinical/handover/{admission_id}")
    assert handover_resp.status_code == 200
    handover = handover_resp.json()
    assert handover["patient_name"] == "Clara Oswald"
    assert handover["allergy_status"] == "Penicillin"
    assert handover["ward_name"] == "Emergency Assessment Unit (EAU)"
    assert handover["bed_number"] == "EAU-01"
    assert len(handover["active_medications"]) == 1
    assert handover["latest_doctor_review"] is not None
    assert "polyphonic wheeze" in handover["latest_doctor_review"]["content"]

    timeline_resp = client.get(f"/clinical/timeline/{admission_id}")
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()
    event_types = [e["event_type"] for e in timeline]
    assert "ADMISSION" in event_types
    assert "VITAL_SIGNS" in event_types
    assert "DOCTOR_REVIEW" in event_types
    assert "MEDICATION_ORDER" in event_types
    assert "MEDICATION_ADMINISTRATION" in event_types
    assert "INVESTIGATION_ORDER" in event_types
    assert "INVESTIGATION_RESULT" in event_types

    # --- Step 10: Medication Discontinuation ---
    disc_payload = {
        "discontinued_by": doctor_user.id,
        "reason": "Stat dose completed; patient transitioning to oral prednisolone.",
    }
    disc_resp = client.post(f"/medications/{med_order_id}/discontinue", json=disc_payload)
    assert disc_resp.status_code == 200
    assert disc_resp.json()["status"] == "DISCONTINUED"

    # --- Step 11: Patient Discharge (Bed freed back to AVAILABLE) ---
    discharge_payload = {
        "discharged_by": doctor_user.id,
        "discharge_summary": "Asthma exacerbation fully resolved. Wheeze cleared. PEFR 480 L/min (>80% predicted). Discharged with oral prednisolone taper and inhaled corticosteroids.",
    }
    discharge_resp = client.post(f"/admissions/{admission_id}/discharge", json=discharge_payload)
    assert discharge_resp.status_code == 200
    assert discharge_resp.json()["status"] == "DISCHARGED"

    # Verify bed is now AVAILABLE
    bed_after = client.get(f"/wards/beds/{bed_id}")
    assert bed_after.status_code == 200
    assert bed_after.json()["status"] == "AVAILABLE"

    # --- Step 12: Audit Trail Verification ---
    audit_resp = client.get("/audit/", headers=admin_headers)
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    assert len(audit_logs) >= 8

    actions = [log["action"] for log in audit_logs]
    assert "CREATE" in actions
    assert "DISCHARGE" in actions
    assert "DISCONTINUE" in actions
    assert "ORDER" in actions
    assert "RESULT" in actions


def test_audit_endpoint_security_authorization(client, db):
    # Non-admin user cannot access audit logs (403 Forbidden)
    nurse_user = create_user(
        db,
        username="audit.nurse",
        full_name="Nurse Audit",
        role="NURSE",
        password="Password123!",
    )
    login_resp = client.post("/users/login", json={"username": "audit.nurse", "password": "Password123!"})
    nurse_token = login_resp.json()["access_token"]
    nurse_headers = {"Authorization": f"Bearer {nurse_token}"}

    forbidden_resp = client.get("/audit/", headers=nurse_headers)
    assert forbidden_resp.status_code == 403
    assert "Operation not permitted" in forbidden_resp.json()["detail"]

    # Unauthenticated request returns 401
    unauth_resp = client.get("/audit/")
    assert unauth_resp.status_code == 401
