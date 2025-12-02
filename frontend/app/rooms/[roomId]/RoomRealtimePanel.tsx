"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import type { Participant, Room } from "@/types/api";

interface EventMessage {
  type: string;
  [key: string]: any;
}

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
  const roomCode = room.code;
  const hostId = room.host_id;
  const wsUrl = useMemo(() => `${resolveWsBase()}/ws/rooms/${roomId}`, [roomId]);
  const [events, setEvents] = useState<EventMessage[]>([]);
  const [roundNumber, setRoundNumber] = useState(room.current_round);
  const [durationMinutes, setDurationMinutes] = useState(3);
  const [problemCount, setProblemCount] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [playerOne, setPlayerOne] = useState<string | undefined>(room.player_one_id ?? undefined);
  const [playerTwo, setPlayerTwo] = useState<string | undefined>(room.player_two_id ?? undefined);
  const [participantList, setParticipantList] = useState<Participant[]>(participants);
  const [assigningSlot, setAssigningSlot] = useState<"player_one" | "player_two" | null>(null);
  const [selectedPlayers, setSelectedPlayers] = useState({
    player_one: room.player_one_id ?? "",
    player_two: room.player_two_id ?? "",
  });
  const joinStateRef = useRef<{ userId?: string; joined: boolean }>({ joined: false });

  const { user } = useAuth();
  const router = useRouter();
  const isHost = user?.id === hostId;

  useEffect(() => {
    setRoundNumber(room.current_round);
  }, [room.current_round]);

  useEffect(() => {
    setPlayerOne(room.player_one_id ?? undefined);
    setPlayerTwo(room.player_two_id ?? undefined);
    setSelectedPlayers({
      player_one: room.player_one_id ?? "",
      player_two: room.player_two_id ?? "",
    });
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
    if (!user?.id || !roomCode) return;

    if (participantList.some((p) => p.user_id === user.id)) {
      joinStateRef.current = { userId: user.id, joined: true };
      return;
    }

    if (joinStateRef.current.joined && joinStateRef.current.userId === user.id) {
      return;
    }

    let cancelled = false;

    const attemptJoin = async () => {
      joinStateRef.current = { userId: user.id, joined: true };
      try {
        await api.post("/rooms/join", {
          code: roomCode,
          team_label: null,
        });
        refreshParticipants();
      } catch (err: any) {
        if (cancelled) return;
        joinStateRef.current = { userId: user.id, joined: false };
        setError(err?.response?.data?.detail ?? "방 참가에 실패했습니다.");
      }
    };

    attemptJoin();

    return () => {
      cancelled = true;
    };
  }, [user?.id, roomCode, participantList, refreshParticipants]);

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
        } else if (data.type === "room_closed") {
          setError("방장이 방을 종료했습니다.");
          setTimeout(() => router.push("/rooms"), 1000);
        }
        setEvents((prev) => [data, ...prev].slice(0, 30));
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

  const handleAssign = async (slot: "player_one" | "player_two", userId: string) => {
    setAssigningSlot(slot);
    setError(null);
    try {
      await api.post(`/rooms/${roomId}/players`, {
        slot,
        user_id: userId || null,
      });
      setSuccess("플레이어 구성을 업데이트했습니다.");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "플레이어를 지정하지 못했습니다.");
    } finally {
      setAssigningSlot(null);
    }
  };

  const displayName = (participant?: Participant, fallbackId?: string) => {
    if (participant?.username) return participant.username;
    if (participant?.user_id) return `참가자 ${participant.user_id.slice(0, 6)}…`;
    if (fallbackId) return `참가자 ${fallbackId.slice(0, 6)}…`;
    return "비어 있음";
  };

  const options = [{ label: "비워두기", value: "" }].concat(
    participantList.map((p) => ({
      label: displayName(p),
      value: p.user_id,
    })),
  );

  const playerLabel = (userId?: string) => {
    if (!userId) return "비어 있음";
    const participant = participantList.find((p) => p.user_id === userId);
    return displayName(participant, userId);
  };

  const participantItems = participantList.map((participant) => {
    const baseLabel = participant.user_id === hostId ? "방장" : participant.role === "player" ? "플레이어" : "관전자";
    const slotLabel =
      participant.user_id === playerOne
        ? "플레이어 1"
        : participant.user_id === playerTwo
          ? "플레이어 2"
          : null;
    return {
      ...participant,
      label: displayName(participant),
      roleLabel: slotLabel ?? baseLabel,
      isHost: participant.user_id === hostId,
    };
  });

  const spectatorCount = participantList.filter((p) => p.role !== "player").length;
  const modeLabel = room.round_type === "round1_individual" ? "1라운드 개인전" : "2라운드 팀전";
  const statusLabel =
    room.status === "in_progress" ? "진행 중" : room.status === "completed" ? "종료" : "대기 중";
  const statusBadgeClass =
    room.status === "in_progress"
      ? "border-emerald-500 text-emerald-300"
      : room.status === "completed"
        ? "border-night-600 text-night-200"
        : "border-amber-400 text-amber-200";
  const mapName = room.description?.trim() || "추억의 성큰웨이 #X2";
  const hostDisplayName = displayName(participantList.find((p) => p.user_id === hostId), hostId);

  const describeEvent = (event: EventMessage) => {
    switch (event.type) {
      case "player_assignment":
        return "플레이어 구성이 변경되었습니다.";
      case "participant_joined":
        return `${displayName(event.participant)} 님이 입장했습니다.`;
      case "participant_left":
        return "참가자가 퇴장했습니다.";
      case "round_started":
        return "라운드가 시작되었습니다.";
      case "round_finished":
        return "라운드가 종료되었습니다.";
      case "problem_advanced":
        return "다음 문제로 이동했습니다.";
      default:
        return JSON.stringify(event);
    }
  };

  return (
    <div className="space-y-5 text-sm text-night-200">
      <div className="rounded-3xl border border-night-800/80 bg-[#080f1f]/80 p-5 shadow-[0_25px_50px_rgba(0,0,0,0.55)]">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-[0.4em] text-night-500">참가 코드</p>
            <p className="text-3xl font-black tracking-[0.35em] text-emerald-300">{roomCode}</p>
            <p className="text-xs text-night-500">
              참가자 {participantItems.length}명 · 관전자 {spectatorCount}명
            </p>
          </div>
          <div className="text-right">
            <p className="text-night-500">방 상태</p>
            <span className={`inline-flex rounded-full border px-4 py-1 text-xs font-semibold ${statusBadgeClass}`}>
              {statusLabel}
            </span>
            <p className="mt-1 text-xs text-night-500">현재 라운드 {roundNumber}</p>
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-night-800/70 bg-night-950/40 p-5">
        <div className="grid gap-5">
          <div className="rounded-2xl border border-night-800 bg-[radial-gradient(circle_at_top,#202f55,#060b18)] p-4">
            <div className="grid grid-cols-6 gap-1">
              {Array.from({ length: 24 }).map((_, index) => (
                <div
                  key={`cell-${index}`}
                  className={`h-6 rounded-sm ${
                    index % 5 === 0 ? "bg-emerald-400/60" : index % 7 === 0 ? "bg-red-400/40" : "bg-night-800/80"
                  }`}
                />
              ))}
            </div>
          </div>
          <div className="grid gap-3 text-xs text-night-300 sm:grid-cols-2">
            <div>
              <p className="text-night-500">게임 이름</p>
              <p className="text-lg font-semibold text-white">{room.name}</p>
            </div>
            <div>
              <p className="text-night-500">지도 이름</p>
              <p className="text-lg font-semibold text-white">{mapName}</p>
            </div>
            <div>
              <p className="text-night-500">모드</p>
              <p className="text-lg font-semibold text-white">{modeLabel}</p>
            </div>
            <div>
              <p className="text-night-500">호스트</p>
              <p className="text-lg font-semibold text-white">{hostDisplayName}</p>
            </div>
            <div>
              <p className="text-night-500">진행 시간</p>
              <p className="text-lg font-semibold text-white">{durationMinutes}분</p>
            </div>
            <div>
              <p className="text-night-500">문제 개수</p>
              <p className="text-lg font-semibold text-white">{problemCount}개</p>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-night-800/70 bg-night-950/40 p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-white">플레이어 슬롯</p>
          <div className="flex items-center gap-2 text-xs text-night-500">
            {isHost ? "방장 전용" : "관전자 모드"}
            <button
              type="button"
              onClick={async () => {
                try {
                  await api.delete(`/rooms/${roomId}/participants/me`);
                  router.push("/rooms");
                } catch (err: any) {
                  setError(err?.response?.data?.detail ?? "방 나가기에 실패했습니다.");
                }
              }}
              className="rounded-md border border-night-700 px-3 py-1 text-night-200 transition hover:border-red-500 hover:text-red-300"
            >
              방 나가기
            </button>
          </div>
        </div>
        <div className="mt-4 grid gap-3">
          {["player_one", "player_two"].map((slot) => {
            const isPlayerOne = slot === "player_one";
            const assigned = isPlayerOne ? playerOne : playerTwo;
            return (
              <div
                key={slot}
                className="rounded-2xl border border-night-900/70 bg-night-950/50 p-3 text-night-200"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[12px] uppercase tracking-[0.3em] text-night-500">
                      {isPlayerOne ? "slot a" : "slot b"}
                    </p>
                    <p className="text-xl font-semibold text-white">{playerLabel(assigned)}</p>
                  </div>
                  {isHost && (
                    <div className="text-[10px] text-night-500">
                      {assigningSlot === slot ? "지정 중..." : isPlayerOne ? "플레이어 1" : "플레이어 2"}
                    </div>
                  )}
                </div>
                {isHost && (
                  <div className="mt-3">
                    <select
                      value={selectedPlayers[slot as "player_one" | "player_two"]}
                      disabled={assigningSlot === slot}
                      onChange={(e) => {
                        const value = e.target.value;
                        setSelectedPlayers((prev) => ({
                          ...prev,
                          [slot]: value,
                        }));
                        handleAssign(slot as "player_one" | "player_two", value);
                      }}
                      className="w-full rounded-lg border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none disabled:opacity-60"
                    >
                      {options.map((option) => (
                        <option key={`${slot}-${option.value || "none"}`} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

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

      <div className="rounded-3xl border border-night-800/70 bg-night-950/40 p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-white">참여자 {participantItems.length}명</p>
          <span className="text-xs text-night-500">방장/플레이어/관전자</span>
        </div>
        <div className="mt-4 space-y-2 text-xs">
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

      {events.length > 0 && (
        <div className="rounded-3xl border border-night-800/70 bg-black/60 p-4 font-mono text-xs text-emerald-200">
          <p className="font-sans text-sm font-semibold text-night-200">실시간 로그</p>
          <div className="mt-3 max-h-64 space-y-1 overflow-y-auto pr-1">
            {events.map((event, index) => (
              <p key={`${event.type}-${index}`} className="flex items-center gap-2">
                <span className="font-sans text-[10px] text-amber-300">[{event.type}]</span>
                <span>{describeEvent(event)}</span>
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

