import RoomForm from "@/components/forms/RoomForm";
import RoomList from "@/components/rooms/RoomList";
import TopNav from "@/components/TopNav";
import type { Room, Participant } from "@/types/api";

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

async function fetchParticipants(roomId: string): Promise<Participant[]> {
  try {
    const res = await fetch(`${API_BASE}/rooms/${roomId}/participants`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export const revalidate = 0;

export default async function RoomsPage() {
  const rooms = await fetchRooms();
  const roomsWithParticipants = await Promise.all(
    rooms.map(async (room) => {
      const participants = await fetchParticipants(room.id);
      return { ...room, participants };
    }),
  );
  return (
    <div>
      <TopNav />
      <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        <section>
          <RoomList rooms={roomsWithParticipants} />
        </section>
        <section>
          <RoomForm />
        </section>
      </main>
    </div>
  );
}

