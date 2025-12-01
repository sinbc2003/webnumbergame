from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..config import get_settings
from ..database import get_session
from ..dependencies import get_current_user
from ..enums import RoundType, ParticipantRole
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
    PlayerAssignmentRequest,
    InputUpdateRequest,
)
from ..services.game_service import GameService
from ..services.room_service import RoomService

router = APIRouter(prefix="/rooms", tags=["rooms"])
settings = get_settings()


def _participant_to_public(participant: RoomParticipant, username: str) -> ParticipantPublic:
    payload = participant.model_dump()
    payload["username"] = username
    return ParticipantPublic.model_validate(payload)


@router.delete("/{room_id}/participants/me", status_code=status.HTTP_204_NO_CONTENT)
async def leave_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    room = await _get_room_or_404(session, room_id)
    participant_stmt = select(RoomParticipant).where(
        RoomParticipant.room_id == room.id,
        RoomParticipant.user_id == current_user.id,
    )
    participant = (await session.execute(participant_stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="참가 중이 아닙니다.")

    await session.delete(participant)

    slot_changed = False
    if room.player_one_id == current_user.id:
        room.player_one_id = None
        slot_changed = True
    if room.player_two_id == current_user.id:
        room.player_two_id = None
        slot_changed = True

    if room.host_id == current_user.id:
        await session.delete(room)
        await session.commit()
        await manager.broadcast_room(
            room.id,
            {"type": "room_closed", "room_id": room.id},
        )
        return

    session.add(room)
    await session.commit()

    await manager.broadcast_room(
        room.id,
        {
            "type": "participant_left",
            "room_id": room.id,
            "user_id": current_user.id,
        },
    )
    if slot_changed:
        await manager.broadcast_room(
            room.id,
            {
                "type": "player_assignment",
                "room_id": room.id,
                "player_one_id": room.player_one_id,
                "player_two_id": room.player_two_id,
            },
        )


async def _get_room_or_404(session: AsyncSession, room_id: str) -> Room:
    statement = select(Room).where(Room.id == room_id)
    result = await session.execute(statement)
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="방을 찾을 수 없습니다.")
    await _ensure_host_active(session, room)
    return room


async def _ensure_host_active(session: AsyncSession, room: Room) -> None:
    stmt = select(RoomParticipant.id).where(
        RoomParticipant.room_id == room.id,
        RoomParticipant.user_id == room.host_id,
    )
    host = (await session.execute(stmt)).scalar_one_or_none()
    if host:
        return

    await session.delete(room)
    await session.commit()
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="방이 종료되었습니다.")


async def _set_participant_role(
    session: AsyncSession,
    room_id: str,
    user_id: str | None,
    role: ParticipantRole,
) -> None:
    if not user_id:
        return
    statement = select(RoomParticipant).where(
        RoomParticipant.room_id == room_id,
        RoomParticipant.user_id == user_id,
    )
    result = await session.execute(statement)
    participant = result.scalar_one_or_none()
    if participant:
        participant.role = role
        session.add(participant)


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
    statement = (
        select(RoomParticipant, User)
        .join(User, User.id == RoomParticipant.user_id)
        .where(RoomParticipant.room_id == room_id)
    )
    result = await session.execute(statement)
    rows = result.all()
    return [_participant_to_public(participant, user.username) for participant, user in rows]


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
    await _ensure_host_active(session, room)
    try:
        participant = await service.join_room(room=room, user=current_user, team_label=payload.team_label)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    participant_public = _participant_to_public(participant, current_user.username)

    await manager.broadcast_room(
        room.id,
        {
            "type": "participant_joined",
            "room_id": room.id,
            "participant": participant_public.model_dump(),
        },
    )
    if participant.role == ParticipantRole.PLAYER:
        await manager.broadcast_room(
            room.id,
            {
                "type": "player_assignment",
                "room_id": room.id,
                "player_one_id": room.player_one_id,
                "player_two_id": room.player_two_id,
            },
        )
    return participant_public


@router.post("/{room_id}/players", response_model=RoomPublic)
async def assign_player(
    room_id: str,
    payload: PlayerAssignmentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    room = await _get_room_or_404(session, room_id)
    if room.host_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="방장만 플레이어를 지정할 수 있습니다.")

    slot_attr = "player_one_id" if payload.slot == "player_one" else "player_two_id"
    previous_user_id = getattr(room, slot_attr)

    if payload.user_id:
        participant_stmt = select(RoomParticipant).where(
            RoomParticipant.room_id == room.id,
            RoomParticipant.user_id == payload.user_id,
        )
        participant_result = await session.execute(participant_stmt)
        participant = participant_result.scalar_one_or_none()
        if not participant:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="해당 사용자가 방에 참가해 있지 않습니다.")

    setattr(room, slot_attr, payload.user_id)
    other_attr = "player_two_id" if slot_attr == "player_one_id" else "player_one_id"
    if payload.user_id and getattr(room, other_attr) == payload.user_id:
        setattr(room, other_attr, previous_user_id if previous_user_id and previous_user_id != payload.user_id else None)

    session.add(room)
    await _set_participant_role(session, room.id, previous_user_id, ParticipantRole.SPECTATOR)
    await _set_participant_role(session, room.id, payload.user_id, ParticipantRole.PLAYER)
    await _set_participant_role(session, room.id, room.player_one_id, ParticipantRole.PLAYER)
    await _set_participant_role(session, room.id, room.player_two_id, ParticipantRole.PLAYER)

    await session.commit()
    await session.refresh(room)

    await manager.broadcast_room(
        room.id,
        {
            "type": "player_assignment",
            "room_id": room.id,
            "player_one_id": room.player_one_id,
            "player_two_id": room.player_two_id,
        },
    )
    return RoomPublic.model_validate(room)


@router.post("/{room_id}/inputs", status_code=status.HTTP_204_NO_CONTENT)
async def update_player_input(
    room_id: str,
    payload: InputUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    room = await _get_room_or_404(session, room_id)
    if current_user.id not in {room.player_one_id, room.player_two_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="플레이어만 입력을 전송할 수 있습니다.")

    await manager.broadcast_room(
        room.id,
        {
            "type": "input_update",
            "room_id": room.id,
            "user_id": current_user.id,
            "expression": payload.expression,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


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

    if not room.player_one_id or not room.player_two_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="두 플레이어가 지정되어야 합니다.",
        )

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
    metadata = {
        "problems": serialized,
        "current_index": 0,
        "player_one_id": room.player_one_id,
        "player_two_id": room.player_two_id,
    }

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
        "player_one_id": room.player_one_id,
        "player_two_id": room.player_two_id,
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
    player_one_id = metadata.get("player_one_id")
    player_two_id = metadata.get("player_two_id")
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
        player_one_id=player_one_id,
        player_two_id=player_two_id,
    )


@router.get("/{room_id}/active-match", response_model=ActiveMatchResponse | None)
async def get_active_match(room_id: str, session: AsyncSession = Depends(get_session)):
    service = GameService(session)
    match = await service.get_active_match(room_id)
    if not match:
        return None
    return _build_active_match_response(match)

