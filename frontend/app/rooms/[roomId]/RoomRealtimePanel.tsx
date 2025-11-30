"use client";

import { useEffect, useMemo, useState } from "react";
import { getRuntimeConfig } from "@/lib/runtimeConfig";

interface EventMessage {
  type: string;
  [key: string]: any;
}

interface Props {
  roomId: string;
  roomCode: string;
}

const resolveWsBase = () => {
  const { wsBase, apiBase } = getRuntimeConfig();
  if (wsBase) {
    return wsBase;
  }
  const trimmed = apiBase.replace(/\/api$/, "");
  return trimmed.replace(/^http/, "ws");
};

export default function RoomRealtimePanel({ roomId, roomCode }: Props) {
  const wsUrl = useMemo(() => `${resolveWsBase()}/ws/rooms/${roomId}`, [roomId]);
  const [events, setEvents] = useState<EventMessage[]>([]);

  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents((prev) => [data, ...prev].slice(0, 20));
      } catch {
        // ignore
      }
    };
    return () => ws.close();
  }, [wsUrl]);

  return (
    <div className="card space-y-3">
      <div>
        <p className="text-sm font-semibold text-night-200">참가 코드</p>
        <p className="text-2xl font-bold tracking-widest text-white">{roomCode}</p>
      </div>
      <div>
        <p className="text-sm font-semibold text-night-200">실시간 이벤트</p>
        <div className="mt-2 max-h-64 space-y-2 overflow-y-auto rounded-lg border border-night-800 bg-night-950/40 p-3 text-xs text-night-300">
          {events.length === 0 && <p>아직 이벤트가 없습니다.</p>}
          {events.map((event, index) => (
            <p key={`${event.type}-${index}`} className="flex justify-between gap-2">
              <span className="font-semibold text-night-200">{event.type}</span>
              <span className="text-right text-night-400 truncate">{JSON.stringify(event)}</span>
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

