"use client";

// 용범의 탑 — 타이틀 화면(게임 진입점). 메뉴 이동 시 페이드 아웃 후 전환.
import { useRouter } from "next/navigation";
import { useState } from "react";
import styles from "./title.module.css";

const FADE_MS = 380;

export default function Title() {
  const router = useRouter();
  const [leaving, setLeaving] = useState(false);

  function go(href: string) {
    if (leaving) return;
    setLeaving(true);
    setTimeout(() => router.push(href), FADE_MS);
  }
  function exit() {
    if (leaving) return;
    setLeaving(true);
    setTimeout(() => {
      try {
        if (window.top && window.top !== window.self) { window.top.location.hash = "scan"; return; }
      } catch { /* cross-origin 폴백 */ }
      window.location.href = "/";
    }, FADE_MS);
  }

  return (
    <div className={`${styles.scene} ${leaving ? styles.leaving : ""}`}>
      <div className={styles.stars} aria-hidden="true" />
      <div className={styles.logo}>
        <span className={styles.sub}>보안 수련의 탑</span>
        <h1>용범의 탑</h1>
        <span className={styles.en}>THE&nbsp;TOWER</span>
      </div>
      <nav className={styles.menu} aria-label="타이틀 메뉴">
        <button type="button" className={styles.item} onClick={() => go("/lobby")}>게임 시작</button>
        <button type="button" className={styles.item} onClick={() => go("/intro")}>인트로</button>
        <button type="button" className={styles.item} onClick={exit}>종료</button>
      </nav>
      <p className={styles.foot}>합성·격리 환경 · 학습 전용</p>
    </div>
  );
}
