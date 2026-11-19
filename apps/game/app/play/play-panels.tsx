import { useState } from "react";
import type { Game, Rank } from "./game-api";
import s from "./play.module.css";

export function Investigation({ game, busy, output, act }: { game: Game; busy: boolean; output: string[]; act: (action: string, data: object) => Promise<void> }) {
  const [command, setCommand] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  return <section className={s.card} aria-labelledby="explore-title"><h2 id="explore-title">01 · 기록 탐색</h2><p>{game.problem.objective}</p>
    {game.problem.type === "terminal" ? <>
      <p>가상 기록만 조사합니다. <code>help</code>로 허용 명령을 확인하세요.</p>
      <div className={s.terminal} role="log" aria-label="명령 실행 기록" aria-live="polite">{output.length ? output.map((line, i) => <pre key={i}>{line}</pre>) : <p>아직 실행한 명령이 없습니다.</p>}</div>
      <form onSubmit={e => { e.preventDefault(); if (command.trim()) void act("commands", { command: command.trim() }); }}><label htmlFor="command">명령 입력</label><div className={s.row}><input id="command" value={command} onChange={e => setCommand(e.target.value)} maxLength={256} autoComplete="off" spellCheck={false} disabled={busy || game.cleared} placeholder="help" /><button disabled={busy || game.cleared || !command.trim()}>실행</button></div></form>
    </> : <p>판단에 필요한 증거를 선택한 뒤 확인하세요.</p>}
    <h3>수집한 증거</h3>{!game.evidence.length && <p>명령을 실행하면 발견한 증거가 여기에 나타납니다.</p>}
    {game.evidence.map(e => <div className={s.evidence} key={e.number}>{game.problem.type === "choice" ? <label><input type="checkbox" checked={selected.includes(e.number)} disabled={busy || game.cleared} onChange={() => setSelected(ids => ids.includes(e.number) ? ids.filter(id => id !== e.number) : [...ids, e.number])} /> {e.number} · {e.title}</label> : <strong>{e.number} · {e.title}</strong>}<p>{e.detail}</p><small>{e.tag}</small></div>)}
    {game.problem.type === "choice" && <button disabled={busy || !selected.length || game.cleared} onClick={() => void act("evidence", { evidenceIds: selected })}>선택한 증거 확인</button>}
  </section>;
}
export function Judgment({ game, busy, act }: { game: Game; busy: boolean; act: (action: string, data: object) => Promise<void> }) {
  const [choice, setChoice] = useState("");
  return <section className={s.card} aria-labelledby="judgment-title"><h2 id="judgment-title">02 · 분류 → 판정 → 조치</h2><p>완료한 판정 {game.progress} / 3</p>
    {!game.canJudge && !game.cleared && <p>먼저 기록을 조사하고 필요한 증거를 확인하세요.</p>}
    {game.step && !game.cleared && <form onSubmit={e => { e.preventDefault(); if (choice) void act("answers", { step: game.step!.key, choiceId: choice }); }}><fieldset disabled={busy || !game.canJudge}><legend>{game.step.question}</legend>{game.step.choices.map(c => <label className={s.option} key={c.id}><input type="radio" name="answer" value={c.id} checked={choice === c.id} onChange={() => setChoice(c.id)} /> {c.label}</label>)}<button disabled={!choice}>판정 제출</button></fieldset></form>}
    {game.cleared && <><h3>봉인 해제 · 관문 통과</h3>{game.flag && <code className={s.flag}>{game.flag}</code>}{game.floor < 10 && <button disabled={busy} onClick={() => void act("next", {})}>다음 층으로 →</button>}</>}
  </section>;
}
export function Companion({ game, busy, act }: { game: Game; busy: boolean; act: (action: string, data: object) => Promise<void> }) {
  return <section className={s.card}><h2>라온 · 동료의 의견</h2><blockquote>{game.problem.allyOpening}</blockquote><p>동료의 의견도 기록과 대조해 보세요.</p><p>신뢰도 {game.trust} / 100</p><progress value={game.trust} max={100} aria-label="라온 신뢰도" />
    {game.hints.map(h => <div className={s.evidence} key={h.level}><strong>힌트 {h.level} · {h.source === "rule" ? "규칙 기반 안내" : "AI 응답"}</strong><p>{h.text}</p></div>)}
    <button disabled={busy || game.hints.length >= 3 || game.cleared} onClick={() => void act("hints", {})}>다음 힌트 요청 ({game.hints.length}/3)</button><small>힌트당 층 점수 −3 · 신뢰도 −1</small>
  </section>;
}
export function Rankings({ ranks }: { ranks: Rank[] | null }) {
  return <>{ranks !== null && (ranks.length ? <div className={s.tableWrap}><table><caption>서버에 기록된 등반 순위</caption><thead><tr>{["순위", "이름", "층", "점수", "신뢰도", "힌트"].map(h => <th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{ranks.map(r => <tr key={r.rank}><td>{r.rank}</td><td>{r.name}</td><td>{r.floor}</td><td>{r.score}</td><td>{r.trust}</td><td>{r.hints}</td></tr>)}</tbody></table></div> : <p>아직 등록된 등반 기록이 없습니다.</p>)}</>;
}
