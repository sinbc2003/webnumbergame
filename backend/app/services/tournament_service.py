import random
import string
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..enums import TournamentStatus, RoundType, RoomStatus, ParticipantRole
from ..models import Tournament, TournamentSlot, TournamentMatch, User, Room, RoomParticipant
from ..schemas.tournament import TournamentCreate, SlotSeed


@dataclass
class TournamentBundle:
    tournament: Tournament
    slots: List[TournamentSlot]
    matches: List[TournamentMatch]


class TournamentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _generate_code(self) -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    async def create(self, *, host: User, payload: TournamentCreate) -> Tournament:
        tournament = Tournament(
            name=payload.name,
            host_id=host.id,
            status=TournamentStatus.SEEDING,
            participant_slots=payload.participant_slots,
        )
        self.session.add(tournament)
        await self.session.flush()

        slots = [
            TournamentSlot(tournament_id=tournament.id, position=index + 1)
            for index in range(payload.participant_slots)
        ]
        self.session.add_all(slots)

        await self.session.commit()
        await self.session.refresh(tournament)
        await self.create_bracket(tournament)
        return tournament

    async def join(self, *, tournament: Tournament, user: User) -> Tournament:
        if tournament.status == TournamentStatus.LIVE:
            raise ValueError("이미 시작된 토너먼트입니다.")

        slot_stmt = (
            select(TournamentSlot)
            .where(TournamentSlot.tournament_id == tournament.id)
            .order_by(TournamentSlot.position)
        )
        slots = (await self.session.execute(slot_stmt)).scalars().all()

        if any(slot.user_id == user.id for slot in slots):
            return tournament

        slot = next((slot for slot in slots if slot.user_id is None), None)
        if slot is None:
            raise ValueError("참가 인원이 가득 찼습니다.")

        slot.user_id = user.id
        self.session.add(slot)
        await self.session.commit()
        await self.session.refresh(slot)

        if all(s.user_id for s in slots):
            await self._initialize_first_round(tournament, slots)

        return tournament

    async def seed_slots(self, *, tournament: Tournament, seeds: List[SlotSeed]) -> List[TournamentSlot]:
        position_map = {seed.position: seed for seed in seeds}
        statement = select(TournamentSlot).where(TournamentSlot.tournament_id == tournament.id)
        result = await self.session.execute(statement)
        slots = result.scalars().all()
        for slot in slots:
            data = position_map.get(slot.position)
            if not data:
                continue
            slot.user_id = data.user_id
            slot.team_label = data.team_label
            slot.seed = data.seed
            self.session.add(slot)
        await self.session.commit()
        return slots

    async def create_bracket(self, tournament: Tournament) -> List[TournamentMatch]:
        existing_stmt = select(TournamentMatch).where(TournamentMatch.tournament_id == tournament.id)
        existing = (await self.session.execute(existing_stmt)).scalars().all()
        if existing:
            return existing

        matchups = []
        total_slots = tournament.participant_slots
        rounds = 0
        size = total_slots
        while size >= 1:
            size //= 2
            rounds += 1
        round_sizes = [total_slots // (2 ** round_idx) for round_idx in range(1, rounds + 1)]
        for round_index, size in enumerate(round_sizes, start=1):
            for matchup_index in range(size):
                match = TournamentMatch(
                    tournament_id=tournament.id,
                    round_index=round_index,
                    matchup_index=matchup_index + 1,
                    round_type=RoundType.TOURNAMENT_1V1,
                )
                self.session.add(match)
                matchups.append(match)
        await self.session.commit()
        return matchups

    async def get_bundle(self, tournament_id: str) -> Optional[TournamentBundle]:
        tournament_stmt = select(Tournament).where(Tournament.id == tournament_id)
        slot_stmt = select(TournamentSlot).where(TournamentSlot.tournament_id == tournament_id)
        match_stmt = select(TournamentMatch).where(TournamentMatch.tournament_id == tournament_id)

        tournament = (await self.session.execute(tournament_stmt)).scalar_one_or_none()
        if not tournament:
            return None
        slots = (await self.session.execute(slot_stmt)).scalars().all()
        matches = (await self.session.execute(match_stmt)).scalars().all()
        return TournamentBundle(tournament=tournament, slots=slots, matches=matches)

    async def _initialize_first_round(self, tournament: Tournament, slots: List[TournamentSlot]) -> None:
        if tournament.status == TournamentStatus.LIVE:
            return

        matches = await self.create_bracket(tournament)
        round_one_matches = [m for m in matches if m.round_index == 1]

        pairs = [slots[i : i + 2] for i in range(0, len(slots), 2)]
        for index, pair in enumerate(pairs, start=1):
            if len(pair) < 2 or not pair[0].user_id or not pair[1].user_id:
                continue
            match = next((m for m in round_one_matches if m.matchup_index == index), None)
            if not match:
                continue
            room_id = await self._create_room_for_match(tournament, index, pair[0], pair[1])
            match.room_id = room_id
            match.player_one_id = pair[0].user_id
            match.player_two_id = pair[1].user_id
            self.session.add(match)

        tournament.status = TournamentStatus.LIVE
        self.session.add(tournament)
        await self.session.commit()

    async def _create_room_for_match(
        self,
        tournament: Tournament,
        matchup_index: int,
        slot_a: TournamentSlot,
        slot_b: TournamentSlot,
    ) -> str:
        code = self._generate_code()
        room = Room(
            code=code,
            name=f"{tournament.name} - 라운드1 매치 {matchup_index}",
            description=f"시드 {slot_a.position} vs {slot_b.position}",
            host_id=slot_a.user_id,
            status=RoomStatus.WAITING,
            round_type=RoundType.TOURNAMENT_1V1,
            max_players=32,
            tournament_id=tournament.id,
            player_one_id=slot_a.user_id,
            player_two_id=slot_b.user_id,
        )
        self.session.add(room)
        await self.session.flush()

        for user_id in (slot_a.user_id, slot_b.user_id):
            participant = RoomParticipant(
                room_id=room.id,
                user_id=user_id,
                is_ready=True,
                role=ParticipantRole.PLAYER,
            )
            self.session.add(participant)

        await self.session.flush()
        return room.id

