export type RoomStatus = "waiting" | "in_progress" | "completed" | "archived";
export type RoundType = "round1_individual" | "round2_team";
export type RoomMode = "individual" | "team" | "tournament";

export interface User {
  id: string;
  email: string;
  username: string;
  rating: number;
  win_count: number;
  loss_count: number;
  total_score: number;
  is_admin: boolean;
  created_at: string;
}

export type ParticipantRole = "player" | "spectator";

export interface Room {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  host_id: string;
  status: RoomStatus;
  round_type: RoundType;
  mode: RoomMode;
  team_size: number;
  max_players: number;
  current_round: number;
  player_one_id?: string | null;
  player_two_id?: string | null;
  created_at: string;
}

export interface Participant {
  id: string;
  user_id: string;
  username: string;
  team_label?: string | null;
  is_ready: boolean;
  order_index?: number | null;
  score: number;
  role: ParticipantRole;
}

export interface LeaderboardEntry {
  user_id: string;
  username: string;
  rating: number;
  win_count: number;
  loss_count: number;
  total_matches: number;
  total_score: number;
  win_points: number;
  accuracy_points: number;
  activity_points: number;
  performance_score: number;
}

export interface DashboardSummary {
  total_users: number;
  active_rooms: number;
  ongoing_matches: number;
  online_players: number;
  updated_at: string;
}

export interface Tournament {
  id: string;
  name: string;
  status: string;
  participant_slots: number;
  created_at: string;
}

export interface TournamentSlot {
  id: string;
  position: number;
  user_id?: string | null;
  team_label?: string | null;
  seed?: number | null;
}

export interface TournamentMatch {
  id: string;
  round_index: number;
  matchup_index: number;
  round_type: RoundType;
  room_id?: string | null;
  player_one_id?: string | null;
  player_two_id?: string | null;
}

export interface TournamentBundle {
  tournament: Tournament;
  slots: TournamentSlot[];
  matches: TournamentMatch[];
}

export interface Problem {
  id: string;
  round_type: RoundType;
  target_number: number;
  optimal_cost: number;
  created_at: string;
}

export interface ResetSummary {
  deleted: Record<string, number>;
}

export interface UserResetResponse {
  user: User;
  message: string;
}

export interface ActiveMatchProblem {
  target_number: number;
  optimal_cost: number;
  index: number;
}

export interface ActiveMatch {
  match_id: string;
  round_number: number;
  target_number: number;
  optimal_cost: number;
  deadline?: string | null;
  current_index: number;
  total_problems: number;
  problems: ActiveMatchProblem[];
  player_one_id?: string | null;
  player_two_id?: string | null;
}

