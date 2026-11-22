import pytest
from app.audit.models import AuditLog
from app.audit.service import (
    GENESIS_HASH,
    calculate_log_hash,
    create_audit_log,
    verify_audit_trail,
)
from app.users.models import User
from app.users.service import hash_password
from app.users.tokens import create_access_token


@pytest.fixture
def test_admin_user(db):
    admin = User(
        username="audit.admin",
        password_hash=hash_password("AdminPass123!"),
        full_name="Audit Administrator",
        role="ADMIN",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_nurse_user(db):
    nurse = User(
        username="audit.nurse",
        password_hash=hash_password("NursePass123!"),
        full_name="Ward Nurse",
        role="NURSE",
        is_active=True,
    )
    db.add(nurse)
    db.commit()
    db.refresh(nurse)
    return nurse


def test_genesis_audit_log_has_canonical_seed_and_valid_hash(db):
    log1 = create_audit_log(
        db=db,
        user_id=1,
        action="SYSTEM_INIT",
        entity_type="SYSTEM",
        entity_id=1,
        details="System initialized",
    )
    db.commit()
    db.refresh(log1)

    assert log1.previous_hash == GENESIS_HASH
    assert len(log1.current_hash) == 64
    expected_hash = calculate_log_hash(
        previous_hash=GENESIS_HASH,
        timestamp=log1.timestamp,
        user_id=1,
        action="SYSTEM_INIT",
        entity_type="SYSTEM",
        entity_id=1,
        details="System initialized",
    )
    assert log1.current_hash == expected_hash


def test_sequential_audit_logs_chain_cryptographically(db):
    log1 = create_audit_log(db, 1, "CREATE", "PATIENT", 101, "Created patient Adanu")
    db.commit()

    log2 = create_audit_log(db, 1, "ADMIT", "ADMISSION", 201, "Admitted to Male Medical Ward")
    db.commit()

    log3 = create_audit_log(db, 1, "RECORD", "VITAL_SIGN", 301, "Recorded NEWS2 score 3")
    db.commit()

    db.refresh(log1)
    db.refresh(log2)
    db.refresh(log3)

    assert log1.previous_hash == GENESIS_HASH
    assert log2.previous_hash == log1.current_hash
    assert log3.previous_hash == log2.current_hash


def test_verify_audit_trail_returns_valid_for_intact_chain(db):
    create_audit_log(db, 1, "ACTION_1", "ENTITY", 1, "First event")
    create_audit_log(db, 1, "ACTION_2", "ENTITY", 2, "Second event")
    create_audit_log(db, 1, "ACTION_3", "ENTITY", 3, "Third event")
    db.commit()

    result = verify_audit_trail(db)
    assert result["status"] == "VALID"
    assert result["records_verified"] == 3
    assert result["tamper_detected"] is False
    assert result["tampered_log_id"] is None


def test_verify_audit_trail_detects_data_tampering(db):
    log1 = create_audit_log(db, 1, "PRESCRIBE", "MEDICATION", 1, "Administered Ceftriaxone 1g")
    log2 = create_audit_log(db, 1, "DISPENSE", "MEDICATION", 2, "Dispensed by Pharmacy")
    log3 = create_audit_log(db, 1, "DISCHARGE", "ADMISSION", 1, "Discharged home")
    db.commit()

    # Simulate malicious direct database tampering on log2 details
    log2.details = "TAMPERED: Altered dosage to 2g illegally"
    db.commit()

    result = verify_audit_trail(db)
    assert result["status"] == "TAMPER_DETECTED"
    assert result["tamper_detected"] is True
    assert result["tampered_log_id"] == log2.id
    assert "Content tampering detected" in result["details"]


def test_verify_audit_trail_detects_broken_chain(db):
    log1 = create_audit_log(db, 1, "ACTION_A", "ENTITY", 1, "Event A")
    log2 = create_audit_log(db, 1, "ACTION_B", "ENTITY", 2, "Event B")
    log3 = create_audit_log(db, 1, "ACTION_C", "ENTITY", 3, "Event C")
    db.commit()

    # Simulate malicious chain break by tampering with previous_hash
    log3.previous_hash = "deadbeef" * 8
    db.commit()

    result = verify_audit_trail(db)
    assert result["status"] == "TAMPER_DETECTED"
    assert result["tamper_detected"] is True
    assert result["tampered_log_id"] == log3.id
    assert "Chain continuity broken" in result["details"]


def test_verify_audit_trail_empty_db(db):
    result = verify_audit_trail(db)
    print("DEBUG RESULT:", result)
    assert result["status"] == "VALID"
    assert result["records_verified"] == 0
    assert result["tamper_detected"] is False


def test_verify_endpoint_success_for_admin(client, test_admin_user, db):
    create_audit_log(db, test_admin_user.id, "LOGIN", "USER", test_admin_user.id, "Admin logged in")
    db.commit()

    token = create_access_token(user_id=test_admin_user.id, username=test_admin_user.username, role=test_admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/audit/verify", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VALID"
    assert data["records_verified"] == 1
    assert data["tamper_detected"] is False


def test_verify_endpoint_forbidden_for_non_admin(client, test_nurse_user, db):
    create_audit_log(db, test_nurse_user.id, "LOGIN", "USER", test_nurse_user.id, "Nurse logged in")
    db.commit()

    token = create_access_token(user_id=test_nurse_user.id, username=test_nurse_user.username, role=test_nurse_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/audit/verify", headers=headers)
    assert response.status_code == 403
