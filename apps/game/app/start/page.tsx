"use client";

// 직업 선택. 각 직업마다 "새 등반 / 이어하기"를 고른다.
//  · 수호자 → /play (블루팀) · 파훼자 → /redteam (레드팀)
//  · 새 등반 = ?new=1, 이어하기 = 저장된 등반 복귀(저장 없으면 비활성)
import { useEffect, useState } from "react";
import styles from "./start.module.css";
import { useFadeNav } from "../use-fade-nav";

const BLUE_SAVE = "tower.run.v1";
const RED_SAVE = "ybt-rt-save";

export default function Start() {
  const { leaving, nav } = useFadeNav();
  const [blue, setBlue] = useState(false);
  const [red, setRed] = useState(false);

  useEffect(() => {
    try { setBlue(!!localStorage.getItem(BLUE_SAVE)); } catch { /* 무시 */ }
    try { setRed(!!localStorage.getItem(RED_SAVE)); } catch { /* 무시 */ }
  }, []);

  return (
    <div className={`${styles.wrap} ${leaving ? styles.leaving : ""}`}>
      <header className={styles.top}>
        <span />
        <button type="button" className={styles.home} onClick={() => nav("/lobby")} title="안전구역" aria-label="안전구역으로"><span className={styles.homeGlyph}>⌂</span></button>
      </header>

      <h1 className={styles.title}>직업 선택</h1>
      <p className={styles.sub}>직업을 고르고, 새로 시작하거나 저장한 등반을 이어가세요. 선택한 직업에 따라 각 층의 문제가 달라집니다.</p>

      <div className={styles.grid}>
        <div className={`${styles.card} ${styles.blue}`}>
          <span className={styles.tag}>분석 · 판정</span>
          <h2 className={styles.cardTitle}>🛡️ 수호자</h2>
          <p className={styles.desc}>흔적을 읽어 위협을 가려내는 직업. 로그·헤더·설정을 조사해 분류→판정→조치 3단으로 관문을 지킨다.</p>
          <div className={styles.cardActions}>
            <button className={styles.startBtn} onClick={() => nav("/play?new=1")}>새 등반</button>
            <button className={styles.resumeBtn} disabled={!blue} onClick={() => blue && nav("/play")}>{blue ? "이어하기" : "저장 없음"}</button>
          </div>
        </div>

        <div className={`${styles.card} ${styles.red}`}>
          <span className={styles.tag}>침투 · 익스플로잇</span>
          <h2 className={styles.cardTitle}>🗡️ 파훼자</h2>
          <p className={styles.desc}>방어를 깨고 안으로 드는 직업. 가상 취약 웹앱을 탐색해 단서를 찾고 직접 공격해 FLAG를 캡처한다.</p>
          <div className={styles.cardActions}>
            <button className={styles.startBtn} onClick={() => nav("/redteam?new=1")}>새 등반</button>
            <button className={styles.resumeBtn} disabled={!red} onClick={() => red && nav("/redteam")}>{red ? "이어하기" : "저장 없음"}</button>
          </div>
        </div>
      </div>

      <p className={styles.note}>두 직업 모두 합성·격리 환경이며 실제 네트워크 요청을 보내지 않습니다.</p>
    </div>
  );
}
