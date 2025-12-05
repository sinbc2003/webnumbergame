import csv
import io
from typing import Sequence

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete as sa_delete, func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
  
from ..database import get_session
from ..dependencies import get_admin_user
from ..enums import RoundType, RoomStatus
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


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("_", "")


TARGET_HEADER_CANDIDATES = {"targetnumber", "target", "goal", "목표값"}
COST_HEADER_CANDIDATES = {"optimalcost", "cost", "mincost", "최소cost", "minimalcost"}


@router.post("/problems/import", status_code=status.HTTP_201_CREATED)
async def import_problems(
    round_type: RoundType = RoundType.ROUND1_INDIVIDUAL,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if file.content_type not in {None, "text/csv", "application/vnd.ms-excel", "application/csv"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV 파일을 업로드해 주세요.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="비어 있는 파일입니다.")

    decoded = None
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            decoded = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if decoded is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="지원하지 않는 인코딩입니다.")

    reader = csv.reader(io.StringIO(decoded))
    try:
        headers = next(reader)
    except StopIteration:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="헤더가 없습니다.")

    normalized_headers = [_normalize_header(header) for header in headers]
    try:
        target_idx = next(i for i, header in enumerate(normalized_headers) if header in TARGET_HEADER_CANDIDATES)
    except StopIteration:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="목표값 헤더가 필요합니다. (예: '목표값')")
    try:
        cost_idx = next(i for i, header in enumerate(normalized_headers) if header in COST_HEADER_CANDIDATES)
    except StopIteration:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="최소 cost 헤더가 필요합니다. (예: '최소cost')")

    problems: list[Problem] = []
    errors: list[str] = []
    for row_number, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        if max(target_idx, cost_idx) >= len(row):
            errors.append(f"{row_number}행: 열의 수가 부족합니다.")
            continue
        try:
            target_value = int(row[target_idx])
            optimal_cost = int(row[cost_idx])
        except ValueError:
            errors.append(f"{row_number}행: 숫자가 아닌 값이 포함되어 있습니다.")
            continue
        if target_value <= 0 or optimal_cost <= 0:
            errors.append(f"{row_number}행: 목표값과 최소 cost는 0보다 커야 합니다.")
            continue
        problems.append(
            Problem(
                round_type=round_type,
                target_number=target_value,
                optimal_cost=optimal_cost,
            )
        )

    if not problems:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효한 문제가 없습니다. CSV 내용을 확인해 주세요.",
        )

    session.add_all(problems)
    await session.commit()

    return {
        "imported": len(problems),
        "errors": errors,
    }


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

    # 매치가 우승 제출을 참조하고 있으면 submissions를 먼저 삭제할 수 없으므로
    # winning_submission_id를 비워 순환 참조를 끊는다.
    await session.execute(sa_update(Match).values(winning_submission_id=None))

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
    user_count_statement = select(func.count()).select_from(User).where(User.is_admin.is_(False))
    user_count = (await session.execute(user_count_statement)).scalar_one()
    if user_count:
        await session.execute(sa_delete(User).where(User.is_admin.is_(False)))
    deleted["users"] = user_count

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


@router.delete("/rooms/empty")
async def delete_empty_rooms(session: AsyncSession = Depends(get_session)) -> dict:
    subquery = select(RoomParticipant.room_id)
    room_ids = (
        await session.execute(
            select(Room.id)
            .where(Room.status != RoomStatus.ARCHIVED)
            .where(~Room.id.in_(subquery))
        )
    ).scalars().all()

    if not room_ids:
        return {"deleted": 0}

    match_ids = (
        await session.execute(select(Match.id).where(Match.room_id.in_(room_ids)))
    ).scalars().all()

    if match_ids:
        await session.execute(
            sa_update(Match).where(Match.id.in_(match_ids)).values(winning_submission_id=None)
        )
        await session.execute(
            sa_delete(Submission).where(Submission.match_id.in_(match_ids))
        )
        await session.execute(
            sa_delete(RoundSnapshot).where(RoundSnapshot.match_id.in_(match_ids))
        )
        await session.execute(sa_delete(Match).where(Match.id.in_(match_ids)))

    team_ids = (
        await session.execute(select(Team.id).where(Team.room_id.in_(room_ids)))
    ).scalars().all()

    if team_ids:
        await session.execute(sa_delete(TeamMember).where(TeamMember.team_id.in_(team_ids)))
        await session.execute(sa_delete(Team).where(Team.id.in_(team_ids)))

    await session.execute(sa_delete(RoomParticipant).where(RoomParticipant.room_id.in_(room_ids)))
    await session.execute(sa_delete(Room).where(Room.id.in_(room_ids)))
    await session.commit()

    return {"deleted": len(room_ids)}


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


