/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        aqua: {
          DEFAULT: "#00D9C0",
          dark: "#00B4A0",
          light: "#33E8D4",
          muted: "#00D9C020",
        },
        surface: {
          DEFAULT: "#1A1A1A",
          light: "#2A2A2A",
          lighter: "#3A3A3A",
        },
        background: {
          DEFAULT: "#000000",
          secondary: "#0A0A0A",
        },
      },
    },
  },
  plugins: [],
};
