from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel

from ..enums import MatchStatus, RoundType


class Match(SQLModel, table=True):
    __tablename__ = "matches"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    room_id: str = Field(foreign_key="rooms.id", index=True)
    round_type: RoundType = Field(default=RoundType.ROUND1_INDIVIDUAL)
    target_number: int = Field(default=0)
    optimal_cost: int = Field(default=0)
    status: MatchStatus = Field(default=MatchStatus.PENDING)
    deadline: datetime | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)
    winning_submission_id: str | None = Field(default=None, foreign_key="submissions.id")
    round_number: int = Field(default=1)
    metadata_snapshot: dict | None = Field(default=None, sa_column_kwargs={"nullable": True})
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RoundSnapshot(SQLModel, table=True):
    """
    팀전 릴레이 기록을 위해 라운드별 전체 식을 저장하는 보조 테이블.
    """

    __tablename__ = "round_snapshots"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    match_id: str = Field(foreign_key="matches.id", index=True)
    team_label: str | None = Field(default=None)
    composed_expression: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

