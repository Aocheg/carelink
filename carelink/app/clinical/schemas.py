from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClinicalNoteCreate(BaseModel):
    admission_id: int = Field(gt=0)
    author_id: int = Field(gt=0)
    note_type: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=3000)
    plan: str | None = Field(default=None, max_length=2000)

    @field_validator("note_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {
            "DOCTOR_REVIEW",
            "NURSING_ASSESSMENT",
            "NURSING_DIAGNOSIS",
            "NURSING_NOTE",
            "HANDOVER_NOTE",
        }
        cleaned = v.strip().upper()
        if cleaned not in allowed:
            raise ValueError(f"note_type must be one of: {', '.join(sorted(allowed))}")
        return cleaned

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("content cannot be empty")
        return cleaned


class ClinicalNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admission_id: int
    author_id: int
    note_type: str
    content: str
    plan: str | None = None
    created_at: datetime


class TimelineEvent(BaseModel):
    event_type: str
    timestamp: datetime
    title: str
    description: str
    recorded_by: int | str | None = None
    metadata: dict = {}


class HandoverSummary(BaseModel):
    admission_id: int
    admission_number: str
    patient_id: int
    patient_name: str
    patient_number: str
    sex: str
    age_years: int | None = None
    allergy_status: str
    allergy_details: str | None = None
    ward_name: str
    bed_number: str
    admitted_at: datetime
    length_of_stay_days: int
    admitting_reason: str
    latest_vitals: dict | None = None
    news2_score: int | None = None
    clinical_alerts: list[dict] = []
    active_medications: list[dict] = []
    latest_doctor_review: dict | None = None
    latest_nursing_note: dict | None = None
    pending_investigations: list[dict] = []
