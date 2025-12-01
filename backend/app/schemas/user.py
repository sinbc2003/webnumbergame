from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    id: str
    email: str
    username: str


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserPublic(UserBase):
    rating: int
    win_count: int
    loss_count: int
    total_score: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

