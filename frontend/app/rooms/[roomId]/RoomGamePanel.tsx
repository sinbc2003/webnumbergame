"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import type { ActiveMatch, Participant, RoundType, Room } from "@/types/api";

type BoardSlot = "playerOne" | "playerTwo";
type PlayerAssignmentSlot = "player_one" | "player_two";

type RoomEventPayload = {
  type?: string;
  player_one_id?: string | null;
  player_two_id?: string | null;
  participant?: Participant;
  user_id?: string;
  expression?: string;
  reason?: string;
  winner_user_id?: string | null;
  winner_submission_id?: string | null;
  submission?: {
    expression: string;
    score: number;
    result_value?: number | null;
    user_id?: string | null;
    distance?: number | null;
    cost?: number;
    is_optimal?: boolean;
    submitted_at?: string;
    team_label?: string | null;
    match_id?: string;
  };
  winner_submission?: {
    id: string;
    match_id: string;
    user_id?: string | null;
    team_label?: string | null;
    expression: string;
    result_value?: number | null;
    cost?: number;
    distance?: number | null;
    is_optimal?: boolean;
    score: number;
    submitted_at: string;
  };
};

interface HistoryEntry {
  expression: string;
  score: number;
  value: number | null;
  timestamp: string;
}

interface BoardState {
  expression: string;
  history: HistoryEntry[];
}

interface TeamMemberState {
  name: string;
  allocation: number;
  remaining: number;
  input: string;
}

type RoundOutcome = {
  reason: string;
  winnerId?: string | null;
  distance?: number | null;
  score?: number | null;
};

const allowedTokens = new Set(["1", "+", "*", "(", ")"]);
const sanitizeExpression = (value: string) =>
  value
    .split("")
    .filter((char) => allowedTokens.has(char))
    .join("");
const computeExpressionValue = (value: string): number | null => {
  const sanitized = sanitizeExpression(value).trim();
  if (!sanitized) return null;
  if (/[\+\*\(]$/.test(sanitized)) return null;
  try {
    const result = Function(`"use strict"; return (${sanitized});`)();
    if (typeof result === "number" && Number.isFinite(result)) {
      return result;
    }
    return null;
  } catch {
    return null;
  }
};
const countOperators = (expression: string): number =>
  expression.split("").filter((char) => char === "+" || char === "*").length;
const INPUT_WARNING = "사용 가능한 기호는 1, +, *, (, ) 만 허용됩니다.";
const CRITICAL_COUNTDOWN_THRESHOLD = 5;
const TEAM_MEMBER_COUNT = 4;
const TEAM_DEFAULT_ALLOCATION = [8, 8, 8, 8];
const TEAM_MEMBER_LABELS = ["1번 주자", "2번 주자", "3번 주자", "4번 주자"];
const TEAM_ALLOWED_SYMBOLS: Array<{ symbol: string; label: string }> = [
  { symbol: "1", label: "1" },
  { symbol: "(", label: "(" },
  { symbol: ")", label: ")" },
  { symbol: "+", label: "+" },
  { symbol: "*", label: "*" },
];
const TEAM_COST_TABLE: Record<string, number> = {
  "1": 1,
  "+": 2,
  "*": 3,
  "(": 1,
  ")": 1,
};

const createDefaultTeamMembers = (): TeamMemberState[] =>
  TEAM_MEMBER_LABELS.map((name, index) => {
    const allocation = TEAM_DEFAULT_ALLOCATION[index] ?? TEAM_DEFAULT_ALLOCATION[0];
    return {
      name,
      allocation,
      remaining: allocation,
      input: "",
    };
  });

interface Props {
  room: Room;
  participants: Participant[];
  onPlayerFocusChange?: (isFocused: boolean) => void;
}

const resolveWsBase = () => {
  const { wsBase, apiBase } = getRuntimeConfig();
  if (wsBase) return wsBase;
  const trimmed = apiBase.replace(/\/api$/, "");
  return trimmed.replace(/^http/, "ws");
};

const createBoardState = (): BoardState => ({ expression: "", history: [] });

export default function RoomGamePanel({ room, participants, onPlayerFocusChange }: Props) {
  const roomId = room.id;
  const roundType: RoundType = room.round_type;
  const initialPlayerOne = room.player_one_id ?? undefined;
  const initialPlayerTwo = room.player_two_id ?? undefined;
  const { user } = useAuth();
  const router = useRouter();
  const isTeamRound = roundType === "round2_team";
  const [playerOne, setPlayerOne] = useState<string | undefined>(initialPlayerOne);
  const [playerTwo, setPlayerTwo] = useState<string | undefined>(initialPlayerTwo);
  const [boards, setBoards] = useState<{ playerOne: BoardState; playerTwo: BoardState }>({
    playerOne: createBoardState(),
    playerTwo: createBoardState(),
  });
  const [pendingInput, setPendingInput] = useState<{ slot: BoardSlot; value: string } | null>(null);
  const [submittingSlot, setSubmittingSlot] = useState<BoardSlot | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [participantState, setParticipantState] = useState<Participant[]>(participants);
  const [inputWarnings, setInputWarnings] = useState<Record<BoardSlot, string | null>>({
    playerOne: null,
    playerTwo: null,
  });
  const [roundOutcome, setRoundOutcome] = useState<RoundOutcome | null>(null);
  const [preCountdown, setPreCountdown] = useState<number | null>(null);
  const [leaving, setLeaving] = useState(false);
  const [assigningSlot, setAssigningSlot] = useState<PlayerAssignmentSlot | null>(null);
  const countdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const userInteractedRef = useRef(false);
  const tickRef = useRef<number | null>(null);
  const [initialRemaining, setInitialRemaining] = useState<number | null>(null);
  const [activeMatchId, setActiveMatchId] = useState<string | null>(null);
  const [slotSelections, setSlotSelections] = useState<{ player_one: string; player_two: string }>({
    player_one: room.player_one_id ?? "",
    player_two: room.player_two_id ?? "",
  });

  const playerIdsRef = useRef<{ playerOne: string | undefined; playerTwo: string | undefined }>({
    playerOne: initialPlayerOne,
    playerTwo: initialPlayerTwo,
  });

  useEffect(() => {
    const next = room.player_one_id ?? undefined;
    playerIdsRef.current.playerOne = next;
    setPlayerOne(next);
  }, [room.player_one_id]);

  useEffect(() => {
    const next = room.player_two_id ?? undefined;
    playerIdsRef.current.playerTwo = next;
    setPlayerTwo(next);
  }, [room.player_two_id]);

  useEffect(() => {
    setSlotSelections({
      player_one: playerOne ?? "",
      player_two: playerTwo ?? "",
    });
  }, [playerOne, playerTwo]);

  useEffect(() => {
    setParticipantState(participants);
  }, [participants]);

  useEffect(() => {
    return () => {
      if (countdownTimerRef.current) {
        clearInterval(countdownTimerRef.current);
        countdownTimerRef.current = null;
      }
    };
  }, []);

  const fetcher = async (url: string) => {
    const { data } = await api.get<ActiveMatch | null>(url);
    return data;
  };

  const { data, mutate } = useSWR(user ? `/rooms/${roomId}/active-match` : null, fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  const activeMatch = data ?? null;
  const hasActiveMatch = Boolean(activeMatch);

  const wsUrl = useMemo(() => `${resolveWsBase()}/ws/rooms/${roomId}`, [roomId]);
  const isHost = user?.id === room.host_id;

  useEffect(() => {
    if (!data?.match_id) {
      setActiveMatchId(null);
      setInitialRemaining(null);
      return;
    }
    setActiveMatchId((prev) => {
      if (prev === data.match_id) {
        return prev;
      }
      setInitialRemaining(null);
      tickRef.current = null;
      return data.match_id;
    });
  }, [data?.match_id]);

  const slotFromUserId = (userId?: string | null): BoardSlot | null => {
    if (!userId) return null;
    if (userId === playerIdsRef.current.playerOne) return "playerOne";
    if (userId === playerIdsRef.current.playerTwo) return "playerTwo";
    return null;
  };

  const ensureAudioContext = useCallback(() => {
    if (typeof window === "undefined") return null;
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return null;
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContextClass();
    }
    if (audioContextRef.current.state === "suspended") {
      audioContextRef.current.resume();
    }
    return audioContextRef.current;
  }, []);

  const armAudio = useCallback(() => {
    if (userInteractedRef.current) return;
    if (ensureAudioContext()) {
      userInteractedRef.current = true;
    }
  }, [ensureAudioContext]);

  const playTone = useCallback(
    (type: "success" | "error" | "tick") => {
      const ctx = ensureAudioContext();
      if (!ctx) return;

      const config =
        type === "success"
          ? { freq: 920, duration: 0.25, wave: "sine", gain: 0.25 }
          : type === "error"
            ? { freq: 220, duration: 0.35, wave: "sawtooth", gain: 0.35 }
            : { freq: 660, duration: 0.12, wave: "square", gain: 0.18 };

      const oscillator = ctx.createOscillator();
      const gain = ctx.createGain();
      oscillator.frequency.value = config.freq;
      oscillator.type = config.wave as OscillatorType;
      gain.gain.value = config.gain;
      oscillator.connect(gain);
      gain.connect(ctx.destination);

      const now = ctx.currentTime;
      oscillator.start(now);
      oscillator.stop(now + config.duration);
    },
    [ensureAudioContext],
  );

  const triggerPreCountdown = useCallback(() => {
    if (countdownTimerRef.current) {
      clearInterval(countdownTimerRef.current);
    }
    setPreCountdown(5);
    countdownTimerRef.current = setInterval(() => {
      setPreCountdown((prev) => {
        if (prev === null) {
          return prev;
        }
        if (prev <= 0) {
          if (countdownTimerRef.current) {
            clearInterval(countdownTimerRef.current);
            countdownTimerRef.current = null;
          }
          return null;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

  const handleExpressionChange = useCallback(
    (slot: BoardSlot, rawValue: string) => {
      armAudio();
      const sanitized = sanitizeExpression(rawValue);
      setBoards((prev) => ({
        ...prev,
        [slot]: { ...prev[slot], expression: sanitized },
      }));
      setPendingInput({ slot, value: sanitized });
      setInputWarnings((prev) => ({
        ...prev,
        [slot]: sanitized !== rawValue ? INPUT_WARNING : null,
      }));
      if (sanitized !== rawValue) {
        playTone("error");
      }
    },
    [armAudio, playTone],
  );

  const participantLabel = useCallback(
    (userId?: string) => {
      if (!userId) return "대기 중";
      const participant = participantState.find((p) => p.user_id === userId);
      if (participant?.username) return participant.username;
      if (participant?.user_id) return `참가자 ${participant.user_id.slice(0, 6)}…`;
      return userId.slice(0, 6);
    },
    [participantState],
  );

  const roundLabel = roundType === "round1_individual" ? "1라운드 개인전" : "2라운드 팀전";
  const participantQueue = useMemo(() => {
    return participantState
      .map((participant, index) => ({ participant, index }))
      .sort((a, b) => {
        const orderA = a.participant.order_index ?? Number.POSITIVE_INFINITY;
        const orderB = b.participant.order_index ?? Number.POSITIVE_INFINITY;
        if (orderA !== orderB) return orderA - orderB;
        return a.index - b.index;
      })
      .map((entry) => entry.participant);
  }, [participantState]);

  const spectatorQueue = useMemo(
    () => participantQueue.filter((participant) => participant.role !== "player"),
    [participantQueue],
  );

  const participantOptions = useMemo(
    () =>
      [{ label: "비워두기", value: "" }].concat(
        participantQueue.map((participant) => ({
          label: participant.username ?? (participant.user_id ? `참가자 ${participant.user_id.slice(0, 6)}…` : "이름 없음"),
          value: participant.user_id,
        })),
      ),
    [participantQueue],
  );

  const playerQueuePreview = useMemo(() => participantQueue.slice(0, 4), [participantQueue]);
  const participantOrder = useCallback(
    (userId?: string | null) => {
      if (!userId) return null;
      const index = participantQueue.findIndex((participant) => participant.user_id === userId);
      return index === -1 ? null : index + 1;
    },
    [participantQueue],
  );

  const handleLeaveRoom = useCallback(async () => {
    if (leaving) return;

    const confirmed =
      typeof window === "undefined" ? true : window.confirm("방을 나가시겠습니까? 진행 중이면 기권 처리됩니다.");
    if (!confirmed) {
      return;
    }

    setStatusError(null);
    setStatusMessage(null);

    if (!user) {
      router.push("/rooms");
      return;
    }

    try {
      setLeaving(true);
      await api.delete(`/rooms/${roomId}/participants/me`);
      router.push("/rooms");
    } catch (err: any) {
      if (err?.response?.status === 404) {
        router.push("/rooms");
      } else {
        setStatusError(err?.response?.data?.detail ?? "방 나가기 중 오류가 발생했습니다.");
      }
    } finally {
      setLeaving(false);
    }
  }, [leaving, roomId, router, user]);

  const renderLeaveButton = () => (
    <button
      type="button"
      onClick={handleLeaveRoom}
      disabled={leaving}
      className="rounded-md border border-red-500/60 px-3 py-1 text-xs font-semibold text-red-100 transition hover:border-red-400 hover:text-white disabled:opacity-60"
    >
      {leaving ? "나가는 중..." : "방 나가기"}
    </button>
  );

  const handleAssignSlot = useCallback(
    async (slot: PlayerAssignmentSlot, userId: string) => {
      if (!isHost) return;
      setAssigningSlot(slot);
      setStatusError(null);
      setSlotSelections((prev) => ({
        ...prev,
        [slot]: userId,
      }));
      try {
        await api.post(`/rooms/${roomId}/players`, {
          slot,
          user_id: userId || null,
        });
        setStatusMessage("플레이어 구성을 업데이트했습니다.");
        mutate();
      } catch (err: any) {
        setStatusError(err?.response?.data?.detail ?? "플레이어 지정에 실패했습니다.");
        setSlotSelections({
          player_one: playerOne ?? "",
          player_two: playerTwo ?? "",
        });
      } finally {
        setAssigningSlot(null);
      }
    },
    [isHost, mutate, playerOne, playerTwo, roomId],
  );

  useEffect(() => {
    if (!user) return;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as RoomEventPayload;
        switch (payload.type) {
          case "player_assignment": {
            const nextOne = payload.player_one_id ?? undefined;
            const nextTwo = payload.player_two_id ?? undefined;
            const prevOne = playerIdsRef.current.playerOne;
            const prevTwo = playerIdsRef.current.playerTwo;
            playerIdsRef.current = { playerOne: nextOne, playerTwo: nextTwo };
            setPlayerOne(nextOne);
            setPlayerTwo(nextTwo);
            setParticipantState((prev) =>
              prev.map((p) => ({
                ...p,
                role: p.user_id === nextOne || p.user_id === nextTwo ? "player" : "spectator",
              })),
            );
            setBoards((prev) => ({
              playerOne: nextOne && nextOne === prevOne ? prev.playerOne : createBoardState(),
              playerTwo: nextTwo && nextTwo === prevTwo ? prev.playerTwo : createBoardState(),
            }));
            mutate();
            break;
          }
          case "participant_joined": {
            if (!payload.participant) break;
            setParticipantState((prev) => {
              if (prev.some((p) => p.id === payload.participant!.id)) {
                return prev;
              }
              return [...prev, payload.participant!];
            });
            break;
          }
          case "participant_left": {
            if (!payload.user_id) break;
            setParticipantState((prev) => prev.filter((p) => p.user_id !== payload.user_id));
            if (playerIdsRef.current.playerOne === payload.user_id) {
              playerIdsRef.current.playerOne = undefined;
              setPlayerOne(undefined);
            }
            if (playerIdsRef.current.playerTwo === payload.user_id) {
              playerIdsRef.current.playerTwo = undefined;
              setPlayerTwo(undefined);
            }
            break;
          }
          case "input_update": {
            const slot = slotFromUserId(payload.user_id);
            if (!slot) break;
            setBoards((prev) => ({
              ...prev,
              [slot]: { ...prev[slot], expression: payload.expression ?? "" },
            }));
            break;
          }
          case "submission_received": {
            if (!payload.submission) break;
            const slot = slotFromUserId(payload.submission.user_id);
            if (slot) {
              setBoards((prev) => {
                const nextHistory: HistoryEntry[] = [
                  {
                    expression: payload.submission!.expression,
                    score: payload.submission!.score,
                    value: payload.submission!.result_value ?? null,
                    timestamp: new Date().toISOString(),
                  },
                  ...prev[slot].history,
                ].slice(0, 10);
                return {
                  ...prev,
                  [slot]: { ...prev[slot], history: nextHistory },
                };
              });
            }
            if (payload.submission.user_id && payload.submission.user_id === user?.id) {
              if (payload.submission.distance === 0) {
                setStatusMessage("정답입니다! 다음 문제를 기다려 주세요.");
                setStatusError(null);
                playTone("success");
              } else if (typeof payload.submission.distance === "number") {
                setStatusError(`목표까지 ${payload.submission.distance}만큼 차이납니다.`);
                playTone("error");
              }
            }
            break;
          }
          case "round_started": {
            setBoards({
              playerOne: createBoardState(),
              playerTwo: createBoardState(),
            });
            setStatusMessage("새 라운드가 시작되었습니다. 카운트다운 후 입력이 열립니다.");
            setStatusError(null);
            setRoundOutcome(null);
            setInitialRemaining(null);
            tickRef.current = null;
            triggerPreCountdown();
            mutate();
            break;
          }
          case "problem_advanced": {
            setStatusMessage("다음 문제로 이동했습니다.");
            mutate();
            break;
          }
          case "round_finished": {
            const reason = payload.reason ?? "optimal";
            const winnerSubmission = payload.winner_submission;
            const winnerId =
              payload.winner_user_id ?? winnerSubmission?.user_id ?? payload.winner_submission_id ?? null;
            setRoundOutcome({
              reason,
              winnerId,
              distance: winnerSubmission?.distance ?? null,
              score: winnerSubmission?.score ?? null,
            });
            setPreCountdown(null);
            setInitialRemaining(null);
            tickRef.current = null;
            setBoards({
              playerOne: createBoardState(),
              playerTwo: createBoardState(),
            });
            if (winnerId) {
              const winnerLabel = participantLabel(winnerId);
              if (winnerId === user?.id) {
                const message =
                  reason === "timeout"
                    ? "시간 종료! 근사 정답으로 승리했습니다."
                    : reason === "forfeit"
                      ? "상대가 나가 기권승으로 처리되었습니다."
                      : "정답으로 승리했습니다!";
                setStatusMessage(message);
                setStatusError(null);
                playTone("success");
              } else {
                const message =
                  reason === "timeout"
                    ? `${winnerLabel} 님이 더 가까운 해답을 제출했습니다.`
                    : reason === "forfeit"
                      ? `${winnerLabel} 님이 남아 있어 승리했습니다.`
                      : `${winnerLabel} 님이 정답을 찾아 라운드가 종료되었습니다.`;
                setStatusError(message);
                playTone("error");
              }
            } else if (reason === "timeout") {
              setStatusMessage("시간 종료! 제출된 식이 없어 무승부입니다.");
              setStatusError(null);
            } else if (reason === "forfeit") {
              setStatusMessage("상대가 나가 라운드가 종료되었습니다.");
              setStatusError(null);
            }
            mutate();
            break;
          }
          case "room_closed": {
            const closingReason = payload.reason ?? "closed";
            if (closingReason === "forfeit") {
              setStatusMessage("상대가 방을 떠나 경기가 종료되었습니다.");
              setStatusError(null);
        } else if (closingReason === "host_left" || closingReason === "host_left_forfeit" || closingReason === "host_disconnected") {
          setStatusError("방장이 퇴장했습니다.");
            } else {
              setStatusError("방장이 방을 종료했습니다.");
            }
            setTimeout(() => router.push("/rooms"), 1000);
            break;
          }
          default:
            break;
        }
      } catch {
        // ignore malformed event
      }
    };
    return () => ws.close();
  }, [user, wsUrl, mutate, router, participantLabel, playTone, triggerPreCountdown]);

  useEffect(() => {
    if (remaining === null) {
      tickRef.current = null;
      return;
    }
    setInitialRemaining((prev) => {
      if (prev === null || remaining > prev) {
        return remaining;
      }
      return prev;
    });
    if (remaining <= CRITICAL_COUNTDOWN_THRESHOLD) {
      if (tickRef.current !== remaining) {
        playTone("tick");
        tickRef.current = remaining;
      }
    } else {
      tickRef.current = null;
    }
  }, [remaining, playTone]);

  const parseDeadline = useCallback((value?: string | null) => {
    if (!value) return null;
    const normalized = /z$/i.test(value) ? value : `${value}Z`;
    const timestamp = Date.parse(normalized);
    return Number.isNaN(timestamp) ? null : timestamp;
  }, []);

  useEffect(() => {
    const deadline = parseDeadline(data?.deadline);
    if (!deadline) {
      setRemaining(null);
      return;
    }
    const update = () => {
      const diff = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
      setRemaining(diff);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [data?.deadline, parseDeadline]);

  const mySlot: BoardSlot | null = useMemo(() => {
    if (!user?.id) return null;
    if (playerOne && user.id === playerOne) return "playerOne";
    if (playerTwo && user.id === playerTwo) return "playerTwo";
    return null;
  }, [user?.id, playerOne, playerTwo]);

  useEffect(() => {
    onPlayerFocusChange?.(hasActiveMatch && Boolean(mySlot));
  }, [hasActiveMatch, mySlot, onPlayerFocusChange]);

  useEffect(() => {
    if (!pendingInput || pendingInput.slot !== mySlot) return;
    if (!pendingInput.value.trim()) return;
    const timeout = setTimeout(() => {
      api.post(`/rooms/${roomId}/inputs`, { expression: pendingInput.value }).catch(() => {});
    }, 250);
    return () => clearTimeout(timeout);
  }, [pendingInput, mySlot, roomId]);

  const submitExpression = async (slot: BoardSlot) => {
    armAudio();
    const value = boards[slot].expression.trim();
    if (!value) {
      setStatusError("식을 입력해 주세요.");
      return;
    }
    setSubmittingSlot(slot);
    setStatusError(null);
    setStatusMessage(null);
    try {
      await api.post(`/rooms/${roomId}/submit`, {
        expression: value,
        mode: roundType,
        team_label: null,
      });
      setBoards((prev) => ({
        ...prev,
        [slot]: { ...prev[slot], expression: "" },
      }));
      setStatusMessage("제출했습니다! 결과를 기다려 주세요.");
      setInputWarnings((prev) => ({
        ...prev,
        [slot]: null,
      }));
    } catch (err: any) {
      setStatusError(err?.response?.data?.detail ?? "제출 중 오류가 발생했습니다.");
      playTone("error");
    } finally {
      setSubmittingSlot(null);
    }
  };

  const formatRemaining = () => {
    if (remaining === null) return "-";
    const minutes = Math.floor(remaining / 60)
      .toString()
      .padStart(2, "0");
    const seconds = Math.floor(remaining % 60)
      .toString()
      .padStart(2, "0");
    return `${minutes}:${seconds}`;
  };

  const isPlayerView = hasActiveMatch && Boolean(mySlot);
  const visibleSlots: BoardSlot[] = isPlayerView && mySlot ? [mySlot] : (["playerOne", "playerTwo"] as BoardSlot[]);
  const myBoard = mySlot ? boards[mySlot] : null;
  const myExpression = myBoard?.expression ?? "";
  const myHistory = myBoard?.history ?? [];
  const expressionValue = useMemo(() => computeExpressionValue(myExpression), [myExpression]);
  const operatorCount = useMemo(() => countOperators(myExpression), [myExpression]);
  const expressionValueDisplay = myExpression.trim() ? expressionValue ?? "-" : "-";
  const operatorCountDisplay = myExpression.trim() ? operatorCount : "-";
  const formattedRemaining = formatRemaining();
  const countdownPercent =
    initialRemaining && remaining !== null && initialRemaining > 0
      ? Math.max(0, Math.min(1, remaining / initialRemaining))
      : 0;
  const isCountdownCritical = remaining !== null && remaining <= CRITICAL_COUNTDOWN_THRESHOLD;
  const problemIndicators = activeMatch
    ? Array.from({ length: activeMatch.total_problems }, (_, index) => {
        if (index < activeMatch.current_index) return "done";
        if (index === activeMatch.current_index) return "current";
        return "hidden";
      })
    : [];
  const lobbyShellClass =
    "relative space-y-6 rounded-[30px] border border-night-800/80 bg-[rgba(5,10,20,0.85)] p-6 text-night-100 shadow-[0_25px_70px_rgba(0,0,0,0.6)]";

  const containerClass = isPlayerView
    ? "fixed inset-0 z-40 mx-auto flex w-full max-w-6xl flex-col bg-[#050a15] px-3 py-4 text-white sm:px-5 sm:py-5"
    : hasActiveMatch
      ? "fixed inset-0 z-40 overflow-y-auto bg-[#050a15]/95 p-6 space-y-4"
      : lobbyShellClass;

  if (isPlayerView && activeMatch) {
    return (
      <div className={`${containerClass} relative`}>
        {preCountdown !== null && <CountdownOverlay value={preCountdown} />}
        <div className="flex h-full flex-col gap-4">
          <div className="rounded-[32px] border-2 border-indigo-500/50 bg-night-950/70 px-5 py-4 text-night-100 shadow-[0_30px_80px_rgba(0,0,0,0.65)]">
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <p className="text-[11px] uppercase tracking-[0.55em] text-indigo-200/70">{roundLabel}</p>
                <div className="mt-2 flex items-end gap-3">
                  <span className="text-base text-night-400">문제 :</span>
                  <span className="text-5xl font-black text-white sm:text-6xl">{activeMatch.target_number}</span>
                </div>
                <p className="mt-1 text-xs text-night-500">
                  {activeMatch.current_index + 1} / {activeMatch.total_problems} 문제 진행 중
                </p>
              </div>
              <div className="ml-auto flex flex-wrap items-center justify-end gap-3">
                <div className="min-w-[130px] rounded-2xl border border-indigo-400/50 bg-night-900/70 px-4 py-3 text-right">
                  <p className="text-[11px] tracking-[0.45em] text-indigo-200">값</p>
                  <p className="text-3xl font-black text-white">{expressionValueDisplay}</p>
                </div>
                <div className="min-w-[150px] rounded-2xl border border-amber-400/50 bg-night-900/70 px-4 py-3 text-right">
                  <p className="text-[11px] tracking-[0.35em] text-amber-200">연산기호개수</p>
                  <p className="text-3xl font-black text-amber-200">{operatorCountDisplay}</p>
                </div>
                <div className="hidden sm:block">{renderLeaveButton()}</div>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-night-400 sm:gap-4">
              <p className="font-semibold text-amber-200">
                최적 코스트 {activeMatch.optimal_cost} 이하로 정답을 만들면 즉시 승리!
              </p>
              <div className="flex flex-wrap gap-1 text-[10px] uppercase tracking-[0.4em] text-night-500">
                {problemIndicators.map((state, index) => (
                  <span
                    key={`indicator-${index}`}
                    className={`h-1.5 w-6 rounded-full ${state === "current" ? "bg-amber-400" : state === "done" ? "bg-emerald-400" : "bg-night-700"}`}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <div className="space-y-1 text-emerald-300">
              {statusMessage && <p>• {statusMessage}</p>}
            </div>
            <div className="space-y-1 text-red-400">{statusError && <p>• {statusError}</p>}</div>
            <div className="sm:hidden">{renderLeaveButton()}</div>
          </div>

          <div className="flex flex-1 flex-col">
            {visibleSlots.map((slot) => {
              const assignedUser = slot === "playerOne" ? playerOne : playerTwo;
              const isMine = mySlot === slot;
              if (isTeamRound && isMine) {
                return (
                  <TeamBoard
                    key={slot}
                    matchId={activeMatch.match_id}
                    expression={boards[slot].expression}
                    history={boards[slot].history}
                    onExpressionChange={(value) => handleExpressionChange(slot, value)}
                    onSubmit={() => submitExpression(slot)}
                    submitting={submittingSlot === slot}
                    disabled={!activeMatch || !assignedUser}
                    playTone={playTone}
                    armAudio={armAudio}
                  />
                );
              }
              return (
                <PlayerPanel
                  key={slot}
                  title={slot === "playerOne" ? "플레이어 1" : "플레이어 2"}
                  userLabel={participantLabel(assignedUser)}
                  expression={boards[slot].expression}
                  history={boards[slot].history}
                  onExpressionChange={isMine ? (value) => handleExpressionChange(slot, value) : undefined}
                  onSubmit={isMine ? () => submitExpression(slot) : undefined}
                  onFocus={isMine ? armAudio : undefined}
                  disabled={!activeMatch || !assignedUser}
                  isMine={isMine}
                  submitting={submittingSlot === slot}
                  placeholder={slot === "playerOne" ? "예: (1+1)*1" : "예: 1+(1*1)"}
                  warningMessage={inputWarnings[slot]}
                  focusLayout
                />
              );
            })}
          </div>

          <div className="rounded-3xl border border-night-800/80 bg-night-950/50 px-6 py-4 text-night-300">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs text-night-500">문제 진행도</p>
                <p className="text-lg font-semibold text-white">
                  {activeMatch.current_index + 1} / {activeMatch.total_problems}
                </p>
              </div>
              <div className="flex flex-1 justify-center">
                <div
                  className={`flex h-32 w-32 items-center justify-center rounded-full border-4 font-mono text-4xl sm:text-5xl ${
                    isCountdownCritical ? "border-red-500 text-red-300" : "border-indigo-400 text-indigo-200"
                  } bg-night-900/60`}
                >
                  {formattedRemaining}
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-night-500">남은 문제</p>
                <p className="text-lg font-semibold text-white">
                  {Math.max(0, activeMatch.total_problems - activeMatch.current_index - 1)}개
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!hasActiveMatch) {
    const spectatorCount = participantState.filter((p) => p.role !== "player").length;
    const readyCount = participantState.filter((p) => p.is_ready).length;
    const hostLabel = participantLabel(room.host_id);
    return (
      <div className={lobbyShellClass}>
        {preCountdown !== null && <CountdownOverlay value={preCountdown} />}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-night-800/60 pb-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.45em] text-night-500">ROOM LOBBY</p>
            <h2 className="text-3xl font-black text-white">{room.name}</h2>
            <p className="text-sm text-night-400">
              {roundLabel} · 방 코드 <span className="font-mono text-emerald-300">{room.code}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-amber-400/60 px-4 py-1 text-xs font-semibold tracking-[0.45em] text-amber-200">
              대기 중
            </span>
            {renderLeaveButton()}
          </div>
        </div>
        {!user && <p className="text-sm text-night-500">로그인 후 이용해 주세요.</p>}
        <div className="mt-6 grid gap-6 lg:grid-cols-[2.5fr,1.5fr]">
          <div className="space-y-4">
            <div className="rounded-2xl border border-night-800/70 bg-night-950/30 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.4em] text-night-500">플레이어 슬롯</p>
                  <p className="text-2xl font-semibold text-white">입장 순으로 자동 배치</p>
                </div>
                <span className="rounded-full border border-indigo-500/50 px-3 py-1 text-[11px] tracking-[0.35em] text-indigo-200">
                  {isHost ? "HOST CONTROL" : "관전자 모드"}
                </span>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {(["player_one", "player_two"] as PlayerAssignmentSlot[]).map((slot) => {
                  const boardSlot: BoardSlot = slot === "player_one" ? "playerOne" : "playerTwo";
                  const assignedUser = boardSlot === "playerOne" ? playerOne : playerTwo;
                  const assignedParticipant = participantState.find((participant) => participant.user_id === assignedUser);
                  const order = participantOrder(assignedUser);
                  return (
                    <div key={slot} className="rounded-2xl border border-night-800/70 bg-night-950/60 p-4 text-sm text-night-200">
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <p className="text-[11px] uppercase tracking-[0.3em] text-night-500">
                            {slot === "player_one" ? "SLOT A" : "SLOT B"}
                          </p>
                          <p className="text-xl font-semibold text-white">{participantLabel(assignedUser)}</p>
                        </div>
                        {assignedParticipant?.is_ready && (
                          <span className="rounded-full border border-emerald-400 px-2 py-0.5 text-[10px] text-emerald-200">READY</span>
                        )}
                      </div>
                      <p className="mt-1 text-[11px] text-night-500">
                        {order ? `입장 #${order}` : "아직 지정되지 않았습니다."}
                      </p>
                      {isHost ? (
                        <select
                          value={slotSelections[slot]}
                          disabled={assigningSlot === slot}
                          onChange={(event) => handleAssignSlot(slot, event.target.value)}
                          className="mt-3 w-full rounded-lg border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none disabled:opacity-60"
                        >
                          {participantOptions.map((option) => (
                            <option key={`${slot}-${option.value || "empty"}`} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <p className="mt-3 rounded-lg border border-night-800/60 bg-night-900/50 px-3 py-2 text-xs text-night-400">
                          방장이 순서를 조정할 수 있습니다.
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
              <div className="mt-5 rounded-xl border border-night-800/60 bg-night-900/40 p-3">
                <p className="text-[11px] uppercase tracking-[0.4em] text-night-500">입장 대기열</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {playerQueuePreview.length === 0 && <span className="text-xs text-night-500">아직 입장한 사용자가 없습니다.</span>}
                  {playerQueuePreview.map((participant) => (
                    <span
                      key={`queue-${participant.id}`}
                      className="inline-flex items-center gap-1 rounded-full border border-night-700 px-3 py-1 text-xs text-night-200"
                    >
                      <span className="text-[10px] text-night-500">#{participantOrder(participant.user_id) ?? "-"}</span>
                      {participant.username ?? participant.user_id.slice(0, 6)}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-night-800/70 bg-night-900/40 p-4 text-night-200">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-white">관전자 슬롯</p>
                <span className="text-xs text-night-500">{spectatorQueue.length}명</span>
              </div>
              <div className="mt-4 grid max-h-[360px] gap-3 overflow-y-auto pr-1 sm:grid-cols-2">
                {spectatorQueue.length === 0 && (
                  <p className="rounded-xl border border-night-800/60 bg-night-950/40 p-3 text-xs text-night-500">관전자가 없습니다.</p>
                )}
                {spectatorQueue.map((spectator) => (
                  <div
                    key={`spectator-${spectator.id}`}
                    className="rounded-xl border border-night-800/70 bg-night-950/50 p-3 text-xs text-night-300"
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-white">{spectator.username ?? spectator.user_id.slice(0, 6)}</p>
                      <span className="text-[10px] text-night-500">#{participantOrder(spectator.user_id) ?? "-"}</span>
                    </div>
                    <p className="text-[11px] text-night-500">
                      {spectator.user_id === room.host_id ? "방장" : spectator.role === "player" ? "플레이어" : "관전자"}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-night-800/70 bg-night-900/40 p-4 text-xs text-night-300">
              <div className="grid gap-3 text-sm text-night-300 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <p className="text-night-500">참가자</p>
                  <p className="text-lg font-semibold text-white">{participantState.length}명</p>
                </div>
                <div>
                  <p className="text-night-500">관전자</p>
                  <p className="text-lg font-semibold text-white">{spectatorCount}명</p>
                </div>
                <div>
                  <p className="text-night-500">준비 완료</p>
                  <p className="text-lg font-semibold text-emerald-300">{readyCount}명</p>
                </div>
                <div>
                  <p className="text-night-500">최대 인원</p>
                  <p className="text-lg font-semibold text-white">{room.max_players}명</p>
                </div>
                <div>
                  <p className="text-night-500">호스트</p>
                  <p className="text-lg font-semibold text-white">{hostLabel}</p>
                </div>
                <div>
                  <p className="text-night-500">현재 라운드</p>
                  <p className="text-lg font-semibold text-white">{room.current_round}</p>
                </div>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="rounded-2xl border border-night-800/70 bg-night-950/30 p-4 text-sm">
              <p className="text-xs uppercase tracking-[0.35em] text-night-500">상태 콘솔</p>
              <div className="mt-3 space-y-2 text-night-200">
                {statusMessage ? (
                  <p className="text-emerald-300">• {statusMessage}</p>
                ) : (
                  <p className="text-night-500">방장이 라운드를 시작하면 스타크래프트식 카운트다운이 표시됩니다.</p>
                )}
                {statusError && <p className="text-red-300">• {statusError}</p>}
              </div>
            </div>
            {roundOutcome && (
              <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
                <p className="font-semibold">
                  {roundOutcome.reason === "timeout"
                    ? "시간 종료 결과"
                    : roundOutcome.reason === "forfeit"
                      ? "기권 처리"
                      : "직전 라운드 결과"}
                </p>
                <p className="mt-1">
                  승자: {roundOutcome.winnerId ? participantLabel(roundOutcome.winnerId ?? undefined) : "무승부"}
                </p>
                {typeof roundOutcome.distance === "number" && (
                  <p className="text-xs text-amber-200/70">목표와의 차이 {roundOutcome.distance}</p>
                )}
              </div>
            )}
            <div className="rounded-2xl border border-night-800/80 bg-night-950/30 p-4 text-xs text-night-400">
              <p className="font-semibold text-night-100">라운드 개시 안내</p>
              <p className="mt-2">
                방장이 <span className="text-emerald-300">라운드 시작</span>을 누르면 5 → 0 카운트다운이 표시되고,
                0이 되면 즉시 전장 화면으로 전환됩니다.
              </p>
              <p className="mt-2">카운트다운 동안 플레이어는 식 입력창이 잠긴 상태로 준비 시간을 가집니다.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${containerClass} relative`}>
      {preCountdown !== null && <CountdownOverlay value={preCountdown} />}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-white">실시간 경기</h2>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-emerald-500 px-3 py-0.5 text-xs text-emerald-300">진행 중</span>
          {renderLeaveButton()}
        </div>
      </div>
      {!user && <p className="text-sm text-night-400">로그인 후 이용할 수 있습니다.</p>}

      {statusMessage && <p className="text-sm text-green-400">{statusMessage}</p>}
      {statusError && <p className="text-sm text-red-400">{statusError}</p>}

      {roundOutcome && (
        <div className="rounded-lg border border-night-800 bg-night-900/40 p-4 text-sm text-night-200">
          <p className="font-semibold text-night-100">
            {roundOutcome.reason === "timeout"
              ? "시간 종료 결과"
              : roundOutcome.reason === "forfeit"
                ? "상대 기권 승리"
                : "라운드 결과"}
          </p>
          <p className="mt-1 text-night-300">
            승자: {roundOutcome.winnerId ? participantLabel(roundOutcome.winnerId ?? undefined) : "무승부"}
          </p>
          {typeof roundOutcome.distance === "number" && (
            <p className="text-xs text-night-500">목표와의 차이: {roundOutcome.distance}</p>
          )}
        </div>
      )}

      <div className="grid gap-3 rounded-lg border border-night-800/60 bg-night-950/40 p-4 text-sm text-night-200 sm:grid-cols-2">
        <div>
          <p className="text-night-500">현재 문제</p>
          <p className="text-2xl font-bold text-white">{activeMatch?.target_number ?? "-"}</p>
        </div>
        <div>
          <p className="text-night-500">남은 시간</p>
          <p className={`text-3xl font-bold ${isCountdownCritical ? "text-red-400" : "text-indigo-300"}`}>
            {formattedRemaining}
          </p>
          <div className="mt-2 h-2 w-full rounded-full bg-night-900">
            <div
              className={`h-full rounded-full ${isCountdownCritical ? "bg-red-500" : "bg-indigo-500"}`}
              style={{ width: `${countdownPercent * 100}%` }}
            />
          </div>
        </div>
        <div>
          <p className="text-night-500">최적 코스트</p>
          <p className="text-xl font-semibold text-night-100">{activeMatch?.optimal_cost ?? "-"}</p>
        </div>
        <div>
          <p className="text-night-500">문제 진행도</p>
          <p className="text-xl font-semibold text-night-100">
            {activeMatch ? `${activeMatch.current_index + 1} / ${activeMatch.total_problems}` : "-"}
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {visibleSlots.map((slot) => {
          const isMine = mySlot === slot;
          const assignedUser = slot === "playerOne" ? playerOne : playerTwo;
          return (
            <PlayerPanel
              key={slot}
              title={slot === "playerOne" ? "플레이어 1" : "플레이어 2"}
              userLabel={participantLabel(assignedUser)}
              expression={boards[slot].expression}
              history={boards[slot].history}
              onExpressionChange={isMine ? (value) => handleExpressionChange(slot, value) : undefined}
              onSubmit={isMine ? () => submitExpression(slot) : undefined}
              onFocus={isMine ? armAudio : undefined}
              disabled={!activeMatch || !assignedUser}
              isMine={isMine}
              submitting={submittingSlot === slot}
              placeholder={slot === "playerOne" ? "예: (1+1)*1" : "예: 1+(1*1)"}
              warningMessage={inputWarnings[slot]}
              focusLayout={Boolean(mySlot)}
            />
          );
        })}
      </div>
    </div>
  );
}

interface TeamBoardProps {
  matchId: string;
  expression: string;
  history: HistoryEntry[];
  onExpressionChange: (value: string) => void;
  onSubmit: () => void;
  submitting: boolean;
  disabled: boolean;
  playTone: (type: "success" | "error" | "tick") => void;
  armAudio: () => void;
}

function TeamBoard({
  matchId,
  expression,
  history,
  onExpressionChange,
  onSubmit,
  submitting,
  disabled,
  playTone,
  armAudio,
}: TeamBoardProps) {
  const [members, setMembers] = useState<TeamMemberState[]>(() => createDefaultTeamMembers());
  const [currentIndex, setCurrentIndex] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const combined = useMemo(() => members.map((member) => member.input).join(""), [members]);
  const activeMember = members[currentIndex];
  const canEditAllocation = combined.length === 0;

  useEffect(() => {
    setMembers(createDefaultTeamMembers());
    setCurrentIndex(0);
    setMessage(null);
    setError(null);
    onExpressionChange("");
  }, [matchId, onExpressionChange]);

  useEffect(() => {
    if (combined !== expression) {
      onExpressionChange(combined);
    }
  }, [combined, expression, onExpressionChange]);

  const updateMember = (index: number, updater: (member: TeamMemberState) => TeamMemberState) => {
    setMembers((prev) => prev.map((member, idx) => (idx === index ? updater(member) : member)));
  };

  const handleAllocationChange = (index: number, value: number) => {
    if (!canEditAllocation) return;
    const sanitized = Math.max(0, Number.isFinite(value) ? value : 0);
    updateMember(index, (member) => ({
      ...member,
      allocation: sanitized,
      remaining: sanitized,
      input: "",
    }));
  };

  const handleCharInput = (symbol: string) => {
    if (disabled) return;
    armAudio();
    setError(null);
    const cost = TEAM_COST_TABLE[symbol] ?? 0;
    if (activeMember.remaining < cost) {
      setError("남은 코인이 부족합니다.");
      playTone("error");
      return;
    }
    updateMember(currentIndex, (member) => ({
      ...member,
      input: member.input + symbol,
      remaining: member.remaining - cost,
    }));
  };

  const handleDelete = () => {
    if (disabled) return;
    armAudio();
    if (!activeMember.input) {
      return;
    }
    const nextInput = activeMember.input.slice(0, -1);
    const removed = activeMember.input.slice(-1);
    const refund = TEAM_COST_TABLE[removed] ?? 0;
    updateMember(currentIndex, (member) => ({
      ...member,
      input: nextInput,
      remaining: member.remaining + refund,
    }));
  };

  const handleNext = () => {
    if (currentIndex >= TEAM_MEMBER_COUNT - 1) {
      setMessage("모든 주자의 입력이 완료되었습니다. 필요하면 이전 주자를 선택해 조정하세요.");
      return;
    }
    setCurrentIndex((prev) => prev + 1);
    setMessage(`${TEAM_MEMBER_LABELS[currentIndex + 1]} 차례입니다.`);
  };

  const handlePrev = () => {
    if (currentIndex === 0) return;
    setCurrentIndex((prev) => prev - 1);
    setMessage(`${TEAM_MEMBER_LABELS[currentIndex - 1]} 차례로 돌아갔습니다.`);
  };

  const handleReset = () => {
    setMembers(createDefaultTeamMembers());
    setCurrentIndex(0);
    setMessage(null);
    setError(null);
  };

  const handleSubmit = () => {
    if (!combined.trim()) {
      setError("식을 먼저 작성해 주세요.");
      return;
    }
    onSubmit();
  };

  return (
    <div className="rounded-2xl border-2 border-night-800 bg-night-950/50 p-6 text-night-100 shadow-lg">
      <div className="grid gap-3 sm:grid-cols-4">
        {members.map((member, index) => (
          <div key={member.name} className="rounded-lg border border-night-800 bg-night-900/40 p-3 text-xs">
            <p className="font-semibold text-white">{member.name}</p>
            <div className="mt-1 flex items-center gap-2">
              <label className="flex-1 text-night-500">
                할당
                <input
                  type="number"
                  min={0}
                  value={member.allocation}
                  disabled={!canEditAllocation}
                  onChange={(e) => handleAllocationChange(index, Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-night-800 bg-night-950 px-2 py-1 text-white focus:border-indigo-400 focus:outline-none"
                />
              </label>
              <p className="w-16 text-right text-night-400">
                남음 <span className="font-semibold text-white">{member.remaining}</span>
              </p>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 rounded-xl border border-night-800 bg-night-900/50 p-4 font-mono text-xl text-white">
        <p className="text-xs text-night-500">현재 식</p>
        <p className="mt-2 min-h-[64px] break-words text-2xl">{expression || "입력을 시작하세요."}</p>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-[2fr,1fr]">
        <div>
          <div className="flex items-center justify-between text-sm text-night-400">
            <p>
              현재 차례: <span className="font-semibold text-white">{activeMember.name}</span>
            </p>
            <div className="space-x-2">
              <button
                type="button"
                onClick={handlePrev}
                disabled={currentIndex === 0}
                className="rounded-md border border-night-700 px-3 py-1 text-xs text-night-200 disabled:opacity-40"
              >
                이전
              </button>
              <button
                type="button"
                onClick={handleNext}
                className="rounded-md border border-night-700 px-3 py-1 text-xs text-night-200 disabled:opacity-40"
              >
                다음
              </button>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-5 gap-2">
            {TEAM_ALLOWED_SYMBOLS.map(({ symbol, label }) => (
              <button
                key={symbol}
                type="button"
                onClick={() => handleCharInput(symbol)}
                className="rounded-lg border border-night-700 bg-night-900/70 py-3 text-lg font-semibold text-white hover:border-indigo-500"
              >
                {label}
                <span className="block text-[10px] text-night-500">-{TEAM_COST_TABLE[symbol]} coin</span>
              </button>
            ))}
            <button
              type="button"
              onClick={handleDelete}
              className="rounded-lg border border-night-700 bg-night-900/70 py-3 text-sm font-semibold text-white hover:border-red-500"
            >
              ← 지우기
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="rounded-lg border border-night-700 bg-night-900/70 py-3 text-sm font-semibold text-white hover:border-amber-500"
            >
              전체 초기화
            </button>
          </div>
          {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
          {message && <p className="mt-2 text-xs text-night-400">{message}</p>}
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={disabled || submitting || !expression.trim()}
              className="flex-1 rounded-lg bg-indigo-600 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700"
            >
              {submitting ? "제출 중..." : "최종 제출"}
            </button>
          </div>
        </div>
        {history.length > 0 && (
          <div className="rounded-xl border border-night-800 bg-night-900/40 p-3 text-xs text-night-300">
            <p className="text-sm font-semibold text-night-100">최근 기록</p>
            <div className="mt-3 max-h-64 space-y-2 overflow-y-auto pr-1">
              {history.map((entry, index) => (
                <div key={`${entry.timestamp}-${index}`} className="rounded border border-night-800/70 bg-night-900/40 p-2">
                  <p className="font-semibold text-white">{entry.expression}</p>
                  <p className="text-[11px] text-night-400">
                    점수 {entry.score} | 값 {entry.value ?? "-"}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface PlayerPanelProps {
  title: string;
  userLabel: string;
  expression: string;
  history: HistoryEntry[];
  onExpressionChange?: (value: string) => void;
  onSubmit?: () => void;
  onFocus?: () => void;
  disabled: boolean;
  isMine: boolean;
  submitting: boolean;
  placeholder?: string;
  warningMessage?: string | null;
  focusLayout?: boolean;
}

function PlayerPanel({
  title,
  userLabel,
  expression,
  history,
  onExpressionChange,
  onSubmit,
  onFocus,
  disabled,
  isMine,
  submitting,
  placeholder,
  warningMessage,
  focusLayout,
}: PlayerPanelProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit?.();
      return;
    }
    if (event.key === " " || event.key === "Tab") {
      event.preventDefault();
    }
  };

  if (focusLayout) {
    const bestEntry =
      history.length === 0
        ? null
        : history.reduce<HistoryEntry | null>((best, entry) => {
            if (!best || entry.score > best.score) {
              return entry;
            }
            return best;
          }, null);
    return (
      <div className="flex flex-1 flex-col gap-6 lg:flex-row">
        <div className="flex-1 rounded-[32px] border-2 border-indigo-600/40 bg-night-950/60 p-6 text-night-100 shadow-[0_25px_90px_rgba(0,0,0,0.6)]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-indigo-200/80">{title}</p>
              <p className="text-3xl font-semibold text-white">{userLabel}</p>
            </div>
            {isMine && (
              <span className="rounded-full border border-indigo-400/70 px-4 py-1 text-xs font-semibold text-indigo-200">
                내 화면
              </span>
            )}
          </div>
          <textarea
            value={expression}
            onChange={(e) => onExpressionChange?.(e.target.value)}
            onFocus={onFocus}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={!isMine || disabled || submitting}
            spellCheck={false}
            autoComplete="off"
            className="mt-6 min-h-[160px] w-full flex-1 rounded-2xl border-2 border-indigo-500/40 bg-night-900 px-4 py-4 font-mono text-2xl text-white focus:border-indigo-300 focus:outline-none"
          />
          {warningMessage && <p className="mt-2 text-sm text-amber-200/90">{warningMessage}</p>}
          {isMine && onSubmit && (
            <button
              type="button"
              onClick={onSubmit}
              disabled={disabled || submitting || !expression.trim()}
              className="mt-4 h-14 w-full rounded-2xl bg-indigo-600 text-lg font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700"
            >
              {submitting ? "제출 중..." : "제출하기"}
            </button>
          )}
          {isMine && <p className="mt-2 text-sm text-night-400">Enter 키를 누르면 즉시 제출됩니다.</p>}
        </div>
        <div className="w-full lg:w-80">
          <div className="rounded-3xl border border-night-800/70 bg-night-950/40 p-4">
            <p className="text-sm font-semibold text-white">최근 히스토리</p>
            <div className="mt-3 max-h-[420px] space-y-3 overflow-y-auto pr-2">
              {history.length === 0 && <p className="text-sm text-night-500">아직 제출 기록이 없습니다.</p>}
              {history.map((entry, index) => (
                <div
                  key={`${entry.timestamp}-${index}`}
                  className="rounded-2xl border border-night-800/70 bg-night-900/40 p-3 text-sm text-night-200"
                >
                  <p className="font-semibold text-white">{entry.expression}</p>
                  <p className="text-xs text-night-400">
                    점수 {entry.score} | 값 {entry.value ?? "-"}
                  </p>
                </div>
              ))}
            </div>
          </div>
          {bestEntry && (
            <div className="mt-3 rounded-3xl border border-amber-400/40 bg-amber-500/10 p-4 text-sm text-amber-100">
              <p className="font-semibold">🏆 최고 기록</p>
              <p className="mt-1 font-mono text-lg text-white">{bestEntry.expression}</p>
              <p className="text-xs text-amber-200/70">
                점수 {bestEntry.score} | 값 {bestEntry.value ?? "-"}
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-night-800 bg-night-950/30 p-4 text-sm text-night-200">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-night-400">{title}</p>
          <p className="text-lg font-semibold text-white">{userLabel}</p>
        </div>
        {isMine && <span className="text-xs text-indigo-400">내 화면</span>}
      </div>

      <textarea
        value={expression}
        onChange={(e) => onExpressionChange?.(e.target.value)}
        onFocus={onFocus}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={!isMine || disabled || submitting}
        spellCheck={false}
        autoComplete="off"
        className="mt-3 h-24 w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
      />

      {warningMessage && <p className="mt-1 text-xs text-amber-200">{warningMessage}</p>}

      {isMine && onSubmit && (
        <button
          type="button"
          onClick={onSubmit}
          disabled={disabled || submitting || !expression.trim()}
          className="mt-2 w-full rounded-md bg-indigo-600 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700"
        >
          {submitting ? "제출 중..." : "제출하기"}
        </button>
      )}

      {isMine && <p className="mt-1 text-xs text-night-500">Enter 키를 누르면 즉시 제출됩니다.</p>}

      <div className="mt-4">
        <p className="text-xs font-semibold text-night-300">최근 기록</p>
        <div className="mt-2 max-h-36 space-y-2 overflow-y-auto text-xs text-night-400">
          {history.length === 0 && <p>아직 제출 기록이 없습니다.</p>}
          {history.map((entry, index) => (
            <div key={`${entry.timestamp}-${index}`} className="rounded border border-night-800/70 bg-night-900/40 p-2">
              <p className="font-semibold text-white">{entry.expression}</p>
              <p className="text-[11px] text-night-400">
                점수 {entry.score} | 값 {entry.value ?? "-"}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CountdownOverlay({ value }: { value: number }) {
  return (
    <div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-2 rounded-full border-2 border-amber-400/70 bg-black/70 px-10 py-8 text-center">
        <p className="text-xs uppercase tracking-[0.6em] text-amber-200/80">COUNTDOWN</p>
        <p className="text-6xl font-black text-amber-300 drop-shadow-[0_0_25px_rgba(247,223,173,0.65)]">{value}</p>
        <p className="text-[12px] text-amber-100/80">라운드 준비 중</p>
      </div>
    </div>
  );
}

