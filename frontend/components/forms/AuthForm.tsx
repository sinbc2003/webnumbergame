"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";

interface Props {
  mode: "login" | "register";
}

export default function AuthForm({ mode }: Props) {
  const { login, register, adminLogin, loading } = useAuth();
  const router = useRouter();
  const [nickname, setNickname] = useState("");
  const [isAdminMode, setIsAdminMode] = useState(false);
  const [adminId, setAdminId] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      if (isAdminMode) {
        if (!adminId.trim() || !adminPassword.trim()) {
          setMessage("관리자 아이디와 비밀번호를 입력해 주세요.");
          return;
        }
        await adminLogin(adminId.trim(), adminPassword);
        router.push("/admin");
      } else if (mode === "login") {
        await login(nickname);
      } else {
        await register(nickname);
      }
      if (!isAdminMode) {
        router.push("/dashboard");
      }
    } catch (error: any) {
      setMessage(error?.response?.data?.detail ?? "요청에 실패했습니다.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card max-w-md space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">{isAdminMode ? "관리자 로그인" : "닉네임으로 입장"}</h1>
        <button
          type="button"
          onClick={() => {
            setIsAdminMode((prev) => !prev);
            setMessage(null);
          }}
          className="text-xs text-indigo-300 underline"
        >
          {isAdminMode ? "일반 모드" : "관리자 모드"}
        </button>
      </div>
      {isAdminMode ? (
        <p className="text-sm text-night-400">관리자 계정으로 접속하려면 아이디와 비밀번호를 입력하세요.</p>
      ) : (
        <p className="text-sm text-night-400">회원가입 없이 사용할 닉네임만 입력하면 바로 게임에 참여할 수 있습니다.</p>
      )}

      {isAdminMode ? (
        <>
          <label className="block text-sm text-night-300">
            관리자 아이디
            <input
              type="text"
              required
              value={adminId}
              onChange={(e) => setAdminId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
            />
          </label>
          <label className="block text-sm text-night-300">
            비밀번호
            <input
              type="password"
              required
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
            />
          </label>
        </>
      ) : (
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
      )}
      {message && <p className="text-sm text-night-300">{message}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-indigo-500 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-40"
      >
        {loading ? "처리 중..." : isAdminMode ? "관리자 접속" : "입장하기"}
      </button>
      {!isAdminMode && (
        <p className="text-center text-sm text-night-400">
          다른 기기에서 다시 접속할 때도 같은 닉네임을 입력하면 이어서 이용할 수 있습니다.
        </p>
      )}
    </form>
  );
}

