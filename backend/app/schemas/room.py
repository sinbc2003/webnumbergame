from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from ..enums import RoomStatus, RoundType


class RoomCreate(BaseModel):
    name: str
    description: str | None = None
    round_type: RoundType = RoundType.ROUND1_INDIVIDUAL
    max_players: int = Field(default=16, ge=2, le=32)


class RoomPublic(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    host_id: str
    status: RoomStatus
    round_type: RoundType
    max_players: int
    current_round: int
    created_at: datetime

    class Config:
        from_attributes = True


class ParticipantPublic(BaseModel):
    id: str
    user_id: str
    team_label: str | None
    is_ready: bool
    order_index: int | None
    score: int

    class Config:
        from_attributes = True


class JoinRoomRequest(BaseModel):
    code: str
    team_label: str | None = None


class StartRoundRequest(BaseModel):
    target_number: int
    optimal_cost: int
    round_number: int = 1
    duration_minutes: int | None = None


class SubmissionRequest(BaseModel):
    expression: str
    mode: RoundType
    team_label: str | None = None


class TeamMemberInput(BaseModel):
    user_id: str
    allocated_budget: int
    order_index: int


class TeamSetupRequest(BaseModel):
    name: str
    label: str
    total_budget: int
    members: List[TeamMemberInput]

