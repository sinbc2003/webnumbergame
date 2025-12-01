from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field

from ..enums import RoomStatus, RoundType, ParticipantRole


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
    player_one_id: str | None
    player_two_id: str | None
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
    role: ParticipantRole

    class Config:
        from_attributes = True


class JoinRoomRequest(BaseModel):
    code: str
    team_label: str | None = None


class StartRoundRequest(BaseModel):
    round_number: int = 1
    duration_minutes: int | None = None
    problem_count: int = Field(default=5, ge=1, le=10)


class PlayerAssignmentRequest(BaseModel):
    slot: Literal["player_one", "player_two"]
    user_id: str | None = None


class SubmissionRequest(BaseModel):
    expression: str
    mode: RoundType
    team_label: str | None = None


class InputUpdateRequest(BaseModel):
    expression: str = Field(default="", max_length=256)


class TeamMemberInput(BaseModel):
    user_id: str
    allocated_budget: int
    order_index: int


class TeamSetupRequest(BaseModel):
    name: str
    label: str
    total_budget: int
    members: List[TeamMemberInput]


class ActiveMatchProblem(BaseModel):
    target_number: int
    optimal_cost: int
    index: int


class ActiveMatchResponse(BaseModel):
    match_id: str
    round_number: int
    target_number: int
    optimal_cost: int
    deadline: datetime | None
    current_index: int
    total_problems: int
    problems: List[ActiveMatchProblem]
    player_one_id: str | None
    player_two_id: str | None

