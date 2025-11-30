const DEFAULT_API_BASE = "http://localhost:8000/api";
const DEFAULT_WS_BASE = "ws://localhost:8000";

export type RuntimeConfig = {
  apiBase: string;
  wsBase: string;
};

declare global {
  interface Window {
    __RUNTIME_CONFIG__?: Partial<RuntimeConfig>;
  }
}

const readFromWindow = (): Partial<RuntimeConfig> | null => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.__RUNTIME_CONFIG__ ?? null;
};

const readFromProcessEnv = (): Partial<RuntimeConfig> => ({
  apiBase: process.env.API_BASE ?? process.env.NEXT_PUBLIC_API_BASE ?? undefined,
  wsBase: process.env.WS_BASE ?? process.env.NEXT_PUBLIC_WS_BASE ?? undefined
});

export const getRuntimeConfig = (): RuntimeConfig => {
  const source = readFromWindow() ?? readFromProcessEnv();
  return {
    apiBase: source.apiBase ?? DEFAULT_API_BASE,
    wsBase: source.wsBase ?? DEFAULT_WS_BASE
  };
};

export { DEFAULT_API_BASE, DEFAULT_WS_BASE };


