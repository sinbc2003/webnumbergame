"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { getRuntimeConfig } from "@/lib/runtimeConfig";

type LobbyMessage = {
  id: string;
  user: string;
  userId: string;
  message: string;
  timestamp: string;
  clientId?: string;
};

type LobbyUser = {
  user_id: string;
  username: string;
};

interface LobbyContextValue {
  messages: LobbyMessage[];
  roster: LobbyUser[];
  connected: boolean;
  sendMessage: (text: string) => void;
}

const LobbyContext = createContext<LobbyContextValue>({
  messages: [],
  roster: [],
  connected: false,
  sendMessage: () => {},
});

const resolveWsBase = () => {
  const { wsBase, apiBase } = getRuntimeConfig();
  if (wsBase) return wsBase;
  const trimmed = apiBase.replace(/\/api$/, "");
  return trimmed.replace(/^http/, "ws");
};

export function LobbyProvider({ children }: { children: React.ReactNode }) {
  const { user, token } = useAuth();
  const [messages, setMessages] = useState<LobbyMessage[]>([]);
  const [roster, setRoster] = useState<LobbyUser[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!user || !token) {
      setConnected(false);
      setMessages([]);
      setRoster([]);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    const wsBase = resolveWsBase();
    const url = new URL(`${wsBase}/ws/lobby`);
    url.searchParams.set("token", token);

    const socket = new WebSocket(url.toString());
    wsRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => {
      setConnected(false);
      wsRef.current = null;
    };
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "chat") {
          if (payload.client_id && pendingIdsRef.current.has(payload.client_id)) {
            pendingIdsRef.current.delete(payload.client_id);
            return;
          }
          const entry: LobbyMessage = {
            id: `${payload.timestamp ?? Date.now()}-${payload.user_id ?? Math.random()}`,
            user: payload.user ?? "Unknown",
            userId: payload.user_id ?? "unknown",
            message: payload.message ?? "",
            timestamp: payload.timestamp ?? new Date().toISOString(),
            clientId: payload.client_id,
          };
          setMessages((prev) => [...prev.slice(-99), entry]);
        } else if (payload.type === "roster" && Array.isArray(payload.users)) {
          setRoster(
            payload.users
              .filter((item: LobbyUser) => Boolean(item?.user_id && item?.username))
              .map((item: LobbyUser) => ({
                user_id: item.user_id,
                username: item.username,
              })),
          );
        }
      } catch {
        // ignore malformed events
      }
    };

    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [token, user]);

  const sendMessage = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }
    const clientId =
      typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `local-${Date.now()}`;
    pendingIdsRef.current.add(clientId);
    setMessages((prev) => [
      ...prev.slice(-99),
      {
        id: clientId,
        user: user?.username ?? "나",
        userId: user?.id ?? "me",
        message: trimmed,
        timestamp: new Date().toISOString(),
        clientId,
      },
    ]);
    wsRef.current.send(
      JSON.stringify({
        type: "chat",
        message: trimmed,
        client_id: clientId,
      }),
    );
  };

  const value = useMemo(
    () => ({
      messages,
      roster,
      connected,
      sendMessage,
    }),
    [connected, messages, roster],
  );

  return <LobbyContext.Provider value={value}>{children}</LobbyContext.Provider>;
}

export const useLobby = () => useContext(LobbyContext);


