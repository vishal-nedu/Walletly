
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from databasemodel import User, Wallet, Transaction
from enums import TransactionType, TransactionStatus
from model import TransferResponse


def get_transaction_history(
    db: Session,
    current_user: User,
    page: int = 1,
    limit: int = 3,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    direction: str | None = None,
    transaction_type: TransactionType | None = None,
    transaction_status: TransactionStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    # Find the wallet belonging to the authenticated user.
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == current_user.id)
        .first()
    )

    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )

    wallet_id = wallet.public_wallet_id

    # Only retrieve transactions involving this user's wallet.
    transactions = db.query(Transaction).filter(
        or_(
            Transaction.sender_wallet_id == wallet_id,
            Transaction.receiver_wallet_id == wallet_id,
        )
    )

    # Search transaction IDs and the participating wallet IDs.
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"

        transactions = transactions.filter(
            or_(
                Transaction.public_transaction_id.ilike(search_pattern),
                Transaction.sender_wallet_id.ilike(search_pattern),
                Transaction.receiver_wallet_id.ilike(search_pattern),
            )
        )

    # Validate and apply the sent/received filter.
    if direction is not None:
        if direction not in ("sent", "received"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direction must be 'sent' or 'received'",
            )

        if direction == "sent":
            transactions = transactions.filter(
                Transaction.sender_wallet_id == wallet_id
            )
        else:
            transactions = transactions.filter(
                Transaction.receiver_wallet_id == wallet_id
            )

    # Filter by type and status.
    if transaction_type is not None:
        transactions = transactions.filter(
            Transaction.transaction_type == transaction_type
        )

    if transaction_status is not None:
        transactions = transactions.filter(
            Transaction.status == transaction_status
        )

    # Validate and apply the amount range.
    if (
        min_amount is not None
        and max_amount is not None
        and min_amount > max_amount
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_amount cannot exceed max_amount",
        )

    if min_amount is not None:
        transactions = transactions.filter(
            Transaction.amount >= min_amount
        )

    if max_amount is not None:
        transactions = transactions.filter(
            Transaction.amount <= max_amount
        )

    # Validate and apply the date range.
    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date",
        )

    if start_date is not None:
        start_datetime = datetime.combine(
            start_date,
            time.min,
            tzinfo=timezone.utc,
        )

        transactions = transactions.filter(
            Transaction.created_at >= start_datetime
        )

    if end_date is not None:
        next_day = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )

        transactions = transactions.filter(
            Transaction.created_at < next_day
        )

    # Whitelist sorting fields instead of accepting arbitrary columns.
    sort_columns = {
        "created_at": Transaction.created_at,
        "amount": Transaction.amount,
        "public_transaction_id": Transaction.public_transaction_id,
    }

    if sort_by not in sort_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sort_by field",
        )

    if sort_order not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_order must be 'asc' or 'desc'",
        )

    sort_column = sort_columns[sort_by]
    ordering = asc if sort_order == "asc" else desc

    # Count filtered results before pagination.
    total = transactions.count()

    results = (
        transactions
        .order_by(
            ordering(sort_column),
            Transaction.public_transaction_id.asc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "items": [
            TransferResponse(
                public_transaction_id=transaction.public_transaction_id,
                sender_wallet_id=transaction.sender_wallet_id,
                receiver_wallet_id=transaction.receiver_wallet_id,
                amount=transaction.amount,
                description=transaction.description,
                transaction_type=transaction.transaction_type,
                status=transaction.status,
                failure_reason=transaction.failure_reason,
                created_at=transaction.created_at,
            )
            for transaction in results
        ],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }


def get_transaction_details(
    db: Session,
    current_user: User,
    public_transaction_id: str,
) -> TransferResponse:
    # Find the authenticated user's wallet.
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == current_user.id)
        .first()
    )

    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )

    # Return the transaction only if this user's wallet is involved.
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.public_transaction_id == public_transaction_id,
            or_(
                Transaction.sender_wallet_id == wallet.public_wallet_id,
                Transaction.receiver_wallet_id == wallet.public_wallet_id,
            ),
        )
        .first()
    )

    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return TransferResponse(
        public_transaction_id=transaction.public_transaction_id,
        sender_wallet_id=transaction.sender_wallet_id,
        receiver_wallet_id=transaction.receiver_wallet_id,
        amount=transaction.amount,
        description=transaction.description,
        transaction_type=transaction.transaction_type,
        status=transaction.status,
        failure_reason=transaction.failure_reason,
        created_at=transaction.created_at,
    )
