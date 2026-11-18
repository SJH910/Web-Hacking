"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import styles from "./page.module.css";

const SLIDE_DURATION = 3750;

const slides = [
  {
    chapter: "PROLOGUE · 도착",
    title: "구름 아래, 오래된 문",
    copy: "작은 등불 하나가 잠든 탑의 입구를 비춘다.",
    scene: "arrival",
  },
  {
    chapter: "THE GATE · 개방",
    title: "봉인이 깨어나다",
    copy: "금빛 문양이 빛나고, 닫혀 있던 길이 열린다.",
    scene: "opening",
  },
  {
    chapter: "ASCENT · 상승",
    title: "기억을 따라 오르다",
    copy: "구름과 희미한 창을 지나, 끝없는 계단이 이어진다.",
    scene: "ascent",
  },
  {
    chapter: "THE SUMMIT · 서막",
    title: "당신의 이야기가 시작된다",
    copy: "기억을 믿을 것인가, 기록을 믿을 것인가.",
    scene: "title",
  },
];

export default function IntroPage() {
  const [activeSlide, setActiveSlide] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [hasStarted, setHasStarted] = useState(false);

  const goToSlide = useCallback((index: number) => {
    setActiveSlide(Math.max(0, Math.min(slides.length - 1, index)));
    setIsPlaying(false);
    setHasStarted(true);
  }, []);

  const replay = useCallback(() => {
    setActiveSlide(0);
    setIsPlaying(true);
    setHasStarted(true);
  }, []);

  useEffect(() => {
    if (!isPlaying) return;

    const timer = window.setTimeout(() => {
      if (activeSlide === slides.length - 1) {
        setIsPlaying(false);
      } else {
        setActiveSlide((current) => current + 1);
      }
    }, SLIDE_DURATION);

    return () => window.clearTimeout(timer);
  }, [activeSlide, isPlaying]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        setHasStarted(true);
        setActiveSlide((current) => Math.min(slides.length - 1, current + 1));
        setIsPlaying(false);
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setHasStarted(true);
        setActiveSlide((current) => Math.max(0, current - 1));
        setIsPlaying(false);
      }
      if (event.code === "Space" && !(event.target instanceof HTMLButtonElement)) {
        event.preventDefault();
        setHasStarted(true);
        setIsPlaying((current) => !current);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const current = slides[activeSlide];

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <Link href="/" className={styles.brand} aria-label="용범의 탑으로 돌아가기">
          <span className={styles.brandSigil}>Y</span>
          <span>용범의 탑</span>
        </Link>
        <div className={styles.headerMeta}>
          <span className={styles.liveDot} />
          <span>인트로 시네마틱</span>
        </div>
        <Link href="/" className={styles.skipLink}>
          인트로 건너뛰기 <span aria-hidden="true">↗</span>
        </Link>
      </header>

      <section
        className={`${styles.stage} ${styles[current.scene]}`}
        aria-label="용범의 탑 인트로"
        aria-roledescription="슬라이드"
      >
        <div className={styles.stars} aria-hidden="true" />
        <div className={styles.moon} aria-hidden="true" />
        <div className={`${styles.cloud} ${styles.cloudOne}`} aria-hidden="true" />
        <div className={`${styles.cloud} ${styles.cloudTwo}`} aria-hidden="true" />
        <div className={styles.mountain} aria-hidden="true" />

        <Tower />

        {(activeSlide === 0 || activeSlide === 1) && (
          <div className={styles.traveler} aria-hidden="true">
            <span className={styles.cloak} />
            <span className={styles.lantern} />
          </div>
        )}

        {activeSlide === 1 && <div className={styles.gateGlow} aria-hidden="true" />}
        {activeSlide === 3 && <div className={styles.summitSeal} aria-hidden="true">✦</div>}

        <div className={styles.vignette} aria-hidden="true" />
        <div className={styles.sceneLabel}>
          <span className={styles.sceneIndex}>0{activeSlide + 1}</span>
          <span>{current.chapter}</span>
        </div>

        <div className={styles.caption} key={current.scene}>
          {activeSlide === 3 ? (
            <>
              <p className={styles.finalEyebrow}>AN ORIGINAL DARK FANTASY ADVENTURE</p>
              <h1 className={styles.logoTitle}>용범의 탑</h1>
              <p className={styles.finalCopy}>{current.copy}</p>
            </>
          ) : (
            <>
              <p className={styles.captionEyebrow}>YONGBEOM&apos;S TOWER</p>
              <h1>{current.title}</h1>
              <p className={styles.captionCopy}>{current.copy}</p>
            </>
          )}
        </div>

        {activeSlide === 3 && !isPlaying && (
          <Link className={styles.enterButton} href="/">
            탑에 입장하기 <span aria-hidden="true">→</span>
          </Link>
        )}

        <div className={styles.stageBottom}>
          <span>기억의 파편을 따라</span>
        </div>
      </section>

      <footer className={styles.controls}>
        <div className={styles.controlGroup}>
          <button
            type="button"
            className={styles.iconButton}
            aria-label="이전 장면"
            onClick={() => goToSlide(activeSlide - 1)}
            disabled={activeSlide === 0}
          >
            ←
          </button>
          <button
            type="button"
            className={styles.playButton}
            onClick={() => {
              if (activeSlide === slides.length - 1 && !isPlaying) {
                replay();
                return;
              }
              setHasStarted(true);
              setIsPlaying((currentPlaying) => !currentPlaying);
            }}
            aria-label={
              activeSlide === slides.length - 1 && !isPlaying
                ? "인트로 다시 재생"
                : isPlaying
                  ? "일시 정지"
                  : "재생"
            }
          >
            {activeSlide === slides.length - 1 && !isPlaying ? "↻" : isPlaying ? "Ⅱ" : "▶"}
          </button>
          <button
            type="button"
            className={styles.iconButton}
            aria-label="다음 장면"
            onClick={() => goToSlide(activeSlide + 1)}
            disabled={activeSlide === slides.length - 1}
          >
            →
          </button>
        </div>

        <div className={styles.timeline} aria-label="인트로 진행 상황">
          <div className={styles.timelineTrack}>
            <span
              className={styles.timelineProgress}
              key={`${activeSlide}-${isPlaying}-${hasStarted}`}
              style={{
                width: `${((activeSlide + 1) / slides.length) * 100}%`,
                animationDuration: `${SLIDE_DURATION}ms`,
                animationPlayState: isPlaying ? "running" : "paused",
                opacity: hasStarted || activeSlide > 0 ? 1 : 0.62,
              }}
            />
          </div>
          <span className={styles.timecode}>
            00:{String(activeSlide * 4).padStart(2, "0")} <i>/</i> 00:15
          </span>
        </div>

        <div className={styles.slidePicker} aria-label="장면 바로가기">
          {slides.map((slide, index) => (
            <button
              type="button"
              key={slide.scene}
              className={`${styles.slideDot} ${index === activeSlide ? styles.activeDot : ""} ${
                index < activeSlide ? styles.pastDot : ""
              }`}
              aria-label={`${index + 1}번째 장면: ${slide.title}`}
              aria-current={index === activeSlide ? "step" : undefined}
              onClick={() => goToSlide(index)}
            />
          ))}
        </div>
      </footer>
      <p className={styles.keyboardHint}>← → 장면 이동 <span>·</span> Space 재생 / 일시 정지</p>
    </main>
  );
}

function Tower() {
  return (
    <svg
      className={styles.tower}
      viewBox="0 0 640 900"
      role="img"
      aria-label="구름 위로 솟은 고대의 탑"
      preserveAspectRatio="xMidYMax meet"
    >
      <defs>
        <linearGradient id="towerStone" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#171522" />
          <stop offset=".48" stopColor="#332b43" />
          <stop offset="1" stopColor="#171522" />
        </linearGradient>
        <linearGradient id="towerLight" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#f4d48a" stopOpacity=".95" />
          <stop offset="1" stopColor="#b98745" stopOpacity=".35" />
        </linearGradient>
        <filter id="softGlow">
          <feGaussianBlur stdDeviation="9" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path d="M183 880 228 198 320 62 412 198 457 880Z" fill="url(#towerStone)" stroke="#756286" strokeOpacity=".38" />
      <path d="m228 198 92-136 92 136-24 19H252Z" fill="#29243a" stroke="#887391" strokeOpacity=".45" />
      <path d="m252 217 68-96 68 96-28 15h-80Z" fill="#211e2e" />
      <path d="M183 880 228 198h24l-35 682Zm205-682h24l45 682h-34Z" fill="#14131f" opacity=".8" />
      <path d="M221 375h198M210 571h220M198 768h244" stroke="#81718b" strokeOpacity=".25" strokeWidth="3" />
      <path d="M276 267v83m88-83v83m-100 112v72m112-72v72m-125 134v71m139-71v71m-153 130v55m166-55v55" stroke="url(#towerLight)" strokeWidth="7" filter="url(#softGlow)" />
      <path d="M285 270h-18v81h18m70-81h18v81h-18m-85 115h-18v72h18m102-72h18v72h-18m-115 63h-18v72h18m132-72h18v72h-18m-148 63h-18v56h18m164-56h18v56h-18" fill="none" stroke="#dfbd79" strokeOpacity=".32" strokeWidth="2" />
      <path d="m320 72 14 29-14 26-14-26Z" fill="#e7c779" filter="url(#softGlow)" />
      <path d="M302 876h36v24h-36z" fill="#0f0e17" />
    </svg>
  );
}
