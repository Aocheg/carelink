from fastapi.testclient import TestClient

from app.main import app
from app.users.security import hash_password, verify_password
from app.users.service import create_user

def test_hash_password_does_not_return_plaintext():
    password = "mySecret123"

    password_hash = hash_password(password)

    assert password_hash != password
    assert isinstance(password_hash, str)


def test_correct_password_verifies():
    password = "mySecret123"

    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_wrong_password_does_not_verify():
    password = "mySecret123"

    password_hash = hash_password(password)

    assert verify_password("wrongPassword", password_hash) is False


def test_same_password_produces_different_hashes():
    password = "mySecret123"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash

    assert verify_password(password, first_hash) is True
    assert verify_password(password, second_hash) is True

def test_empty_password_is_rejected():
    try:
        hash_password("")
    except ValueError:
        return

    assert False, "Empty passwords should be rejected"


def test_malformed_hash_does_not_verify():
    assert verify_password(
        "mySecret123",
        "not-a-valid-password-hash",
    ) is False

def test_create_user_stores_password_hash(db):
    user = create_user(
        db,
        username="security.test",
        full_name="Security Test",
        role="NURSE",
        password="mySecret123",
    )

    assert user.password_hash != "mySecret123"
    assert user.password_hash != "NOT_SET_YET"

    assert verify_password(
        "mySecret123",
        user.password_hash,
    ) is True

    assert verify_password(
        "wrongPassword",
        user.password_hash,
    ) is False

def test_create_user_api_hashes_password(client):
    response = client.post(
        "/users/",
        json={
            "username": "api.security",
            "full_name": "API Security User",
            "role": "NURSE",
            "password": "mySecret123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["username"] == "api.security"
    assert data["full_name"] == "API Security User"
    assert data["role"] == "NURSE"
    assert data["is_active"] is True

    assert "password" not in data
    assert "password_hash" not in data
