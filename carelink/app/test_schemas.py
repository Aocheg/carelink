from app.patients.schemas import PatientCreate


patient = PatientCreate(
    full_name="John Doe",
    date_of_birth="1998-05-20",
    sex="Male",
    marital_status="Single",
    religion="Christianity",
    occupation="Teacher",
    address="12 Main Street, Otukpo",
    phone_number="08012345678",
    blood_group="O+",
    genotype="AA",
    allergy_status="No known allergy"
)

print(patient)
print(patient.date_of_birth)
print(type(patient.date_of_birth))