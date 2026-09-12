import type { ModelComparisonRow } from "@/lib/types";

const BAR_COLOR: Record<string, string> = { red: "bg-red", gray: "bg-[#5f6779]" };

export default function ModelComparisonTable({ rows }: { rows: ModelComparisonRow[] }) {
  return (
    <table className="w-full text-[0.78rem]">
      <thead>
        <tr>
          {["Modelo", "PR-AUC", "", "Leitura"].map((h, i) => (
            <th
              key={i}
              className="border-b border-line px-2.5 py-1.5 text-left text-[0.66rem] font-semibold uppercase text-mut2"
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="[&>tr:last-child>td]:border-b-0">
        {rows.map((row) => (
          <tr key={row.model}>
            <td className="border-b border-[#171c27] px-2.5 py-2">{row.model}</td>
            <td
              className={`border-b border-[#171c27] px-2.5 py-2 font-sora font-semibold ${
                row.tone === "red" ? "text-red" : ""
              }`}
            >
              {row.pr_auc}
            </td>
            <td className="border-b border-[#171c27] px-2.5 py-2">
              <span className="block h-1.5 min-w-[70px] overflow-hidden rounded-md bg-[#1b202c]">
                <i className={`block h-full rounded-md ${BAR_COLOR[row.tone]}`} style={{ width: `${row.bar_pct}%` }} />
              </span>
            </td>
            <td className="border-b border-[#171c27] px-2.5 py-2">{row.note}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
