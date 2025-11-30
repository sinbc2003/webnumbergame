import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";
import { DEFAULT_API_BASE, DEFAULT_WS_BASE } from "@/lib/runtimeConfig";

const runtimeConfig = {
  apiBase: process.env.NEXT_PUBLIC_API_BASE ?? process.env.API_BASE ?? DEFAULT_API_BASE,
  wsBase: process.env.NEXT_PUBLIC_WS_BASE ?? process.env.WS_BASE ?? DEFAULT_WS_BASE
};

const serializedRuntimeConfig = JSON.stringify(runtimeConfig).replace(/</g, "\\u003c");

export const metadata: Metadata = {
  title: "숫자게임 플랫폼",
  description: "3분 최적해 대결을 위한 실시간 웹 숫자게임",
  icons: [{ rel: "icon", url: "/favicon.ico" }]
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <script
          id="runtime-config"
          dangerouslySetInnerHTML={{
            __html: `window.__RUNTIME_CONFIG__ = ${serializedRuntimeConfig};`
          }}
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

