from datetime import datetime, timezone

import pytest

from app.admissions.models import Admission
from app.audit.models import AuditLog
from app.facilities.models import Facility
from app.patients.models import Patient
from app.users.models import User
from app.vitals.service import (
    create_vital_sign,
    get_vital_sign_by_id,
    get_vital_signs_by_admission,
)
from app.wards.models import Bed, Ward


def create_test_data(db):
    facility = Facility(
        name="Test General Hospital",
        description="Facility used for automated tests",
    )
    db.add(facility)
    db.flush()

    ward = Ward(
        facility_id=facility.id,
        name="Test Medical Ward",
        description="Ward used for automated tests",
    )
    db.add(ward)
    db.flush()

    bed = Bed(
        ward_id=ward.id,
        bed_number="TEST-01",
        status="AVAILABLE",
    )
    db.add(bed)
    db.flush()

    patient = Patient(
        patient_number="CL-TEST-000001",
        full_name="Test Patient",
        date_of_birth=datetime(1990, 1, 1).date(),
        sex="Male",
        marital_status="Single",
        religion="Christianity",
        occupation="Engineer",
        address="Test Address",
        phone_number="08000000000",
        blood_group="O+",
        genotype="AA",
        allergy_status="No known allergy",
    )
    db.add(patient)
    db.flush()

    user = User(
        username="test_nurse",
        password_hash="TEST_HASH",
        full_name="Test Nurse",
        role="NURSE",
        is_active=True,
    )
    db.add(user)
    db.flush()

    admission = Admission(
        admission_number="ADM-TEST-000001",
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="CLINIC",
        reason_for_admission="Test admission",
        presenting_complaint="Test complaint",
        patient_account="Test patient account",
        doctor_assessment="Test doctor assessment",
        nursing_assessment="Test nursing assessment",
        nursing_diagnosis="Test nursing diagnosis",
        admitted_by=user.id,
        status="ACTIVE",
    )

    bed.status = "OCCUPIED"

    db.add(admission)
    db.commit()
    db.refresh(admission)
    db.refresh(user)

    return admission, user


def make_vital_data(
    admission_id,
    recorded_by,
    *,
    recorded_at=None,
    systolic_bp=120,
    diastolic_bp=80,
    pulse=78,
    temperature=36.8,
    respiratory_rate=18,
    spo2=98,
    measurement_status="COMPLETE",
    not_measured_reason=None,
    notes=None,
):
    return type(
        "VitalData",
        (),
        {
            "admission_id": admission_id,
            "recorded_by": recorded_by,
            "recorded_at": recorded_at or datetime.now(timezone.utc),
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "pulse": pulse,
            "temperature": temperature,
            "respiratory_rate": respiratory_rate,
            "spo2": spo2,
            "measurement_status": measurement_status,
            "not_measured_reason": not_measured_reason,
            "notes": notes,
        },
    )()


def test_create_complete_vital_sign(db):
    admission, user = create_test_data(db)

    vital_data = make_vital_data(
        admission.id,
        user.id,
    )

    vital = create_vital_sign(db, vital_data)

    assert vital.id is not None
    assert vital.admission_id == admission.id
    assert vital.recorded_by == user.id
    assert vital.systolic_bp == 120
    assert vital.diastolic_bp == 80
    assert vital.pulse == 78
    assert vital.temperature == 36.8
    assert vital.respiratory_rate == 18
    assert vital.spo2 == 98
    assert vital.measurement_status == "COMPLETE"


def test_create_vital_sign_creates_audit_log(db):
    admission, user = create_test_data(db)

    vital_data = make_vital_data(
        admission.id,
        user.id,
    )

    vital = create_vital_sign(db, vital_data)

    audit_log = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "VITAL_SIGN")
        .filter(AuditLog.entity_id == vital.id)
        .first()
    )

    assert audit_log is not None
    assert audit_log.action == "CREATE"
    assert audit_log.user_id == user.id


def test_create_partial_vital_sign_with_reason(db):
    admission, user = create_test_data(db)

    vital_data = make_vital_data(
        admission.id,
        user.id,
        spo2=None,
        measurement_status="PARTIAL",
        not_measured_reason="Pulse oximeter unavailable",
    )

    vital = create_vital_sign(db, vital_data)

    assert vital.measurement_status == "PARTIAL"
    assert vital.spo2 is None
    assert vital.not_measured_reason == "Pulse oximeter unavailable"


def test_partial_vital_sign_requires_reason(db):
    admission, user = create_test_data(db)

    vital_data = make_vital_data(
        admission.id,
        user.id,
        spo2=None,
        measurement_status="PARTIAL",
        not_measured_reason=None,
    )

    with pytest.raises(
        ValueError,
        match="not_measured_reason is required",
    ):
        create_vital_sign(db, vital_data)


def test_complete_vital_sign_requires_all_values(db):
    admission, user = create_test_data(db)

    vital_data = make_vital_data(
        admission.id,
        user.id,
        spo2=None,
        measurement_status="COMPLETE",
    )

    with pytest.raises(
        ValueError,
        match="COMPLETE measurements require all vital-sign values",
    ):
        create_vital_sign(db, vital_data)


def test_not_measured_vital_sign(db):
    admission, user = create_test_data(db)

    vital_data = make_vital_data(
        admission.id,
        user.id,
        systolic_bp=None,
        diastolic_bp=None,
        pulse=None,
        temperature=None,
        respiratory_rate=None,
        spo2=None,
        measurement_status="NOT_MEASURED",
        not_measured_reason="Vital-sign equipment unavailable",
        notes="Patient assessment deferred until equipment became available.",
    )

    vital = create_vital_sign(db, vital_data)

    assert vital.measurement_status == "NOT_MEASURED"
    assert vital.systolic_bp is None
    assert vital.pulse is None
    assert vital.spo2 is None
    assert vital.not_measured_reason == "Vital-sign equipment unavailable"


def test_not_measured_cannot_contain_values(db):
    admission, user = create_test_data(db)

    vital_data = make_vital_data(
        admission.id,
        user.id,
        systolic_bp=120,
        diastolic_bp=80,
        pulse=None,
        temperature=None,
        respiratory_rate=None,
        spo2=None,
        measurement_status="NOT_MEASURED",
        not_measured_reason="Equipment unavailable",
    )

    with pytest.raises(
        ValueError,
        match="NOT_MEASURED records cannot contain vital-sign values",
    ):
        create_vital_sign(db, vital_data)


def test_nonexistent_admission_rejected(db):
    _, user = create_test_data(db)

    vital_data = make_vital_data(
        999999,
        user.id,
    )

    with pytest.raises(
        ValueError,
        match="Admission not found",
    ):
        create_vital_sign(db, vital_data)


def test_inactive_healthcare_worker_rejected(db):
    admission, user = create_test_data(db)

    user.is_active = False
    db.commit()

    vital_data = make_vital_data(
        admission.id,
        user.id,
    )

    with pytest.raises(
        ValueError,
        match="Recording healthcare worker is inactive",
    ):
        create_vital_sign(db, vital_data)


def test_get_vital_sign_by_id(db):
    admission, user = create_test_data(db)

    vital_data = make_vital_data(
        admission.id,
        user.id,
    )

    vital = create_vital_sign(db, vital_data)

    found_vital = get_vital_sign_by_id(
        db,
        vital.id,
    )

    assert found_vital is not None
    assert found_vital.id == vital.id


def test_get_vital_signs_by_admission(db):
    admission, user = create_test_data(db)

    first_vital_data = make_vital_data(
        admission.id,
        user.id,
        recorded_at=datetime(
            2026,
            1,
            1,
            8,
            0,
            tzinfo=timezone.utc,
        ),
    )

    second_vital_data = make_vital_data(
        admission.id,
        user.id,
        recorded_at=datetime(
            2026,
            1,
            1,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        systolic_bp=118,
        diastolic_bp=76,
        pulse=82,
        temperature=37.0,
        respiratory_rate=19,
        spo2=97,
    )

    first_vital = create_vital_sign(
        db,
        first_vital_data,
    )

    second_vital = create_vital_sign(
        db,
        second_vital_data,
    )

    vitals = get_vital_signs_by_admission(
        db,
        admission.id,
    )

    assert len(vitals) == 2
    assert vitals[0].id == first_vital.id
    assert vitals[1].id == second_vital.id


def test_get_vitals_for_nonexistent_admission(db):
    with pytest.raises(
        ValueError,
        match="Admission not found",
    ):
        get_vital_signs_by_admission(
            db,
            999999,
        )


def test_vital_timestamp_preserves_utc_timezone(db):
    from datetime import datetime, timezone

    from app.vitals.service import create_vital_sign
    from app.vitals.schemas import VitalSignCreate

    facility = Facility(
        name="Timezone Test Facility",
    )
    db.add(facility)
    db.flush()

    ward = Ward(
        facility_id=facility.id,
        name="Timezone Test Ward",
    )
    db.add(ward)
    db.flush()

    bed = Bed(
        ward_id=ward.id,
        bed_number="TZ-01",
        status="AVAILABLE",
    )
    db.add(bed)
    db.flush()

    patient = Patient(
        patient_number="TZ-001",
        full_name="Timezone Test Patient",
        allergy_status="No known allergy",
    )
    db.add(patient)
    db.flush()

    user = User(
        username="timezone_test_nurse",
        password_hash="NOT_SET_YET",
        full_name="Timezone Test Nurse",
        role="NURSE",
        is_active=True,
    )
    db.add(user)
    db.flush()

    admission = Admission(
        admission_number="TZ-ADM-001",
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="CLINIC",
        reason_for_admission="Timezone test",
        admitted_by=user.id,
        status="ACTIVE",
    )
    db.add(admission)
    db.flush()

    recorded_at = datetime(
        2026,
        9,
        14,
        20,
        40,
        tzinfo=timezone.utc,
    )

    vital_data = VitalSignCreate(
        admission_id=admission.id,
        recorded_by=user.id,
        recorded_at=recorded_at,
        systolic_bp=120,
        diastolic_bp=80,
        pulse=78,
        temperature=36.8,
        respiratory_rate=18,
        spo2=98,
        measurement_status="COMPLETE",
    )

    vital = create_vital_sign(db, vital_data)

    assert vital.recorded_at.tzinfo is not None
    assert vital.recorded_at.utcoffset() == timezone.utc.utcoffset(recorded_at)
    assert vital.recorded_at == recorded_at