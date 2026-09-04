export default function CeilingTrendChart() {
  return (
    <svg viewBox="0 0 640 200" width="100%">
      <line x1={34} y1={172} x2={626} y2={172} stroke="var(--line)" />
      <line x1={34} y1={84} x2={626} y2={84} stroke="var(--amber)" strokeDasharray="6 5" opacity={0.7} />
      <text x={540} y={77} fontSize={10} fill="var(--amber)">
        teto (meta)
      </text>
      <polyline
        points="34,130 74,118 114,124 154,106 194,96 234,108 274,90 314,82 354,76 394,86 434,70 474,62 514,72 554,56 594,50 626,54"
        fill="none"
        stroke="var(--txt)"
        strokeWidth={2}
      />
      <circle cx={594} cy={50} r={3.6} fill="var(--red)" />
      <text x={556} y={38} fontSize={10} fill="var(--red)">
        125% da meta
      </text>
    </svg>
  );
}
