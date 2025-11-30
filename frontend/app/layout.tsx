import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "숫자게임 플랫폼",
  description: "3분 최적해 대결을 위한 실시간 웹 숫자게임",
  icons: [{ rel: "icon", url: "/favicon.ico" }]
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

