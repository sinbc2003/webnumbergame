from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..config import get_settings
from ..database import get_session
from ..dependencies import get_current_user
from ..enums import RoundType
from ..events.manager import manager
from ..models import Problem, Room, RoomParticipant, Submission, User
from ..schemas.room import (
    RoomCreate,
    RoomPublic,
    JoinRoomRequest,
    StartRoundRequest,
    SubmissionRequest,
    ParticipantPublic,
    ActiveMatchResponse,
    ActiveMatchProblem,
)
from ..services.game_service import GameService
from ..services.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])
settings = get_settings()


async def _get_room_or_404(session: AsyncSession, room_id: str) -> Room:
    statement = select(Room).where(Room.id == room_id)
    result = await session.execute(statement)
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="방을 찾을 수 없습니다.")
    return room


@router.get("", response_model=list[RoomPublic])
async def list_rooms(session: AsyncSession = Depends(get_session)):
    service = RoomService(session)
    rooms = await service.list_active_rooms()
    return [RoomPublic.model_validate(room) for room in rooms]


@router.post("", response_model=RoomPublic, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = RoomService(session)
    room = await service.create_room(host=current_user, payload=payload)
    return RoomPublic.model_validate(room)


@router.get("/{room_id}", response_model=RoomPublic)
async def get_room(room_id: str, session: AsyncSession = Depends(get_session)):
    room = await _get_room_or_404(session, room_id)
    return RoomPublic.model_validate(room)


@router.get("/{room_id}/participants", response_model=list[ParticipantPublic])
async def get_participants(room_id: str, session: AsyncSession = Depends(get_session)):
    await _get_room_or_404(session, room_id)
    statement = select(RoomParticipant).where(RoomParticipant.room_id == room_id)
    result = await session.execute(statement)
    participants = result.scalars().all()
    return [ParticipantPublic.model_validate(p) for p in participants]


@router.post("/join", response_model=ParticipantPublic)
async def join_room(
    payload: JoinRoomRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = RoomService(session)
    room = await service.get_room_by_code(payload.code)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="참가 코드를 찾을 수 없습니다.")
    try:
        participant = await service.join_room(room=room, user=current_user, team_label=payload.team_label)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await manager.broadcast_room(
        room.id,
        {
            "type": "participant_joined",
            "room_id": room.id,
            "participant": ParticipantPublic.model_validate(participant).model_dump(),
        },
    )
    return ParticipantPublic.model_validate(participant)


@router.post("/{room_id}/rounds", response_model=dict)
async def start_round(
    room_id: str,
    payload: StartRoundRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    room = await _get_room_or_404(session, room_id)
    if room.host_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="방장만 라운드를 시작할 수 있습니다.")

    duration = payload.duration_minutes or settings.default_round_minutes
    problem_count = payload.problem_count or 5

    statement = (
        select(Problem)
        .where(Problem.round_type == room.round_type)
        .order_by(func.random())
        .limit(problem_count)
    )
    result = await session.execute(statement)
    problems = result.scalars().all()
    if not problems:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="등록된 문제가 없습니다. 관리자 페이지에서 문제를 추가하세요.")

    serialized = [
        {"target_number": problem.target_number, "optimal_cost": problem.optimal_cost} for problem in problems
    ]
    first = serialized[0]
    metadata = {"problems": serialized, "current_index": 0}

    game_service = GameService(session)
    match = await game_service.create_match(
        room=room,
        target_number=first["target_number"],
        optimal_cost=first["optimal_cost"],
        round_number=payload.round_number,
        duration_minutes=duration,
        metadata=metadata,
    )

    event_payload = {
        "type": "round_started",
        "room_id": room.id,
        "match_id": match.id,
        "target_number": match.target_number,
        "optimal_cost": match.optimal_cost,
        "deadline": match.deadline.isoformat() if match.deadline else None,
        "problems": serialized,
        "current_index": 0,
    }
    await manager.broadcast_room(room.id, event_payload)
    return event_payload


def _serialize_submission(submission: Submission) -> dict:
    return {
        "id": submission.id,
        "match_id": submission.match_id,
        "user_id": submission.user_id,
        "team_label": submission.team_label,
        "expression": submission.expression,
        "result_value": submission.result_value,
        "cost": submission.cost,
        "distance": submission.distance,
        "is_optimal": submission.is_optimal,
        "score": submission.score,
        "submitted_at": submission.submitted_at.isoformat(),
    }


@router.post("/{room_id}/submit", response_model=dict)
async def submit_expression(
    room_id: str,
    payload: SubmissionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    room = await _get_room_or_404(session, room_id)
    game_service = GameService(session)
    match = await game_service.get_active_match(room.id)
    if not match:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="진행 중인 라운드가 없습니다.")

    team_label = payload.team_label if room.round_type == RoundType.ROUND2_TEAM else None
    submission = await game_service.submit_expression(
        match=match,
        user=current_user,
        team_label=team_label,
        expression=payload.expression,
    )

    event_payload = {
        "type": "submission_received",
        "room_id": room.id,
        "match_id": match.id,
        "submission": _serialize_submission(submission),
    }
    await manager.broadcast_room(room.id, event_payload)

    if submission.distance == 0:
        metadata = match.metadata_snapshot or {}
        problems = metadata.get("problems") or []
        current_index = metadata.get("current_index", 0)
        has_more = problems and current_index < len(problems) - 1

        if has_more:
            next_index = current_index + 1
            next_problem = problems[next_index]
            match.target_number = next_problem["target_number"]
            match.optimal_cost = next_problem["optimal_cost"]
            metadata["current_index"] = next_index
            match.metadata_snapshot = metadata
            session.add(match)
            await session.commit()
            await session.refresh(match)

            await manager.broadcast_room(
                room.id,
                {
                    "type": "problem_advanced",
                    "room_id": room.id,
                    "match_id": match.id,
                    "current_index": next_index,
                    "target_number": match.target_number,
                    "optimal_cost": match.optimal_cost,
                    "deadline": match.deadline.isoformat() if match.deadline else None,
                },
            )
        else:
            await game_service.close_match(match, submission.id)
            await manager.broadcast_room(
                room.id,
                {
                    "type": "round_finished",
                    "room_id": room.id,
                    "match_id": match.id,
                    "winner_submission_id": submission.id,
                },
            )

    return event_payload


def _build_active_match_response(match) -> ActiveMatchResponse:
    metadata = match.metadata_snapshot or {}
    stored_problems = metadata.get("problems") or []
    problems = stored_problems or [
        {"target_number": match.target_number, "optimal_cost": match.optimal_cost}
    ]
    current_index = metadata.get("current_index", 0)
    mapped = [
        ActiveMatchProblem(
            target_number=item["target_number"],
            optimal_cost=item["optimal_cost"],
            index=index,
        )
        for index, item in enumerate(problems)
    ]
    return ActiveMatchResponse(
        match_id=match.id,
        round_number=match.round_number,
        target_number=match.target_number,
        optimal_cost=match.optimal_cost,
        deadline=match.deadline,
        current_index=current_index,
        total_problems=len(mapped),
        problems=mapped,
    )


@router.get("/{room_id}/active-match", response_model=ActiveMatchResponse | None)
async def get_active_match(room_id: str, session: AsyncSession = Depends(get_session)):
    service = GameService(session)
    match = await service.get_active_match(room_id)
    if not match:
        return None
    return _build_active_match_response(match)

