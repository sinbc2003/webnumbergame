from datetime import datetime
from typing import List

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    user_id: str
    username: str
    rating: int
    win_count: int
    total_score: int


class DashboardSummary(BaseModel):
    total_users: int
    active_rooms: int
    ongoing_matches: int
    online_players: int
    updated_at: datetime


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    calculated_at: datetime

