import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./hooks/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        night: {
          50: "#eef7ff",
          100: "#d8ecff",
          200: "#b9d6ff",
          300: "#90b4ff",
          400: "#5a8ee1",
          500: "#3c6bc0",
          600: "#2b4f95",
          700: "#203a6a",
          800: "#142346",
          900: "#0b1429",
          950: "#050916"
        }
      }
    }
  },
  plugins: []
};

export default config;

