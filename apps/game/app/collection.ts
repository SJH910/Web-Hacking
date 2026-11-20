"use client";

// 본 엔딩·수집한 칭호를 브라우저(localStorage)에 모은다. 로컬·뷰어 전용 수집 기록.
// 엔딩 도달 시 recordEnding, 기록 탭에서 readCollection으로 표시.

const KEY = "ybt-collection";

// game_engine ENDINGS 제목과 정확히 일치해야 함(미수집 판별용).
export const ALL_ENDINGS = [
  "공명(共鳴)", "우직한 동행", "냉철한 등반가", "무명(無名)의 등정", "고독한 해결사", "홀로 오른 탑",
];
export const ALL_BADGES = ["무결", "침묵의 등반"];

export type Collection = { endings: string[]; badges: string[] };

export function readCollection(): Collection {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const d = JSON.parse(raw);
      return {
        endings: Array.isArray(d.endings) ? d.endings.filter((x: unknown) => typeof x === "string") : [],
        badges: Array.isArray(d.badges) ? d.badges.filter((x: unknown) => typeof x === "string") : [],
      };
    }
  } catch { /* 비공개 모드·차단 등 */ }
  return { endings: [], badges: [] };
}

export function recordEnding(ending: string, badges: string[] = []) {
  try {
    const c = readCollection();
    const e = new Set(c.endings);
    if (ending) e.add(ending);
    const b = new Set(c.badges);
    badges.forEach((x) => { if (x) b.add(x); });
    localStorage.setItem(KEY, JSON.stringify({ endings: [...e], badges: [...b] }));
  } catch { /* 저장 실패는 무시(수집은 편의 기능) */ }
}
