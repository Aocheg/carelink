import pytest
from fastapi import HTTPException

from app.users.service import create_user
from app.users.tokens import create_access_token


def test_get_current_user_with_valid_token(db):
    user = create_user(
        db,
        username="current.user",
        full_name="Current User",
        role="NURSE",
        password="TestPassword123",
    )

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )

    from app.users.dependencies import get_current_user

    current_user = get_current_user(
        f"Bearer {token}",
        db,
    )

    assert current_user.id == user.id
    assert current_user.username == "current.user"


def test_get_current_user_rejects_invalid_token(db):
    from app.users.dependencies import get_current_user

    with pytest.raises(HTTPException) as exc_info:
        get_current_user("invalid-token", db)

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_missing_token(db):
    from app.users.dependencies import get_current_user

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None, db)

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_inactive_user(db):
    user = create_user(
        db,
        username="inactive.user",
        full_name="Inactive User",
        role="NURSE",
        password="TestPassword123",
    )

    user.is_active = False
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )

    from app.users.dependencies import get_current_user

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(f"Bearer {token}", db)

    assert exc_info.value.status_code == 401