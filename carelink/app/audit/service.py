import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog

GENESIS_HASH = "0" * 64


def format_timestamp(ts: datetime) -> str:
    """Canonical UTC string representation ensuring cross-database hash reproducibility."""
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts.strftime("%Y-%m-%d %H:%M:%S.%f")


def calculate_log_hash(
    previous_hash: str,
    timestamp: datetime,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: str | None,
) -> str:
    ts_str = format_timestamp(timestamp)
    payload = f"{previous_hash}|{ts_str}|{user_id}|{action}|{entity_type}|{entity_id}|{details or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: str | None = None,
):
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
    latest = db.execute(stmt).scalars().first()
    previous_hash = latest.current_hash if latest and latest.current_hash else GENESIS_HASH

    now = datetime.now(timezone.utc)
    current_hash = calculate_log_hash(
        previous_hash=previous_hash,
        timestamp=now,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )

    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp=now,
        details=details,
        previous_hash=previous_hash,
        current_hash=current_hash,
    )

    db.add(audit_log)
    db.flush()
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


def verify_audit_trail(db: Session) -> dict:
    logs = list(db.execute(select(AuditLog).order_by(AuditLog.id.asc())).scalars().all())
    if not logs:
        return {
            "status": "VALID",
            "records_verified": 0,
            "tamper_detected": False,
            "tampered_log_id": None,
            "last_verified_hash": None,
            "details": "Audit trail is empty. 0 records verified.",
        }

    expected_prev_hash = GENESIS_HASH
    for log in logs:
        if log.previous_hash != expected_prev_hash:
            return {
                "status": "TAMPER_DETECTED",
                "records_verified": log.id - 1 if log.id else 0,
                "tamper_detected": True,
                "tampered_log_id": log.id,
                "last_verified_hash": expected_prev_hash,
                "details": f"Chain continuity broken at record ID {log.id}: previous_hash mismatch.",
            }

        recalculated_hash = calculate_log_hash(
            previous_hash=log.previous_hash,
            timestamp=log.timestamp,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
        )
        if log.current_hash != recalculated_hash:
            return {
                "status": "TAMPER_DETECTED",
                "records_verified": log.id - 1 if log.id else 0,
                "tamper_detected": True,
                "tampered_log_id": log.id,
                "last_verified_hash": log.previous_hash,
                "details": f"Content tampering detected at record ID {log.id}: signature mismatch.",
            }

        expected_prev_hash = log.current_hash

    return {
        "status": "VALID",
        "records_verified": len(logs),
        "tamper_detected": False,
        "tampered_log_id": None,
        "last_verified_hash": expected_prev_hash,
        "details": f"All {len(logs)} audit records cryptographically verified with unbroken SHA-256 chain.",
    }