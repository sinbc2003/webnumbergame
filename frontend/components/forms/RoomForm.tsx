"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import api from "@/lib/api";
import type { Room, RoundType, RoomMode } from "@/types/api";
import { useShellTransition } from "@/hooks/useShellTransition";

interface Props {
  onCreated?: (room: Room) => void;
}

export default function RoomForm({ onCreated }: Props) {
  const router = useRouter();
  const transition = useShellTransition();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [roundType, setRoundType] = useState<RoundType>("round1_individual");
  const [matchMode, setMatchMode] = useState<RoomMode>("individual");
  const [teamSize, setTeamSize] = useState(1);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (matchMode === "team") {
      setRoundType("round2_team");
      setTeamSize((prev) => (prev === 2 || prev === 4 ? prev : 2));
    } else {
      setRoundType("round1_individual");
      setTeamSize((prev) => (prev >= 1 && prev <= 3 ? prev : 1));
    }
  }, [matchMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMessage(null);
    try {
      const { data } = await api.post<Room>("/rooms", {
        name,
        description,
        round_type: roundType,
        mode: matchMode,
        team_size: teamSize,
      });
      setStatusMessage("방이 생성되었습니다.");
      onCreated?.(data);
      transition(() => router.push(`/rooms/${data.id}`));
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
        게임 분류
        <select
          value={matchMode}
          onChange={(e) => setMatchMode(e.target.value as RoomMode)}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        >
          <option value="individual">개인전</option>
          <option value="team">팀전</option>
        </select>
      </label>
      <label className="block text-sm text-night-300">
        대전 방식
        <select
          value={teamSize}
          onChange={(e) => setTeamSize(Number(e.target.value))}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        >
          {matchMode === "individual" ? (
            <>
              <option value={1}>1 vs 1 (기본)</option>
              <option value={2}>2 vs 2 (릴레이)</option>
              <option value={3}>3 vs 3 (릴레이)</option>
            </>
          ) : (
            <>
              <option value={2}>2 vs 2 팀전</option>
              <option value={4}>4 vs 4 팀전</option>
            </>
          )}
        </select>
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

