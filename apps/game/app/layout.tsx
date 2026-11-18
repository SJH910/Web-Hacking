import type { Metadata } from "next";
import "./globals.css";
import SiteBgm from "./site-bgm";

export const metadata: Metadata = {
  title: "용범의 탑 | 관문 기록실",
  description: "가상 시나리오를 조사하고 증거를 모아 관문을 통과하세요.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        {children}
        <SiteBgm />
      </body>
    </html>
  );
}
