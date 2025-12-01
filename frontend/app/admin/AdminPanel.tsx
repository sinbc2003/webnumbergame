"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import type { Problem, ResetSummary } from "@/types/api";

const roundTypeLabels: Record<string, string> = {
  round1_individual: "1라운드 개인전",
  round2_team: "2라운드 팀전"
};

const initialForm = {
  round_type: "round1_individual",
  target_number: 50,
  optimal_cost: 10
};

export default function AdminPanel() {
  const { user } = useAuth();
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [resetResult, setResetResult] = useState<ResetSummary | null>(null);

  const fetchProblems = async () => {
    if (!user?.is_admin) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Problem[]>("/admin/problems");
      setProblems(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "문제 목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProblems();
  }, [user?.is_admin]);

  if (!user) {
    return <p className="text-night-300">로그인이 필요합니다.</p>;
  }

  if (!user.is_admin) {
    return <p className="text-night-300">관리자만 접근할 수 있습니다.</p>;
  }

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      await api.post("/admin/problems", {
        round_type: form.round_type,
        target_number: Number(form.target_number),
        optimal_cost: Number(form.optimal_cost)
      });
      setSuccess("문제를 추가했습니다.");
      setForm(initialForm);
      fetchProblems();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "문제를 추가하지 못했습니다.");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("해당 문제를 삭제할까요?")) return;
    setError(null);
    try {
      await api.delete(`/admin/problems/${id}`);
      setProblems((prev) => prev.filter((p) => p.id !== id));
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "삭제에 실패했습니다.");
    }
  };

  const handleReset = async () => {
    if (!confirm("모든 방/매치 데이터를 초기화할까요? 이 작업은 되돌릴 수 없습니다.")) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      const { data } = await api.post<ResetSummary>("/admin/reset");
      setResetResult(data);
      setSuccess("데이터를 초기화했습니다.");
      fetchProblems();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "초기화에 실패했습니다.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-night-800 bg-night-950/50 p-5">
        <h2 className="text-lg font-semibold text-white">문제 등록</h2>
        <form onSubmit={handleSubmit} className="mt-4 grid gap-4 sm:grid-cols-4">
          <label className="text-sm text-night-300">
            <span className="mb-1 block text-night-400">라운드 구분</span>
            <select
              name="round_type"
              value={form.round_type}
              onChange={handleInputChange}
              className="w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
            >
              <option value="round1_individual">1라운드 개인전</option>
              <option value="round2_team">2라운드 팀전</option>
            </select>
          </label>
          <label className="text-sm text-night-300">
            <span className="mb-1 block text-night-400">목표 숫자</span>
            <input
              type="number"
              min={1}
              max={9999}
              name="target_number"
              value={form.target_number}
              onChange={handleInputChange}
              className="w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
              required
            />
          </label>
          <label className="text-sm text-night-300">
            <span className="mb-1 block text-night-400">최적 코스트</span>
            <input
              type="number"
              min={1}
              max={9999}
              name="optimal_cost"
              value={form.optimal_cost}
              onChange={handleInputChange}
              className="w-full rounded-md border border-night-800 bg-night-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
              required
            />
          </label>
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full rounded-md bg-indigo-600 py-2 font-semibold text-white transition hover:bg-indigo-500"
            >
              문제 추가
            </button>
          </div>
        </form>
        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        {success && <p className="mt-3 text-sm text-green-400">{success}</p>}
      </div>

      <div className="rounded-xl border border-night-800 bg-night-950/40 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">문제 목록</h2>
          <button
            onClick={fetchProblems}
            className="rounded-md border border-night-700 px-3 py-1 text-xs text-night-100 transition hover:border-night-500 hover:text-white"
          >
            새로고침
          </button>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm text-night-200">
            <thead>
              <tr className="border-b border-night-800 text-night-400">
                <th className="px-3 py-2">라운드</th>
                <th className="px-3 py-2">목표</th>
                <th className="px-3 py-2">최적 코스트</th>
                <th className="px-3 py-2">추가일</th>
                <th className="px-3 py-2 text-right">관리</th>
              </tr>
            </thead>
            <tbody>
              {!problems.length && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-night-500">
                    등록된 문제가 없습니다.
                  </td>
                </tr>
              )}
              {problems.map((problem) => (
                <tr key={problem.id} className="border-b border-night-900">
                  <td className="px-3 py-2">{roundTypeLabels[problem.round_type] ?? problem.round_type}</td>
                  <td className="px-3 py-2">{problem.target_number}</td>
                  <td className="px-3 py-2">{problem.optimal_cost}</td>
                  <td className="px-3 py-2 text-night-400">{new Date(problem.created_at).toLocaleString()}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => handleDelete(problem.id)}
                      className="text-xs text-red-400 transition hover:text-red-300"
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-red-900/60 bg-red-900/10 p-5 text-sm text-red-100">
        <h2 className="text-lg font-semibold text-red-200">전체 초기화</h2>
        <p className="mt-2 text-red-200">
          모든 방, 매치, 참가자, 토너먼트 데이터가 삭제됩니다. 실제 운영 중이라면 주의하세요.
        </p>
        <button
          onClick={handleReset}
          className="mt-3 rounded-md border border-red-500 px-4 py-2 text-sm font-semibold text-red-100 transition hover:bg-red-500/20"
        >
          전체 데이터 초기화
        </button>
        {resetResult && (
          <pre className="mt-3 overflow-x-auto rounded bg-night-900 p-3 text-xs text-night-200">
            {JSON.stringify(resetResult.deleted, null, 2)}
          </pre>
        )}
      </div>

      {loading && <p className="text-night-400">불러오는 중...</p>}
    </div>
  );
}


