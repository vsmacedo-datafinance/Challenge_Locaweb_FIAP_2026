import type { SchedulePlanRow } from "@/lib/types";

export default function SchedulePlanTable({ rows }: { rows: SchedulePlanRow[] }) {
  return (
    <table className="w-full text-[0.78rem]">
      <thead>
        <tr>
          {["Dia", "Previsto", "Sugestão"].map((h) => (
            <th
              key={h}
              className="border-b border-line px-2.5 py-1.5 text-left text-[0.66rem] font-semibold uppercase text-mut2"
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="[&>tr:last-child>td]:border-b-0">
        {rows.map((row) => (
          <tr key={row.day}>
            <td className="border-b border-[#171c27] px-2.5 py-2">{row.day}</td>
            <td className="border-b border-[#171c27] px-2.5 py-2 font-sora font-semibold">{row.forecast}</td>
            <td className={`border-b border-[#171c27] px-2.5 py-2 ${row.tone === "amber" ? "text-amber" : ""}`}>
              {row.suggestion}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
