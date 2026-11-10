/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0b0e16",
        surface: "#11151f",
        border: "#222938",
        muted: "#8995a8",
        blue: "#2864ed",
      },
    },
  },
  plugins: [],
};
