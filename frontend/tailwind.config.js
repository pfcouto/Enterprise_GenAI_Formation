/** @type {import('tailwindcss').Config} */
// Palette: Sunday League DESIGN.md (Floodlight dark scheme). One blue accent, navy-tinted neutrals,
// one warm note (tertiary). The stock Tailwind ramps used by the components are re-pointed to those tokens,
// so no component hard-codes a hex value. No gradients anywhere.
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        // navy neutrals (surface ladder + text roles)
        slate: {
          50: "#F6F8FB", 100: "#E8EEF4", 200: "#DCE6F0", 300: "#B6C6D8", 400: "#A6B4C4",
          500: "#6F8093", 600: "#47566A", 700: "#34414F", 800: "#2B3643", 900: "#1D2630", 950: "#141B23",
        },
        // brand accent: logo blue family
        blue: {
          50: "#D3E8FB", 100: "#D3E8FB", 200: "#D3E8FB", 300: "#9BD0F5", 400: "#4AADEE", 500: "#219AE5",
          600: "#0863A3", 700: "#0E4A73", 800: "#0E4A73", 900: "#0A3552", 950: "#04223A",
        },
        // the warm note (tertiary): second track, highlights, warnings
        amber: {
          200: "#FFE3BD", 300: "#FFD08E", 400: "#FFB95C", 500: "#E39A2E", 600: "#8A5300",
          700: "#6E4300", 800: "#5C3C00", 900: "#472A00", 950: "#2C1A00",
        },
        // semantic success only (SuccessGreen)
        green: { 300: "#8FD493", 400: "#4CAF50", 500: "#4CAF50", 600: "#3D8E41", 900: "#17361A", 950: "#0F2411" },
        red: { 400: "#FFB4AB", 500: "#BA1A1A" },
      },
    },
  },
  plugins: [],
};
