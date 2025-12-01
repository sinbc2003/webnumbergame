"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import type { Participant } from "@/types/api";

interface EventMessage {
  type: string;
  [key: string]: any;
}

interface Props {
  roomId: string;
  roomCode: string;
  hostId: string;
  currentRound: number;
  playerOneId?: string;
  playerTwoId?: string;
  participants: Participant[];
}

const resolveWsBase = () => {
  const { wsBase, apiBase } = getRuntimeConfig();
  if (wsBase) {
    return wsBase;
  }
  const trimmed = apiBase.replace(/\/api$/, "");
  return trimmed.replace(/^http/, "ws");
};

export default function RoomRealtimePanel({
  roomId,
  roomCode,
  hostId,
  currentRound,
  playerOneId,
  playerTwoId,
  participants,
}: Props) {
  const wsUrl = useMemo(() => `${resolveWsBase()}/ws/rooms/${roomId}`, [roomId]);
  const [events, setEvents] = useState<EventMessage[]>([]);
  const [roundNumber, setRoundNumber] = useState(currentRound);
  const [durationMinutes, setDurationMinutes] = useState(3);
  const [problemCount, setProblemCount] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [playerOne, setPlayerOne] = useState<string | undefined>(playerOneId ?? undefined);
  const [playerTwo, setPlayerTwo] = useState<string | undefined>(playerTwoId ?? undefined);
  const [participantList, setParticipantList] = useState<Participant[]>(participants);
  const [assigningSlot, setAssigningSlot] = useState<"player_one" | "player_two" | null>(null);
  const [selectedPlayers, setSelectedPlayers] = useState({
    player_one: playerOneId ?? "",
    player_two: playerTwoId ?? "",
  });

  const { user } = useAuth();
  const isHost = user?.id === hostId;

  useEffect(() => {
    setRoundNumber(currentRound);
  }, [currentRound]);

  useEffect(() => {
    setPlayerOne(playerOneId ?? undefined);
    setPlayerTwo(playerTwoId ?? undefined);
    setSelectedPlayers({
      player_one: playerOneId ?? "",
      player_two: playerTwoId ?? "",
    });
  }, [playerOneId, playerTwoId]);

  useEffect(() => {
    setParticipantList(participants);
  }, [participants]);

  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "player_assignment") {
          setPlayerOne(data.player_one_id ?? undefined);
          setPlayerTwo(data.player_two_id ?? undefined);
          setParticipantList((prev) =>
            prev.map((p) => ({
              ...p,
              role:
                p.user_id === data.player_one_id || p.user_id === data.player_two_id ? "player" : "spectator",
            })),
          );
        } else if (data.type === "participant_joined") {
          setParticipantList((prev) => {
            if (prev.some((p) => p.id === data.participant.id)) return prev;
            return [...prev, data.participant];
          });
        }
        setEvents((prev) => [data, ...prev].slice(0, 30));
      } catch {
        // ignore malformed payloads
      }
    };
    return () => ws.close();
  }, [wsUrl]);

  const handleStartRound = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      await api.post(`/rooms/${roomId}/rounds`, {
        round_number: Number(roundNumber),
        duration_minutes: durationMinutes ? Number(durationMinutes) : undefined,
        problem_count: Number(problemCount),
      });
      setSuccess("등록된 문제에서 무작위로 라운드를 시작했습니다.");
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "라운드 시작에 실패했습니다.";
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAssign = async (slot: "player_one" | "player_two") => {
    setAssigningSlot(slot);
    setError(null);
    try {
      await api.post(`/rooms/${roomId}/players`, {
        slot,
        user_id: selectedPlayers[slot] || null,
      });
      setSuccess("플레이어 구성을 업데이트했습니다.");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "플레이어를 지정하지 못했습니다.");
    } finally {
      setAssigningSlot(null);
    }
  };

  const options = [{ label: "비워두기", value: "" }].concat(
    participantList.map((p) => ({
      label: `참가자 ${p.user_id.slice(0, 6)}…`,
      value: p.user_id,
    })),
  );

  const playerLabel = (userId?: string) => {
    if (!userId) return "비어 있음";
    const participant = participantList.find((p) => p.user_id === userId);
    return participant ? `참가자 ${participant.user_id.slice(0, 6)}…` : userId.slice(0, 6);
  };

  const spectators = participantList.filter((p) => p.role !== "player");

  return (
    <div className="card space-y-4">
      <div>
        <p className="text-sm font-semibold text-night-200">참가 코드</p>
        <p className="text-2xl font-bold tracking-widest text-white">{roomCode}</p>
      </div>

      <div className="rounded-lg border border-night-800 bg-night-950/40 p-4 text-sm text-night-200">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-night-100">플레이어 슬롯</p>
          <p className="text-xs text-night-500">방장 전용</p>
        </div>
        {["player_one", "player_two"].map((slot) => {
          const isPlayerOne = slot === "player_one";
          const assigned = isPlayerOne ? playerOne : playerTwo;
          return (
            <div
              key={slot}
              className="mt-3 flex flex-col gap-2 border-b border-night-900 pb-3 text-night-200 last:border-0 last:pb-0"
            >
              <div className="flex items-center justify-between">
                <p className="text-night-300">{isPlayerOne ? "플레이어 1" : "플레이어 2"}</p>
                <p className="font-semibold text-white">{playerLabel(assigned)}</p>
              </div>
              {isHost && (
                <div className="flex flex-col gap-2 sm:flex-row">
                  <select
                    value={selectedPlayers[slot as "player_one" | "player_two"]}
                    onChange={(e) =>
                      setSelectedPlayers((prev) => ({
                        ...prev,
                        [slot]: e.target.value,
                      }))
                    }
                    className="flex-1 rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
                  >
                    {options.map((option) => (
                      <option key={`${slot}-${option.value || "none"}`} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => handleAssign(slot as "player_one" | "player_two")}
                    disabled={assigningSlot === slot}
                    className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700"
                  >
                    지정
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {isHost ? (
        <form
          onSubmit={handleStartRound}
          className="space-y-3 rounded-lg border border-night-800 bg-night-950/50 p-4 text-sm text-night-200"
        >
          <p className="text-night-300">
            방장만 라운드를 시작할 수 있습니다. 목표 숫자는 관리자 페이지에서 등록한 문제 중 무작위로 선택됩니다.
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="space-y-1 text-night-400">
              <span>라운드 번호</span>
              <input
                type="number"
                min={1}
                max={99}
                value={roundNumber}
                onChange={(e) => setRoundNumber(Number(e.target.value))}
                className="w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
                required
              />
            </label>
            <label className="space-y-1 text-night-400">
              <span>진행 시간(분)</span>
              <input
                type="number"
                min={1}
                max={30}
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(Number(e.target.value))}
                className="w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
              />
            </label>
            <label className="space-y-1 text-night-400">
              <span>문제 개수</span>
              <input
                type="number"
                min={1}
                max={10}
                value={problemCount}
                onChange={(e) => setProblemCount(Number(e.target.value))}
                className="w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
              />
            </label>
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          {success && <p className="text-sm text-green-400">{success}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-indigo-600 py-2 font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700"
          >
            {submitting ? "시작 중..." : "라운드 시작"}
          </button>
        </form>
      ) : (
        <div className="rounded-lg border border-night-800 bg-night-950/40 px-4 py-3 text-sm text-night-300">
          방장이 라운드를 시작하면 여기에 실시간 이벤트가 표시됩니다.
        </div>
      )}

      <div className="rounded-lg border border-night-800 bg-night-950/40 p-4 text-sm text-night-200">
        <p className="text-sm font-semibold text-night-200">관전자 {spectators.length}명</p>
        <div className="mt-2 max-h-32 space-y-1 overflow-y-auto text-xs text-night-400">
          {spectators.length === 0 && <p>아직 관전자가 없습니다.</p>}
          {spectators.map((spectator) => (
            <p key={spectator.id}>• {spectator.user_id.slice(0, 8)}…</p>
          ))}
        </div>
      </div>

      <div>
        <p className="text-sm font-semibold text-night-200">실시간 이벤트</p>
        <div className="mt-2 max-h-64 space-y-2 overflow-y-auto rounded-lg border border-night-800 bg-night-950/40 p-3 text-xs text-night-300">
          {events.length === 0 && <p>아직 이벤트가 없습니다.</p>}
          {events.map((event, index) => (
            <p key={`${event.type}-${index}`} className="flex justify-between gap-2">
              <span className="font-semibold text-night-200">{event.type}</span>
              <span className="truncate text-right text-night-400">{JSON.stringify(event)}</span>
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

