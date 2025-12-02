"use client";

import { useMemo } from "react";
import type { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";

import { useAuth } from "@/hooks/useAuth";

type NavButton = {
  id: string;
  label: string;
  hint: string;
  href?: string;
  action?: "quit";
};

const NAV_BUTTONS: NavButton[] = [
  { id: "channel", label: "Channel", hint: "KOR-1", href: "/dashboard" },
  { id: "friends", label: "Friends", hint: "COMMS", href: "/rooms" },
  { id: "create", label: "Create", hint: "OPS", href: "/tournaments/create" },
  { id: "join", label: "Join", hint: "MATCH", href: "/rooms" },
  { id: "league", label: "League", hint: "RANK", href: "/tournaments" },
  { id: "quit", label: "Quit", hint: "EXIT", action: "quit" }
];

const ADMIN_BUTTON: NavButton = { id: "ops", label: "Ops", hint: "ADMIN", href: "/admin" };

const ROSTER_PRESET = [
  { name: "IllltoSsIlllll", clan: "9990", rank: "gm", signal: 4 },
  { name: "Dunhil[joa]", clan: "S2", rank: "diamond", signal: 4 },
  { name: "SinBu-N.SJ[S2]", clan: "S2", rank: "diamond", signal: 3 },
  { name: "Oppa", clan: "CASL", rank: "platinum", signal: 3 },
  { name: "pol.bbo", clan: "GDI", rank: "gold", signal: 2 },
  { name: "Gore777.a010", clan: "DMG", rank: "silver", signal: 4 },
  { name: "okbarigirl", clan: "S.C", rank: "gold", signal: 3 },
  { name: "1041503", clan: "N/A", rank: "bronze", signal: 2 },
  { name: "Kristy", clan: "GG", rank: "gold", signal: 3 },
  { name: "Gore777.a002", clan: "DMG", rank: "silver", signal: 2 }
];

interface Props {
  children: ReactNode;
  pageTitle?: string;
  description?: string;
  logLines?: string[];
}

export default function BattleNetShell({ children, pageTitle = "Sunken Warriors", description, logLines }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const navButtons = useMemo(() => {
    if (user?.is_admin) {
      const base = [...NAV_BUTTONS];
      const quitIndex = base.findIndex((button) => button.action === "quit");
      const insertionIndex = quitIndex === -1 ? base.length : quitIndex;
      base.splice(insertionIndex, 0, ADMIN_BUTTON);
      return base;
    }
    return NAV_BUTTONS;
  }, [user?.is_admin]);

  const stats = useMemo(() => {
    const now = new Date();
    const usersOnline = 29151 + now.getMinutes() * 11;
    const activeGames = 6700 + (now.getSeconds() % 30) * 7;
    const lastCheck = now.toLocaleString("ko-KR", {
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit"
    });
    return { usersOnline, activeGames, lastCheck };
  }, []);

  const roster = useMemo(() => {
    if (!user) return ROSTER_PRESET;
    const copy = [...ROSTER_PRESET];
    copy.splice(2, 0, {
      name: user.username,
      clan: user.is_admin ? "OPS" : "ALLY",
      rank: user.is_admin ? "gm" : "diamond",
      signal: 4
    });
    return copy.slice(0, 10);
  }, [user]);

  const computedLog = useMemo(() => {
    if (logLines && logLines.length > 0) {
      return logLines;
    }
    return [
      "이 서버는 Kor-Net에서 호스팅합니다.",
      `현재: ${stats.usersOnline.toLocaleString()} 사용자가 ${stats.activeGames}게임을 플레이하고 있습니다.`,
      "기본 채널에서 도배 방지를 위해 일부 채팅 기능이 제한됩니다.",
      `Joining channel: ${pageTitle}`,
      description ? description : "사령부 데이터 동기화 중...",
      user ? `<${user.username}> 접속 승인됨.` : "게스트 모드로 접속되었습니다.",
      "미소랜드 길드모집합니다 Ch : Op Ms-"
    ];
  }, [description, logLines, pageTitle, stats, user]);

  const handleQuit = () => {
    if (user) {
      logout();
    }
    router.push("/login");
  };

  const handleNavigate = (button: NavButton) => {
    if (button.action === "quit") {
      handleQuit();
      return;
    }
    if (button.href) {
      router.push(button.href);
    }
  };

  return (
    <div className="bnet-shell">
      <div className="bnet-frame">
        <header className="bnet-header">
          <div>
            <p className="bnet-logo">STARCRAFT</p>
            <p className="bnet-subtitle">BROOD WAR COMMAND CONSOLE</p>
          </div>
          <div className="bnet-banner">
            <p>월드 오브 워크래프트 - 불타는 성전</p>
            <span>지금 사전등록</span>
          </div>
        </header>
        <div className="bnet-body">
          <aside className="bnet-menu">
            {navButtons.map((button) => {
              const isActive = button.href ? pathname.startsWith(button.href) : false;
              return (
                <button
                  key={button.id}
                  type="button"
                  onClick={() => handleNavigate(button)}
                  className={clsx("bnet-button", isActive && "bnet-button--active", button.action === "quit" && "bnet-button--alert")}
                >
                  <span>{button.label}</span>
                  <span className="bnet-button__hint">{button.hint}</span>
                </button>
              );
            })}
          </aside>
          <main className="bnet-main">
            <section className="bnet-console">
              <div className="bnet-console__header">
                <div>
                  <p className="bnet-console__title">{pageTitle}</p>
                  <p className="bnet-console__desc">
                    {description ?? "사령부 연결 상태 양호 · LATENCY GREEN"}
                  </p>
                </div>
                <div className="bnet-console__chip">
                  {user ? `ID ${user.username}` : "Guest Access"}
                </div>
              </div>
              <div className="bnet-console__log">
                {computedLog.map((line, index) => (
                  <p key={`${line}-${index}`} className="crt-text">
                    {line}
                  </p>
                ))}
                <p className="bnet-console__timestamp">Last check · {stats.lastCheck}</p>
              </div>
            </section>
            <section className="bnet-content">{children}</section>
          </main>
          <aside className="bnet-roster">
            <div className="bnet-roster__title">
              Brood War Ladder <span>(89)</span>
            </div>
            <ul className="bnet-roster__list">
              {roster.map((player) => (
                <li key={`${player.name}-${player.clan}`} className="bnet-roster__item">
                  <div>
                    <p className="bnet-roster__name">{player.name}</p>
                    <p className="bnet-roster__clan">{player.clan}</p>
                  </div>
                  <div className="bnet-roster__meta">
                    <span className={clsx("bnet-roster__badge", `badge-${player.rank}`)} />
                    <div className="bnet-roster__signal">
                      {Array.from({ length: 4 }).map((_, index) => (
                        <span key={index} className={clsx("bar", index < player.signal && "active")} />
                      ))}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
            <button type="button" className="bnet-roster__cta">
              Whisper
            </button>
          </aside>
        </div>
        <footer className="bnet-footer">© 2000-2025 Kor-Net Command Center · Build stable/14.2.14</footer>
      </div>
    </div>
  );
}

