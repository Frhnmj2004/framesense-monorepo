import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: "#76a939",
        "background-dark": "#0f1510",
        yellowGreen: {
          50: "#f4faeb",
          100: "#e7f3d4",
          200: "#d1e7af",
          300: "#aad373",
          400: "#94c457",
          500: "#76a939",
          600: "#5a862a",
          700: "#466724",
          800: "#3a5321",
          900: "#334720",
          950: "#18260d",
        },
      },
      fontFamily: {
        display: ["var(--font-be-vietnam-pro)", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        "2xl": "1rem",
        full: "9999px",
      },
      animation: {
        shimmer: "shimmer 2s ease-in-out infinite",
      },
      keyframes: {
        shimmer: {
          "0%, 100%": { opacity: "0.3" },
          "50%": { opacity: "0.8" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
