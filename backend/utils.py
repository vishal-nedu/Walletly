import secrets
import string

from sqlalchemy.orm import Session

from databasemodel import Transaction,Wallet


def generate_transaction_id(db: Session) -> str:
    characters = string.ascii_uppercase + string.digits + string.ascii_lowercase

    while True:
        candidate = "".join(
            secrets.choice(characters)
            for _ in range(15)
        )

        exists = (
            db.query(Transaction.public_transaction_id)
            .filter(
                Transaction.public_transaction_id == candidate
            )
            .first()
        )

        if exists is None:
            return candidate

def generate_public_wallet_id(db: Session) -> str:
    characters = string.ascii_uppercase + string.digits

    while True:
        candidate = ''.join(
            secrets.choice(characters)
            for _ in range(12)
        )

        exists = db.query(Wallet.public_wallet_id).filter(
            Wallet.public_wallet_id == candidate
        ).first()

        if exists is None:
            return candidate