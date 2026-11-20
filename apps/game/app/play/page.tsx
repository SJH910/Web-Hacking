"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { gameRequest, isRanks, readSave, request, SAVE_KEY, type Game, type Rank } from "./game-api";
import { Companion, Investigation, Judgment, Rankings } from "./play-panels";
import { recordEnding } from "../collection";
import { useFadeNav } from "../use-fade-nav";
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
  const [ranks, setRanks] = useState<Rank[] | null>(null);
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
  async function ranking() {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try { const result = await request("rankings"); if (!isRanks(result)) throw new Error("랭킹 응답 형식이 올바르지 않습니다."); setRanks(result); }
    catch (e) { setError(e instanceof Error ? e.message : "랭킹을 불러오지 못했습니다."); }
    finally { lock.current = false; setBusy(false); }
  }
  const disabled = busy || needsSync;
  const trust = game?.trust ?? 60;
  const raonTier = trust >= 80 ? "high" : trust >= 50 ? "mid" : "low";
  const playerTier = game?.cleared ? "win" : "idle";
  return <div className={`${s.shell} ${leaving ? s.leaving : ""}`}>
    <a className={s.skip} href="#play-main">게임으로 건너뛰기</a>
    <header className={s.top}>
      <Link href="/start" className={s.back} onClick={e => { e.preventDefault(); nav("/start"); }}>← 직업 선택</Link>
      <span className={s.badge}>🛡️ 수호자</span>
    </header>

    {game && <div className={s.floorbar}><span className={s.floortag}>⛰ 제 {game.floor} 층</span><span className={s.status}>{game.cleared ? "통과" : "조사 중"}</span></div>}
    <h1 ref={heading} tabIndex={-1} className={s.title}>{game ? game.problem.title : "새로운 등반을 시작하세요"}</h1>
    <p className={s.sub}>{game ? `${game.problem.difficulty} · 분류→판정→조치로 봉인을 해제하세요` : "기록을 탐색하고 증거로 관문을 여세요 · 합성·격리"}</p>

    {game && <div className={s.stage}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className={s.player} src={`/game/sprites/player_${playerTier}.png`} alt="플레이어" />
      <div className={s.speech}><span className={s.who}>라온</span>{game.problem.allyOpening}</div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className={s.raon} src={`/game/sprites/raon_${raonTier}.png`} alt="라온" />
    </div>}

    <main id="play-main" className={s.main} aria-busy={busy}>
      <div role="status" className={s.note}>{busy ? "기록을 불러오는 중…" : storageNote}</div>{error && <div className={s.error} role="alert">{error}{needsSync && <p>요청이 처리됐을 수 있습니다. 현재 상태를 다시 불러온 후 계속하세요.</p>}<p><Link href="/start" onClick={e => { e.preventDefault(); nav("/start"); }}>← 직업 선택으로</Link></p></div>}{feedback && <p role="status" className={s.feedback}>{feedback}</p>}
      {!game && !error && <section className={s.card}><p className={s.note}>등반을 준비하는 중…</p></section>}
      {game && <>
        <section className={s.summary} aria-label="등반 현황"><span>점수 <b>{game.score}</b></span><span>신뢰도 <b>{game.trust}</b></span><span>오답 <b>{game.totalWrong}</b></span><span>힌트 <b>{game.totalHints}</b></span></section>
        <Investigation key={`${game.runId}:${game.floor}`} game={game} busy={disabled} output={output} act={act} />
        <Judgment key={`${game.runId}:${game.floor}:${game.step?.key}`} game={game} busy={disabled} act={act} />
        <Companion game={game} busy={disabled} act={act} />
        {game.ending && <section className={`${s.card} ${s.ending}`}><h2>🏳️ {game.ending.title}</h2><p>{game.ending.narrative}</p><p className={s.note}>최종 점수 {game.score} · 신뢰도 보너스 {game.ending.bonus} · 오답 {game.totalWrong} · 힌트 {game.totalHints}</p>{game.ending.badges.length > 0 && <p>획득 칭호: {game.ending.badges.join(" · ")}</p>}<button className={s.primary} disabled={disabled} onClick={() => void act("ranking", {})}>등반 기록 등록</button></section>}
      </>}
      <section id="rankings" className={s.card}><h2>랭킹</h2><p className={s.note}>총점 → 신뢰도 → 힌트 사용 수 순서로 비교합니다.</p><button disabled={busy} onClick={() => void ranking()}>랭킹 불러오기</button><Rankings ranks={ranks} /></section>
    </main>
  </div>;
}
