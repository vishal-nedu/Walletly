from enums import TransactionStatus, TransactionType
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from databasemodel import User,Wallet
from model import Transfer as TransferSchema
from databasemodel import Transaction as TransferModel
from sqlalchemy.exc import IntegrityError
from utils import generate_transaction_id

def existing_transfer_response(
    existing,
    sender_wallet_id,
    receiver_wallet_id,
    amount,
    description,
):
    # A key cannot represent a different operation.
    if (
        existing.transaction_type != TransactionType.TRANSFER
        or existing.sender_wallet_id != sender_wallet_id
        or existing.receiver_wallet_id != receiver_wallet_id
        or existing.amount != amount
        or existing.description != description
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key already used for a different transfer"
        )

    # A retry of a recorded failed attempt must not execute again.
    if existing.status == TransactionStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=existing.failure_reason or "Previous transfer failed"
        )

    return {
        "message": "Transfer already processed",
        "public_transaction_id": existing.public_transaction_id,
        "sender_wallet_id": existing.sender_wallet_id,
        "receiver_wallet_id": existing.receiver_wallet_id,
        "amount": str(existing.amount),
        "description": existing.description,
        "status": existing.status.value
    }

def process_transfer(db: Session,current_user: User,transfer: TransferSchema,idempotency_key: str,) -> dict:
    if transfer.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer amount must be greater than zero"
        )

    try:
        # Derive the sender from the authenticated user.
        sender = (
            db.query(Wallet)
            .filter(Wallet.user_id == current_user.id)
            .first()
        )

        if sender is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sender wallet not found"
            )

        sender_public_id = sender.public_wallet_id
        receiver_public_id = transfer.receiver_wallet_id

        if sender_public_id == receiver_public_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sender and receiver wallets cannot be the same"
            )

        # Fast path for an already-processed request.
        existing = (
            db.query(TransferModel)
            .filter(
                TransferModel.user_id == current_user.id,
                TransferModel.idempotency_key == idempotency_key
            )
            .first()
        )

        if existing is not None:
            result = existing_transfer_response(
                existing,
                sender_public_id,
                receiver_public_id,
                transfer.amount
                , transfer.description
            )
            db.rollback()
            return result

        # Lock both wallets in one consistent order.
        wallet_ids = sorted([
            sender_public_id,
            receiver_public_id
        ])

        wallets = (
            db.query(Wallet)
            .filter(Wallet.public_wallet_id.in_(wallet_ids))
            .order_by(Wallet.public_wallet_id.asc())
            .with_for_update()
            .all()
        )

        wallet_map = {
            wallet.public_wallet_id: wallet
            for wallet in wallets
        }

        sen_wallet = wallet_map.get(sender_public_id)
        rec_wallet = wallet_map.get(receiver_public_id)

        if sen_wallet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sender wallet not found"
            )

        if sen_wallet.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access restricted"
            )

        if rec_wallet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiver wallet not found"
            )

        # Recheck after locking: another simultaneous request may
        # have completed the same operation while this request waited.
        existing = (
            db.query(TransferModel)
            .filter(
                TransferModel.user_id == current_user.id,
                TransferModel.idempotency_key == idempotency_key
            )
            .first()
        )

        if existing is not None:
            result = existing_transfer_response(
                existing,
                sender_public_id,
                receiver_public_id,
                transfer.amount
                , transfer.description
            )
            db.rollback()
            return result

        # No balance changes have occurred yet.
        if sen_wallet.balance < transfer.amount:
            # Record the failed business attempt in this transaction.
            failed_transfer = TransferModel(
                public_transaction_id=generate_transaction_id(db),
                user_id=current_user.id,
                sender_wallet_id=sen_wallet.public_wallet_id,
                receiver_wallet_id=rec_wallet.public_wallet_id,
                amount=transfer.amount,
                description=transfer.description,
                transaction_type=TransactionType.TRANSFER,
                status=TransactionStatus.FAILED,
                idempotency_key=idempotency_key,
                failure_reason="Insufficient balance"
            )

            db.add(failed_transfer)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient balance"
            )

        # Debit, credit and successful transaction record are atomic.
        sen_wallet.balance -= transfer.amount
        rec_wallet.balance += transfer.amount

        new_transfer = TransferModel(
            public_transaction_id=generate_transaction_id(db),
            user_id=current_user.id,
            sender_wallet_id=sen_wallet.public_wallet_id,
            receiver_wallet_id=rec_wallet.public_wallet_id,
            amount=transfer.amount,
            description=transfer.description,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.SUCCESS,
            idempotency_key=idempotency_key
        )

        db.add(new_transfer)
        db.flush()

        result = {
            "message": "Transfer successful",
            "public_transaction_id": new_transfer.public_transaction_id,
            "sender_wallet_id": sen_wallet.public_wallet_id,
            "receiver_wallet_id": rec_wallet.public_wallet_id,
            "description": new_transfer.description,
            "amount": str(new_transfer.amount),
            "status": TransactionStatus.SUCCESS.value
        }

        db.commit()
        return result

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()

        # The unique constraint is the final safeguard if a duplicate
        # key reaches insertion despite the application-level checks.
        existing = (
            db.query(TransferModel)
            .filter(
                TransferModel.user_id == current_user.id,
                TransferModel.idempotency_key == idempotency_key
            )
            .first()
        )

        if existing is not None:
            sender = (
                db.query(Wallet)
                .filter(Wallet.user_id == current_user.id)
                .first()
            )

            if sender is not None:
                return existing_transfer_response(
                    existing,
                    sender.public_wallet_id,
                    transfer.receiver_wallet_id,
                    transfer.amount,
                    transfer.description
                )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transfer failed"
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transfer failed"
        )