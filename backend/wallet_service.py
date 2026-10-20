from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from databasemodel import User, Wallet, Transaction
from enums import TransactionType, TransactionStatus
from utils import generate_transaction_id


def deposit_to_wallet(
    db: Session,
    current_user: User,
    amount,
) -> dict:
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == current_user.id)
        .with_for_update()
        .first()
    )

    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )

    wallet_id = wallet.public_wallet_id
    new_balance = wallet.balance + amount

    try:
        wallet.balance = new_balance

        deposit_transaction = Transaction(
            public_transaction_id=generate_transaction_id(db),
            user_id=current_user.id,
            amount=amount,
            sender_wallet_id=None,
            receiver_wallet_id=wallet_id,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.SUCCESS,
        )

        db.add(deposit_transaction)
        db.commit()

        return {
            "message": "Deposit successful",
            "public_wallet_id": wallet_id,
            "balance": str(new_balance),
        }

    except Exception as exc:
        db.rollback()

        # Attempt to preserve a record of the failed deposit.
        # This is best-effort: the database might also reject this record.
        try:
            failed_deposit = Transaction(
                public_transaction_id=generate_transaction_id(db),
                user_id=current_user.id,
                amount=amount,
                sender_wallet_id=None,
                receiver_wallet_id=wallet_id,
                transaction_type=TransactionType.DEPOSIT,
                status=TransactionStatus.FAILED,
                failure_reason="Deposit processing failed",
            )

            db.add(failed_deposit)
            db.commit()

        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deposit failed",
        ) from exc


def withdraw_from_wallet(
    db: Session,
    current_user: User,
    amount,
) -> dict:
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The amount must be greater than zero",
        )

    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == current_user.id)
        .with_for_update()
        .first()
    )

    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )

    wallet_id = wallet.public_wallet_id

    if wallet.balance < amount:
        # Release the wallet lock before recording the failed attempt.
        db.rollback()

        try:
            failed_withdrawal = Transaction(
                public_transaction_id=generate_transaction_id(db),
                user_id=current_user.id,
                amount=amount,
                sender_wallet_id=wallet_id,
                receiver_wallet_id=None,
                transaction_type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.FAILED,
                failure_reason="Insufficient balance",
            )

            db.add(failed_withdrawal)
            db.commit()

        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance",
        )

    new_balance = wallet.balance - amount

    try:
        wallet.balance = new_balance

        withdrawal_transaction = Transaction(
            public_transaction_id=generate_transaction_id(db),
            user_id=current_user.id,
            amount=amount,
            sender_wallet_id=wallet_id,
            receiver_wallet_id=None,
            transaction_type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.SUCCESS,
        )

        db.add(withdrawal_transaction)
        db.commit()

        return {
            "message": "Withdrawal successful",
            "public_wallet_id": wallet_id,
            "balance": str(new_balance),
            "public_transaction_id": (
                withdrawal_transaction.public_transaction_id
            ),
        }

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Withdrawal processing failed",
        ) from exc
