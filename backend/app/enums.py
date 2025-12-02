from enum import Enum


class RoomStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RoundType(str, Enum):
    SOLO_1V1 = "solo_1v1"
    RELAY_2V2 = "relay_2v2"
    RELAY_3V3 = "relay_3v3"
    RELAY_4V4 = "relay_4v4"
    TEAM_2V2 = "team_2v2"
    TEAM_4V4 = "team_4v4"
    TOURNAMENT_1V1 = "tournament_1v1"


class MatchStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"


class TournamentStatus(str, Enum):
    DRAFT = "draft"
    SEEDING = "seeding"
    LIVE = "live"
    COMPLETED = "completed"


class ParticipantRole(str, Enum):
    PLAYER = "player"
    SPECTATOR = "spectator"
