import type { Mode, Scenario } from "./scenarios";
import styles from "./page.module.css";

export type RunStatus = "idle" | "running" | "ready" | "error" | "complete";

type Props = {
  scenario: Scenario; mode: Mode; status: RunStatus; selected: string[];
  feedback: string; showHint: boolean; onSelect: (id: string) => void;
  onJudge: () => void; onRetry: () => void;
};

export default function AnalysisResults({ scenario, mode, status, selected, feedback, showHint, onSelect, onJudge, onRetry }: Props) {
  return (
    <section id="evidence" className={styles.panel} aria-labelledby="results-title" aria-busy={status === "running"}>
      <div className={styles.panelHeading}>
        <div><span className={styles.eyebrow}>02 / EVIDENCE</span><h2 id="results-title">결과와 증거 기록</h2></div>
        <span className={styles.tag}>{status === "complete" ? "✓ 검증 완료" : "합성 데이터"}</span>
      </div>
      <div role="status" aria-live="polite">
        {status === "idle" && <div className={styles.empty}><span className={styles.emptyIcon} aria-hidden="true">▤</span><h3>첫 번째 단서를 기다리고 있어요</h3><p>시나리오와 조사 방식을 선택하고<br />‘관문 조사 시작’을 눌러 기록을 확인하세요.</p><span className={styles.muted}>기록 확인 → 증거 선택 → 관문 판정</span></div>}
        {status === "running" && <div className={styles.empty}><span className={styles.loader} /><h3>준비된 기록을 불러오는 중</h3><p>{scenario.title}의 합성 데이터를 확인하고 있습니다.</p></div>}
        {status === "error" && <div className={styles.empty}><span className={styles.errorText}>! 기록을 불러오지 못했습니다</span><p>오류 체험으로 이번 실행을 중단했습니다. 결과는 생성되지 않았습니다.</p><button className={styles.primary} onClick={onRetry}>다시 시도</button></div>}
      </div>
      {(status === "ready" || status === "complete") && <div className={styles.results}>
        <div className={styles.resultSummary}><strong>✓ {mode === "observe" ? "기록 관찰" : "준비된 행동 재생"} 완료</strong><span>증거 {scenario.evidence.length}개 발견</span></div>
        <details className={styles.logs} open><summary>{mode === "observe" ? "원본 합성 로그" : "시뮬레이션 재생 기록"}</summary><pre>{(mode === "observe" ? scenario.observation : scenario.simulation).join("\n")}</pre></details>
        <fieldset className={styles.evidenceList} disabled={status === "complete"}>
          <legend>판단을 뒷받침하는 증거 2개를 선택하세요</legend>
          {scenario.evidence.map((item, index) => <label className={styles.evidenceItem} key={item.id}>
            <input type="checkbox" checked={selected.includes(item.id)} onChange={() => onSelect(item.id)} />
            <span><span className={styles.source}>증거 0{index + 1} · {item.source}</span><strong>{item.title}</strong><span>{item.detail}</span></span>
          </label>)}
        </fieldset>
        <p className={styles.unknown}><strong>미확인 항목</strong> {scenario.unconfirmed}</p>
        {showHint && <p className={styles.hint}><strong>길잡이 힌트</strong> {scenario.hint}</p>}
        <div className={styles.judgeRow}><span>{selected.length} / 2개 선택</span><button className={styles.primary} disabled={selected.length === 0 || status === "complete"} onClick={onJudge}>{status === "complete" ? "✓ 관문 검증 완료" : "선택한 증거로 판정하기 →"}</button></div>
        <div aria-live="polite">{feedback && <p className={status === "complete" ? styles.success : styles.errorMessage}>{feedback}</p>}</div>
      </div>}
    </section>
  );
}
