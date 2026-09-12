from app.admissions.service import create_admission
from app.admissions.schemas import AdmissionCreate
from app.patients.models import Patient
from app.patients.service import create_patient
from app.patients.schemas import PatientCreate
from app.facilities.models import Facility
from app.facilities.service import create_facility
from app.facilities.schemas import FacilityCreate
from app.wards.service import create_ward, create_bed
from app.wards.schemas import WardCreate, BedCreate
from app.users.service import create_user
from app.users.models import User
from app.wards.models import Ward, Bed
from app.audit.models import AuditLog


def test_create_admission(db):
    patient = create_patient(
        db,
        PatientCreate(
            full_name="Admission Test Patient",
            date_of_birth="1980-01-10",
            sex="Male",
            allergy_status="No known allergy",
        ),
    )

    facility = create_facility(
        db,
        FacilityCreate(
            name="Test Hospital",
        ),
    )

    ward = create_ward(
        db,
        WardCreate(
            facility_id=facility.id,
            name="Medical Ward",
        ),
    )

    bed = create_bed(
        db,
        BedCreate(
            ward_id=ward.id,
            bed_number="01",
        ),
    )

    user = create_user(
        db,
        username="test.nurse",
        full_name="Test Nurse",
        role="NURSE",
    )

    admission_data = AdmissionCreate(
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="A&E/Emergency",
        reason_for_admission="Test admission",
        presenting_complaint="Test complaint",
        admitted_by=user.id,
    )

    admission = create_admission(db, admission_data)

    assert admission.id == 1
    assert admission.admission_number == "ADM-2026-000001"
    assert admission.patient_id == patient.id
    assert admission.ward_id == ward.id
    assert admission.bed_id == bed.id
    assert admission.status == "ACTIVE"

    db.refresh(bed)

    assert bed.status == "OCCUPIED"

def test_cannot_admit_patient_to_occupied_bed(db):
    patient_one = create_patient(
        db,
        PatientCreate(
            full_name="First Patient",
            date_of_birth="1980-01-10",
            sex="Male",
            allergy_status="No known allergy",
        ),
    )

    patient_two = create_patient(
        db,
        PatientCreate(
            full_name="Second Patient",
            date_of_birth="1985-02-20",
            sex="Female",
            allergy_status="No known allergy",
        ),
    )

    facility = create_facility(
        db,
        FacilityCreate(
            name="Test Hospital",
        ),
    )

    ward = create_ward(
        db,
        WardCreate(
            facility_id=facility.id,
            name="Medical Ward",
        ),
    )

    bed = create_bed(
        db,
        BedCreate(
            ward_id=ward.id,
            bed_number="01",
        ),
    )

    user = create_user(
        db,
        username="test.nurse",
        full_name="Test Nurse",
        role="NURSE",
    )

    first_admission = AdmissionCreate(
        patient_id=patient_one.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="A&E/Emergency",
        reason_for_admission="First admission",
        admitted_by=user.id,
    )

    create_admission(db, first_admission)

    second_admission = AdmissionCreate(
        patient_id=patient_two.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="A&E/Emergency",
        reason_for_admission="Second admission",
        admitted_by=user.id,
    )

    try:
        create_admission(db, second_admission)
        assert False, "Expected admission to fail because the bed is occupied"
    except ValueError as error:
        assert str(error) == "Selected bed is not available"


def test_cannot_use_bed_from_wrong_ward(db):
    patient = create_patient(
        db,
        PatientCreate(
            full_name="Wrong Ward Test Patient",
            date_of_birth="1990-03-15",
            sex="Male",
            allergy_status="No known allergy",
        ),
    )

    facility = create_facility(
        db,
        FacilityCreate(
            name="Test Hospital",
        ),
    )

    medical_ward = create_ward(
        db,
        WardCreate(
            facility_id=facility.id,
            name="Medical Ward",
        ),
    )

    surgical_ward = create_ward(
        db,
        WardCreate(
            facility_id=facility.id,
            name="Surgical Ward",
        ),
    )

    bed = create_bed(
        db,
        BedCreate(
            ward_id=surgical_ward.id,
            bed_number="01",
        ),
    )

    user = create_user(
        db,
        username="wrong.ward.nurse",
        full_name="Wrong Ward Nurse",
        role="NURSE",
    )

    admission_data = AdmissionCreate(
        patient_id=patient.id,
        ward_id=medical_ward.id,
        bed_id=bed.id,
        source="A&E/Emergency",
        reason_for_admission="Wrong ward test",
        admitted_by=user.id,
    )

    try:
        create_admission(db, admission_data)
        assert False, "Expected admission to fail because the bed belongs to another ward"
    except ValueError as error:
        assert str(error) == "Selected bed does not belong to selected ward"



def test_cannot_admit_nonexistent_patient(db):
    facility = create_facility(
        db,
        FacilityCreate(
            name="Test Hospital",
        ),
    )

    ward = create_ward(
        db,
        WardCreate(
            facility_id=facility.id,
            name="Medical Ward",
        ),
    )

    bed = create_bed(
        db,
        BedCreate(
            ward_id=ward.id,
            bed_number="01",
        ),
    )

    user = create_user(
        db,
        username="missing.patient.nurse",
        full_name="Missing Patient Nurse",
        role="NURSE",
    )

    admission_data = AdmissionCreate(
        patient_id=999,
        ward_id=ward.id,
        bed_id=bed.id,
        source="A&E/Emergency",
        reason_for_admission="Nonexistent patient test",
        admitted_by=user.id,
    )

    try:
        create_admission(db, admission_data)
        assert False, "Expected admission to fail because the patient does not exist"
    except ValueError as error:
        assert str(error) == "Patient not found"


def test_cannot_admit_to_nonexistent_ward(db):
    patient = Patient(
        full_name="Test Patient",
        patient_number="CL-000001",
        allergy_status="No known allergy",
    )
    db.add(patient)

    facility = Facility(
        name="Test Facility"
    )
    db.add(facility)

    bed = Bed(
        ward_id=999,
        bed_number="01",
        status="AVAILABLE",
    )
    db.add(bed)

    user = User(
        username="test.nurse",
        password_hash="test",
        full_name="Test Nurse",
        role="NURSE",
    )
    db.add(user)

    db.commit()

    admission_data = AdmissionCreate(
        patient_id=patient.id,
        ward_id=999,
        bed_id=bed.id,
        source="A&E/Emergency",
        reason_for_admission="Test reason",
        admitted_by=user.id,
    )

    try:
        create_admission(db, admission_data)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert str(error) == "Ward not found"



def test_cannot_admit_to_nonexistent_bed(db):
    patient = Patient(
        full_name="Test Patient",
        patient_number="CL-000001",
        allergy_status="No known allergy",
    )
    db.add(patient)

    facility = Facility(
        name="Test Facility"
    )
    db.add(facility)

    ward = Ward(
        facility_id=1,
        name="Medical Ward",
    )
    db.add(ward)

    user = User(
        username="test.nurse",
        password_hash="test",
        full_name="Test Nurse",
        role="NURSE",
    )
    db.add(user)

    db.commit()

    admission_data = AdmissionCreate(
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=999,
        source="A&E/Emergency",
        reason_for_admission="Test reason",
        admitted_by=user.id,
    )

    try:
        create_admission(db, admission_data)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert str(error) == "Bed not found"


def test_cannot_admit_with_nonexistent_user(db):
    patient = Patient(
        full_name="Test Patient",
        patient_number="CL-000001",
        allergy_status="No known allergy",
    )
    db.add(patient)

    facility = Facility(
        name="Test Facility"
    )
    db.add(facility)

    ward = Ward(
        facility_id=1,
        name="Medical Ward",
    )
    db.add(ward)

    bed = Bed(
        ward_id=1,
        bed_number="01",
        status="AVAILABLE",
    )
    db.add(bed)

    db.commit()

    admission_data = AdmissionCreate(
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="A&E/Emergency",
        reason_for_admission="Test reason",
        admitted_by=999,
    )

    try:
        create_admission(db, admission_data)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert str(error) == "Admitting healthcare worker not found"

def test_cannot_admit_with_inactive_user(db):
    patient = Patient(
        full_name="Test Patient",
        patient_number="CL-000001",
        allergy_status="No known allergy",
    )
    db.add(patient)

    facility = Facility(
        name="Test Facility"
    )
    db.add(facility)

    ward = Ward(
        facility_id=1,
        name="Medical Ward",
    )
    db.add(ward)

    bed = Bed(
        ward_id=1,
        bed_number="01",
        status="AVAILABLE",
    )
    db.add(bed)

    user = User(
        username="inactive.nurse",
        password_hash="test",
        full_name="Inactive Nurse",
        role="NURSE",
        is_active=False,
    )
    db.add(user)

    db.commit()

    admission_data = AdmissionCreate(
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="A&E/Emergency",
        reason_for_admission="Test reason",
        admitted_by=user.id,
    )

    try:
        create_admission(db, admission_data)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert str(error) == "Admitting healthcare worker is inactive"
    
def test_successful_admission_creates_audit_log(db):
    patient = Patient(
        full_name="Audit Test Patient",
        patient_number="CL-000001",
        allergy_status="No known allergy",
    )
    db.add(patient)

    facility = Facility(
        name="Audit Test Facility"
    )
    db.add(facility)

    ward = Ward(
        facility_id=1,
        name="Medical Ward",
    )
    db.add(ward)

    bed = Bed(
        ward_id=1,
        bed_number="01",
        status="AVAILABLE",
    )
    db.add(bed)

    user = User(
        username="audit.nurse",
        password_hash="test",
        full_name="Audit Nurse",
        role="NURSE",
    )
    db.add(user)

    db.commit()

    admission_data = AdmissionCreate(
        patient_id=patient.id,
        ward_id=ward.id,
        bed_id=bed.id,
        source="A&E/Emergency",
        reason_for_admission="Audit test admission",
        admitted_by=user.id,
    )

    admission = create_admission(db, admission_data)

    audit_log = db.query(AuditLog).filter(
        AuditLog.entity_type == "ADMISSION",
        AuditLog.entity_id == admission.id,
    ).first()

    assert audit_log is not None
    assert audit_log.user_id == user.id
    assert audit_log.action == "CREATE"
    assert audit_log.details == f"Admission {admission.admission_number} created"