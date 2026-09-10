from app.patients.service import generate_patient_number
from app.patients.service import create_patient
from app.patients.schemas import PatientCreate
from app.patients.service import find_duplicate_patient


def test_generate_patient_number(db):
    patient_number = generate_patient_number(db)

    assert patient_number == "CL-000001"


def test_create_patient(db):
    patient_data = PatientCreate(
        full_name="Test Patient",
        date_of_birth="1990-01-15",
        sex="Male",
        marital_status="Single",
        religion="Christianity",
        occupation="Teacher",
        address="Test Address",
        phone_number="08000000000",
        blood_group="O+",
        genotype="AA",
        allergy_status="No known allergy",
        allergy_details=None,
    )

    patient = create_patient(db, patient_data)

    assert patient.id == 1
    assert patient.patient_number == "CL-000001"
    assert patient.full_name == "Test Patient"
    assert patient.date_of_birth.isoformat() == "1990-01-15"

def test_find_duplicate_patient(db):
    patient_data = PatientCreate(
        full_name="Duplicate Test Patient",
        date_of_birth="1985-05-20",
        sex="Female",
        marital_status="Married",
        religion="Christianity",
        occupation="Nurse",
        address="Test Address",
        phone_number="08011111111",
        blood_group="A+",
        genotype="AA",
        allergy_status="No known allergy",
        allergy_details=None,
    )

    create_patient(db, patient_data)

    duplicate = find_duplicate_patient(
        db,
        "Duplicate Test Patient",
        patient_data.date_of_birth,
    )

    assert duplicate is not None
    assert duplicate.full_name == "Duplicate Test Patient"
    assert duplicate.date_of_birth == patient_data.date_of_birth