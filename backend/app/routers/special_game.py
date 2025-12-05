from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_user
from ..game.special_game import (
    SpecialExpressionError,
    count_symbol_usage,
    evaluate_special_expression,
    normalize_expression,
)
from ..models import Problem, SpecialGameAttempt, SpecialGameConfig, User
from ..schemas.special_game import (
    SpecialGameConfigState,
    SpecialGameContextResponse,
    SpecialGameLeaderboardEntry,
    SpecialGameSubmissionRequest,
    SpecialGameSubmissionResponse,
)

router = APIRouter(prefix="/special-game", tags=["special-game"])


async def _get_config(session: AsyncSession) -> SpecialGameConfig | None:
    result = await session.execute(select(SpecialGameConfig).where(SpecialGameConfig.id == 1))
    return result.scalar_one_or_none()


async def _serialize_config(
    config: SpecialGameConfig, session: AsyncSession
) -> SpecialGameConfigState | None:
    if not config.problem_id:
        return None
    problem = await session.get(Problem, config.problem_id)
    if not problem:
        return SpecialGameConfigState(
            problem_id=config.problem_id,
            title=config.title,
            description=config.description,
            target_number=None,
            optimal_cost=None,
            updated_at=config.updated_at,
        )
    return SpecialGameConfigState(
        problem_id=problem.id,
        title=config.title,
        description=config.description,
        target_number=problem.target_number,
        optimal_cost=problem.optimal_cost,
        updated_at=config.updated_at,
    )


async def _load_problem(session: AsyncSession) -> tuple[SpecialGameConfig, Problem]:
    config = await _get_config(session)
    if not config or not config.problem_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="등록된 Special Game 문제가 없습니다.")
    problem = await session.get(Problem, config.problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="특수 게임용 문제를 찾을 수 없습니다.")
    return config, problem


async def _fetch_leaderboard(session: AsyncSession, problem_id: str, limit: int = 20) -> list[SpecialGameLeaderboardEntry]:
    statement = (
        select(SpecialGameAttempt)
        .where(SpecialGameAttempt.problem_id == problem_id)
        .order_by(SpecialGameAttempt.symbol_count.desc(), SpecialGameAttempt.recorded_at.asc())
        .limit(limit)
    )
    result = await session.execute(statement)
    attempts = result.scalars().all()
    return [
        SpecialGameLeaderboardEntry(
            user_id=attempt.user_id,
            username=attempt.username_snapshot,
            expression=attempt.expression,
            symbol_count=attempt.symbol_count,
            recorded_at=attempt.recorded_at,
        )
        for attempt in attempts
    ]


@router.get("/context", response_model=SpecialGameContextResponse)
async def read_special_game_context(session: AsyncSession = Depends(get_session)) -> SpecialGameContextResponse:
    config = await _get_config(session)
    serialized = None
    leaderboard: list[SpecialGameLeaderboardEntry] = []
    if config:
        serialized = await _serialize_config(config, session)
        if serialized and serialized.target_number is not None:
            leaderboard = await _fetch_leaderboard(session, serialized.problem_id)
    return SpecialGameContextResponse(config=serialized, leaderboard=leaderboard)


@router.get("/leaderboard", response_model=list[SpecialGameLeaderboardEntry])
async def read_special_game_leaderboard(session: AsyncSession = Depends(get_session)) -> list[SpecialGameLeaderboardEntry]:
    config = await _get_config(session)
    if not config or not config.problem_id:
        return []
    problem = await session.get(Problem, config.problem_id)
    if not problem:
        return []
    return await _fetch_leaderboard(session, problem.id)


@router.post("/submit", response_model=SpecialGameSubmissionResponse)
async def submit_special_expression(
    payload: SpecialGameSubmissionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SpecialGameSubmissionResponse:
    _, problem = await _load_problem(session)

    try:
        normalized = normalize_expression(payload.expression)
        symbol_count = count_symbol_usage(normalized)
        value = evaluate_special_expression(normalized)
    except SpecialExpressionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if value != problem.target_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"식의 결과({value})가 목표 숫자 {problem.target_number}와 일치하지 않습니다.",
        )

    statement = select(SpecialGameAttempt).where(
        SpecialGameAttempt.user_id == current_user.id,
        SpecialGameAttempt.problem_id == problem.id,
    )
    result = await session.execute(statement)
    attempt = result.scalar_one_or_none()

    is_record = False
    message = "기록이 갱신되지 않았습니다."

    if attempt:
        if symbol_count > attempt.symbol_count:
            attempt.expression = normalized
            attempt.symbol_count = symbol_count
            attempt.username_snapshot = current_user.username
            attempt.computed_value = value
            attempt.recorded_at = datetime.utcnow()
            session.add(attempt)
            is_record = True
            message = "최고 기록을 갱신했습니다!"
        else:
            message = "기호 사용 수가 기존 기록보다 높아야 합니다."
    else:
        new_attempt = SpecialGameAttempt(
            user_id=current_user.id,
            problem_id=problem.id,
            username_snapshot=current_user.username,
            expression=normalized,
            symbol_count=symbol_count,
            computed_value=value,
        )
        session.add(new_attempt)
        attempt = new_attempt
        is_record = True
        message = "첫 기록이 등록되었습니다!"

    await session.commit()

    if is_record:
        await session.refresh(attempt)

    return SpecialGameSubmissionResponse(
        expression=attempt.expression,
        symbol_count=attempt.symbol_count,
        is_record=is_record,
        message=message,
    )


