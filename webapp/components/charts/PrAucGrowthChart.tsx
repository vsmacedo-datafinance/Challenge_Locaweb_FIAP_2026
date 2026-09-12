import type { PrAucGrowthPoint } from "@/lib/types";

const X_POSITIONS = [80, 180, 280];
const OPACITIES = [0.45, 0.7, 1];
const MAX_VALUE = 0.24;
const BASELINE_Y = 170;
const MAX_HEIGHT = 120;
const BAR_WIDTH = 60;

export default function PrAucGrowthChart({ data }: { data: PrAucGrowthPoint[] }) {
  const heights = data.map((point) => {
    const numeric = parseFloat(point.value.replace(",", "."));
    return Math.max(4, (numeric / MAX_VALUE) * MAX_HEIGHT);
  });

  return (
    <svg viewBox="0 0 420 210" width="100%">
      <line x1={46} y1={170} x2={400} y2={170} stroke="var(--line)" />
      <line x1={46} y1={110} x2={400} y2={110} stroke="#171B25" />
      <line x1={46} y1={50} x2={400} y2={50} stroke="#171B25" />
      <text x={14} y={174} fontSize={10}>
        0,0
      </text>
      <text x={14} y={114} fontSize={10}>
        0,12
      </text>
      <text x={14} y={54} fontSize={10}>
        0,24
      </text>

      {data.map((point, i) => {
        const x = X_POSITIONS[i] ?? X_POSITIONS[X_POSITIONS.length - 1];
        return (
          <rect
            key={point.period}
            x={x}
            y={BASELINE_Y - heights[i]}
            width={BAR_WIDTH}
            height={heights[i]}
            rx={5}
            fill="var(--red)"
            opacity={OPACITIES[i] ?? 1}
          />
        );
      })}

      <g fontSize={11} textAnchor="middle" fill="var(--txt)" fontWeight={600}>
        {data.map((point, i) => {
          const x = (X_POSITIONS[i] ?? X_POSITIONS[X_POSITIONS.length - 1]) + BAR_WIDTH / 2;
          return (
            <text key={point.period} x={x} y={BASELINE_Y - heights[i] - 9}>
              {point.value}
            </text>
          );
        })}
      </g>

      <g fontSize={10} textAnchor="middle">
        {data.map((point, i) => {
          const x = (X_POSITIONS[i] ?? X_POSITIONS[X_POSITIONS.length - 1]) + BAR_WIDTH / 2;
          return (
            <text key={point.period} x={x} y={188}>
              {point.period}
            </text>
          );
        })}
      </g>
    </svg>
  );
}
