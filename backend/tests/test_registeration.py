from database import Session
from databasemodel import User, Wallet



def test_register_user_creates_user_and_wallet(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "test-register@example.com",
            "password": "TestPass@123",
        },
    )

    assert response.status_code == 201

    with Session() as db:
        user = (
            db.query(User)
            .filter(User.email == "test-register@example.com")
            .first()
        )

        assert user is not None
        assert user.name == "Test User"
        assert user.hashed_password != "TestPass@123"

        wallet = (
            db.query(Wallet)
            .filter(Wallet.user_id == user.id)
            .first()
        )

        assert wallet is not None
        assert len(wallet.public_wallet_id) == 12
        assert wallet.balance == 0


def test_duplicate_email_registration_is_rejected(client):
    payload = {
        "name": "Test User",
        "email": "duplicate@example.com",
        "password": "TestPass@123",
    }

    first_response = client.post(
        "/auth/register",
        json=payload,
    )

    second_response = client.post(
        "/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    with Session() as db:
        user_count = (
            db.query(User)
            .filter(User.email == "duplicate@example.com")
            .count()
        )

        wallet_count = (
            db.query(Wallet)
            .join(User, Wallet.user_id == User.id)
            .filter(User.email == "duplicate@example.com")
            .count()
        )

        assert user_count == 1
        assert wallet_count == 1