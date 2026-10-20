def register_user(client, email="auth-test@example.com"):
    return client.post(
        "/auth/register",
        json={
            "name": "Authentication Test",
            "email": email,
            "password": "TestPass@123",
        },
    )


def login_user(client, email="auth-test@example.com"):
    return client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPass@123",
        },
    )


def test_login_returns_access_and_refresh_tokens(client):
    register_response = register_user(client)
    assert register_response.status_code == 201

    response = login_user(client)

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


def test_login_rejects_incorrect_password(client):
    register_response = register_user(client)
    assert register_response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": "auth-test@example.com",
            "password": "WrongPass@123",
        },
    )

    assert response.status_code == 401


def test_authenticated_user_can_access_profile(client):
    register_response = register_user(client)
    assert register_response.status_code == 201

    login_response = login_user(client)
    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "auth-test@example.com"
    assert data["name"] == "Authentication Test"
    assert data["public_wallet_id"]
    assert len(data["public_wallet_id"]) == 12


def test_profile_rejects_missing_token(client):
    response = client.get("/users/me")

    assert response.status_code == 401


def test_refresh_token_returns_working_access_token(client):
    register_response = register_user(client)
    assert register_response.status_code == 201

    login_response = login_user(client)
    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200

    new_access_token = refresh_response.json()["access_token"]
    assert new_access_token

    profile_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )

    assert profile_response.status_code == 200