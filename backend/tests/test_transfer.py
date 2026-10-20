
from decimal import Decimal

import transfer_service
from database import Session
from databasemodel import Transaction
from enums import TransactionStatus, TransactionType



def create_authenticated_user(client, email):
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Transfer Test",
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
    headers = {"Authorization": f"Bearer {token}"}

    wallet_response = client.get("/wallet", headers=headers)
    assert wallet_response.status_code == 200

    wallet_id = wallet_response.json()["wallet_id"]
    return headers, wallet_id


def test_successful_transfer_updates_balances_and_saves_description(client):
    sender_headers, sender_wallet_id = create_authenticated_user(
        client, "sender-transfer@example.com"
    )
    receiver_headers, receiver_wallet_id = create_authenticated_user(
        client, "receiver-transfer@example.com"
    )

    deposit_response = client.post(
        "/wallet/deposit",
        json={"amount": "200.00"},
        headers=sender_headers,
    )
    assert deposit_response.status_code == 200

    response = client.post(
        "/transfers",
        json={
            "receiver_wallet_id": receiver_wallet_id,
            "amount": "75.00",
            "description": "Dinner payment",
        },
        headers={
            **sender_headers,
            "Idempotency-Key": "success-transfer-001",
        },
    )

    assert response.status_code == 200
    transaction_id = response.json()["public_transaction_id"]

    sender_balance = client.get(
        "/wallet", headers=sender_headers
    ).json()["balance"]

    receiver_balance = client.get(
        "/wallet", headers=receiver_headers
    ).json()["balance"]

    assert Decimal(str(sender_balance)) == Decimal("125.00")
    assert Decimal(str(receiver_balance)) == Decimal("75.00")

    with Session() as db:
        transaction = (
            db.query(Transaction)
            .filter(
                Transaction.public_transaction_id == transaction_id
            )
            .first()
        )

        assert transaction is not None
        assert transaction.transaction_type == TransactionType.TRANSFER
        assert transaction.status == TransactionStatus.SUCCESS
        assert transaction.amount == Decimal("75.00")
        assert transaction.description == "Dinner payment"


def test_insufficient_funds_preserves_balances_and_records_failure(client):
    sender_headers, sender_wallet_id = create_authenticated_user(
        client, "insufficient-sender@example.com"
    )
    receiver_headers, receiver_wallet_id = create_authenticated_user(
        client, "insufficient-receiver@example.com"
    )

    response = client.post(
        "/transfers",
        json={
            "receiver_wallet_id": receiver_wallet_id,
            "amount": "50.00",
            "description": "Insufficient funds test",
        },
        headers={
            **sender_headers,
            "Idempotency-Key": "insufficient-transfer-001",
        },
    )

    assert response.status_code == 400

    sender_balance = client.get(
        "/wallet", headers=sender_headers
    ).json()["balance"]

    receiver_balance = client.get(
        "/wallet", headers=receiver_headers
    ).json()["balance"]

    assert Decimal(str(sender_balance)) == Decimal("0.00")
    assert Decimal(str(receiver_balance)) == Decimal("0.00")

    with Session() as db:
        transaction = (
            db.query(Transaction)
            .filter(
                Transaction.idempotency_key == "insufficient-transfer-001"
            )
            .first()
        )

        assert transaction is not None
        assert transaction.status == TransactionStatus.FAILED
        assert transaction.failure_reason == "Insufficient balance"


def test_retry_with_same_key_does_not_transfer_twice(client):
    sender_headers, sender_wallet_id = create_authenticated_user(
        client, "retry-sender@example.com"
    )
    receiver_headers, receiver_wallet_id = create_authenticated_user(
        client, "retry-receiver@example.com"
    )

    deposit_response = client.post(
        "/wallet/deposit",
        json={"amount": "100.00"},
        headers=sender_headers,
    )
    assert deposit_response.status_code == 200

    payload = {
        "receiver_wallet_id": receiver_wallet_id,
        "amount": "40.00",
        "description": "Retry test",
    }
    headers = {
        **sender_headers,
        "Idempotency-Key": "retry-transfer-001",
    }

    first_response = client.post(
        "/transfers", json=payload, headers=headers
    )
    second_response = client.post(
        "/transfers", json=payload, headers=headers
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    sender_balance = client.get(
        "/wallet", headers=sender_headers
    ).json()["balance"]

    receiver_balance = client.get(
        "/wallet", headers=receiver_headers
    ).json()["balance"]

    assert Decimal(str(sender_balance)) == Decimal("60.00")
    assert Decimal(str(receiver_balance)) == Decimal("40.00")

    with Session() as db:
        count = (
            db.query(Transaction)
            .filter(
                Transaction.idempotency_key == "retry-transfer-001"
            )
            .count()
        )

        assert count == 1


def test_same_key_with_different_description_returns_conflict(client):
    sender_headers, sender_wallet_id = create_authenticated_user(
        client, "conflict-sender@example.com"
    )
    receiver_headers, receiver_wallet_id = create_authenticated_user(
        client, "conflict-receiver@example.com"
    )

    deposit_response = client.post(
        "/wallet/deposit",
        json={"amount": "100.00"},
        headers=sender_headers,
    )
    assert deposit_response.status_code == 200

    headers = {
        **sender_headers,
        "Idempotency-Key": "description-conflict-001",
    }

    first_response = client.post(
        "/transfers",
        json={
            "receiver_wallet_id": receiver_wallet_id,
            "amount": "30.00",
            "description": "First payment",
        },
        headers=headers,
    )

    second_response = client.post(
        "/transfers",
        json={
            "receiver_wallet_id": receiver_wallet_id,
            "amount": "30.00",
            "description": "Different payment",
        },
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409

    sender_balance = client.get(
        "/wallet", headers=sender_headers
    ).json()["balance"]

    receiver_balance = client.get(
        "/wallet", headers=receiver_headers
    ).json()["balance"]

    assert Decimal(str(sender_balance)) == Decimal("70.00")
    assert Decimal(str(receiver_balance)) == Decimal("30.00")

    with Session() as db:
        count = (
            db.query(Transaction)
            .filter(
                Transaction.idempotency_key
                == "description-conflict-001"
            )
            .count()
        )

        assert count == 1


def test_transfer_database_failure_rolls_back_both_balances(
    client, monkeypatch
):
    sender_headers, sender_wallet_id = create_authenticated_user(
        client, "rollback-sender@example.com"
    )
    receiver_headers, receiver_wallet_id = create_authenticated_user(
        client, "rollback-receiver@example.com"
    )

    # Give the sender sufficient money for the transfer.
    deposit_response = client.post(
        "/wallet/deposit",
        json={"amount": "100.00"},
        headers=sender_headers,
    )
    assert deposit_response.status_code == 200

    # Obtain an existing transaction ID that will cause a primary-key
    # collision when the new transfer record is inserted.
    with Session() as db:
        existing_transaction = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_type == TransactionType.DEPOSIT,
                Transaction.receiver_wallet_id == sender_wallet_id,
            )
            .first()
        )

        assert existing_transaction is not None
        duplicate_id = existing_transaction.public_transaction_id

    # Force the transfer to reuse the existing transaction ID.
    monkeypatch.setattr(
        transfer_service,
        "generate_transaction_id",
        lambda  db: duplicate_id,
    )

    response = client.post(
        "/transfers",
        json={
            "receiver_wallet_id": receiver_wallet_id,
            "amount": "40.00",
            "description": "Rollback test",
        },
        headers={
            **sender_headers,
            "Idempotency-Key": "rollback-transfer-001",
        },
    )

    # The duplicate primary key should make the transfer fail.
    assert response.status_code == 500

    # Verify neither balance was modified by the failed transfer.
    sender_balance = client.get(
        "/wallet", headers=sender_headers
    ).json()["balance"]

    receiver_balance = client.get(
        "/wallet", headers=receiver_headers
    ).json()["balance"]

    assert Decimal(str(sender_balance)) == Decimal("100.00")
    assert Decimal(str(receiver_balance)) == Decimal("0.00")

    with Session() as db:
        attempted_transfer_count = (
            db.query(Transaction)
            .filter(
                Transaction.idempotency_key == "rollback-transfer-001"
            )
            .count()
        )

        assert attempted_transfer_count == 0

        # The original deposit must not have been deleted or changed.
        original_transaction_count = (
            db.query(Transaction)
            .filter(
                Transaction.public_transaction_id == duplicate_id
            )
            .count()
        )

        assert original_transaction_count == 1
