"use client";

// 페이지 이동 시 페이드 아웃 → 전환. 도착 화면은 각 모듈 CSS의 진입 애니메이션으로 페이드 인.
import { useRouter } from "next/navigation";
import { useState } from "react";

export const FADE_MS = 360;

export function useFadeNav() {
  const router = useRouter();
  const [leaving, setLeaving] = useState(false);

  function nav(href: string) {
    if (leaving) return;
    setLeaving(true);
    setTimeout(() => router.push(href), FADE_MS);
  }

  return { leaving, nav };
}
