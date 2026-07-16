import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#FFFFFF",
        "surface-muted": "#F6F7F9",
        border: "#E3E6EB",
        "text-primary": "#14181F",
        "text-secondary": "#5B6472",
        accent: { 50: "#EAF0FE", 600: "#2F5FDE", 700: "#23409E" },
        success: { 50: "#E9F7EF", 600: "#1F9D66" },
        danger: { 50: "#FBEAEA", 600: "#D64545" },
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        sans: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
