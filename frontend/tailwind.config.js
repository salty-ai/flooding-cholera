/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#1392ec",
        "alert-orange": "#fa6238",
        "env-green": "#0bda5b",
        surface: {
          DEFAULT: "#ffffff",
          highlight: "#f0f2f5",
        },
        risk: {
          low: '#22c55e',
          medium: '#eab308',
          high: '#ef4444',
          unknown: '#6b7280',
        },
      },
      fontFamily: {
        display: ["Inter", "sans-serif"],
        sans: ["Inter", "sans-serif"],
        mono: ["'JetBrains Mono'", "'Fira Code'", "monospace"],
      },
    },
  },
  plugins: [],
}
