export const FREE_BETA_CONTINUITY_DAYS = 180;
export const FREE_BETA_CONTINUITY_WINDOW = `${FREE_BETA_CONTINUITY_DAYS}d`;

export const MOBILE_CONTINUITY_PLAN = {
  tier: "beta_free" as const,
  continuityDays: FREE_BETA_CONTINUITY_DAYS,
  continuityWindow: FREE_BETA_CONTINUITY_WINDOW,
  title: `${FREE_BETA_CONTINUITY_DAYS}-day continuity`,
  badge: "Beta access",
  summary: `Talk and Offload both stay connected across your last ${FREE_BETA_CONTINUITY_DAYS} days.`,
  upgradeCopy: "Upgrade later to keep your full history connected.",
};

