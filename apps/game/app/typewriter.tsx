"use client";

// 텍스트가 바뀌면 한 글자씩 타이핑되는 효과. 라온 말풍선용.
import { useEffect, useState } from "react";

export function Typewriter({ text, speed = 24 }: { text: string; speed?: number }) {
  const [shown, setShown] = useState(text);

  useEffect(() => {
    // reduced-motion이면 즉시 표시
    if (typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setShown(text);
      return;
    }
    setShown("");
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);

  return <>{shown}</>;
}
