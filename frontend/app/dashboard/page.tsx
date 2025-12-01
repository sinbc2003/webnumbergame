import TopNav from "@/components/TopNav";
import RequireAuth from "@/components/RequireAuth";
import SummaryGrid from "@/components/dashboard/SummaryGrid";
import LeaderboardCard from "@/components/dashboard/LeaderboardCard";
import type { DashboardSummary, LeaderboardEntry } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function fetchSummary(): Promise<DashboardSummary | undefined> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/summary`, { cache: "no-store" });
    if (!res.ok) return undefined;
    return res.json();
  } catch {
    return undefined;
  }
}

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

export default async function DashboardPage() {
  const [summary, leaderboard] = await Promise.all([fetchSummary(), fetchLeaderboard()]);

  return (
    <RequireAuth>
      <div>
        <TopNav />
        <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
          <section>
            <SummaryGrid summary={summary} />
          </section>
          <section className="grid gap-6 lg:grid-cols-2">
            <LeaderboardCard entries={leaderboard} />
            <div className="card">
              <p className="text-sm font-semibold text-night-200">실시간 공지</p>
              <p className="mt-3 text-sm text-night-300">
                1라운드 개인전은 3분 동안 최적해를 찾으면 즉시 승리합니다. 2라운드 팀전에서는 팀 배분과 작전 타임을 활용해 가장
                효율적인 수식을 만들어 보세요.
              </p>
            </div>
          </section>
        </main>
      </div>
    </RequireAuth>
  );
}


