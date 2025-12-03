import type { RoomMode } from "@/types/api";

interface ModeProps {
  mode: RoomMode;
  team_size?: number;
}

const formatMatchup = (teamSize?: number) => {
  const normalized = Math.max(1, teamSize ?? 1);
  return `${normalized} vs ${normalized}`;
};

export const describeRoomMode = ({ mode, team_size }: ModeProps) => {
  if (mode === "team") {
    return `팀전 · ${formatMatchup(team_size)}`;
  }
  if (mode === "individual") {
    return team_size && team_size > 1
      ? `개인전 · ${formatMatchup(team_size)} 릴레이`
      : "개인전 · 1 vs 1";
  }
  return "토너먼트";
};

export const describeModeBadge = ({ mode, team_size }: ModeProps) => {
  if (mode === "team") {
    return `팀전 ${formatMatchup(team_size)}`;
  }
  if (mode === "individual") {
    return team_size && team_size > 1 ? `개인전 ${formatMatchup(team_size)}` : "개인전 1 vs 1";
  }
  return "토너먼트";
};

export const describeMatchup = (teamSize?: number) => formatMatchup(teamSize);

