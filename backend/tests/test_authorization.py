def create_authenticated_user(client, email):
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Authorization Test",
            "email": email,
            "password": "TestPass@123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPass@123",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_unrelated_user_cannot_access_transaction_details(client):
    sender_headers = create_authenticated_user(
        client, "auth-sender@example.com"
    )
    receiver_headers = create_authenticated_user(
        client, "auth-receiver@example.com"
    )
    unrelated_headers = create_authenticated_user(
        client, "auth-unrelated@example.com"
    )

    receiver_wallet_id = client.get(
        "/wallet", headers=receiver_headers
    ).json()["wallet_id"]

    client.post(
        "/wallet/deposit",
        json={"amount": "100.00"},
        headers=sender_headers,
    )

    transfer_response = client.post(
        "/transfers",
        json={
            "receiver_wallet_id": receiver_wallet_id,
            "amount": "25.00",
            "description": "Authorization test",
        },
        headers={
            **sender_headers,
            "Idempotency-Key": "authorization-test-001",
        },
    )

    assert transfer_response.status_code == 200

    transaction_id = transfer_response.json()["public_transaction_id"]

    response = client.get(
        f"/transactions/{transaction_id}",
        headers=unrelated_headers,
    )

    assert response.status_code == 404


def test_receiver_can_access_transaction_details(client):
    sender_headers = create_authenticated_user(
        client, "receiver-access-sender@example.com"
    )
    receiver_headers = create_authenticated_user(
        client, "receiver-access-recipient@example.com"
    )

    receiver_wallet_id = client.get(
        "/wallet", headers=receiver_headers
    ).json()["wallet_id"]

    client.post(
        "/wallet/deposit",
        json={"amount": "100.00"},
        headers=sender_headers,
    )

    transfer_response = client.post(
        "/transfers",
        json={
            "receiver_wallet_id": receiver_wallet_id,
            "amount": "20.00",
            "description": "Receiver access test",
        },
        headers={
            **sender_headers,
            "Idempotency-Key": "receiver-access-001",
        },
    )

    assert transfer_response.status_code == 200

    transaction_id = transfer_response.json()["public_transaction_id"]

    response = client.get(
        f"/transactions/{transaction_id}",
        headers=receiver_headers,
    )

    assert response.status_code == 200
    assert response.json()["public_transaction_id"] == transaction_id


def test_unrelated_user_does_not_see_transaction_in_history(client):
    sender_headers = create_authenticated_user(
        client, "history-sender@example.com"
    )
    receiver_headers = create_authenticated_user(
        client, "history-receiver@example.com"
    )
    unrelated_headers = create_authenticated_user(
        client, "history-unrelated@example.com"
    )

    receiver_wallet_id = client.get(
        "/wallet", headers=receiver_headers
    ).json()["wallet_id"]

    client.post(
        "/wallet/deposit",
        json={"amount": "100.00"},
        headers=sender_headers,
    )

    transfer_response = client.post(
        "/transfers",
        json={
            "receiver_wallet_id": receiver_wallet_id,
            "amount": "30.00",
        },
        headers={
            **sender_headers,
            "Idempotency-Key": "history-authorization-001",
        },
    )

    assert transfer_response.status_code == 200
    transaction_id = transfer_response.json()["public_transaction_id"]

    response = client.get(
        "/transactions",
        headers=unrelated_headers,
    )

    assert response.status_code == 200

    transaction_ids = {
        item["public_transaction_id"]
        for item in response.json()["items"]
    }

    assert transaction_id not in transaction_ids