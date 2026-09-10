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

class PatientResponse(BaseModel):
    id: int
    patient_number: str
    full_name: str
    date_of_birth: date | None
    sex: str | None
    marital_status: str | None
    religion: str | None
    occupation: str | None
    address: str | None
    phone_number: str | None
    blood_group: str | None
    genotype: str | None
    allergy_status: str
    allergy_details: str | None

class NextOfKinCreate(BaseModel):
    full_name: str
    relationship: str
    phone_number: str
    address: str | None = None
    is_primary: bool = True


class NextOfKinResponse(BaseModel):
    id: int
    patient_id: int
    full_name: str
    relationship: str
    phone_number: str
    address: str | None
    is_primary: bool