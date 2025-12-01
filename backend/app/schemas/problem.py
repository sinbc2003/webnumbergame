from datetime import datetime

from pydantic import BaseModel, Field

from ..enums import RoundType


class ProblemBase(BaseModel):
    round_type: RoundType = RoundType.ROUND1_INDIVIDUAL
    target_number: int = Field(gt=0, le=9999)
    optimal_cost: int = Field(gt=0, le=9999)


class ProblemCreate(ProblemBase):
    pass


class ProblemUpdate(BaseModel):
    round_type: RoundType | None = None
    target_number: int | None = Field(default=None, gt=0, le=9999)
    optimal_cost: int | None = Field(default=None, gt=0, le=9999)


class ProblemPublic(ProblemBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ResetSummary(BaseModel):
    deleted: dict[str, int]


