from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog


def create_audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: str | None = None,
):
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )

    db.add(audit_log)
    return audit_log


def get_audit_logs(
    db: Session,
    entity_type: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    action: str | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())