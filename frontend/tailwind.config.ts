import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111111",
        muted: "#6B7280",
        line: "#E5E7EB",
        accent: "#0F766E",
        review: "#B45309",
      },
    },
  },
  plugins: [],
};
export default config;
