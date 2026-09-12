import { renderBold } from "@/lib/boldText";
import type { ExplainabilityData } from "@/lib/types";
import NoteBox from "./NoteBox";

function FactorRow({ factor, pct, positive }: { factor: string; pct: string; positive: boolean }) {
  const width = Math.min(50, Math.abs(parseFloat(pct)) * 1.5);
  return (
    <div className="mb-1.5 grid grid-cols-[170px_1fr_50px] items-center gap-2.5 text-[0.74rem]">
      <span className="text-[#c7ccda]">{factor}</span>
      <span className="relative h-1.5 rounded-[5px] bg-[#1b202c]">
        <i
          className={`absolute top-0 h-full rounded-[5px] ${positive ? "bg-red" : "bg-cyan"}`}
          style={positive ? { left: "50%", width: `${width}%` } : { right: "50%", width: `${width}%` }}
        />
      </span>
      <span className={`text-right font-sora font-semibold ${positive ? "text-red" : "text-cyan"}`}>{pct}</span>
    </div>
  );
}

export default function ExplainabilityPanel({
  data,
  probabilityLabel,
}: {
  data: ExplainabilityData;
  probabilityLabel: string;
}) {
  return (
    <div className="rounded-chronos border border-line bg-panel p-4">
      <h3 className="text-[0.9rem] font-semibold">
        Por que {probabilityLabel}? · {data.incident_id}
      </h3>
      <p className="mb-3 text-[0.73rem] text-mut">Fatores do score deste chamado (explicabilidade)</p>

      <div className="mb-2 text-[0.74rem] text-mut">Elevam o risco</div>
      {data.increasing.map((f) => (
        <FactorRow key={f.factor} factor={f.factor} pct={f.pct} positive />
      ))}

      <div className="mb-2 mt-3 text-[0.74rem] text-mut">Reduzem o risco</div>
      {data.decreasing.map((f) => (
        <FactorRow key={f.factor} factor={f.factor} pct={f.pct} positive={false} />
      ))}

      <div className="mt-4">
        <NoteBox icon="3" tone="red">
          {renderBold(data.summary_note)}
        </NoteBox>
      </div>
    </div>
  );
}
