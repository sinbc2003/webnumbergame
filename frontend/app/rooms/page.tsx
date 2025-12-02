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
    <div>
      <TopNav />
      <main className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[1fr_320px]">
        <section>
          <RoomList rooms={rooms} />
        </section>
        <section>
          <RoomForm />
        </section>
      </main>
    </div>
  );
}

