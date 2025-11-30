import type { DashboardSummary } from "@/types/api";

const labels: Record<keyof Omit<DashboardSummary, "updated_at">, string> = {
  total_users: "전체 사용자",
  active_rooms: "활성 방",
  ongoing_matches: "진행중 라운드",
  online_players: "실시간 접속자"
};

interface Props {
  summary?: DashboardSummary;
}

export default function SummaryGrid({ summary }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {(Object.keys(labels) as Array<keyof typeof labels>).map((key) => (
        <div key={key} className="card">
          <p className="text-sm text-night-300">{labels[key]}</p>
          <p className="mt-2 text-3xl font-semibold text-white">
            {summary ? summary[key] : "--"}
          </p>
        </div>
      ))}
    </div>
  );
}

