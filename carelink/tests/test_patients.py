from app.patients.service import generate_patient_number


def test_generate_patient_number():
    assert generate_patient_number