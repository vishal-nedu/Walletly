from pydantic import BaseModel,EmailStr,Field,StringConstraints
from decimal import Decimal
from datetime import datetime
from typing import Annotated
from enums import TransactionType,TransactionStatus
PublicWalletId = Annotated[
    str,
    StringConstraints(
        min_length=12,
        max_length=12,
        pattern=r"^[A-Z0-9]{12}$"
    )
]

PublicTransactionId = Annotated[
    str,
    StringConstraints(
        min_length=15,
        max_length=15,
        pattern=r"^[A-Z0-9a-z]{15}$"
    )
]

PositiveAmount = Annotated[
    Decimal,
    Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )
]
NonNegativeAmount = Annotated[
    Decimal,
    Field(
        ge=0,
        max_digits=12,
        decimal_places=2
    )
]
class UserBase(BaseModel):
    name: str=Field(min_length=1,max_length=100)

class User(UserBase):
    id:int


class Wallet(BaseModel):
    public_wallet_id:PublicWalletId
    balance:NonNegativeAmount



class TransferResponse(BaseModel):
    public_transaction_id: PublicTransactionId
    sender_wallet_id: PublicWalletId | None = None
    receiver_wallet_id: PublicWalletId| None = None
    amount: PositiveAmount
    description: str | None = None
    transaction_type: TransactionType
    status: TransactionStatus
    failure_reason: str | None = None
    created_at: datetime

class UserRegister(UserBase):
    email: EmailStr
    password: str=Field(min_length=8)


class UserResponse(UserBase):
    id: int

    email: EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str
class AmountRequest(BaseModel):
    amount:PositiveAmount

class Transfer(AmountRequest):
    receiver_wallet_id:PublicWalletId
    description: str | None = Field(default=None, max_length=255)

class DepositRequest(AmountRequest):
    pass

class WithdrawRequest(AmountRequest):
    pass