from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..database import get_session
from ..events.manager import manager
from ..models import Match, Room, User
from ..schemas.dashboard import DashboardSummary, LeaderboardEntry, LeaderboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def read_summary(session: AsyncSession = Depends(get_session)):
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0  # type: ignore
    active_rooms = (await session.execute(select(func.count(Room.id)))).scalar() or 0  # type: ignore
    ongoing_matches = (await session.execute(select(func.count(Match.id)))).scalar() or 0  # type: ignore

    return DashboardSummary(
        total_users=total_users,
        active_rooms=active_rooms,
        ongoing_matches=ongoing_matches,
        online_players=manager.online_player_count,
        updated_at=datetime.now(timezone.utc),
    )


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(session: AsyncSession = Depends(get_session), limit: int = 20):
    statement = (
        select(User)
        .order_by(User.rating.desc(), User.total_score.desc())
        .limit(limit)
    )
    result = await session.execute(statement)
    users = result.scalars().all()
    entries = [
        LeaderboardEntry(
            user_id=user.id,
            username=user.username,
            rating=user.rating,
            win_count=user.win_count,
            total_score=user.total_score,
        )
        for user in users
    ]
    return LeaderboardResponse(entries=entries, calculated_at=datetime.now(timezone.utc))

