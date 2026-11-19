export type Evidence = { number: string; title: string; detail: string; tag: string };
export type Step = { key: "classify" | "verdict" | "action"; question: string; choices: { id: string; label: string }[] };
export type Game = {
  runId: string; revision: number; seed: string; floor: number; score: number; trust: number;
  progress: number; cleared: boolean; canJudge: boolean; totalWrong: number; totalHints: number;
  problem: { id: string; title: string; type: "terminal" | "choice"; difficulty: string; objective: string; allyOpening: string };
  evidence: Evidence[]; step: Step | null; flag?: string;
  hints: { level: number; text: string; source: "rule" | "llm" }[];
  ending?: { title: string; narrative: string; badges: string[]; bonus: number };
};
export type Result = { state: Game; output?: string; feedback?: string; correct?: boolean };
export type Rank = { rank: number; name: string; floor: number; score: number; trust: number; hints: number };
const object = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null;
const text = (v: unknown): v is string => typeof v === "string";
const number = (v: unknown, min = 0, max = Number.MAX_SAFE_INTEGER) => Number.isSafeInteger(v) && (v as number) >= min && (v as number) <= max;
export function isGame(v: unknown): v is Game {
  if (!object(v) || !text(v.runId) || !/^[a-zA-Z0-9_-]{1,128}$/.test(v.runId) || !text(v.seed) || !number(v.revision) || !number(v.floor, 1, 10) || !number(v.score) || !number(v.trust, 0, 100) || !number(v.progress, 0, 3) || !number(v.totalWrong) || !number(v.totalHints)) return false;
  if (typeof v.cleared !== "boolean" || typeof v.canJudge !== "boolean" || !object(v.problem)) return false;
  const p = v.problem;
  if (![p.id, p.title, p.difficulty, p.objective, p.allyOpening].every(text) || !["terminal", "choice"].includes(String(p.type))) return false;
  if (!Array.isArray(v.evidence) || !v.evidence.every(e => object(e) && [e.number, e.title, e.detail, e.tag].every(text))) return false;
  if (!Array.isArray(v.hints) || !v.hints.every(h => object(h) && number(h.level, 1, 3) && text(h.text) && ["rule", "llm"].includes(String(h.source)))) return false;
  if (v.flag !== undefined && !text(v.flag)) return false;
  if (v.step !== null && (!object(v.step) || !["classify", "verdict", "action"].includes(String(v.step.key)) || !text(v.step.question) || !Array.isArray(v.step.choices) || !v.step.choices.length || !v.step.choices.every(c => object(c) && text(c.id) && text(c.label)))) return false;
  if (v.ending !== undefined && (!object(v.ending) || !text(v.ending.title) || !text(v.ending.narrative) || !number(v.ending.bonus) || !Array.isArray(v.ending.badges) || !v.ending.badges.every(text))) return false;
  return true;
}
export function isRanks(v: unknown): v is Rank[] {
  return Array.isArray(v) && v.every(r => object(r) && number(r.rank, 1) && text(r.name) && number(r.floor, 1, 10) && number(r.score) && number(r.trust, 0, 100) && number(r.hints));
}
export async function request(path: string, body?: unknown): Promise<unknown> {
  const response = await fetch(`/api/game/${path}`, {
    method: body === undefined ? "GET" : "POST", cache: "no-store",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error(response.status === 404 ? "게임 서버가 아직 연결되지 않았습니다. 잠시 후 다시 시도해 주세요." : `요청을 완료하지 못했습니다 (${response.status}). 상태를 다시 불러와 주세요.`);
  return response.json();
}
export async function gameRequest(path: string, body?: unknown): Promise<Result> {
  const result = await request(path, body);
  if (!object(result) || !isGame(result.state) || (result.output !== undefined && !text(result.output)) || (result.feedback !== undefined && !text(result.feedback)) || (result.correct !== undefined && typeof result.correct !== "boolean")) throw new Error("게임 응답 형식을 확인할 수 없습니다. 다시 불러와 주세요.");
  return result as Result;
}
export const SAVE_KEY = "tower.run.v1";
// 점수 등은 복원 권한이 없다. 서버에서 재검증할 실행 ID만 저장한다.
export function readSave(raw: string | null): string | null {
  if (!raw) return null;
  try { const value: unknown = JSON.parse(raw); return object(value) && value.version === 1 && text(value.runId) && /^[a-zA-Z0-9_-]{1,128}$/.test(value.runId) ? value.runId : null; } catch { return null; }
}
