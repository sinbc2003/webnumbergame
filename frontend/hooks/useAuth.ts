"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import api, { setAuthToken } from "@/lib/api";
import { User } from "@/types/api";

interface AuthResponse {
  access_token: string;
  expires_at: string;
  user: User;
}

interface AuthState {
  user?: User;
  token?: string;
  loading: boolean;
  login: (nickname: string) => Promise<void>;
  register: (nickname: string) => Promise<void>;
  adminLogin: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hydrate: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => {
      const enterAsGuest = async (nickname: string) => {
        set({ loading: true });
        try {
          const { data } = await api.post<AuthResponse>("/auth/guest", { nickname });
          setAuthToken(data.access_token);
          set({ user: data.user, token: data.access_token });
        } finally {
          set({ loading: false });
        }
      };

      return {
        user: undefined,
        token: undefined,
        loading: false,
        hydrate: () => {
          const token = get().token ?? null;
          setAuthToken(token);
        },
        login: async (nickname) => enterAsGuest(nickname),
        register: async (nickname) => enterAsGuest(nickname),
        adminLogin: async (username, password) => {
          set({ loading: true });
          try {
            const { data } = await api.post<AuthResponse>("/auth/admin/login", { username, password });
            setAuthToken(data.access_token);
            set({ user: data.user, token: data.access_token });
          } finally {
            set({ loading: false });
          }
        },
        logout: () => {
          setAuthToken(null);
          set({ user: undefined, token: undefined });
        },
      };
    },
    {
      name: "number-game-auth",
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          setAuthToken(state.token);
        }
      },
    }
  )
);

