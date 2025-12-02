"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";

import { useAuth } from "@/hooks/useAuth";
import { useLobby } from "@/hooks/useLobby";

type NavButton = {
  id: string;
  label: string;
  hint: string;
  href?: string;
  action?: "quit";
};

const NAV_BUTTONS: NavButton[] = [
  { id: "channel", label: "Channel", hint: "HOME", href: "/dashboard" },
  { id: "rooms", label: "Rooms", hint: "MATCH", href: "/rooms" },
  { id: "forge", label: "Forge", hint: "BUILD", href: "/tournaments/create" },
  { id: "league", label: "League", hint: "RANK", href: "/tournaments" },
  { id: "quit", label: "Quit", hint: "EXIT", action: "quit" },
];

const ADMIN_BUTTON: NavButton = { id: "ops", label: "Ops", hint: "ADMIN", href: "/admin" };
const BADGE_SEQUENCE = ["gm", "diamond", "platinum", "gold", "silver", "bronze"];

interface Props {
  children: ReactNode;
  pageTitle?: string;
  description?: string;
}

const formatTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--:--";
  }
  return date.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
};

export default function MathNetworkShell({ children, pageTitle = "MathGame Command", description }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { messages, roster, connected, sendMessage } = useLobby();
  const [chatInput, setChatInput] = useState("");
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages]);

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

  const decoratedRoster = useMemo(() => {
    if (!roster.length) return [];
    return roster.map((entry, index) => {
      const badge = BADGE_SEQUENCE[index % BADGE_SEQUENCE.length];
      const signal = (entry.username?.charCodeAt(0) ?? index) % 4;
      return {
        ...entry,
        badge,
        signal: signal + 1,
      };
    });
  }, [roster]);

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

  const handleChatSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!chatInput.trim()) return;
    sendMessage(chatInput);
    setChatInput("");
  };

  return (
    <div className="bnet-shell">
      <div className="bnet-frame">
        <header className="bnet-header">
          <div>
            <p className="bnet-logo">MATHGAME</p>
            <p className="bnet-subtitle">REALTIME NETWORK COMMAND</p>
          </div>
          <div className="bnet-banner">
            <p>MathGame 시즌 이벤트</p>
            <span>랭크전 OPEN</span>
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
                  <p className="bnet-console__desc">{description ?? "채널 MathNet-01 연결됨 · 전체 채팅 활성화"}</p>
                </div>
                <div className={clsx("bnet-console__chip", connected ? "chip-online" : "chip-offline")}>
                  {connected ? "CHANNEL ONLINE" : "CONNECTING"}
                </div>
              </div>
              <div className="bnet-chat">
                <div className="bnet-chat__log" ref={chatScrollRef}>
                  {messages.length === 0 ? (
                    <p className="bnet-chat__placeholder">아직 메시지가 없습니다. 첫 채팅을 입력해 보세요.</p>
                  ) : (
                    messages.map((entry) => (
                      <div key={entry.id} className="bnet-chat__line">
                        <span className="bnet-chat__time">{formatTime(entry.timestamp)}</span>
                        <span className="bnet-chat__author">{entry.user}</span>
                        <span className="bnet-chat__message">{entry.message}</span>
                      </div>
                    ))
                  )}
                </div>
                <form className="bnet-chat__form" onSubmit={handleChatSubmit}>
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(event) => setChatInput(event.target.value)}
                    placeholder={connected ? "채널에 메시지 보내기" : "연결 중..."}
                    disabled={!connected}
                  />
                  <button type="submit" disabled={!connected || !chatInput.trim()}>
                    Send
                  </button>
                </form>
              </div>
            </section>
            <section className="bnet-content">{children}</section>
          </main>
          <aside className="bnet-roster">
            <div className="bnet-roster__title">
              MathGame Ladder <span>({decoratedRoster.length || 0})</span>
            </div>
            <ul className="bnet-roster__list">
              {decoratedRoster.length === 0 && <li className="bnet-roster__empty">접속 중인 사령관이 없습니다.</li>}
              {decoratedRoster.map((player) => (
                <li key={player.user_id} className="bnet-roster__item">
                  <div>
                    <p className="bnet-roster__name">{player.username}</p>
                    <p className="bnet-roster__clan">{player.user_id.slice(0, 8)}</p>
                  </div>
                  <div className="bnet-roster__meta">
                    <span className={clsx("bnet-roster__badge", `badge-${player.badge}`)} />
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
        <footer className="bnet-footer">© 2025 MathGame Command · Build stable/14.2.14</footer>
      </div>
    </div>
  );
}

