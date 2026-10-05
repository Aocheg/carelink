from datetime import timedelta

import pytest

from app.users.tokens import create_access_token, decode_access_token


def test_create_access_token_contains_user_information():
    token = create_access_token(
        user_id=1,
        username="nurse.john",
        role="NURSE",
    )

    payload = decode_access_token(token)

    assert payload["sub"] == "1"
    assert payload["username"] == "nurse.john"
    assert payload["role"] == "NURSE"


def test_tampered_token_is_rejected():
    token = create_access_token(
        user_id=1,
        username="nurse.john",
        role="NURSE",
    )

    tampered_token = token[:-1] + (
        "a" if token[-1] != "a" else "b"
    )

    with pytest.raises(ValueError):
        decode_access_token(tampered_token)


def test_expired_token_is_rejected():
    token = create_access_token(
        user_id=1,
        username="nurse.john",
        role="NURSE",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(ValueError):
        decode_access_token(token)