"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { gameRequest, readSave, SAVE_KEY, type Game } from "./game-api";
import { Investigation, Judgment } from "./play-panels";
import { recordEnding } from "../collection";
import { useFadeNav } from "../use-fade-nav";
import { Typewriter } from "../typewriter";
import s from "./play.module.css";

export default function Play() {
  const { leaving, nav } = useFadeNav();
  const [game, setGame] = useState<Game | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [storageNote, setStorageNote] = useState("");
  const [feedback, setFeedback] = useState("");
  const [output, setOutput] = useState<string[]>([]);
  const [confirmNew, setConfirmNew] = useState(false);
  const [needsSync, setNeedsSync] = useState(false);
  const lock = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    try { const raw = localStorage.getItem(SAVE_KEY); setSaved(readSave(raw)); if (raw && !readSave(raw)) setStorageNote("저장 기록을 읽을 수 없습니다. 새 등반을 시작해 주세요."); }
    catch { setStorageNote("이 브라우저에서는 자동 저장을 사용할 수 없습니다."); }
  }, []);
  useEffect(() => { if (game) heading.current?.focus(); }, [game?.floor, game?.runId]); // 층 전환 시 맥락 안내
  useEffect(() => { if (game?.ending) recordEnding(game.ending.title, game.ending.badges); }, [game?.ending]); // 본 엔딩·칭호 수집
  const [bubble, setBubble] = useState("");
  useEffect(() => {  // 말풍선: 힌트 받으면 최신 힌트, 아니면 라온 첫마디
    if (!game) return;
    setBubble(game.hints.length > 0 ? game.hints[game.hints.length - 1].text : game.problem.allyOpening);
  }, [game?.hints.length, game?.floor, game?.runId, game?.problem.allyOpening]); // eslint-disable-line react-hooks/exhaustive-deps
  const started = useRef(false);
  useEffect(() => {  // 바로 문제 진입: ?new=1이면 새 등반, 아니면 저장 기록 이어하기(없으면 새 등반)
    if (started.current) return;
    started.current = true;
    const wantNew = new URLSearchParams(window.location.search).get("new") === "1";
    let savedRun: string | null = null;
    try { savedRun = readSave(localStorage.getItem(SAVE_KEY)); } catch { savedRun = null; }
    if (!wantNew && savedRun) void load(`runs/${encodeURIComponent(savedRun)}`);
    else void load("runs", { requestId: crypto.randomUUID() });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function load(path: string, body?: object) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try {
      const result = await gameRequest(path, body);
      if (!game || result.state.floor !== game.floor || result.state.runId !== game.runId) setOutput([]);
      setGame(result.state); setFeedback(result.feedback ?? ""); setNeedsSync(false);
      if (result.output) setOutput(lines => [...lines.slice(-49), `${body && "command" in body ? `$ ${body.command}\n` : ""}${result.output}`]);
      setSaved(result.state.runId); setConfirmNew(false);
      try { localStorage.setItem(SAVE_KEY, JSON.stringify({ version: 1, runId: result.state.runId })); setStorageNote("진행 기록이 저장되었습니다."); }
      catch { setStorageNote("저장 공간에 접근하지 못했습니다. 현재 플레이는 계속할 수 있습니다."); }
    } catch (e) { setError(e instanceof Error ? e.message : "요청에 실패했습니다."); if (game && body !== undefined) setNeedsSync(true); }
    finally { lock.current = false; setBusy(false); }
  }
  async function act(action: string, data: object) {
    if (!game || needsSync) return;
    await load(`runs/${encodeURIComponent(game.runId)}/${action}`, { ...data, revision: game.revision, requestId: crypto.randomUUID() });
  }
  const disabled = busy || needsSync;
  const trust = game?.trust ?? 60;
  const raonTier = trust >= 80 ? "high" : trust >= 50 ? "mid" : "low";
  const playerTier = game?.cleared ? "win" : "idle";
  return <div className={`${s.shell} ${leaving ? s.leaving : ""}`}>
    <a className={s.skip} href="#play-main">게임으로 건너뛰기</a>
    <header className={s.top}>
      <Link href="/start" className={s.back} onClick={e => { e.preventDefault(); nav("/start"); }}>← 직업 선택</Link>
      <div className={s.topRight}>
        <span className={s.badge}>🛡️ 수호자</span>
        <button type="button" className={s.home} onClick={() => nav("/lobby")} title="안전구역" aria-label="안전구역으로"><span className={s.homeGlyph}>⌂</span></button>
      </div>
    </header>

    {game && <div className={s.floorbar}><span className={s.floortag}>⛰ 제 {game.floor} 층</span><span className={s.status}>{game.cleared ? "통과" : "조사 중"}</span></div>}
    <h1 ref={heading} tabIndex={-1} className={s.title}>{game ? game.problem.title : "새로운 등반을 시작하세요"}</h1>
    <p className={s.sub}>{game ? `${game.problem.difficulty} · 분류→판정→조치로 봉인을 해제하세요` : "기록을 탐색하고 증거로 관문을 여세요 · 합성·격리"}</p>

    {game && <div className={s.stage}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className={s.player} src={`/game/sprites/player_${playerTier}.png`} alt="플레이어" />
      <div className={s.speechCol}>
        <div className={s.speech}><span className={s.who}>라온</span><Typewriter text={bubble} /></div>
        <div className={s.stageFoot}>
          <div className={s.trustMini}><span>신뢰도 <b>{game.trust}</b></span><div className={s.tbar}><div className={s.tfill} style={{ width: `${game.trust}%` }} /></div></div>
          <button className={s.hintBtn} onClick={() => void act("hints", {})} disabled={disabled || game.hints.length >= 3 || game.cleared}>힌트 요청 ({3 - game.hints.length})</button>
        </div>
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className={s.raon} src={`/game/sprites/raon_${raonTier}.png`} alt="라온" />
    </div>}
    {game && game.hints.length > 0 && <div className={s.hintCard}><span className={s.hintCardTitle}>받은 힌트</span><div className={s.hintLog}>{game.hints.map(h => <div key={h.level} className={s.hintItem}>힌트 {h.level}: {h.text}</div>)}</div></div>}

    <main id="play-main" className={s.main} aria-busy={busy}>
      <div role="status" className={s.note}>{busy ? "기록을 불러오는 중…" : storageNote}</div>{error && <div className={s.error} role="alert">{error}{needsSync && <p>요청이 처리됐을 수 있습니다. 현재 상태를 다시 불러온 후 계속하세요.</p>}<p><Link href="/start" onClick={e => { e.preventDefault(); nav("/start"); }}>← 직업 선택으로</Link></p></div>}{feedback && <p role="status" className={s.feedback}>{feedback}</p>}
      {!game && !error && <section className={s.card}><p className={s.note}>등반을 준비하는 중…</p></section>}
      {game && <>
        <Investigation key={`${game.runId}:${game.floor}`} game={game} busy={disabled} output={output} act={act} />
        <Judgment key={`${game.runId}:${game.floor}:${game.step?.key}`} game={game} busy={disabled} act={act} />
        {game.ending && <section className={`${s.card} ${s.ending}`}><h2>🏳️ {game.ending.title}</h2><p>{game.ending.narrative}</p>{game.ending.badges.length > 0 && <p>획득 칭호: {game.ending.badges.join(" · ")}</p>}<button className={s.primary} disabled={disabled} onClick={() => void act("ranking", {})}>랭킹에 등록</button></section>}
      </>}
    </main>
  </div>;
}
