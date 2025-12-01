import Link from "next/link";

import TopNav from "@/components/TopNav";
import type { Tournament } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function fetchTournaments(): Promise<Tournament[]> {
  try {
    const res = await fetch(`${API_BASE}/tournaments`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function TournamentPage() {
  const tournaments = await fetchTournaments();

  return (
    <div>
      <TopNav />
      <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-white">토너먼트</h1>
          <Link
            href="/tournaments/create"
            className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400"
          >
            새 토너먼트
          </Link>
        </div>
        <div className="space-y-4">
          {tournaments.map((tournament) => (
            <Link
              key={tournament.id}
              href={`/tournaments/${tournament.id}`}
              className="block rounded-xl border border-night-800 bg-night-900/70 p-5 transition hover:border-night-600"
            >
              <p className="text-lg font-semibold text-white">{tournament.name}</p>
              <p className="text-sm text-night-400">
                상태: {tournament.status} · 참가 슬롯 {tournament.participant_slots}명
              </p>
            </Link>
          ))}
          {tournaments.length === 0 && (
            <p className="text-sm text-night-400">등록된 토너먼트가 없습니다. 대회를 생성해 보세요.</p>
          )}
        </div>
      </main>
    </div>
  );
}

