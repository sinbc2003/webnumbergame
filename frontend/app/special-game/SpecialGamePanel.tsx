"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import api from "@/lib/api";
import type { SpecialGameContext, SpecialGameSubmissionResponse } from "@/types/api";

export default function SpecialGamePanel() {
  const [context, setContext] = useState<SpecialGameContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expression, setExpression] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [highlightSuccess, setHighlightSuccess] = useState<boolean | null>(null);

  const config = context?.config ?? null;
  const leaderboard = context?.leaderboard ?? [];

  const fetchContext = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<SpecialGameContext>("/special-game/context");
      setContext(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "스페셜 게임 정보를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  const bestRecord = useMemo(() => leaderboard[0], [leaderboard]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!config) {
      setFeedback("아직 스페셜 게임 문제가 설정되지 않았습니다.");
      setHighlightSuccess(false);
      return;
    }
    if (!expression.trim()) {
      setFeedback("수식을 입력해 주세요.");
      setHighlightSuccess(false);
      return;
    }
    setSubmitting(true);
    setFeedback(null);
    setHighlightSuccess(null);
    try {
      const payload = { expression };
      const { data } = await api.post<SpecialGameSubmissionResponse>("/special-game/submit", payload);
      setFeedback(data.message);
      setHighlightSuccess(data.is_record);
      setExpression("");
      await fetchContext();
    } catch (err: any) {
      setFeedback(err?.response?.data?.detail ?? "제출에 실패했습니다.");
      setHighlightSuccess(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 text-night-100">
      <section className="rounded-xl border border-night-800 bg-night-950/60 p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-night-500">SPECIAL EVENT</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">
              {config?.title ?? "Special Game 준비 중"}
            </h1>
            <p className="mt-2 text-sm text-night-400">
              1, (, ), +, -, *, ** 만 사용하여 목표 숫자를 만들고 가장 많은 기호를 활용한 지휘관이 됩니다.
            </p>
          </div>
          {config?.target_number !== undefined && config?.target_number !== null && (
            <div className="rounded-lg border border-indigo-600/40 bg-indigo-600/10 px-5 py-4 text-center">
              <p className="text-xs uppercase tracking-[0.2em] text-indigo-200">TARGET</p>
              <p className="mt-1 text-3xl font-bold text-indigo-100">{config.target_number}</p>
              {config?.optimal_cost && (
                <p className="text-xs text-indigo-200/80">기존 최적 cost: {config.optimal_cost}</p>
              )}
            </div>
          )}
        </div>
        {config?.description && (
          <p className="mt-4 rounded-md border border-night-800 bg-night-900/60 p-3 text-sm text-night-200">
            {config.description}
          </p>
        )}
        {!config && !loading && (
          <p className="mt-4 text-sm text-amber-300">
            현재 관리자가 지정한 Special Game 문제가 없습니다. 설정되면 자동으로 표시됩니다.
          </p>
        )}
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      </section>

      <section className="rounded-xl border border-night-800 bg-night-950/70 p-6">
        <h2 className="text-lg font-semibold text-white">수식 제출</h2>
        <p className="mt-1 text-sm text-night-400">거듭제곱은 ** 로 표기하며, 기호 개수가 많을수록 높은 기록입니다.</p>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <label className="block text-sm text-night-300">
            <span className="mb-2 block text-night-400">표현식</span>
            <textarea
              value={expression}
              onChange={(event) => setExpression(event.target.value)}
              rows={3}
              placeholder="예) (1+1)*(1+1+1)**2"
              className="w-full rounded-lg border border-night-800 bg-night-900 px-4 py-3 font-mono text-sm text-white placeholder:text-night-600 focus:border-indigo-500 focus:outline-none"
              disabled={submitting || !config}
              maxLength={512}
            />
          </label>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-xs text-night-500">
              허용 기호: <code className="font-mono text-night-200">1 ( ) + - * **</code>
            </div>
            <button
              type="submit"
              disabled={!config || submitting}
              className="rounded-md bg-indigo-600 px-6 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
            >
              {submitting ? "검증 중..." : "제출하기"}
            </button>
          </div>
          {feedback && (
            <p className={`text-sm ${highlightSuccess ? "text-emerald-300" : "text-amber-300"}`}>{feedback}</p>
          )}
        </form>
      </section>

      <section className="rounded-xl border border-night-800 bg-night-950/70 p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">기호 사용 리더보드</h2>
            <p className="text-sm text-night-400">
              높은 기호 수 → 같은 기호 수일 때는 먼저 달성한 기록이 우선합니다.
            </p>
          </div>
          {config?.updated_at && (
            <p className="text-xs text-night-500">
              문제 설정: {new Date(config.updated_at).toLocaleString("ko-KR")}
            </p>
          )}
        </div>
        {loading ? (
          <p className="mt-6 text-sm text-night-400">리더보드를 불러오는 중입니다...</p>
        ) : (
          <div className="mt-4 overflow-hidden rounded-lg border border-night-900">
            <table className="min-w-full divide-y divide-night-900 text-sm">
              <thead className="bg-night-900/60 text-night-400">
                <tr>
                  <th className="px-4 py-2 text-left">순위</th>
                  <th className="px-4 py-2 text-left">지휘관</th>
                  <th className="px-4 py-2 text-left">표현식</th>
                  <th className="px-4 py-2 text-left">기호 수</th>
                  <th className="px-4 py-2 text-left">기록 시각</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-night-900">
                {!leaderboard.length && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-night-500">
                      아직 등록된 기록이 없습니다. 첫 기록에 도전해 보세요!
                    </td>
                  </tr>
                )}
                {leaderboard.map((entry, index) => (
                  <tr
                    key={entry.user_id}
                    className={index === 0 ? "bg-indigo-900/10 text-indigo-100" : "text-night-100"}
                  >
                    <td className="px-4 py-3 font-semibold">#{index + 1}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium">{entry.username}</p>
                      {bestRecord?.user_id === entry.user_id && (
                        <span className="text-xs text-indigo-300">현재 최고 기록</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-night-200">
                      <span className="break-all">{entry.expression}</span>
                    </td>
                    <td className="px-4 py-3 font-semibold">{entry.symbol_count}</td>
                    <td className="px-4 py-3 text-night-400">
                      {new Date(entry.recorded_at).toLocaleString("ko-KR")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

