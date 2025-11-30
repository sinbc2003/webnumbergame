from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from ..enums import TournamentStatus, RoundType


class Tournament(SQLModel, table=True):
    __tablename__ = "tournaments"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    status: TournamentStatus = Field(default=TournamentStatus.DRAFT)
    host_id: str = Field(foreign_key="users.id")
    bracket: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    starts_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TournamentSlot(SQLModel, table=True):
    __tablename__ = "tournament_slots"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    tournament_id: str = Field(foreign_key="tournaments.id", index=True)
    position: int = Field(index=True)
    user_id: str | None = Field(default=None, foreign_key="users.id")
    team_label: str | None = Field(default=None)
    seed: int | None = Field(default=None)


class TournamentMatch(SQLModel, table=True):
    __tablename__ = "tournament_matches"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    tournament_id: str = Field(foreign_key="tournaments.id", index=True)
    round_index: int
    matchup_index: int
    room_id: str | None = Field(default=None, foreign_key="rooms.id")
    round_type: RoundType = Field(default=RoundType.ROUND1_INDIVIDUAL)
    winner_slot: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

