"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import type { ActiveMatch, Participant, RoundType } from "@/types/api";

type BoardSlot = "playerOne" | "playerTwo";

type RoomEventPayload = {
  type?: string;
  player_one_id?: string | null;
  player_two_id?: string | null;
  participant?: Participant;
  user_id?: string;
  expression?: string;
  reason?: string;
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
const INPUT_WARNING = "사용 가능한 기호는 1, +, *, (, ) 만 허용됩니다.";
const CRITICAL_COUNTDOWN_THRESHOLD = 5;

interface Props {
  roomId: string;
  roundType: RoundType;
  playerOneId?: string;
  playerTwoId?: string;
  participants: Participant[];
}

const resolveWsBase = () => {
  const { wsBase, apiBase } = getRuntimeConfig();
  if (wsBase) return wsBase;
  const trimmed = apiBase.replace(/\/api$/, "");
  return trimmed.replace(/^http/, "ws");
};

const createBoardState = (): BoardState => ({ expression: "", history: [] });

export default function RoomGamePanel({
  roomId,
  roundType,
  playerOneId,
  playerTwoId,
  participants,
}: Props) {
  const { user } = useAuth();
  const router = useRouter();
  const [playerOne, setPlayerOne] = useState<string | undefined>(playerOneId ?? undefined);
  const [playerTwo, setPlayerTwo] = useState<string | undefined>(playerTwoId ?? undefined);
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
  const countdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const userInteractedRef = useRef(false);
  const tickRef = useRef<number | null>(null);
  const [initialRemaining, setInitialRemaining] = useState<number | null>(null);
  const [activeMatchId, setActiveMatchId] = useState<string | null>(null);

  const playerIdsRef = useRef<{ playerOne: string | undefined; playerTwo: string | undefined }>({
    playerOne: playerOneId ?? undefined,
    playerTwo: playerTwoId ?? undefined,
  });

  useEffect(() => {
    const next = playerOneId ?? undefined;
    playerIdsRef.current.playerOne = next;
    setPlayerOne(next);
  }, [playerOneId]);

  useEffect(() => {
    const next = playerTwoId ?? undefined;
    playerIdsRef.current.playerTwo = next;
    setPlayerTwo(next);
  }, [playerTwoId]);

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

  const { data, mutate, isLoading } = useSWR(user ? `/rooms/${roomId}/active-match` : null, fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  const wsUrl = useMemo(() => `${resolveWsBase()}/ws/rooms/${roomId}`, [roomId]);

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
    setPreCountdown(3);
    countdownTimerRef.current = setInterval(() => {
      setPreCountdown((prev) => {
        if (prev === null || prev <= 1) {
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
            const winnerId = winnerSubmission?.user_id ?? payload.winner_submission_id ?? null;
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
                setStatusMessage(reason === "timeout" ? "시간 종료! 근사 정답으로 승리했습니다." : "정답으로 승리했습니다!");
                setStatusError(null);
                playTone("success");
              } else {
                setStatusError(
                  reason === "timeout"
                    ? `${winnerLabel} 님이 더 가까운 해답을 제출했습니다.`
                    : `${winnerLabel} 님이 정답을 찾아 라운드가 종료되었습니다.`,
                );
                playTone("error");
              }
            } else {
              setStatusMessage("시간 종료! 제출된 식이 없어 무승부입니다.");
              setStatusError(null);
            }
            mutate();
            break;
          }
          case "room_closed": {
            setStatusError("방장이 방을 종료했습니다.");
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

  useEffect(() => {
    if (!data?.deadline) {
      setRemaining(null);
      return;
    }
    const deadline = new Date(data.deadline).getTime();
    const update = () => {
      const diff = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
      setRemaining(diff);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [data?.deadline]);

  const mySlot: BoardSlot | null =
    user?.id && user.id === playerIdsRef.current.playerOne
      ? "playerOne"
      : user?.id === playerIdsRef.current.playerTwo
        ? "playerTwo"
        : null;

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

  const activeMatch = data ?? null;
  const hasActiveMatch = Boolean(activeMatch);
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
  const containerClass = hasActiveMatch
    ? "fixed inset-0 z-40 overflow-y-auto bg-night-950/95 p-6 space-y-4"
    : "card space-y-4";

  return (
    <div className={containerClass}>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">실시간 경기</h2>
        <span
          className={`rounded-full border px-3 py-0.5 text-xs ${
            hasActiveMatch ? "border-emerald-500 text-emerald-300" : "border-night-700 text-night-400"
          }`}
        >
          {hasActiveMatch ? "진행 중" : "대기 중"}
        </span>
      </div>
      {!user && <p className="text-sm text-night-400">로그인 후 이용할 수 있습니다.</p>}

      {!hasActiveMatch && !isLoading && (
        <div className="rounded-lg border border-night-800 bg-night-950/40 p-5 text-sm text-night-300">
          <p className="font-semibold text-night-100">아직 라운드가 시작되지 않았습니다.</p>
          <p className="mt-2 text-night-400">
            방장이 두 명의 플레이어를 지정하고 라운드를 시작하면 게임 화면이 전체에 표시됩니다.
          </p>
        </div>
      )}

      {statusMessage && <p className="text-sm text-green-400">{statusMessage}</p>}
      {statusError && <p className="text-sm text-red-400">{statusError}</p>}

      {roundOutcome && (
        <div className="rounded-lg border border-night-800 bg-night-900/40 p-4 text-sm text-night-200">
          <p className="font-semibold text-night-100">
            {roundOutcome.reason === "timeout" ? "시간 종료 결과" : "라운드 결과"}
          </p>
          <p className="mt-1 text-night-300">
            승자: {roundOutcome.winnerId ? participantLabel(roundOutcome.winnerId ?? undefined) : "무승부"}
          </p>
          {typeof roundOutcome.distance === "number" && (
            <p className="text-xs text-night-500">목표와의 차이: {roundOutcome.distance}</p>
          )}
        </div>
      )}

      {hasActiveMatch && (
        <>
          {preCountdown !== null && (
            <div className="rounded-xl border border-indigo-500/70 bg-night-900/60 p-4 text-center text-white">
              <p className="text-sm text-night-400">라운드 시작까지</p>
              <p className="text-4xl font-bold text-indigo-200">{preCountdown}</p>
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

          <div className="space-y-2 rounded-lg border border-night-800/60 bg-night-950/30 p-4 text-sm text-night-300">
            <p className="font-semibold text-night-200">문제 진행 상황</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {problemIndicators.length === 0 && <p className="text-night-500">등록된 문제가 없습니다.</p>}
              {problemIndicators.map((state, index) => (
                <span
                  key={`indicator-${index}`}
                  className={`rounded-full px-3 py-1 text-xs ${
                    state === "done"
                      ? "bg-emerald-600/20 text-emerald-300"
                      : state === "current"
                        ? "bg-indigo-600/20 text-indigo-200"
                        : "bg-night-800 text-night-500"
                  }`}
                >
                  #{index + 1} · {state === "done" ? "완료" : state === "current" ? "진행 중" : "비공개"}
                </span>
              ))}
            </div>
            <p className="text-xs text-night-500">다음 문제는 공개되지 않으며, 현재 문제만 확인할 수 있습니다.</p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {(["playerOne", "playerTwo"] as BoardSlot[]).map((slot) => {
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
                  placeholder={slot === "playerOne" ? "예: (1+2)*3" : "예: (1+3)*2"}
                  warningMessage={inputWarnings[slot]}
                />
              );
            })}
          </div>
        </>
      )}
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
}: PlayerPanelProps) {
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
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSubmit?.();
            return;
          }
          if (event.key === " " || event.key === "Tab") {
            event.preventDefault();
          }
        }}
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

      {isMine && (
        <p className="mt-1 text-xs text-night-500">Enter 키를 누르면 즉시 제출됩니다.</p>
      )}

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

