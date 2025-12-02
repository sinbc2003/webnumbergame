from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sa_delete, func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_admin_user
from ..events.manager import manager
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
    User,
)
from ..schemas.problem import ProblemCreate, ProblemPublic, ProblemUpdate, ResetSummary
from ..schemas.admin import UserResetRequest, UserResetResponse
from ..schemas.user import UserPublic

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
    room_ids_result = await session.execute(select(Room.id))
    room_ids = [row[0] for row in room_ids_result.fetchall()]

    # 삭제 순서는 외래키 제약 조건을 위배하지 않도록
    # Room 을 참조하는 엔터티들을 먼저 정리한 뒤,
    # Tournament 등 상위 개체를 삭제하는 순서로 정렬한다.
    model_sequence = [
        (Submission, "submissions"),
        (RoundSnapshot, "round_snapshots"),
        (Match, "matches"),
        (RoomParticipant, "room_participants"),
        (TeamMember, "team_members"),
        (Team, "teams"),
        (TournamentMatch, "tournament_matches"),
        (Room, "rooms"),
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

    # 기존 사용자(관리자 제외) 제거 후 깨끗한 상태에서 다시 시작
    await session.execute(sa_delete(User).where(User.is_admin.is_(False)))

    await session.commit()

    for room_id in room_ids:
        await manager.broadcast_room(
            room_id,
            {
                "type": "room_closed",
                "room_id": room_id,
                "reason": "admin_reset",
            },
        )

    await manager.broadcast_dashboard({"type": "dashboard_reset"})

    return ResetSummary(deleted=deleted)


@router.post("/users/reset", response_model=UserResetResponse)
async def reset_user_account(
    payload: UserResetRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResetResponse:
    statement = select(User).where(User.username == payload.username)
    if payload.user_id:
        statement = statement.where(User.id == payload.user_id)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    user.rating = 1200
    user.win_count = 0
    user.loss_count = 0
    user.total_score = 0
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResetResponse(
        user=UserPublic.model_validate(user),
        message="계정을 초기화했습니다.",
    )


