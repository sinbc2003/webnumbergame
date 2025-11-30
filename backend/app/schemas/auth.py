from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from .user import UserPublic


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GuestRequest(BaseModel):
    nickname: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserPublic


class TokenPayload(BaseModel):
    sub: str | None = None
    exp: Optional[int] = None

