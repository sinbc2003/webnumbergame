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
  const isRegisterMode = mode === "register";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [username, setUsername] = useState("");
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
        return;
      }

      const trimmedEmail = email.trim();
      if (!trimmedEmail) {
        setMessage("이메일을 입력해 주세요.");
        return;
      }
      if (!password) {
        setMessage("비밀번호를 입력해 주세요.");
        return;
      }

      if (isRegisterMode) {
        const trimmedUsername = username.trim();
        if (!trimmedUsername) {
          setMessage("닉네임을 입력해 주세요.");
          return;
        }
        if (password !== confirmPassword) {
          setMessage("비밀번호가 일치하지 않습니다.");
          return;
        }
        await register({
          email: trimmedEmail,
          username: trimmedUsername,
          password,
        });
      } else {
        await login({
          email: trimmedEmail,
          password,
        });
      }
      router.push("/dashboard");
    } catch (error: any) {
      setMessage(error?.response?.data?.detail ?? "요청에 실패했습니다.");
    }
  };

  const renderAuthFields = () => {
    if (isAdminMode) {
      return (
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
      );
    }

    return (
      <>
        {isRegisterMode && (
          <label className="block text-sm text-night-300">
            닉네임
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
          이메일
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
          />
        </label>
        <label className="block text-sm text-night-300">
          비밀번호
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
          />
        </label>
        {isRegisterMode && (
          <label className="block text-sm text-night-300">
            비밀번호 확인
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-night-700 bg-night-950/70 p-2 text-white"
            />
          </label>
        )}
      </>
    );
  };

  return (
    <form onSubmit={handleSubmit} className="card max-w-md space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">
          {isAdminMode ? "관리자 로그인" : isRegisterMode ? "회원가입" : "로그인"}
        </h1>
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
      ) : isRegisterMode ? (
        <p className="text-sm text-night-400">이메일과 비밀번호, 사용할 닉네임을 입력하면 계정이 생성됩니다.</p>
      ) : (
        <p className="text-sm text-night-400">이메일과 비밀번호로 로그인해 게임 진행 상황을 저장하세요.</p>
      )}

      {renderAuthFields()}

      {message && <p className="text-sm text-night-300">{message}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-indigo-500 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-40"
      >
        {loading ? "처리 중..." : isAdminMode ? "관리자 접속" : isRegisterMode ? "회원가입" : "로그인"}
      </button>
    </form>
  );
}

