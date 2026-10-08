import pytest
from fastapi import HTTPException

from app.users.dependencies import get_current_user, require_permission, require_roles
from app.users.roles import (
    ROLE_PERMISSIONS,
    SUPPORTED_ROLES,
    Role,
    has_permission,
    normalize_role,
    validate_role,
)
from app.users.schemas import UserCreate
from app.users.service import create_user
from app.users.tokens import create_access_token


# ==========================================
# 1. Supported Roles & Normalization Tests
# ==========================================

def test_supported_roles_completeness():
    expected_roles = {
        "ADMIN",
        "DOCTOR",
        "NURSE",
        "PHARMACIST",
        "LABORATORY_STAFF",
        "LAB_TECH",
    }
    assert expected_roles.issubset(SUPPORTED_ROLES)


def test_validate_role_accepts_valid_roles():
    for role_name in ("admin", "DOCTOR", "Nurse", "pharmacist", "laboratory_staff", "lab_tech"):
        normalized = validate_role(role_name)
        assert normalized in SUPPORTED_ROLES
        assert normalized == normalized.upper()


def test_validate_role_rejects_unsupported_roles():
    for invalid in ("HACKER", "SUPERUSER", "PATIENT", "MANAGER", "CLERK", ""):
        with pytest.raises(ValueError):
            validate_role(invalid)


def test_user_create_schema_validates_role():
    # Valid role succeeds
    schema = UserCreate(
        username="doc1",
        full_name="Doctor One",
        role="doctor",
        password="ValidPassword123",
    )
    assert schema.role == "DOCTOR"

    # Invalid role raises validation error
    with pytest.raises(Exception):
        UserCreate(
            username="bad1",
            full_name="Bad Role User",
            role="UNAUTHORIZED_ROLE",
            password="ValidPassword123",
        )


def test_create_user_service_validates_and_normalizes_role(db):
    user = create_user(
        db,
        username="norm.nurse",
        full_name="Normalized Nurse",
        role="nurse",
        password="ValidPassword123",
    )
    assert user.role == "NURSE"

    with pytest.raises(ValueError):
        create_user(
            db,
            username="bad.role",
            full_name="Bad Role",
            role="INVALID_ROLE",
            password="ValidPassword123",
        )


# ==========================================
# 2. Permissions Matrix Tests
# ==========================================

def test_clinical_permissions_matrix():
    # Doctors can prescribe medications; nurses cannot
    assert has_permission("DOCTOR", "medications:prescribe") is True
    assert has_permission("NURSE", "medications:prescribe") is False

    # Nurses can administer medications; pharmacists cannot bedside administer
    assert has_permission("NURSE", "medications:administer") is True
    assert has_permission("PHARMACIST", "medications:administer") is False

    # Pharmacists can review and dispense medications
    assert has_permission("PHARMACIST", "medications:dispense") is True
    assert has_permission("LABORATORY_STAFF", "medications:dispense") is False

    # Laboratory staff can record investigations; nurses cannot
    assert has_permission("LABORATORY_STAFF", "investigations:record") is True
    assert has_permission("NURSE", "investigations:record") is False

    # Admins have administrative permissions
    assert has_permission("ADMIN", "users:read") is True
    assert has_permission("NURSE", "users:read") is False


# ==========================================
# 3. require_roles Dependency Unit Tests
# ==========================================

def test_require_roles_allows_matching_role(db):
    doctor = create_user(
        db,
        username="auth.doctor",
        full_name="Authorized Doctor",
        role="DOCTOR",
        password="ValidPassword123",
    )

    verifier = require_roles("DOCTOR")
    result = verifier(current_user=doctor)
    assert result.id == doctor.id
    assert result.role == "DOCTOR"


def test_require_roles_allows_multiple_accepted_roles(db):
    nurse = create_user(
        db,
        username="auth.nurse",
        full_name="Authorized Nurse",
        role="NURSE",
        password="ValidPassword123",
    )

    verifier = require_roles("DOCTOR", "NURSE", "ADMIN")
    result = verifier(current_user=nurse)
    assert result.id == nurse.id


def test_require_roles_rejects_unauthorized_role_with_403(db):
    pharmacist = create_user(
        db,
        username="auth.pharmacist",
        full_name="Authorized Pharmacist",
        role="PHARMACIST",
        password="ValidPassword123",
    )

    verifier = require_roles("DOCTOR")
    with pytest.raises(HTTPException) as exc_info:
        verifier(current_user=pharmacist)

    assert exc_info.value.status_code == 403
    assert "Operation not permitted" in exc_info.value.detail


def test_require_permission_unit_behavior(db):
    doctor = create_user(
        db,
        username="perm.doctor",
        full_name="Permission Doctor",
        role="DOCTOR",
        password="ValidPassword123",
    )
    nurse = create_user(
        db,
        username="perm.nurse",
        full_name="Permission Nurse",
        role="NURSE",
        password="ValidPassword123",
    )

    prescribe_checker = require_permission("medications:prescribe")

    # Doctor succeeds
    assert prescribe_checker(current_user=doctor).id == doctor.id

    # Nurse fails with 403
    with pytest.raises(HTTPException) as exc_info:
        prescribe_checker(current_user=nurse)
    assert exc_info.value.status_code == 403


# ==========================================
# 4. API Endpoints RBAC & Anti-Spoofing Tests
# ==========================================

def test_get_users_unauthenticated_returns_401(client):
    response = client.get("/users/")
    assert response.status_code == 401


def test_get_users_non_admin_returns_403(client, db):
    nurse = create_user(
        db,
        username="nurse.regular",
        full_name="Regular Nurse",
        role="NURSE",
        password="ValidPassword123",
    )
    token = create_access_token(
        user_id=nurse.id,
        username=nurse.username,
        role=nurse.role,
    )

    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Operation not permitted for this user role"


def test_get_users_admin_returns_200(client, db):
    admin = create_user(
        db,
        username="admin.superuser",
        full_name="Super Admin",
        role="ADMIN",
        password="ValidPassword123",
    )
    token = create_access_token(
        user_id=admin.id,
        username=admin.username,
        role=admin.role,
    )

    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(u["username"] == "admin.superuser" for u in data)


def test_api_does_not_trust_client_supplied_role_header(client, db):
    """
    Ensure the API strictly derives permissions from the authenticated user
    record in the database and NEVER trusts spoofed client headers like
    X-Role, Role, or X-User-Role.
    """
    nurse = create_user(
        db,
        username="nurse.sneaky",
        full_name="Sneaky Nurse",
        role="NURSE",
        password="ValidPassword123",
    )
    token = create_access_token(
        user_id=nurse.id,
        username=nurse.username,
        role=nurse.role,
    )

    response = client.get(
        "/users/",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Role": "ADMIN",
            "Role": "ADMIN",
            "X-User-Role": "ADMIN",
        },
    )
    # Must still be rejected because database record specifies NURSE
    assert response.status_code == 403


def test_api_does_not_trust_client_supplied_role_query_param(client, db):
    """
    Ensure the API ignores ?role=ADMIN in query parameters.
    """
    nurse = create_user(
        db,
        username="nurse.query",
        full_name="Query Nurse",
        role="NURSE",
        password="ValidPassword123",
    )
    token = create_access_token(
        user_id=nurse.id,
        username=nurse.username,
        role=nurse.role,
    )

    response = client.get(
        "/users/?role=ADMIN",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_get_roles_and_permissions_endpoint(client):
    response = client.get("/users/roles")
    assert response.status_code == 200
    data = response.json()

    assert "roles" in data
    assert "ADMIN" in data["roles"]
    assert "DOCTOR" in data["roles"]
    assert "NURSE" in data["roles"]
    assert "PHARMACIST" in data["roles"]
    assert "LABORATORY_STAFF" in data["roles"]

    assert "permissions" in data
    assert "medications:prescribe" in data["permissions"]["DOCTOR"]
    assert "medications:prescribe" not in data["permissions"]["NURSE"]


# ==========================================
# 5. Clinical Workflow Role-Enforcement Tests
# ==========================================

def _setup_clinical_context(db):
    import random
    from datetime import date
    from app.facilities.models import Facility
    from app.wards.models import Ward, Bed
    from app.patients.models import Patient
    from app.admissions.models import Admission

    rnd = random.randint(1000, 9999)
    facility = Facility(name=f"General Hospital {rnd}")
    db.add(facility)
    db.flush()

    ward = Ward(facility_id=facility.id, name="ICU")
    db.add(ward)
    db.flush()

    bed = Bed(ward_id=ward.id, bed_number=f"BED-{rnd}", status="AVAILABLE")
    db.add(bed)
    db.flush()

    patient = Patient(
        patient_number=f"CL-RBAC-{rnd}",
        full_name="RBAC Patient",
        date_of_birth=date(1995, 5, 5),
        sex="Female",
        allergy_status="No known allergy",
    )
    db.add(patient)
    db.flush()

    admitting_nurse = create_user(
        db,
        username=f"setup.nurse.{rnd}",
        full_name="Setup Nurse",
        role="NURSE",
        password="ValidPassword123",
    )

    admission = Admission(
        admission_number=f"ADM-RBAC-{rnd}",
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        admitted_by=admitting_nurse.id,
        source="EMERGENCY",
        reason_for_admission="Acute medical observation",
        status="ACTIVE",
    )
    db.add(admission)
    db.flush()

    return patient, ward, bed, admission


def test_clinical_rbac_nurse_cannot_prescribe_medication(db):
    from datetime import date
    from app.medications.schemas import MedicationOrderCreate
    from app.medications.service import create_medication_order

    patient, ward, bed, admission = _setup_clinical_context(db)
    doctor = create_user(db, username="doc.prescribe", full_name="Dr. Prescribe", role="DOCTOR", password="ValidPassword123")
    nurse = create_user(db, username="nurse.prescribe", full_name="Nurse NoPrescribe", role="NURSE", password="ValidPassword123")

    # Nurse trying to prescribe must be rejected
    order_by_nurse = MedicationOrderCreate(
        admission_id=admission.id,
        medication_name="Gentamicin",
        dose="80 mg",
        route="IV",
        frequency="OD",
        start_date=date(2026, 10, 1),
        prescribed_by=nurse.id,
        status="ACTIVE",
    )
    with pytest.raises(ValueError) as exc:
        create_medication_order(db, order_by_nurse)
    assert "cannot prescribe medications" in str(exc.value)

    # Doctor prescribing succeeds
    order_by_doctor = MedicationOrderCreate(
        admission_id=admission.id,
        medication_name="Gentamicin",
        dose="80 mg",
        route="IV",
        frequency="OD",
        start_date=date(2026, 10, 1),
        prescribed_by=doctor.id,
        status="ACTIVE",
    )
    saved = create_medication_order(db, order_by_doctor)
    assert saved.id is not None
    assert saved.prescribed_by == doctor.id


def test_clinical_rbac_pharmacist_cannot_administer_medication(db):
    from datetime import date, datetime, timezone
    from app.medications.models import MedicationOrder
    from app.medications.schemas import MedicationAdministrationCreate
    from app.medications.service import create_medication_administration

    patient, ward, bed, admission = _setup_clinical_context(db)
    doctor = create_user(db, username="doc.order", full_name="Dr. Order", role="DOCTOR", password="ValidPassword123")
    nurse = create_user(db, username="nurse.administer", full_name="Nurse Administer", role="NURSE", password="ValidPassword123")
    pharmacist = create_user(db, username="pharm.user", full_name="Pharm User", role="PHARMACIST", password="ValidPassword123")

    order = MedicationOrder(
        admission_id=admission.id,
        medication_name="Paracetamol",
        dose="1g",
        route="ORAL",
        frequency="QDS",
        start_date=date(2026, 10, 1),
        prescribed_by=doctor.id,
        status="ACTIVE",
    )
    db.add(order)
    db.flush()

    # Pharmacist cannot administer at bedside
    admin_by_pharm = MedicationAdministrationCreate(
        medication_order_id=order.id,
        administered_by=pharmacist.id,
        administered_at=datetime.now(timezone.utc),
        status="ADMINISTERED",
    )
    with pytest.raises(ValueError) as exc:
        create_medication_administration(db, admin_by_pharm)
    assert "cannot administer medications" in str(exc.value)

    # Nurse administering succeeds
    admin_by_nurse = MedicationAdministrationCreate(
        medication_order_id=order.id,
        administered_by=nurse.id,
        administered_at=datetime.now(timezone.utc),
        status="ADMINISTERED",
    )
    saved_admin = create_medication_administration(db, admin_by_nurse)
    assert saved_admin.id is not None
    assert saved_admin.administered_by == nurse.id



def test_clinical_rbac_pharmacist_cannot_record_vitals(db):
    from app.vitals.schemas import VitalSignCreate
    from app.vitals.service import create_vital_sign

    patient, ward, bed, admission = _setup_clinical_context(db)
    nurse = create_user(db, username="nurse.vitals", full_name="Nurse Vitals", role="NURSE", password="ValidPassword123")
    pharmacist = create_user(db, username="pharm.vitals", full_name="Pharm Vitals", role="PHARMACIST", password="ValidPassword123")

    # Pharmacist cannot record vitals
    vital_by_pharm = VitalSignCreate(
        admission_id=admission.id,
        recorded_by=pharmacist.id,
        systolic_bp=120,
        diastolic_bp=80,
        pulse=72,
        temperature=36.8,
        respiratory_rate=16,
        spo2=98.0,
        measurement_status="COMPLETE",
    )
    with pytest.raises(ValueError) as exc:
        create_vital_sign(db, vital_by_pharm)
    assert "cannot record vital signs" in str(exc.value)

    # Nurse can record vitals
    vital_by_nurse = VitalSignCreate(
        admission_id=admission.id,
        recorded_by=nurse.id,
        systolic_bp=120,
        diastolic_bp=80,
        pulse=72,
        temperature=36.8,
        respiratory_rate=16,
        spo2=98.0,
        measurement_status="COMPLETE",
    )
    saved_vital = create_vital_sign(db, vital_by_nurse)
    assert saved_vital.id is not None
    assert saved_vital.recorded_by == nurse.id


def test_clinical_rbac_pharmacist_cannot_admit_patient(db):
    from app.admissions.schemas import AdmissionCreate
    from app.admissions.service import create_admission

    patient, ward, bed, _ = _setup_clinical_context(db)
    pharmacist = create_user(db, username="pharm.admit", full_name="Pharm Admit", role="PHARMACIST", password="ValidPassword123")

    adm_data = AdmissionCreate(
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        admitted_by=pharmacist.id,
        source="OUTPATIENT",
        reason_for_admission="Observation",
    )
    with pytest.raises(ValueError) as exc:
        create_admission(db, adm_data)
    assert "cannot admit patients" in str(exc.value)


