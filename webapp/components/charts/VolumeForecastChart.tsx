export default function VolumeForecastChart({ d1Callout }: { d1Callout: string }) {
  return (
    <svg viewBox="0 0 640 205" width="100%">
      <line x1={38} y1={168} x2={622} y2={168} stroke="var(--line)" />
      <line x1={38} y1={118} x2={622} y2={118} stroke="#171B25" />
      <line x1={38} y1={68} x2={622} y2={68} stroke="#171B25" />
      <text x={16} y={172} fontSize={10}>
        0
      </text>
      <text x={10} y={122} fontSize={10}>
        25
      </text>
      <text x={10} y={72} fontSize={10}>
        50
      </text>
      <path
        d="M448,140 L476,118 L504,152 L532,150 L560,102 L588,100 L616,110 L616,164 L588,160 L560,156 L532,166 L504,166 L476,150 L448,156 Z"
        fill="rgba(69,224,230,.10)"
      />
      <polyline
        points="40,118 69,108 98,124 127,96 156,90 185,132 214,138 243,104 272,98 301,112 330,86 359,92 388,128 417,110 448,146"
        fill="none"
        stroke="var(--txt)"
        strokeWidth={2}
      />
      <polyline
        points="448,146 476,134 504,159 532,159 560,127 588,126 616,131"
        fill="none"
        stroke="var(--cyan)"
        strokeWidth={2.4}
        strokeDasharray="6 5"
      />
      <line x1={448} y1={28} x2={448} y2={168} stroke="#2B3242" strokeDasharray="3 4" />
      <text x={452} y={38} fontSize={10}>
        hoje
      </text>
      <circle cx={476} cy={134} r={3.4} fill="var(--cyan)" />
      <text x={464} y={121} fontSize={10} fill="var(--cyan)">
        {d1Callout}
      </text>
    </svg>
  );
}
