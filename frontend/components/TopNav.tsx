"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";

import { useAuth } from "@/hooks/useAuth";

const baseLinks = [
  { href: "/dashboard", label: "대시보드" },
  { href: "/rooms", label: "게임방" },
  { href: "/tournaments", label: "토너먼트" }
];

export default function TopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const links = [...baseLinks];
  if (user?.is_admin) {
    links.push({ href: "/admin", label: "관리자" });
  }

  return (
    <header className="sticky top-0 z-30 bg-night-950/80 backdrop-blur border-b border-night-800">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight text-white">
          숫자게임 플랫폼
        </Link>
        <nav className="flex items-center gap-6 text-sm font-medium text-night-200">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={clsx(
                "transition-colors hover:text-white",
                pathname === link.href && "text-white"
              )}
            >
              {link.label}
            </Link>
          ))}
          {user ? (
            <button
              onClick={handleLogout}
              className="rounded-full border border-night-700 px-3 py-1 text-xs text-night-100 transition hover:border-night-500 hover:text-white"
            >
              로그아웃
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="rounded-full border border-night-700 px-3 py-1 text-xs text-night-100 transition hover:border-night-500 hover:text-white"
              >
                로그인
              </Link>
              <Link
                href="/register"
                className="rounded-full border border-indigo-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-indigo-500"
              >
                회원가입
              </Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}

