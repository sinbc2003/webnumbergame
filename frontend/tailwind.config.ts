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
          50: "#f4f5fb",
          100: "#e6e7f5",
          200: "#cdd2eb",
          300: "#a6b2db",
          400: "#7c8ec7",
          500: "#5d71b5",
          600: "#4a579c",
          700: "#3d4781",
          800: "#343a66",
          900: "#2d3354",
          950: "#151726"
        }
      }
    }
  },
  plugins: []
};

export default config;

