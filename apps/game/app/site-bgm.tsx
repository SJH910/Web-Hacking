"use client";

import { useCallback, useRef, useState } from "react";
import styles from "./site-bgm.module.css";

export default function SiteBgm() {
  const [enabled, setEnabled] = useState(false);
  const [error, setError] = useState("");
  const audioRef = useRef<HTMLAudioElement>(null);

  const toggleMusic = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (!audio.paused) {
      audio.pause();
      setEnabled(false);
      setError("");
      return;
    }

    audio.volume = 0.48;
    try {
      await audio.play();
      setEnabled(true);
      setError("");
    } catch {
      setEnabled(false);
      setError("음원을 재생할 수 없습니다. 다시 눌러 시도해 주세요.");
    }
  }, []);

  return (
    <>
      <audio
        ref={audioRef}
        src="/game/audio/yongbeom-tower-theme.wav"
        preload="none"
        loop
      />
      <div className={styles.audioControl}>
        <button
          type="button"
          className={`${styles.toggle} ${enabled ? styles.enabled : ""}`}
          onClick={() => void toggleMusic()}
          aria-pressed={enabled}
          aria-label={enabled ? "배경 음악 끄기" : "배경 음악 켜기"}
          title="페이지 이동 중에도 유지되는 오리지널 배경 음악"
        >
          <span className={styles.icon} aria-hidden="true">{enabled ? "♫" : "♩"}</span>
          <span className={styles.label}>{enabled ? "BGM 켜짐" : "BGM 켜기"}</span>
          {enabled && (
            <span className={styles.equalizer} aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
          )}
        </button>
        {error && <span className={styles.error} role="status">{error}</span>}
      </div>
    </>
  );
}
