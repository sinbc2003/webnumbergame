import Link from "next/link";

import RoomRealtimePanel from "./RoomRealtimePanel";
import TopNav from "@/components/TopNav";
import type { Participant, Room } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function fetchRoom(roomId: string): Promise<Room | null> {
  try {
    const res = await fetch(`${API_BASE}/rooms/${roomId}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function fetchParticipants(roomId: string): Promise<Participant[]> {
  try {
    const res = await fetch(`${API_BASE}/rooms/${roomId}/participants`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function RoomDetailPage({ params }: { params: { roomId: string } }) {
  const room = await fetchRoom(params.roomId);
  const participants = room ? await fetchParticipants(room.id) : [];

  if (!room) {
    return (
      <div className="mx-auto max-w-xl text-center text-white">
        <TopNav />
        <main className="px-6 py-10">
          <p>방을 찾을 수 없습니다.</p>
          <Link href="/rooms" className="text-indigo-400 underline">
            방 목록으로 돌아가기
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div>
      <TopNav />
      <main className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[2fr_1fr]">
        <section className="space-y-4">
          <div className="card">
            <h1 className="text-2xl font-semibold text-white">{room.name}</h1>
            <p className="mt-1 text-night-400">{room.description}</p>
            <div className="mt-4 grid gap-3 text-sm text-night-300 sm:grid-cols-2">
              <div>
                <p className="text-night-500">모드</p>
                <p className="text-white">{room.round_type === "round1_individual" ? "1라운드 개인전" : "2라운드 팀전"}</p>
              </div>
              <div>
                <p className="text-night-500">최대 인원</p>
                <p className="text-white">{room.max_players}명</p>
              </div>
            </div>
          </div>
          <div className="card">
            <p className="text-sm font-semibold text-night-200">참가자</p>
            <div className="mt-3 space-y-2">
              {participants.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between rounded-lg border border-night-800/70 bg-night-950/40 px-3 py-2 text-sm"
                >
                  <p className="text-night-200">플레이어 {p.user_id.slice(0, 6)}…</p>
                  <p className="text-night-400">{p.team_label ?? "개인전"}</p>
                </div>
              ))}
              {participants.length === 0 && <p className="text-sm text-night-500">아직 참가자가 없습니다.</p>}
            </div>
          </div>
        </section>
        <section>
          <RoomRealtimePanel roomId={room.id} roomCode={room.code} />
        </section>
      </main>
    </div>
  );
}

