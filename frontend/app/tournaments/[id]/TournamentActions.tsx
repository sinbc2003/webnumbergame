"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import type { TournamentSlot } from "@/types/api";

interface Props {
  tournamentId: string;
  slots: TournamentSlot[];
}

export default function TournamentActions({ tournamentId, slots }: Props) {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const filled = slots.filter((slot) => slot.user_id).length;
  const isFull = filled >= 16;
  const joined = user ? slots.some((slot) => slot.user_id === user.id) : false;

  const handleJoin = async () => {
    if (!user) {
      router.push("/login");
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      await api.post(`/tournaments/${tournamentId}/join`, {});
      setMessage("참가 신청이 완료되었습니다.");
      router.refresh();
    } catch (err: any) {
      setMessage(err?.response?.data?.detail ?? "참가에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return <p className="text-sm text-night-400">로그인 후 참가할 수 있습니다.</p>;
  }

  if (joined) {
    return <p className="text-sm text-night-300">이미 이 토너먼트에 참가했습니다.</p>;
  }

  if (isFull) {
    return <p className="text-sm text-night-400">참가 인원이 가득 찼습니다.</p>;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-night-300">현재 참가 인원 {filled} / 16</p>
      <button
        type="button"
        disabled={loading}
        onClick={handleJoin}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:bg-night-700"
      >
        {loading ? "참가 신청 중..." : "토너먼트 참가"}
      </button>
      {message && <p className="text-xs text-night-400">{message}</p>}
    </div>
  );
}


