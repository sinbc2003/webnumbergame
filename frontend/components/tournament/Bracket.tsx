import Link from "next/link";

interface BracketMatch {
  id: string;
  round: number;
  matchup: number;
  playerOne?: string;
  playerTwo?: string;
  roomId?: string;
}

interface Props {
  matches: BracketMatch[];
}

export default function Bracket({ matches }: Props) {
  if (!matches.length) {
    return <p className="text-sm text-night-400">아직 대진표가 생성되지 않았습니다.</p>;
  }

  const grouped = matches.reduce<Record<number, BracketMatch[]>>((acc, match) => {
    acc[match.round] = acc[match.round] || [];
    acc[match.round].push(match);
    return acc;
  }, {});

  const rounds = Object.keys(grouped)
    .map((key) => Number(key))
    .sort((a, b) => a - b);

  return (
    <div className="grid gap-6" style={{ gridTemplateColumns: `repeat(${Math.max(rounds.length, 1)}, minmax(0, 1fr))` }}>
      {rounds.map((round) => (
        <div key={`round-${round}`} className="space-y-4">
          <p className="text-sm font-semibold text-night-300">Round {round}</p>
          {grouped[round]
            .sort((a, b) => a.matchup - b.matchup)
            .map((match) => (
              <div key={match.id} className="rounded-lg border border-night-800 bg-night-950/60 p-4 text-sm">
                <div className="flex items-center justify-between text-night-400">
                  <span>매치 {match.matchup}</span>
                  {match.roomId && (
                    <Link href={`/rooms/${match.roomId}`} className="text-xs text-indigo-400 underline">
                      방 이동
                    </Link>
                  )}
                </div>
                <div className="mt-3 space-y-2 text-white">
                  <p>{match.playerOne ?? "대기 중"}</p>
                  <p>{match.playerTwo ?? "대기 중"}</p>
                </div>
              </div>
            ))}
        </div>
      ))}
    </div>
  );
}

