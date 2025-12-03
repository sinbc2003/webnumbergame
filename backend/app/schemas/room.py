from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field, model_validator

from ..enums import RoomStatus, RoundType, ParticipantRole, RoomMode


class RoomCreate(BaseModel):
    name: str
    description: str | None = None
    round_type: RoundType = RoundType.ROUND1_INDIVIDUAL
    mode: RoomMode = RoomMode.INDIVIDUAL
    team_size: int = Field(default=1, ge=1, le=8)

    @model_validator(mode="after")
    def validate_configuration(self) -> "RoomCreate":
        if self.mode == RoomMode.INDIVIDUAL:
            if self.round_type != RoundType.ROUND1_INDIVIDUAL:
                raise ValueError("개인전은 1라운드 문제만 사용할 수 있습니다.")
            if self.team_size not in (1, 2, 3):
                raise ValueError("개인전은 1vs1, 2vs2, 3vs3만 가능합니다.")
        elif self.mode == RoomMode.TEAM:
            if self.round_type != RoundType.ROUND2_TEAM:
                raise ValueError("팀전은 2라운드 문제만 사용할 수 있습니다.")
            if self.team_size not in (2, 4):
                raise ValueError("팀전은 2vs2 또는 4vs4만 지원합니다.")
        elif self.mode == RoomMode.TOURNAMENT:
            raise ValueError("토너먼트 모드는 /tournaments API를 이용해 생성하세요.")
        return self


class RoomPublic(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    host_id: str
    status: RoomStatus
    round_type: RoundType
    mode: RoomMode
    team_size: int
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
    username: str
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


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


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


class ChatMessageResponse(BaseModel):
    message_id: str
    room_id: str
    user_id: str
    username: str
    message: str
    timestamp: datetime

