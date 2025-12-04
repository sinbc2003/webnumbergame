export const RELAY_TEAM_A = "relay_a";
export const RELAY_TEAM_B = "relay_b";

export type RelayTeamLabel = typeof RELAY_TEAM_A | typeof RELAY_TEAM_B;

export const describeRelayTeam = (label: RelayTeamLabel) => {
  if (label === RELAY_TEAM_A) return "릴레이 A 팀";
  return "릴레이 B 팀";
};

