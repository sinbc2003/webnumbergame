import random
import string
from typing import Optional, Sequence

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..config import get_settings
from ..enums import RoomStatus, ParticipantRole, MatchStatus
from ..models import Room, RoomParticipant, User, Match
from ..schemas.room import RoomCreate

settings = get_settings()


class RoomService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _generate_code(self) -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    async def create_room(self, *, host: User, payload: RoomCreate) -> Room:
        code = self._generate_code()
        room = Room(
            code=code,
            name=payload.name,
            description=payload.description,
            host_id=host.id,
            round_type=payload.round_type,
            player_one_id=host.id,
        )
        self.session.add(room)
        await self.session.flush()

        participant = RoomParticipant(
            room_id=room.id,
            user_id=host.id,
            is_ready=True,
            role=ParticipantRole.PLAYER,
        )
        self.session.add(participant)

        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def list_active_rooms(self) -> Sequence[Room]:
        statement = (
            select(Room)
            .join(
                RoomParticipant,
                (RoomParticipant.room_id == Room.id) & (RoomParticipant.user_id == Room.host_id),
            )
            .where(Room.status != RoomStatus.ARCHIVED)
            .order_by(Room.created_at.desc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_room_by_code(self, code: str) -> Optional[Room]:
        statement = select(Room).where(Room.code == code)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def join_room(self, *, room: Room, user: User, team_label: str | None = None) -> RoomParticipant:
        active_match_stmt = (
            select(func.count(Match.id))
            .where(Match.room_id == room.id, Match.status == MatchStatus.ACTIVE)
        )
        has_active_match = (await self.session.execute(active_match_stmt)).scalar() or 0

        statement = select(RoomParticipant).where(
            RoomParticipant.room_id == room.id,
            RoomParticipant.user_id == user.id,
        )
        result = await self.session.execute(statement)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        role = ParticipantRole.SPECTATOR
        updated_room = False

        if not has_active_match:
            if room.player_one_id is None:
                room.player_one_id = user.id
                role = ParticipantRole.PLAYER
                updated_room = True
            elif room.player_two_id is None and room.player_one_id != user.id:
                room.player_two_id = user.id
                role = ParticipantRole.PLAYER
                updated_room = True

        if updated_room:
            self.session.add(room)

        participant = RoomParticipant(
            room_id=room.id,
            user_id=user.id,
            team_label=team_label,
            role=role,
        )
        self.session.add(participant)
        await self.session.commit()
        await self.session.refresh(participant)
        return participant

