/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0f1115",
          900: "#141922",
          800: "#1c2330",
        },
        mist: {
          100: "#eef2ff",
          200: "#cbd5e1",
          400: "#94a3b8",
        },
        aurora: {
          300: "#9fb9ff",
          400: "#6f8dff",
          500: "#4f67ff",
        },
      },
      fontFamily: {
        sans: ['"Avenir Next"', '"Segoe UI"', "sans-serif"],
        display: ['"Iowan Old Style"', '"Palatino Linotype"', "serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 24px 80px rgba(0, 0, 0, 0.32)",
      },
      backgroundImage: {
        "hero-glow":
          "radial-gradient(circle at top left, rgba(111, 141, 255, 0.22), transparent 34%), radial-gradient(circle at 80% 10%, rgba(255, 255, 255, 0.08), transparent 22%), radial-gradient(circle at bottom right, rgba(77, 111, 255, 0.14), transparent 30%)",
      },
    },
  },
  plugins: [],
};
