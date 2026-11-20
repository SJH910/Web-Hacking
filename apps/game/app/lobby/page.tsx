"use client";

// 용범의 탑 — 안전구역(로비). 타이틀(/)에서 "게임 시작"으로 진입하는 허브.
import Link from "next/link";
import { useState } from "react";
import styles from "../page.module.css";

const RAON_GREETING =
  "여기선 안전해. 숨 고르고, 준비되면 등반을 시작하자. — 아, 내 조언이 늘 맞는 건 아니니 꼭 증거로 확인하고.";

export default function Lobby() {
  const [tab, setTab] = useState<"lobby" | "record" | "companion">("lobby");

  return <div className={styles.shell}>
    <a className={styles.skip} href="#lobby">안전구역으로 건너뛰기</a>
    <header className={styles.header}><div className={styles.headerInner}>
      <Link className={styles.brand} href="/"><span className={styles.sigil} aria-hidden="true">♜</span>용범의 탑<span className={styles.brandSub}>THE TOWER</span></Link>
      <nav className={styles.nav} aria-label="주 메뉴">
        <Link href="/start">등반 시작</Link>
        <button type="button" className={styles.navTab} aria-current={tab === "lobby" ? "page" : undefined} onClick={() => setTab("lobby")}>안전구역</button>
        <button type="button" className={styles.navTab} aria-current={tab === "record" ? "page" : undefined} onClick={() => setTab("record")}>기록</button>
        <button type="button" className={styles.navTab} aria-current={tab === "companion" ? "page" : undefined} onClick={() => setTab("companion")}>동료</button>
      </nav>
      <span className={styles.floorBadge}>◇ 안전구역</span><Link className={styles.introLink} href="/">타이틀 ↩</Link>
    </div></header>

    <main className={styles.main} id="lobby">
      <div className={styles.breadcrumb}>용범의 탑 <span>/</span> <strong>안전구역</strong></div>
      <section className={styles.heading}>
        <div><span className={styles.eyebrow}>BASE · SAFE ZONE</span><h1>안전구역에 들어섰습니다.</h1><p>탑을 오르기 전, 여기서 숨을 고르세요. 준비되면 직업을 골라 등반을 시작합니다.</p></div>
        <div className={styles.chapterMark} aria-hidden="true">⌂<span>안전구역</span></div>
      </section>

      <section className={styles.heroStage}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className={styles.heroPlayer} src="/game/sprites/player_idle.png" alt="플레이어" />
        <div className={styles.heroSpeech}><span className={styles.heroWho}>라온</span>{RAON_GREETING}</div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className={styles.heroRaon} src="/game/sprites/raon_mid.png" alt="라온" />
      </section>

      <div className={styles.tabpanel}>
        {tab === "lobby" && <>
          <section className={styles.cta} aria-labelledby="cta-title">
            <div><span className={styles.eyebrow}>START CLIMB</span><h2 id="cta-title">등반을 시작하시겠어요?</h2><p>직업을 선택하면 그 방식으로 각 층의 관문이 출제됩니다.</p></div>
            <Link className={styles.ctaBtn} href="/start">등반 시작 →</Link>
          </section>

          <section className={styles.panel} aria-labelledby="about-title">
            <div className={styles.panelHeading}><div><span className={styles.eyebrow}>THE TOWER</span><h2 id="about-title">용범의 탑이란?</h2></div><span className={styles.muted}>보안 수련장</span></div>
            <div className={styles.aboutGrid}>
              <div className={styles.aboutCard}><strong>🛡️ 수호자</strong><p>흔적을 읽어 위협을 가려낸다. 로그·설정을 조사해 취약 여부를 판정하는 길.</p></div>
              <div className={styles.aboutCard}><strong>🗡️ 파훼자</strong><p>방어를 깨고 안으로 든다. 가상 취약 웹앱을 탐색·공격해 FLAG를 캡처하는 길.</p></div>
            </div>
            <p className={styles.aboutFoot}>두 길 모두 <b>합성·격리 환경</b>에서 진행되며 실제 네트워크 요청을 보내지 않습니다.</p>
          </section>

          <section className={styles.safety} aria-label="시뮬레이션 안내"><span aria-hidden="true">◇</span><div><strong>탑 안에서만 이루어지는 안전한 수련</strong><p>사전 제작된 합성 데이터만 사용합니다. 실제 URL 입력·외부 요청·사이트 스캔은 지원하지 않습니다.</p></div><span className={styles.tag}>로컬 전용</span></section>
        </>}

        {tab === "record" && <section className={styles.panel} aria-labelledby="record-title">
          <div className={styles.panelHeading}><div><span className={styles.eyebrow}>RECORD</span><h2 id="record-title">등반 기록</h2></div><span className={styles.muted}>세이브·랭킹</span></div>
          <div className={styles.recordEmpty}>
            <span className={styles.recordIcon} aria-hidden="true">⌔</span>
            <h3>아직 등반 기록이 없습니다</h3>
            <p>직업을 골라 첫 등반을 시작하세요.<br />오른 층·획득한 FLAG·랭킹은 등반 중에 기록됩니다.</p>
            <Link className={styles.ctaBtn} href="/start">등반 시작 →</Link>
          </div>
        </section>}

        {tab === "companion" && <section className={styles.companion} aria-labelledby="companion-title">
          <div className={styles.companionHeader}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className={styles.companionSprite} src="/game/sprites/raon_mid.png" alt="라온" />
            <div><h2 id="companion-title">라온</h2><p>기억이 흐릿한 당신의 길잡이</p></div><span className={styles.tag}>동료</span>
          </div>
          <blockquote>나는 길을 안내하지만 완벽하진 않아. 가끔 틀린 말을 하니, 늘 증거로 확인해 줘.</blockquote>
          <div className={styles.opinionLabel}><strong>신뢰도에 따라 달라집니다</strong><span>표정·조언 품질</span></div>
          <div className={styles.trustRow}>
            {([["high", "신뢰 높음", "다정하고 분명한 조언"], ["mid", "보통", "절반쯤 모호한 방향"], ["low", "신뢰 낮음", "서늘하고 흐릿"]] as const).map(([k, label, desc]) => (
              <div className={styles.trustCard} key={k}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/game/sprites/raon_${k}.png`} alt={label} />
                <strong>{label}</strong><small>{desc}</small>
              </div>
            ))}
          </div>
          <p className={styles.companionFoot}>✧ 라온의 말을 따를지, 증거로 반박할지에 따라 신뢰도가 변합니다.</p>
        </section>}
      </div>

      <footer className={styles.footer}><span>용범의 탑 <span> / </span> 안전구역</span><span>합성·격리 환경 · 학습 전용</span></footer>
    </main>
  </div>;
}
