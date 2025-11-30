interface MatchSlot {
  round: number;
  index: number;
  label: string;
  team?: string;
}

interface Props {
  slots: MatchSlot[];
}

export default function Bracket({ slots }: Props) {
  const grouped = slots.reduce<Record<number, MatchSlot[]>>((acc, slot) => {
    acc[slot.round] = acc[slot.round] || [];
    acc[slot.round].push(slot);
    return acc;
  }, {});

  return (
    <div className="grid gap-6 md:grid-cols-4">
      {Object.keys(grouped)
        .sort((a, b) => Number(a) - Number(b))
        .map((round) => (
          <div key={round} className="space-y-4">
            <p className="text-sm font-semibold text-night-300">Round {round}</p>
            {grouped[Number(round)].map((slot) => (
              <div key={slot.label} className="rounded-lg border border-night-800 bg-night-950/60 p-3 text-sm">
                <p className="text-night-400">{slot.label}</p>
                <p className="font-medium text-white">{slot.team ?? "대기 중"}</p>
              </div>
            ))}
          </div>
        ))}
    </div>
  );
}

