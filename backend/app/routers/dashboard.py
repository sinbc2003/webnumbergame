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


WIN_WEIGHT = 100
ACCURACY_DIVIDER = 25
ACTIVITY_WEIGHT = 10


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(session: AsyncSession = Depends(get_session), limit: int = 20):
    batch_limit = min(max(limit * 5, limit), 200)
    statement = (
        select(User)
        .order_by(User.win_count.desc(), User.total_score.desc())
        .limit(batch_limit)
    )
    result = await session.execute(statement)
    users = result.scalars().all()

    enriched: list[LeaderboardEntry] = []
    for user in users:
        total_matches = user.win_count + user.loss_count
        win_points = user.win_count * WIN_WEIGHT
        accuracy_points = max(0, user.total_score // ACCURACY_DIVIDER)
        activity_points = total_matches * ACTIVITY_WEIGHT
        performance_score = win_points + accuracy_points + activity_points
        enriched.append(
            LeaderboardEntry(
                user_id=user.id,
                username=user.username,
                rating=user.rating,
                win_count=user.win_count,
                loss_count=user.loss_count,
                total_matches=total_matches,
                total_score=user.total_score,
                win_points=win_points,
                accuracy_points=accuracy_points,
                activity_points=activity_points,
                performance_score=performance_score,
            )
        )

    enriched.sort(
        key=lambda entry: (
            entry.performance_score,
            entry.win_count,
            entry.total_score,
        ),
        reverse=True,
    )

    return LeaderboardResponse(entries=enriched[:limit], calculated_at=datetime.now(timezone.utc))

