from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvestigationOrderCreate(BaseModel):
    admission_id: int = Field(gt=0)
    test_name: str = Field(min_length=1, max_length=150)
    category: str = Field(default="GENERAL", max_length=50)
    ordered_by: int = Field(gt=0)
    urgency: str = Field(default="ROUTINE", max_length=20)
    clinical_indication: str | None = Field(default=None, max_length=500)

    @field_validator("test_name", "category")
    @classmethod
    def strip_text(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        allowed = {"ROUTINE", "URGENT", "STAT"}
        cleaned = v.strip().upper()
        if cleaned not in allowed:
            raise ValueError(f"Urgency must be one of: {', '.join(sorted(allowed))}")
        return cleaned


class InvestigationResultCreate(BaseModel):
    investigation_order_id: int = Field(gt=0)
    recorded_by: int = Field(gt=0)
    result_value: str = Field(min_length=1, max_length=1000)
    reference_range: str | None = Field(default=None, max_length=100)
    is_abnormal: bool = False
    critical_alert: bool = False
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("result_value")
    @classmethod
    def strip_result(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Result value cannot be empty")
        return cleaned


class InvestigationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_order_id: int
    recorded_by: int
    recorded_at: datetime
    result_value: str
    reference_range: str | None = None
    is_abnormal: bool
    critical_alert: bool
    notes: str | None = None
    created_at: datetime


class InvestigationOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admission_id: int
    test_name: str
    category: str
    ordered_by: int
    ordered_at: datetime
    urgency: str
    clinical_indication: str | None = None
    status: str
    results: list[InvestigationResultResponse] = []
    created_at: datetime
