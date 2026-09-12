import type { RiskItemData } from "@/lib/types";

const TONE_BG: Record<string, string> = { red: "bg-red", amber: "bg-amber", cyan: "bg-cyan" };
const TONE_TEXT: Record<string, string> = { red: "text-red", amber: "text-amber", cyan: "text-cyan" };

export default function RiskRadar({ items, compact = false }: { items: RiskItemData[]; compact?: boolean }) {
  return (
    <div className="flex flex-col gap-1.5">
      {items.map((item) => (
        <div
          key={item.incident_id}
          className={`grid items-center gap-2.5 rounded-[10px] border border-line bg-bg2 px-3 py-2.5 text-[0.78rem] ${
            compact ? "grid-cols-[22px_96px_1fr_52px]" : "grid-cols-[24px_100px_1fr_110px_56px]"
          }`}
        >
          <span className="font-sora font-bold text-mut2">{item.rank}</span>
          <span className="font-sora text-[0.76rem] font-semibold">{item.incident_id}</span>
          {!compact && (
            <span className="overflow-hidden truncate text-[0.72rem] text-mut">
              <b className="font-medium text-[#c7ccda]">{item.team}</b> · {item.asset} · {item.description}
            </span>
          )}
          <span className="h-[7px] overflow-hidden rounded-md bg-[#1b202c]">
            <i
              className={`block h-full rounded-md ${TONE_BG[item.tone]}`}
              style={{ width: `${Math.round(item.probability * 100)}%` }}
            />
          </span>
          <span className={`text-right font-sora text-[0.82rem] font-bold ${TONE_TEXT[item.tone]}`}>
            {Math.round(item.probability * 100)}%
          </span>
        </div>
      ))}
    </div>
  );
}
