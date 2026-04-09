from pydantic import BaseModel, EmailStr


class SignUpRequest(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    phoneNumber: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateAccountRequest(BaseModel):
    fullName: str
    email: EmailStr
    phoneNumber: str
    password: str | None = None


class ParticipantLookupRequest(BaseModel):
    value: str


class ExpenseParticipantRequest(BaseModel):
    userId: int
    displayName: str


class SaveExpenseRequest(BaseModel):
    createdByUserId: int
    description: str
    amount: float
    participants: list[ExpenseParticipantRequest]
    paidByUserId: int | None = None
    paidByDisplayName: str
    splitType: str
    singleParticipantSplitOption: str | None = None


class UserResponse(BaseModel):
    id: int
    fullName: str
    email: str
    phoneNumber: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class ExpenseResponse(BaseModel):
    id: int
    createdByUserId: int
    description: str
    amount: float
    paidByUserId: int | None
    paidByDisplayName: str
    splitType: str
    singleParticipantSplitOption: str | None
    participants: list[ExpenseParticipantRequest]


class ActivityExpenseResponse(BaseModel):
    id: int
    description: str
    amount: float
    paidByUserId: int | None
    paidByDisplayName: str
    splitType: str
    singleParticipantSplitOption: str | None
    participants: list[ExpenseParticipantRequest]
    createdAt: int


class FriendBalanceResponse(BaseModel):
    friendUserId: int
    friendDisplayName: str
    balanceAmount: float
    balanceState: str