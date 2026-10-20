
from decimal import Decimal
from sqlalchemy import Enum as SAEnum
from enums import TransactionStatus,TransactionType
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Numeric, Index, Identity, text,CheckConstraint, UniqueConstraint
from sqlalchemy.orm import declarative_base



Base = declarative_base()
class User(Base):
    __tablename__ = "user"
    id = Column(Integer,primary_key=True,autoincrement=True)
    name = Column(String(100),nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)


class Wallet(Base):
    __tablename__ = "wallet"
    id=Column(Integer,Identity(),unique=True,nullable=False)
    public_wallet_id = Column(String(12),primary_key=True,nullable=False)
    user_id=Column(Integer,ForeignKey("user.id"),unique=True,nullable=False)
    balance=Column(Numeric(12,2),nullable=False,default=Decimal("0.00"),server_default=text("0.00"))
    __table_args__ = (CheckConstraint("char_length(public_wallet_id) = 12",name="ck_wallet_public_id_length"),CheckConstraint("balance>=0",name="ck_wallet_balance_nonnegative"),)



class Transaction(Base):
    __tablename__ = "transfer"

    # Internal row number only
    id = Column(
        Integer,
        Identity(),
        unique=True,
        nullable=False
    )

    # Actual transaction identifier used by the application
    public_transaction_id = Column(
        String(15),
        primary_key=True,
        nullable=False
    )

    # User who initiated the operation
    user_id = Column(
        Integer,
        ForeignKey("user.id"),
        nullable=False
    )

    # These reference the public wallet IDs directly
    sender_wallet_id = Column(
        String(12),
        ForeignKey("wallet.public_wallet_id"),
        nullable=True
    )

    receiver_wallet_id = Column(
        String(12),
        ForeignKey("wallet.public_wallet_id"),
        nullable=True
    )

    amount = Column(
        Numeric(12, 2),
        nullable=False
    )
    description = Column(String(255), nullable=True)
    transaction_type = Column(
        SAEnum(
            TransactionType,
            name="transaction_type_enum",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ]
        ),
        nullable=False
    )

    status = Column(
        SAEnum(
            TransactionStatus,
            name="transaction_status_enum",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ]
        ),
        nullable=False
    )

    # Supplied by the frontend for transfer idempotency
    idempotency_key = Column(
        String(100),
        nullable=True
    )

    failure_reason = Column(
        String(255),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_transfer_user_key"
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_transfer_amount_positive"
        ),
        CheckConstraint(
            "char_length(public_transaction_id) = 15",
            name="ck_transfer_public_id_length"
        ),
        Index(
            "ix_transfer_user_created",
            "user_id",
            "created_at"
        ),
        Index(
            "ix_transfer_sender",
            "sender_wallet_id"
        ),
        Index(
            "ix_transfer_receiver",
            "receiver_wallet_id"
        )
    )

