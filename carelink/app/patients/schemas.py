from datetime import date
from pydantic import BaseModel

class PatientCreate(BaseModel):
    full_name: str
    date_of_birth: date | None = None
    sex: str | None = None
    marital_status: str | None = None
    religion: str | None = None
    occupation: str | None = None
    address: str | None = None
    phone_number: str | None = None
    blood_group: str | None = None
    genotype: str | None = None
    allergy_status: str
    allergy_details: str | None = None

class NextOfKinCreate(BaseModel):
    full_name: str
    relationship: str
    phone_numberrrrrr: str
    address: str | None = None
