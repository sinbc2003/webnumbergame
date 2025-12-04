"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";

interface Props {
  children: React.ReactNode;
}

export default function RequireAuth({ children }: Props) {
  const router = useRouter();
  const { user, hydrated } = useAuth();
  const [ready, setReady] = useState(() => useAuth.persist?.hasHydrated?.() ?? false);

  useEffect(() => {
    if (useAuth.persist?.hasHydrated?.()) {
      setReady(true);
      return;
    }
    const unsub = useAuth.persist?.onFinishHydration?.(() => {
      setReady(true);
    });
    return () => {
      unsub?.();
    };
  }, []);

  useEffect(() => {
    if (!hydrated && !ready) {
      return;
    }
    if (!user) {
      router.replace("/login");
    }
  }, [hydrated, ready, user, router]);

  if (!hydrated && !ready) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-sm text-night-400">
        세션 정보를 불러오는 중입니다...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-sm text-night-400">
        로그인 후 이용해 주세요.
      </div>
    );
  }

  return <>{children}</>;
}

