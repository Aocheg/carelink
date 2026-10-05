from app.users.service import create_user


def test_login_with_correct_credentials(client, db):
    create_user(
        db,
        username="login.test",
        full_name="Login Test User",
        role="NURSE",
        password="mySecret123",
    )

    response = client.post(
        "/users/login",
        json={
            "username": "login.test",
            "password": "mySecret123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_with_wrong_password(client, db):
    create_user(
        db,
        username="wrong.password",
        full_name="Wrong Password User",
        role="NURSE",
        password="mySecret123",
    )

    response = client.post(
        "/users/login",
        json={
            "username": "wrong.password",
            "password": "wrongPassword",
        },
    )

    assert response.status_code == 401


def test_login_with_unknown_username(client):
    response = client.post(
        "/users/login",
        json={
            "username": "does.not.exist",
            "password": "mySecret123",
        },
    )

    assert response.status_code == 401