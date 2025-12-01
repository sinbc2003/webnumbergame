"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import api from "@/lib/api";
import type { Tournament } from "@/types/api";

export default function TournamentForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slots, setSlots] = useState(8);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      const { data } = await api.post<Tournament>("/tournaments", {
        name,
        participant_slots: slots
      });
      setMessage("토너먼트가 생성되었습니다.");
      router.push(`/tournaments/${data.id}`);
    } catch (error: any) {
      setMessage(error?.response?.data?.detail ?? "생성에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-4">
      <h2 className="text-lg font-semibold text-white">토너먼트 생성</h2>
      <label className="block text-sm text-night-300">
        이름
      <label className="block text-sm text-night-300">
        참가 슬롯
        <select
          value={slots}
          onChange={(e) => setSlots(Number(e.target.value))}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        >
          {[4, 8, 16, 32].map((size) => (
            <option key={size} value={size}>
              {size}명
            </option>
          ))}
        </select>
      </label>
        <input
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        />
      </label>
      {message && <p className="text-sm text-night-300">{message}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-indigo-500 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-40"
      >
        {loading ? "생성 중..." : "생성하기"}
      </button>
    </form>
  );
}

