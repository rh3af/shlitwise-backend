from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(index=True, unique=True)
    password_hash: str
    phone_number: str
    created_at: int


class Expense(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_by_user_id: int = Field(index=True)
    description: str
    amount: float
    paid_by_user_id: Optional[int] = Field(default=None, index=True)
    paid_by_display_name: str
    split_type: str
    single_participant_split_option: Optional[str] = None
    created_at: int


class ExpenseParticipant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    expense_id: int = Field(index=True)
    participant_user_id: int = Field(index=True)
    participant_display_name: str