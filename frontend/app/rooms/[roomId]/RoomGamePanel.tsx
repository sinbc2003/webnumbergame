"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import { describeRoomMode, describeMatchup } from "@/lib/roomLabels";
import { RELAY_TEAM_A, RELAY_TEAM_B } from "@/lib/relay";
import type { ActiveMatch, Participant, RoundType, Room } from "@/types/api";

type BoardSlot = "playerOne" | "playerTwo";
type PlayerAssignmentSlot = "player_one" | "player_two";
type RelaySelections = {
  teamA: string[];
  teamB: string[];
};
type RelayTeamKey = keyof RelaySelections;

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
  message_id?: string;
  username?: string;
  message?: string;
  timestamp?: string;
  team_a?: Array<{
    slot_index?: number;
    user_id?: string | null;
    username?: string | null;
  }>;
  team_b?: Array<{
    slot_index?: number;
    user_id?: string | null;
    username?: string | null;
  }>;
  team_size?: number;
  problem_index?: number;
  total_problems?: number;
  include_problem_state?: boolean;
  match_id?: string;
  target_number?: number;
  optimal_cost?: number;
  deadline?: string;
};

interface HistoryEntry {
  expression: string;
  operatorCount: number;
  timestamp: string;
  submittedAt: string;
  isOptimal?: boolean;
  metTarget?: boolean;
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

interface RoomChatMessage {
  id: string;
  userId: string;
  username: string;
  message: string;
  timestamp: string;
}

type RoundOutcome = {
  reason: string;
  winnerId?: string | null;
  operatorCount?: number | null;
  submittedAt?: string | null;
  isOptimal?: boolean;
};

interface MatchSummary {
  finishedAt: string;
  reason: string;
  winnerId: string | null;
  winnerLabel: string;
  winnerExpression?: string | null;
  winnerOperatorCount?: number | null;
  winnerSubmittedAt?: string | null;
  targetNumber?: number | null;
  totalProblems?: number | null;
  optimalCost?: number | null;
  matchup: string;
  histories: {
    playerOne: HistoryEntry[];
    playerTwo: HistoryEntry[];
  };
  players: {
    playerOneLabel: string;
    playerTwoLabel: string;
  };
}

const allowedTokens = new Set(["1", "+", "*", "(", ")"]);
const sanitizeExpression = (value: string) =>
  value
    .split("")
    .filter((char) => allowedTokens.has(char))
    .join("");
const normalizedForEvaluation = (value: string): string => sanitizeExpression(value).trim();
const computeExpressionValue = (value: string): number | null => {
  const sanitized = normalizedForEvaluation(value);
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
  normalizedForEvaluation(expression)
    .split("")
    .filter((char) => allowedTokens.has(char))
    .length;
const INPUT_WARNING = "사용 가능한 기호는 1, +, *, (, ) 만 허용됩니다.";
const CRITICAL_COUNTDOWN_THRESHOLD = 5;
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
const TEAM_MEMBER_LABEL_MAP: Record<number, string[]> = {
  2: ["1번 주자", "2번 주자"],
  4: ["1번 주자", "2번 주자", "3번 주자", "4번 주자"],
};
const TEAM_TOTAL_BUDGET = 32;

const createEmptyRelaySelections = (teamSize: number): RelaySelections => {
  const normalized = Math.max(0, teamSize);
  return {
    teamA: Array.from({ length: normalized }, () => ""),
    teamB: Array.from({ length: normalized }, () => ""),
  };
};

const deriveRelaySelections = (participants: Participant[], teamSize: number): RelaySelections => {
  const base = createEmptyRelaySelections(teamSize);
  if (!teamSize) {
    return base;
  }
  participants.forEach((participant) => {
    if (!participant.user_id) return;
    const order = typeof participant.order_index === "number" ? participant.order_index : null;
    if (order === null || order < 0 || order >= teamSize) return;
    if (participant.team_label === RELAY_TEAM_A) {
      base.teamA[order] = participant.user_id;
    } else if (participant.team_label === RELAY_TEAM_B) {
      base.teamB[order] = participant.user_id;
    }
  });
  return base;
};

const relaySelectionsToPayload = (state: RelaySelections) => ({
  team_a: state.teamA.map((value) => value || null),
  team_b: state.teamB.map((value) => value || null),
});

const buildMemberNames = (teamSize: number) => {
  if (TEAM_MEMBER_LABEL_MAP[teamSize]) {
    return TEAM_MEMBER_LABEL_MAP[teamSize]!;
  }
  return Array.from({ length: teamSize }, (_, index) => `${index + 1}번 주자`);
};

const buildAllocations = (teamSize: number) => {
  const normalized = Math.max(1, teamSize);
  const base = Math.max(4, Math.floor(TEAM_TOTAL_BUDGET / normalized));
  const allocations = Array.from({ length: normalized }, () => base);
  let remainder = TEAM_TOTAL_BUDGET - base * normalized;
  for (let index = 0; index < allocations.length && remainder > 0; index += 1) {
    allocations[index] += 1;
    remainder -= 1;
  }
  return allocations;
};

const createDefaultTeamMembers = (teamSize: number): TeamMemberState[] => {
  const names = buildMemberNames(teamSize);
  const allocations = buildAllocations(teamSize);
  return names.map((name, index) => {
    const allocation = allocations[index] ?? allocations[0] ?? 8;
    return {
      name,
      allocation,
      remaining: allocation,
      input: "",
    };
  });
};

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
  const teamSize = Math.max(1, room.team_size ?? (isTeamRound ? 4 : 1));
  const isRelayRoom = teamSize > 1;
  const relaySlotCount = isRelayRoom ? teamSize : 0;
  const [playerOne, setPlayerOne] = useState<string | undefined>(initialPlayerOne);
  const [playerTwo, setPlayerTwo] = useState<string | undefined>(initialPlayerTwo);
  const [boards, setBoards] = useState<{ playerOne: BoardState; playerTwo: BoardState }>({
    playerOne: createBoardState(),
    playerTwo: createBoardState(),
  });
  const boardsRef = useRef<{ playerOne: BoardState; playerTwo: BoardState }>(boards);
  const lastProblemSnapshotRef = useRef<{ playerOne: HistoryEntry[]; playerTwo: HistoryEntry[] } | null>(null);
  const [pendingInput, setPendingInput] = useState<{ slot: BoardSlot; value: string } | null>(null);
  const [submittingSlot, setSubmittingSlot] = useState<BoardSlot | null>(null);
  const playerTextareaRefs = useRef<Record<BoardSlot, HTMLTextAreaElement | null>>({
    playerOne: null,
    playerTwo: null,
  });
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [participantState, setParticipantState] = useState<Participant[]>(participants);
  const [inputWarnings, setInputWarnings] = useState<Record<BoardSlot, string | null>>({
    playerOne: null,
    playerTwo: null,
  });
  const [roundOutcome, setRoundOutcome] = useState<RoundOutcome | null>(null);
  const [matchSummary, setMatchSummary] = useState<MatchSummary | null>(null);
  const [showSummary, setShowSummary] = useState(false);
  const [roomClosedReason, setRoomClosedReason] = useState<string | null>(null);
  const [preCountdown, setPreCountdown] = useState<number | null>(null);
  const [leaving, setLeaving] = useState(false);
  const [assigningSlot, setAssigningSlot] = useState<PlayerAssignmentSlot | null>(null);
  const [relaySelections, setRelaySelections] = useState<RelaySelections>(() =>
    deriveRelaySelections(participants, relaySlotCount),
  );
  const [relaySaving, setRelaySaving] = useState(false);
  const countdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const userInteractedRef = useRef(false);
  const tickRef = useRef<number | null>(null);
  const activeMatchRef = useRef<ActiveMatch | null>(null);
  const [initialRemaining, setInitialRemaining] = useState<number | null>(null);
  const [activeMatchId, setActiveMatchId] = useState<string | null>(null);
  const [slotSelections, setSlotSelections] = useState<{ player_one: string; player_two: string }>({
    player_one: room.player_one_id ?? "",
    player_two: room.player_two_id ?? "",
  });
  const [chatMessages, setChatMessages] = useState<RoomChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [chatErrorMessage, setChatErrorMessage] = useState<string | null>(null);
  const [scoreboard, setScoreboard] = useState<{ playerOne: number; playerTwo: number }>({
    playerOne: 0,
    playerTwo: 0,
  });
  const [problemWins, setProblemWins] = useState<{ playerOne: number; playerTwo: number }>({
    playerOne: 0,
    playerTwo: 0,
  });
  const [latestCostBySlot, setLatestCostBySlot] = useState<{ playerOne: number | null; playerTwo: number | null }>({
    playerOne: null,
    playerTwo: null,
  });
  const [lastWinnerLabel, setLastWinnerLabel] = useState<string | null>(null);
  const [lastWinReason, setLastWinReason] = useState<string | null>(null);

  const playerIdsRef = useRef<{ playerOne: string | undefined; playerTwo: string | undefined }>({
    playerOne: initialPlayerOne,
    playerTwo: initialPlayerTwo,
  });
  const chatBodyRef = useRef<HTMLDivElement | null>(null);
  const joinStateRef = useRef<{ userId?: string; joined: boolean }>({ joined: false });

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
    if (!chatBodyRef.current) return;
    chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
  }, [chatMessages]);

  useEffect(() => {
    setParticipantState(participants);
  }, [participants]);

  useEffect(() => {
    if (!isRelayRoom) {
      setRelaySelections(createEmptyRelaySelections(0));
      return;
    }
    setRelaySelections(deriveRelaySelections(participantState, relaySlotCount));
  }, [isRelayRoom, participantState, relaySlotCount]);

  useEffect(() => {
    boardsRef.current = boards;
  }, [boards]);

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
  const applyActiveMatchPatch = useCallback(
    (patch: Partial<ActiveMatch>) => {
      mutate(
        (current) => {
          if (!current) {
            return current;
          }
          const next = { ...current, ...patch };
          activeMatchRef.current = next;
          return next;
        },
        false,
      );
    },
    [mutate],
  );
  const hasActiveMatch = Boolean(activeMatch);

  useEffect(() => {
    activeMatchRef.current = activeMatch;
  }, [activeMatch]);

  useEffect(() => {
    if (hasActiveMatch) {
      setShowSummary(false);
      setRoomClosedReason(null);
    }
  }, [hasActiveMatch]);

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
      setBoards((prev) => ({
        ...prev,
        [slot]: { ...prev[slot], expression: rawValue },
      }));
      const sanitized = sanitizeExpression(rawValue);
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

  const renderScoreboardPanel = (className = "") => {
    const slotALabel = participantLabel(playerOne);
    const slotBLabel = participantLabel(playerTwo);
    return (
      <div className={`rounded-2xl border border-night-800/70 bg-night-950/30 p-4 text-night-200 ${className}`}>
        <p className="text-[11px] uppercase tracking-[0.35em] text-night-500">SCORE BOARD</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          <div>
            <p className="text-xs text-night-500">{slotLabels.playerOne}</p>
            <p className="text-lg font-semibold text-white">{slotALabel}</p>
            <p className="mt-1 text-3xl font-black text-emerald-300">{scoreboard.playerOne}</p>
          </div>
          <div className="flex flex-col items-center justify-center">
            <span className="text-sm text-night-500">vs</span>
          </div>
          <div className="text-right">
            <p className="text-xs text-night-500">{slotLabels.playerTwo}</p>
            <p className="text-lg font-semibold text-white">{slotBLabel}</p>
            <p className="mt-1 text-3xl font-black text-indigo-300">{scoreboard.playerTwo}</p>
          </div>
        </div>
        {lastWinnerLabel && (
          <p className="mt-3 text-xs text-night-400">
            최근 승자: <span className="font-semibold text-white">{lastWinnerLabel}</span>
            {lastWinReason ? ` · ${lastWinReason}` : ""}
          </p>
        )}
        <div className="mt-3 rounded-xl border border-night-900/60 bg-night-900/30 px-3 py-2 text-xs text-night-400">
          <p className="uppercase tracking-[0.35em] text-night-600">Problem Score</p>
          <p className="mt-1 text-2xl font-black text-white">
            {problemWins.playerOne} : {problemWins.playerTwo}
          </p>
          <p className="text-[11px] text-night-500">
            라운드 내 완료된 문제 승부 (A / B)
          </p>
        </div>
      </div>
    );
  };

  const roundLabel = describeRoomMode({ mode: room.mode, team_size: teamSize });
  const matchupLabel = describeMatchup(teamSize);
  const slotLabels = {
    playerOne: teamSize > 1 ? "릴레이 A 팀" : "플레이어 1",
    playerTwo: teamSize > 1 ? "릴레이 B 팀" : "플레이어 2",
  };
  const renderRelayTeamColumn = (teamKey: RelayTeamKey) => {
    if (!isRelayRoom) return null;
    const selections = relaySelections[teamKey];
    const columnLabel = teamKey === "teamA" ? slotLabels.playerOne : slotLabels.playerTwo;
    const assignedCount = selections.filter((value) => Boolean(value)).length;
    const slotInfoLabel = (participant: Participant | null) => {
      if (!participant?.team_label || typeof participant.order_index !== "number") return null;
      const teamName = participant.team_label === RELAY_TEAM_A ? "A" : "B";
      return `${teamName}팀 · ${participant.order_index + 1}번`;
    };
    return (
      <div className="rounded-2xl border border-night-900/60 bg-night-950/40 p-4 text-xs text-night-200 sm:text-sm">
        <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.3em] text-night-500">
          <span>{columnLabel}</span>
          <span>
            {assignedCount} / {relaySlotCount}명
          </span>
        </div>
        <div className="mt-3 space-y-2">
          {selections.map((userId, index) => {
            const participant = userId ? participantMap.get(userId) ?? null : null;
            const options = buildRelayOptions(userId);
            const slotTitle = `${index + 1}번 슬롯`;
            const displayName = userId ? participantLabel(userId) : "비어 있음";
            const meta = slotInfoLabel(participant);
            return (
              <div
                key={`${teamKey}-${index}`}
                className="flex min-w-0 items-center gap-2 rounded-xl border border-night-900/40 bg-night-900/20 px-3 py-2 text-night-100"
              >
                <span className="text-night-500">{slotTitle}</span>
                <span className="flex-1 truncate font-semibold text-white">{displayName}</span>
                {meta && <span className="hidden text-[11px] text-night-500 md:inline">{meta}</span>}
                {participant?.is_ready && (
                  <span className="rounded-full border border-emerald-400 px-2 py-0.5 text-[10px] text-emerald-200">READY</span>
                )}
                {isHost ? (
                  <select
                    value={userId}
                    disabled={relaySaving}
                    onChange={(event) => handleRelaySlotChange(teamKey, index, event.target.value)}
                    className="w-32 rounded-md border border-night-800 bg-night-950 px-2 py-1 text-xs text-white focus:border-indigo-500 focus:outline-none disabled:opacity-60 sm:text-sm"
                  >
                    {options.map((option) => (
                      <option
                        key={`${teamKey}-${index}-${option.value || "empty"}`}
                        value={option.value}
                        disabled={option.disabled}
                      >
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="text-[11px] text-night-500">
                    {displayName === "비어 있음" ? "배정 대기" : "배정됨"}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };
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

  const canSendChat = Boolean(user);

  const refreshParticipantsList = useCallback(async () => {
    try {
      const { data } = await api.get<Participant[]>(`/rooms/${roomId}/participants`);
      setParticipantState(data);
    } catch {
      // ignore
    }
  }, [roomId]);

  const participantMap = useMemo(() => {
    const map = new Map<string, Participant>();
    participantState.forEach((participant) => {
      if (participant.user_id) {
        map.set(participant.user_id, participant);
      }
    });
    return map;
  }, [participantState]);

  const assignedRelayUserIds = useMemo(() => {
    const values = [...relaySelections.teamA, ...relaySelections.teamB].filter(Boolean) as string[];
    return new Set(values);
  }, [relaySelections]);

  const buildRelayOptions = useCallback(
    (currentValue: string) => {
      const normalizedCurrent = currentValue || "";
      return [{ label: "비워두기", value: "", disabled: false }].concat(
        participantQueue.map((participant) => {
          const disabled =
            assignedRelayUserIds.has(participant.user_id) && participant.user_id !== normalizedCurrent;
          return {
            label: participant.username ?? (participant.user_id ? `참가자 ${participant.user_id.slice(0, 6)}…` : "이름 없음"),
            value: participant.user_id,
            disabled,
          };
        }),
      );
    },
    [participantQueue, assignedRelayUserIds],
  );

  const refreshRoomSnapshot = useCallback(async () => {
    try {
      const { data } = await api.get<Room>(`/rooms/${roomId}`);
      const nextOne = data.player_one_id ?? undefined;
      const nextTwo = data.player_two_id ?? undefined;
      playerIdsRef.current = { playerOne: nextOne, playerTwo: nextTwo };
      setPlayerOne(nextOne);
      setPlayerTwo(nextTwo);
      setSlotSelections({
        player_one: nextOne ?? "",
        player_two: nextTwo ?? "",
      });
    } catch {
      // ignore
    }
  }, [roomId]);

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

  const participantOrder = useCallback(
    (userId?: string | null) => {
      if (!userId) return null;
      const index = participantQueue.findIndex((participant) => participant.user_id === userId);
      return index === -1 ? null : index + 1;
    },
    [participantQueue],
  );

  const handleSendChat = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!canSendChat) {
        setChatErrorMessage("로그인 후 대화를 보낼 수 있습니다.");
        return;
      }
      const trimmed = chatInput.trim();
      if (!trimmed) return;
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
    },
    [canSendChat, chatInput, roomId],
  );

  const formatChatTime = useCallback((value: string) => {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
  }, []);

  const handleLeaveRoom = useCallback(async () => {
    if (leaving) return;

    let allowLeave = true;
    if (typeof window !== "undefined") {
      if (hasActiveMatch) {
        allowLeave = window.confirm("라운드가 진행 중입니다. 지금 나가면 기권 처리됩니다. 나가시겠습니까?");
      } else if (isHost) {
        allowLeave = window.confirm("방장이 나가면 방이 종료됩니다. 나가시겠습니까?");
      }
    }
    if (!allowLeave) {
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
  }, [hasActiveMatch, isHost, leaving, roomId, router, user]);

  const handleReturnToLobby = useCallback(() => {
    router.push("/rooms");
  }, [router]);

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
      if (!isHost || isRelayRoom) return;
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
    [isHost, isRelayRoom, mutate, playerOne, playerTwo, roomId],
  );

  const handleRelaySlotChange = useCallback(
    async (teamKey: RelayTeamKey, slotIndex: number, rawValue: string) => {
      if (!isHost || !isRelayRoom || relaySaving) return;
      const nextValue = rawValue || "";
      if (relaySelections[teamKey][slotIndex] === nextValue) return;
      setStatusError(null);
      setStatusMessage(null);
      const nextSelections: RelaySelections = {
        teamA: [...relaySelections.teamA],
        teamB: [...relaySelections.teamB],
      };
      if (nextValue) {
        nextSelections.teamA = nextSelections.teamA.map((value, idx) =>
          value === nextValue && !(teamKey === "teamA" && idx === slotIndex) ? "" : value,
        );
        nextSelections.teamB = nextSelections.teamB.map((value, idx) =>
          value === nextValue && !(teamKey === "teamB" && idx === slotIndex) ? "" : value,
        );
      }
      nextSelections[teamKey][slotIndex] = nextValue;
      setRelaySelections(nextSelections);
      setRelaySaving(true);
      try {
        await api.post(`/rooms/${roomId}/relay-roster`, relaySelectionsToPayload(nextSelections));
        setStatusMessage("릴레이 슬롯을 업데이트했습니다.");
      } catch (err: any) {
        setStatusError(err?.response?.data?.detail ?? "릴레이 슬롯을 업데이트하지 못했습니다.");
        await refreshParticipantsList();
      } finally {
        setRelaySaving(false);
      }
    },
    [isHost, isRelayRoom, relaySaving, relaySelections, refreshParticipantsList, roomId],
  );

  const handleProblemOutcome = useCallback(
    (payload: RoomEventPayload) => {
      const snapshot = boardsRef.current;
      lastProblemSnapshotRef.current = {
        playerOne: snapshot.playerOne.history.map((entry) => ({ ...entry })),
        playerTwo: snapshot.playerTwo.history.map((entry) => ({ ...entry })),
      };

      const reason = payload.reason ?? "optimal";
      const winnerSubmission = payload.winner_submission ?? null;
      const winnerId =
        payload.winner_user_id ?? winnerSubmission?.user_id ?? payload.winner_submission_id ?? null;

      setRoundOutcome({
        reason,
        winnerId,
        operatorCount: typeof winnerSubmission?.cost === "number" ? winnerSubmission.cost : null,
        submittedAt: winnerSubmission?.submitted_at ?? null,
        isOptimal: Boolean(winnerSubmission?.is_optimal),
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
        setLastWinnerLabel(winnerLabel);
        const reasonLabel =
          reason === "timeout"
            ? "시간 종료 판정"
            : reason === "forfeit"
              ? "기권승"
              : reason === "optimal"
                ? "최적 연산기호 달성"
                : "최종 판정";
        setLastWinReason(reasonLabel);
        if (winnerId === playerIdsRef.current.playerOne) {
          setScoreboard((prev) => ({ ...prev, playerOne: prev.playerOne + 1 }));
          setProblemWins((prev) => ({ ...prev, playerOne: prev.playerOne + 1 }));
        } else if (winnerId === playerIdsRef.current.playerTwo) {
          setScoreboard((prev) => ({ ...prev, playerTwo: prev.playerTwo + 1 }));
          setProblemWins((prev) => ({ ...prev, playerTwo: prev.playerTwo + 1 }));
        }
        if (winnerId === user?.id) {
          const operatorCopy =
            typeof winnerSubmission?.cost === "number" ? `${winnerSubmission.cost}개 연산기호로 ` : "";
          const message =
            reason === "timeout"
              ? `${operatorCopy}시간 종료! 가장 효율적으로 승리했습니다.`
              : reason === "forfeit"
                ? "상대가 나가 기권승으로 처리되었습니다."
                : `${operatorCopy}승리했습니다!`;
          setStatusMessage(message.trim());
          setStatusError(null);
          playTone("success");
        } else {
          const operatorCopy =
            typeof winnerSubmission?.cost === "number"
              ? `${winnerSubmission.cost}개 연산기호`
              : "더 적은 연산기호";
          const message =
            reason === "timeout"
              ? `${winnerLabel} 님이 ${operatorCopy}로 시간을 지배했습니다.`
              : reason === "forfeit"
                ? `${winnerLabel} 님이 남아 있어 승리했습니다.`
                : `${winnerLabel} 님이 ${operatorCopy}로 판정을 가져갔습니다.`;
          setStatusError(message);
          setStatusMessage(null);
          playTone("error");
        }
      } else if (reason === "timeout") {
        setStatusMessage("시간 종료! 제출된 식이 없어 무승부입니다.");
        setStatusError(null);
      } else if (reason === "forfeit") {
        setStatusMessage("상대가 나가 라운드가 종료되었습니다.");
        setStatusError(null);
      }
    },
    [participantLabel, playTone, user?.id],
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
            if (payload.participant?.user_id === user?.id) {
              refreshRoomSnapshot();
            }
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
            if (payload.user_id === user?.id) break;
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
              const submissionCost =
                typeof payload.submission.cost === "number"
                  ? payload.submission.cost
                  : countOperators(payload.submission.expression);
              setLatestCostBySlot((prev) => ({
                ...prev,
                [slot]: submissionCost,
              }));
              setBoards((prev) => {
                const metTarget =
                  payload.submission!.distance === 0 ||
                  (typeof payload.submission!.result_value === "number" &&
                    (activeMatchRef.current?.target_number ?? activeMatch?.target_number) ===
                      payload.submission!.result_value);
                const entry: HistoryEntry = {
                  expression: payload.submission!.expression,
                  operatorCount: submissionCost,
                  timestamp: new Date().toISOString(),
                  submittedAt: payload.submission!.submitted_at ?? new Date().toISOString(),
                  isOptimal: Boolean(payload.submission!.is_optimal),
                  metTarget,
                };
                const shouldRecord = allowHistory(entry);
                const nextHistory: HistoryEntry[] = shouldRecord
                  ? [entry, ...prev[slot].history].slice(0, 10)
                  : prev[slot].history;
                return {
                  ...prev,
                  [slot]: { ...prev[slot], history: nextHistory },
                };
              });
            }
            if (payload.submission.user_id && payload.submission.user_id === user?.id) {
              if (payload.submission.distance === 0) {
                const submissionCost =
                  typeof payload.submission.cost === "number"
                    ? payload.submission.cost
                    : countOperators(payload.submission.expression);
                setStatusMessage(`목표 달성! 연산기호 ${submissionCost}개로 기록했습니다.`);
                setStatusError(null);
                playTone("success");
              } else if (typeof payload.submission.distance === "number") {
                setStatusError("아직 목표값에 도달하지 못했습니다. 조금만 더 조정해 보세요.");
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
            setLatestCostBySlot({ playerOne: null, playerTwo: null });
            setScoreboard({ playerOne: 0, playerTwo: 0 });
            setProblemWins({ playerOne: 0, playerTwo: 0 });
            setLastWinnerLabel(null);
            setLastWinReason(null);
            setStatusMessage("새 라운드가 시작되었습니다. 카운트다운 후 입력이 열립니다.");
            setStatusError(null);
            setRoundOutcome(null);
            setInitialRemaining(null);
            tickRef.current = null;
            lastProblemSnapshotRef.current = null;
            triggerPreCountdown();
            mutate();
            break;
          }
          case "problem_advanced": {
            setStatusMessage("다음 문제로 이동했습니다.");
            lastProblemSnapshotRef.current = null;
            setLatestCostBySlot({ playerOne: null, playerTwo: null });
            setBoards({
              playerOne: createBoardState(),
              playerTwo: createBoardState(),
            });
            if (payload.problem_index !== undefined) {
              applyActiveMatchPatch({
                current_index: payload.problem_index,
                target_number: payload.target_number ?? activeMatchRef.current?.target_number,
                optimal_cost: payload.optimal_cost ?? activeMatchRef.current?.optimal_cost,
                deadline: payload.deadline ?? activeMatchRef.current?.deadline,
              });
            }
            mutate();
            break;
          }
          case "problem_finished": {
            handleProblemOutcome(payload);
            mutate();
            break;
          }
          case "round_finished": {
            const reason = payload.reason ?? "optimal";
            const winnerSubmission = payload.winner_submission;
            const winnerId =
              payload.winner_user_id ?? winnerSubmission?.user_id ?? payload.winner_submission_id ?? null;

            if (payload.include_problem_state !== false) {
              handleProblemOutcome(payload);
            } else if (!lastProblemSnapshotRef.current) {
              const snapshot = boardsRef.current;
              lastProblemSnapshotRef.current = {
                playerOne: snapshot.playerOne.history.map((entry) => ({ ...entry })),
                playerTwo: snapshot.playerTwo.history.map((entry) => ({ ...entry })),
              };
            }

            const historySource =
              lastProblemSnapshotRef.current ??
              {
                playerOne: boardsRef.current.playerOne.history,
                playerTwo: boardsRef.current.playerTwo.history,
              };
            const historySnapshot = {
              playerOne: historySource.playerOne.map((entry) => ({ ...entry })),
              playerTwo: historySource.playerTwo.map((entry) => ({ ...entry })),
            };
            lastProblemSnapshotRef.current = null;

            setPreCountdown(null);
            setInitialRemaining(null);
            tickRef.current = null;

            const activeSnapshot = activeMatchRef.current;
            const winnerLabel = winnerId ? participantLabel(winnerId) : "무승부";

            setRoundOutcome((prev) =>
              prev ?? {
                reason,
                winnerId,
                operatorCount:
                  typeof winnerSubmission?.cost === "number" ? winnerSubmission.cost : null,
                submittedAt: winnerSubmission?.submitted_at ?? null,
                isOptimal: Boolean(winnerSubmission?.is_optimal),
              },
            );
            setMatchSummary({
              finishedAt: new Date().toISOString(),
              reason,
              winnerId,
              winnerLabel,
              winnerExpression: winnerSubmission?.expression ?? null,
              winnerOperatorCount:
                typeof winnerSubmission?.cost === "number" ? winnerSubmission.cost : null,
              winnerSubmittedAt: winnerSubmission?.submitted_at ?? null,
              targetNumber: activeSnapshot?.target_number ?? payload.target_number ?? null,
              totalProblems: payload.total_problems ?? activeSnapshot?.total_problems ?? null,
              optimalCost: activeSnapshot?.optimal_cost ?? payload.optimal_cost ?? null,
              matchup: matchupLabel,
              histories: historySnapshot,
              players: {
                playerOneLabel: participantLabel(playerIdsRef.current.playerOne ?? undefined),
                playerTwoLabel: participantLabel(playerIdsRef.current.playerTwo ?? undefined),
              },
            });
            setShowSummary(true);
            setRoomClosedReason(null);
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
            const summaryHistories = {
              playerOne: boardsRef.current.playerOne.history.map((entry) => ({ ...entry })),
              playerTwo: boardsRef.current.playerTwo.history.map((entry) => ({ ...entry })),
            };
            setMatchSummary((prev) => {
              if (prev) {
                return prev;
              }
              return {
                finishedAt: new Date().toISOString(),
                reason: closingReason,
                winnerId: null,
                winnerLabel: "경기가 종료되었습니다.",
                winnerExpression: null,
                winnerOperatorCount: null,
                winnerSubmittedAt: null,
                targetNumber: activeMatchRef.current?.target_number ?? null,
                totalProblems: activeMatchRef.current?.total_problems ?? null,
                optimalCost: activeMatchRef.current?.optimal_cost ?? null,
                matchup: matchupLabel,
                histories: summaryHistories,
                players: {
                  playerOneLabel: participantLabel(playerIdsRef.current.playerOne ?? undefined),
                  playerTwoLabel: participantLabel(playerIdsRef.current.playerTwo ?? undefined),
                },
              };
            });
            setRoomClosedReason(
              closingReason === "forfeit"
                ? "상대 기권으로 방이 종료되었습니다."
                : closingReason === "host_left" || closingReason === "host_left_forfeit"
                  ? "방장이 퇴장해 방이 종료되었습니다."
                  : closingReason === "host_disconnected"
                    ? "방장 연결이 끊어져 방이 종료되었습니다."
                    : "방이 종료되었습니다.",
            );
            setShowSummary(true);
            break;
          }
          case "chat_message": {
            setChatMessages((prev) => {
              const next = [
                ...prev,
                {
                  id: payload.message_id ?? `${Date.now()}-${prev.length}`,
                  userId: payload.user_id ?? "unknown",
                  username: payload.username ?? "익명",
                  message: payload.message ?? "",
                  timestamp: payload.timestamp ?? new Date().toISOString(),
                },
              ];
              return next.slice(-50);
            });
            break;
          }
          case "relay_roster": {
            const slotMap = new Map<string, { team_label: string; order_index: number }>();
            const applySlots = (
              slots: RoomEventPayload["team_a"],
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
            applySlots(payload.team_a ?? [], RELAY_TEAM_A);
            applySlots(payload.team_b ?? [], RELAY_TEAM_B);
            setParticipantState((prev) =>
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
                return {
                  ...participant,
                  team_label: info.team_label,
                  order_index: info.order_index,
                };
              }),
            );
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
  }, [user, wsUrl, mutate, refreshRoomSnapshot, router, participantLabel, playTone, triggerPreCountdown, matchupLabel]);

  useEffect(() => {
    if (!user?.id || !room.code) return;
    if (participantState.some((p) => p.user_id === user.id)) {
      joinStateRef.current = { joined: true, userId: user.id };
      return;
    }
    if (joinStateRef.current.joined && joinStateRef.current.userId === user.id) {
      return;
    }
    let cancelled = false;
    const attemptJoin = async () => {
      joinStateRef.current = { joined: true, userId: user.id };
      try {
        await api.post("/rooms/join", {
          code: room.code,
          team_label: null,
        });
        await refreshRoomSnapshot();
      } catch (err: any) {
        if (cancelled) return;
        joinStateRef.current = { joined: false, userId: user.id };
        setStatusError(err?.response?.data?.detail ?? "방 참가에 실패했습니다.");
      }
    };
    attemptJoin();
    return () => {
      cancelled = true;
    };
  }, [participantState, refreshRoomSnapshot, room.code, user?.id]);

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

  useEffect(() => {
    if (remaining === 0 && hasActiveMatch) {
      mutate();
    }
  }, [remaining, hasActiveMatch, mutate]);

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
    const rawValue = boards[slot].expression.trim();
    const sanitized = normalizedForEvaluation(rawValue);
    if (!sanitized) {
      setStatusError("식을 입력해 주세요.");
      return;
    }
    setSubmittingSlot(slot);
    setStatusError(null);
    setStatusMessage(null);
    try {
      await api.post(`/rooms/${roomId}/submit`, {
        expression: sanitized,
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
      requestAnimationFrame(() => {
        playerTextareaRefs.current[slot]?.focus();
      });
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
  const isSimplifiedSoloView = isPlayerView && !isTeamRound && teamSize === 1;
  const visibleSlots: BoardSlot[] = isPlayerView && mySlot ? [mySlot] : (["playerOne", "playerTwo"] as BoardSlot[]);
  const myBoard = mySlot ? boards[mySlot] : null;
  const myExpression = myBoard?.expression ?? "";
  const myHistory = myBoard?.history ?? [];
  const allowHistory = (entry: HistoryEntry | null) => {
    if (!entry) return false;
    return Boolean(entry.metTarget || entry.isOptimal);
  };
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
  useEffect(() => {
    if (!isPlayerView || !mySlot) return;
    requestAnimationFrame(() => {
      playerTextareaRefs.current[mySlot]?.focus();
    });
  }, [isPlayerView, mySlot]);
  const problemIndicators = activeMatch
    ? Array.from({ length: activeMatch.total_problems }, (_, index) => {
        if (index < activeMatch.current_index) return "done";
        if (index === activeMatch.current_index) return "current";
        return "hidden";
      })
    : [];
  const lobbyShellClass =
    "relative space-y-4 rounded-2xl border border-night-800/80 bg-[rgba(5,10,20,0.88)] p-4 text-night-100 shadow-[0_20px_60px_rgba(0,0,0,0.55)] sm:p-5";

  const containerClass = isPlayerView
    ? "fixed inset-0 z-40 mx-auto flex w-full max-w-6xl flex-col bg-[#050a15] px-3 py-4 text-white sm:px-5 sm:py-5"
    : hasActiveMatch
      ? "fixed inset-0 z-40 overflow-y-auto bg-[#050a15]/95 p-6 space-y-4"
      : lobbyShellClass;

  if (isSimplifiedSoloView && activeMatch && mySlot) {
    const assignedUser = mySlot === "playerOne" ? playerOne : playerTwo;
    const opponentCostForSolo =
      mySlot === "playerOne" ? latestCostBySlot.playerTwo : latestCostBySlot.playerOne;
    return (
      <div className="min-h-screen bg-[#050a15] px-4 py-6 text-night-100">
        {preCountdown !== null && <CountdownOverlay value={preCountdown} />}
        <div className="mx-auto flex max-w-5xl flex-col gap-4">
          <div className="rounded-3xl border border-night-800/60 bg-night-950/70 p-4 shadow-[0_18px_50px_rgba(0,0,0,0.5)] sm:p-5">
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="min-w-[170px]">
                  <p className="text-[11px] uppercase tracking-[0.45em] text-night-500">{roundLabel}</p>
                  <p className="mt-1 text-xs text-night-400">
                    {activeMatch.current_index + 1} / {activeMatch.total_problems} 문제 진행 중
                  </p>
                </div>
                <div className="order-3 w-full sm:order-2 sm:flex-1">
                  <div className="flex justify-center">
                    <div
                      className={`w-full max-w-[240px] rounded-full border-2 px-8 py-3 text-center text-4xl font-black ${
                        isCountdownCritical ? "border-red-500 text-red-300" : "border-indigo-400 text-white"
                      } bg-night-900/60`}
                    >
                      {formattedRemaining}
                    </div>
                  </div>
                  <div className="mt-3 text-center text-sm text-night-400">
                    <p className="text-[11px] uppercase tracking-[0.35em] text-night-600">문제 스코어</p>
                    <p className="text-2xl font-black text-white">
                      {problemWins.playerOne} : {problemWins.playerTwo}
                    </p>
                  </div>
                </div>
                <div className="order-2 ml-auto shrink-0 sm:order-3">{renderLeaveButton()}</div>
              </div>

              <div className="grid gap-3 text-night-200 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-night-900/60 bg-night-900/30 p-3">
                  <p className="text-[11px] uppercase tracking-[0.3em] text-night-500">목표값</p>
                  <p className="mt-1 text-3xl font-black text-white">{activeMatch.target_number}</p>
                </div>
                <div className="rounded-2xl border border-night-900/60 bg-night-900/30 p-3">
                  <p className="text-[11px] uppercase tracking-[0.3em] text-night-500">최적 연산기호수</p>
                  <p className="mt-1 text-3xl font-black text-white">{activeMatch.optimal_cost}</p>
                </div>
                <div className="rounded-2xl border border-night-900/60 bg-night-900/30 p-3">
                  <p className="text-[11px] uppercase tracking-[0.35em] text-night-500">값</p>
                  <p className="mt-1 text-2xl font-bold text-white">{expressionValueDisplay}</p>
                </div>
                <div className="rounded-2xl border border-night-900/60 bg-night-900/30 p-3">
                  <p className="text-[11px] uppercase tracking-[0.35em] text-night-500">연산기호</p>
                  <p className="mt-1 text-2xl font-bold text-white">{operatorCountDisplay}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-[32px] border border-night-800/70 bg-night-950/70 p-5 shadow-[0_25px_60px_rgba(0,0,0,0.55)] sm:p-6">
            <PlayerPanel
              key={mySlot}
              title={`${slotLabels.playerOne}`}
              userLabel={participantLabel(assignedUser)}
              expression={boards[mySlot].expression}
              history={boards[mySlot].history}
              onExpressionChange={(value) => handleExpressionChange(mySlot, value)}
              onSubmit={() => submitExpression(mySlot)}
              onFocus={armAudio}
              disabled={!activeMatch || !assignedUser}
              isMine
              submitting={submittingSlot === mySlot}
              placeholder="예: (1+1)*1"
              warningMessage={inputWarnings[mySlot]}
              focusLayout
              emphasizeInput
              hideIdentity
              opponentOperatorCount={opponentCostForSolo}
              textareaRefCallback={(el) => {
                playerTextareaRefs.current[mySlot] = el;
              }}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <div className="text-emerald-300">{statusMessage && <>• {statusMessage}</>}</div>
            <div className="text-red-400">{statusError && <>• {statusError}</>}</div>
          </div>
        </div>
      </div>
    );
  }

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
          {renderScoreboardPanel()}

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
               const slotOpponentCost =
                slot === "playerOne" ? latestCostBySlot.playerTwo : latestCostBySlot.playerOne;
              if (isTeamRound && isMine) {
                return (
                  <TeamBoard
                    key={slot}
                    matchId={activeMatch.match_id}
                    teamSize={teamSize}
                    expression={boards[slot].expression}
                    history={boards[slot].history}
                    onExpressionChange={(value) => handleExpressionChange(slot, value)}
                    onSubmit={() => submitExpression(slot)}
                    submitting={submittingSlot === slot}
                    disabled={!activeMatch || !assignedUser}
                    playTone={playTone}
                    armAudio={armAudio}
                    opponentOperatorCount={slotOpponentCost}
                  />
                );
              }
              return (
                <PlayerPanel
                  key={slot}
                  title={slot === "playerOne" ? slotLabels.playerOne : slotLabels.playerTwo}
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
                  opponentOperatorCount={slotOpponentCost}
                  textareaRefCallback={(el) => {
                    playerTextareaRefs.current[slot] = el;
                  }}
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
            <div className="mt-3 flex flex-wrap items-center justify-center gap-3 text-sm text-night-400">
              <p className="text-[11px] uppercase tracking-[0.35em] text-night-600">문제 스코어</p>
              <p className="text-2xl font-black text-white">
                {problemWins.playerOne} : {problemWins.playerTwo}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!hasActiveMatch) {
    const renderSlotSelector = (slot: PlayerAssignmentSlot) => {
      const boardSlot: BoardSlot = slot === "player_one" ? "playerOne" : "playerTwo";
      const assignedUser = boardSlot === "playerOne" ? playerOne : playerTwo;
      const assignedParticipant = participantState.find((participant) => participant.user_id === assignedUser);
      const showHostSelector = isHost && !isRelayRoom;
      const order = participantOrder(assignedUser);
      const helperText = isRelayRoom
        ? "릴레이 로스터에서 자동으로 지정됩니다."
        : order
          ? `입장 #${order}`
          : showHostSelector
            ? "아직 지정되지 않았습니다."
            : "방장이 지정할 때까지 대기 중입니다.";
      const label = slot === "player_one" ? "왼쪽 플레이어" : "오른쪽 플레이어";
      return (
        <div key={`slot-${slot}`} className="rounded-2xl border border-night-800/60 bg-night-950/40 p-3 text-sm text-night-200">
          <div className="flex items-center justify-between text-[11px] text-night-500">
            <span>{label}</span>
            {assignedParticipant?.is_ready && (
              <span className="rounded-full border border-emerald-400 px-2 py-0.5 text-[10px] text-emerald-200">READY</span>
            )}
          </div>
          {showHostSelector ? (
            <select
              value={slotSelections[slot]}
              disabled={assigningSlot === slot}
              onChange={(event) => handleAssignSlot(slot, event.target.value)}
              className="mt-2 w-full rounded-lg border border-night-800 bg-night-900 px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none disabled:opacity-60"
            >
              {participantOptions.map((option) => (
                <option key={`${slot}-${option.value || "empty"}`} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          ) : (
            <div className="mt-2 rounded-lg border border-night-800/60 bg-night-900/30 px-3 py-2 text-sm text-white">
              {participantLabel(assignedUser)}
            </div>
          )}
          <p className="mt-1 text-[11px] text-night-500">{helperText}</p>
        </div>
      );
    };

    const slotSelectors = (["player_one", "player_two"] as PlayerAssignmentSlot[]).map((slot) => renderSlotSelector(slot));

    return (
      <div className={lobbyShellClass}>
        {preCountdown !== null && <CountdownOverlay value={preCountdown} />}
        <div className="flex flex-wrap items-end justify-between gap-3 pb-2 sm:gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.35em] text-night-500">ROOM LOBBY</p>
            <h2 className="text-2xl font-black text-white sm:text-3xl">{room.name}</h2>
            <p className="text-sm text-night-400">{roundLabel}</p>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <span className="rounded-full border border-amber-400/60 px-3 py-0.5 text-[10px] font-semibold tracking-[0.35em] text-amber-200">
              대기 중
            </span>
            {renderLeaveButton()}
          </div>
        </div>
        {!user && <p className="text-sm text-night-500">로그인 후 이용해 주세요.</p>}
        {matchSummary && !showSummary && (
          <div className="mt-2 sm:mt-3">
            <button
              type="button"
              onClick={() => setShowSummary(true)}
              className="rounded-full border border-amber-400/60 px-4 py-1 text-xs font-semibold uppercase tracking-[0.4em] text-amber-200 transition hover:border-amber-300"
            >
              최근 경기 요약 보기
            </button>
          </div>
        )}
        {showSummary && (
          <div className="mt-2 sm:mt-3">
            <MatchSummaryCard
              summary={matchSummary}
              roomClosedReason={roomClosedReason}
              onClose={() => setShowSummary(false)}
              onReturn={handleReturnToLobby}
            />
          </div>
        )}
        <div className="mt-3 flex flex-1 flex-col gap-3 overflow-hidden sm:mt-4">
          {!isRelayRoom && (
            <div className="w-full rounded-2xl border border-night-800/70 bg-night-950/30 p-3 sm:p-4">
              <div className="flex flex-wrap items-center justify-between text-[11px] uppercase tracking-[0.3em] text-night-500">
                <span>플레이어 선택</span>
                <span className="rounded-full border border-indigo-500/50 px-3 py-0.5 text-[10px] font-semibold text-indigo-200">
                  {isHost ? "HOST" : "관전자"}
                </span>
              </div>
              <div className="mt-2 grid gap-2 md:grid-cols-[1fr_auto_1fr] md:items-center">
                {slotSelectors[0]}
                <div className="flex items-center justify-center rounded-2xl border border-night-800/50 bg-night-950/40 px-4 py-6 text-xs font-semibold tracking-[0.35em] text-night-400">
                  VS
                </div>
                {slotSelectors[1]}
              </div>
            </div>
          )}

          {isRelayRoom && (
            <div className="w-full rounded-2xl border border-night-800/70 bg-night-950/30 p-3 sm:p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.4em] text-night-500">릴레이 로스터</p>
                  <p className="text-2xl font-semibold text-white">{matchupLabel} 팀 구성</p>
                </div>
                {relaySaving && <span className="text-xs text-night-500">업데이트 중...</span>}
              </div>
              <div className="mt-2 grid gap-2 lg:grid-cols-2">
                {renderRelayTeamColumn("teamA")}
                {renderRelayTeamColumn("teamB")}
              </div>
            </div>
          )}

          <div className="flex w-full flex-col rounded-2xl border border-night-800/70 bg-night-900/40 p-3 text-night-200 h-[280px] lg:h-[40vh] overflow-hidden sm:p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-white">방 채팅</p>
              <span className="text-xs text-night-500">실시간 대화</span>
            </div>
            <div
              ref={chatBodyRef}
              className="mt-2 flex-1 min-h-[180px] space-y-2 overflow-y-auto rounded-2xl border border-night-800/70 bg-night-950/60 p-3 text-xs text-night-100"
            >
              {chatMessages.length === 0 && <p className="text-night-500">아직 메시지가 없습니다.</p>}
              {chatMessages.map((message) => (
                <div key={message.id} className="space-y-1 rounded-xl border border-night-800/60 bg-night-900/40 p-2">
                  <div className="flex items-center justify-between text-[11px] text-night-500">
                    <span className="font-semibold text-white">{message.username}</span>
                    <span>{formatChatTime(message.timestamp)}</span>
                  </div>
                  <p className="whitespace-pre-wrap break-all text-night-100">{message.message}</p>
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

          {roundOutcome && (
            <div className="w-full rounded-2xl border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-100">
              <p className="font-semibold">
                {roundOutcome.reason === "timeout"
                  ? "시간 종료 결과"
                  : roundOutcome.reason === "forfeit"
                ? "기권 처리"
                : roundOutcome.reason === "optimal"
                  ? "최적 연산기호 달성"
                  : "직전 라운드 결과"}
              </p>
              <p className="mt-1">
                승자: {roundOutcome.winnerId ? participantLabel(roundOutcome.winnerId ?? undefined) : "무승부"}
              </p>
          {typeof roundOutcome.operatorCount === "number" && (
            <p className="text-xs text-amber-200/70">연산기호 {roundOutcome.operatorCount}개</p>
          )}
          {roundOutcome.submittedAt && (
            <p className="text-[11px] text-amber-200/60">
              제출 시각 {new Date(roundOutcome.submittedAt).toLocaleTimeString("ko-KR")}
            </p>
          )}
            </div>
          )}
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
                : roundOutcome.reason === "optimal"
                  ? "최적 연산기호 달성"
                  : "라운드 결과"}
          </p>
          <p className="mt-1 text-night-300">
            승자: {roundOutcome.winnerId ? participantLabel(roundOutcome.winnerId ?? undefined) : "무승부"}
          </p>
          {typeof roundOutcome.operatorCount === "number" && (
            <p className="text-xs text-night-500">연산기호 {roundOutcome.operatorCount}개</p>
          )}
          {roundOutcome.submittedAt && (
            <p className="text-[11px] text-night-600">
              제출 시각 {new Date(roundOutcome.submittedAt).toLocaleTimeString("ko-KR")}
            </p>
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
      {renderScoreboardPanel()}

      <div className="grid gap-6 lg:grid-cols-2">
        {visibleSlots.map((slot) => {
          const isMine = mySlot === slot;
          const assignedUser = slot === "playerOne" ? playerOne : playerTwo;
          const slotOpponentCost =
            slot === "playerOne" ? latestCostBySlot.playerTwo : latestCostBySlot.playerOne;
          return (
            <PlayerPanel
              key={slot}
              title={slot === "playerOne" ? slotLabels.playerOne : slotLabels.playerTwo}
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
              opponentOperatorCount={slotOpponentCost}
              textareaRefCallback={(el) => {
                playerTextareaRefs.current[slot] = el;
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

interface TeamBoardProps {
  matchId: string;
  teamSize: number;
  expression: string;
  history: HistoryEntry[];
  onExpressionChange: (value: string) => void;
  onSubmit: () => void;
  submitting: boolean;
  disabled: boolean;
  playTone: (type: "success" | "error" | "tick") => void;
  armAudio: () => void;
  opponentOperatorCount?: number | null;
}

function TeamBoard({
  matchId,
  teamSize,
  expression,
  history,
  onExpressionChange,
  onSubmit,
  submitting,
  disabled,
  playTone,
  armAudio,
  opponentOperatorCount,
}: TeamBoardProps) {
  const [members, setMembers] = useState<TeamMemberState[]>(() => createDefaultTeamMembers(teamSize));
  const [currentIndex, setCurrentIndex] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const combined = useMemo(() => members.map((member) => member.input).join(""), [members]);
  const activeMember = members[currentIndex];
  const canEditAllocation = combined.length === 0;

  useEffect(() => {
    setMembers(createDefaultTeamMembers(teamSize));
    setCurrentIndex(0);
    setMessage(null);
    setError(null);
    onExpressionChange("");
  }, [matchId, onExpressionChange, teamSize]);

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
    if (currentIndex >= members.length - 1) {
      setMessage("모든 주자의 입력이 완료되었습니다. 필요하면 이전 주자를 선택해 조정하세요.");
      return;
    }
    setCurrentIndex((prev) => prev + 1);
    const nextMember = members[currentIndex + 1];
    setMessage(nextMember ? `${nextMember.name} 차례입니다.` : null);
  };

  const handlePrev = () => {
    if (currentIndex === 0) return;
    setCurrentIndex((prev) => prev - 1);
    const prevMember = members[currentIndex - 1];
    setMessage(prevMember ? `${prevMember.name} 차례로 돌아갔습니다.` : null);
  };

  const handleReset = () => {
    setMembers(createDefaultTeamMembers(teamSize));
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
        <p className="mt-2 min-h-[64px] break-all text-2xl">{expression || "입력을 시작하세요."}</p>
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
                  <p className="text-[11px] text-night-400">연산기호 {entry.operatorCount}개</p>
                </div>
              ))}
            </div>
          </div>
        )}
        {typeof opponentOperatorCount === "number" && (
          <div className="mt-3 rounded-xl border border-indigo-500/40 bg-indigo-500/10 p-3 text-xs text-indigo-100">
            <p className="font-semibold text-white">상대 최근 연산기호</p>
            <p className="mt-1 text-2xl font-black text-white">{opponentOperatorCount}개</p>
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
  textareaRefCallback?: (el: HTMLTextAreaElement | null) => void;
  emphasizeInput?: boolean;
  hideIdentity?: boolean;
  opponentOperatorCount?: number | null;
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
  textareaRefCallback,
  emphasizeInput = false,
  hideIdentity = false,
  opponentOperatorCount,
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
            if (!best) {
              return entry;
            }
            if (entry.operatorCount < best.operatorCount) {
              return entry;
            }
            if (entry.operatorCount === best.operatorCount) {
              return entry.submittedAt < best.submittedAt ? entry : best;
            }
            return best;
          }, null);
    const textareaMarginTop = hideIdentity ? "mt-4" : "mt-6";
    return (
      <div className="flex flex-1 flex-col gap-6 lg:flex-row">
        <div
          className={`flex-1 rounded-[32px] border-2 border-indigo-600/40 bg-night-950/60 ${emphasizeInput ? "p-7" : "p-6"} text-night-100 shadow-[0_25px_90px_rgba(0,0,0,0.6)]`}
        >
          {!hideIdentity && (
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
          )}
          <textarea
            value={expression}
            onChange={(e) => onExpressionChange?.(e.target.value)}
            onFocus={onFocus}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={!isMine || disabled || submitting}
            spellCheck={false}
            autoComplete="off"
            ref={textareaRefCallback}
            className={`${textareaMarginTop} w-full flex-1 rounded-2xl border-2 border-indigo-500/40 bg-night-900 px-4 py-4 font-mono text-white focus:border-indigo-300 focus:outline-none ${
              emphasizeInput ? "min-h-[220px] text-3xl" : "min-h-[160px] text-2xl"
            }`}
          />
          {warningMessage && <p className="mt-2 text-sm text-amber-200/90">{warningMessage}</p>}
          {isMine && onSubmit && (
            <button
              type="button"
              onClick={onSubmit}
              disabled={disabled || submitting || !expression.trim()}
              className={`mt-4 w-full rounded-2xl bg-indigo-600 font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700 ${
                emphasizeInput ? "h-16 text-xl" : "h-14 text-lg"
              }`}
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
                  <p className="break-all font-semibold text-white">{entry.expression}</p>
                  <p className="text-xs text-night-400">연산기호 {entry.operatorCount}개</p>
                </div>
              ))}
            </div>
          </div>
          {bestEntry && (
            <div className="mt-3 rounded-3xl border border-amber-400/40 bg-amber-500/10 p-4 text-sm text-amber-100">
              <p className="font-semibold">🏆 최고 기록</p>
              <p className="mt-1 break-all font-mono text-lg text-white">{bestEntry.expression}</p>
              <p className="text-xs text-amber-200/70">연산기호 {bestEntry.operatorCount}개</p>
            </div>
          )}
          {isMine && typeof opponentOperatorCount === "number" && (
            <div className="mt-3 rounded-3xl border border-indigo-500/40 bg-indigo-500/10 p-4 text-xs text-indigo-100">
              <p className="font-semibold text-white">상대 최근 연산기호</p>
              <p className="mt-1 text-2xl font-black text-white">{opponentOperatorCount}개</p>
              <p className="text-[11px] text-indigo-200/70">이 수보다 줄이면 앞서갑니다!</p>
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
        ref={textareaRefCallback}
        className="mt-3 h-24 w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 font-mono text-white focus:border-indigo-500 focus:outline-none"
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
            <p className="break-all font-semibold text-white">{entry.expression}</p>
            <p className="text-[11px] text-night-400">연산기호 {entry.operatorCount}개</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface MatchSummaryCardProps {
  summary: MatchSummary | null;
  roomClosedReason: string | null;
  onClose: () => void;
  onReturn: () => void;
}

const translateSummaryReason = (reason: string) => {
  switch (reason) {
    case "timeout":
      return "시간 종료";
    case "forfeit":
      return "기권";
    case "optimal":
      return "최적 연산기호";
    default:
      return "경기 종료";
  }
};

const computeHistoryStats = (history: HistoryEntry[]) => {
  if (!history.length) {
    return { attempts: 0, bestEntry: null, averageOperatorCount: null };
  }
  const bestEntry = history.reduce((best, entry) => {
    if (!best) return entry;
    if (entry.operatorCount < best.operatorCount) return entry;
    if (entry.operatorCount === best.operatorCount) {
      return entry.submittedAt < best.submittedAt ? entry : best;
    }
    return best;
  }, history[0]);
  const averageOperatorCount = Math.round(
    history.reduce((sum, entry) => sum + entry.operatorCount, 0) / history.length,
  );
  return { attempts: history.length, bestEntry, averageOperatorCount };
};

function MatchSummaryCard({ summary, roomClosedReason, onClose, onReturn }: MatchSummaryCardProps) {
  if (!summary) {
    return (
      <div className="rounded-3xl border border-night-800/60 bg-night-950/40 p-5 text-sm text-night-200">
        <p className="text-[11px] uppercase tracking-[0.4em] text-night-500">Match Summary</p>
        <p className="mt-2 text-2xl font-semibold text-white">경기가 종료되었습니다.</p>
        {roomClosedReason && <p className="mt-1 text-night-400">{roomClosedReason}</p>}
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onReturn}
            className="rounded-xl border border-indigo-500/60 px-4 py-2 text-sm font-semibold text-indigo-100 transition hover:border-indigo-400"
          >
            로비로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  const reasonLabel = translateSummaryReason(summary.reason);
  const players = [
    {
      key: "playerOne",
      label: summary.players.playerOneLabel,
      history: summary.histories.playerOne,
    },
    {
      key: "playerTwo",
      label: summary.players.playerTwoLabel,
      history: summary.histories.playerTwo,
    },
  ];

  return (
    <div className="rounded-3xl border border-amber-400/30 bg-night-950/70 p-5 text-sm text-night-200 shadow-[0_20px_60px_rgba(0,0,0,0.45)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.4em] text-amber-300/70">Match Summary</p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {summary.winnerId ? `${summary.winnerLabel} 승리` : "무승부"}
          </p>
          <p className="text-xs text-night-400">
            종료 사유: {reasonLabel} · {new Date(summary.finishedAt).toLocaleTimeString("ko-KR")}
          </p>
        </div>
        <div className="text-right text-xs text-night-400">
          {summary.targetNumber !== null && summary.targetNumber !== undefined && (
            <p>
              목표값 <span className="font-semibold text-white">{summary.targetNumber}</span>
            </p>
          )}
          {summary.optimalCost !== null && summary.optimalCost !== undefined && (
            <p>
              최적 코스트 ≤ <span className="font-semibold text-white">{summary.optimalCost}</span>
            </p>
          )}
          <p className="mt-1 text-night-500">{summary.matchup}</p>
        </div>
      </div>
      {summary.winnerExpression && (
        <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-50">
          <p className="text-xs uppercase tracking-[0.3em] text-amber-200/80">Winner Expression</p>
          <p className="mt-2 font-mono text-lg text-white">{summary.winnerExpression}</p>
          {typeof summary.winnerOperatorCount === "number" && (
            <p className="text-xs text-amber-200/80">연산기호 {summary.winnerOperatorCount}개</p>
          )}
          {summary.winnerSubmittedAt && (
            <p className="text-[11px] text-amber-200/60">
              제출 시각 {new Date(summary.winnerSubmittedAt).toLocaleTimeString("ko-KR")}
            </p>
          )}
        </div>
      )}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {players.map((player) => {
          const stats = computeHistoryStats(player.history);
          return (
            <div key={player.key} className="rounded-2xl border border-night-800/70 bg-night-900/50 p-4">
              <div className="flex items-center justify-between">
                <p className="text-lg font-semibold text-white">{player.label}</p>
                <p className="text-xs text-night-400">시도 {stats.attempts}회</p>
              </div>
              {stats.bestEntry ? (
                <div className="mt-3 rounded-xl border border-night-800/60 bg-night-950/40 p-3 text-xs">
                  <p className="text-night-400">최소 연산기호</p>
                  <p className="mt-1 font-mono text-base text-white">{stats.bestEntry.expression}</p>
                  <p className="text-[11px] text-night-500">연산기호 {stats.bestEntry.operatorCount}개</p>
                </div>
              ) : (
                <p className="mt-3 text-xs text-night-500">기록이 없습니다.</p>
              )}
              {typeof stats.averageOperatorCount === "number" && (
                <p className="mt-2 text-xs text-night-400">
                  평균 연산기호 {stats.averageOperatorCount}개
                </p>
              )}
              <div className="mt-3 max-h-40 space-y-2 overflow-y-auto pr-1 text-xs">
                {player.history.length === 0 && (
                  <p className="text-night-500">최근 제출 기록이 없습니다.</p>
                )}
                {player.history
                  .slice(-5)
                  .reverse()
                  .map((entry, index) => (
                    <div
                      key={`${entry.timestamp}-${index}`}
                      className="rounded-lg border border-night-800/60 bg-night-950/30 p-2"
                    >
                      <p className="font-semibold text-white">{entry.expression}</p>
                      <p className="text-[11px] text-night-500">연산기호 {entry.operatorCount}개</p>
                    </div>
                  ))}
              </div>
            </div>
          );
        })}
      </div>
      {roomClosedReason && <p className="mt-3 text-xs text-night-500">{roomClosedReason}</p>}
      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onReturn}
          className="rounded-xl border border-indigo-500/60 px-4 py-2 text-sm font-semibold text-indigo-100 transition hover:border-indigo-400"
        >
          로비로 돌아가기
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl border border-night-700 px-4 py-2 text-sm font-semibold text-night-100 transition hover:border-night-500"
        >
          요약 닫기
        </button>
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

