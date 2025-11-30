import type { LeaderboardEntry } from "@/types/api";

interface Props {
  entries: LeaderboardEntry[];
}

export default function LeaderboardCard({ entries }: Props) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-night-200">랭킹 TOP 10</p>
        <p className="text-xs text-night-400">승수 · 점수 기준</p>
      </div>
      <div className="mt-4 space-y-3">
        {entries.map((entry, index) => (
          <div key={entry.user_id} className="flex items-center justify-between">
            <div>
              <p className="text-sm text-white">
                #{index + 1} {entry.username}
              </p>
              <p className="text-xs text-night-400">승 {entry.win_count} / 점수 {entry.total_score}</p>
            </div>
            <span className="text-sm font-semibold text-night-200">{entry.rating} RP</span>
          </div>
        ))}
        {entries.length === 0 && <p className="text-sm text-night-500">아직 기록이 없습니다.</p>}
      </div>
    </div>
  );
}

