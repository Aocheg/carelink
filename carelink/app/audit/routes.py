from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit.schemas import AuditLogResponse, AuditVerificationResponse
from app.audit.service import get_audit_logs, verify_audit_trail
from app.database.connection import SessionLocal
from app.users.dependencies import require_roles
from app.users.models import User

router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/verify",
    response_model=AuditVerificationResponse,
)
def verify_audit_trail_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """
    Forensic Verification Endpoint:
    Cryptographically validates the complete SHA-256 chained audit ledger.
    Detects any unauthorized modification, deletion, or back-dating of clinical records.
    Restricted to system administrators (NDPA 2023 & statutory compliance).
    """
    return verify_audit_trail(db)


@router.get(
    "/",
    response_model=list[AuditLogResponse],
)
def get_audit_logs_endpoint(
    entity_type: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    action: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    return get_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
        limit=limit,
    )
