import type { LeaderboardEntry } from "@/types/api";
import { getTierFromScore } from "@/lib/tiers";

interface Props {
  entries: LeaderboardEntry[];
}

const tierColor = (rank: number) => {
  if (rank === 1) return "text-amber-300";
  if (rank === 2) return "text-slate-200";
  if (rank === 3) return "text-orange-400";
  return "text-slate-400";
};

export default function LeaderboardCard({ entries }: Props) {
  return (
    <div className="ladder-card">
      <header className="ladder-card__header">
        <div>
          <p className="ladder-card__eyebrow">MATHGAME NETWORK</p>
          <h2 className="ladder-card__title">Leaderboard</h2>
        </div>
        <div className="ladder-card__tags">
          <span>1v1</span>
          <span>Season · Live</span>
        </div>
      </header>
      <div className="ladder-table__wrapper">
        <table className="ladder-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Player</th>
              <th>Points</th>
              <th>Wins</th>
              <th>Losses</th>
              <th>Matches</th>
              <th>Rating</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, index) => {
              const resolvedScore =
                typeof entry.performance_score === "number"
                  ? entry.performance_score
                  : typeof entry.total_score === "number"
                    ? entry.total_score
                    : typeof entry.rating === "number"
                      ? entry.rating
                      : 0;
              const tier = getTierFromScore(resolvedScore);
              return (
                <tr key={entry.user_id} className={index === 1 ? "ladder-row--highlight" : undefined}>
                  <td className={tierColor(index + 1)}>#{index + 1}</td>
                  <td>
                    <div className="ladder-player">
                      <div className="ladder-avatar" aria-hidden="true">
                        {entry.username.slice(0, 1).toUpperCase()}
                      </div>
                      <div>
                        <p className="ladder-player__name">{entry.username}</p>
                        <p className="ladder-player__meta">{entry.win_count}W / {entry.loss_count}L · {entry.rating} RP</p>
                      </div>
                      <span className={`ladder-badge badge-${tier}`}>{tier.toUpperCase()}</span>
                    </div>
                  </td>
                  <td className="text-cyan-200">{entry.performance_score}</td>
                  <td>{entry.win_count}</td>
                  <td>{entry.loss_count}</td>
                  <td>{entry.total_matches}</td>
                  <td>{entry.total_score}</td>
                </tr>
              );
            })}
            {entries.length === 0 && (
              <tr>
                <td colSpan={7} className="ladder-empty">
                  아직 기록이 없습니다.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

