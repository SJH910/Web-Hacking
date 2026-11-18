"use client";

import { FormEvent, useState } from "react";

type Scenario = {
  id: string;
  title: string;
  subtitle: string;
  category: string;
  difficulty: string;
  icon: string;
};

const scenarios: Scenario[] = [
  {
    id: "archive",
    title: "기록 보관소",
    subtitle: "접근 기록에서 수상한 흔적을 찾아보세요.",
    category: "로그 분석",
    difficulty: "쉬움",
    icon: "▤",
  },
  {
    id: "login",
    title: "유리문 로그인",
    subtitle: "가상 로그인 흐름의 권한 설정을 확인하세요.",
    category: "권한 검토",
    difficulty: "보통",
    icon: "⌑",
  },
  {
    id: "greenhouse",
    title: "제어실 온실",
    subtitle: "요청 기록과 응답 헤더의 단서를 대조하세요.",
    category: "응답 검토",
    difficulty: "보통",
    icon: "⌘",
  },
];

const findings = [
  {
    number: "01",
    title: "반복된 접근 시도",
    detail: "같은 세션에서 짧은 시간 동안 요청이 이어졌습니다.",
    tag: "접근 기록",
    icon: "↗",
  },
  {
    number: "02",
    title: "응답 코드의 변화",
    detail: "정상 응답 뒤에 권한 관련 응답이 기록되어 있습니다.",
    tag: "응답 기록",
    icon: "⌁",
  },
  {
    number: "03",
    title: "검토할 권한 정보",
    detail: "한 항목의 역할 정보가 주변 기록과 일치하지 않습니다.",
    tag: "권한 단서",
    icon: "◇",
  },
];

export default function Home() {
  const [selectedScenario, setSelectedScenario] = useState(scenarios[0].id);
  const [mode, setMode] = useState<"observe" | "simulate">("observe");
  const [isRunning, setIsRunning] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [hintLevel, setHintLevel] = useState("기본");
  const [message, setMessage] = useState("");
  const [chatReply, setChatReply] = useState("");

  const scenario =
    scenarios.find((item) => item.id === selectedScenario) ?? scenarios[0];

  function runScenario() {
    if (isRunning) return;
    setIsRunning(true);
    setHasRun(false);
    window.setTimeout(() => {
      setIsRunning(false);
      setHasRun(true);
    }, 850);
  }

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!message.trim()) return;
    setChatReply(
      "음… 기록에 반복된 접근이 있는 건 보여. 그래도 그게 문제의 원인인지는 증거를 더 확인해야 할 것 같아.",
    );
    setMessage("");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="#" aria-label="용범의 탑 홈">
            <span className="brand-mark" aria-hidden="true">
              Y
            </span>
            <span className="brand-name">용범의 탑</span>
            <span className="brand-chip">모험가 기록</span>
          </a>
          <nav className="main-nav" aria-label="주 메뉴">
            <a href="/intro" className="nav-link">
              인트로
            </a>
            <a href="#" className="nav-link">
              탑 지도
            </a>
            <a href="#" className="nav-link active" aria-current="page">
              이번 관문
            </a>
            <a href="#" className="nav-link">
              기억 조각
            </a>
            <a href="#" className="nav-link">
              동료
            </a>
          </nav>
          <div className="topbar-right">
            <span className="floor-pill">
              <span className="floor-dot" />
              제3층
            </span>
            <button className="avatar-button" aria-label="플레이어 메뉴">
              용
            </button>
          </div>
        </div>
      </header>

      <div className="page-wrap">
        <div className="breadcrumb">
          <span>이야기</span>
          <span className="crumb-slash">›</span>
          <span>제3층 · 기록의 문</span>
        </div>

        <section className="page-heading">
          <div>
            <div className="eyebrow">
              <span className="eyebrow-line" />
              MAIN QUEST <span className="eyebrow-divider">/</span> 제3층 관문
            </div>
            <h1>기록의 문을 열어라</h1>
            <p className="page-description">
              흩어진 기억을 모아 봉인을 풀고, 동료의 말을 직접 확인하세요.
            </p>
          </div>
          <div className="progress-card">
            <div className="progress-copy">
              <span>관문의 봉인</span>
              <strong>{hasRun ? "2 / 3" : "1 / 3"}</strong>
            </div>
            <div className="seal-pips" aria-hidden="true">
              <span className="lit" />
              <span className={hasRun ? "lit" : ""} />
              <span />
            </div>
            <div
              className="progress-track"
              role="progressbar"
              aria-label="관문 진행도"
              aria-valuemin={0}
              aria-valuemax={3}
              aria-valuenow={hasRun ? 2 : 1}
            >
              <span className={hasRun ? "progress-fill complete" : "progress-fill"} />
            </div>
          </div>
        </section>

        <section className="safety-banner" aria-label="시뮬레이션 안내">
          <span className="safety-icon" aria-hidden="true">
            <SafetyIcon />
          </span>
          <p>
            <strong>안전한 게임 시뮬레이션입니다.</strong>
            <span>
              {" "}
              아래 시나리오는 합성 데이터만 사용하며 실제 웹사이트에 접속하거나
              요청을 보내지 않습니다.
            </span>
          </p>
          <span className="safe-label">시뮬레이션 전용</span>
        </section>

        <div className="workspace-grid">
          <div className="main-column">
            <section className="panel setup-panel">
              <div className="panel-heading">
                <div>
                  <div className="section-kicker">QUEST BOARD · 임무 선택</div>
                  <h2>어떤 흔적부터 따라갈까요?</h2>
                </div>
                <span className="local-badge">
                  <span /> 탑 안에서만 진행
                </span>
              </div>

              <div className="scenario-list" role="radiogroup" aria-label="시나리오">
                {scenarios.map((item) => (
                  <button
                    className={`scenario-card ${selectedScenario === item.id ? "selected" : ""}`}
                    key={item.id}
                    onClick={() => {
                      setSelectedScenario(item.id);
                      setHasRun(false);
                    }}
                    role="radio"
                    aria-checked={selectedScenario === item.id}
                  >
                    <span className="scenario-icon" aria-hidden="true">
                      {item.icon}
                    </span>
                    <span className="scenario-content">
                      <span className="scenario-title-row">
                        <strong>{item.title}</strong>
                        <span className="difficulty">{item.difficulty}</span>
                      </span>
                      <span className="scenario-description">{item.subtitle}</span>
                      <span className="scenario-category">{item.category}</span>
                    </span>
                    <span className="radio-indicator" aria-hidden="true">
                      {selectedScenario === item.id ? "✓" : ""}
                    </span>
                  </button>
                ))}
              </div>

              <div className="mode-heading">
                <div>
                  <h3>행동 선택</h3>
                  <p>관문 안에서 허용된 행동만 선택할 수 있습니다.</p>
                </div>
                <span className="mode-help">방식 안내 <span aria-hidden="true">ⓘ</span></span>
              </div>
              <div className="mode-options">
                <button
                  className={`mode-card ${mode === "observe" ? "selected" : ""}`}
                  onClick={() => setMode("observe")}
                  aria-pressed={mode === "observe"}
                >
                  <span className="mode-icon observe-icon" aria-hidden="true">
                    ◉
                  </span>
                  <span className="mode-copy">
                    <span className="mode-title">
                      흔적 살피기 <span className="mode-tag passive">관찰</span>
                    </span>
                    <span className="mode-description">
                      남겨진 기록과 장면을 천천히 살핍니다.
                    </span>
                  </span>
                  <span className="mode-check">{mode === "observe" ? "✓ 선택됨" : ""}</span>
                </button>
                <button
                  className={`mode-card ${mode === "simulate" ? "selected" : ""}`}
                  onClick={() => setMode("simulate")}
                  aria-pressed={mode === "simulate"}
                >
                  <span className="mode-icon simulate-icon" aria-hidden="true">
                    ✳
                  </span>
                  <span className="mode-copy">
                    <span className="mode-title">
                      기억 되짚기 <span className="mode-tag replay">상호작용</span>
                    </span>
                    <span className="mode-description">
                      준비된 단서에 질문하고 반응을 확인합니다.
                    </span>
                  </span>
                  <span className="mode-check">{mode === "simulate" ? "✓ 선택됨" : ""}</span>
                </button>
              </div>

              <div className="settings-wrap">
                <button
                  className="settings-toggle"
                  onClick={() => setShowSettings((value) => !value)}
                  aria-expanded={showSettings}
                >
                  <span className={`chevron ${showSettings ? "open" : ""}`}>›</span>
                  모험 설정 <span className="settings-caption">힌트 · 난이도</span>
                </button>
                {showSettings && (
                  <div className="settings-content">
                    <label htmlFor="hint-level">힌트 표시</label>
                    <select
                      id="hint-level"
                      value={hintLevel}
                      onChange={(event) => setHintLevel(event.target.value)}
                    >
                      <option>기본</option>
                      <option>자세히</option>
                      <option>숨김</option>
                    </select>
                    <span>실제 대상이나 네트워크 설정은 변경할 수 없습니다.</span>
                  </div>
                )}
              </div>

              <div className="panel-actions">
                <div className="selection-summary">
                  <span className="summary-icon">✦</span>
                  <span>
                    <strong>{scenario.title}</strong> · {mode === "observe" ? "관찰" : "퍼즐 재생"}
                  </span>
                </div>
                <button className="primary-button" onClick={runScenario} disabled={isRunning}>
                  {isRunning ? (
                    <>
                      <span className="spinner" /> 기록을 살피는 중
                    </>
                  ) : hasRun ? (
                    <>
                      다시 조사하기 <span aria-hidden="true">↻</span>
                    </>
                  ) : (
                    <>
                      관문 조사 시작 <span aria-hidden="true">→</span>
                    </>
                  )}
                </button>
              </div>
            </section>

            <section className="panel results-panel" aria-live="polite">
              {!hasRun && !isRunning ? (
                <div className="empty-state">
                  <span className="empty-illustration" aria-hidden="true">
                    <span className="empty-sparkle">✦</span>
                    <span className="empty-document">▤</span>
                  </span>
                  <div>
                    <h2>아직 발견한 기록이 없습니다</h2>
                    <p>
                      시나리오와 조사 방식을 고른 다음 관문 조사를 시작하세요.
                    </p>
                  </div>
                  <span className="empty-step">첫 번째 단서를 기다리는 중</span>
                </div>
              ) : isRunning ? (
                <div className="loading-state">
                  <span className="loading-orbit" aria-hidden="true">✦</span>
                  <strong>{scenario.title}의 기록을 확인하고 있어요</strong>
                  <span>게임 시나리오 안의 단서를 정리하는 중입니다.</span>
                </div>
              ) : (
                <div className="results-content">
                  <div className="results-heading">
                    <div className="results-title-group">
                      <span className="result-check">✓</span>
                      <div>
                        <div className="section-kicker">조사 완료 · {scenario.category}</div>
                        <h2>{scenario.title}에서 단서를 찾았습니다</h2>
                      </div>
                    </div>
                    <span className="finding-count">발견한 증거 3</span>
                  </div>
                  <div className="findings-list">
                    {findings.map((item) => (
                      <article className="finding-row" key={item.number}>
                        <span className="finding-number">{item.number}</span>
                        <span className="finding-icon" aria-hidden="true">{item.icon}</span>
                        <div className="finding-copy">
                          <h3>{item.title}</h3>
                          <p>{item.detail}</p>
                        </div>
                        <span className="finding-tag">{item.tag}</span>
                      </article>
                    ))}
                  </div>
                  <div className="evidence-note">
                    <span aria-hidden="true">i</span>
                    이 기억 조각은 선택한 관문 시나리오 안에서 발견했습니다.
                  </div>
                </div>
              )}
            </section>
          </div>

          <aside className="side-column">
            <section className="companion-card">
              <div className="companion-header">
                <div className="companion-title">
                  <span className="companion-avatar" aria-hidden="true">
                    <span>ㄹ</span>
                    <i />
                  </span>
                  <div>
                    <h2>라온</h2>
                    <span className="companion-subtitle">길잡이 · 기억이 조금 흐릿하다</span>
                  </div>
                </div>
                <button className="more-button" aria-label="동료 메뉴">···</button>
              </div>
              <div className="trust-row">
                <span>라온의 신뢰</span>
                <strong>64%</strong>
              </div>
              <div className="trust-track"><span /></div>
              <div className="chat-log">
                <div className="chat-time">조금 전</div>
                <div className="chat-bubble">
                  이 층의 기록은 자꾸 뒤섞여… 반복된 흔적부터 살펴보자. 내가 기억하는 게 전부 맞진 않을 수도 있어.
                </div>
                {chatReply && (
                  <div className="chat-bubble companion-reply">{chatReply}</div>
                )}
              </div>
              <form className="chat-form" onSubmit={sendMessage}>
                <label className="sr-only" htmlFor="companion-message">
                  라온에게 질문하기
                </label>
                <input
                  id="companion-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="라온에게 물어보기..."
                />
                <button type="submit" aria-label="메시지 전송" disabled={!message.trim()}>
                  ↑
                </button>
              </form>
              <div className="companion-footnote">
                <span>✦</span> 동료의 말은 증거와 함께 확인하세요.
              </div>
            </section>

            <section className="evidence-card">
              <div className="evidence-card-heading">
                <div>
                  <div className="section-kicker">모험 기록</div>
                  <h2>기억 조각</h2>
                </div>
                <span className="evidence-total">{hasRun ? "3" : "0"} <small>/ 5</small></span>
              </div>
              <div className="evidence-progress">
                <span className={hasRun ? "evidence-progress-fill filled" : "evidence-progress-fill"} />
              </div>
              {hasRun ? (
                <ul className="evidence-mini-list">
                  <li><span className="mini-evidence-icon">↗</span> 반복된 접근 시도 <span>확인</span></li>
                  <li><span className="mini-evidence-icon">⌁</span> 응답 코드의 변화 <span>확인</span></li>
                  <li><span className="mini-evidence-icon">◇</span> 검토할 권한 정보 <span>확인</span></li>
                </ul>
              ) : (
                <div className="evidence-empty">
                  <span className="evidence-lock">◇</span>
                  <p>조사를 시작하면<br />발견한 증거가 여기에 모입니다.</p>
                </div>
              )}
              <button className="text-button" disabled={!hasRun}>
                증거 기록 보기 <span aria-hidden="true">→</span>
              </button>
            </section>

            <div className="floor-note">
              <span className="floor-note-icon">Ⅲ</span>
              <p><strong>제3층 · 기록의 문</strong><br />기억을 믿을 것인가, 기록을 믿을 것인가?</p>
              <span className="note-sparkle">✧</span>
            </div>
          </aside>
        </div>

        <footer className="page-footer">
          <span>용범의 탑 <span className="footer-dot">·</span> 제3층 탐험 기록</span>
          <span>게임 속 가상 시나리오</span>
        </footer>
      </div>
    </main>
  );
}

function SafetyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3.2 19 6v5.1c0 4.5-2.8 7.7-7 9.7-4.2-2-7-5.2-7-9.7V6l7-2.8Z" />
      <path d="m9 12 2 2 4-4.2" />
    </svg>
  );
}
