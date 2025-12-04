"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import RoomGamePanel from "./RoomGamePanel";
import RoomRealtimePanel from "./RoomRealtimePanel";
import { useAuth } from "@/hooks/useAuth";
import type { Participant, Room } from "@/types/api";

interface Props {
  room: Room;
  participants: Participant[];
}

export default function RoomPageShell({ room, participants }: Props) {
  const [focusMode, setFocusMode] = useState(false);
  const { user } = useAuth();

  const viewerParticipant = useMemo(() => {
    if (!user?.id) return null;
    return participants.find((participant) => participant.user_id === user.id) ?? null;
  }, [participants, user?.id]);

  const isHost = user?.id === room.host_id;
  const isActivePlayer = viewerParticipant?.role === "player";
  // Hosts and assigned players keep the sidebar; pure spectators get a full-width layout.
  const showSidebar = !focusMode && (isHost || isActivePlayer);
  const layoutClass = focusMode ? "" : showSidebar ? "grid gap-6 lg:grid-cols-[2.2fr,1fr]" : "";

  const handleFocusChange = useCallback((next: boolean) => {
    setFocusMode(next);
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const className = "focus-shell-compact";
    const { body } = document;
    if (!body) return;
    if (focusMode) {
      body.classList.add(className);
    } else {
      body.classList.remove(className);
    }
    return () => {
      body.classList.remove(className);
    };
  }, [focusMode]);

  return (
    <div className={layoutClass}>
      <section>
        <RoomGamePanel room={room} participants={participants} onPlayerFocusChange={handleFocusChange} />
      </section>
      {showSidebar && (
        <section>
          <RoomRealtimePanel room={room} participants={participants} />
        </section>
      )}
    </div>
  );
}


