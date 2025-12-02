import Link from "next/link";

import RoomRealtimePanel from "./RoomRealtimePanel";
import RoomGamePanel from "./RoomGamePanel";
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
    <div className="min-h-screen">
      <TopNav />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-[2.2fr,1fr]">
          <section>
            <RoomGamePanel room={room} participants={participants} />
          </section>
          <section>
            <RoomRealtimePanel room={room} participants={participants} />
          </section>
        </div>
      </main>
    </div>
  );
}

