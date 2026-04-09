import time

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select

from app.auth import generate_token, hash_password, is_strong_password, is_valid_phone
from app.database import create_db_and_tables, get_session
from app.models import Expense, ExpenseParticipant, User
from app.schemas import (
    ActivityExpenseResponse,
    AuthResponse,
    ExpenseParticipantRequest,
    ExpenseResponse,
    FriendBalanceResponse,
    LoginRequest,
    ParticipantLookupRequest,
    SaveExpenseRequest,
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


@app.post("/users/lookup", response_model=UserResponse)
def lookup_user(payload: ParticipantLookupRequest, session: Session = Depends(get_session)):
    value = payload.value.strip()

    if not value:
        raise HTTPException(status_code=400, detail="Lookup value is required")

    is_email = "@" in value
    is_phone = value.isdigit()

    if is_email:
        normalized_email = value.lower()
        user = session.exec(select(User).where(User.email == normalized_email)).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="There is no account found with the entered email address"
            )

    elif is_phone:
        user = session.exec(select(User).where(User.phone_number == value)).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="There is no account found with the entered phone number"
            )

    else:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid email address or phone number"
        )

    return UserResponse(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        phoneNumber=user.phone_number,
    )


@app.post("/expenses", response_model=ExpenseResponse)
def save_expense(payload: SaveExpenseRequest, session: Session = Depends(get_session)):
    description = payload.description.strip()
    amount = payload.amount
    created_by_user_id = payload.createdByUserId
    participants = payload.participants
    paid_by_user_id = payload.paidByUserId
    paid_by_display_name = payload.paidByDisplayName.strip()
    split_type = payload.splitType.strip()
    single_participant_split_option = (
        payload.singleParticipantSplitOption.strip()
        if payload.singleParticipantSplitOption
        else None
    )

    if not description:
        raise HTTPException(status_code=400, detail="Description is required")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    if not participants:
        raise HTTPException(status_code=400, detail="At least one participant is required")

    created_by_user = session.get(User, created_by_user_id)
    if not created_by_user:
        raise HTTPException(status_code=404, detail="Expense creator user not found")

    if not paid_by_display_name:
        raise HTTPException(status_code=400, detail="Paid by display name is required")

    if split_type not in {"EQUAL"}:
        raise HTTPException(status_code=400, detail="Unsupported split type")

    if len(participants) == 1 and not single_participant_split_option:
        raise HTTPException(
            status_code=400,
            detail="Single participant split option is required when there is exactly one participant"
        )

    if len(participants) > 1 and single_participant_split_option is not None:
        raise HTTPException(
            status_code=400,
            detail="Single participant split option is only valid for one participant"
        )

    participant_user_ids: set[int] = set()

    for participant in participants:
        participant_user = session.get(User, participant.userId)
        if not participant_user:
            raise HTTPException(
                status_code=404,
                detail=f"Participant user with id {participant.userId} was not found"
            )

        if participant.userId in participant_user_ids:
            raise HTTPException(status_code=400, detail="Duplicate participants are not allowed")

        participant_user_ids.add(participant.userId)

    if paid_by_user_id is not None:
        payer_user = session.get(User, paid_by_user_id)
        if not payer_user:
            raise HTTPException(status_code=404, detail="Paid by user was not found")

    expense = Expense(
        created_by_user_id=created_by_user_id,
        description=description,
        amount=amount,
        paid_by_user_id=paid_by_user_id,
        paid_by_display_name=paid_by_display_name,
        split_type=split_type,
        single_participant_split_option=single_participant_split_option,
        created_at=int(time.time()),
    )

    session.add(expense)
    session.commit()
    session.refresh(expense)

    saved_participants: list[ExpenseParticipantRequest] = []

    for participant in participants:
        expense_participant = ExpenseParticipant(
            expense_id=expense.id,
            participant_user_id=participant.userId,
            participant_display_name=participant.displayName,
        )
        session.add(expense_participant)

        saved_participants.append(
            ExpenseParticipantRequest(
                userId=participant.userId,
                displayName=participant.displayName,
            )
        )

    session.commit()

    return ExpenseResponse(
        id=expense.id,
        createdByUserId=expense.created_by_user_id,
        description=expense.description,
        amount=expense.amount,
        paidByUserId=expense.paid_by_user_id,
        paidByDisplayName=expense.paid_by_display_name,
        splitType=expense.split_type,
        singleParticipantSplitOption=expense.single_participant_split_option,
        participants=saved_participants,
    )


@app.get("/expenses/activity/{user_id}", response_model=list[ActivityExpenseResponse])
def get_activity_expenses(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    participant_rows = session.exec(
        select(ExpenseParticipant).where(ExpenseParticipant.participant_user_id == user_id)
    ).all()

    expense_ids = {row.expense_id for row in participant_rows}

    created_expenses = session.exec(
        select(Expense).where(Expense.created_by_user_id == user_id)
    ).all()

    for expense in created_expenses:
        expense_ids.add(expense.id)

    expenses = []
    if expense_ids:
        expenses = session.exec(
            select(Expense).where(Expense.id.in_(expense_ids))
        ).all()

    expenses = sorted(expenses, key=lambda x: x.created_at, reverse=True)

    activity_list: list[ActivityExpenseResponse] = []

    for expense in expenses:
        expense_participants = session.exec(
            select(ExpenseParticipant).where(ExpenseParticipant.expense_id == expense.id)
        ).all()

        participants = [
            ExpenseParticipantRequest(
                userId=row.participant_user_id,
                displayName=row.participant_display_name,
            )
            for row in expense_participants
        ]

        activity_list.append(
            ActivityExpenseResponse(
                id=expense.id,
                description=expense.description,
                amount=expense.amount,
                paidByUserId=expense.paid_by_user_id,
                paidByDisplayName=expense.paid_by_display_name,
                splitType=expense.split_type,
                singleParticipantSplitOption=expense.single_participant_split_option,
                participants=participants,
                createdAt=expense.created_at,
            )
        )

    return activity_list


@app.get("/friends/balances/{user_id}", response_model=list[FriendBalanceResponse])
def get_friend_balances(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    participant_rows = session.exec(
        select(ExpenseParticipant).where(ExpenseParticipant.participant_user_id == user_id)
    ).all()

    expense_ids = {row.expense_id for row in participant_rows}

    created_expenses = session.exec(
        select(Expense).where(Expense.created_by_user_id == user_id)
    ).all()

    for expense in created_expenses:
        expense_ids.add(expense.id)

    if not expense_ids:
        return []

    expenses = session.exec(
        select(Expense).where(Expense.id.in_(expense_ids))
    ).all()

    friend_balances: dict[int, dict] = {}

    for expense in expenses:
        expense_participants = session.exec(
            select(ExpenseParticipant).where(ExpenseParticipant.expense_id == expense.id)
        ).all()

        participant_ids = [p.participant_user_id for p in expense_participants]

        if user_id not in participant_ids:
            participant_ids.append(user_id)

        all_people_count = len(participant_ids)
        if all_people_count <= 1:
            continue

        share_per_person = expense.amount / all_people_count

        for participant in expense_participants:
            friend_id = participant.participant_user_id
            if friend_id == user_id:
                continue

            if friend_id not in friend_balances:
                friend_balances[friend_id] = {
                    "friendDisplayName": participant.participant_display_name,
                    "netAmount": 0.0,
                }

            # Single participant custom split logic
            if len(expense_participants) == 1 and expense.single_participant_split_option:
                option = expense.single_participant_split_option

                if option == "YOU_PAID_SPLIT_EQUALLY":
                    friend_balances[friend_id]["netAmount"] += share_per_person

                elif option == "YOU_ARE_OWED_FULL_AMOUNT":
                    friend_balances[friend_id]["netAmount"] += expense.amount

                elif option == "OTHER_PAID_SPLIT_EQUALLY":
                    friend_balances[friend_id]["netAmount"] -= share_per_person

                elif option == "OTHER_IS_OWED_FULL_AMOUNT":
                    friend_balances[friend_id]["netAmount"] -= expense.amount

            # Multi participant equal split logic
            else:
                if expense.paid_by_user_id is None:
                    # You paid
                    friend_balances[friend_id]["netAmount"] += share_per_person
                elif expense.paid_by_user_id == friend_id:
                    # Friend paid, so you owe your share
                    friend_balances[friend_id]["netAmount"] -= share_per_person
                else:
                    # Someone else paid, no direct balance change with this friend for now
                    pass

    response: list[FriendBalanceResponse] = []

    for friend_id, balance_data in friend_balances.items():
        net_amount = round(balance_data["netAmount"], 2)

        if net_amount > 0:
            balance_state = "THEY_OWE_YOU"
        elif net_amount < 0:
            balance_state = "YOU_OWE"
        else:
            balance_state = "BALANCED"

        response.append(
            FriendBalanceResponse(
                friendUserId=friend_id,
                friendDisplayName=balance_data["friendDisplayName"],
                balanceAmount=abs(net_amount),
                balanceState=balance_state,
            )
        )

    response.sort(key=lambda item: item.friendDisplayName.lower())
    return response