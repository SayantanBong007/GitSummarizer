/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      // A defined depth system instead of scattered arbitrary shadow values --
      // slate-tinted (not neutral gray) so shadows harmonize with the brand hue.
      boxShadow: {
        card:        "0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.06)",
        "card-hover": "0 8px 20px -4px rgb(15 23 42 / 0.10), 0 3px 8px -3px rgb(15 23 42 / 0.06)",
        glow:        "0 0 0 1px rgb(99 102 241 / 0.08), 0 12px 32px -8px rgb(99 102 241 / 0.25)",
      },
      backgroundImage: {
        "dot-grid":
          "radial-gradient(circle, rgb(99 102 241 / 0.14) 1px, transparent 1px)",
      },
      backgroundSize: {
        dots: "24px 24px",
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: "none",
            code: { color: "#4f46e5" },
            "code::before": { content: '""' },
            "code::after": { content: '""' },
          },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
