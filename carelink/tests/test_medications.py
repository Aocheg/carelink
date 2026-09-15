from datetime import date

import pytest

from app.admissions.models import Admission
from app.audit.models import AuditLog
from app.facilities.models import Facility
from app.medications.schemas import MedicationOrderCreate
from app.medications.service import (
    create_medication_order,
    get_medication_order_by_id,
    get_medication_orders_by_admission,
)
from app.patients.models import Patient
from app.users.models import User
from app.wards.models import Bed, Ward


def create_test_data(db):
    facility = Facility(
        name="Medication Test Hospital",
        description="Test facility",
        is_active=True,
    )
    db.add(facility)
    db.flush()

    ward = Ward(
        facility_id=facility.id,
        name="Medical Ward",
        description="Test medical ward",
        is_active=True,
    )
    db.add(ward)
    db.flush()

    bed = Bed(
        ward_id=ward.id,
        bed_number="BED-01",
        status="AVAILABLE",
    )
    db.add(bed)
    db.flush()

    patient = Patient(
        patient_number="CL-TEST-001",
        full_name="Medication Test Patient",
        date_of_birth=date(1990, 1, 1),
        sex="Female",
        marital_status="Single",
        religion="Christianity",
        occupation="Teacher",
        address="Test Address",
        phone_number="08000000000",
        blood_group="O+",
        genotype="AA",
        allergy_status="NO_KNOWN_ALLERGY",
        allergy_details=None,
    )
    db.add(patient)
    db.flush()

    user = User(
        username="medication_test_doctor",
        password_hash="TEST_HASH",
        full_name="Medication Test Doctor",
        role="DOCTOR",
        is_active=True,
    )
    db.add(user)
    db.flush()

    admission = Admission(
        admission_number="ADM-TEST-001",
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="DOCTOR_OFFICE",
        reason_for_admission="Test admission",
        presenting_complaint="Test complaint",
        patient_account="Test account",
        doctor_assessment="Test doctor assessment",
        nursing_assessment="Test nursing assessment",
        nursing_diagnosis="Test nursing diagnosis",
        admitted_by=user.id,
        status="ACTIVE",
    )
    db.add(admission)

    bed.status = "OCCUPIED"

    db.commit()

    db.refresh(admission)
    db.refresh(user)

    return admission, user


def create_medication_data(
    admission_id: int,
    prescribed_by: int,
    medication_name: str = "Amoxicillin",
):
    return MedicationOrderCreate(
        admission_id=admission_id,
        medication_name=medication_name,
        dose="500 mg",
        route="ORAL",
        frequency="EVERY_8_HOURS",
        start_date=date(2026, 9, 15),
        end_date=None,
        prescribed_by=prescribed_by,
        status="ACTIVE",
        instructions="Take after food.",
    )


def test_create_medication_order(db):
    admission, user = create_test_data(db)

    medication_data = create_medication_data(
        admission.id,
        user.id,
    )

    medication = create_medication_order(
        db,
        medication_data,
    )

    assert medication.id is not None
    assert medication.admission_id == admission.id
    assert medication.medication_name == "Amoxicillin"
    assert medication.dose == "500 mg"
    assert medication.route == "ORAL"
    assert medication.frequency == "EVERY_8_HOURS"
    assert medication.prescribed_by == user.id
    assert medication.status == "ACTIVE"


def test_create_medication_order_creates_audit_log(db):
    admission, user = create_test_data(db)

    medication_data = create_medication_data(
        admission.id,
        user.id,
    )

    medication = create_medication_order(
        db,
        medication_data,
    )

    audit_log = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "MEDICATION_ORDER",
            AuditLog.entity_id == medication.id,
        )
        .first()
    )

    assert audit_log is not None
    assert audit_log.action == "CREATE"
    assert audit_log.user_id == user.id


def test_create_medication_order_rejects_nonexistent_admission(db):
    _, user = create_test_data(db)

    medication_data = create_medication_data(
        admission_id=999999,
        prescribed_by=user.id,
    )

    with pytest.raises(
        ValueError,
        match="Admission not found",
    ):
        create_medication_order(
            db,
            medication_data,
        )


def test_create_medication_order_rejects_nonexistent_prescriber(db):
    admission, _ = create_test_data(db)

    medication_data = create_medication_data(
        admission_id=admission.id,
        prescribed_by=999999,
    )

    with pytest.raises(
        ValueError,
        match="Prescribing healthcare worker not found",
    ):
        create_medication_order(
            db,
            medication_data,
        )


def test_create_medication_order_rejects_inactive_prescriber(db):
    admission, user = create_test_data(db)

    user.is_active = False
    db.commit()

    medication_data = create_medication_data(
        admission.id,
        user.id,
    )

    with pytest.raises(
        ValueError,
        match="Prescribing healthcare worker is inactive",
    ):
        create_medication_order(
            db,
            medication_data,
        )


def test_get_medication_order_by_id(db):
    admission, user = create_test_data(db)

    medication_data = create_medication_data(
        admission.id,
        user.id,
    )

    medication = create_medication_order(
        db,
        medication_data,
    )

    found_medication = get_medication_order_by_id(
        db,
        medication.id,
    )

    assert found_medication is not None
    assert found_medication.id == medication.id
    assert found_medication.medication_name == "Amoxicillin"


def test_get_medication_orders_by_admission(db):
    admission, user = create_test_data(db)

    first_medication = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            user.id,
            medication_name="Amoxicillin",
        ),
    )

    second_medication = create_medication_order(
        db,
        create_medication_data(
            admission.id,
            user.id,
            medication_name="Paracetamol",
        ),
    )

    medications = get_medication_orders_by_admission(
        db,
        admission.id,
    )

    assert len(medications) == 2
    assert medications[0].id == first_medication.id
    assert medications[1].id == second_medication.id


def test_get_medication_orders_rejects_nonexistent_admission(db):
    with pytest.raises(
        ValueError,
        match="Admission not found",
    ):
        get_medication_orders_by_admission(
            db,
            999999,
        )