from pydantic import BaseModel, EmailStr


class SignUpRequest(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    phoneNumber: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    fullName: str
    email: str
    phoneNumber: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse