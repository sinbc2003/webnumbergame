"use client";

import { useCallback, useState } from "react";

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


