from datetime import date
from pydantic import BaseModel

class PatientCreate(BaseModel):
    full_name: str
    date_of_birth: date | None = None
    sex: str | None = None
    marital_status: str | None = None
    religion: str | None = None
    