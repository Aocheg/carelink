from datetime import datetime

from pydantic import BaseModel


class AdmissionCreate(BaseModel):
    patient_id: int
    ward_id: int
    bed_id: int
    source: str
    reason_for_admission: str
    presenting_complaint: str | None = None
    patient_account: str | None = None
    doctor_assessment: str | None = None
    nursing_assessment: str | None = None
    nursing_diagnosis: str | None = None
    admitted_by: int


class AdmissionDischarge(BaseModel):
    discharged_by: int
    discharge_summary: str


class AdmissionResponse(BaseModel):
    id: int
    admission_number: str
    patient_id: int
    ward_id: int
    bed_id: int
    admitted_at: datetime
    source: str
    reason_for_admission: str
    presenting_complaint: str | None
    patient_account: str | None
    doctor_assessment: str | None
    nursing_assessment: str | None
    nursing_diagnosis: str | None
    admitted_by: int
    status: str
    discharged_at: datetime | None = None
    discharge_summary: str | None = None
    discharged_by: int | None = None