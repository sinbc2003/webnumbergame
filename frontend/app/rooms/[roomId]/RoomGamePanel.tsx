"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import type { ActiveMatch, Participant, RoundType } from "@/types/api";

type BoardSlot = "playerOne" | "playerTwo";

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

  const fetcher = async (url: string) => {
    const { data } = await api.get<ActiveMatch | null>(url);
    return data;
  };

  const { data, mutate, isLoading } = useSWR(user ? `/rooms/${roomId}/active-match` : null, fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  const wsUrl = useMemo(() => `${resolveWsBase()}/ws/rooms/${roomId}`, [roomId]);

  const slotFromUserId = (userId?: string | null): BoardSlot | null => {
    if (!userId) return null;
    if (userId === playerIdsRef.current.playerOne) return "playerOne";
    if (userId === playerIdsRef.current.playerTwo) return "playerTwo";
    return null;
  };

  useEffect(() => {
    if (!user) return;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string };
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
            setParticipantState((prev) => {
              if (prev.some((p) => p.id === payload.participant.id)) return prev;
              return [...prev, payload.participant];
            });
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
            const slot = slotFromUserId(payload.submission?.user_id);
            if (!slot) break;
            setBoards((prev) => {
              const nextHistory: HistoryEntry[] = [
                {
                  expression: payload.submission.expression,
                  score: payload.submission.score,
                  value: payload.submission.result_value ?? null,
                  timestamp: new Date().toISOString(),
                },
                ...prev[slot].history,
              ].slice(0, 10);
              return {
                ...prev,
                [slot]: { ...prev[slot], history: nextHistory },
              };
            });
            break;
          }
          case "round_started": {
            setBoards({
              playerOne: createBoardState(),
              playerTwo: createBoardState(),
            });
            setStatusMessage("새 라운드가 시작되었습니다.");
            mutate();
            break;
          }
          case "problem_advanced": {
            setStatusMessage("다음 문제로 이동했습니다.");
            mutate();
            break;
          }
          case "round_finished": {
            setStatusMessage("라운드가 종료되었습니다.");
            mutate();
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
  }, [user, wsUrl, mutate]);

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
    } catch (err: any) {
      setStatusError(err?.response?.data?.detail ?? "제출 중 오류가 발생했습니다.");
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

  const participantLabel = (userId?: string) => {
    if (!userId) return "대기 중";
    const participant = participantState.find((p) => p.user_id === userId);
    return participant ? `참가자 ${participant.user_id.slice(0, 6)}…` : userId.slice(0, 6);
  };

  const activeMatch = data ?? null;
  const isSpectator = mySlot === null;

  return (
    <div className="card space-y-4">
      <h2 className="text-lg font-semibold text-white">실시간 경기</h2>
      {!user && <p className="text-sm text-night-400">로그인 후 이용할 수 있습니다.</p>}

      {!activeMatch && !isLoading && (
        <p className="text-sm text-night-400">진행 중인 라운드가 없습니다. 방장이 라운드를 시작하면 게임이 표시됩니다.</p>
      )}

      {statusMessage && <p className="text-sm text-green-400">{statusMessage}</p>}
      {statusError && <p className="text-sm text-red-400">{statusError}</p>}

      <div className="grid gap-3 rounded-lg border border-night-800/60 bg-night-950/40 p-4 text-sm text-night-200 sm:grid-cols-2">
        <div>
          <p className="text-night-500">현재 문제</p>
          <p className="text-2xl font-bold text-white">{activeMatch?.target_number ?? "-"}</p>
        </div>
        <div>
          <p className="text-night-500">남은 시간</p>
          <p className="text-2xl font-bold text-indigo-400">{formatRemaining()}</p>
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

      {activeMatch && (
        <div className="space-y-2 rounded-lg border border-night-800/60 bg-night-950/30 p-4 text-xs text-night-300">
          <p className="font-semibold text-night-200">현재 라운드 문제 목록</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {activeMatch.problems.map((problem) => (
              <div
                key={`${problem.target_number}-${problem.index}`}
                className={`rounded-md border px-3 py-2 ${
                  problem.index === activeMatch.current_index
                    ? "border-indigo-500 bg-indigo-500/10 text-indigo-100"
                    : "border-night-800 text-night-300"
                }`}
              >
                <p>#{problem.index + 1}</p>
                <p className="text-sm font-semibold text-white">{problem.target_number}</p>
                <p className="text-[11px] text-night-400">최적 {problem.optimal_cost}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
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
              onExpressionChange={
                isMine
                  ? (value) => {
                      setBoards((prev) => ({
                        ...prev,
                        [slot]: { ...prev[slot], expression: value },
                      }));
                      setPendingInput({ slot, value });
                    }
                  : undefined
              }
              onSubmit={isMine ? () => submitExpression(slot) : undefined}
              disabled={!activeMatch || !assignedUser}
              isMine={isMine}
              submitting={submittingSlot === slot}
              placeholder={slot === "playerOne" ? "예: (1+2)*3" : "예: (1+3)*2"}
            />
          );
        })}
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
  disabled: boolean;
  isMine: boolean;
  submitting: boolean;
  placeholder?: string;
}

function PlayerPanel({
  title,
  userLabel,
  expression,
  history,
  onExpressionChange,
  onSubmit,
  disabled,
  isMine,
  submitting,
  placeholder,
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
        placeholder={placeholder}
        disabled={!isMine || disabled || submitting}
        className="mt-3 h-24 w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
      />

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

```


