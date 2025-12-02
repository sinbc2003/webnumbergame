"use client";

import { SWRConfig } from "swr";

import { LobbyProvider } from "@/hooks/useLobby";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        shouldRetryOnError: false,
        revalidateOnFocus: true,
      }}
    >
      <LobbyProvider>{children}</LobbyProvider>
    </SWRConfig>
  );
}

