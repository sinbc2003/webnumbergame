from enum import Enum


class RoomStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RoundType(str, Enum):
    ROUND1_INDIVIDUAL = "round1_individual"
    ROUND2_TEAM = "round2_team"


class MatchStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"


class TournamentStatus(str, Enum):
    DRAFT = "draft"
    SEEDING = "seeding"
    LIVE = "live"
    COMPLETED = "completed"

