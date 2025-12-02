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
  accent: string;
}> = [
  { id: "solo", label: "개인전", description: "1v1 래더 모드", roundType: "round1_individual", accent: "emerald" },
  { id: "team", label: "팀전", description: "협동 2v2 / 4v4", roundType: "round2_team", accent: "indigo" },
  { id: "tournament", label: "토너먼트", description: "브래킷 기반 대회 생성", roundType: null, accent: "amber" },
];

const SIZE_OPTIONS = [
  { id: "1v1", label: "1 vs 1", slots: 2, hint: "듀얼" },
  { id: "2v2", label: "2 vs 2", slots: 4, hint: "소규모 전투" },
  { id: "4v4", label: "4 vs 4", slots: 8, hint: "대규모 협동" },
];

interface Props {
  onCreated?: (room: Room) => void;
}

export default function RoomCreateBoard({ onCreated }: Props) {
  const router = useRouter();
  const [mode, setMode] = useState(MODE_OPTIONS[0]);
  const [size, setSize] = useState(SIZE_OPTIONS[0]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const transition = useShellTransition();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!mode.roundType) {
      transition(() => router.push("/tournaments/create"));
      return;
    }
    setSubmitting(true);
    setStatusMessage(null);
    try {
      const payload = {
        name: name.trim() || `[${size.label}] 커스텀 방`,
        description: `${mode.label} · ${size.label}${description ? ` · ${description.trim()}` : ""}`,
        round_type: mode.roundType,
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
          <div>
            <p className="room-create__title">게임 크기</p>
            <div className="room-create__sizes">
              {SIZE_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setSize(option)}
                  className={clsx("size-chip", option.id === size.id && "size-chip--active")}
                >
                  <span>{option.label}</span>
                  <span className="size-chip__meta">{option.hint}</span>
                </button>
              ))}
            </div>
          </div>
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


