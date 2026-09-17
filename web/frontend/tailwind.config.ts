import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // GEOReady brand palette
        navy: {
          950: "#060A14",
          900: "#0A0F1E",
          800: "#0F172A",
          700: "#1A2236",
          600: "#243049",
        },
        indigo: {
          400: "#818CF8",
          500: "#6366F1",
          600: "#4F46E5",
          700: "#4338CA",
        },
        emerald: {
          400: "#34D399",
          500: "#10B981",
        },
        amber: {
          400: "#FCD34D",
          500: "#F59E0B",
        },
        crimson: {
          400: "#F87171",
          500: "#EF4444",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "hero-glow":
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(79,70,229,0.15), transparent)",
        "card-glow":
          "linear-gradient(135deg, rgba(79,70,229,0.08) 0%, transparent 60%)",
      },
      boxShadow: {
        "glow-indigo": "0 0 20px rgba(79,70,229,0.3)",
        "glow-emerald": "0 0 20px rgba(16,185,129,0.3)",
        "glow-crimson": "0 0 20px rgba(239,68,68,0.3)",
        card: "0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.05)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "spin-slow": "spin 3s linear infinite",
        "fade-in": "fadeIn 0.5s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
