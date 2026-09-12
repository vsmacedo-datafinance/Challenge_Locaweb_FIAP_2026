import type { ReactNode } from "react";

/** Divide um texto em "**negrito**" nos marcadores vindos da API e retorna nodes prontos para renderizar. */
export function renderBold(text: string): ReactNode[] {
  return text.split("**").map((part, i) =>
    i % 2 === 1 ? (
      <b key={i} className="text-txt font-semibold">
        {part}
      </b>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}
