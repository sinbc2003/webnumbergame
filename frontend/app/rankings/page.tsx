import RequireAuth from "@/components/RequireAuth";
import TopNav from "@/components/TopNav";
import LeaderboardCard from "@/components/dashboard/LeaderboardCard";
import type { LeaderboardEntry } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function fetchLeaderboard(): Promise<LeaderboardEntry[]> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/leaderboard`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.entries;
  } catch {
    return [];
  }
}

export const revalidate = 0;

export default async function RankingsPage() {
  const leaderboard = await fetchLeaderboard();
  return (
    <RequireAuth>
      <TopNav layout="focus" pageTitle="MathGame Leaderboard" description="전체 지휘관 순위를 실시간 확인" showChat={false}>
        <div className="leaderboard-full">
          <LeaderboardCard entries={leaderboard} />
        </div>
      </TopNav>
    </RequireAuth>
  );
}


