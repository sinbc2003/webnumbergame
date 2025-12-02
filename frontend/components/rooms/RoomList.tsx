import Link from "next/link";

import type { Room, Participant } from "@/types/api";

type RoomWithParticipants = Room & { participants: Participant[] };

interface Props {
  rooms: RoomWithParticipants[];
}

const ROUND_LABELS: Record<string, string> = {
  round1_individual: "1라운드 · 개인전",
  round2_team: "2라운드 · 팀전",
};

const STATUS_LABELS: Record<string, string> = {
  waiting: "대기 중",
  in_progress: "진행 중",
  completed: "완료",
  archived: "종료",
};

const statusStyles: Record<string, string> = {
  waiting: "border-amber-500/40 text-amber-200",
  in_progress: "border-emerald-500/40 text-emerald-200",
  completed: "border-indigo-500/40 text-indigo-200",
  archived: "border-night-700 text-night-400",
};

const playerLabel = (room: RoomWithParticipants, slotId: string | undefined | null, label: string) => {
  if (!slotId) {
    return `${label}: 대기 중`;
  }
  const participant = room.participants.find((p) => p.user_id === slotId);
  return `${label}: ${participant?.username ?? "배정 완료"}`;
};

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
      {rooms.map((room) => {
        const playerOne = playerLabel(room, room.player_one_id, "플레이어 1");
        const playerTwo = playerLabel(room, room.player_two_id, "플레이어 2");
        const participantCount = room.participants.length;
        const roundLabel = ROUND_LABELS[room.round_type] ?? "라운드 정보";
        const statusLabel = STATUS_LABELS[room.status] ?? "상태 미정";
        const statusBadge = statusStyles[room.status] ?? "border-night-700 text-night-400";

        return (
          <Link
            key={room.id}
            href={`/rooms/${room.id}`}
            className="block rounded-2xl border border-night-800 bg-night-900/70 p-5 transition hover:border-night-600 hover:bg-night-900"
          >
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-lg font-semibold text-white">{room.name}</p>
                  {room.description ? (
                    <p className="text-sm text-night-400">{room.description}</p>
                  ) : (
                    <p className="text-sm text-night-500">설명 없음</p>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-indigo-500/40 px-3 py-1 text-xs text-indigo-200">
                    {roundLabel}
                  </span>
                  <span className={`rounded-full border px-3 py-1 text-xs ${statusBadge}`}>{statusLabel}</span>
                </div>
              </div>

              <div className="grid gap-3 text-sm text-night-200 lg:grid-cols-3">
                <div className="rounded-xl border border-night-800/70 bg-night-950/40 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-night-500">플레이어 슬롯</p>
                  <div className="mt-2 space-y-1 text-night-100">
                    <p>{playerOne}</p>
                    <p>{playerTwo}</p>
                  </div>
                </div>
                <div className="rounded-xl border border-night-800/70 bg-night-950/40 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-night-500">참여자</p>
                  <p className="mt-1 text-2xl font-semibold text-white">
                    {participantCount} <span className="text-sm text-night-500">/ {room.max_players}</span>
                  </p>
                  <p className="text-[11px] text-night-500">관전 포함</p>
                </div>
                <div className="rounded-xl border border-night-800/70 bg-night-950/40 p-3">
                  <p className="text-[11px] uppercase tracking-wide text-night-500">진행 라운드</p>
                  <p className="mt-1 text-2xl font-semibold text-white">{room.current_round}</p>
                  <p className="text-[11px] text-night-500">라운드가 시작되면 자동 업데이트</p>
                </div>
              </div>

              <div className="flex items-center justify-end">
                <span className="text-sm font-semibold text-indigo-300">입장하기 →</span>
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

