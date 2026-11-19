export type Mode = "observe" | "simulate";
export type Evidence = { id: string; title: string; detail: string; source: string };
export type Scenario = {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  objective: string;
  evidence: Evidence[];
  requiredIds: string[];
  observation: string[];
  simulation: string[];
  unconfirmed: string;
  opinion: string;
  confidence: number;
  hint: string;
};

export const scenarios: Scenario[] = [
  {
    id: "archive", title: "기록 보관소", description: "반복된 접근 기록 속에서 권한 검사의 흔적을 찾습니다.", difficulty: "쉬움",
    objective: "반복 요청만으로 침입을 단정할 수 있는지, 접근 결과를 근거로 판단하세요.",
    evidence: [
      { id: "a1", title: "같은 세션의 반복 요청", detail: "합성 세션 S-07이 보관소 열람을 세 번 요청했습니다.", source: "접근 로그 · 01–03" },
      { id: "a2", title: "모든 열람 요청이 거부됨", detail: "세 요청 모두 403으로 끝났고, 문서 반환 건수는 0입니다.", source: "응답 로그 · 01–03" },
      { id: "a3", title: "정상적인 기록 백업", detail: "정기 백업 작업은 다른 세션 S-02에서 정상 종료됐습니다.", source: "작업 로그 · 04" },
    ],
    requiredIds: ["a1", "a2"],
    observation: ["09:41:01  S-07  archive.read  403  documents=0", "09:41:03  S-07  archive.read  403  documents=0", "09:41:05  S-07  archive.read  403  documents=0", "09:42:00  S-02  backup       200  scheduled=true"],
    simulation: ["준비된 행동: 방문자 역할로 보관소 열람", "권한 검사: 열람 권한 없음", "재생 결과: 403 · 문서 반환 없음"],
    unconfirmed: "요청자의 의도는 이 기록만으로 확인할 수 없습니다.",
    opinion: "같은 요청이 반복돼서 침입에 성공한 것 같아. 하지만 응답 기록까지 살펴봐야 확실하겠어.", confidence: 42,
    hint: "요청 횟수와 실제 문서 반환 여부를 함께 보여주는 두 증거를 선택하세요.",
  },
  {
    id: "login", title: "유리문 로그인", description: "인증 성공과 관리자 권한을 구분해 확인합니다.", difficulty: "보통",
    objective: "로그인한 방문자가 관리자 메뉴에 접근할 수 있는지 판단하세요.",
    evidence: [
      { id: "l1", title: "방문자 로그인 성공", detail: "합성 계정 visitor-03의 인증은 성공했지만 역할은 visitor입니다.", source: "인증 로그 · 01" },
      { id: "l2", title: "관리자 메뉴 접근 거부", detail: "동일 계정의 관리자 메뉴 요청은 역할 검사에서 거부됐습니다.", source: "권한 로그 · 02" },
      { id: "l3", title: "언어 설정 저장", detail: "화면 표시 언어가 한국어로 저장되었습니다. 권한과는 관계없습니다.", source: "설정 로그 · 03" },
    ],
    requiredIds: ["l1", "l2"],
    observation: ["10:03:01  visitor-03  sign_in      200  role=visitor", "10:03:04  visitor-03  admin.view   403  required=admin", "10:03:06  visitor-03  preferences  200  locale=ko"],
    simulation: ["준비된 행동: 로그인한 방문자로 관리자 메뉴 열기", "역할 대조: visitor ≠ admin", "재생 결과: 403 · 관리자 화면 표시 안 됨"],
    unconfirmed: "관리자 계정 자체의 안전성은 이 시나리오의 검토 범위가 아닙니다.",
    opinion: "로그인 성공이 관리자 권한까지 뜻하는 건 아닐지도 몰라. 역할 검사 결과를 같이 보자.", confidence: 76,
    hint: "인증 결과와 관리자 메뉴의 권한 검사 결과를 함께 선택하세요.",
  },
  {
    id: "greenhouse", title: "제어실 온실", description: "저장된 화면과 최신 응답을 대조합니다.", difficulty: "보통",
    objective: "오래된 화면에 표시된 온도를 현재 온도로 믿을 수 있는지 판단하세요.",
    evidence: [
      { id: "g1", title: "오래된 화면의 온도", detail: "저장된 화면은 08:00에 생성되었고 온도를 31도로 표시합니다.", source: "화면 스냅샷 · 01" },
      { id: "g2", title: "최신 응답의 온도", detail: "09:00에 생성된 응답에는 온도 24도와 캐시 사용 안 함이 기록되어 있습니다.", source: "응답 헤더·본문 · 02" },
      { id: "g3", title: "정상 조명 예약", detail: "조명은 매일 07:00에 켜집니다. 현재 온도의 근거는 아닙니다.", source: "예약 기록 · 03" },
    ],
    requiredIds: ["g1", "g2"],
    observation: ["08:00:00  snapshot  temperature=31°C", "09:00:00  response  temperature=24°C  cache-control=no-store", "07:00:00  lighting  schedule=daily  status=on"],
    simulation: ["준비된 행동: 저장 화면과 최신 응답 대조", "생성 시각: 08:00 → 09:00", "재생 결과: 31°C → 24°C · 오래된 화면으로 현재 온도 판단 불가"],
    unconfirmed: "온도가 바뀐 원인은 제공된 기록에서 확인되지 않습니다.",
    opinion: "화면에는 31도로 보여. 지금도 더운 걸까? 이 화면이 언제 만들어졌는지 확인해 줘.", confidence: 51,
    hint: "두 온도 기록의 생성 시각을 비교할 수 있는 증거를 선택하세요.",
  },
];

export function judgeEvidence(scenario: Scenario, selectedIds: string[]): boolean {
  const ids = new Set(selectedIds);
  return ids.size === scenario.requiredIds.length && scenario.requiredIds.every((id) => ids.has(id));
}
