import type { LeaderboardEntry } from "@/types/api";

interface Props {
  entries: LeaderboardEntry[];
}

export default function LeaderboardCard({ entries }: Props) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-night-200">랭킹 TOP 10</p>
        <p className="text-xs text-night-400">점수 = 승리×100 + 정확도 + 활동</p>
      </div>
      <div className="mt-4 space-y-3">
        {entries.map((entry, index) => (
          <div key={entry.user_id} className="rounded-lg border border-night-800/60 bg-night-900/30 p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-white">
                  #{index + 1} {entry.username}
                </p>
                <p className="text-xs text-night-500">
                  승 {entry.win_count} · 패 {entry.loss_count} · 경기 {entry.total_matches} · 총점 {entry.total_score}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-indigo-300">{entry.performance_score} pts</p>
                <p className="text-[11px] text-night-500">{entry.rating} RP</p>
              </div>
            </div>
            <div className="mt-2 grid gap-1 text-[11px] text-night-400">
              <p>승리 {entry.win_points} · 정확도 {entry.accuracy_points} · 활동 {entry.activity_points}</p>
              <div className="h-1.5 w-full rounded-full bg-night-800">
                <div
                  className="h-full rounded-full bg-indigo-500"
                  style={{
                    width: `${Math.min(100, (entry.performance_score / Math.max(1, entries[0]?.performance_score ?? 1)) * 100)}%`,
                  }}
                />
              </div>
            </div>
          </div>
        ))}
        {entries.length === 0 && <p className="text-sm text-night-500">아직 기록이 없습니다.</p>}
      </div>
    </div>
  );
}

