"use client";

import { useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import { useRouter } from "next/navigation";

import api from "@/lib/api";
import type { Room, RoundType } from "@/types/api";
import { useShellTransition } from "@/hooks/useShellTransition";

const MODE_OPTIONS: Array<{
  id: string;
  label: string;
  description: string;
  roundType: RoundType | null;
  variants?: Array<{ id: string; label: string; roundType: RoundType }>;
}> = [
  {
    id: "solo",
    label: "릴레이 개인전",
    description: "킹오브파이터식 릴레이",
    roundType: "solo_1v1",
    variants: [
      { id: "solo_1v1", label: "1 vs 1", roundType: "solo_1v1" },
      { id: "relay_2v2", label: "2 vs 2 릴레이", roundType: "relay_2v2" },
      { id: "relay_3v3", label: "3 vs 3 릴레이", roundType: "relay_3v3" },
      { id: "relay_4v4", label: "4 vs 4 릴레이", roundType: "relay_4v4" },
    ],
  },
  {
    id: "team",
    label: "팀전",
    description: "코스트 분배 협동전",
    roundType: "team_2v2",
    variants: [
      { id: "team_2v2", label: "2 vs 2", roundType: "team_2v2" },
      { id: "team_4v4", label: "4 vs 4", roundType: "team_4v4" },
    ],
  },
  { id: "tournament", label: "토너먼트", description: "1v1 싱글 브래킷", roundType: null },
];

interface Props {
  onCreated?: (room: Room) => void;
}

export default function RoomCreateBoard({ onCreated }: Props) {
  const router = useRouter();
  const [mode, setMode] = useState(MODE_OPTIONS[0]);
  const [variant, setVariant] = useState<RoundType | null>(mode.roundType);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const transition = useShellTransition();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!variant) {
      transition(() => router.push("/tournaments/create"));
      return;
    }
    setSubmitting(true);
    setStatusMessage(null);
    try {
      const payload = {
        name: name.trim() || `[${size.label}] 커스텀 방`,
        description: `${mode.label} · ${size.label}${description ? ` · ${description.trim()}` : ""}`,
        round_type: variant,
      };
      const { data } = await api.post<Room>("/rooms", payload);
      onCreated?.(data);
      setStatusMessage("방이 생성되었습니다.");
      transition(() => router.push(`/rooms/${data.id}`));
    } catch (error: any) {
      setStatusMessage(error?.response?.data?.detail ?? "방 생성에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="room-create">
      <div className="room-create__panel">
        <p className="room-create__title">게임 모드</p>
        <div className="room-create__modes">
          {MODE_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setMode(option)}
              className={clsx("mode-card", option.id === mode.id && "mode-card--active")}
            >
              <span className="mode-card__label">{option.label}</span>
              <span className="mode-card__desc">{option.description}</span>
            </button>
          ))}
        </div>
      </div>
      {mode.id === "tournament" ? (
        <div className="room-create__panel">
          <p className="room-create__title">토너먼트 생성</p>
          <p className="room-create__helper">토너먼트는 별도 화면에서 브래킷과 참가자를 구성합니다.</p>
          <Link href="/tournaments/create" className="room-create__cta">
            토너먼트 만들기
          </Link>
        </div>
      ) : (
        <form className="room-create__panel space-y-4" onSubmit={handleSubmit}>
          {mode.variants && (
            <div>
              <p className="room-create__title">세부 모드</p>
              <div className="room-create__sizes">
                {mode.variants.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setVariant(item.roundType)}
                    className={clsx("size-chip", variant === item.roundType && "size-chip--active")}
                  >
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          <label className="room-create__field">
            <span>방 이름</span>
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="예: 2v2 FAST GAME" />
          </label>
          <label className="room-create__field">
            <span>설명</span>
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="선택 입력" />
          </label>
          {statusMessage && <p className="room-create__status">{statusMessage}</p>}
          <button type="submit" className="room-create__cta" disabled={submitting}>
            {submitting ? "생성 중..." : "방 만들기"}
          </button>
        </form>
      )}
    </div>
  );
}


