
from datetime import date
from decimal import Decimal

import databasemodel
from jose import JWTError, jwt

from sqlalchemy.exc import IntegrityError

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    Header,
    Path,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from auth import (
    oauth2_scheme,
    verify_access_token,
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
)
from database import Session, engine
from databasemodel import User, Wallet

from enums import TransactionType, TransactionStatus
from model import (
    Transfer as TransferSchema,
    UserRegister,
    UserLogin,
    RefreshTokenRequest,
    DepositRequest,
    WithdrawRequest,
)
from security import get_password_hash, verify_password
from transfer_service import process_transfer
from utils import generate_public_wallet_id
from wallet_service import deposit_to_wallet, withdraw_from_wallet
from transaction_service import (get_transaction_details,get_transaction_history)

app = FastAPI()
databasemodel.Base.metadata.create_all(bind=engine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db=Session()
    try:
        yield db
    finally:
        db.close()
def get_current_user(token:str=Depends(oauth2_scheme),db:Session=Depends(get_db)):
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")

    if user_id is None or not str(user_id).isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user

@app.get("/users/me")
def get_me(current_user = Depends(get_current_user),db:Session=Depends(get_db)):
    wallet=db.query(Wallet).filter(current_user.id==Wallet.user_id).first();
    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found"
        )
    return {
        "id":current_user.id,
        "public_wallet_id": wallet.public_wallet_id,
        "name": current_user.name,
        "email": current_user.email
    }

@app.get("/")
def home():
    return "welcome to wallet system"




@app.post("/auth/register")
def create(user:UserRegister,db:Session = Depends(get_db)):
    user_exist=db.query(User).filter(User.email == user.email).first()
    if user_exist:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT,content="user already exist")
    try:
        new_user=User(name=user.name,email=user.email,hashed_password=get_password_hash(user.password))
        db.add(new_user)
        db.flush()
        new_wallet=Wallet(user_id=new_user.id,balance=0,public_wallet_id=generate_public_wallet_id(db))
        db.add(new_wallet)
        db.commit()
        db.refresh(new_user)
        db.refresh(new_wallet)
        return JSONResponse(status_code=status.HTTP_201_CREATED,content=f"new wallet created successfully with user_id {new_user.id} with wallet id={new_wallet.public_wallet_id}")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="user already exist or a  database constraint failed")
    except Exception as exc:
        db.rollback()
        # print("Registration error:", repr(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Registration failed")


@app.post("/auth/login")
def login(user:UserLogin,db:Session = Depends(get_db)):
    user_exist=db.query(User).filter(User.email == user.email).first()
    if not user_exist:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="user not found")
    if verify_password(user.password,user_exist.hashed_password):
        token_data = {"sub": str(user_exist.id)}
        create_token=create_access_token(token_data)
        refresh_token=create_refresh_token(token_data)
        return {"access_token":create_token,"refresh_token":refresh_token,"token_type":"bearer"}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect email or Password")

@app.post("/auth/refresh")
def refresh_access_token(request:RefreshTokenRequest,db:Session = Depends(get_db)):
    unauthorized=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid or expired refresh token",headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(
            request.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        if payload.get("token_type") != "refresh":
            raise unauthorized

        subject = payload.get("sub")

        if not subject:
            raise unauthorized

        try:
            user_id = int(subject)
        except (TypeError, ValueError):
            raise unauthorized

    except JWTError:
        raise unauthorized

    user = (
        db.query(databasemodel.User)
        .filter(databasemodel.User.id == user_id)
        .first()
    )

    if user is None:
        raise unauthorized

    new_access_token = create_access_token({
        "sub": str(user.id)
    })

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@app.get("/wallet")
def get_my_wallet(current_user=Depends(get_current_user),db:Session = Depends(get_db)):
    wallet=db.query(Wallet).filter(Wallet.user_id==current_user.id).first()
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    return {
        "wallet_id": wallet.public_wallet_id,
        "balance": wallet.balance
    }
@app.post("/wallet/deposit")
def deposit(request:DepositRequest,db:Session = Depends(get_db),current_user=Depends(get_current_user)):
    return deposit_to_wallet(
        db=db,
        current_user=current_user,
        amount=request.amount,
    )

@app.post("/wallet/withdraw")
def withdraw(request:WithdrawRequest,db:Session = Depends(get_db),current_user=Depends(get_current_user)):
    return withdraw_from_wallet(
        db=db,
        current_user=current_user,
        amount=request.amount,
    )





# def existing_transfer_response(
#     existing,
#     sender_wallet_id,
#     receiver_wallet_id,
#     amount,
#     description,
# ):
#     # A key cannot represent a different operation.
#     if (
#         existing.transaction_type != TransactionType.TRANSFER
#         or existing.sender_wallet_id != sender_wallet_id
#         or existing.receiver_wallet_id != receiver_wallet_id
#         or existing.amount != amount
#         or existing.description != description
#     ):
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="Idempotency key already used for a different transfer"
#         )
#
#     # A retry of a recorded failed attempt must not execute again.
#     if existing.status == TransactionStatus.FAILED:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=existing.failure_reason or "Previous transfer failed"
#         )
#
#     return {
#         "message": "Transfer already processed",
#         "public_transaction_id": existing.public_transaction_id,
#         "sender_wallet_id": existing.sender_wallet_id,
#         "receiver_wallet_id": existing.receiver_wallet_id,
#         "amount": str(existing.amount),
#         "description": existing.description,
#         "status": existing.status.value
#     }


@app.post("/transfers")
def money_transfer(
    transfer: TransferSchema,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=100
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return process_transfer(
        db=db,
        current_user=current_user,
        transfer=transfer,
        idempotency_key=idempotency_key,
    )



@app.get("/transactions")
def transaction_history(
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1, le=100),
    min_amount: Decimal | None = Query(None, ge=0),
    max_amount: Decimal | None = Query(None, ge=0),
    search: str | None = Query(None, max_length=100),
    direction: str | None = Query(None),
    transaction_type: TransactionType | None = Query(None,alias="type"),
    transaction_status: TransactionStatus | None = Query(None, alias="status"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_transaction_history(
        db=db,
        current_user=current_user,
        page=page,
        limit=limit,
        min_amount=min_amount,
        max_amount=max_amount,
        direction=direction,
        transaction_type=transaction_type,
        transaction_status=transaction_status,
        start_date=start_date,
        end_date=end_date,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )



@app.get("/transactions/{id}")
def transaction(id:str=Path(...,min_length=15,max_length=15),db: Session = Depends(get_db),current_user=Depends(get_current_user)):

    return get_transaction_details(
        db=db,
        current_user=current_user,
        public_transaction_id=id,
    )




