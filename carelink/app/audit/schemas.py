from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    timestamp: datetime
    details: str | None = None
    previous_hash: str | None = None
    current_hash: str | None = None


class AuditVerificationResponse(BaseModel):
    status: str
    records_verified: int
    tamper_detected: bool
    tampered_log_id: int | None = None
    last_verified_hash: str | None = None
    details: str
