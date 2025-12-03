"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import { describeRoomMode } from "@/lib/roomLabels";
import type { Participant, Room } from "@/types/api";

interface RoomChatMessage {
  id: string;
  userId: string;
  username: string;
  message: string;
  timestamp: string;
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
  const [chatMessages, setChatMessages] = useState<RoomChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [chatErrorMessage, setChatErrorMessage] = useState<string | null>(null);
  const [roundNumber, setRoundNumber] = useState(room.current_round);
  const [durationMinutes, setDurationMinutes] = useState(3);
  const [problemCount, setProblemCount] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [playerOne, setPlayerOne] = useState<string | undefined>(room.player_one_id ?? undefined);
  const [playerTwo, setPlayerTwo] = useState<string | undefined>(room.player_two_id ?? undefined);
  const [participantList, setParticipantList] = useState<Participant[]>(participants);
  const joinStateRef = useRef<{ userId?: string; joined: boolean }>({ joined: false });
  const chatBodyRef = useRef<HTMLDivElement | null>(null);

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
        } else if (data.type === "chat_message") {
          setChatMessages((prev) => {
            const next = [
              ...prev,
              {
                id: data.message_id ?? `${Date.now()}-${prev.length}`,
                userId: data.user_id ?? "unknown",
                username: data.username ?? "익명",
                message: data.message ?? "",
                timestamp: data.timestamp ?? new Date().toISOString(),
              },
            ];
            return next.slice(-50);
          });
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

  const modeLabel = describeRoomMode({ mode: room.mode, team_size: room.team_size });
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

  const formatChatTime = (value: string) => {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
  };

  const canSendChat = Boolean(user);

  useEffect(() => {
    if (!chatBodyRef.current) return;
    chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
  }, [chatMessages]);

  const handleSendChat = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSendChat) {
      setChatErrorMessage("로그인 후 대화를 보낼 수 있습니다.");
      return;
    }
    const trimmed = chatInput.trim();
    if (!trimmed) {
      return;
    }
    setChatSending(true);
    setChatErrorMessage(null);
    try {
      await api.post(`/rooms/${roomId}/chat`, { message: trimmed });
      setChatInput("");
    } catch (err: any) {
      setChatErrorMessage(err?.response?.data?.detail ?? "메시지를 보내지 못했습니다.");
    } finally {
      setChatSending(false);
    }
  };

  return (
    <div className="space-y-5 text-sm text-night-200">
      <div className="rounded-3xl border border-night-800/70 bg-night-950/40 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.4em] text-night-500">ROOM OVERVIEW</p>
            <p className="mt-1 text-2xl font-semibold text-white">{room.name}</p>
            <p className="text-sm text-night-400">방 코드 {room.code}</p>
          </div>
          <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusBadgeClass}`}>{statusLabel}</span>
        </div>
        <div className="mt-4 grid gap-3 text-xs text-night-300 sm:grid-cols-2">
          <div>
            <p className="text-night-500">모드</p>
            <p className="text-lg font-semibold text-white">{modeLabel}</p>
          </div>
          <div>
            <p className="text-night-500">호스트</p>
            <p className="text-lg font-semibold text-white">{hostDisplayName}</p>
          </div>
          <div>
            <p className="text-night-500">지도 이름</p>
            <p className="text-lg font-semibold text-white">{mapName}</p>
          </div>
          <div>
            <p className="text-night-500">참가자</p>
            <p className="text-lg font-semibold text-white">{participantItems.length}명 참가 중</p>
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

      <div className="rounded-3xl border border-night-800/70 bg-night-950/40 p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-white">방 채팅</p>
          <span className="text-xs text-night-500">실시간 대화</span>
        </div>
        <div
          ref={chatBodyRef}
          className="mt-3 max-h-64 space-y-2 overflow-y-auto rounded-2xl border border-night-800/70 bg-night-950/60 p-3 text-xs text-night-100"
        >
          {chatMessages.length === 0 && <p className="text-night-500">아직 메시지가 없습니다.</p>}
          {chatMessages.map((message) => (
            <div key={message.id} className="space-y-1 rounded-xl border border-night-800/60 bg-night-900/40 p-2">
              <div className="flex items-center justify-between text-[11px] text-night-500">
                <span className="font-semibold text-white">{message.username}</span>
                <span>{formatChatTime(message.timestamp)}</span>
              </div>
              <p className="whitespace-pre-wrap break-words text-night-100">{message.message}</p>
            </div>
          ))}
        </div>
        {chatErrorMessage && <p className="mt-2 text-xs text-red-400">{chatErrorMessage}</p>}
        {canSendChat ? (
          <form onSubmit={handleSendChat} className="mt-3 flex gap-2">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              maxLength={500}
              placeholder="메시지를 입력하세요"
              className="flex-1 rounded-xl border border-night-800 bg-night-950 px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={chatSending || !chatInput.trim()}
              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700"
            >
              {chatSending ? "전송 중..." : "전송"}
            </button>
          </form>
        ) : (
          <p className="mt-3 text-xs text-night-500">로그인 후 대화에 참여할 수 있습니다.</p>
        )}
      </div>
    </div>
  );
}

