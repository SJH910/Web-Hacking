"use client";

// 용범의 탑 — 안전구역(로비). 타이틀(/)에서 "게임 시작"으로 진입하는 허브.
import Link from "next/link";
import { useEffect, useState } from "react";
import styles from "../page.module.css";
import { useFadeNav } from "../use-fade-nav";
import { ALL_BADGES, ALL_ENDINGS, readCollection, type Collection } from "../collection";

const RAON_GREETING =
  "여기선 안전해. 숨 고르고, 준비되면 등반을 시작하자. — 아, 내 조언이 늘 맞는 건 아니니 꼭 증거로 확인하고.";

type Rank = { rank: number; name: string; floor: number; score: number; trust: number; hints: number };

export default function Lobby() {
  const [tab, setTab] = useState<"lobby" | "record" | "ranking" | "companion">("lobby");
  const [ranks, setRanks] = useState<Rank[] | null>(null);
  const [col, setCol] = useState<Collection>({ endings: [], badges: [] });
  const [blueTrust, setBlueTrust] = useState<number | null>(null);
  const [redTrust, setRedTrust] = useState<number | null>(null);
  const { leaving, nav } = useFadeNav();

  useEffect(() => {
    fetch("/api/game/rankings").then((r) => r.json()).then((d) => setRanks(Array.isArray(d) ? d : [])).catch(() => setRanks([]));
    setCol(readCollection());
    // 파훼자(레드팀) 신뢰도: 세이브에서
    try { const raw = localStorage.getItem("ybt-rt-save"); if (raw) { const s = JSON.parse(raw); if (typeof s.trust === "number") setRedTrust(s.trust); } } catch { /* 무시 */ }
    // 수호자(블루팀) 신뢰도: 저장된 런 조회
    (async () => {
      try {
        const raw = localStorage.getItem("tower.run.v1");
        if (!raw) return;
        const { runId } = JSON.parse(raw);
        if (!runId) return;
        const d = await (await fetch(`/api/game/runs/${encodeURIComponent(runId)}`)).json();
        if (d?.state && typeof d.state.trust === "number") setBlueTrust(d.state.trust);
      } catch { /* 무시 */ }
    })();
  }, []);

  return <div className={`${styles.shell} ${leaving ? styles.leaving : ""}`}>
    <a className={styles.skip} href="#lobby">안전구역으로 건너뛰기</a>
    <header className={styles.header}><div className={styles.headerInner}>
      <Link className={styles.brand} href="/"><span className={styles.sigil} aria-hidden="true"><span className={styles.sigilGlyph}>♜</span></span>용범의 탑<span className={styles.brandSub}>THE TOWER</span></Link>
      <nav className={styles.nav} aria-label="주 메뉴">
        <Link href="/start" onClick={(e) => { e.preventDefault(); nav("/start"); }}>등반 시작</Link>
        <button type="button" className={styles.navTab} aria-current={tab === "lobby" ? "page" : undefined} onClick={() => setTab("lobby")}>안전구역</button>
        <button type="button" className={styles.navTab} aria-current={tab === "record" ? "page" : undefined} onClick={() => setTab("record")}>기록</button>
        <button type="button" className={styles.navTab} aria-current={tab === "ranking" ? "page" : undefined} onClick={() => setTab("ranking")}>랭킹</button>
        <button type="button" className={styles.navTab} aria-current={tab === "companion" ? "page" : undefined} onClick={() => setTab("companion")}>동료</button>
      </nav>
      <span className={styles.floorBadge}>◇ 안전구역</span><Link className={styles.introLink} href="/" onClick={(e) => { e.preventDefault(); nav("/"); }}>타이틀 ↩</Link>
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
            <Link className={styles.ctaBtn} href="/start" onClick={(e) => { e.preventDefault(); nav("/start"); }}>등반 시작 →</Link>
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
          <div className={styles.panelHeading}><div><span className={styles.eyebrow}>MY RECORD</span><h2 id="record-title">내 기록</h2></div><span className={styles.muted}>본인 수집 · 로컬 저장</span></div>
          <div className={styles.collectBody}>
            <div className={styles.collectHead}><strong>본 엔딩</strong><span>{col.endings.length} / {ALL_ENDINGS.length}</span></div>
            <div className={styles.endGrid}>
              {ALL_ENDINGS.map((e) => {
                const seen = col.endings.includes(e);
                return <div key={e} className={`${styles.endCard} ${seen ? styles.seen : styles.locked}`}><span className={styles.endMark}>{seen ? "★" : "☆"}</span><strong>{seen ? e : "？ ？ ？"}</strong></div>;
              })}
            </div>

            <div className={styles.collectHead}><strong>수집한 칭호</strong><span>{col.badges.length} / {ALL_BADGES.length}</span></div>
            <div className={styles.badgeRow}>
              {ALL_BADGES.map((b) => {
                const has = col.badges.includes(b);
                return <span key={b} className={`${styles.badgeChip} ${has ? styles.badgeHas : styles.badgeLocked}`}>✦ {has ? b : "？？？"}</span>;
              })}
            </div>

            {col.endings.length === 0 && col.badges.length === 0 &&
              <p className={styles.companionFoot}>아직 완주 기록이 없습니다. 등반을 끝까지 올라 엔딩을 보면 여기에 모입니다.</p>}
            <div className={styles.recordCta}><Link className={styles.ctaBtn} href="/start" onClick={(e) => { e.preventDefault(); nav("/start"); }}>등반 시작 →</Link></div>
          </div>
        </section>}

        {tab === "ranking" && <section className={styles.panel} aria-labelledby="ranking-title">
          <div className={styles.panelHeading}><div><span className={styles.eyebrow}>RANKING</span><h2 id="ranking-title">랭킹</h2></div><span className={styles.muted}>로컬 서버 기준</span></div>
          <div className={styles.rankBody}>
            {ranks === null
              ? <div className={styles.recordEmpty}><span className={styles.recordIcon} aria-hidden="true">…</span><p>불러오는 중…</p></div>
              : ranks.length === 0
                ? <div className={styles.recordEmpty}><span className={styles.recordIcon} aria-hidden="true">♛</span><h3>아직 랭킹이 없습니다</h3><p>모든 층을 통과하고 랭킹에 등록하면 여기에 표시됩니다.</p></div>
                : <ol className={styles.rankList}>{ranks.map((r) => (
                    <li key={r.rank}><span className={styles.rankNo}>{r.rank}</span><span className={styles.rankName}>{r.name}</span><span className={styles.rankMeta}>{r.floor}층 · {r.score}점 · 신뢰 {r.trust}</span></li>
                  ))}</ol>}
            <p className={styles.rankNote}>✧ 로컬 전용입니다. 공용 서버에 배포하면 이 서버에 접속한 여러 플레이어의 랭킹이 함께 모입니다.</p>
          </div>
        </section>}

        {tab === "companion" && <section className={styles.companion} aria-labelledby="companion-title">
          <div className={styles.companionHeader}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className={styles.companionSprite} src="/game/sprites/raon_mid.png" alt="라온" />
            <div><h2 id="companion-title">라온</h2><p>기억이 흐릿한 당신의 길잡이</p></div><span className={styles.tag}>동료</span>
          </div>
          <blockquote>나는 길을 안내하지만 완벽하진 않아. 가끔 틀린 말을 하니, 늘 증거로 확인해 줘.</blockquote>

          <div className={styles.trustBox}>
            <div className={styles.trustHead}><strong>신뢰도</strong><span>직업별 현재 등반 기준 · 실시간</span></div>
            <div className={styles.trustDual}>
              {([["🛡️ 수호자", blueTrust], ["🗡️ 파훼자", redTrust]] as const).map(([label, val]) => (
                <div className={styles.trustOne} key={label}>
                  <span className={styles.trustJob}>{label}</span>
                  {val === null
                    ? <span className={styles.trustNone}>진행 중인 등반 없음 · 시작값 60</span>
                    : <div className={styles.gauge}><div className={styles.gaugeFill} style={{ width: `${val}%` }}><span>{val}</span></div></div>}
                </div>
              ))}
            </div>
            <div className={styles.trustBands}>
              <span><b>&lt; 50</b> 흐릿하고 서늘</span>
              <span><b>50–79</b> 절반쯤 모호한 방향</span>
              <span><b>≥ 80</b> 분명하고 구체적인 조언</span>
            </div>
          </div>

          <div className={styles.rules}>
            <div className={styles.rule}><span className={styles.up}>▲</span> 라온을 의심하고 <b>증거로 반박해 성공</b>하면 신뢰도 상승</div>
            <div className={styles.rule}><span className={styles.down}>▼</span> 라온의 (틀린) 말을 <b>따라 실수</b>하면 하락 · 힌트 사용 시 소폭 하락</div>
          </div>

          <p className={styles.companionFoot}>✧ 신뢰도는 <b>등반마다(수호자·파훼자 각각) 따로</b> 쌓이며, 실제 값은 각 등반 화면에 실시간 표시됩니다. <b>등정 결말(엔딩)</b>도 이에 따라 갈립니다.</p>
        </section>}
      </div>

      <footer className={styles.footer}><span>용범의 탑 <span> / </span> 안전구역</span><span>합성·격리 환경 · 학습 전용</span></footer>
    </main>
  </div>;
}
