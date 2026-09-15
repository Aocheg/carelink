from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MedicationOrderCreate(BaseModel):
    admission_id: int = Field(gt=0)

    medication_name: str = Field(
        min_length=1,
        max_length=150,
    )

    dose: str = Field(
        min_length=1,
        max_length=100,
    )

    route: str = Field(
        min_length=1,
        max_length=50,
    )

    frequency: str = Field(
        min_length=1,
        max_length=100,
    )

    start_date: date

    end_date: date | None = None

    prescribed_by: int = Field(gt=0)

    status: str = "ACTIVE"

    instructions: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator(
        "medication_name",
        "dose",
        "route",
        "frequency",
        "status",
    )
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty")

        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        value = value.strip().upper()

        allowed_statuses = {
            "ACTIVE",
            "DISCONTINUED",
            "COMPLETED",
        }

        if value not in allowed_statuses:
            raise ValueError(
                "status must be ACTIVE, DISCONTINUED, or COMPLETED"
            )

        return value

    @field_validator("instructions")
    @classmethod
    def clean_instructions(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value if value else None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError(
                "end_date cannot be earlier than start_date"
            )

        return self


class MedicationOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admission_id: int
    medication_name: str
    dose: str
    route: str
    frequency: str
    start_date: date
    end_date: date | None
    prescribed_by: int
    status: str
    instructions: str | None
    created_at: datetime
    updated_at: datetime