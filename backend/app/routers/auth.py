from datetime import datetime, timedelta, timezone
import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..config import get_settings
from ..database import get_session
from ..models import User
from ..schemas.auth import RegisterRequest, LoginRequest, GuestRequest, Token
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


@router.post("/guest", response_model=Token)
async def guest_login(payload: GuestRequest, session: AsyncSession = Depends(get_session)):
    nickname = payload.nickname.strip()
    if not nickname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="닉네임을 입력해 주세요.")

    normalized_username = nickname[:30]
    statement = select(User).where(User.username == normalized_username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        # 충돌 시 숫자 접미사를 붙여 고유한 사용자 이름 생성
        suffix = 1
        candidate = normalized_username
        while user is None:
            stmt = select(User).where(User.username == candidate)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is None:
                user = User(
                    email=f"guest-{uuid4().hex}@guest.local",
                    username=candidate,
                    hashed_password=get_password_hash(secrets.token_hex(16)),
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                candidate = f"{normalized_username}{suffix}"
                suffix += 1

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

