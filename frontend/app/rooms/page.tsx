import RoomForm from "@/components/forms/RoomForm";
import RoomList from "@/components/rooms/RoomList";
import TopNav from "@/components/TopNav";
import type { Room } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function fetchRooms(): Promise<Room[]> {
  try {
    const res = await fetch(`${API_BASE}/rooms`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export const revalidate = 0;

export default async function RoomsPage() {
  const rooms = await fetchRooms();
  return (
    <TopNav layout="focus" pageTitle="Channel Lobby : Rooms" description="실시간 방 편성 · MATCH QUEUE READY" showChat={false}>
      <main className="mx-auto grid max-w-6xl gap-6 py-4 lg:grid-cols-[1fr_320px]">
        <section>
          <RoomList rooms={rooms} />
        </section>
        <section>
          <RoomForm />
        </section>
      </main>
    </TopNav>
  );
}

