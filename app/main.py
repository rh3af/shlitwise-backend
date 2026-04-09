import time

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select

from app.auth import generate_token, hash_password, is_strong_password, is_valid_phone
from app.database import create_db_and_tables, get_session
from app.models import User
from app.schemas import (
    AuthResponse,
    LoginRequest,
    SignUpRequest,
    UpdateAccountRequest,
    UserResponse,
)

app = FastAPI(title="ShlitWise Auth API")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/health")
def health():
    return {"status": "ok", "service": "shlitwise-auth-api"}


@app.post("/signup", response_model=AuthResponse)
def signup(payload: SignUpRequest, session: Session = Depends(get_session)):
    full_name = payload.fullName.strip()
    email = payload.email.strip().lower()
    password = payload.password
    phone_number = payload.phoneNumber.strip()

    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required")

    if not is_strong_password(password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters and include uppercase, lowercase, and a digit",
        )

    if not is_valid_phone(phone_number):
        raise HTTPException(
            status_code=400,
            detail="Enter a valid phone number with at least 10 digits",
        )

    existing_user = session.exec(select(User).where(User.email == email)).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="An account already exists for this email")

    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        phone_number=phone_number,
        created_at=int(time.time()),
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return AuthResponse(
        token=generate_token(),
        user=UserResponse(
            id=user.id,
            fullName=user.full_name,
            email=user.email,
            phoneNumber=user.phone_number,
        ),
    )


@app.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    email = payload.email.strip().lower()
    password_hash = hash_password(payload.password)

    user = session.exec(select(User).where(User.email == email)).first()
    if not user or user.password_hash != password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return AuthResponse(
        token=generate_token(),
        user=UserResponse(
            id=user.id,
            fullName=user.full_name,
            email=user.email,
            phoneNumber=user.phone_number,
        ),
    )


@app.put("/account/{user_id}", response_model=UserResponse)
def update_account(user_id: int, payload: UpdateAccountRequest, session: Session = Depends(get_session)):
    full_name = payload.fullName.strip()
    email = payload.email.strip().lower()
    phone_number = payload.phoneNumber.strip()
    password = (payload.password or "").strip()

    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required")

    if not is_valid_phone(phone_number):
        raise HTTPException(
            status_code=400,
            detail="Enter a valid phone number with at least 10 digits",
        )

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_user = session.exec(select(User).where(User.email == email)).first()
    if existing_user and existing_user.id != user_id:
        raise HTTPException(status_code=409, detail="Another account already uses this email")

    user.full_name = full_name
    user.email = email
    user.phone_number = phone_number

    if password:
        if not is_strong_password(password):
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters and include uppercase, lowercase, and a digit",
            )
        user.password_hash = hash_password(password)

    session.add(user)
    session.commit()
    session.refresh(user)

    return UserResponse(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        phoneNumber=user.phone_number,
    )