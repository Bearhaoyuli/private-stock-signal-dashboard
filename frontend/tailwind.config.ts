import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#111111",
        sand: "#f4efe3",
        clay: "#dbd0be",
        pine: "#214031",
        ember: "#8f3b2f",
        brass: "#7b5b14",
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "ui-sans-serif", "system-ui"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "SFMono-Regular"],
      },
      boxShadow: {
        panel: "0 14px 48px rgba(17, 17, 17, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;

