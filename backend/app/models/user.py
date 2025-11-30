from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    email: str = Field(index=True, unique=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    rating: int = Field(default=1200)
    win_count: int = Field(default=0)
    loss_count: int = Field(default=0)
    total_score: int = Field(default=0)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

