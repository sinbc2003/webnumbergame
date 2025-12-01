"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";

interface EventMessage {
  type: string;
  [key: string]: any;
}

interface Props {
  roomId: string;
  roomCode: string;
  hostId: string;
  currentRound: number;
}

const resolveWsBase = () => {
  const { wsBase, apiBase } = getRuntimeConfig();
  if (wsBase) {
    return wsBase;
  }
  const trimmed = apiBase.replace(/\/api$/, "");
  return trimmed.replace(/^http/, "ws");
};

export default function RoomRealtimePanel({ roomId, roomCode, hostId, currentRound }: Props) {
  const wsUrl = useMemo(() => `${resolveWsBase()}/ws/rooms/${roomId}`, [roomId]);
  const [events, setEvents] = useState<EventMessage[]>([]);
  const { user } = useAuth();
  const isHost = user?.id === hostId;

  const [roundNumber, setRoundNumber] = useState(currentRound);
  const [durationMinutes, setDurationMinutes] = useState(3);
  const [problemCount, setProblemCount] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents((prev) => [data, ...prev].slice(0, 20));
      } catch {
        // ignore malformed payloads
      }
    };
    return () => ws.close();
  }, [wsUrl]);

  useEffect(() => {
    setRoundNumber(currentRound);
  }, [currentRound]);

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

  return (
    <div className="card space-y-4">
      <div>
        <p className="text-sm font-semibold text-night-200">참가 코드</p>
        <p className="text-2xl font-bold tracking-widest text-white">{roomCode}</p>
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

