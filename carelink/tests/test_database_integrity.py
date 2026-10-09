from datetime import date
import sqlite3
import pytest
from sqlalchemy import create_engine, select, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base
from app.admissions.models import Admission
from app.admissions.schemas import AdmissionCreate, AdmissionDischarge
from app.admissions.service import create_admission, discharge_admission
from app.clinical.models import ClinicalNote
from app.clinical.schemas import ClinicalNoteCreate
from app.clinical.service import create_clinical_note
from app.database.seed import seed_database
from app.facilities.models import Facility
from app.facilities.schemas import FacilityCreate
from app.facilities.service import create_facility
from app.investigations.models import InvestigationOrder
from app.investigations.schemas import InvestigationOrderCreate
from app.investigations.service import create_investigation_order
from app.medications.models import MedicationOrder
from app.medications.schemas import MedicationOrderCreate, MedicationOrderDiscontinue
from app.medications.service import create_medication_order, discontinue_medication_order
from app.patients.models import Patient
from app.patients.schemas import PatientCreate
from app.patients.service import create_patient
from app.users.models import User
from app.users.service import create_user
from app.vitals.models import VitalSign
from app.vitals.schemas import VitalSignCreate
from app.vitals.service import create_vital_sign
from app.wards.models import Bed, Ward
from app.wards.schemas import BedCreate, WardCreate
from app.wards.service import create_bed, create_ward


@pytest.fixture
def fk_strict_db():
    """
    Creates an isolated SQLite in-memory database with strictly ENFORCED foreign keys.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_conn, conn_record):
        if isinstance(dbapi_conn, sqlite3.Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ============================================================
# 1. Foreign Key Relationship Enforcement
# ============================================================

def test_foreign_key_prevents_admission_with_invalid_patient(fk_strict_db):
    facility = create_facility(fk_strict_db, FacilityCreate(name="St. Mary's"))
    ward = create_ward(fk_strict_db, WardCreate(facility_id=facility.id, name="Ward A"))
    bed = create_bed(fk_strict_db, BedCreate(ward_id=ward.id, bed_number="01"))
    doctor = create_user(
        fk_strict_db,
        username="dr.house",
        full_name="Dr. Gregory House",
        role="DOCTOR",
        password="PassWord123!",
    )

    # Patient ID 999999 does not exist
    invalid_admission = Admission(
        admission_number="ADM-TEST-001",
        patient_id=999999,
        ward_id=ward.id,
        bed_id=bed.id,
        source="A&E",
        reason_for_admission="Fever",
        admitted_by=doctor.id,
    )
    fk_strict_db.add(invalid_admission)
    with pytest.raises(IntegrityError):
        fk_strict_db.commit()
    fk_strict_db.rollback()


def test_foreign_key_prevents_vitals_with_invalid_admission(fk_strict_db):
    doctor = create_user(
        fk_strict_db,
        username="dr.cameron",
        full_name="Dr. Allison Cameron",
        role="DOCTOR",
        password="PassWord123!",
    )

    # Admission ID 888888 does not exist
    invalid_vital = VitalSign(
        admission_id=888888,
        recorded_by=doctor.id,
        systolic_bp=120,
        diastolic_bp=80,
    )
    fk_strict_db.add(invalid_vital)
    with pytest.raises(IntegrityError):
        fk_strict_db.commit()
    fk_strict_db.rollback()


def test_foreign_key_prevents_medication_with_invalid_admission(fk_strict_db):
    doctor = create_user(
        fk_strict_db,
        username="dr.chase",
        full_name="Dr. Robert Chase",
        role="DOCTOR",
        password="PassWord123!",
    )

    # Admission ID 777777 does not exist
    invalid_med = MedicationOrder(
        admission_id=777777,
        medication_name="Aspirin",
        dose="75mg",
        route="Oral",
        frequency="OD",
        start_date=date(2026, 10, 8),
        prescribed_by=doctor.id,
    )
    fk_strict_db.add(invalid_med)
    with pytest.raises(IntegrityError):
        fk_strict_db.commit()
    fk_strict_db.rollback()


def test_foreign_key_prevents_clinical_note_with_invalid_admission(fk_strict_db):
    doctor = create_user(
        fk_strict_db,
        username="dr.foreman",
        full_name="Dr. Eric Foreman",
        role="DOCTOR",
        password="PassWord123!",
    )

    # Admission ID 666666 does not exist
    invalid_note = ClinicalNote(
        admission_id=666666,
        author_id=doctor.id,
        note_type="DOCTOR_REVIEW",
        content="Patient review",
    )
    fk_strict_db.add(invalid_note)
    with pytest.raises(IntegrityError):
        fk_strict_db.commit()
    fk_strict_db.rollback()


# ============================================================
# 2. Uniqueness & Duplicate Prevention Constraints
# ============================================================

def test_duplicate_bed_number_in_same_ward_prevented(db):
    facility = create_facility(db, FacilityCreate(name="General Clinic"))
    ward = create_ward(db, WardCreate(facility_id=facility.id, name="ICU"))

    create_bed(db, BedCreate(ward_id=ward.id, bed_number="BED-01"))

    # Attempt duplicate bed number in the same ward
    with pytest.raises(IntegrityError):
        dup_bed = Bed(ward_id=ward.id, bed_number="BED-01")
        db.add(dup_bed)
        db.commit()
    db.rollback()


def test_duplicate_ward_name_in_same_facility_prevented(db):
    facility = create_facility(db, FacilityCreate(name="City Hospital"))

    create_ward(db, WardCreate(facility_id=facility.id, name="Cardiology"))

    # Attempt duplicate ward name in the same facility
    with pytest.raises(IntegrityError):
        dup_ward = Ward(facility_id=facility.id, name="Cardiology")
        db.add(dup_ward)
        db.commit()
    db.rollback()


def test_duplicate_username_prevented(db):
    create_user(
        db,
        username="unique.nurse",
        full_name="Nurse One",
        role="NURSE",
        password="Password123!",
    )

    with pytest.raises(ValueError, match="already exists"):
        create_user(
            db,
            username="unique.nurse",
            full_name="Nurse Two",
            role="NURSE",
            password="Password456!",
        )


def test_concurrent_active_admission_for_same_patient_prevented(db):
    patient = create_patient(
        db,
        PatientCreate(
            full_name="John Concurrent",
            date_of_birth="1990-01-01",
            sex="Male",
            allergy_status="No known allergy",
        ),
    )
    facility = create_facility(db, FacilityCreate(name="Central Clinic"))
    ward = create_ward(db, WardCreate(facility_id=facility.id, name="Ward 1"))
    bed1 = create_bed(db, BedCreate(ward_id=ward.id, bed_number="B1"))
    bed2 = create_bed(db, BedCreate(ward_id=ward.id, bed_number="B2"))
    doctor = create_user(
        db,
        username="dr.concurrent",
        full_name="Dr. Concurrent",
        role="DOCTOR",
        password="Password123!",
    )

    # First admission succeeds
    adm1 = create_admission(
        db,
        AdmissionCreate(
            patient_id=patient.id,
            ward_id=ward.id,
            bed_id=bed1.id,
            source="A&E",
            reason_for_admission="First condition",
            admitted_by=doctor.id,
        ),
    )
    assert adm1.status == "ACTIVE"

    # Second admission for the SAME patient while first is active MUST fail
    with pytest.raises(ValueError, match="already has an active admission"):
        create_admission(
            db,
            AdmissionCreate(
                patient_id=patient.id,
                ward_id=ward.id,
                bed_id=bed2.id,
                source="A&E",
                reason_for_admission="Second condition",
                admitted_by=doctor.id,
            ),
        )


def test_cannot_admit_to_occupied_bed(db):
    patient1 = create_patient(
        db,
        PatientCreate(
            full_name="Patient First",
            date_of_birth="1980-01-01",
            sex="Male",
            allergy_status="No known allergy",
        ),
    )
    patient2 = create_patient(
        db,
        PatientCreate(
            full_name="Patient Second",
            date_of_birth="1982-02-02",
            sex="Female",
            allergy_status="No known allergy",
        ),
    )
    facility = create_facility(db, FacilityCreate(name="Occupancy Clinic"))
    ward = create_ward(db, WardCreate(facility_id=facility.id, name="Ward Shared"))
    bed = create_bed(db, BedCreate(ward_id=ward.id, bed_number="SingleBed"))
    doctor = create_user(
        db,
        username="dr.occupancy",
        full_name="Dr. Occupancy",
        role="DOCTOR",
        password="Password123!",
    )

    create_admission(
        db,
        AdmissionCreate(
            patient_id=patient1.id,
            ward_id=ward.id,
            bed_id=bed.id,
            source="A&E",
            reason_for_admission="Admit 1",
            admitted_by=doctor.id,
        ),
    )

    with pytest.raises(ValueError, match="Selected bed is not available"):
        create_admission(
            db,
            AdmissionCreate(
                patient_id=patient2.id,
                ward_id=ward.id,
                bed_id=bed.id,
                source="A&E",
                reason_for_admission="Admit 2",
                admitted_by=doctor.id,
            ),
        )


# ============================================================
# 3. Transaction Atomicity & Rollback Safety
# ============================================================

def test_admission_creation_rolls_back_atomically_on_failure(db, monkeypatch):
    patient = create_patient(
        db,
        PatientCreate(
            full_name="Atomicity Patient",
            date_of_birth="1975-05-05",
            sex="Male",
            allergy_status="No known allergy",
        ),
    )
    facility = create_facility(db, FacilityCreate(name="Atomicity Hospital"))
    ward = create_ward(db, WardCreate(facility_id=facility.id, name="AMU"))
    bed = create_bed(db, BedCreate(ward_id=ward.id, bed_number="Bed-A1"))
    doctor = create_user(
        db,
        username="dr.atomic",
        full_name="Dr. Atomic",
        role="DOCTOR",
        password="Password123!",
    )

    # Simulate unexpected failure during audit log step
    import app.admissions.service as adm_srv
    def mock_audit_fail(*args, **kwargs):
        raise RuntimeError("Simulated audit write failure")

    monkeypatch.setattr(adm_srv, "create_audit_log", mock_audit_fail)

    with pytest.raises(RuntimeError, match="Simulated audit write failure"):
        create_admission(
            db,
            AdmissionCreate(
                patient_id=patient.id,
                ward_id=ward.id,
                bed_id=bed.id,
                source="A&E",
                reason_for_admission="Atomic test",
                admitted_by=doctor.id,
            ),
        )

    # Verify no partial state was committed: bed remains AVAILABLE and no admission exists
    db.refresh(bed)
    assert bed.status == "AVAILABLE"
    adm_count = db.execute(select(Admission).where(Admission.patient_id == patient.id)).scalars().all()
    assert len(adm_count) == 0


def test_discharge_rolls_back_atomically_on_failure(db, monkeypatch):
    patient = create_patient(
        db,
        PatientCreate(
            full_name="Discharge Rollback Patient",
            date_of_birth="1978-08-08",
            sex="Female",
            allergy_status="No known allergy",
        ),
    )
    facility = create_facility(db, FacilityCreate(name="Rollback Hospital"))
    ward = create_ward(db, WardCreate(facility_id=facility.id, name="Ward Rollback"))
    bed = create_bed(db, BedCreate(ward_id=ward.id, bed_number="B-Rollback"))
    doctor = create_user(
        db,
        username="dr.rollback",
        full_name="Dr. Rollback",
        role="DOCTOR",
        password="Password123!",
    )

    admission = create_admission(
        db,
        AdmissionCreate(
            patient_id=patient.id,
            ward_id=ward.id,
            bed_id=bed.id,
            source="A&E",
            reason_for_admission="Pre-discharge",
            admitted_by=doctor.id,
        ),
    )

    import app.admissions.service as adm_srv
    def mock_discharge_audit_fail(*args, **kwargs):
        raise RuntimeError("Simulated audit failure on discharge")

    monkeypatch.setattr(adm_srv, "create_audit_log", mock_discharge_audit_fail)

    with pytest.raises(RuntimeError, match="Simulated audit failure on discharge"):
        discharge_admission(
            db,
            admission.id,
            AdmissionDischarge(
                discharged_by=doctor.id,
                discharge_summary="Attempted discharge",
            ),
        )

    # Verification: admission remains ACTIVE, bed remains OCCUPIED
    db.refresh(admission)
    db.refresh(bed)
    assert admission.status == "ACTIVE"
    assert bed.status == "OCCUPIED"


# ============================================================
# 4. Fresh Database Seeding End-to-End
# ============================================================

def test_fictional_seeder_runs_cleanly_on_fresh_database(tmp_path, monkeypatch):
    test_db_path = tmp_path / "fresh_seed_test.db"
    test_url = f"sqlite:///{test_db_path}"

    monkeypatch.setenv("DATABASE_URL", test_url)

    engine = create_engine(test_url)
    seed_database(target_engine=engine, drop_existing=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        patients = session.execute(select(Patient)).scalars().all()
        admissions = session.execute(select(Admission)).scalars().all()
        vitals = session.execute(select(VitalSign)).scalars().all()
        meds = session.execute(select(MedicationOrder)).scalars().all()
        notes = session.execute(select(ClinicalNote)).scalars().all()
        users = session.execute(select(User)).scalars().all()

        assert len(patients) >= 2
        assert len(admissions) >= 1
        assert len(vitals) >= 2
        assert len(meds) >= 1
        assert len(notes) >= 2
        assert len(users) >= 5

        # Check that Eleanor Vance is admitted in AMU-01
        adm = admissions[0]
        assert adm.status == "ACTIVE"
        assert "pneumonia" in adm.reason_for_admission.lower()

        # Check that users have hashed passwords, not plain text
        for u in users:
            assert not u.password_hash.startswith("Password")
            assert not u.password_hash.startswith("AdminPassword")
            assert len(u.password_hash) > 30

    finally:
        session.close()
        engine.dispose()
