import Link from "next/link";

import type { Room } from "@/types/api";

interface Props {
  rooms: Room[];
}

export default function RoomList({ rooms }: Props) {
  if (!rooms.length) {
    return (
      <div className="card text-sm text-night-300">
        아직 생성된 방이 없습니다. 새로운 숫자게임 방을 만들어보세요!
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {rooms.map((room) => (
        <Link
          key={room.id}
          href={`/rooms/${room.id}`}
          className="block rounded-xl border border-night-800 bg-night-900/70 p-5 transition hover:border-night-600 hover:bg-night-900"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lg font-semibold text-white">{room.name}</p>
              <p className="text-sm text-night-400">{room.description ?? "설명 없음"}</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase text-night-400">{room.round_type === "round1_individual" ? "개인전" : "팀전"}</p>
              <p className="text-sm text-night-300">코드 {room.code}</p>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}

