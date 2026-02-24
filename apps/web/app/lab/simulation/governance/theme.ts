// Light-theme palette for governance components
// Matches the warm lab/simulation design system
export const govPalette = {
  bg: "#faf8f5",
  card: "#ffffff",
  cardAlt: "#f5f0eb",
  border: "#e8e0d8",
  text: "#2d2a26",
  textSecondary: "#5a5450",
  muted: "#8a7f73",
  dim: "#a09890",
  veryDim: "#c4bdb5",
  accent: "#c4703f",
  accentLight: "#f0e0d0",
  // Semantic status colors
  allow: "#4caf7a",
  allowBg: "rgba(76, 175, 122, 0.08)",
  warn: "#e6923a",
  warnBg: "rgba(230, 146, 58, 0.08)",
  block: "#e05555",
  blockBg: "rgba(224, 85, 85, 0.08)",
  reconcile: "#a855f7",
  reconcileBg: "rgba(168, 85, 247, 0.08)",
  // Check indicators
  checkPass: "#4caf7a",
  checkFail: "#e05555",
};

// Profile definitions with light-theme colorDim
export const GOV_PROFILES = [
  {
    id: "adaptive" as const,
    label: "Adaptive",
    osType: "Vata-dominant",
    dosha: "Vata",
    color: "#8b5cf6",
    colorDim: "rgba(139, 92, 246, 0.08)",
    doshaScores: { vata: 0.50, pitta: 0.30, kapha: 0.20 },
  },
  {
    id: "performance" as const,
    label: "Performance",
    osType: "Pitta-dominant",
    dosha: "Pitta",
    color: "#f59e0b",
    colorDim: "rgba(245, 158, 11, 0.08)",
    doshaScores: { vata: 0.20, pitta: 0.50, kapha: 0.30 },
  },
  {
    id: "conservation" as const,
    label: "Conservation",
    osType: "Kapha-dominant",
    dosha: "Kapha",
    color: "#10b981",
    colorDim: "rgba(16, 185, 129, 0.08)",
    doshaScores: { vata: 0.20, pitta: 0.30, kapha: 0.50 },
  },
];
