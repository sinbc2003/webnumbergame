from datetime import datetime
from uuid import uuid4
from typing import Optional

from sqlmodel import Field, SQLModel

from ..enums import RoomStatus, RoundType, ParticipantRole


class Room(SQLModel, table=True):
    __tablename__ = "rooms"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    description: str | None = Field(default=None)
    host_id: str = Field(foreign_key="users.id")
    status: RoomStatus = Field(default=RoomStatus.WAITING)
    current_round: int = Field(default=1)
    round_type: RoundType = Field(default=RoundType.ROUND1_INDIVIDUAL)
    tournament_id: Optional[str] = Field(default=None, foreign_key="tournaments.id")
    expires_at: Optional[datetime] = Field(default=None)
    player_one_id: str | None = Field(default=None, foreign_key="users.id")
    player_two_id: str | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RoomParticipant(SQLModel, table=True):
    __tablename__ = "room_participants"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    room_id: str = Field(foreign_key="rooms.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    team_label: str | None = Field(default=None)
    is_ready: bool = Field(default=False)
    order_index: int | None = Field(default=None)
    score: int = Field(default=0)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    role: ParticipantRole = Field(default=ParticipantRole.SPECTATOR)

