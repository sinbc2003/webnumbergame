"use client";

import { useCallback, useEffect, useState } from "react";

import RoomGamePanel from "./RoomGamePanel";
import RoomRealtimePanel from "./RoomRealtimePanel";
import type { Participant, Room } from "@/types/api";

interface Props {
  room: Room;
  participants: Participant[];
}

export default function RoomPageShell({ room, participants }: Props) {
  const [focusMode, setFocusMode] = useState(false);

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
    <div className={focusMode ? "" : "grid gap-6 lg:grid-cols-[2.2fr,1fr]"}>
      <section>
        <RoomGamePanel room={room} participants={participants} onPlayerFocusChange={handleFocusChange} />
      </section>
      {!focusMode && (
        <section>
          <RoomRealtimePanel room={room} participants={participants} />
        </section>
      )}
    </div>
  );
}


