from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from ..enums import RoundType


class Problem(SQLModel, table=True):
    __tablename__ = "problems"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    round_type: RoundType = Field(default=RoundType.ROUND1_INDIVIDUAL, index=True)
    target_number: int = Field(gt=0)
    optimal_cost: int = Field(gt=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


