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
RELAY_TEAM_A = "relay_a"
RELAY_TEAM_B = "relay_b"
RELAY_TEAMS = (RELAY_TEAM_A, RELAY_TEAM_B)


class RoomService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _generate_code(self) -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    async def create_room(self, *, host: User, payload: RoomCreate) -> Room:
        code = self._generate_code()
        player_slots = max(2, payload.team_size * 2)
        capacity = min(player_slots, settings.max_room_capacity)
        room = Room(
            code=code,
            name=payload.name,
            description=payload.description,
            host_id=host.id,
            round_type=payload.round_type,
            mode=payload.mode,
            team_size=payload.team_size,
            max_players=capacity,
            player_one_id=host.id,
        )
        self.session.add(room)
        await self.session.flush()

        relay_label = RELAY_TEAM_A if payload.team_size > 1 else None
        participant = RoomParticipant(
            room_id=room.id,
            user_id=host.id,
            is_ready=True,
            role=ParticipantRole.PLAYER,
            team_label=relay_label,
            order_index=0 if relay_label else None,
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

    @staticmethod
    def _normalize_slot_values(values: list[str | None], team_size: int) -> list[str | None]:
        limit = max(0, team_size)
        normalized: list[str | None] = [(value or None) for value in values[:limit]]
        if len(normalized) < limit:
            normalized.extend([None] * (limit - len(normalized)))
        return normalized

    async def _fetch_participants_with_user(
        self,
        room_id: str,
    ) -> tuple[list[RoomParticipant], dict[str, str]]:
        statement = (
            select(RoomParticipant, User)
            .join(User, User.id == RoomParticipant.user_id)
            .where(RoomParticipant.room_id == room_id)
        )
        result = await self.session.execute(statement)
        rows = result.all()
        participants: list[RoomParticipant] = []
        usernames: dict[str, str] = {}
        for participant, user in rows:
            participants.append(participant)
            usernames[participant.user_id] = user.username
        return participants, usernames

    @staticmethod
    def _build_relay_payload(
        participants: list[RoomParticipant],
        usernames: dict[str, str],
        team_size: int,
    ) -> dict:
        def build(team_label: str) -> list[dict]:
            slots = [
                {"slot_index": index, "user_id": None, "username": None}
                for index in range(max(0, team_size))
            ]
            for participant in participants:
                if participant.team_label != team_label:
                    continue
                slot_index = participant.order_index
                if slot_index is None:
                    continue
                if slot_index < 0 or slot_index >= len(slots):
                    continue
                slots[slot_index] = {
                    "slot_index": slot_index,
                    "user_id": participant.user_id,
                    "username": usernames.get(participant.user_id),
                }
            return slots

        return {
            "team_a": build(RELAY_TEAM_A),
            "team_b": build(RELAY_TEAM_B),
        }

    async def update_relay_roster(
        self,
        *,
        room: Room,
        team_a: list[str | None],
        team_b: list[str | None],
    ) -> dict:
        if room.team_size <= 1:
            raise ValueError("릴레이 슬롯을 지원하지 않는 방입니다.")
        normalized = {
            RELAY_TEAM_A: self._normalize_slot_values(team_a or [], room.team_size),
            RELAY_TEAM_B: self._normalize_slot_values(team_b or [], room.team_size),
        }
        assignments: dict[str, tuple[str, int]] = {}
        for team_label, slots in normalized.items():
            for index, user_id in enumerate(slots):
                if not user_id:
                    continue
                if user_id in assignments:
                    raise ValueError("한 참가자를 여러 슬롯에 배치할 수 없습니다.")
                assignments[user_id] = (team_label, index)

        participants, usernames = await self._fetch_participants_with_user(room.id)
        participant_ids = {participant.user_id for participant in participants}
        for user_id in assignments:
            if user_id not in participant_ids:
                raise ValueError("방 참가자만 슬롯에 배치할 수 있습니다.")

        for participant in participants:
            assignment = assignments.get(participant.user_id)
            if assignment:
                participant.team_label = assignment[0]
                participant.order_index = assignment[1]
            else:
                participant.team_label = None
                participant.order_index = None
            self.session.add(participant)

        await self.session.commit()
        return self._build_relay_payload(participants, usernames, room.team_size)

    async def normalize_relay_roster(self, room: Room) -> tuple[dict | None, bool]:
        if room.team_size <= 1:
            return None, False

        participants, usernames = await self._fetch_participants_with_user(room.id)
        has_change = False
        for team_label in RELAY_TEAMS:
            team_members = [
                participant for participant in participants if participant.team_label == team_label
            ]
            team_members.sort(
                key=lambda participant: (
                    participant.order_index if participant.order_index is not None else room.team_size + 100,
                    participant.joined_at,
                )
            )
            for index, participant in enumerate(team_members):
                if index >= room.team_size:
                    if participant.team_label is not None or participant.order_index is not None:
                        participant.team_label = None
                        participant.order_index = None
                        self.session.add(participant)
                        has_change = True
                    continue
                if participant.order_index != index:
                    participant.order_index = index
                    self.session.add(participant)
                    has_change = True

        payload = self._build_relay_payload(participants, usernames, room.team_size)
        return payload, has_change

