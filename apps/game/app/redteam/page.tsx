"use client";

// 용범의 탑 — 파훼자(레드팀) 모드. 백엔드 /api/redteam 에 붙는다.
// 등반: 각 층마다 중복 없이 랜덤 출제(X3, 시드 기반). 선택 불가 — FLAG 캡처 시 다음 층.
// 각 챌린지는 '실제 웹페이지처럼' 렌더되고, 페이지 안에서 링크 클릭·폼 입력으로 상호작용한다.
// 점진 전환: 기존 블루팀 게임(play/)과 별도 라우트. 합성·결정적, 실제 요청 없음.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import styles from "./redteam.module.css";

type StartInfo = {
  challengeId: string; title: string; siteName: string; difficulty: string; owasp: string;
  tier: string; entry: string; session: { user: string; cookies: string };
  allyOpening: string; hintCount: number; floor: number; floors: number;
};
type VisitResp = {
  status: number; title: string; html: string; owner: string | null;
  sourceComments: string[]; exploited: boolean; flagRevealed: boolean;
};

export default function RedTeam() {
  const [seed, setSeed] = useState<string>("");
  const [info, setInfo] = useState<StartInfo | null>(null);
  const [cid, setCid] = useState<string>("");
  const [path, setPath] = useState("/");
  const [resp, setResp] = useState<VisitResp | null>(null);
  const [showSrc, setShowSrc] = useState(false);
  const [used, setUsed] = useState(0);
  const [hints, setHints] = useState<string[]>([]);
  const [flag, setFlag] = useState("");
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  const [cleared, setCleared] = useState(false);
  const [wrong, setWrong] = useState(false);

  const go = useCallback(async (p: string, data?: Record<string, string>, forCid?: string) => {
    const useCid = forCid || cid;
    if (!useCid) return;
    const target = (p || "/").trim();
    setPath(target);
    const r = await fetch(`/api/redteam/${useCid}/visit`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: target, data }),
    });
    setResp(await r.json());
    setShowSrc(false);
  }, [cid]);

  const loadFloor = useCallback(async (s: string, n: number) => {
    const info: StartInfo = await (await fetch(`/api/redteam/floor/${s}/${n}`)).json();
    setInfo(info); setCid(info.challengeId);
    setUsed(0); setHints([]); setFlag(""); setResult(null); setCleared(false);
    await go(info.entry, undefined, info.challengeId);
  }, [go]);

  // 새 등반: 시드 발급 → 1층
  const newClimb = useCallback(async () => {
    const c = await (await fetch("/api/redteam/climb")).json();
    setSeed(c.seed);
    await loadFloor(c.seed, 1);
  }, [loadFloor]);

  useEffect(() => { void newClimb(); }, [newClimb]);

  function onViewportClick(e: React.MouseEvent) {
    const a = (e.target as HTMLElement).closest("a");
    if (a) {
      const href = a.getAttribute("href") || "";
      if (href.startsWith("/")) { e.preventDefault(); void go(href); }
    }
  }
  function onViewportSubmit(e: React.FormEvent) {
    const form = (e.target as HTMLElement).closest("form");
    if (!form) return;
    e.preventDefault();
    const action = form.getAttribute("action") || path;
    const data: Record<string, string> = {};
    form.querySelectorAll("input, textarea, select").forEach((el) => {
      const n = (el as HTMLInputElement).name;
      if (n) data[n] = (el as HTMLInputElement).value;
    });
    void go(action, data);
  }

  async function getHint() {
    if (!info || used >= info.hintCount) return;
    const lv = used + 1;
    const d = await (await fetch(`/api/redteam/${cid}/hint`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ level: lv }),
    })).json();
    if (d.text) { setHints((h) => [...h, `힌트 ${lv}: ${d.text}`]); setUsed(lv); }
  }
  async function submitFlag() {
    const d = await (await fetch(`/api/redteam/${cid}/submit`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ flag: flag.trim() }),
    })).json();
    if (d.cleared) { setResult({ ok: true, text: `✅ 통과! — ${d.wrapUp}` }); setCleared(true); }
    else { setResult({ ok: false, text: `❌ 틀렸습니다 — ${d.message || "실패"}` }); setWrong(true); setTimeout(() => setWrong(false), 500); }
  }

  const isLast = info ? info.floor >= info.floors : false;
  // 스프라이트 상태: 정답(통과)·오답에 반응
  const playerState = result?.ok ? "win" : result && !result.ok ? "fail" : "idle";
  const raonState = result?.ok ? "high" : result && !result.ok ? "low" : "mid";
  const src = resp
    ? resp.html + (resp.sourceComments.length ? "\n\n<!-- 주석 -->\n" + resp.sourceComments.map((c) => `<!-- ${c} -->`).join("\n") : "")
    : "";

  return (
    <div className={styles.wrap}>
      <header className={styles.top}>
        <Link href="/start" className={styles.back}>← 직업 선택</Link>
        <span className={styles.badge}>🗡️ 파훼자</span>
      </header>

      <div className={styles.floorbar}>
        <span className={styles.floortag}>⛰ 제 {info?.floor ?? "-"} 층 <span className={styles.of}>/ 총 {info?.floors ?? "-"} 층</span></span>
        <div className={styles.progress}>
          {Array.from({ length: info?.floors ?? 0 }).map((_, i) => (
            <i key={i} className={i + 1 < (info?.floor ?? 0) ? styles.pDone : i + 1 === info?.floor ? styles.pNow : styles.pNext} />
          ))}
        </div>
      </div>

      <h1 className={styles.title}>{info ? `${info.title} — ${info.owasp}` : "등반 준비 중…"}</h1>
      <p className={styles.sub}>
        {info ? `사이트: ${info.siteName} · 난이도 ${info.difficulty} · 티어 ${info.tier}` : ""} · 랜덤 출제 · 합성·격리 · 실제 요청 없음
      </p>

      <div className={styles.stage}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className={styles.player} src={`/game/sprites/player_${playerState}.png`} alt="플레이어" />
        <div className={styles.speech}><span className={styles.who}>라온</span>{info?.allyOpening ?? "…"}</div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className={styles.raonSprite} src={`/game/sprites/raon_${raonState}.png`} alt="라온" />
      </div>

      <section className={styles.browser}>
        <div className={styles.chrome}>
          <span className={styles.dots}><i /><i /><i /></span>
          <input className={styles.addr} value={path} onChange={(e) => setPath(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && go(path)} spellCheck={false} />
          <button className={styles.btn} onClick={() => go(path)}>이동</button>
          <button className={styles.btn} onClick={() => setShowSrc((s) => !s)}>소스</button>
        </div>
        {resp && (
          <div className={styles.statusbar}>
            HTTP <span className={resp.status === 200 ? styles.ok : styles.warn}>{resp.status}</span>
            {resp.owner && <> · 소유자 <b>{resp.owner}</b></>}
            {info && <> · 세션 {info.session.user} · {info.session.cookies}</>}
          </div>
        )}
        <div className={styles.viewport} onClick={onViewportClick} onSubmit={onViewportSubmit}
             dangerouslySetInnerHTML={{ __html: resp?.html ?? "불러오는 중…" }} />
        {resp?.exploited && (
          <div className={styles.exploit}>⚡ 익스플로잇 성공 — 방어가 뚫렸습니다. 본문에서 FLAG를 찾으세요.</div>
        )}
        {showSrc && <pre className={styles.src}>{src}</pre>}
      </section>

      <section className={styles.panel}>
        <div className={styles.bar}>
          <b>라온에게 힌트 요청</b>
          <button className={styles.btn} onClick={getHint}>힌트 ({info ? info.hintCount - used : 0} 남음)</button>
        </div>
        {hints.map((hh, i) => <div key={i} className={styles.hint}>{hh}</div>)}
      </section>

      <section className={`${styles.panel} ${wrong ? styles.shake : ""}`}>
        <b>FLAG 제출</b>
        <div className={styles.bar} style={{ marginTop: 6 }}>
          <input className={styles.flagInput} value={flag} onChange={(e) => setFlag(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && submitFlag()} placeholder="FLAG{...}" disabled={cleared} />
          <button className={styles.primary} onClick={submitFlag} disabled={cleared}>제출</button>
        </div>
        {result && <div className={result.ok ? styles.resultOk : styles.resultNo}>{result.text}</div>}
        {cleared && !isLast && (
          <button className={styles.next} onClick={() => loadFloor(seed, (info?.floor ?? 1) + 1)}>다음 층으로 →</button>
        )}
        {cleared && isLast && (
          <div className={styles.summit}>🏳️ 정상 등정 완료! 모든 층을 돌파했습니다.
            <button className={styles.next} onClick={newClimb}>새 등반 시작</button>
          </div>
        )}
      </section>

      <p className={styles.note}>학습용 가상 환경. 모든 페이지·데이터·세션은 합성이며 실제 네트워크 요청을 보내지 않습니다.</p>
    </div>
  );
}
