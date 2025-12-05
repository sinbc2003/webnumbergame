export type TierId = "bronze" | "silver" | "gold" | "diamond" | "ruby" | "platinum";

export interface TierDefinition {
  id: TierId;
  label: string;
  minScore: number;
}

export const TIER_DEFINITIONS: TierDefinition[] = [
  { id: "bronze", label: "Bronze", minScore: 0 },
  { id: "silver", label: "Silver", minScore: 1000 },
  { id: "gold", label: "Gold", minScore: 2000 },
  { id: "diamond", label: "Diamond", minScore: 3000 },
  { id: "ruby", label: "Ruby", minScore: 4000 },
  { id: "platinum", label: "Platinum", minScore: 5000 },
];

const MIN_TIER = TIER_DEFINITIONS[0];

export const getTierFromScore = (score: number | null | undefined): TierId => {
  const normalized = Number.isFinite(score) ? (score as number) : 0;
  for (let index = TIER_DEFINITIONS.length - 1; index >= 0; index -= 1) {
    const tier = TIER_DEFINITIONS[index];
    if (normalized >= tier.minScore) {
      return tier.id;
    }
  }
  return MIN_TIER.id;
};

