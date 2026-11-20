"use client";

// 등반 시작 — 루트 선택. 선택에 따라 출제가 갈린다:
//  · 기존(블루팀 분석·판정) → /play (game_engine 10층 풀)
//  · 레드팀(침투) → /redteam (가상 취약 웹앱 챌린지)
import Link from "next/link";
import styles from "./start.module.css";

export default function Start() {
  return (
    <div className={styles.wrap}>
      <header className={styles.top}>
        <Link href="/" className={styles.back}>← 용범의 탑</Link>
      </header>

      <h1 className={styles.title}>직업 선택</h1>
      <p className={styles.sub}>어떤 직업으로 탑을 오를지 고르세요. 선택한 직업에 따라 각 층의 문제가 달라집니다.</p>

      <div className={styles.grid}>
        <Link href="/play" className={`${styles.card} ${styles.blue}`}>
          <span className={styles.tag}>분석 · 판정</span>
          <h2 className={styles.cardTitle}>🛡️ 수호자</h2>
          <p className={styles.desc}>흔적을 읽어 위협을 가려내는 직업. 로그·헤더·설정을 조사해 분류→판정→조치 3단으로 관문을 지킨다.</p>
          <span className={styles.go}>이 직업으로 시작 →</span>
        </Link>

        <Link href="/redteam" className={`${styles.card} ${styles.red}`}>
          <span className={styles.tag}>침투 · 익스플로잇</span>
          <h2 className={styles.cardTitle}>🗡️ 파훼자</h2>
          <p className={styles.desc}>방어를 깨고 안으로 드는 직업. 가상 취약 웹앱을 탐색해 단서를 찾고 직접 공격해 FLAG를 캡처한다.</p>
          <span className={styles.go}>이 직업으로 시작 →</span>
        </Link>
      </div>

      <p className={styles.note}>두 루트 모두 합성·격리 환경이며 실제 네트워크 요청을 보내지 않습니다.</p>
    </div>
  );
}
