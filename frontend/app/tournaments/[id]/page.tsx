import Link from "next/link";

import TopNav from "@/components/TopNav";
import Bracket from "@/components/tournament/Bracket";
import type { TournamentBundle } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function fetchBundle(id: string): Promise<TournamentBundle | null> {
  try {
    const res = await fetch(`${API_BASE}/tournaments/${id}/bundle`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function TournamentDetailPage({ params }: { params: { id: string } }) {
  const bundle = await fetchBundle(params.id);

  if (!bundle) {
    return (
      <div>
        <TopNav />
        <main className="mx-auto max-w-4xl px-6 py-10 text-center text-white">
          <p>토너먼트를 찾을 수 없습니다.</p>
          <Link href="/tournaments" className="text-indigo-400 underline">
            목록으로 돌아가기
          </Link>
        </main>
      </div>
    );
  }

  const bracketSlots = bundle.slots.map((slot) => ({
    round: Math.ceil(slot.position / 2),
    index: slot.position,
    label: `시드 ${slot.seed ?? slot.position}`,
    team: slot.team_label ?? slot.user_id ?? "-"
  }));

  return (
    <div>
      <TopNav />
      <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        <div className="card">
          <h1 className="text-2xl font-semibold text-white">{bundle.tournament.name}</h1>
          <p className="text-sm text-night-400">상태: {bundle.tournament.status}</p>
        </div>
        <Bracket slots={bracketSlots} />
      </main>
    </div>
  );
}

