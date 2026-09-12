import type { ReactNode } from "react";

const TONE_STYLES: Record<string, string> = {
  red: "bg-red-soft text-red",
  cyan: "bg-cyan-soft text-cyan",
  amber: "bg-amber-soft text-amber",
};

export default function NoteBox({
  icon,
  tone,
  children,
}: {
  icon: string;
  tone: "red" | "cyan" | "amber";
  children: ReactNode;
}) {
  return (
    <div className="flex gap-3 rounded-xl border border-line bg-bg2 px-4 py-3.5 text-[0.8rem] text-mut">
      <div
        className={`flex h-[34px] w-[34px] flex-none items-center justify-center rounded-[9px] font-sora text-[0.85rem] font-extrabold ${TONE_STYLES[tone]}`}
      >
        {icon}
      </div>
      <div>{children}</div>
    </div>
  );
}
