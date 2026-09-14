from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VitalSignCreate(BaseModel):
    admission_id: int = Field(gt=0)
    recorded_by: int = Field(gt=0)

    recorded_at: datetime | None = None

    systolic_bp: int | None = Field(default=None, ge=40, le=300)
    diastolic_bp: int | None = Field(default=None, ge=20, le=200)

    pulse: int | None = Field(default=None, ge=20, le=300)

    temperature: float | None = Field(default=None, ge=25.0, le=45.0)

    respiratory_rate: int | None = Field(default=None, ge=4, le=80)

    spo2: float | None = Field(default=None, ge=0.0, le=100.0)

    measurement_status: str = "COMPLETE"

    not_measured_reason: str | None = None

    notes: str | None = None

    @field_validator("measurement_status")
    @classmethod
    def validate_measurement_status(cls, value: str) -> str:
        allowed_statuses = {
            "COMPLETE",
            "PARTIAL",
            "NOT_MEASURED",
        }

        value = value.strip().upper()

        if value not in allowed_statuses:
            raise ValueError(
                "measurement_status must be COMPLETE, PARTIAL, or NOT_MEASURED"
            )

        return value

    @model_validator(mode="after")
    def validate_measurement_state(self):
        measurements = [
            self.systolic_bp,
            self.diastolic_bp,
            self.pulse,
            self.temperature,
            self.respiratory_rate,
            self.spo2,
        ]

        measured_count = sum(
            value is not None for value in measurements
        )

        if (self.systolic_bp is None) != (self.diastolic_bp is None):
            raise ValueError(
                "Systolic and diastolic blood pressure must be recorded together"
            )

        reason = (
            self.not_measured_reason.strip()
            if self.not_measured_reason
            else None
        )

        if self.measurement_status == "COMPLETE":
            if measured_count != 6:
                raise ValueError(
                    "COMPLETE measurements require all vital-sign values"
                )

            if reason is not None:
                raise ValueError(
                    "not_measured_reason must be empty for COMPLETE measurements"
                )

        elif self.measurement_status == "PARTIAL":
            if measured_count == 0:
                raise ValueError(
                    "PARTIAL measurements require at least one vital-sign value"
                )

            if measured_count == 6:
                raise ValueError(
                    "PARTIAL measurements must have at least one missing vital-sign value"
                )

            if reason is None:
                raise ValueError(
                    "not_measured_reason is required for PARTIAL measurements"
                )

            self.not_measured_reason = reason

        elif self.measurement_status == "NOT_MEASURED":
            if measured_count != 0:
                raise ValueError(
                    "NOT_MEASURED records cannot contain vital-sign values"
                )

            if reason is None:
                raise ValueError(
                    "not_measured_reason is required for NOT_MEASURED measurements"
                )

            self.not_measured_reason = reason

        return self


class VitalSignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admission_id: int
    recorded_by: int
    recorded_at: datetime

    systolic_bp: int | None
    diastolic_bp: int | None
    pulse: int | None
    temperature: float | None
    respiratory_rate: int | None
    spo2: float | None

    measurement_status: str
    not_measured_reason: str | None
    notes: str | None
    created_at: datetime