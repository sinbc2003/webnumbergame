from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..enums import MatchStatus, RoundType
from ..game.engine import NumberGameEngine
from ..models import Match, Room, Submission, User


class GameService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.engine = NumberGameEngine()

    async def create_match(
        self,
        *,
        room: Room,
        target_number: int,
        optimal_cost: int,
        round_number: int,
        duration_minutes: int,
        metadata: dict | None = None,
    ) -> Match:
        deadline = datetime.utcnow() + timedelta(minutes=duration_minutes)
        match = Match(
            room_id=room.id,
            round_type=room.round_type,
            target_number=target_number,
            optimal_cost=optimal_cost,
            status=MatchStatus.ACTIVE,
            started_at=datetime.utcnow(),
            deadline=deadline,
            round_number=round_number,
            metadata_snapshot=metadata,
        )
        self.session.add(match)
        await self.session.commit()
        await self.session.refresh(match)
        return match

    async def get_active_match(self, room_id: str) -> Optional[Match]:
        statement = (
            select(Match)
            .where(Match.room_id == room_id)
            .where(Match.status == MatchStatus.ACTIVE)
            .order_by(Match.created_at.desc())
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_best_submission(self, match_id: str) -> Optional[Submission]:
        distance_nulls_last = case((Submission.distance.is_(None), 1), else_=0)
        statement = (
            select(Submission)
            .where(Submission.match_id == match_id)
            .order_by(distance_nulls_last, Submission.distance, Submission.submitted_at, Submission.cost)
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def submit_expression(
        self,
        *,
        match: Match,
        user: Optional[User],
        team_label: str | None,
        expression: str,
    ) -> Submission:
        evaluation = self.engine.evaluate(
            expression=expression,
            target_number=match.target_number,
            optimal_cost=match.optimal_cost,
            deadline=match.deadline,
        )

        submission = Submission(
            match_id=match.id,
            user_id=user.id if user else None,
            team_label=team_label,
            expression=expression,
            result_value=evaluation.value,
            cost=evaluation.cost,
            distance=evaluation.distance,
            is_optimal=evaluation.is_optimal,
            score=evaluation.score,
            submitted_round=match.round_number,
        )
        self.session.add(submission)

        if user:
            user.total_score += evaluation.score
            if evaluation.distance == 0:
                user.win_count += 1
            await self.session.flush()

        await self.session.commit()
        await self.session.refresh(submission)
        return submission

    async def close_match(self, match: Match, winning_submission_id: str | None = None) -> Match:
        match.status = MatchStatus.CLOSED
        match.finished_at = datetime.utcnow()
        match.winning_submission_id = winning_submission_id
        self.session.add(match)
        await self.session.commit()
        await self.session.refresh(match)
        return match

