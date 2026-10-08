from datetime import timedelta

from app.users.service import create_user
from app.users.tokens import create_access_token


def test_get_current_user_me_without_token_returns_401(client):
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_get_current_user_me_with_malformed_auth_header_returns_401(client):
    # Header missing "Bearer " prefix
    response = client.get(
        "/users/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authorization header"

    # Header with "Bearer " but empty token
    response_empty = client.get(
        "/users/me",
        headers={"Authorization": "Bearer   "},
    )
    assert response_empty.status_code == 401
    assert response_empty.json()["detail"] == "Authentication required"


def test_get_current_user_me_with_invalid_token_returns_401(client):
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token"


def test_get_current_user_me_with_expired_token_returns_401(client, db):
    user = create_user(
        db,
        username="expired.user",
        full_name="Expired User",
        role="NURSE",
        password="ValidPassword123",
    )

    expired_token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token"


def test_get_current_user_me_with_inactive_user_returns_401(client, db):
    user = create_user(
        db,
        username="inactive.doctor",
        full_name="Inactive Doctor",
        role="DOCTOR",
        password="ValidPassword123",
    )
    user.is_active = False
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "User account is inactive"


def test_get_current_user_me_with_nonexistent_user_token_returns_401(client):
    token = create_access_token(
        user_id=999999,
        username="ghost.user",
        role="NURSE",
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"



def test_get_current_user_me_with_valid_token_returns_user_profile(client, db):
    user = create_user(
        db,
        username="dr.jane",
        full_name="Dr. Jane Smith",
        role="DOCTOR",
        password="ValidPassword123",
    )

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == user.id
    assert data["username"] == "dr.jane"
    assert data["full_name"] == "Dr. Jane Smith"
    assert data["role"] == "DOCTOR"
    assert data["is_active"] is True

    # Security check: password hashes must never be exposed
    assert "password" not in data
    assert "password_hash" not in data
