"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import { useRouter } from "next/navigation";

import api from "@/lib/api";
import type { Room, RoundType, RoomMode } from "@/types/api";
import { useShellTransition } from "@/hooks/useShellTransition";

type SizeOption = {
  id: string;
  label: string;
  teamSize: number;
  hint: string;
  disabled?: boolean;
  comingSoon?: string;
};

type ModeOption = {
  id: "individual" | "team" | "tournament";
  label: string;
  description: string;
  helper?: string;
  roundType: RoundType | null;
  mode: RoomMode | null;
  accent: string;
  sizes?: SizeOption[];
};

const MODE_OPTIONS: ModeOption[] = [
  {
    id: "individual",
    label: "개인전",
    description: "1vs1 기본 / 2vs2·3vs3 릴레이",
    helper: "킹오브파이터식으로 승자가 다음 상대와 이어붙습니다.",
    roundType: "round1_individual",
    mode: "individual",
    accent: "emerald",
    sizes: [
      { id: "solo-1v1", label: "1 vs 1", teamSize: 1, hint: "표준 래더" },
      {
        id: "solo-2v2",
        label: "2 vs 2",
        teamSize: 2,
        hint: "릴레이 팀전",
        disabled: true,
        comingSoon: "곧 개발 예정",
      },
      {
        id: "solo-3v3",
        label: "3 vs 3",
        teamSize: 3,
        hint: "릴레이 팀전",
        disabled: true,
        comingSoon: "곧 개발 예정",
      },
    ],
  },
  {
    id: "team",
    label: "팀전",
    description: "2라운드 레퍼런스 룰",
    helper: "‘참고’ 폴더의 2라운드 팀전처럼 하나의 수식을 순차 입력합니다.",
    roundType: "round2_team",
    mode: "team",
    accent: "indigo",
    sizes: [
      {
        id: "team-2v2",
        label: "2 vs 2",
        teamSize: 2,
        hint: "코스트 분배 협동",
        disabled: true,
        comingSoon: "곧 개발 예정",
      },
      {
        id: "team-4v4",
        label: "4 vs 4",
        teamSize: 4,
        hint: "풀 로스터",
        disabled: true,
        comingSoon: "곧 개발 예정",
      },
    ],
  },
  {
    id: "tournament",
    label: "토너먼트",
    description: "32강~ 결승 브래킷",
    helper: "전용 생성 화면에서 참가자를 배치해 주세요.",
    roundType: null,
    mode: "tournament",
    accent: "amber",
  },
];

interface Props {
  onCreated?: (room: Room) => void;
}

export default function RoomCreateBoard({ onCreated }: Props) {
  const router = useRouter();
  const [mode, setMode] = useState<ModeOption>(MODE_OPTIONS[0]);
  const [size, setSize] = useState<SizeOption | null>(MODE_OPTIONS[0].sizes?.[0] ?? null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const transition = useShellTransition();

  useEffect(() => {
    if (!mode.sizes?.length) {
      setSize(null);
      return;
    }
    setSize((prev) => {
      if (prev && !prev.disabled && mode.sizes?.some((item) => item.id === prev.id && !item.disabled)) {
        return prev;
      }
      return mode.sizes?.find((item) => !item.disabled) ?? null;
    });
  }, [mode]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!mode.roundType || !mode.mode) {
      transition(() => router.push("/tournaments/create"));
      return;
    }
    if (!size) {
      setStatusMessage("대전 방식을 선택해 주세요.");
      return;
    }
    setSubmitting(true);
    setStatusMessage(null);
    try {
      const payload = {
        name: name.trim() || `[${size.label}] 커스텀 방`,
        description: `${mode.label} · ${size.label}${description ? ` · ${description.trim()}` : ""}`,
        round_type: mode.roundType,
        mode: mode.mode,
        team_size: size.teamSize,
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
            <p className="room-create__title">{mode.id === "team" ? "팀 구성" : "대전 방식"}</p>
            {mode.helper && <p className="room-create__helper">{mode.helper}</p>}
            <div className="room-create__sizes">
              {mode.sizes?.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => {
                    if (option.disabled) return;
                    setSize(option);
                  }}
                  disabled={option.disabled}
                  className={clsx(
                    "size-chip",
                    option.id === size?.id && "size-chip--active",
                    option.disabled && "size-chip--disabled",
                  )}
                  title={option.disabled ? option.comingSoon ?? "곧 개발 예정" : undefined}
                >
                  <span>{option.label}</span>
                  <span className="size-chip__meta">
                    {option.disabled ? option.comingSoon ?? "곧 개발 예정" : option.hint}
                  </span>
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


