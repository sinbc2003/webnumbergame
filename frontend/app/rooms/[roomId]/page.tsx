import Link from "next/link";

import RoomPageShell from "./RoomPageShell";
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

  return (
    <TopNav layout="focus" showChat={false} hideFocusHeader>
      <main className="mx-auto max-w-6xl pb-6 pt-3 sm:pt-4">
        <RoomPageShell room={room} participants={participants} />
      </main>
    </TopNav>
  );
}

