import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0C11",
        bg2: "#0E1119",
        panel: "#121620",
        line: "#1F2430",
        red: "#F5233C",
        "red-soft": "rgba(245,35,60,.13)",
        cyan: "#45E0E6",
        "cyan-soft": "rgba(69,224,230,.11)",
        amber: "#F5A623",
        "amber-soft": "rgba(245,166,35,.13)",
        txt: "#EDEFF4",
        mut: "#98A0B3",
        mut2: "#5F6779",
      },
      fontFamily: {
        sora: ["var(--font-sora)", "system-ui", "sans-serif"],
        inter: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        chronos: "14px",
      },
    },
  },
  plugins: [],
};

export default config;
