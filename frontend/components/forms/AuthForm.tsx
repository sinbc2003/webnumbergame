"use client";

import { useState } from "react";
import Link from "next/link";

import { useAuth } from "@/hooks/useAuth";

interface Props {
  mode: "login" | "register";
}

export default function AuthForm({ mode }: Props) {
  const { login, register, loading } = useAuth();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, username, password);
      }
      setMessage("완료되었습니다! 상단 메뉴에서 이동해 주세요.");
    } catch (error: any) {
      setMessage(error?.response?.data?.detail ?? "요청에 실패했습니다.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card max-w-md space-y-4">
      <h1 className="text-2xl font-semibold text-white">
        {mode === "login" ? "로그인" : "회원가입"}
      </h1>
      <label className="block text-sm text-night-300">
        이메일
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        />
      </label>
      {mode === "register" && (
        <label className="block text-sm text-night-300">
          사용자 이름
          <input
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
          />
        </label>
      )}
      <label className="block text-sm text-night-300">
        비밀번호
        <input
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
        />
      </label>
      {message && <p className="text-sm text-night-300">{message}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-indigo-500 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-40"
      >
        {loading ? "처리 중..." : mode === "login" ? "로그인" : "회원가입"}
      </button>
      <p className="text-center text-sm text-night-400">
        {mode === "login" ? (
          <>
            처음 오셨나요? <Link href="/register" className="text-indigo-400">회원가입</Link>
          </>
        ) : (
          <>
            이미 계정이 있나요? <Link href="/login" className="text-indigo-400">로그인</Link>
          </>
        )}
      </p>
    </form>
  );
}

