import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Original tokens — kept so existing utility classes keep working.
        ink: "#0b0b10",
        plum: "#1a1326",
        accent: "#c79bff",
        gold: "#d6b66a",
        // Generative Atelier palette — used for gradient accents,
        // streaming-state pulses and conic gauges.
        magenta: "#ff2d6e",
        cyan: "#3ee5ff",
        // Soft elevated surface for cards under the grain layer.
        surface: "#15111d",
      },
      fontFamily: {
        // Editorial display — used for hero / page titles.
        display: ["Georgia", "ui-serif", "serif"],
        // Mono block — lyric sheet, persona id, BPM/key chips.
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "Liberation Mono",
          "Courier New",
          "monospace",
        ],
      },
      backgroundImage: {
        // Signature magenta → cyan ribbon.
        atelier: "linear-gradient(120deg, #ff2d6e 0%, #c79bff 50%, #3ee5ff 100%)",
        "atelier-soft":
          "linear-gradient(120deg, rgba(255,45,110,0.18) 0%, rgba(199,155,255,0.18) 50%, rgba(62,229,255,0.18) 100%)",
      },
      boxShadow: {
        // Soft cinematic bloom around CTA buttons / streaming nodes.
        bloom: "0 0 24px -4px rgba(255,45,110,0.55), 0 0 48px -10px rgba(62,229,255,0.45)",
        "bloom-soft": "0 0 18px -8px rgba(199,155,255,0.6)",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": {
            boxShadow:
              "0 0 0 0 rgba(255,45,110,0.45), 0 0 0 0 rgba(62,229,255,0.0)",
          },
          "50%": {
            boxShadow:
              "0 0 0 6px rgba(255,45,110,0.0), 0 0 18px 4px rgba(62,229,255,0.45)",
          },
        },
        shimmer: {
          "0%": { backgroundPosition: "0% 50%" },
          "100%": { backgroundPosition: "200% 50%" },
        },
      },
      animation: {
        "pulse-glow": "pulse-glow 1.8s ease-in-out infinite",
        shimmer: "shimmer 6s linear infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
