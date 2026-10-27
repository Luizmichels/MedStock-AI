import type { Config } from "tailwindcss";

/**
 * Tokens do design "Previa Insumos". As cores pontuais também podem ser usadas
 * diretamente via valores arbitrários (ex.: bg-[#0A2540]) nos componentes.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      colors: {
        navy: {
          DEFAULT: "#0A2540",
          900: "#071A2E",
          700: "#0E2F52",
          600: "#16426B",
        },
        brand: {
          DEFAULT: "#4AA8E0",
          600: "#3B97CF",
          700: "#2F8FD0",
          800: "#1F6FB2",
          900: "#1F5FA0",
        },
        ink: {
          DEFAULT: "#10243B",
          700: "#3B4B5E",
        },
        muted: {
          DEFAULT: "#5B6B7E",
          400: "#8494A6",
          300: "#9FB6CE",
        },
        line: {
          DEFAULT: "#DCE6F0",
          200: "#E4EBF2",
        },
        surface: {
          app: "#EEF3F9",
          panel: "#F5F8FC",
          sky: "#EAF3FB",
        },
      },
    },
  },
  plugins: [],
};

export default config;
