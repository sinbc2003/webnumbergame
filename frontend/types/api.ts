export type RoomStatus = "waiting" | "in_progress" | "completed" | "archived";
export type RoundType = "round1_individual" | "round2_team";

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

export interface Room {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  host_id: string;
  status: RoomStatus;
  round_type: RoundType;
  max_players: number;
  current_round: number;
  created_at: string;
}

export interface Participant {
  id: string;
  user_id: string;
  team_label?: string | null;
  is_ready: boolean;
  order_index?: number | null;
  score: number;
}

export interface LeaderboardEntry {
  user_id: string;
  username: string;
  rating: number;
  win_count: number;
  total_score: number;
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
  starts_at?: string | null;
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
}

export interface TournamentBundle {
  tournament: Tournament;
  slots: TournamentSlot[];
  matches: TournamentMatch[];
}

