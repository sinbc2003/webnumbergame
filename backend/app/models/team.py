from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


class Team(SQLModel, table=True):
    __tablename__ = "teams"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    room_id: str = Field(foreign_key="rooms.id", index=True)
    name: str
    label: str
    total_budget: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TeamMember(SQLModel, table=True):
    __tablename__ = "team_members"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    team_id: str = Field(foreign_key="teams.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    order_index: int = Field(default=0)
    allocated_budget: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

