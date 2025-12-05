from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class SpecialGameConfig(SQLModel, table=True):
    __tablename__ = "special_game_config"

    id: int = Field(default=1, primary_key=True)
    problem_id: str | None = Field(default=None, foreign_key="problems.id", index=True)
    title: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1024)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )


class SpecialGameAttempt(SQLModel, table=True):
    __tablename__ = "special_game_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_special_attempt_user_problem"),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    problem_id: str = Field(foreign_key="problems.id", index=True)
    username_snapshot: str = Field(max_length=120)
    expression: str
    symbol_count: int = Field(gt=0)
    computed_value: int = Field(default=0)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


