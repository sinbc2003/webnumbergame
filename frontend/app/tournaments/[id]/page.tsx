import Link from "next/link";

import TopNav from "@/components/TopNav";
import Bracket from "@/components/tournament/Bracket";
import type { TournamentBundle } from "@/types/api";
import TournamentActions from "./TournamentActions";

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

  const formatPlayer = (userId?: string | null) => {
    if (!userId) return "대기 중";
    return `플레이어 ${userId.slice(0, 6)}…`;
  };

  const bracketMatches = bundle.matches.map((match) => ({
    id: match.id,
    round: match.round_index,
    matchup: match.matchup_index,
    playerOne: formatPlayer(match.player_one_id),
    playerTwo: formatPlayer(match.player_two_id),
    roomId: match.room_id ?? undefined
  }));

  return (
    <div>
      <TopNav />
      <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        <div className="card space-y-4">
          <div>
            <h1 className="text-2xl font-semibold text-white">{bundle.tournament.name}</h1>
            <p className="text-sm text-night-400">상태: {bundle.tournament.status}</p>
          </div>
          <TournamentActions tournamentId={bundle.tournament.id} slots={bundle.slots} />
        </div>
        <Bracket matches={bracketMatches} />
      </main>
    </div>
  );
}

