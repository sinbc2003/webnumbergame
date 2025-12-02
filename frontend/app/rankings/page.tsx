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
      <TopNav pageTitle="랭킹 패널" description="MathGame 최상위 지휘관 현황" showChat={false}>
        <main className="mx-auto max-w-5xl px-6 py-8 space-y-4">
          <h1 className="text-3xl font-semibold text-white">랭킹</h1>
          <p className="text-sm text-night-400">실시간 퍼포먼스 점수를 기준으로 정렬된 상위 플레이어 목록입니다.</p>
          <LeaderboardCard entries={leaderboard} />
        </main>
      </TopNav>
    </RequireAuth>
  );
}


