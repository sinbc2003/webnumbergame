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
      <TopNav pageTitle="Channel Offline" description="선택한 방을 찾을 수 없습니다." showChat={false}>
        <main className="mx-auto max-w-xl py-10 text-center text-white">
          <p>방을 찾을 수 없습니다.</p>
          <Link href="/rooms" className="text-indigo-300 underline">
            방 목록으로 돌아가기
          </Link>
        </main>
      </TopNav>
    );
  }

  const roundLabel = room.round_type === "round1_individual" ? "1라운드 개인전" : "2라운드 팀전";

  return (
    <TopNav
      pageTitle={`Room · ${room.name}`}
      description={`방 코드 ${room.code} · ${roundLabel} · 현재 ${participants.length}명`}
      showChat={false}
    >
      <main className="mx-auto max-w-6xl py-6">
        <div className="grid gap-6 lg:grid-cols-[2.2fr,1fr]">
          <section>
            <RoomGamePanel room={room} participants={participants} />
          </section>
          <section>
            <RoomRealtimePanel room={room} participants={participants} />
          </section>
        </div>
      </main>
    </TopNav>
  );
}

