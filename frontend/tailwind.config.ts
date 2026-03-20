/* Tailwind configuration */
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sage: {
          50: "#F4F7F3",
          100: "#E8EFE6",
          200: "#D1DDD2",
          300: "#B9CCBE",
          400: "#A2BBAA",
          500: "#8BAA96",
          600: "#6B8E71",
          700: "#5A7A63",
          800: "#496655",
          900: "#385247",
        },
        terracotta: {
          50: "#FBF5F1",
          100: "#F5E8DC",
          200: "#EDD3BA",
          300: "#E5BE98",
          400: "#DDA976",
          500: "#D4845C",
          600: "#C67950",
          700: "#B86D43",
          800: "#A96037",
          900: "#8B4E2A",
        },
        forest: {
          50: "#F1F5ED",
          100: "#E3EBDB",
          200: "#C7D7B7",
          300: "#ABC393",
          400: "#8FAF6F",
          500: "#739B4B",
          600: "#5D8535",
          700: "#476F2A",
          800: "#315921",
          900: "#1F3A15",
        },
        cream: "#F5F1E8",
        sand: "#D4C4B0",
      },
      fontFamily: {
        serif: ["Playfair Display", "serif"],
        sans: ["Montserrat", "Lato", "sans-serif"],
      },
    },
  },
  plugins: [],
};
