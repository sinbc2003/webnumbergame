from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import delete as sa_delete, select, update as sa_update, exists
from sqlalchemy.ext.asyncio import AsyncSession

from ..enums import MatchStatus, RoomStatus
from ..events.manager import manager
from ..models import (
    Match,
    Room,
    RoomParticipant,
    RoundSnapshot,
    Submission,
    Team,
    TeamMember,
)


async def _delete_rooms_by_ids(
    session: AsyncSession,
    room_ids: Iterable[str],
    *,
    reason: str,
) -> int:
    ids = [room_id for room_id in room_ids if room_id]
    if not ids:
        return 0

    match_ids = (
        await session.execute(select(Match.id).where(Match.room_id.in_(ids)))
    ).scalars().all()
    if match_ids:
        await session.execute(
            sa_update(Match)
            .where(Match.id.in_(match_ids))
            .values(winning_submission_id=None)
        )
        await session.execute(sa_delete(Submission).where(Submission.match_id.in_(match_ids)))
        await session.execute(sa_delete(RoundSnapshot).where(RoundSnapshot.match_id.in_(match_ids)))
        await session.execute(sa_delete(Match).where(Match.id.in_(match_ids)))

    team_ids = (
        await session.execute(select(Team.id).where(Team.room_id.in_(ids)))
    ).scalars().all()
    if team_ids:
        await session.execute(sa_delete(TeamMember).where(TeamMember.team_id.in_(team_ids)))
        await session.execute(sa_delete(Team).where(Team.id.in_(team_ids)))

    await session.execute(sa_delete(RoomParticipant).where(RoomParticipant.room_id.in_(ids)))
    await session.execute(sa_delete(Room).where(Room.id.in_(ids)))
    await session.commit()

    for room_id in ids:
        await manager.broadcast_room(
            room_id,
            {
                "type": "room_closed",
                "room_id": room_id,
                "reason": reason,
            },
        )
    return len(ids)


async def delete_empty_rooms(session: AsyncSession, *, reason: str) -> int:
    subquery = select(RoomParticipant.room_id)
    room_ids = (
        await session.execute(
            select(Room.id)
            .where(Room.status != RoomStatus.ARCHIVED)
            .where(~Room.id.in_(subquery))
        )
    ).scalars().all()
    return await _delete_rooms_by_ids(session, room_ids, reason=reason)


async def delete_idle_rooms(
    session: AsyncSession,
    *,
    cutoff: datetime,
    reason: str,
) -> int:
    active_match_exists = (
        select(Match.id)
        .where(Match.room_id == Room.id)
        .where(Match.status == MatchStatus.ACTIVE)
    ).exists()
    room_ids = (
        await session.execute(
            select(Room.id)
            .where(Room.status == RoomStatus.WAITING)
            .where(Room.created_at < cutoff)
            .where(~active_match_exists)
        )
    ).scalars().all()
    return await _delete_rooms_by_ids(session, room_ids, reason=reason)

