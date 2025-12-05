from datetime import datetime

from pydantic import BaseModel, Field


class SpecialGameConfigPayload(BaseModel):
    problem_id: str = Field(..., description="특수 게임에 사용할 문제 ID")
    title: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1024)


class SpecialGameConfigState(BaseModel):
    problem_id: str
    title: str | None = None
    description: str | None = None
    target_number: int | None = None
    optimal_cost: int | None = None
    updated_at: datetime | None = None


class SpecialGameLeaderboardEntry(BaseModel):
    user_id: str
    username: str
    expression: str
    symbol_count: int
    recorded_at: datetime


class SpecialGameContextResponse(BaseModel):
    config: SpecialGameConfigState | None = None
    leaderboard: list[SpecialGameLeaderboardEntry] = Field(default_factory=list)


class SpecialGameSubmissionRequest(BaseModel):
    expression: str = Field(..., min_length=1, max_length=512)


class SpecialGameSubmissionResponse(BaseModel):
    expression: str
    symbol_count: int
    is_record: bool
    message: str


