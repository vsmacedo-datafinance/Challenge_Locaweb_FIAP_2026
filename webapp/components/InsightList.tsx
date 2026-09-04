import { renderBold } from "@/lib/boldText";
import type { InsightData } from "@/lib/types";
import NoteBox from "./NoteBox";

export default function InsightList({ insights }: { insights: InsightData[] }) {
  return (
    <div className="flex flex-col gap-2">
      {insights.map((insight, i) => (
        <NoteBox key={insight.text} icon={String(i + 1)} tone={insight.tone}>
          {renderBold(insight.text)}
        </NoteBox>
      ))}
    </div>
  );
}
