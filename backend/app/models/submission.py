from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


class Submission(SQLModel, table=True):
    __tablename__ = "submissions"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    match_id: str = Field(foreign_key="matches.id", index=True)
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    team_label: str | None = Field(default=None)
    expression: str
    result_value: float | None = Field(default=None)
    cost: int = Field(default=0)
    distance: float | None = Field(default=None)
    is_optimal: bool = Field(default=False)
    score: int = Field(default=0)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_round: int = Field(default=1)

