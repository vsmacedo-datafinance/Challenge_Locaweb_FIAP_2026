import KpiCard from "./KpiCard";
import type { KpiCard as KpiCardData } from "@/lib/types";

export default function KpiGrid({ kpis }: { kpis: KpiCardData[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {kpis.map((kpi) => (
        <KpiCard key={kpi.label} kpi={kpi} />
      ))}
    </div>
  );
}
