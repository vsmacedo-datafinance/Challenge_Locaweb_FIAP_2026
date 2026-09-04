import type { KpiCard as KpiCardData } from "@/lib/types";

const TONE_TEXT: Record<string, string> = {
  default: "",
  cyan: "text-cyan",
  red: "text-red",
  amber: "text-amber",
};

export default function KpiCard({ kpi }: { kpi: KpiCardData }) {
  return (
    <div
      className={`relative overflow-hidden rounded-chronos border border-line bg-panel p-4 ${
        kpi.highlight ? "before:absolute before:inset-x-0 before:top-0 before:h-0.5 before:bg-red before:content-['']" : ""
      }`}
    >
      <div className="mb-1.5 text-[0.72rem] text-mut">{kpi.label}</div>
      <div className={`font-sora text-[1.85rem] font-extrabold leading-none ${TONE_TEXT[kpi.tone]}`}>{kpi.value}</div>
      <div className="mt-1.5 text-[0.7rem] text-mut2">{kpi.sub}</div>
    </div>
  );
}
