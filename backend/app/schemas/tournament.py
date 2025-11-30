from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from ..enums import TournamentStatus, RoundType


class TournamentCreate(BaseModel):
    name: str
    starts_at: datetime | None = None


class TournamentPublic(BaseModel):
    id: str
    name: str
    status: TournamentStatus
    starts_at: datetime | None
    bracket: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


class SlotSeed(BaseModel):
    position: int
    user_id: str | None = None
    team_label: str | None = None
    seed: int | None = None


class SeedRequest(BaseModel):
    slots: List[SlotSeed]


class TournamentMatchPublic(BaseModel):
    id: str
    round_index: int
    matchup_index: int
    round_type: RoundType
    room_id: str | None = None

    class Config:
        from_attributes = True


class TournamentSlotPublic(BaseModel):
    id: str
    position: int
    user_id: str | None = None
    team_label: str | None = None
    seed: int | None = None

    class Config:
        from_attributes = True


class TournamentBundleResponse(BaseModel):
    tournament: TournamentPublic
    slots: List[TournamentSlotPublic]
    matches: List[TournamentMatchPublic]

