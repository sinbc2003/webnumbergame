"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import api, { setAuthToken } from "@/lib/api";
import { User } from "@/types/api";

type Setter = (
  partial: AuthState | Partial<AuthState> | ((state: AuthState) => AuthState | Partial<AuthState>),
  replace?: boolean,
) => void;

let setStateRef: Setter | null = null;

interface AuthResponse {
  access_token: string;
  expires_at: string;
  user: User;
}

interface LoginPayload {
  email: string;
  password: string;
}

interface RegisterPayload {
  email: string;
  username: string;
  password: string;
}

interface AuthState {
  user?: User;
  token?: string;
  hydrated: boolean;
  loading: boolean;
  login: (credentials: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  adminLogin: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => {
      setStateRef = set;
      return {
        user: undefined,
        token: undefined,
        hydrated: false,
        loading: false,
        login: async ({ email, password }) => {
          set({ loading: true });
          try {
            const { data } = await api.post<AuthResponse>("/auth/login", {
              email,
              password,
            });
            setAuthToken(data.access_token);
            set({ user: data.user, token: data.access_token, hydrated: true });
          } finally {
            set({ loading: false });
          }
        },
        register: async ({ email, username, password }) => {
          set({ loading: true });
          try {
            const { data } = await api.post<AuthResponse>("/auth/register", {
              email,
              username,
              password,
            });
            setAuthToken(data.access_token);
            set({ user: data.user, token: data.access_token, hydrated: true });
          } finally {
            set({ loading: false });
          }
        },
        adminLogin: async (username, password) => {
          set({ loading: true });
          try {
            const { data } = await api.post<AuthResponse>("/auth/admin/login", { username, password });
            setAuthToken(data.access_token);
            set({ user: data.user, token: data.access_token, hydrated: true });
          } finally {
            set({ loading: false });
          }
        },
        logout: () => {
          setAuthToken(null);
          set({ user: undefined, token: undefined, hydrated: true });
        },
      };
    },
    {
      name: "number-game-auth",
      onRehydrateStorage: () => (state) => {
        setAuthToken(state?.token ?? null);
        setStateRef?.((current) => ({
          ...current,
          user: state?.user,
          token: state?.token,
          hydrated: true,
        }));
      },
    }
  )
);

