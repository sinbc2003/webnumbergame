from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..database import get_session
from ..dependencies import get_current_user
from ..models import Tournament, User
from ..schemas.tournament import (
    TournamentCreate,
    TournamentPublic,
    SeedRequest,
    TournamentMatchPublic,
    TournamentBundleResponse,
    TournamentSlotPublic,
)
from ..services.tournament_service import TournamentService

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


async def _get_tournament_or_404(session: AsyncSession, tournament_id: str) -> Tournament:
    statement = select(Tournament).where(Tournament.id == tournament_id)
    result = await session.execute(statement)
    tournament = result.scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="토너먼트를 찾을 수 없습니다.")
    return tournament


@router.post("", response_model=TournamentPublic, status_code=status.HTTP_201_CREATED)
async def create_tournament(
    payload: TournamentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = TournamentService(session)
    tournament = await service.create(host=current_user, payload=payload)
    return TournamentPublic.model_validate(tournament)


@router.get("", response_model=list[TournamentPublic])
async def list_tournaments(session: AsyncSession = Depends(get_session)):
    statement = select(Tournament).order_by(Tournament.created_at.desc())
    result = await session.execute(statement)
    tournaments = result.scalars().all()
    return [TournamentPublic.model_validate(t) for t in tournaments]


@router.post("/{tournament_id}/seed", response_model=TournamentPublic)
async def seed_tournament(
    tournament_id: str,
    payload: SeedRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tournament = await _get_tournament_or_404(session, tournament_id)
    if tournament.host_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="호스트만 시드를 설정할 수 있습니다.")

    service = TournamentService(session)
    await service.seed_slots(tournament=tournament, seeds=payload.slots)
    return TournamentPublic.model_validate(tournament)


@router.post("/{tournament_id}/bracket", response_model=list[TournamentMatchPublic])
async def build_bracket(
    tournament_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tournament = await _get_tournament_or_404(session, tournament_id)
    if tournament.host_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="호스트만 브래킷을 생성할 수 있습니다.")
    service = TournamentService(session)
    matches = await service.create_bracket(tournament)
    return [TournamentMatchPublic.model_validate(match) for match in matches]


@router.get("/{tournament_id}", response_model=TournamentPublic)
async def get_tournament(tournament_id: str, session: AsyncSession = Depends(get_session)):
    tournament = await _get_tournament_or_404(session, tournament_id)
    return TournamentPublic.model_validate(tournament)


@router.get("/{tournament_id}/bundle", response_model=TournamentBundleResponse)
async def get_tournament_bundle(tournament_id: str, session: AsyncSession = Depends(get_session)):
    service = TournamentService(session)
    bundle = await service.get_bundle(tournament_id)
    if not bundle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="토너먼트를 찾을 수 없습니다.")
    return TournamentBundleResponse(
        tournament=TournamentPublic.model_validate(bundle.tournament),
        slots=[TournamentSlotPublic.model_validate(slot) for slot in bundle.slots],
        matches=[TournamentMatchPublic.model_validate(match) for match in bundle.matches],
    )

