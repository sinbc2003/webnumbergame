"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import Link from "next/link";
import { useRouter } from "next/navigation";
import useSWR from "swr";

import type { Participant, Room } from "@/types/api";
import api from "@/lib/api";
import { describeRoomMode } from "@/lib/roomLabels";
import RoomCreateBoard from "./RoomCreateBoard";

const fetchParticipants = async (roomId: string) => {
  const { data } = await api.get<Participant[]>(`/rooms/${roomId}/participants`);
  return data;
};

interface RoomHubProps {
  initialRooms: Room[];
  view: "join" | "create";
  showTabs?: boolean;
}

const fetchRooms = async () => {
  const { data } = await api.get<Room[]>("/rooms");
  return data;
};

const formatRoomCreatedAt = (value?: string | null) => {
  if (!value) return "-";
  const hasTimezone = /([+-]\d{2}:?\d{2}|z)$/i.test(value);
  const normalized = hasTimezone ? value : `${value}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export default function RoomHub({ initialRooms, view, showTabs = false }: RoomHubProps) {
  const [currentView, setCurrentView] = useState<"join" | "create">(view);
  const activeView = showTabs ? currentView : view;
  const { data: liveRooms } = useSWR("/rooms", fetchRooms, { fallbackData: initialRooms, refreshInterval: 5000 });
  const rooms = liveRooms ?? [];
  return (
    <div className="room-hub">
      {showTabs && (
        <div className="room-hub__tabs">
          <button type="button" onClick={() => setCurrentView("join")} className={clsx(activeView === "join" && "active")}>
            Join
          </button>
          <button type="button" onClick={() => setCurrentView("create")} className={clsx(activeView === "create" && "active")}>
            Create
          </button>
        </div>
      )}
      {activeView === "join" ? <RoomJoinPanel rooms={rooms} /> : <RoomCreateBoard />}
    </div>
  );
}

function RoomJoinPanel({ rooms }: { rooms: Room[] }) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [modeFilter, setModeFilter] = useState<"all" | "solo" | "team">("all");
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(rooms[0]?.id ?? null);
  const filtered = useMemo(() => {
    return rooms.filter((room) => {
      const matchesSearch = room.name.toLowerCase().includes(search.trim().toLowerCase());
      if (!matchesSearch) return false;
      if (modeFilter === "all") return true;
      return modeFilter === "solo" ? room.mode === "individual" : room.mode === "team";
    });
  }, [rooms, search, modeFilter]);
  const selectedRoom = filtered.find((room) => room.id === selectedRoomId) ?? filtered[0];
  const { data: participants } = useSWR(selectedRoom ? selectedRoom.id : null, fetchParticipants);
  const playerCount = participants?.length ?? 0;

  return (
    <div className="room-join">
      <div className="room-join__list">
        <div className="room-list__toolbar">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search game name"
            className="room-list__search"
          />
          <div className="room-list__modes">
            <button
              type="button"
              onClick={() => setModeFilter("all")}
              className={clsx(modeFilter === "all" && "active")}
            >
              전체
            </button>
            <button
              type="button"
              onClick={() => setModeFilter("solo")}
              className={clsx(modeFilter === "solo" && "active")}
            >
              개인전
            </button>
            <button
              type="button"
              onClick={() => setModeFilter("team")}
              className={clsx(modeFilter === "team" && "active")}
            >
              팀전
            </button>
          </div>
          <Link href="/tournaments" className="room-list__filter">
            토너먼트
          </Link>
        </div>
        <div className="room-list__table">
          <div className="room-list__header">
            <span>Players</span>
            <span>Game Name</span>
            <span>Type</span>
            <span>Created</span>
          </div>
          <div className="room-list__body">
            {filtered.map((room) => (
              <button
                key={room.id}
                type="button"
                className={clsx("room-list__row", selectedRoom?.id === room.id && "active")}
                onClick={() => setSelectedRoomId(room.id)}
                onDoubleClick={() => router.push(`/rooms/${room.id}`)}
              >
                <span className="room-list__players">-- / {room.max_players}</span>
                <span className="room-list__name">{room.name}</span>
                <span>{describeRoomMode({ mode: room.mode, team_size: room.team_size })}</span>
                <span>{formatRoomCreatedAt(room.created_at)}</span>
              </button>
            ))}
            {filtered.length === 0 && <p className="room-list__empty">조건에 맞는 방이 없습니다.</p>}
          </div>
        </div>
      </div>
      <div className="room-join__details">
        {selectedRoom ? (
          <>
            <p className="room-join__title">{selectedRoom.name}</p>
            <p className="room-join__label">{describeRoomMode({ mode: selectedRoom.mode, team_size: selectedRoom.team_size })}</p>
            <dl className="room-join__meta">
              <div>
                <dt>Players</dt>
                <dd>
                  {playerCount} / {selectedRoom.max_players}
                </dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{selectedRoom.status}</dd>
              </div>
              <div>
                <dt>Room Code</dt>
                <dd>{selectedRoom.code}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{formatRoomCreatedAt(selectedRoom.created_at)}</dd>
              </div>
            </dl>
            <p className="room-join__desc">{selectedRoom.description ?? "설명 없음"}</p>
            <Link href={`/rooms/${selectedRoom.id}`} className="room-join__cta">
              Join
            </Link>
          </>
        ) : (
          <p className="room-list__empty">방을 선택해 주세요.</p>
        )}
      </div>
    </div>
  );
}


