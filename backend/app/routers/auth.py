from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..config import get_settings
from ..database import get_session
from ..models import User
from ..schemas.auth import RegisterRequest, LoginRequest, Token
from ..schemas.user import UserPublic
from ..security import create_access_token, get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=Token)
async def register_user(payload: RegisterRequest, session: AsyncSession = Depends(get_session)):
    for field, value in (("email", payload.email), ("username", payload.username)):
        existing_stmt = select(User).where(getattr(User, field) == value)
        result = await session.execute(existing_stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field}가 이미 사용 중입니다.",
            )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    token_value = create_access_token(user.id, expires_delta)
    return Token(
        access_token=token_value,
        expires_at=datetime.now(timezone.utc) + expires_delta,
        user=UserPublic.model_validate(user),
    )


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    statement = select(User).where(User.email == payload.email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    token_value = create_access_token(user.id, expires_delta)
    return Token(
        access_token=token_value,
        expires_at=datetime.now(timezone.utc) + expires_delta,
        user=UserPublic.model_validate(user),
    )

