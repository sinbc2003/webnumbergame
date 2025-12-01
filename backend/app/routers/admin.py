from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_admin_user
from ..models import (
    Match,
    Problem,
    Room,
    RoomParticipant,
    RoundSnapshot,
    Submission,
    Team,
    TeamMember,
    Tournament,
    TournamentMatch,
    TournamentSlot,
)
from ..schemas.problem import ProblemCreate, ProblemPublic, ProblemUpdate, ResetSummary

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin_user)],
)


async def _get_problem_or_404(problem_id: str, session: AsyncSession) -> Problem:
    statement = select(Problem).where(Problem.id == problem_id)
    result = await session.execute(statement)
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")
    return problem


@router.get("/problems", response_model=list[ProblemPublic])
async def list_problems(
    round_type: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> Sequence[ProblemPublic]:
    statement = select(Problem).order_by(Problem.created_at.desc())
    if round_type:
        statement = statement.where(Problem.round_type == round_type)
    result = await session.execute(statement)
    problems = result.scalars().all()
    return [ProblemPublic.model_validate(problem) for problem in problems]


@router.post("/problems", response_model=ProblemPublic, status_code=status.HTTP_201_CREATED)
async def create_problem(payload: ProblemCreate, session: AsyncSession = Depends(get_session)) -> ProblemPublic:
    problem = Problem(**payload.model_dump())
    session.add(problem)
    await session.commit()
    await session.refresh(problem)
    return ProblemPublic.model_validate(problem)


@router.put("/problems/{problem_id}", response_model=ProblemPublic)
async def update_problem(
    problem_id: str,
    payload: ProblemUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProblemPublic:
    problem = await _get_problem_or_404(problem_id, session)
    update_payload = payload.model_dump(exclude_unset=True)
    for key, value in update_payload.items():
        setattr(problem, key, value)
    session.add(problem)
    await session.commit()
    await session.refresh(problem)
    return ProblemPublic.model_validate(problem)


@router.delete("/problems/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_problem(problem_id: str, session: AsyncSession = Depends(get_session)) -> None:
    problem = await _get_problem_or_404(problem_id, session)
    await session.delete(problem)
    await session.commit()


@router.post("/reset", response_model=ResetSummary)
async def reset_arena(session: AsyncSession = Depends(get_session)) -> ResetSummary:
    model_sequence = [
        (Submission, "submissions"),
        (RoundSnapshot, "round_snapshots"),
        (Match, "matches"),
        (RoomParticipant, "room_participants"),
        (Room, "rooms"),
        (TeamMember, "team_members"),
        (Team, "teams"),
        (TournamentMatch, "tournament_matches"),
        (TournamentSlot, "tournament_slots"),
        (Tournament, "tournaments"),
    ]

    deleted: dict[str, int] = {}

    for model, label in model_sequence:
        count_statement = select(func.count()).select_from(model)
        count = (await session.execute(count_statement)).scalar_one()
        if count:
            await session.execute(sa_delete(model))
        deleted[label] = count

    await session.commit()
    return ResetSummary(deleted=deleted)


