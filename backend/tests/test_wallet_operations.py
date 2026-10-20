from decimal import Decimal

from database import Session
from databasemodel import  Transaction
from enums import TransactionType, TransactionStatus


def create_authenticated_user(client):
    email = "wallet-test@example.com"

    register_response = client.post(
        "/auth/register",
        json={
            "name": "Wallet Test",
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


def test_deposit_updates_balance_and_records_transaction(client):
    headers = create_authenticated_user(client)

    response = client.post(
        "/wallet/deposit",
        json={"amount": "250.00"},
        headers=headers,
    )

    assert response.status_code == 200

    wallet_response = client.get(
        "/wallet",
        headers=headers,
    )
    assert wallet_response.status_code == 200

    assert Decimal(str(wallet_response.json()["balance"])) == Decimal(
        "250.00"
    )

    with Session() as db:
        transaction = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_type == TransactionType.DEPOSIT
            )
            .first()
        )

        assert transaction is not None
        assert transaction.status == TransactionStatus.SUCCESS
        assert transaction.amount == Decimal("250.00")


def test_successful_withdrawal_updates_balance(client):
    headers = create_authenticated_user(client)

    deposit_response = client.post(
        "/wallet/deposit",
        json={"amount": "300.00"},
        headers=headers,
    )
    assert deposit_response.status_code == 200

    withdrawal_response = client.post(
        "/wallet/withdraw",
        json={"amount": "100.00"},
        headers=headers,
    )
    assert withdrawal_response.status_code == 200

    wallet_response = client.get(
        "/wallet",
        headers=headers,
    )
    assert wallet_response.status_code == 200

    assert Decimal(str(wallet_response.json()["balance"])) == Decimal(
        "200.00"
    )

    with Session() as db:
        transaction = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_type == TransactionType.WITHDRAWAL
            )
            .first()
        )

        assert transaction is not None
        assert transaction.status == TransactionStatus.SUCCESS
        assert transaction.amount == Decimal("100.00")


def test_insufficient_withdrawal_preserves_balance_and_records_failure(
    client,
):
    headers = create_authenticated_user(client)

    response = client.post(
        "/wallet/withdraw",
        json={"amount": "50.00"},
        headers=headers,
    )

    assert response.status_code == 400

    wallet_response = client.get(
        "/wallet",
        headers=headers,
    )
    assert wallet_response.status_code == 200

    assert Decimal(str(wallet_response.json()["balance"])) == Decimal(
        "0.00"
    )

    with Session() as db:
        transaction = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_type == TransactionType.WITHDRAWAL
            )
            .first()
        )

        assert transaction is not None
        assert transaction.status == TransactionStatus.FAILED
        assert transaction.amount == Decimal("50.00")