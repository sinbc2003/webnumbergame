from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..enums import TournamentStatus, RoundType
from ..models import Tournament, TournamentSlot, TournamentMatch, User
from ..schemas.tournament import TournamentCreate, SlotSeed


@dataclass
class TournamentBundle:
    tournament: Tournament
    slots: List[TournamentSlot]
    matches: List[TournamentMatch]


class TournamentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, host: User, payload: TournamentCreate) -> Tournament:
        tournament = Tournament(
            name=payload.name,
            host_id=host.id,
            status=TournamentStatus.SEEDING,
            starts_at=payload.starts_at,
        )
        self.session.add(tournament)
        await self.session.flush()

        slots = [
            TournamentSlot(tournament_id=tournament.id, position=index + 1)
            for index in range(16)
        ]
        self.session.add_all(slots)

        await self.session.commit()
        await self.session.refresh(tournament)
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
        matchups = []
        round_sizes = [8, 4, 2, 1]
        round_type = RoundType.ROUND1_INDIVIDUAL
        for round_index, size in enumerate(round_sizes, start=1):
            for matchup_index in range(size):
                match = TournamentMatch(
                    tournament_id=tournament.id,
                    round_index=round_index,
                    matchup_index=matchup_index + 1,
                    round_type=round_type if round_index == 1 else RoundType.ROUND2_TEAM,
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

