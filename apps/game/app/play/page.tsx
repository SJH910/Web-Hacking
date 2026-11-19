"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { gameRequest, isRanks, readSave, request, SAVE_KEY, type Game, type Rank } from "./game-api";
import { Companion, Investigation, Judgment, Rankings } from "./play-panels";
import s from "./play.module.css";

export default function Play() {
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
  return <div className={s.shell}><a className={s.skip} href="#play-main">게임으로 건너뛰기</a><header className={s.header}><Link href="/">♜ 용범의 탑</Link><nav aria-label="게임 메뉴"><Link href="/">기존 데모</Link><Link href="/intro">인트로</Link><a href="#rankings">랭킹</a></nav></header>
    <main id="play-main" className={s.main} aria-busy={busy}><span className={s.kicker}>THE TOWER · 증거로 여는 열 개의 문</span><h1 ref={heading} tabIndex={-1}>{game ? `${game.floor}층 · ${game.problem.title}` : "새로운 등반을 시작하세요"}</h1><p>기록을 탐색하고, 분류·판정·조치로 봉인을 해제하세요.</p>
      <section className={s.toolbar} aria-label="등반 관리"><button disabled={busy} onClick={() => saved || game ? setConfirmNew(true) : void load("runs", { requestId: crypto.randomUUID() })}>새 등반</button><button disabled={busy || !saved} onClick={() => saved && void load(`runs/${encodeURIComponent(saved)}`)}>저장한 등반 이어하기</button>{game && <button disabled={busy} onClick={() => void load(`runs/${encodeURIComponent(game.runId)}`)}>현재 상태 다시 불러오기</button>}</section>
      {confirmNew && <section className={s.card} aria-label="새 등반 확인"><p>새 등반이 생성되면 이어하기 기록이 바뀝니다. 계속할까요?</p><div className={s.row}><button disabled={busy} onClick={() => void load("runs", { requestId: crypto.randomUUID() })}>새 등반 시작</button><button disabled={busy} onClick={() => setConfirmNew(false)}>취소</button></div></section>}
      <div role="status">{busy ? "기록을 불러오는 중…" : storageNote}</div>{error && <div className={s.error} role="alert">{error}{needsSync && <p>요청이 처리됐을 수 있습니다. 현재 상태를 다시 불러온 후 계속하세요.</p>}</div>}<p role="status">{feedback}</p>
      {!game && <section className={s.card}><h2>탐험 준비</h2><p>새 등반을 시작하거나 저장한 기록을 불러오세요. 첫 3층은 쉬운 문제로 시작하며, 한 번의 등반에서 같은 문제는 반복되지 않습니다.</p><p>가상 터미널과 증거 선택 문제를 모두 만나게 됩니다. 판단은 수집한 기록을 바탕으로 하세요.</p></section>}
      {game && <><section className={s.summary} aria-label="등반 현황"><strong>{game.floor} / 10층 · {game.cleared ? "통과" : "조사 중"}</strong><span>점수 {game.score}</span><span>신뢰도 {game.trust}</span><span>오답 {game.totalWrong} · 힌트 {game.totalHints}</span><progress max={10} value={game.floor - 1 + Number(game.cleared)} aria-label="통과한 층" /></section>
        <div className={s.layout}><div className={s.column}><Investigation key={`${game.runId}:${game.floor}`} game={game} busy={disabled} output={output} act={act} /><Judgment key={`${game.runId}:${game.floor}:${game.step?.key}`} game={game} busy={disabled} act={act} /></div><aside><Companion game={game} busy={disabled} act={act} /><p>문제 유형: {game.problem.type === "terminal" ? "가상 터미널" : "증거 선택"} · {game.problem.difficulty}</p><small>출제 시드: {game.seed}</small></aside></div>
        {game.ending && <section className={s.card}><h2>{game.ending.title}</h2><p>{game.ending.narrative}</p><p>최종 점수 {game.score} · 신뢰도 보너스 {game.ending.bonus} (총점에 포함)</p><p>총 오답 {game.totalWrong} · 힌트 {game.totalHints}</p><p>{game.ending.badges.join(" · ")}</p><button disabled={disabled} onClick={() => void act("ranking", {})}>등반 기록 등록</button></section>}
      </>}
      <section id="rankings" className={s.card}><h2>등반 기록 · 랭킹</h2><p>총점 → 신뢰도 → 힌트 사용 수 순서로 비교합니다.</p><button disabled={busy} onClick={() => void ranking()}>랭킹 불러오기</button><Rankings ranks={ranks} /></section>
    </main></div>;
}
