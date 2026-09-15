from datetime import date, datetime, timezone

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


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

        if value != "ACTIVE":
            raise ValueError(
                "New medication orders must have status ACTIVE"
            )

        return value

    @field_validator("instructions")
    @classmethod
    def clean_instructions(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value if value else None

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.end_date is not None
            and self.end_date < self.start_date
        ):
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


class MedicationAdministrationCreate(BaseModel):
    medication_order_id: int = Field(gt=0)

    administered_by: int = Field(gt=0)

    administered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    status: str

    not_administered_reason: str | None = Field(
        default=None,
        max_length=2000,
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        value = value.strip().upper()

        allowed_statuses = {
            "ADMINISTERED",
            "NOT_ADMINISTERED",
            "REFUSED",
            "HELD",
        }

        if value not in allowed_statuses:
            raise ValueError(
                "status must be ADMINISTERED, NOT_ADMINISTERED, "
                "REFUSED, or HELD"
            )

        return value

    @field_validator(
        "not_administered_reason",
        "notes",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value if value else None

    @field_validator("administered_at")
    @classmethod
    def normalize_datetime(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "administered_at must include timezone information"
            )

        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_reason(self):
        statuses_requiring_reason = {
            "NOT_ADMINISTERED",
            "REFUSED",
            "HELD",
        }

        if (
            self.status in statuses_requiring_reason
            and not self.not_administered_reason
        ):
            raise ValueError(
                "not_administered_reason is required when "
                "medication is not administered"
            )

        if (
            self.status == "ADMINISTERED"
            and self.not_administered_reason is not None
        ):
            raise ValueError(
                "not_administered_reason must be empty when "
                "medication is administered"
            )

        return self


class MedicationAdministrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medication_order_id: int
    administered_by: int
    administered_at: datetime
    status: str
    not_administered_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime