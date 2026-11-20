"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import AnalysisResults, { type RunStatus } from "./analysis-results";
import { judgeEvidence, scenarios, type Mode } from "./scenarios";
import styles from "./page.module.css";

export default function Home() {
  const [scenarioId, setScenarioId] = useState(scenarios[0].id);
  const [mode, setMode] = useState<Mode>("observe");
  const [status, setStatus] = useState<RunStatus>("idle");
  const [selected, setSelected] = useState<string[]>([]);
  const [completed, setCompleted] = useState<string[]>([]);
  const [feedback, setFeedback] = useState("");
  const [showHint, setShowHint] = useState(false);
  const [failNext, setFailNext] = useState(false);
  const [question, setQuestion] = useState("evidence");
  const [reply, setReply] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scenario = scenarios.find((item) => item.id === scenarioId)!;
  const running = status === "running";
  const hasEvidence = status === "ready" || status === "complete";

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  function resetResult() {
    setStatus("idle"); setSelected([]); setFeedback(""); setReply("");
  }

  function runScenario() {
    if (timer.current) return;
    const shouldFail = failNext;
    setFailNext(false);
    setSelected([]); setFeedback(""); setReply(""); setStatus("running");
    timer.current = setTimeout(() => {
      timer.current = null;
      setStatus(shouldFail ? "error" : "ready");
    }, 700);
  }

  function judge() {
    if (status !== "ready") return;
    if (judgeEvidence(scenario, selected)) {
      setStatus("complete");
      setCompleted((ids) => ids.includes(scenario.id) ? ids : [...ids, scenario.id]);
      setFeedback("관문 검증 완료! 서로 연결되는 두 기록을 근거로 판단했습니다. 다른 시나리오에서도 라온의 말을 확인해 보세요.");
    } else {
      setFeedback("아직 근거가 충분하지 않아요. 목표와 직접 관련된 두 증거만 선택하고 다시 판정해 보세요.");
    }
  }

  return <div className={styles.shell}>
    <a className={styles.skip} href="#analysis">관문 분석으로 건너뛰기</a>
    <header className={styles.header}><div className={styles.headerInner}>
      <Link className={styles.brand} href="/"><span className={styles.sigil} aria-hidden="true">♜</span>용범의 탑<span className={styles.brandSub}>THE TOWER</span></Link>
      <nav className={styles.nav} aria-label="주 메뉴"><Link href="/start">등반 시작</Link><a href="#tower">층 탐험</a><a href="#analysis" aria-current="page">관문 분석</a><a href="#evidence">증거 기록</a><a href="#companion">AI 동료</a></nav>
      <span className={styles.floorBadge}>◇ 제3층</span><Link className={styles.introLink} href="/intro">인트로 ↗</Link>
    </div></header>
    <main className={styles.main}>
      <div className={styles.breadcrumb}>탑 탐험 <span>/</span> 제3층 <span>/</span> <strong>기록의 문</strong></div>
      <section className={styles.heading}>
        <div><span className={styles.eyebrow}>FLOOR 03 · THE ARCHIVE</span><h1>흔적을 읽고, 진실에 다가서세요.</h1><p>동료의 말은 하나의 가설입니다. 기록을 조사하고 증거로 관문을 여세요.</p></div>
        <div className={styles.chapterMark} aria-hidden="true">Ⅲ<span>기록의 문</span></div>
      </section>
      <section className={styles.safety} aria-label="시뮬레이션 안내"><span aria-hidden="true">◇</span><div><strong>탑 안에서만 이루어지는 안전한 조사</strong><p>사전 제작된 합성 데이터만 사용합니다. 실제 URL 입력·외부 요청·사이트 스캔은 지원하지 않습니다.</p></div><span className={styles.tag}>로컬 목업</span></section>
      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          <section id="analysis" className={styles.panel} aria-labelledby="setup-title">
            <div className={styles.panelHeading}><div><span className={styles.eyebrow}>01 / INVESTIGATION</span><h2 id="setup-title">어떤 기록부터 살펴볼까요?</h2></div><span className={styles.muted}>시나리오 3개</span></div>
            <fieldset className={styles.setup} disabled={running}>
              <legend className={styles.srOnly}>시나리오와 조사 방식</legend>
              <div className={styles.scenarios}>
                {scenarios.map((item, index) => <label className={styles.scenario} key={item.id}>
                  <input type="radio" name="scenario" value={item.id} checked={scenarioId === item.id} onChange={() => { setScenarioId(item.id); resetResult(); }} />
                  <span className={styles.scenarioIcon} aria-hidden="true">{["▤", "⌑", "⌘"][index]}</span>
                  <span className={styles.scenarioBody}><strong>{item.title}</strong><span>{item.description}</span><small>{item.difficulty} <span>·</span> {completed.includes(item.id) ? "✓ 검증 완료" : "미완료"}</small></span>
                </label>)}
              </div>
              <p className={styles.objective}><strong>이번 목표</strong>{scenario.objective}</p>
              <h3 className={styles.fieldTitle}>조사 방식</h3>
              <div className={styles.modes}>
                <label className={styles.mode}><input type="radio" name="mode" checked={mode === "observe"} onChange={() => { setMode("observe"); resetResult(); }} /><span><strong>◉ 관찰</strong><small>준비된 로그와 응답을 직접 읽습니다.</small></span></label>
                <label className={styles.mode}><input type="radio" name="mode" checked={mode === "simulate"} onChange={() => { setMode("simulate"); resetResult(); }} /><span><strong>▷ 시뮬레이션</strong><small>정해진 행동과 결과를 재생합니다.</small></span></label>
              </div>
              <details className={styles.settings}><summary>게임 설정 <span>힌트 · 목업 오류 체험</span></summary><div><label><input type="checkbox" checked={showHint} onChange={(event) => setShowHint(event.target.checked)} /> 증거 선택 힌트 표시</label><label><input type="checkbox" checked={failNext} onChange={(event) => setFailNext(event.target.checked)} /> 다음 조사에서 불러오기 오류 체험</label><p>오류 체험은 한 번만 적용됩니다. 실제 서버에는 연결하지 않습니다.</p></div></details>
            </fieldset>
            <div className={styles.actions}><span><strong>{scenario.title}</strong><small>{mode === "observe" ? "로그 관찰" : "행동 재생"} · 정적 시나리오</small></span><button className={styles.primary} disabled={running} onClick={runScenario}>{running ? "기록을 확인하는 중…" : hasEvidence ? "다시 조사하기 ↻" : "관문 조사 시작 →"}</button></div>
          </section>
          <AnalysisResults scenario={scenario} mode={mode} status={status} selected={selected} feedback={feedback} showHint={showHint} onSelect={(id) => { setSelected((ids) => ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id]); setFeedback(""); }} onJudge={judge} onRetry={runScenario} />
        </div>
        <aside className={styles.sidebar}>
          <section id="tower" className={styles.towerCard} aria-labelledby="tower-title"><span className={styles.eyebrow}>YOUR JOURNEY</span><div className={styles.towerTitle}><h2 id="tower-title">제3층 · 기록의 문</h2><span aria-hidden="true">Ⅲ</span></div><p>기억을 믿을 것인가,<br />기록을 믿을 것인가?</p><div className={styles.steps}><span>01 도착</span><span>02 개방</span><strong>03 기록</strong><span>04 잠김</span></div><div className={styles.progressLabel}><span>시나리오 검증</span><strong>{completed.length} / 3</strong></div><progress max={3} value={completed.length} aria-label="완료한 시나리오" /><p className={styles.towerFoot}>{completed.length === 3 ? "✓ 모든 시나리오를 검증했습니다. 다음 층은 준비 중입니다." : "증거를 선택하고 판단하면 진행도가 기록됩니다."}</p></section>
          <section id="companion" className={styles.companion} aria-labelledby="companion-title"><div className={styles.companionHeader}><span className={styles.avatar} aria-hidden="true">ㄹ<span>✦</span></span><div><h2 id="companion-title">라온</h2><p>기억이 흐릿한 당신의 길잡이</p></div><span className={styles.tag}>목업</span></div>
            <div className={styles.opinionLabel}><strong>동료의 의견</strong><span>증거와 별개</span></div><blockquote>{hasEvidence ? scenario.opinion : "이 문 너머의 기록은 조금 낯설어. 먼저 조사해 줄래? 내 기억이 틀릴 수도 있으니까."}</blockquote>
            <div className={styles.confidence}><span>의견 확신도</span><strong>{hasEvidence ? `${scenario.confidence}%` : "판단 전"}</strong></div><p className={styles.reference}>근거: {hasEvidence ? scenario.evidence[0].source : "아직 확인한 증거 없음"}</p>
            <form className={styles.questionForm} onSubmit={(event) => { event.preventDefault(); setReply(question === "evidence" ? scenario.hint : scenario.unconfirmed); }}><label htmlFor="question">라온에게 물어보기</label><div><select id="question" value={question} onChange={(event) => setQuestion(event.target.value)} disabled={!hasEvidence}><option value="evidence">어떤 증거를 비교할까?</option><option value="unknown">아직 모르는 것은 뭘까?</option></select><button disabled={!hasEvidence} type="submit" aria-label="라온에게 질문 보내기">↑</button></div></form>
            <div aria-live="polite">{reply && <p className={styles.reply}>{reply}</p>}</div><p className={styles.companionFoot}>✧ 정해진 대사를 사용합니다. 실제 AI 연결 전입니다.</p>
          </section>
          <div className={styles.fieldNote}><span>탐험가의 원칙</span><p>좋은 질문은 의심에서,<br />좋은 판단은 증거에서.</p><span aria-hidden="true">✦</span></div>
        </aside>
      </div>
      <footer className={styles.footer}><span>용범의 탑 <span> / </span> 관문 기록실</span><span>프런트엔드 목업 · 진행도는 현재 화면에서만 유지됩니다.</span></footer>
    </main>
  </div>;
}
