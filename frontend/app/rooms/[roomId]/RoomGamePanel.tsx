"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import useSWR from "swr";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import type { ActiveMatch, RoundType } from "@/types/api";

interface Props {
  roomId: string;
  roundType: RoundType;
}

const resolveWsBase = () => {
  const { wsBase, apiBase } = getRuntimeConfig();
  if (wsBase) {
    return wsBase;
  }
  const trimmed = apiBase.replace(/\/api$/, "");
  return trimmed.replace(/^http/, "ws");
};

export default function RoomGamePanel({ roomId, roundType }: Props) {
  const { user } = useAuth();
  const [expression, setExpression] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);

  const fetcher = async (url: string) => {
    const { data } = await api.get<ActiveMatch | null>(url);
    return data;
  };

  const { data, mutate, isLoading } = useSWR(user ? `/rooms/${roomId}/active-match` : null, fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true
  });

  const wsUrl = useMemo(() => `${resolveWsBase()}/ws/rooms/${roomId}`, [roomId]);

  useEffect(() => {
    if (!user) return;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string };
        if (
          payload.type === "round_started" ||
          payload.type === "round_finished" ||
          payload.type === "problem_advanced"
        ) {
          mutate();
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

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!expression.trim()) {
      setError("식을 입력해 주세요.");
      return;
    }
    setMessage(null);
    setError(null);
    try {
      await api.post(`/rooms/${roomId}/submit`, {
        expression,
        mode: roundType,
        team_label: null
      });
      setExpression("");
      setMessage("제출했습니다! 결과를 기다려 주세요.");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "제출 중 오류가 발생했습니다.");
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

  return (
    <div className="card space-y-4">
      <h2 className="text-lg font-semibold text-white">게임 진행</h2>

      {!user && <p className="text-sm text-night-400">로그인 후 이용할 수 있습니다.</p>}

      {user && !data && !isLoading && (
        <p className="text-sm text-night-400">진행 중인 라운드가 없습니다. 방장이 라운드를 시작하면 여기에 표시됩니다.</p>
      )}

      {user && data && (
        <>
          <div className="grid gap-3 rounded-lg border border-night-800/60 bg-night-950/40 p-4 text-sm text-night-200 sm:grid-cols-2">
            <div>
              <p className="text-night-500">현재 문제</p>
              <p className="text-2xl font-bold text-white">{data.target_number}</p>
            </div>
            <div>
              <p className="text-night-500">남은 시간</p>
              <p className="text-2xl font-bold text-indigo-400">{formatRemaining()}</p>
            </div>
            <div>
              <p className="text-night-500">최적 코스트</p>
              <p className="text-xl font-semibold text-night-100">{data.optimal_cost}</p>
            </div>
            <div>
              <p className="text-night-500">문제 진행도</p>
              <p className="text-xl font-semibold text-night-100">
                {data.current_index + 1} / {data.total_problems}
              </p>
            </div>
          </div>

          <div className="space-y-2 rounded-lg border border-night-800/60 bg-night-950/30 p-4 text-xs text-night-300">
            <p className="font-semibold text-night-200">이번 라운드 문제 목록</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {data.problems.map((problem) => (
                <div
                  key={`${problem.target_number}-${problem.index}`}
                  className={`rounded-md border px-3 py-2 ${
                    problem.index === data.current_index
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

          <form onSubmit={handleSubmit} className="space-y-3">
            <label className="block text-sm text-night-300">
              <span className="mb-1 block text-night-400">수식을 입력하세요</span>
              <input
                type="text"
                value={expression}
                onChange={(e) => setExpression(e.target.value)}
                placeholder="예: (1+2)*3"
                className="w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
              />
            </label>
            {error && <p className="text-sm text-red-400">{error}</p>}
            {message && <p className="text-sm text-green-400">{message}</p>}
            <button
              type="submit"
              disabled={!expression.trim()}
              className="w-full rounded-md bg-indigo-600 py-2 font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700"
            >
              제출하기
            </button>
          </form>
        </>
      )}
    </div>
  );
}


