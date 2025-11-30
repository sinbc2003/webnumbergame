"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import api from "@/lib/api";
import type { Room, RoundType } from "@/types/api";

interface Props {
  onCreated?: (room: Room) => void;
}

export default function RoomForm({ onCreated }: Props) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [mode, setMode] = useState<RoundType>("round1_individual");
  const [maxPlayers, setMaxPlayers] = useState(16);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMessage(null);
    try {
      const { data } = await api.post<Room>("/rooms", {
        name,
        description,
        round_type: mode,
        max_players: maxPlayers
      });
      setStatusMessage("방이 생성되었습니다.");
      onCreated?.(data);
      router.push(`/rooms/${data.id}`);
    } catch (error: any) {
      setStatusMessage(error?.response?.data?.detail ?? "방 생성에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-4">
      <h2 className="text-lg font-semibold text-white">새 게임 방 만들기</h2>
      <label className="block text-sm text-night-300">
        방 이름
        <input
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        />
      </label>
      <label className="block text-sm text-night-300">
        설명
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        />
      </label>
      <label className="block text-sm text-night-300">
        모드
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as RoundType)}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        >
          <option value="round1_individual">1라운드 개인전</option>
          <option value="round2_team">2라운드 팀전</option>
        </select>
      </label>
      <label className="block text-sm text-night-300">
        최대 인원
        <input
          type="number"
          min={2}
          max={32}
          value={maxPlayers}
          onChange={(e) => setMaxPlayers(Number(e.target.value))}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        />
      </label>
      {statusMessage && <p className="text-sm text-night-300">{statusMessage}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-indigo-500 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-40"
      >
        {loading ? "생성 중..." : "방 만들기"}
      </button>
    </form>
  );
}

