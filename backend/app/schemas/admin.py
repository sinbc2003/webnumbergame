from pydantic import BaseModel, Field

from .user import UserPublic


class UserResetRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    user_id: str | None = None


class UserResetResponse(BaseModel):
    user: UserPublic
    message: str

