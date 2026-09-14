from datetime import datetime, timezone

import pytest

from app.admissions.models import Admission
from app.facilities.models import Facility
from app.patients.models import Patient
from app.users.models import User
from app.vitals.schemas import VitalSignCreate
from app.vitals.service import create_vital_sign
from app.wards.models import Bed, Ward


def create_test_admission(db):
    facility = Facility(
        name="Safety Test Facility",
    )
    db.add(facility)
    db.flush()

    ward = Ward(
        facility_id=facility.id,
        name="Safety Test Ward",
    )
    db.add(ward)
    db.flush()

    bed = Bed(
        ward_id=ward.id,
        bed_number="SAFE-01",
        status="AVAILABLE",
    )
    db.add(bed)
    db.flush()

    patient = Patient(
        patient_number="SAFE-001",
        full_name="Safety Test Patient",
        allergy_status="No known allergy",
    )
    db.add(patient)
    db.flush()

    user = User(
        username="safety_test_nurse",
        password_hash="NOT_SET_YET",
        full_name="Safety Test Nurse",
        role="NURSE",
        is_active=True,
    )
    db.add(user)
    db.flush()

    admission = Admission(
        admission_number="SAFE-ADM-001",
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="CLINIC",
        reason_for_admission="Safety testing",
        admitted_by=user.id,
        status="ACTIVE",
    )
    db.add(admission)
    db.flush()

    return admission, user


def test_partial_measurement_cannot_contain_all_values(db):
    admission, user = create_test_admission(db)

    with pytest.raises(
        ValueError,
        match="PARTIAL measurements must have at least one missing",
    ):
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=user.id,
            recorded_at=datetime.now(timezone.utc),
            systolic_bp=120,
            diastolic_bp=80,
            pulse=78,
            temperature=36.8,
            respiratory_rate=18,
            spo2=98,
            measurement_status="PARTIAL",
            not_measured_reason="Incorrect status test",
        )


def test_partial_measurement_requires_at_least_one_value(db):
    admission, user = create_test_admission(db)

    with pytest.raises(
        ValueError,
        match="PARTIAL measurements require at least one",
    ):
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=user.id,
            measurement_status="PARTIAL",
            not_measured_reason="No values recorded",
        )


def test_complete_measurement_cannot_have_missing_reason(db):
    admission, user = create_test_admission(db)

    with pytest.raises(
        ValueError,
        match="not_measured_reason must be empty",
    ):
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=user.id,
            systolic_bp=120,
            diastolic_bp=80,
            pulse=78,
            temperature=36.8,
            respiratory_rate=18,
            spo2=98,
            measurement_status="COMPLETE",
            not_measured_reason="Incorrect reason",
        )


def test_blood_pressure_requires_both_values(db):
    admission, user = create_test_admission(db)

    with pytest.raises(
        ValueError,
        match="Systolic and diastolic blood pressure",
    ):
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=user.id,
            systolic_bp=120,
            diastolic_bp=None,
            pulse=78,
            temperature=36.8,
            respiratory_rate=18,
            spo2=98,
            measurement_status="PARTIAL",
            not_measured_reason="Diastolic blood pressure unavailable",
        )


def test_not_measured_requires_reason(db):
    admission, user = create_test_admission(db)

    with pytest.raises(
        ValueError,
        match="not_measured_reason is required",
    ):
        VitalSignCreate(
            admission_id=admission.id,
            recorded_by=user.id,
            measurement_status="NOT_MEASURED",
        )