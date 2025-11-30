"use client";

import { useState } from "react";

import { useAuth } from "@/hooks/useAuth";

interface Props {
  mode: "login" | "register";
}

export default function AuthForm({ mode }: Props) {
  const { login, register, loading } = useAuth();
  const [nickname, setNickname] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      if (mode === "login") {
        await login(nickname);
      } else {
        await register(nickname);
      }
      setMessage("입장되었습니다! 상단 메뉴에서 원하는 화면으로 이동해 주세요.");
    } catch (error: any) {
      setMessage(error?.response?.data?.detail ?? "요청에 실패했습니다.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card max-w-md space-y-4">
      <h1 className="text-2xl font-semibold text-white">닉네임으로 입장</h1>
      <p className="text-sm text-night-400">
        회원가입 없이 사용할 닉네임만 입력하면 바로 게임에 참여할 수 있습니다.
      </p>
      <label className="block text-sm text-night-300">
        닉네임
        <input
          type="text"
          required
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        />
      </label>
      {message && <p className="text-sm text-night-300">{message}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-indigo-500 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-40"
      >
        {loading ? "입장 중..." : "입장하기"}
      </button>
      <p className="text-center text-sm text-night-400">
        다른 기기에서 다시 접속할 때도 같은 닉네임을 입력하면 이어서 이용할 수 있습니다.
      </p>
    </form>
  );
}

