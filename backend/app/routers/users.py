from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..models import User
from ..schemas.user import UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user

