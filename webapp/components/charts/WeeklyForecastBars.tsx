const BARS = [
  { x: 58, y: 143, h: 45, color: "var(--red)" },
  { x: 58, y: 80, h: 61, color: "var(--cyan)" },
  { x: 138, y: 138, h: 50, color: "var(--red)" },
  { x: 138, y: 57, h: 79, color: "var(--cyan)" },
  { x: 218, y: 147, h: 41, color: "var(--red)" },
  { x: 298, y: 147, h: 41, color: "var(--red)" },
  { x: 378, y: 125, h: 63, color: "var(--red)" },
  { x: 378, y: 39, h: 84, color: "var(--cyan)" },
  { x: 458, y: 125, h: 63, color: "var(--red)" },
  { x: 458, y: 35, h: 88, color: "var(--cyan)" },
  { x: 538, y: 125, h: 63, color: "var(--red)" },
  { x: 538, y: 51, h: 72, color: "var(--cyan)" },
];

const DAY_LABELS = [
  { x: 79, label: "sex" },
  { x: 159, label: "sáb" },
  { x: 239, label: "dom" },
  { x: 319, label: "seg" },
  { x: 399, label: "ter" },
  { x: 479, label: "qua" },
  { x: 559, label: "qui" },
];

const TOTAL_LABELS = [
  { x: 79, y: 70, value: "24" },
  { x: 159, y: 47, value: "29" },
  { x: 239, y: 137, value: "9" },
  { x: 319, y: 137, value: "9" },
  { x: 399, y: 29, value: "33" },
  { x: 479, y: 25, value: "34" },
  { x: 559, y: 41, value: "30" },
];

export default function WeeklyForecastBars() {
  return (
    <svg viewBox="0 0 640 225" width="100%">
      <line x1={34} y1={188} x2={626} y2={188} stroke="var(--line)" />
      <g>
        {BARS.map((bar, i) => (
          <rect key={i} x={bar.x} y={bar.y} width={42} height={bar.h} rx={4} fill={bar.color} opacity={bar.color === "var(--red)" ? 0.85 : 0.8} />
        ))}
      </g>
      <g fontSize={11} textAnchor="middle">
        {DAY_LABELS.map((d) => (
          <text key={d.label} x={d.x} y={206}>
            {d.label}
          </text>
        ))}
      </g>
      <g fontSize={11} textAnchor="middle" fill="var(--txt)" fontWeight={600}>
        {TOTAL_LABELS.map((t) => (
          <text key={t.x} x={t.x} y={t.y}>
            {t.value}
          </text>
        ))}
      </g>
    </svg>
  );
}
