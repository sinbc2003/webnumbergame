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

const roundLabelMap: Record<string, string> = {
  solo_1v1: "1라운드 개인전",
  relay_2v2: "2vs2 릴레이",
  relay_3v3: "3vs3 릴레이",
  relay_4v4: "4vs4 릴레이",
  team_2v2: "2vs2 팀전",
  team_4v4: "4vs4 팀전",
  tournament_1v1: "토너먼트 개인전",
};

export default async function RoomDetailPage({ params }: { params: { roomId: string } }) {
  const room = await fetchRoom(params.roomId);
  const participants = room ? await fetchParticipants(room.id) : [];

  if (!room) {
    return (
      <TopNav layout="focus" pageTitle="Channel Offline" description="선택한 방을 찾을 수 없습니다." showChat={false}>
        <main className="mx-auto max-w-xl py-10 text-center text-white">
          <p>방을 찾을 수 없습니다.</p>
          <Link href="/rooms" className="text-indigo-300 underline">
            방 목록으로 돌아가기
          </Link>
        </main>
      </TopNav>
    );
  }

  const roundLabel = roundLabelMap[room.round_type] ?? "커스텀 모드";

  return (
    <TopNav
      layout="focus"
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

