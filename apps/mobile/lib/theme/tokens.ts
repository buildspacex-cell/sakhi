export const colors = {
  bg: "#0B1020",
  bgElevated: "#0F1628",
  surface: "rgba(21, 28, 40, 0.78)",
  surfaceStrong: "rgba(16, 23, 37, 0.94)",
  surfaceMuted: "rgba(27, 36, 54, 0.74)",
  border: "rgba(159, 174, 199, 0.18)",
  borderStrong: "rgba(189, 202, 223, 0.32)",
  text: "#F5F7FB",
  textMuted: "#98A3B8",
  textSubtle: "#7E8798",
  textFaint: "#5E6A7C",
  accent: "#AEBFDB",
  accentBright: "#DCE7FA",
  accentSoft: "rgba(174, 191, 219, 0.14)",
  accentText: "#EDF3FF",
  accentInk: "#172033",
  accentBorder: "rgba(174, 191, 219, 0.4)",
  userBubble: "rgba(39, 50, 69, 0.96)",
  sakhiBubble: "rgba(23, 31, 46, 0.94)",
  deepBubble: "rgba(42, 52, 74, 0.94)",
  systemBubble: "rgba(31, 40, 56, 0.86)",
  gold: "#AEBFDB",
  goldText: "#EDF3FF",
  goldBorder: "rgba(174, 191, 219, 0.4)",
  goldSurface: "rgba(42, 52, 74, 0.94)",
  danger: "#E1AAB3",
  dangerStrong: "#ef6f7e",
  dangerSurface: "rgba(88, 33, 44, 0.36)",
  success: "#93C0A7",
  successSurface: "rgba(37, 61, 53, 0.62)",
  warning: "#DCC698",
  warningSurface: "rgba(88, 72, 45, 0.54)",
  white: "#ffffff",
  black: "#000000",
} as const;

export const spacing = {
  xxs: 4,
  xs: 8,
  sm: 10,
  md: 12,
  lg: 16,
  xl: 20,
  "2xl": 24,
  "3xl": 28,
  "4xl": 32,
  "5xl": 40,
  "6xl": 56,
} as const;

export const radii = {
  sm: 12,
  md: 16,
  lg: 20,
  xl: 24,
  pill: 999,
} as const;

export const typography = {
  kicker: {
    fontSize: 11,
    letterSpacing: 1.1,
    lineHeight: 14,
  },
  label: {
    fontSize: 12,
    lineHeight: 17,
  },
  body: {
    fontSize: 14,
    lineHeight: 20,
  },
  bodyStrong: {
    fontSize: 15,
    lineHeight: 22,
  },
  title: {
    fontSize: 20,
    lineHeight: 26,
  },
  hero: {
    fontSize: 24,
    lineHeight: 34,
  },
} as const;

export const layout = {
  touchMin: 48,
  buttonHeight: 52,
  iconButton: 36,
} as const;

export const shadow = {
  soft: {
    shadowColor: "#000000",
    shadowOpacity: 0.18,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  card: {
    shadowColor: "#000000",
    shadowOpacity: 0.25,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
    elevation: 3,
  },
  accent: {
    shadowColor: "#506381",
    shadowOpacity: 0.26,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
  },
} as const;

export const aurora = {
  teal: "rgba(126, 147, 190, 0.1)",
  tealSoft: "rgba(152, 170, 206, 0.08)",
  amber: "rgba(152, 170, 206, 0.06)",
  amberSoft: "rgba(122, 138, 172, 0.08)",
} as const;

export const theme = {
  colors,
  spacing,
  radii,
  typography,
  layout,
  shadow,
  aurora,
} as const;

export type MobileTheme = typeof theme;
