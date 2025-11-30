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
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
  hydrate: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: undefined,
      token: undefined,
      loading: false,
      hydrate: () => {
        const token = get().token ?? null;
        setAuthToken(token);
      },
      login: async (email, password) => {
        set({ loading: true });
        try {
          const { data } = await api.post<AuthResponse>("/auth/login", { email, password });
          setAuthToken(data.access_token);
          set({ user: data.user, token: data.access_token });
        } finally {
          set({ loading: false });
        }
      },
      register: async (email, username, password) => {
        set({ loading: true });
        try {
          const { data } = await api.post<AuthResponse>("/auth/register", { email, username, password });
          setAuthToken(data.access_token);
          set({ user: data.user, token: data.access_token });
        } finally {
          set({ loading: false });
        }
      },
      logout: () => {
        setAuthToken(null);
        set({ user: undefined, token: undefined });
      }
    }),
    {
      name: "number-game-auth",
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          setAuthToken(state.token);
        }
      }
    }
  )
);

