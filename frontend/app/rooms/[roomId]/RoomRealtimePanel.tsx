"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import { RELAY_TEAM_A, RELAY_TEAM_B } from "@/lib/relay";
import type { Participant, Room } from "@/types/api";

interface Props {
  room: Room;
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

export default function RoomRealtimePanel({ room, participants }: Props) {
  const roomId = room.id;
  const hostId = room.host_id;
  const wsUrl = useMemo(() => `${resolveWsBase()}/ws/rooms/${roomId}`, [roomId]);
  const [roundNumber, setRoundNumber] = useState(room.current_round);
  const [durationMinutes, setDurationMinutes] = useState(3);
  const [problemCount, setProblemCount] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [playerOne, setPlayerOne] = useState<string | undefined>(room.player_one_id ?? undefined);
  const [playerTwo, setPlayerTwo] = useState<string | undefined>(room.player_two_id ?? undefined);
  const [participantList, setParticipantList] = useState<Participant[]>(participants);

  const { user } = useAuth();
  const router = useRouter();
  const isHost = user?.id === hostId;

  useEffect(() => {
    setRoundNumber(room.current_round);
  }, [room.current_round]);

  useEffect(() => {
    setPlayerOne(room.player_one_id ?? undefined);
    setPlayerTwo(room.player_two_id ?? undefined);
  }, [room.player_one_id, room.player_two_id]);

  useEffect(() => {
    setParticipantList(participants);
  }, [participants]);

  const refreshParticipants = useCallback(async () => {
    try {
      const { data } = await api.get<Participant[]>(`/rooms/${roomId}/participants`);
      setParticipantList(data);
    } catch {
      // ignore errors
    }
  }, [roomId]);

  useEffect(() => {
    refreshParticipants();
  }, [refreshParticipants]);

  useEffect(() => {
    const interval = setInterval(refreshParticipants, 5000);
    return () => clearInterval(interval);
  }, [refreshParticipants]);

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
              role: p.user_id === data.player_one_id || p.user_id === data.player_two_id ? "player" : "spectator",
            })),
          );
        } else if (data.type === "participant_joined") {
          setParticipantList((prev) => {
            if (!data.participant) return prev;
            if (prev.some((p) => p.id === data.participant.id)) return prev;
            return [...prev, data.participant];
          });
          refreshParticipants();
        } else if (data.type === "participant_left") {
          setParticipantList((prev) => prev.filter((p) => p.user_id !== data.user_id));
          refreshParticipants();
        } else if (data.type === "relay_roster") {
          const slotMap = new Map<string, { team_label: string; order_index: number }>();
          const applySlots = (
            slots: Array<{ slot_index?: number; user_id?: string | null }>,
            teamLabel: typeof RELAY_TEAM_A | typeof RELAY_TEAM_B,
          ) => {
            slots?.forEach((slot) => {
              if (!slot) return;
              const slotIndex = typeof slot.slot_index === "number" ? slot.slot_index : null;
              const userId = slot.user_id ?? undefined;
              if (!userId || slotIndex === null) return;
              slotMap.set(userId, { team_label: teamLabel, order_index: slotIndex });
            });
          };
          applySlots(data.team_a ?? [], RELAY_TEAM_A);
          applySlots(data.team_b ?? [], RELAY_TEAM_B);
          setParticipantList((prev) =>
            prev.map((participant) => {
              const info = slotMap.get(participant.user_id);
              if (!info) {
                if (!participant.team_label && participant.order_index == null) {
                  return participant;
                }
                return { ...participant, team_label: null, order_index: null };
              }
              if (
                participant.team_label === info.team_label &&
                participant.order_index === info.order_index
              ) {
                return participant;
              }
              return { ...participant, team_label: info.team_label, order_index: info.order_index };
            }),
          );
        } else if (data.type === "room_closed") {
          setError("방장이 방을 종료했습니다.");
          setTimeout(() => router.push("/rooms"), 1000);
        }
      } catch {
        // ignore malformed payloads
      }
    };
    return () => ws.close();
  }, [wsUrl, refreshParticipants, router]);

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

  const displayName = (participant?: Participant, fallbackId?: string) => {
    if (participant?.username) return participant.username;
    if (participant?.user_id) return `참가자 ${participant.user_id.slice(0, 6)}…`;
    if (fallbackId) return `참가자 ${fallbackId.slice(0, 6)}…`;
    return "비어 있음";
  };

  const participantItems = participantList.map((participant) => {
    const baseLabel = participant.user_id === hostId ? "방장" : participant.role === "player" ? "플레이어" : "관전자";
    const relayLabel =
      participant.team_label === RELAY_TEAM_A && typeof participant.order_index === "number"
        ? `릴레이 A 팀 · ${participant.order_index + 1}번`
        : participant.team_label === RELAY_TEAM_B && typeof participant.order_index === "number"
          ? `릴레이 B 팀 · ${participant.order_index + 1}번`
          : null;
    const slotLabel =
      participant.user_id === playerOne
        ? "플레이어 1"
        : participant.user_id === playerTwo
          ? "플레이어 2"
          : relayLabel;
    return {
      ...participant,
      label: displayName(participant),
      roleLabel: slotLabel ?? baseLabel,
      isHost: participant.user_id === hostId,
    };
  });

  return (
    <div className="space-y-5 text-sm text-night-200">
      {isHost ? (
        <form
          onSubmit={handleStartRound}
          className="rounded-3xl border border-night-800/70 bg-night-950/45 p-5 text-night-200"
        >
          <p className="text-xs text-night-400">
            방장이 라운드를 시작하면 스타크래프트식 5초 카운트다운이 표시된 뒤 경기가 전체 화면으로 전환됩니다.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
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
          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
          {success && <p className="mt-1 text-sm text-emerald-300">{success}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="mt-4 w-full rounded-lg bg-indigo-600 py-2 font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700"
          >
            {submitting ? "시작 중..." : "라운드 시작"}
          </button>
        </form>
      ) : (
        <div className="rounded-3xl border border-night-800/70 bg-night-950/30 p-5 text-night-300">
          방장이 &quot;라운드 시작&quot;을 누르면 5 → 0 카운트다운이 재생된 뒤 경기 화면이 표시됩니다.
        </div>
      )}

      <div className="rounded-3xl border border-night-800/70 bg-night-950/40 p-5 flex h-[420px] lg:h-[60vh] flex-col overflow-hidden">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-white">참여자 {participantItems.length}명</p>
          <span className="text-xs text-night-500">방장/플레이어/관전자</span>
        </div>
        <div className="mt-4 flex-1 space-y-2 overflow-y-auto pr-1 text-xs">
          {participantItems.length === 0 && <p className="text-night-500">아직 참가자가 없습니다.</p>}
          {participantItems.map((participant) => (
            <div
              key={participant.id}
              className="flex items-center justify-between rounded-xl border border-night-900/70 bg-night-950/50 px-3 py-2"
            >
              <div>
                <p className="font-semibold text-white">{participant.label}</p>
                <p className="text-[11px] text-night-500">{participant.roleLabel}</p>
              </div>
              <div className="flex items-center gap-2">
                {participant.isHost && (
                  <span className="rounded-full border border-amber-400 px-2 py-0.5 text-[10px] text-amber-300">
                    HOST
                  </span>
                )}
                {participant.role === "player" && !participant.isHost && (
                  <span className="rounded-full border border-emerald-500/60 px-2 py-0.5 text-[10px] text-emerald-200">
                    PLAYER
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

